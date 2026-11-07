"""Steam 계정 연결 ─ OpenID 시작 · 콜백 · 해제 (decisions/0015, ARCHITECTURE 5.4절)

진짜 Steam은 부르지 않는다. check_authentication 답은 conftest의 fake_steam.openid_answer가 정한다.
"""

import asyncio
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from sqlalchemy import func, select

from app.core import oauth_state
from app.core.config import settings
from app.core.oauth_state import create_state
from app.models.user import User
from app.routers.steam_link import STATE_COOKIE_NAME, STATE_COOKIE_PATH
from app.services.steam_openid import STEAM_OPENID_URL, link_steam_account

A = "a@example.com"
B = "b@example.com"
STEAM_A = "76561197960287930"
STEAM_B = "76561198000000001"
CALLBACK = "/api/steam/link/callback"
SIGNED = "signed,op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle"


def return_to(nonce: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}{CALLBACK}?state={nonce}"


def assertion(nonce: str, steam_id: str = STEAM_A, **override: str | None) -> dict[str, str]:
    """Steam이 콜백 주소에 붙여 보내는 값. override로 한 칸씩 망가뜨린다(None이면 뺀다)"""
    claimed = f"https://steamcommunity.com/openid/id/{steam_id}"
    params = {
        "state": nonce,
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "id_res",
        "openid.op_endpoint": STEAM_OPENID_URL,
        "openid.claimed_id": claimed,
        "openid.identity": claimed,
        "openid.return_to": return_to(nonce),
        "openid.response_nonce": "2026-11-06T12:00:00ZabcDEF",
        "openid.assoc_handle": "1234567890",
        "openid.signed": SIGNED,
        "openid.sig": "c2lnbmF0dXJl",
    }
    for key, value in override.items():
        name = "openid." + key
        if value is None:
            params.pop(name, None)
        else:
            params[name] = value
    return params


async def start(client, headers) -> str:
    """연결을 시작하고 Steam 주소에 실린 nonce를 꺼낸다. state 쿠키는 client 쿠키 통에 담긴다"""
    res = await client.post("/api/steam/link/start", headers=headers)
    assert res.status_code == 200, res.text
    url = urlsplit(res.json()["redirect_url"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == STEAM_OPENID_URL
    query = parse_qs(url.query)
    assert query["openid.mode"] == ["checkid_setup"]
    assert query["openid.realm"] == [settings.public_base_url.rstrip("/")]
    sent_return_to = query["openid.return_to"][0]
    return parse_qs(urlsplit(sent_return_to).query)["state"][0]


async def callback(client, params: dict[str, str]) -> str:
    """콜백을 부르고 설정 화면에 붙은 결과(steam=)를 돌려준다"""
    res = await client.get(CALLBACK, params=params)
    assert res.status_code == 303, res.text
    location = urlsplit(res.headers["location"])
    assert location.path == "/settings"
    return parse_qs(location.query)["steam"][0]


async def me(client, headers) -> dict:
    res = await client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


# 점이 없는 호스트(https://test)의 쿠키를 httpx는 "test.local" 도메인으로 담는다 (표준 쿠키 통의 규칙)
# "test"로 넣으면 요청에 실리지 않아, 실패를 기대하는 테스트가 엉뚱한 이유로 통과한다
def state_cookie(client) -> str | None:
    return client.cookies.get(STATE_COOKIE_NAME, domain="test.local", path=STATE_COOKIE_PATH)


def put_state_cookie(client, value: str) -> None:
    client.cookies.set(STATE_COOKIE_NAME, value, domain="test.local", path=STATE_COOKIE_PATH)


# ─── 정상 흐름 ─────────────────────────────────────────────


async def test_link_success(client, auth_headers, fake_steam):
    headers = await auth_headers(A)
    nonce = await start(client, headers)
    assert state_cookie(client) is not None

    assert await callback(client, assertion(nonce)) == "linked"

    body = await me(client, headers)
    assert body["steam_id"] == STEAM_A
    assert body["steam_synced_at"] is None
    # 받은 그대로 되묻되 mode만 바꾼다. 우리가 쓰는 state는 Steam에 보내지 않는다
    assert len(fake_steam.openid_calls) == 1
    sent = fake_steam.openid_calls[0]
    assert sent["openid.mode"] == "check_authentication"
    assert sent["openid.sig"] == "c2lnbmF0dXJl"
    assert "state" not in sent
    # 쪽지는 한 번 쓰면 지운다
    assert state_cookie(client) is None


async def test_start_cookie_attributes(client, auth_headers):
    res = await client.post("/api/steam/link/start", headers=await auth_headers(A))
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert f"path={STATE_COOKIE_PATH}" in cookie
    assert "max-age=300" in cookie


# ─── 위조 · 바꿔치기 ─────────────────────────────────────────


@pytest.mark.parametrize(
    "answer",
    [
        "ns:http://specs.openid.net/auth/2.0\nis_valid:false\n",
        "is_valid:true\n",                                           # ns가 없다
        "ns:http://specs.openid.net/auth/2.0\nis_valid:true_not\n",  # 글자 포함으로 보면 통과한다
        "<html>is_valid:true</html>",
        "",
    ],
    ids=["false", "no-ns", "prefix", "html", "empty"],
)
async def test_steam_says_not_valid(client, auth_headers, fake_steam, answer):
    """Steam이 "내가 쓴 확인서가 아니다"라고 답하면 연결되지 않는다"""
    headers = await auth_headers(A)
    nonce = await start(client, headers)
    fake_steam.openid_answer = lambda request: httpx.Response(200, text=answer)

    assert await callback(client, assertion(nonce)) == "failed"
    assert (await me(client, headers))["steam_id"] is None


@pytest.mark.parametrize(
    "override",
    [
        {"return_to": "https://evil.example/callback?state=x"},   # 다른 사이트용 확인서
        {"op_endpoint": "https://evil.example/openid/login"},
        {"mode": "cancel"},
        {"ns": "http://openid.net/signon/1.1"},
        {"claimed_id": "http://steamcommunity.com/openid/id/76561197960287930"},
        {"claimed_id": "https://steamcommunity.com/openid/id/7656119796028793"},     # 16자리
        {"claimed_id": "https://steamcommunity.com.evil.example/openid/id/76561197960287930"},
        {"claimed_id": "https://steamcommunity.com/openid/id/76561197960287930/x"},
        {"identity": "https://steamcommunity.com/openid/id/76561198000000001"},      # claimed_id와 다르다
        {"signed": "signed,op_endpoint,return_to,response_nonce,assoc_handle"},      # claimed_id가 서명 밖
        {"signed": None},
        {"claimed_id": None},
        {"sig": "x" * 3000},                                                         # 이상하게 큰 값
    ],
    ids=[
        "return-to", "op-endpoint", "cancel", "ns", "http", "16-digits", "other-host", "suffix",
        "identity-mismatch", "unsigned-claimed-id", "no-signed", "no-claimed-id", "huge",
    ],
)
async def test_bad_assertion_rejected_without_asking_steam(client, auth_headers, fake_steam, override):
    """우리 쪽에서 볼 수 있는 이상은 Steam에 전화하기 전에 끊는다"""
    headers = await auth_headers(A)
    nonce = await start(client, headers)

    assert await callback(client, assertion(nonce, **override)) == "failed"
    assert fake_steam.openid_calls == []
    assert (await me(client, headers))["steam_id"] is None


async def test_too_many_params_rejected(client, auth_headers, fake_steam):
    headers = await auth_headers(A)
    nonce = await start(client, headers)
    params = assertion(nonce)
    params.update({f"openid.extra{i}": "x" for i in range(30)})

    assert await callback(client, params) == "failed"
    assert fake_steam.openid_calls == []


# ─── state 쪽지 ─────────────────────────────────────────────


async def test_state_cannot_be_reused(client, auth_headers):
    """같은 콜백을 다시 열어도(쿠키를 되살려도) 두 번 받지 않는다"""
    headers = await auth_headers(A)
    nonce = await start(client, headers)
    saved = state_cookie(client)
    assert await callback(client, assertion(nonce)) == "linked"

    res = await client.delete("/api/steam/link", headers=headers)
    assert res.status_code == 204
    put_state_cookie(client, saved)
    assert await callback(client, assertion(nonce)) == "failed"
    assert (await me(client, headers))["steam_id"] is None


async def test_no_cookie(client, auth_headers, fake_steam):
    headers = await auth_headers(A)
    nonce = await start(client, headers)
    client.cookies.clear()

    assert await callback(client, assertion(nonce)) == "failed"
    assert fake_steam.openid_calls == []


async def test_someone_elses_callback(client, auth_headers, fake_steam):
    """공격자가 자기 Steam 확인서가 붙은 콜백을 내 브라우저로 열게 해도, 내 계정에 붙지 않는다

    공격자의 nonce는 내 쿠키 속 nonce와 다르다. 내 nonce는 HttpOnly 쿠키 · Steam 주소에만 있어 공격자가 모른다
    """
    headers_a = await auth_headers(A)
    await auth_headers(B, nickname="attacker")
    await start(client, headers_a)                     # 내 브라우저에는 내 쪽지
    attacker_nonce, _ = create_state(2, "steam_link")  # 공격자가 자기 브라우저에서 받은 nonce

    assert await callback(client, assertion(attacker_nonce, STEAM_B)) == "failed"
    assert fake_steam.openid_calls == []
    assert (await me(client, headers_a))["steam_id"] is None


async def test_expired_state(client, auth_headers, monkeypatch):
    headers = await auth_headers(A)
    monkeypatch.setattr(oauth_state, "STATE_TTL_SECONDS", -1)
    nonce, cookie = create_state(1, "steam_link")
    put_state_cookie(client, cookie)

    assert await callback(client, assertion(nonce)) == "failed"
    assert (await me(client, headers))["steam_id"] is None


async def test_other_purpose_state(client, auth_headers):
    """Discord용 쪽지로 Steam 문을 열 수 없다"""
    headers = await auth_headers(A)
    nonce, cookie = create_state(1, "discord_login")
    put_state_cookie(client, cookie)

    assert await callback(client, assertion(nonce)) == "failed"
    assert (await me(client, headers))["steam_id"] is None


async def test_state_is_not_access_token(client, auth_headers):
    """state 쪽지는 키가 달라 출입증으로 쓸 수 없다"""
    await auth_headers(A)
    _, cookie = create_state(1, "steam_link")
    res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {cookie}"})
    assert res.status_code == 401


# ─── 이미 연결된 Steam ───────────────────────────────────────


async def test_steam_taken_by_other_account(client, auth_headers):
    headers_a = await auth_headers(A)
    headers_b = await auth_headers(B)
    assert await callback(client, assertion(await start(client, headers_a))) == "linked"

    assert await callback(client, assertion(await start(client, headers_b))) == "taken"
    assert (await me(client, headers_b))["steam_id"] is None
    assert (await me(client, headers_a))["steam_id"] == STEAM_A


async def test_start_when_already_linked(client, auth_headers):
    headers = await auth_headers(A)
    assert await callback(client, assertion(await start(client, headers))) == "linked"

    res = await client.post("/api/steam/link/start", headers=headers)
    assert res.status_code == 409


async def test_second_tab_does_not_overwrite(client, auth_headers, session_factory):
    """두 탭에서 시작해 다른 Steam으로 돌아오면 뒤에 온 쪽이 덮어쓰지 않는다"""
    await auth_headers(A)
    async with session_factory() as db:
        assert await link_steam_account(db, 1, STEAM_A) == "linked"
    async with session_factory() as db:
        assert await link_steam_account(db, 1, STEAM_B) == "already"
    async with session_factory() as db:
        assert await link_steam_account(db, 1, STEAM_A) == "linked"   # 같은 Steam이면 그대로 성공
        assert await link_steam_account(db, 99, STEAM_B) == "failed"  # 사라진 사용자
        assert await db.scalar(select(User.steam_id).where(User.id == 1)) == STEAM_A


async def test_two_accounts_link_same_steam_at_once(client, auth_headers, session_factory):
    """두 계정이 같은 Steam을 동시에 붙이면 하나만 남는다 ─ UNIQUE가 막는다"""
    await auth_headers(A)
    await auth_headers(B)

    async def link(user_id: int) -> str:
        async with session_factory() as db:
            return await link_steam_account(db, user_id, STEAM_A)

    results = await asyncio.gather(link(1), link(2))
    assert sorted(results) == ["linked", "taken"]
    async with session_factory() as db:
        count = await db.scalar(select(func.count()).select_from(User).where(User.steam_id == STEAM_A))
    assert count == 1


# ─── Steam 장애 ─────────────────────────────────────────────


def timeout_error(request):
    raise httpx.ConnectTimeout("느림", request=request)


@pytest.mark.parametrize(
    "respond",
    [timeout_error, lambda r: httpx.Response(503), lambda r: httpx.Response(429)],
    ids=["timeout", "503", "429"],
)
async def test_steam_unavailable(client, auth_headers, fake_steam, respond):
    headers = await auth_headers(A)
    nonce = await start(client, headers)
    fake_steam.openid_answer = respond

    assert await callback(client, assertion(nonce)) == "unavailable"
    assert (await me(client, headers))["steam_id"] is None


# ─── 해제 · 인증 ─────────────────────────────────────────────


async def test_unlink_clears_id_and_sync_time(client, auth_headers, session_factory):
    headers = await auth_headers(A)
    assert await callback(client, assertion(await start(client, headers))) == "linked"
    async with session_factory() as db:
        user = await db.get(User, 1)
        user.steam_synced_at = datetime.now(timezone.utc)
        await db.commit()

    for _ in range(2):   # 두 번 눌러도 같다
        res = await client.delete("/api/steam/link", headers=headers)
        assert res.status_code == 204
    body = await me(client, headers)
    assert body["steam_id"] is None
    assert body["steam_synced_at"] is None

    # 풀었으니 다시 연결할 수 있다
    assert await callback(client, assertion(await start(client, headers))) == "linked"


@pytest.mark.parametrize("method, path", [("POST", "/api/steam/link/start"), ("DELETE", "/api/steam/link")])
async def test_requires_login(client, method, path):
    res = await client.request(method, path)
    assert res.status_code == 401


# ─── Steam 이름 (services/steam.py fetch_persona_name) ─────────────────────


@pytest.fixture
def steam_key(monkeypatch):
    """이름을 받으려면 키가 있어야 한다. 다른 연결 테스트는 키 없이 돌아 Steam 이름을 묻지 않는다"""
    monkeypatch.setattr(settings, "steam_api_key", "secret-key-for-test")


async def test_link_saves_persona_name(client, auth_headers, fake_steam, steam_key):
    fake_steam.personas = {STEAM_A: "할로우 덕후"}
    headers = await auth_headers(A)
    assert await callback(client, assertion(await start(client, headers))) == "linked"

    body = await me(client, headers)
    assert body["steam_persona_name"] == "할로우 덕후"
    assert fake_steam.persona_calls == 1


@pytest.mark.parametrize(
    "respond",
    [lambda r: httpx.Response(500), lambda r: httpx.Response(200, json={"response": {"players": []}})],
    ids=["500", "no-player"],
)
async def test_link_succeeds_without_persona_name(client, auth_headers, fake_steam, steam_key, respond):
    """이름을 못 받아도 연결은 성공한다 ─ 이름은 다음 동기화가 다시 받는다"""
    fake_steam.persona_answer = respond
    headers = await auth_headers(A)
    assert await callback(client, assertion(await start(client, headers))) == "linked"

    body = await me(client, headers)
    assert body["steam_id"] == STEAM_A
    assert body["steam_persona_name"] is None


async def test_failed_link_does_not_ask_name(client, auth_headers, fake_steam, steam_key):
    """다른 계정이 쓰는 Steam(taken)이면 이름도 묻지 않는다"""
    fake_steam.personas = {STEAM_A: "할로우 덕후"}
    assert await callback(client, assertion(await start(client, await auth_headers(A)))) == "linked"
    calls = fake_steam.persona_calls

    headers_b = await auth_headers(B)
    assert await callback(client, assertion(await start(client, headers_b))) == "taken"
    assert fake_steam.persona_calls == calls
    assert (await me(client, headers_b))["steam_persona_name"] is None


async def test_unlink_clears_persona_name(client, auth_headers, fake_steam, steam_key):
    fake_steam.personas = {STEAM_A: "할로우 덕후", STEAM_B: "새 계정"}
    headers = await auth_headers(A)
    assert await callback(client, assertion(await start(client, headers))) == "linked"

    assert (await client.delete("/api/steam/link", headers=headers)).status_code == 204
    assert (await me(client, headers))["steam_persona_name"] is None

    # 다른 Steam을 붙이면 그 Steam의 이름이 된다 ─ 옛 이름이 남지 않는다
    assert await callback(client, assertion(await start(client, headers), steam_id=STEAM_B)) == "linked"
    assert (await me(client, headers))["steam_persona_name"] == "새 계정"


async def test_name_not_saved_after_unlink(client, auth_headers, session_factory):
    """이름을 받는 사이 다른 탭에서 해제했다 ─ 풀린 계정에 이름만 남지 않는다 (save_persona_name 조건부 UPDATE)"""
    from app.services.steam_openid import save_persona_name

    headers = await auth_headers(A)
    assert await callback(client, assertion(await start(client, headers))) == "linked"
    assert (await client.delete("/api/steam/link", headers=headers)).status_code == 204

    async with session_factory() as db:
        await save_persona_name(db, 1, STEAM_A, "늦게 온 이름")
    assert (await me(client, headers))["steam_persona_name"] is None

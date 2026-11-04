"""배포 전 정비 ─ 공개 서버에서 500이나 무제한 요청으로 이어질 입력들 (PLAN M4.5).

고치기 전에 먼저 실패하는 것을 확인한 테스트들이다.
"""

import json

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.rate_limit import login_ip_limiter
from app.services import entry as entry_service
from app.routers import entries as entries_router

EMAIL = "alice@example.com"
PASSWORD = "testpass123"


def as_json(body):
    """짝 없는 서로게이트 글자도 그대로 보낸다. httpx의 json=은 보내기 전에 UTF-8로 바꾸다 실패한다 ─ 브라우저는 이스케이프해서 보낼 수 있다"""
    return {"content": json.dumps(body), "headers": {"content-type": "application/json"}}


async def create(client, headers, title="Hollow Knight", **fields):
    sent = as_json({"title": title, "status": "BACKLOG", **fields})
    return await client.post("/api/entries", content=sent["content"], headers={**headers, **sent["headers"]})


# ── 설정 ────────────────────────────────────────────────


@pytest.mark.parametrize("secret", ["", "a", "x" * 31])
def test_short_jwt_secret_stops_the_server(secret):
    """짧은 비밀은 토큰 위조로 이어진다. 빈 값이면 로그인이 500이 된다 ─ 시작할 때 멈춘다"""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="x", jwt_secret_key=secret)


def test_unknown_env_keys_are_ignored(monkeypatch):
    """운영에서 .env를 하나로 합쳐도(POSTGRES_PASSWORD 등) 서버가 뜬다"""
    settings = Settings(_env_file=None, database_url="x", jwt_secret_key="x" * 32, POSTGRES_PASSWORD="y")
    assert settings.database_url == "x"


# ── 깨진 문자 ───────────────────────────────────────────


@pytest.mark.parametrize("bad", ["a\x00b", "a\ud800b"])
async def test_broken_text_in_entry_is_422(client, auth_headers, bad):
    headers = await auth_headers(EMAIL)
    res = await create(client, headers, title=bad)
    assert res.status_code == 422, res.text
    good = (await create(client, headers)).json()
    for body in ({"review": bad},):
        sent = as_json(body)
        res = await client.patch(f"/api/entries/{good['id']}", content=sent["content"], headers={**headers, **sent["headers"]})
        assert res.status_code == 422, res.text


@pytest.mark.parametrize(
    "body",
    [
        {"email": "new@example.com", "password": PASSWORD, "nickname": "a\x00b"},
        {"email": "new@example.com", "password": PASSWORD, "nickname": "a\ud800b"},
        {"email": "a\ud800@example.com", "password": PASSWORD, "nickname": "닉네임"},
        {"email": "new@example.com", "password": "pass\ud800word1", "nickname": "닉네임"},
    ],
)
async def test_broken_text_in_register_is_422(client, body):
    res = await client.post("/api/auth/register", **as_json(body))
    assert res.status_code == 422, res.text


@pytest.mark.parametrize("email", ["a\x00@example.com", "a\ud800@example.com", "x" * 5000])
async def test_broken_login_email_is_the_same_401(client, email):
    """로그인 실패는 이유를 가리지 않고 같은 답이다 (DESIGN 3.1절)"""
    res = await client.post("/api/auth/login", **as_json({"email": email, "password": PASSWORD}))
    assert res.status_code == 401, res.text
    assert res.json()["detail"] == "이메일 또는 비밀번호가 올바르지 않습니다"


async def test_nul_in_steam_search_is_422(client, auth_headers):
    headers = await auth_headers(EMAIL)
    res = await client.get("/api/steam/apps", params={"q": "ab\x00c"}, headers=headers)
    assert res.status_code == 422, res.text


async def test_422_does_not_echo_the_input(client):
    """Pydantic 기본 응답은 보낸 값을 돌려준다 ─ 짧은 비밀번호가 응답 본문에 그대로 찍힌다"""
    secret = "abc12"
    res = await client.post("/api/auth/register", json={"email": "new@example.com", "password": secret, "nickname": "닉네임"})
    assert res.status_code == 422
    assert secret not in res.text
    issue = res.json()["detail"][0]
    assert issue["loc"][-1] == "password"
    assert issue["msg"]


# ── 범위 ────────────────────────────────────────────────


@pytest.mark.parametrize("offset", [2**31, 2**63, 10**20])
async def test_huge_offset_is_422(client, auth_headers, offset):
    headers = await auth_headers(EMAIL)
    res = await client.get("/api/entries", params={"offset": offset}, headers=headers)
    assert res.status_code == 422, res.text


@pytest.mark.parametrize("date", ["0001-01-01", "1969-12-31", "2101-01-01", "9999-12-31"])
async def test_absurd_purchase_date_is_422(client, auth_headers, date):
    headers = await auth_headers(EMAIL)
    assert (await create(client, headers, purchased_at=date)).status_code == 422
    good = (await create(client, headers, title="다른 게임")).json()
    res = await client.patch(f"/api/entries/{good['id']}", json={"purchased_at": date}, headers=headers)
    assert res.status_code == 422, res.text


async def test_blank_password_is_422(client):
    res = await client.post("/api/auth/register", json={"email": "new@example.com", "password": " " * 8, "nickname": "닉네임"})
    assert res.status_code == 422, res.text


async def test_too_long_login_password_is_422(client):
    res = await client.post("/api/auth/login", json={"email": EMAIL, "password": "x" * 129})
    assert res.status_code == 422, res.text


# ── 동시 실행 ───────────────────────────────────────────


async def test_concurrent_duplicate_entry_is_409(client, auth_headers, monkeypatch):
    """1차 확인을 지나친 뒤 UNIQUE에 걸린 경우 ─ 코드의 제약 이름이 실제와 달라 500이었다"""
    headers = await auth_headers(EMAIL)
    assert (await create(client, headers)).status_code == 201

    async def never_exists(*args, **kwargs):
        return False

    monkeypatch.setattr(entries_router, "entry_exists", never_exists)
    res = await create(client, headers)
    assert res.status_code == 409, res.text
    assert res.json()["detail"] == "이미 등록된 게임입니다"


def test_entry_unique_name_matches_the_model():
    """이름을 문자열로 적어 두면 또 어긋난다 ─ 모델의 실제 제약과 대조한다"""
    from app.models.entry import Entry

    names = {c.name for c in Entry.__table__.constraints}
    assert entries_router.ENTRY_UNIQUE in names
    assert entry_service.MAX_LIMIT == 100


# ── 요청 제한 ───────────────────────────────────────────


async def test_login_is_limited_per_ip_and_account(client):
    """비밀번호 대입 ─ 같은 IP + 같은 계정의 실패가 쌓이면 429"""
    last = None
    for _ in range(11):
        last = await client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong-password"})
    assert last.status_code == 429, last.text
    assert last.headers["retry-after"]
    assert "잠시 후" in last.json()["detail"]


async def test_login_is_limited_per_ip(client):
    """계정을 바꿔 가며 찔러도 IP로 막는다"""
    login_ip_limiter.limit = 3
    try:
        codes = [
            (await client.post("/api/auth/login", json={"email": f"u{i}@example.com", "password": "wrong-password"})).status_code
            for i in range(4)
        ]
    finally:
        login_ip_limiter.limit = 30
    assert codes == [401, 401, 401, 429]


async def test_success_clears_account_failures(client, auth_headers):
    """제 비밀번호를 찾아 들어온 사람의 실패 기록은 지운다"""
    await auth_headers(EMAIL)
    for _ in range(9):
        await client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong-password"})
    ok = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert ok.status_code == 200, ok.text
    res = await client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong-password"})
    assert res.status_code == 401, res.text


async def test_register_is_limited_per_ip(client):
    codes = []
    for i in range(11):
        res = await client.post("/api/auth/register", json={"email": f"n{i}@example.com", "password": PASSWORD, "nickname": "닉네임"})
        codes.append(res.status_code)
    assert codes[:10] == [201] * 10
    assert codes[10] == 429


# ── 출처 ────────────────────────────────────────────────


@pytest.mark.parametrize("site", ["cross-site", "same-site"])
@pytest.mark.parametrize("path", ["/api/auth/refresh", "/api/auth/logout"])
async def test_cookie_routes_reject_other_sites(client, auth_headers, site, path):
    """형제 서브도메인은 SameSite로 막히지 않는다 ─ 브라우저가 알려 주는 출처로 거절한다"""
    await auth_headers(EMAIL)
    res = await client.post(path, headers={"Sec-Fetch-Site": site})
    assert res.status_code == 403, res.text
    # 토큰은 그대로 살아 있다
    assert (await client.post("/api/auth/refresh", headers={"Sec-Fetch-Site": "same-origin"})).status_code == 200


# ── 운영 ────────────────────────────────────────────────


async def test_health_checks_the_database(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


async def test_update_error_message_is_korean(client, auth_headers):
    headers = await auth_headers(EMAIL)
    good = (await create(client, headers)).json()
    res = await client.patch(f"/api/entries/{good['id']}", json={"status": None}, headers=headers)
    assert res.status_code == 422
    assert res.json()["detail"] == "상태는 비울 수 없습니다"
    res = await client.patch(f"/api/entries/{good['id']}", json={"playtime_minutes": None}, headers=headers)
    assert res.json()["detail"] == "플레이타임은 비울 수 없습니다"


async def test_login_removes_expired_tokens(client, auth_headers, session_factory):
    """만료 토큰이 쌓이지 않는다 ─ 폐기됐지만 아직 안 만료된 것은 재사용 감지에 필요해 남긴다"""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, select, update

    from app.models.user import RefreshToken

    await auth_headers(EMAIL)
    async with session_factory() as db:
        await db.execute(update(RefreshToken).values(expires_at=datetime.now(timezone.utc) - timedelta(days=1)))
        await db.commit()
    assert (await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})).status_code == 200
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(RefreshToken)) == 1

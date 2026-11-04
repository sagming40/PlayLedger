"""Steam이 이상하게 답할 때 ─ 비공식 API라 언제든 바뀐다. 등록은 성공하고 미러링은 키 없이 실패한다 (decisions/0008)"""

import httpx
import pytest
from sqlalchemy import func, select

from app.models.game import Game
from app.models.steam_app import SteamApp
from app.services.steam import SteamSyncError, fetch_app_details, sync_steam_apps

A = "a@example.com"
APPID = 367520
KEY = "secret-key-for-test"
MIRROR_NAME = "Hollow Knight"


async def seed_mirror(session_factory):
    async with session_factory() as db:
        db.add(SteamApp(appid=APPID, name=MIRROR_NAME))
        await db.commit()


def timeout_error(request):
    raise httpx.ConnectTimeout("느림", request=request)


GOOD = {"type": "game", "name": "할로우 나이트", "genres": [{"id": "1"}]}


@pytest.mark.parametrize(
    "respond",
    [
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(429),
        lambda r: httpx.Response(200, text="<html>점검 중</html>"),
        lambda r: httpx.Response(200, json=[]),
        lambda r: httpx.Response(200, json={}),
        lambda r: httpx.Response(200, json={str(APPID): None}),
        lambda r: httpx.Response(200, json={str(APPID): {"success": False}}),
        lambda r: httpx.Response(200, json={str(APPID): {"success": True}}),
        lambda r: httpx.Response(200, json={str(APPID): {"success": True, "data": []}}),
        lambda r: httpx.Response(200, json={str(APPID): {"success": True, "data": {**GOOD, "genres": None}}}),
        lambda r: httpx.Response(200, json={str(APPID): {"success": True, "data": {**GOOD, "genres": [{"x": 1}]}}}),
        timeout_error,
    ],
    ids=["500", "429", "html", "list", "empty", "null-entry", "no-success", "no-data", "list-data", "null-genres", "bad-genre", "timeout"],
)
async def test_steam_failure_still_registers_with_mirror_name(client, auth_headers, session_factory, fake_steam, respond):
    """커버 없이, 미러의 영어 이름으로 등록된다"""
    await seed_mirror(session_factory)
    fake_steam.override = respond
    res = await client.post("/api/entries", json={"steam_appid": APPID}, headers=await auth_headers(A))
    assert res.status_code == 201, res.text
    assert res.json()["game"]["title"] == MIRROR_NAME
    assert res.json()["game"]["cover_url"] is None


@pytest.mark.parametrize(
    "bad",
    ["http://cdn.example/a.jpg", "javascript:alert(1)", "https://cdn.example/\x00.jpg", "https://cdn.example/" + "x" * 600, 123, None],
)
async def test_bad_cover_is_dropped(client, auth_headers, session_factory, fake_steam, bad):
    """화면의 img src로 들어가는 값이다 ─ https가 아니면 쓰지 않는다"""
    await seed_mirror(session_factory)
    fake_steam.details[APPID] = {**GOOD, "header_image": bad}
    res = await client.post("/api/entries", json={"steam_appid": APPID}, headers=await auth_headers(A))
    assert res.status_code == 201, res.text
    assert res.json()["game"]["cover_url"] is None
    assert res.json()["game"]["title"] == "할로우 나이트"


@pytest.mark.parametrize("bad", ["a\x00b", "a\ud800b", "!!!", "x" * 300, 123, None])
async def test_bad_name_falls_back_to_mirror(client, auth_headers, session_factory, fake_steam, bad):
    await seed_mirror(session_factory)
    fake_steam.details[APPID] = {**GOOD, "name": bad}
    res = await client.post("/api/entries", json={"steam_appid": APPID}, headers=await auth_headers(A))
    assert res.status_code == 201, res.text
    assert res.json()["game"]["title"] == MIRROR_NAME


@pytest.mark.parametrize("bad", ["1\x00", "abc", "1" * 30])
async def test_bad_genre_id_is_ignored(client, auth_headers, session_factory, fake_steam, bad):
    await seed_mirror(session_factory)
    fake_steam.details[APPID] = {**GOOD, "genres": [{"id": bad}]}
    res = await client.post("/api/entries", json={"steam_appid": APPID}, headers=await auth_headers(A))
    assert res.status_code == 201, res.text
    assert res.json()["game"]["genres"] == []


async def test_non_game_is_rejected_and_nothing_saved(client, auth_headers, session_factory, fake_steam):
    await seed_mirror(session_factory)
    fake_steam.details[APPID] = {**GOOD, "type": "dlc"}
    res = await client.post("/api/entries", json={"steam_appid": APPID}, headers=await auth_headers(A))
    assert res.status_code == 422, res.text
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Game)) == 0


async def test_missing_cover_is_filled_by_the_next_person(client, auth_headers, session_factory, fake_steam):
    await seed_mirror(session_factory)
    fake_steam.override = lambda r: httpx.Response(500)
    await client.post("/api/entries", json={"steam_appid": APPID}, headers=await auth_headers(A))
    fake_steam.override = None
    fake_steam.details[APPID] = {**GOOD, "header_image": "https://cdn.example/a.jpg"}
    res = await client.post("/api/entries", json={"steam_appid": APPID}, headers=await auth_headers("b@example.com"))
    assert res.json()["game"]["cover_url"] == "https://cdn.example/a.jpg"
    # 제목은 먼저 등록된 그대로다
    assert res.json()["game"]["title"] == MIRROR_NAME


async def test_details_never_raise():
    """예외를 내보내지 않는다는 약속 자체를 지킨다"""

    def boom(request):
        raise httpx.ReadError("끊김", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(boom)) as http:
        assert await fetch_app_details(http, APPID) is None


# ─── 미러링 ─────────────────────────────────────────────


async def run_sync(session_factory, respond):
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http, session_factory() as db:
        return await sync_steam_apps(db, http, KEY)


def page(*apps, more=False, last=None):
    response: dict = {"apps": list(apps), "have_more_results": more}
    if last is not None:
        response["last_appid"] = last
    return httpx.Response(200, json={"response": response})


@pytest.mark.parametrize(
    "respond",
    [
        lambda r: httpx.Response(403),
        lambda r: httpx.Response(200, text="<html>"),
        lambda r: httpx.Response(200, json=[]),
        lambda r: httpx.Response(200, json={}),
        lambda r: httpx.Response(200, json={"response": []}),
        lambda r: httpx.Response(200, json={"response": {"apps": "많음"}}),
        lambda r: page({"appid": 1, "name": "a"}, more=True),
        lambda r: page({"appid": 1, "name": "a"}, more=True, last="abc"),
        timeout_error,
    ],
    ids=["403", "html", "list", "no-response", "list-response", "apps-not-list", "no-last", "bad-last", "timeout"],
)
async def test_sync_failures_are_sync_errors_without_the_key(session_factory, respond):
    with pytest.raises(SteamSyncError) as e:
        await run_sync(session_factory, respond)
    assert KEY not in str(e.value)


async def test_sync_stops_when_steam_repeats_the_same_page(session_factory):
    """같은 last_appid를 계속 주면 영원히 돈다 ─ 그 자리에서 멈춘다"""
    calls = []

    def respond(request):
        calls.append(request)
        assert len(calls) < 5, "멈추지 않고 계속 부른다"
        return page({"appid": 1, "name": "a"}, more=True, last=1)

    with pytest.raises(SteamSyncError):
        await run_sync(session_factory, respond)


async def test_sync_skips_broken_rows(session_factory):
    """행 하나가 이상해도 나머지 20만 행을 버리지 않는다"""
    received = await run_sync(
        session_factory,
        lambda r: page(
            {"appid": 1, "name": "정상"},
            {"appid": 2, "name": "NUL\x00제거"},
            {"appid": 3, "name": "   "},
            {"appid": 4},
            {"name": "번호 없음"},
            {"appid": "abc", "name": "문자 번호"},
            {"appid": 2**31, "name": "범위 밖"},
            {"appid": 5, "name": 123},
            "행이 아님",
        ),
    )
    assert received == 2
    async with session_factory() as db:
        assert sorted(await db.scalars(select(SteamApp.name))) == ["NUL제거", "정상"]


async def test_sync_sends_the_key_only_in_the_header(session_factory):
    seen = []

    def respond(request):
        seen.append(request)
        return page()

    await run_sync(session_factory, respond)
    assert seen[0].headers["x-webapi-key"] == KEY
    assert KEY not in str(seen[0].url)

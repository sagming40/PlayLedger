"""Steam 검색 등록 ─ 미러링 · 검색 · 등록 (ARCHITECTURE 5.3절, decisions/0008 · 0009)

진짜 Steam은 부르지 않는다. 가짜 응답은 conftest의 fake_steam이 정한다.
"""

import asyncio
from datetime import date

import httpx
import pytest
from sqlalchemy import func, select

from app.models.game import Game
from app.models.steam_app import SteamApp
from app.services.game import find_or_create_game
from app.services.steam import (
    SteamSyncError,
    parse_release_date,
    search_steam_apps,
    sync_steam_apps,
)

A = "a@example.com"
B = "b@example.com"
KEY = "secret-key-for-test"

HOLLOW = {
    "type": "game",
    "name": "할로우 나이트",
    "header_image": "https://cdn.example/367520/abc/header.jpg?t=1",
    # 1 액션 · 25 어드벤처는 고정 목록에 있고 23 인디는 없다
    "genres": [{"id": "1"}, {"id": "25"}, {"id": "23"}],
    "release_date": {"coming_soon": False, "date": "2017년 2월 24일"},
}


async def mirror(session_factory, *apps: tuple[int, str]) -> None:
    async with session_factory() as db:
        db.add_all(SteamApp(appid=appid, name=name) for appid, name in apps)
        await db.commit()


async def genre_ids(client, headers) -> dict[str, int]:
    res = await client.get("/api/genres", headers=headers)
    return {g["name"]: g["id"] for g in res.json()}


async def count_games(session_factory) -> int:
    async with session_factory() as db:
        return await db.scalar(select(func.count()).select_from(Game))


# ─── 검색 ───────────────────────────────────────────────


async def test_search_requires_login(client):
    res = await client.get("/api/steam/apps", params={"q": "hollow"})
    assert res.status_code == 401, res.json()


async def test_search_finds_part_of_title_and_typo(client, auth_headers, session_factory):
    headers = await auth_headers(A)
    await mirror(session_factory, (367520, "Hollow Knight"), (1086940, "Baldur's Gate 3"), (10, "Counter-Strike"))

    res = await client.get("/api/steam/apps", params={"q": "knight"}, headers=headers)
    assert res.json() == [{"appid": 367520, "name": "Hollow Knight"}], res.json()

    # 오타 · 기호 빠짐 ─ ILIKE로는 못 찾고 pg_trgm만 찾는다
    res = await client.get("/api/steam/apps", params={"q": "hollow knigt"}, headers=headers)
    assert [a["appid"] for a in res.json()] == [367520], res.json()
    res = await client.get("/api/steam/apps", params={"q": "baldurs gate"}, headers=headers)
    assert [a["appid"] for a in res.json()] == [1086940], res.json()


async def test_search_ranks_exact_then_prefix_then_similar(session_factory):
    """'Mt Peak'가 글자 수로는 더 비슷해도, 치는 말로 시작하는 제목이 먼저다"""
    await mirror(session_factory, (1, "Peak Performance Long Title"), (2, "Mt Peak"), (3, "PEAK"))
    async with session_factory() as db:
        rows = await search_steam_apps(db, "peak")
    assert [r.appid for r in rows] == [3, 1, 2], [r.name for r in rows]


async def test_search_treats_wildcards_as_letters(client, auth_headers, session_factory):
    """'%'를 치면 전부 걸리는 것이 아니라, 글자 %를 찾는다"""
    headers = await auth_headers(A)
    # "Area 0"은 0을 포함하지만 "0%"는 아니다 ─ 이스케이프가 없으면 %가 와일드카드가 되어 걸린다
    await mirror(session_factory, (1, "Area 0 Zone"), (2, "100% Orange Juice"))

    res = await client.get("/api/steam/apps", params={"q": "0%"}, headers=headers)
    assert [a["appid"] for a in res.json()] == [2], res.json()


async def test_search_rejects_short_and_blank_query(client, auth_headers, session_factory):
    headers = await auth_headers(A)
    await mirror(session_factory, (1, "Hollow Knight"))

    res = await client.get("/api/steam/apps", params={"q": "h"}, headers=headers)
    assert res.status_code == 422, res.json()
    res = await client.get("/api/steam/apps", params={"q": "   "}, headers=headers)
    assert res.status_code == 200 and res.json() == [], res.json()


async def test_search_on_empty_mirror_returns_nothing(client, auth_headers):
    headers = await auth_headers(A)
    res = await client.get("/api/steam/apps", params={"q": "hollow"}, headers=headers)
    assert res.status_code == 200 and res.json() == [], res.json()


# ─── 등록 ───────────────────────────────────────────────


async def test_register_fills_korean_name_cover_genres_release(client, auth_headers, session_factory, fake_steam):
    headers = await auth_headers(A)
    await mirror(session_factory, (367520, "Hollow Knight"))
    fake_steam.details[367520] = HOLLOW

    res = await client.post(
        "/api/entries",
        json={"steam_appid": 367520, "status": "PLAYING", "playtime_minutes": 90, "purchase_price": 16500},
        headers=headers,
    )
    assert res.status_code == 201, res.json()
    body = res.json()
    assert body["game"]["title"] == "할로우 나이트"
    assert body["game"]["steam_appid"] == 367520
    assert body["game"]["cover_url"] == HOLLOW["header_image"]
    # 인디(23)는 고정 목록에 없어 빠진다
    assert {g["name"] for g in body["game"]["genres"]} == {"액션", "어드벤처"}, body["game"]["genres"]
    # STEAM이면 M6 동기화가 입력한 플레이타임을 덮어쓴다
    assert body["source"] == "MANUAL"
    assert body["playtime_minutes"] == 90

    async with session_factory() as db:
        game = await db.scalar(select(Game).where(Game.steam_appid == 367520))
    assert game.released_at == date(2017, 2, 24)


async def test_unknown_appid_is_rejected_without_calling_steam(client, auth_headers, session_factory, fake_steam):
    """미러에 없는 번호로는 공유 테이블에 게임을 만들 수 없다"""
    headers = await auth_headers(A)

    res = await client.post("/api/entries", json={"steam_appid": 999}, headers=headers)
    assert res.status_code == 422, res.json()
    assert isinstance(res.json()["detail"], str)
    assert await count_games(session_factory) == 0
    assert fake_steam.calls == []


@pytest.mark.parametrize(
    "body", [{"title": "Celeste", "steam_appid": 1}, {"status": "BACKLOG"}]
)
async def test_title_and_appid_must_be_exactly_one(client, auth_headers, session_factory, body):
    headers = await auth_headers(A)
    await mirror(session_factory, (1, "Celeste"))

    res = await client.post("/api/entries", json=body, headers=headers)
    assert res.status_code == 422, res.json()
    assert await count_games(session_factory) == 0


async def test_steam_failure_still_registers_and_next_user_fills_cover(client, auth_headers, session_factory, fake_steam):
    """appdetails가 실패해도 등록은 성공한다. 빈 커버는 다음 사람이 채운다"""
    headers_a = await auth_headers(A)
    headers_b = await auth_headers(B, nickname="other")
    await mirror(session_factory, (367520, "Hollow Knight"))
    ids = await genre_ids(client, headers_a)

    # A ─ Steam 실패 (fake_steam.details가 비어 있어 500)
    res = await client.post(
        "/api/entries", json={"steam_appid": 367520, "genre_ids": [ids["RPG"]]}, headers=headers_a
    )
    assert res.status_code == 201, res.json()
    assert res.json()["game"]["title"] == "Hollow Knight"     # 미러의 영어 이름
    assert res.json()["game"]["cover_url"] is None
    assert [g["name"] for g in res.json()["game"]["genres"]] == ["RPG"]   # 사용자가 고른 값

    # B ─ Steam 복구
    fake_steam.details[367520] = HOLLOW
    res = await client.post("/api/entries", json={"steam_appid": 367520}, headers=headers_b)
    assert res.status_code == 201, res.json()
    game = res.json()["game"]
    assert game["cover_url"] == HOLLOW["header_image"]
    assert game["title"] == "Hollow Knight"                   # 먼저 등록한 제목 유지
    assert [g["name"] for g in game["genres"]] == ["RPG"]     # 0개일 때만 채운다
    assert await count_games(session_factory) == 1


async def test_user_genres_are_used_when_steam_has_no_fixed_genre(client, auth_headers, session_factory, fake_steam):
    headers = await auth_headers(A)
    await mirror(session_factory, (7, "Indie Only"))
    fake_steam.details[7] = {**HOLLOW, "name": "인디뿐", "genres": [{"id": "23"}, {"id": "70"}]}
    ids = await genre_ids(client, headers)

    res = await client.post("/api/entries", json={"steam_appid": 7, "genre_ids": [ids["전략"]]}, headers=headers)
    assert res.status_code == 201, res.json()
    assert [g["name"] for g in res.json()["game"]["genres"]] == ["전략"]


async def test_non_game_type_is_rejected(client, auth_headers, session_factory, fake_steam):
    headers = await auth_headers(A)
    await mirror(session_factory, (598190, "Hollow Knight - Official Soundtrack"))
    fake_steam.details[598190] = {**HOLLOW, "type": "music"}

    res = await client.post("/api/entries", json={"steam_appid": 598190}, headers=headers)
    assert res.status_code == 422, res.json()
    assert await count_games(session_factory) == 0


async def test_duplicate_is_rejected_without_calling_steam_again(client, auth_headers, session_factory, fake_steam):
    """커버가 빈 게임이라도 이미 내 것이면 Steam을 부르지 않는다 (fake_steam이 비어 첫 등록은 커버 없음)"""
    headers = await auth_headers(A)
    await mirror(session_factory, (367520, "Hollow Knight"))

    assert (await client.post("/api/entries", json={"steam_appid": 367520}, headers=headers)).status_code == 201
    calls = len(fake_steam.calls)

    res = await client.post("/api/entries", json={"steam_appid": 367520}, headers=headers)
    assert res.status_code == 409, res.json()
    assert len(fake_steam.calls) == calls


async def test_unusable_name_is_422_not_500(client, auth_headers, session_factory):
    """Steam에는 414자짜리 이름과 기호뿐인 이름이 실제로 있다"""
    headers = await auth_headers(A)
    # 3번은 정규화하면 짧아지지만 원본이 games.title(200자)을 넘는다
    await mirror(session_factory, (1, "가" * 300), (2, "!!!"), (3, "a b " * 80))

    for appid in (1, 2, 3):
        res = await client.post("/api/entries", json={"steam_appid": appid}, headers=headers)
        assert res.status_code == 422, res.json()
    assert await count_games(session_factory) == 0


async def test_long_korean_name_falls_back_to_mirror_name(client, auth_headers, session_factory, fake_steam):
    headers = await auth_headers(A)
    await mirror(session_factory, (5, "Short Name"))
    fake_steam.details[5] = {**HOLLOW, "name": "가" * 300}

    res = await client.post("/api/entries", json={"steam_appid": 5}, headers=headers)
    assert res.status_code == 201, res.json()
    assert res.json()["game"]["title"] == "Short Name"


async def test_manual_and_steam_games_stay_separate(client, auth_headers, session_factory, fake_steam):
    """같은 제목이어도 합치지 않는다 (decisions/0009). 한 사용자가 양쪽을 다 가질 수 있다"""
    headers = await auth_headers(A)
    await mirror(session_factory, (367520, "Hollow Knight"))
    fake_steam.details[367520] = {**HOLLOW, "name": "Hollow Knight"}

    manual = await client.post("/api/entries", json={"title": "Hollow Knight"}, headers=headers)
    steam = await client.post("/api/entries", json={"steam_appid": 367520}, headers=headers)
    assert manual.status_code == steam.status_code == 201, (manual.json(), steam.json())
    assert manual.json()["game"]["id"] != steam.json()["game"]["id"]
    assert manual.json()["game"]["steam_appid"] is None
    assert await count_games(session_factory) == 2


async def test_concurrent_create_of_same_appid_makes_one_row(session_factory):
    """같은 appid를 동시에 만들면 늦은 쪽이 재조회로 먼저 만든 행을 받고, 빈 커버도 채운다"""
    a = session_factory()
    b = session_factory()
    await a.execute(select(1))
    await b.execute(select(1))
    try:
        game_a = await find_or_create_game(a, "할로우 나이트", 367520)

        b_task = asyncio.create_task(
            find_or_create_game(b, "할로우 나이트", 367520, cover_url="https://cdn.example/c.jpg")
        )
        await asyncio.sleep(0.5)
        assert not b_task.done(), "B가 대기하지 않았다 ─ 충돌 상황이 만들어지지 않았다"

        await a.commit()
        game_b = await b_task
        await b.commit()

        assert game_a.id == game_b.id, (game_a.id, game_b.id)
        assert await count_games(session_factory) == 1
        async with session_factory() as check:
            row = await check.scalar(select(Game).where(Game.steam_appid == 367520))
        assert row.cover_url == "https://cdn.example/c.jpg"
    finally:
        await a.close()
        await b.close()


# ─── 날짜 ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "release, expected",
    [
        ({"coming_soon": False, "date": "2017년 2월 24일"}, date(2017, 2, 24)),
        ({"coming_soon": True, "date": "2027년 1월 1일"}, None),    # 출시 전 날짜는 믿지 않는다
        ({"coming_soon": False, "date": "Q1 2027"}, None),
        ({"coming_soon": False, "date": "2027년"}, None),
        ({"coming_soon": False, "date": "2026년 2월 31일"}, None),   # 없는 날짜
        ({"coming_soon": False, "date": ""}, None),
        (None, None),
    ],
)
def test_parse_release_date(release, expected):
    assert parse_release_date(release) == expected


# ─── 미러링 ─────────────────────────────────────────────


def app_list_handler(pages: list[dict], seen: list[httpx.Request]):
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"response": pages[len(seen) - 1]})

    return handle


async def test_sync_is_idempotent_and_skips_blank_names(session_factory):
    pages = [
        {"apps": [{"appid": 1, "name": "One"}, {"appid": 2, "name": "  "}], "have_more_results": True, "last_appid": 2},
        {"apps": [{"appid": 3, "name": "Three"}]},
    ]
    seen: list[httpx.Request] = []
    async with session_factory() as db, httpx.AsyncClient(
        transport=httpx.MockTransport(app_list_handler(pages * 2, seen))
    ) as client:
        assert await sync_steam_apps(db, client, KEY) == 2
        assert await sync_steam_apps(db, client, KEY) == 2
        names = (await db.scalars(select(SteamApp.name).order_by(SteamApp.appid))).all()

    assert list(names) == ["One", "Three"]
    assert seen[1].url.params["last_appid"] == "2"       # 다음 페이지를 이어 받는다
    # 키는 헤더로만 간다 ─ URL에 있으면 로그와 예외에 찍힌다
    assert all(r.headers["x-webapi-key"] == KEY and KEY not in str(r.url) for r in seen)


async def test_sync_updates_changed_name(session_factory):
    await mirror(session_factory, (1, "Old Name"))
    pages = [{"apps": [{"appid": 1, "name": "New Name"}]}]
    async with session_factory() as db, httpx.AsyncClient(
        transport=httpx.MockTransport(app_list_handler(pages, []))
    ) as client:
        await sync_steam_apps(db, client, KEY)
        assert await db.scalar(select(SteamApp.name).where(SteamApp.appid == 1)) == "New Name"


async def test_sync_without_key_stops(session_factory):
    async with session_factory() as db, httpx.AsyncClient() as client:
        with pytest.raises(SteamSyncError):
            await sync_steam_apps(db, client, "")


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(403),
        lambda request: (_ for _ in ()).throw(httpx.ConnectTimeout("timeout", request=request)),
    ],
)
async def test_sync_error_never_contains_key(session_factory, handler):
    async with session_factory() as db, httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(SteamSyncError) as e:
            await sync_steam_apps(db, client, KEY)
    assert KEY not in str(e.value)
    assert e.value.__cause__ is None

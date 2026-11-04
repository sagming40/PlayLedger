"""직접 등록한 게임은 그 사람의 것이다 (decisions/0011, DATA_MODEL 2.4절)

고치기 전에 먼저 실패하는 것을 확인한 테스트들이다.
공개 가입이 열리면 A가 적은 제목과 장르가 B의 화면과 통계에 나타나면 안 된다.
"""

import asyncio

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models.game import Game, game_genres
from app.models.steam_app import SteamApp
from app.routers import entries as entries_router
from app.services.game import find_or_create_game

A = "a@example.com"
B = "b@example.com"
HOLLOW = 367520

# 잠금을 기다리는 게임 삭제가 있는지 DB에게 직접 묻는다
WAITING_GAME_DELETES = text(
    "SELECT count(*) FROM pg_stat_activity "
    "WHERE wait_event_type = 'Lock' AND query ILIKE 'DELETE FROM games%'"
)


async def genre_ids(client, headers) -> dict[str, int]:
    res = await client.get("/api/genres", headers=headers)
    return {g["name"]: g["id"] for g in res.json()}


async def create(client, headers, title="내가 만든 게임", **fields):
    return await client.post("/api/entries", json={"title": title, **fields}, headers=headers)


async def count_games(session_factory) -> int:
    async with session_factory() as db:
        return await db.scalar(select(func.count()).select_from(Game))


# ─── 분리 ───────────────────────────────────────────────


async def test_same_title_makes_separate_games(client, auth_headers):
    """같은 제목이어도 게임 행이 따로다 ─ 먼저 쓴 사람의 표기가 남에게 보이지 않는다"""
    a = await auth_headers(A)
    b = await auth_headers(B)
    first = (await create(client, a, "Hollow Knight")).json()
    second = (await create(client, b, "  hollow KNIGHT ")).json()
    assert first["game"]["id"] != second["game"]["id"]
    assert first["game"]["title"] == "Hollow Knight"
    assert second["game"]["title"] == "hollow KNIGHT"


async def test_genres_do_not_cross_users(client, auth_headers):
    a = await auth_headers(A)
    b = await auth_headers(B)
    ids = await genre_ids(client, a)
    await create(client, a, "같은 제목", genre_ids=[ids["액션"]])
    second = (await create(client, b, "같은 제목", genre_ids=[ids["RPG"]])).json()
    assert [g["name"] for g in second["game"]["genres"]] == ["RPG"]


async def test_same_user_same_title_is_still_409(client, auth_headers):
    a = await auth_headers(A)
    assert (await create(client, a, "Celeste")).status_code == 201
    res = await create(client, a, "CELESTE!")
    assert res.status_code == 409, res.text
    assert res.json()["detail"] == "이미 등록된 게임입니다"


async def test_concurrent_same_title_leaves_one(client, auth_headers, session_factory):
    """동시 등록 ─ 하나는 201, 하나는 409. 500이 나거나 행이 둘이면 안 된다"""
    a = await auth_headers(A)
    responses = await asyncio.gather(create(client, a, "Celeste"), create(client, a, "celeste"))
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert await count_games(session_factory) == 1


async def test_concurrent_two_users_same_title(client, auth_headers, session_factory):
    a = await auth_headers(A)
    b = await auth_headers(B)
    responses = await asyncio.gather(create(client, a, "Celeste"), create(client, b, "Celeste"))
    assert [r.status_code for r in responses] == [201, 201]
    assert await count_games(session_factory) == 2


# ─── 장르 수정 ──────────────────────────────────────────


async def test_owner_can_replace_manual_genres(client, auth_headers):
    a = await auth_headers(A)
    ids = await genre_ids(client, a)
    entry = (await create(client, a, genre_ids=[ids["액션"], ids["RPG"]])).json()

    res = await client.patch(f"/api/entries/{entry['id']}", json={"genre_ids": [ids["전략"]]}, headers=a)
    assert res.status_code == 200, res.text
    assert [g["name"] for g in res.json()["game"]["genres"]] == ["전략"]

    res = await client.patch(f"/api/entries/{entry['id']}", json={"genre_ids": []}, headers=a)
    assert res.json()["game"]["genres"] == []


async def test_steam_genres_stay_fixed(client, auth_headers, session_factory, fake_steam):
    """Steam 게임은 여럿이 같이 보는 행이라 비어 있을 때만 채운다"""
    a = await auth_headers(A)
    ids = await genre_ids(client, a)
    async with session_factory() as db:
        db.add(SteamApp(appid=HOLLOW, name="Hollow Knight"))
        await db.commit()
    entry = (await client.post("/api/entries", json={"steam_appid": HOLLOW, "genre_ids": [ids["액션"]]}, headers=a)).json()

    res = await client.patch(f"/api/entries/{entry['id']}", json={"genre_ids": [ids["RPG"]]}, headers=a)
    assert [g["name"] for g in res.json()["game"]["genres"]] == ["액션"]
    res = await client.patch(f"/api/entries/{entry['id']}", json={"genre_ids": []}, headers=a)
    assert [g["name"] for g in res.json()["game"]["genres"]] == ["액션"]


# ─── 삭제 ───────────────────────────────────────────────


async def test_deleting_entry_removes_my_manual_game(client, auth_headers, session_factory):
    """기록을 지웠는데 내가 적은 제목과 장르가 DB에 남으면 안 된다"""
    a = await auth_headers(A)
    ids = await genre_ids(client, a)
    entry = (await create(client, a, genre_ids=[ids["액션"]])).json()

    assert (await client.delete(f"/api/entries/{entry['id']}", headers=a)).status_code == 204

    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Game)) == 0
        assert await db.scalar(select(func.count()).select_from(game_genres)) == 0

    # 다시 등록하면 처음부터 ─ 지난 장르가 따라오지 않는다
    again = (await create(client, a)).json()
    assert again["game"]["genres"] == []


async def test_deleting_entry_keeps_steam_game(client, auth_headers, session_factory):
    a = await auth_headers(A)
    async with session_factory() as db:
        db.add(SteamApp(appid=HOLLOW, name="Hollow Knight"))
        await db.commit()
    entry = (await client.post("/api/entries", json={"steam_appid": HOLLOW}, headers=a)).json()
    assert (await client.delete(f"/api/entries/{entry['id']}", headers=a)).status_code == 204
    assert await count_games(session_factory) == 1


async def test_delete_waits_while_register_holds_the_game(client, auth_headers, session_factory, monkeypatch):
    """두 탭 ─ 등록이 내 게임을 찾은 직후 삭제가 들어오면, 삭제는 등록이 끝날 때까지 기다린다

    요청 순서를 우연에 맡기지 않으려고 찾은 직후에 삭제를 끼워 넣는다.
    FOR UPDATE를 지우면 삭제가 먼저 끝나 pytest.fail에 걸린다 ─ 그대로 두면 없는 번호로 기록을 넣다가 FK 위반(500)이 된다
    """
    a = await auth_headers(A)
    entry = (await create(client, a)).json()

    real_find = entries_router.find_or_create_game
    remove = None

    async def find_then_delete(*args, **kwargs):
        nonlocal remove
        game = await real_find(*args, **kwargs)
        remove = asyncio.create_task(client.delete(f"/api/entries/{entry['id']}", headers=a))
        async with session_factory() as watcher:
            for _ in range(150):
                if remove.done():
                    pytest.fail("삭제가 기다리지 않고 끝났다 ─ 게임 행이 잠기지 않았다")
                if await watcher.scalar(WAITING_GAME_DELETES):
                    break
                # pg_stat_activity는 트랜잭션 안에서 값이 고정된다 ─ 끝내야 새 값을 본다
                await watcher.rollback()
                await asyncio.sleep(0.1)
            else:
                pytest.fail("삭제가 15초 안에 잠금 대기에 들어가지 않았다")
        return game

    monkeypatch.setattr(entries_router, "find_or_create_game", find_then_delete)
    created = await create(client, a)
    removed = await remove

    # 등록이 본 시점에는 아직 기록이 있다 ─ 이미 등록된 게임
    assert created.status_code == 409, created.text
    assert removed.status_code == 204, removed.text
    assert await count_games(session_factory) == 0


async def test_register_after_delete_creates_a_new_game(client, auth_headers, session_factory):
    """반대 순서 ─ 삭제가 끝난 뒤 찾으면 없으니 새로 만든다"""
    a = await auth_headers(A)
    entry = (await create(client, a)).json()
    assert (await client.delete(f"/api/entries/{entry['id']}", headers=a)).status_code == 204
    again = await create(client, a)
    assert again.status_code == 201, again.text
    assert again.json()["game"]["id"] != entry["game"]["id"]
    assert await count_games(session_factory) == 1


# ─── 규칙 ───────────────────────────────────────────────


async def test_manual_game_without_owner_is_rejected_by_db(session_factory):
    async with session_factory() as db:
        db.add(Game(title="주인 없음", title_norm="주인없음"))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_steam_game_with_owner_is_rejected_by_db(client, auth_headers, session_factory):
    await auth_headers(A)
    async with session_factory() as db:
        from app.models.user import User

        user_id = await db.scalar(select(User.id))
        db.add(Game(title="주인 있음", title_norm="주인있음", steam_appid=1, owner_user_id=user_id))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_service_refuses_manual_game_without_owner(session_factory):
    """입구에서 먼저 막는다 ─ 빠뜨리면 DB 오류가 아니라 바로 알 수 있는 오류로"""
    async with session_factory() as db:
        with pytest.raises(ValueError):
            await find_or_create_game(db, "주인 없음")
        with pytest.raises(ValueError):
            await find_or_create_game(db, "둘 다", 1, owner_user_id=1)


async def test_entries_per_user_are_capped(client, auth_headers, monkeypatch):
    """공개 가입이면 한 사람이 표를 끝없이 키울 수 있다 ─ 남은 건드리지 않는다"""
    monkeypatch.setattr(entries_router, "MAX_ENTRIES_PER_USER", 1)
    a = await auth_headers(A)
    b = await auth_headers(B)
    assert (await create(client, a, "첫 번째")).status_code == 201
    res = await create(client, a, "두 번째")
    assert res.status_code == 409, res.text
    assert "최대" in res.json()["detail"]
    assert (await create(client, b, "첫 번째")).status_code == 201

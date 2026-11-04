"""계정 삭제 ─ 그 사람의 흔적은 전부 지우고 남의 것은 건드리지 않는다 (decisions/0011, PLAN M4.5)

고치기 전에 먼저 실패하는 것을 확인한 테스트들이다.
"""

import asyncio

from sqlalchemy import func, select, text

from app.models.entry import Entry
from app.models.game import Game
from app.models.steam_app import SteamApp
from app.models.user import RefreshToken, User

A = "a@example.com"
B = "b@example.com"
PASSWORD = "testpass123"
HOLLOW = 367520

WAITING_ACCOUNT_DELETE = text(
    "SELECT count(*) FROM pg_stat_activity "
    "WHERE wait_event_type = 'Lock' AND query ILIKE '%FROM users%FOR UPDATE%'"
)


async def remove_account(client, headers, password=PASSWORD):
    return await client.request("DELETE", "/api/auth/me", json={"password": password}, headers=headers)


async def count(session_factory, model) -> int:
    async with session_factory() as db:
        return await db.scalar(select(func.count()).select_from(model))


async def test_requires_login(client):
    res = await client.request("DELETE", "/api/auth/me", json={"password": PASSWORD})
    assert res.status_code == 401, res.text


async def test_password_is_required(client, auth_headers):
    a = await auth_headers(A)
    res = await client.request("DELETE", "/api/auth/me", json={}, headers=a)
    assert res.status_code == 422, res.text


async def test_wrong_password_keeps_everything(client, auth_headers, session_factory):
    """403이다 ─ 401이면 화면이 토큰 만료로 알고 재발급을 시도한다"""
    a = await auth_headers(A)
    res = await remove_account(client, a, "wrong-password")
    assert res.status_code == 403, res.text
    assert res.json()["detail"] == "비밀번호가 올바르지 않습니다"
    assert (await client.get("/api/auth/me", headers=a)).status_code == 200
    assert await count(session_factory, User) == 1


async def test_wrong_password_is_limited(client, auth_headers):
    """탈취된 토큰으로 비밀번호를 대입하는 통로가 되면 안 된다"""
    a = await auth_headers(A)
    for _ in range(10):
        assert (await remove_account(client, a, "wrong-password")).status_code == 403
    res = await remove_account(client, a, "wrong-password")
    assert res.status_code == 429, res.text
    assert res.headers["retry-after"]


async def test_delete_removes_my_data_and_keeps_others(client, auth_headers, session_factory):
    a = await auth_headers(A)
    b = await auth_headers(B)
    async with session_factory() as db:
        db.add(SteamApp(appid=HOLLOW, name="Hollow Knight"))
        await db.commit()
    for headers in (a, b):
        await client.post("/api/entries", json={"title": "같은 제목", "genre_ids": [1]}, headers=headers)
        await client.post("/api/entries", json={"steam_appid": HOLLOW}, headers=headers)

    res = await remove_account(client, a)
    assert res.status_code == 204, res.text

    async with session_factory() as db:
        assert list(await db.scalars(select(User.email))) == [B]
        assert await db.scalar(select(func.count()).select_from(Entry)) == 2
        # B의 직접 등록 게임 + 공유 Steam 게임
        assert await db.scalar(select(func.count()).select_from(Game)) == 2
        assert await db.scalar(select(func.count()).select_from(Game).where(Game.steam_appid == HOLLOW)) == 1

    # B는 그대로 쓴다
    listed = await client.get("/api/entries", headers=b)
    assert listed.json()["total"] == 2


async def test_sessions_die_with_the_account(client, auth_headers, session_factory):
    a = await auth_headers(A)
    res = await remove_account(client, a)
    assert res.status_code == 204, res.text
    # 쿠키를 지우라고 알린다
    assert "pl_refresh_token" in res.headers["set-cookie"]
    assert await count(session_factory, RefreshToken) == 0
    # access 토큰은 만료 전이지만 주인이 없다
    assert (await client.get("/api/auth/me", headers=a)).status_code == 401
    assert (await client.post("/api/auth/refresh")).status_code == 401


async def test_same_email_can_register_again(client, auth_headers):
    a = await auth_headers(A)
    assert (await remove_account(client, a)).status_code == 204
    res = await client.post("/api/auth/register", json={"email": A, "password": PASSWORD, "nickname": "다시"})
    assert res.status_code == 201, res.text


async def test_delete_waits_for_a_registering_tab(client, auth_headers, session_factory):
    """다른 탭의 등록이 끝나기 전에 지우면 그 기록을 못 보고 지나칠 수 있다 ─ 끝나기를 기다렸다가 함께 지운다"""
    a = await auth_headers(A)
    async with session_factory() as db:
        user_id = await db.scalar(select(User.id).where(User.email == A))

    tab = session_factory()
    try:
        # 등록 도중의 다른 탭 ─ 게임과 기록을 넣었고 아직 commit 전이다
        game = Game(title="도중", title_norm="도중", owner_user_id=user_id)
        tab.add(game)
        await tab.flush()
        tab.add(Entry(user_id=user_id, game_id=game.id, status="BACKLOG", source="MANUAL"))
        await tab.flush()

        removing = asyncio.create_task(remove_account(client, a))
        async with session_factory() as watcher:
            for _ in range(150):
                assert not removing.done(), removing.result().text
                if await watcher.scalar(WAITING_ACCOUNT_DELETE):
                    break
                await watcher.rollback()
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("계정 삭제가 15초 안에 잠금 대기에 들어가지 않았다")
        await tab.commit()
    finally:
        await tab.close()

    res = await removing
    assert res.status_code == 204, res.text
    assert await count(session_factory, Entry) == 0
    assert await count(session_factory, Game) == 0

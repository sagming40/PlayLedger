"""Steam 라이브러리 동기화 ─ 병합 규칙 · 직접 입력 지키기 · 동시 실행 · 상한 (ARCHITECTURE 5.1절)

진짜 Steam은 부르지 않는다. 보유 게임 목록은 conftest의 fake_steam.owned가 정한다.
완료 기준 두 번째(직접 입력한 게임의 구매가 · 평점 · 한줄평이 그대로)가 이 파일의 중심이다
"""

import asyncio
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import func, select, update

from app.core.config import settings
from app.models.entry import Entry
from app.models.game import Game
from app.models.steam_app import SteamApp
from app.models.user import User
from app.services import steam_sync
from app.services.steam import OwnedGame
from app.services.steam_sync import SyncNotLinked, SyncTooSoon, merge_owned_games

A = "a@example.com"
B = "b@example.com"
STEAM_A = "76561197960287930"
STEAM_B = "76561198000000001"
SYNC = "/api/steam/sync"

HOLLOW = {"appid": 367520, "name": "Hollow Knight", "playtime_forever": 1234}
CIV = {"appid": 8930, "name": "Sid Meier's Civilization V", "playtime_forever": 37768}
DOTA = {"appid": 570, "name": "Dota 2", "playtime_forever": 0}


@pytest.fixture(autouse=True)
def steam_key(monkeypatch):
    """키 없는 CI에서도 동기화가 Steam(가짜)까지 가게 한다"""
    monkeypatch.setattr(settings, "steam_api_key", "secret-key-for-test")


async def linked_user(auth_headers, session_factory, email=A, steam_id=STEAM_A) -> dict[str, str]:
    """가입 · 로그인하고 Steam을 연결해 둔다(OpenID는 test_steam_link.py가 본다)"""
    headers = await auth_headers(email)
    async with session_factory() as db:
        await db.execute(update(User).where(User.email == email).values(steam_id=steam_id))
        await db.commit()
    return headers


async def allow_next_sync(session_factory) -> None:
    """60초 간격을 기다리는 대신 마지막 동기화 시각을 뒤로 민다"""
    async with session_factory() as db:
        await db.execute(update(User).values(steam_synced_at=User.steam_synced_at - timedelta(minutes=5)))
        await db.commit()


async def my_entries(session_factory, user_id=1) -> dict[int, Entry]:
    """appid → 기록"""
    async with session_factory() as db:
        rows = await db.execute(
            select(Game.steam_appid, Entry).join(Game, Game.id == Entry.game_id).where(Entry.user_id == user_id)
        )
        return {appid: entry for appid, entry in rows.all()}


async def sync(client, headers, expect=200) -> dict:
    res = await client.post(SYNC, headers=headers)
    assert res.status_code == expect, res.text
    return res.json()


# ─── 병합 규칙 ─────────────────────────────────────────────


async def test_first_sync_adds_steam_entries(client, auth_headers, session_factory, fake_steam):
    headers = await linked_user(auth_headers, session_factory)
    fake_steam.owned = [HOLLOW, CIV, DOTA]

    body = await sync(client, headers)

    assert {k: v for k, v in body.items() if k != "synced_at"} == {
        "added": 3, "updated": 0, "unchanged": 0, "skipped_manual": 0,
        "skipped_limit": 0, "skipped_no_title": 0, "same_title_manual": 0,
    }
    assert body["synced_at"].endswith("Z") or "+00:00" in body["synced_at"]
    entries = await my_entries(session_factory)
    assert entries[367520].status == "PLAYING"
    assert entries[570].status == "BACKLOG"          # 0분이면 미시작
    assert entries[8930].playtime_minutes == 37768
    assert all(e.source == "STEAM" for e in entries.values())
    # Steam API는 구매일 · 구매가를 주지 않는다 (decisions/0019)
    assert all(e.purchased_at is None and e.purchase_price is None for e in entries.values())
    async with session_factory() as db:
        game = await db.scalar(select(Game).where(Game.steam_appid == 367520))
        assert game.title == "Hollow Knight"
        assert game.owner_user_id is None             # Steam 게임은 공용
        assert game.cover_url is None                 # 상세는 나중에 (decisions/0016)
        assert (await db.get(User, 1)).steam_synced_at is not None


async def test_manual_entry_is_never_touched(client, auth_headers, session_factory, fake_steam):
    """검색으로 등록한 Steam 게임(MANUAL)의 구매가 · 평점 · 한줄평 · 상태 · 플레이타임이 그대로 남는다 ─ 이 단계의 본질"""
    headers = await linked_user(auth_headers, session_factory)
    async with session_factory() as db:
        db.add(SteamApp(appid=367520, name="Hollow Knight"))
        await db.commit()
    res = await client.post("/api/entries", headers=headers, json={
        "steam_appid": 367520, "status": "CLEARED", "purchased_at": "2023-05-01",
        "purchase_price": 16500, "playtime_minutes": 40, "rating": 5, "review": "명작",
    })
    assert res.status_code == 201, res.text
    before = (await my_entries(session_factory))[367520]
    fake_steam.owned = [HOLLOW]

    body = await sync(client, headers)
    await allow_next_sync(session_factory)
    again = await sync(client, headers)

    assert body["skipped_manual"] == 1 and body["added"] == 0
    assert again["skipped_manual"] == 1
    after = (await my_entries(session_factory))[367520]
    for field in ("status", "purchased_at", "purchase_price", "playtime_minutes", "rating", "review", "source", "updated_at"):
        assert getattr(after, field) == getattr(before, field), field
    assert after.purchased_at == date(2023, 5, 1)


async def test_second_sync_updates_only_playtime(client, auth_headers, session_factory, fake_steam):
    headers = await linked_user(auth_headers, session_factory)
    fake_steam.owned = [HOLLOW, CIV, DOTA]
    await sync(client, headers)
    # 사용자가 Steam 기록의 상태 · 평점을 바꿔 둔다 ─ 동기화가 되돌리면 안 된다
    async with session_factory() as db:
        await db.execute(update(Entry).values(status="ON_HOLD", rating=3, purchase_price=1000))
        await db.commit()
    await allow_next_sync(session_factory)
    fake_steam.owned = [
        {**HOLLOW, "playtime_forever": 2000},   # 늘어남
        {**CIV, "playtime_forever": 30000},     # 줄어듦 ─ Steam 값으로 맞춘다
        DOTA,                                   # 그대로
    ]

    body = await sync(client, headers)

    assert (body["added"], body["updated"], body["unchanged"]) == (0, 2, 1)
    entries = await my_entries(session_factory)
    assert entries[367520].playtime_minutes == 2000
    assert entries[8930].playtime_minutes == 30000
    assert all(e.status == "ON_HOLD" and e.rating == 3 and e.purchase_price == 1000 for e in entries.values())


async def test_game_gone_from_steam_is_kept(client, auth_headers, session_factory, fake_steam):
    headers = await linked_user(auth_headers, session_factory)
    fake_steam.owned = [HOLLOW, CIV]
    await sync(client, headers)
    await allow_next_sync(session_factory)
    fake_steam.owned = [HOLLOW]

    await sync(client, headers)
    assert set(await my_entries(session_factory)) == {367520, 8930}


async def test_zero_games(client, auth_headers, session_factory, fake_steam):
    headers = await linked_user(auth_headers, session_factory)
    body = await sync(client, headers)
    assert body["added"] == 0
    assert await my_entries(session_factory) == {}


async def test_reuses_game_made_by_someone_else(client, auth_headers, session_factory, fake_steam):
    """다른 사람이 먼저 만든 Steam 게임 행을 같이 쓴다 ─ 제목도 먼저 만든 쪽 것이 남는다"""
    headers = await linked_user(auth_headers, session_factory)
    async with session_factory() as db:
        db.add(Game(title="할로우 나이트", title_norm="할로우나이트", steam_appid=367520))
        await db.commit()
    fake_steam.owned = [HOLLOW]

    await sync(client, headers)
    async with session_factory() as db:
        games = (await db.scalars(select(Game).where(Game.steam_appid == 367520))).all()
    assert [g.title for g in games] == ["할로우 나이트"]


async def test_title_falls_back_to_mirror_or_skips(client, auth_headers, session_factory, fake_steam):
    headers = await linked_user(auth_headers, session_factory)
    async with session_factory() as db:
        db.add(SteamApp(appid=10, name="Counter-Strike"))
        await db.commit()
    fake_steam.owned = [
        {"appid": 10, "name": "!!!", "playtime_forever": 1},   # Steam 이름은 못 쓰고 미러 이름은 된다
        {"appid": 20, "playtime_forever": 1},                  # 이름도 미러도 없다
    ]

    body = await sync(client, headers)
    assert (body["added"], body["skipped_no_title"]) == (1, 1)
    async with session_factory() as db:
        assert await db.scalar(select(Game.title).where(Game.steam_appid == 10)) == "Counter-Strike"
        assert await db.scalar(select(func.count()).select_from(Game).where(Game.steam_appid == 20)) == 0


async def test_same_title_manual_game_stays_separate(client, auth_headers, session_factory, fake_steam):
    """직접 등록한 "Hollow Knight"와 Steam의 Hollow Knight는 별개 행이다 (decisions/0009). 수만 알린다"""
    headers = await linked_user(auth_headers, session_factory)
    res = await client.post("/api/entries", headers=headers, json={"title": "hollow knight", "status": "BACKLOG"})
    assert res.status_code == 201
    fake_steam.owned = [HOLLOW, DOTA]

    body = await sync(client, headers)
    assert (body["added"], body["same_title_manual"]) == (2, 1)
    async with session_factory() as db:
        count = await db.scalar(select(func.count()).select_from(Entry).where(Entry.user_id == 1))
    assert count == 3


async def test_entry_limit(client, auth_headers, session_factory, fake_steam, monkeypatch):
    """상한까지만 넣고 나머지는 건너뛴 수로 알린다. 넣지 않을 게임은 공용 games에도 만들지 않는다"""
    headers = await linked_user(auth_headers, session_factory)
    monkeypatch.setattr(steam_sync, "MAX_ENTRIES_PER_USER", 2)
    res = await client.post("/api/entries", headers=headers, json={"title": "직접 등록", "status": "BACKLOG"})
    assert res.status_code == 201
    fake_steam.owned = [HOLLOW, CIV, DOTA]

    body = await sync(client, headers)
    assert (body["added"], body["skipped_limit"]) == (1, 2)
    # appid 순으로 고정 ─ 가장 작은 570(Dota 2)이 들어간다
    assert set(await my_entries(session_factory)) == {None, 570}
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Game).where(Game.steam_appid.is_not(None))) == 1


async def test_limit_does_not_block_updates(client, auth_headers, session_factory, fake_steam, monkeypatch):
    headers = await linked_user(auth_headers, session_factory)
    fake_steam.owned = [HOLLOW]
    await sync(client, headers)
    monkeypatch.setattr(steam_sync, "MAX_ENTRIES_PER_USER", 1)
    await allow_next_sync(session_factory)
    fake_steam.owned = [{**HOLLOW, "playtime_forever": 9999}, CIV]

    body = await sync(client, headers)
    assert (body["updated"], body["added"], body["skipped_limit"]) == (1, 0, 1)


# ─── 오류 ─────────────────────────────────────────────────


async def test_not_linked(client, auth_headers, fake_steam):
    headers = await auth_headers(A)
    res = await client.post(SYNC, headers=headers)
    assert res.status_code == 409
    assert fake_steam.owned_calls == 0


async def test_private_profile(client, auth_headers, session_factory, fake_steam):
    headers = await linked_user(auth_headers, session_factory)
    fake_steam.owned_answer = lambda r: httpx.Response(200, json={"response": {}})

    res = await client.post(SYNC, headers=headers)
    assert res.status_code == 409
    assert "공개" in res.json()["detail"]
    async with session_factory() as db:
        assert (await db.get(User, 1)).steam_synced_at is None   # 실패는 간격에 넣지 않는다


def steam_timeout(request):
    raise httpx.ReadTimeout("느림", request=request)


@pytest.mark.parametrize(
    "respond, code",
    [(steam_timeout, 504), (lambda r: httpx.Response(500), 502), (lambda r: httpx.Response(403), 502)],
    ids=["timeout", "500", "bad-key"],
)
async def test_steam_down_saves_nothing(client, auth_headers, session_factory, fake_steam, respond, code):
    headers = await linked_user(auth_headers, session_factory)
    fake_steam.owned_answer = respond

    res = await client.post(SYNC, headers=headers)
    assert res.status_code == code
    assert "secret-key-for-test" not in res.text
    assert await my_entries(session_factory) == {}


async def test_too_soon(client, auth_headers, session_factory, fake_steam):
    headers = await linked_user(auth_headers, session_factory)
    await sync(client, headers)
    calls = fake_steam.owned_calls

    res = await client.post(SYNC, headers=headers)
    assert res.status_code == 429
    assert 1 <= int(res.headers["Retry-After"]) <= 60
    assert fake_steam.owned_calls == calls   # Steam을 부르지도 않는다


async def test_failed_attempts_are_limited(client, auth_headers, session_factory, fake_steam):
    """비공개 상태로 연타해도 Steam을 끝없이 부르지 않는다"""
    headers = await linked_user(auth_headers, session_factory)
    fake_steam.owned_answer = lambda r: httpx.Response(200, json={"response": {}})
    for _ in range(10):
        assert (await client.post(SYNC, headers=headers)).status_code == 409

    res = await client.post(SYNC, headers=headers)
    assert res.status_code == 429
    assert fake_steam.owned_calls == 10


async def test_requires_login(client):
    assert (await client.post(SYNC)).status_code == 401


# ─── 동시에 ─────────────────────────────────────────────────


OWNED = [OwnedGame(367520, "Hollow Knight", 10), OwnedGame(570, "Dota 2", 0)]


async def test_same_user_twice_at_once(auth_headers, session_factory):
    """같은 사람이 동시에 두 번 ─ 하나는 합치고, 잠금을 기다린 다른 하나는 간격에 걸린다. 중복 0"""
    await linked_user(auth_headers, session_factory)

    async def run():
        async with session_factory() as db:
            return await merge_owned_games(db, 1, STEAM_A, OWNED)

    results = await asyncio.gather(run(), run(), return_exceptions=True)
    assert sorted(type(r).__name__ for r in results) == ["SyncResult", "SyncTooSoon"]
    assert set(await my_entries(session_factory)) == {367520, 570}


async def test_sync_waits_for_user_lock(auth_headers, session_factory):
    """다른 동기화가 진행 중이면(사용자 행이 잠겨 있으면) 기다린다. 앞사람이 끝나면 간격에 걸려 아무것도 하지 않는다

    위 테스트는 두 요청이 실제로 겹치는지 보장하지 못한다(앞의 것이 금방 끝날 수 있다). 잠금을 테스트가 직접 쥐고 순서를 정한다
    """
    await linked_user(auth_headers, session_factory)

    async def run():
        async with session_factory() as db:
            return await merge_owned_games(db, 1, STEAM_A, OWNED)

    async with session_factory() as holder:
        await holder.execute(select(User.id).where(User.id == 1).with_for_update())
        task = asyncio.create_task(run())
        await asyncio.sleep(0.3)
        assert not task.done()   # 잠금을 기다리는 중
        await holder.execute(update(User).where(User.id == 1).values(steam_synced_at=func.now()))
        await holder.commit()

    with pytest.raises(SyncTooSoon):
        await task
    assert await my_entries(session_factory) == {}


async def test_two_users_same_new_game_at_once(auth_headers, session_factory):
    """다른 두 사람이 처음 보는 같은 게임을 동시에 ─ games 행은 하나, 기록은 각자"""
    await linked_user(auth_headers, session_factory, A, STEAM_A)
    await linked_user(auth_headers, session_factory, B, STEAM_B)

    async def run(user_id, steam_id):
        async with session_factory() as db:
            return await merge_owned_games(db, user_id, steam_id, OWNED)

    a, b = await asyncio.gather(run(1, STEAM_A), run(2, STEAM_B))
    assert a.added == b.added == 2
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Game)) == 2
        assert await db.scalar(select(func.count()).select_from(Entry)) == 4


async def test_search_registration_during_sync(auth_headers, session_factory):
    """검색 등록이 진행 중일 때 동기화 ─ 등록(MANUAL)이 이기고 건너뜀으로 센다

    실제로는 등록의 FK 검사가 users 행에 KEY SHARE 잠금을 걸어, 동기화의 사용자 잠금(FOR UPDATE)이 등록이 끝나기를 기다린다.
    그래서 동기화는 commit된 MANUAL 기록을 읽고 건너뛴다. entries ON CONFLICT는 그 뒤의 두 번째 방어선이다
    """
    await linked_user(auth_headers, session_factory)
    async with session_factory() as db:
        game = Game(title="Hollow Knight", title_norm="hollowknight", steam_appid=367520)
        db.add(game)
        await db.commit()
        game_id = game.id

    async with session_factory() as other:
        # 다른 요청이 MANUAL 기록을 넣고 아직 commit하지 않았다
        other.add(Entry(user_id=1, game_id=game_id, status="CLEARED", source="MANUAL", purchase_price=9900))
        await other.flush()

        async def run():
            async with session_factory() as db:
                return await merge_owned_games(db, 1, STEAM_A, OWNED)

        task = asyncio.create_task(run())
        await asyncio.sleep(0.3)   # 동기화가 같은 (사용자, 게임) 줄에서 기다리게 둔다
        await other.commit()
        result = await task

    assert (result.added, result.skipped_manual) == (1, 1)
    entries = await my_entries(session_factory)
    assert entries[367520].source == "MANUAL"
    assert entries[367520].purchase_price == 9900


async def test_source_changed_to_manual_during_sync(auth_headers, session_factory):
    """동기화가 STEAM으로 읽은 뒤, 다른 탭에서 그 기록을 MANUAL로 바꿨다 ─ 사용자가 고친 값을 덮어쓰지 않는다

    기록 수정은 사용자 행을 잠그지 않아 실제로 겹칠 수 있다. 갱신 SQL의 source='STEAM' 조건이 막는다
    """
    await linked_user(auth_headers, session_factory)
    async with session_factory() as db:
        await merge_owned_games(db, 1, STEAM_A, OWNED)
    await allow_next_sync(session_factory)

    async with session_factory() as other:
        await other.execute(
            update(Entry).where(Entry.user_id == 1).values(source="MANUAL", playtime_minutes=77)
        )   # 아직 commit 전 ─ 동기화는 옛 값(STEAM)을 읽는다

        async def run():
            async with session_factory() as db:
                return await merge_owned_games(
                    db, 1, STEAM_A, [OwnedGame(367520, "Hollow Knight", 999), OwnedGame(570, "Dota 2", 5)]
                )

        task = asyncio.create_task(run())
        await asyncio.sleep(0.3)
        assert not task.done()   # 같은 행을 고치려다 기다린다
        await other.commit()
        result = await task

    assert (result.updated, result.skipped_manual) == (0, 2)
    entries = await my_entries(session_factory)
    assert {e.playtime_minutes for e in entries.values()} == {77}


async def test_unlinked_while_fetching(auth_headers, session_factory):
    """Steam에서 받아 오는 사이 연결을 풀었거나 다른 Steam으로 바꿨다 ─ 넣지 않는다"""
    await linked_user(auth_headers, session_factory, steam_id=STEAM_B)
    async with session_factory() as db:
        with pytest.raises(SyncNotLinked):
            await merge_owned_games(db, 1, STEAM_A, OWNED)
    assert await my_entries(session_factory) == {}


async def test_too_soon_is_checked_after_lock(auth_headers, session_factory):
    await linked_user(auth_headers, session_factory)
    async with session_factory() as db:
        await merge_owned_games(db, 1, STEAM_A, OWNED)
    async with session_factory() as db:
        with pytest.raises(SyncTooSoon) as caught:
            await merge_owned_games(db, 1, STEAM_A, OWNED)
    assert 1 <= caught.value.retry_after <= 61

# app/services/steam_sync.py
"""Steam 라이브러리를 내 기록에 합친다 (ARCHITECTURE 5.1절, decisions/0009 · 0016)

비유: 은행 거래 내역을 가계부에 옮겨 적기. 가계부에 없는 거래는 새 줄로 적고,
Steam이 적은 줄(STEAM)은 금액만 최신으로 고치고, 내가 손으로 적은 줄(MANUAL)은 절대 건드리지 않는다.

이 파일은 Steam을 부르지 않는다 ─ 받아 온 목록(services/steam.py fetch_owned_games)만 넣는다.
외부 호출은 잠금을 잡기 전에 끝내야 해서, 부르는 쪽(라우터)이 먼저 받아 온다
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Integer, any_, bindparam, column, func, select, update, values
from sqlalchemy.dialects.postgresql import ARRAY, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.normalize import normalize_title
from app.models.entry import Entry
from app.models.game import Game
from app.models.steam_app import SteamApp
from app.models.user import User
from app.services.steam import OwnedGame, usable_title

# 한 사람의 기록 상한 ─ 등록 API와 같은 값을 쓴다 (routers/entries.py, decisions/0011)
MAX_ENTRIES_PER_USER = 5000

# 한 쿼리에 넣는 행 수 ─ asyncpg는 쿼리 하나에 값을 32767개까지만 받는다 (entries 5칸 × 5000 = 25000)
INSERT_BATCH = 5000

# 같은 사람의 동기화 간격. steam_synced_at으로 센다 ─ 서버를 다시 켜도 남는다 (DATA_MODEL 2.1절)
SYNC_COOLDOWN = timedelta(seconds=60)


class SyncNotLinked(Exception):
    """Steam이 연결돼 있지 않거나, 받아 오는 사이 해제 · 다른 Steam으로 바뀌었다"""


class SyncTooSoon(Exception):
    """방금 동기화했다. retry_after초 뒤에 다시"""

    def __init__(self, retry_after: int):
        super().__init__(retry_after)
        self.retry_after = retry_after


@dataclass
class SyncResult:
    """동기화 결과 요약 (ARCHITECTURE 5.1절) ─ 화면(S-06)이 그대로 보여 준다"""

    added: int = 0               # 새로 만든 기록
    updated: int = 0             # Steam 플레이타임으로 고친 기록
    unchanged: int = 0           # Steam 기록인데 값이 같음
    skipped_manual: int = 0      # 내가 직접 입력한 기록이라 건드리지 않음
    skipped_limit: int = 0       # 상한 5,000개를 넘어 넣지 못함
    skipped_no_title: int = 0    # 이름을 쓸 수 없어 게임을 만들지 못함
    same_title_manual: int = 0   # 새 Steam 기록 중, 내가 직접 등록한 게임과 제목이 같은 것
    synced_at: datetime | None = None


def _any(ids: Iterable[int]):
    """`= ANY(배열)` ─ 목록을 값 하나(배열)로 보낸다. IN (...)은 원소마다 값이 하나씩이라 2만 개면 한도에 닿는다"""
    return any_(bindparam(None, list(ids), type_=ARRAY(Integer)))


def retry_after_seconds(synced_at: datetime | None, now: datetime) -> int:
    """마지막 동기화에서 간격이 덜 지났으면 남은 초(1 이상), 아니면 0"""
    if synced_at is None:
        return 0
    left = (synced_at + SYNC_COOLDOWN - now).total_seconds()
    return int(left) + 1 if left > 0 else 0


async def merge_owned_games(
    db: AsyncSession, user_id: int, steam_id: str, owned: list[OwnedGame]
) -> SyncResult:
    """받아 온 보유 게임 목록을 합치고 commit한다. 트랜잭션 하나 ─ 중간에 실패하면 아무것도 남지 않는다"""
    # 앞에서 읽기만 한 트랜잭션이 열려 있으면 닫는다 ─ 잠금은 새 트랜잭션에서 잡아야 최신 값을 본다
    await db.commit()

    # ① 사용자 잠금 ─ 같은 사람의 동기화가 동시에 오면 줄을 세운다. 계정 삭제(services/auth.py)와도 줄을 선다
    # 비유: 가계부는 한 번에 한 사람만 펼친다
    user = await db.scalar(
        select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
    )
    # 받아 오는 사이 해제했거나 다른 Steam으로 바꿨다 ─ 다른 Steam의 라이브러리를 넣지 않는다
    if user is None or user.steam_id != steam_id:
        await db.rollback()
        raise SyncNotLinked
    now: datetime = await db.scalar(select(func.now()))
    # 앞사람이 방금 끝냈다 ─ 잠금을 기다린 두 번째 요청은 여기서 멈춘다(같은 일을 두 번 하지 않는다)
    wait = retry_after_seconds(user.steam_synced_at, now)
    if wait:
        await db.rollback()
        raise SyncTooSoon(wait)

    result = SyncResult()
    by_appid = {g.appid: g for g in owned}

    # ② 이미 있는 게임 · 내 기록을 한 번에 읽는다 ─ 게임마다 물으면 5,000번 왕복이 된다
    game_ids: dict[int, int] = {}   # appid → games.id
    if by_appid:
        rows = await db.execute(select(Game.steam_appid, Game.id).where(Game.steam_appid == _any(by_appid)))
        game_ids = {r.steam_appid: r.id for r in rows}
    mine: dict[int, tuple[int, str, int]] = {}   # games.id → (entry id, source, playtime)
    if game_ids:
        rows = await db.execute(
            select(Entry.game_id, Entry.id, Entry.source, Entry.playtime_minutes).where(
                Entry.user_id == user_id, Entry.game_id == _any(game_ids.values())
            )
        )
        mine = {r.game_id: (r.id, r.source, r.playtime_minutes) for r in rows}

    # ③ 나누기 ─ STEAM 기록은 갱신 후보, MANUAL은 건너뜀, 없으면 새로 만들 것
    to_update: list[tuple[int, int]] = []   # (entry id, Steam 분)
    new_appids: list[int] = []
    for appid in sorted(by_appid):   # appid 순으로 고정 ─ 상한에 걸릴 때 어떤 게임이 빠지는지 매번 같다
        minutes = by_appid[appid].playtime_minutes
        found = mine.get(game_ids.get(appid, 0))
        if found is None:
            new_appids.append(appid)
        elif found[1] != "STEAM":
            result.skipped_manual += 1
        elif found[2] == minutes:
            result.unchanged += 1
        else:
            to_update.append((found[0], minutes))

    # ④ STEAM 기록 갱신 ─ 플레이타임만. 줄어도 Steam 값으로 맞춘다 (ARCHITECTURE 5.1절)
    # source='STEAM'을 SQL에서 한 번 더 본다 ─ 읽은 뒤 사용자가 다른 탭에서 MANUAL로 바꿨으면 건드리지 않는다
    # 상태 · 구매일 · 구매가 · 평점 · 한줄평은 동기화가 절대 바꾸지 않는다
    entries = Entry.__table__
    for start in range(0, len(to_update), INSERT_BATCH):
        batch = values(column("eid", Integer), column("minutes", Integer), name="steam_values").data(
            to_update[start : start + INSERT_BATCH]
        )
        changed = await db.execute(
            update(entries)
            .where(entries.c.id == batch.c.eid, entries.c.user_id == user_id, entries.c.source == "STEAM")
            .values(playtime_minutes=batch.c.minutes, updated_at=func.now())
            .returning(entries.c.id)
        )
        result.updated += len(changed.all())
    result.skipped_manual += len(to_update) - result.updated

    # ⑤ 상한 ─ 넣을 수 있는 만큼만. 게임 행도 넣을 몫만 만든다(2만 개 라이브러리가 공용 games를 채우지 않게)
    count = await db.scalar(select(func.count()).select_from(Entry).where(Entry.user_id == user_id))
    room = max(0, MAX_ENTRIES_PER_USER - count)
    result.skipped_limit = max(0, len(new_appids) - room)
    new_appids = new_appids[:room]

    # ⑥ 없는 게임 만들기 ─ 제목은 Steam이 준 영어 이름, 안 되면 미러 이름. 상세는 나중에 (decisions/0016)
    missing = [a for a in new_appids if a not in game_ids]
    if missing:
        rows = await db.execute(select(SteamApp.appid, SteamApp.name).where(SteamApp.appid == _any(missing)))
        mirror = {r.appid: r.name for r in rows}
        game_rows = []
        for appid in missing:
            title = usable_title(by_appid[appid].name, mirror.get(appid))
            if title is None:
                result.skipped_no_title += 1
                continue
            game_rows.append({"title": title, "title_norm": normalize_title(title), "steam_appid": appid})
        for start in range(0, len(game_rows), INSERT_BATCH):
            # 다른 사람이 같은 게임을 동시에 넣어도 하나만 남는다 ─ 있으면 넘어간다 (ARCHITECTURE 5.1절)
            # DO NOTHING은 상대 트랜잭션이 끝나기를 기다렸다가 판단한다
            await db.execute(
                insert(Game)
                .values(game_rows[start : start + INSERT_BATCH])
                .on_conflict_do_nothing(index_elements=[Game.steam_appid])
            )
        if game_rows:
            rows = await db.execute(
                select(Game.steam_appid, Game.id).where(Game.steam_appid == _any(r["steam_appid"] for r in game_rows))
            )
            game_ids.update({r.steam_appid: r.id for r in rows})

    # ⑦ 새 기록 ─ source=STEAM, 0분이면 미시작(BACKLOG), 아니면 플레이중 (ARCHITECTURE 5.1절)
    # 세션은 만들지 않는다(첫 값은 기준점). 구매일 · 구매가는 비워 둔다 ─ Steam API가 주지 않는다 (decisions/0019)
    entry_rows = [
        {
            "user_id": user_id,
            "game_id": game_ids[appid],
            "status": "PLAYING" if by_appid[appid].playtime_minutes > 0 else "BACKLOG",
            "playtime_minutes": by_appid[appid].playtime_minutes,
            "source": "STEAM",
        }
        for appid in new_appids
        if appid in game_ids
    ]
    added_game_ids: list[int] = []
    for start in range(0, len(entry_rows), INSERT_BATCH):
        # 검색 등록과 겹쳐도 등록(MANUAL)이 이긴다. 보통은 등록의 FK 검사(users KEY SHARE)가 ①의 잠금과 부딪혀
        # 둘이 줄을 서므로 ②에서 이미 보인다. ON CONFLICT는 그래도 겹쳤을 때의 두 번째 방어선이다 ─ 넘어가고 건너뜀으로 센다
        inserted = await db.scalars(
            insert(Entry)
            .values(entry_rows[start : start + INSERT_BATCH])
            .on_conflict_do_nothing(index_elements=[Entry.user_id, Entry.game_id])
            .returning(Entry.game_id)
        )
        added_game_ids.extend(inserted.all())
    result.added = len(added_game_ids)
    result.skipped_manual += len(entry_rows) - result.added

    # ⑧ 같은 제목의 직접 등록 게임 ─ 행은 따로 두고 수만 알린다 (decisions/0009)
    if added_game_ids:
        steam_norms = select(Game.title_norm).where(Game.id == _any(added_game_ids))
        result.same_title_manual = await db.scalar(
            select(func.count()).select_from(Game).where(
                Game.owner_user_id == user_id,
                Game.steam_appid.is_(None),
                Game.title_norm.in_(steam_norms),
            )
        )

    user.steam_synced_at = now
    result.synced_at = now
    await db.commit()
    return result

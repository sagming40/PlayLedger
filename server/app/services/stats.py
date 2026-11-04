# app/services/stats.py
"""S-05 통계의 집계 (DESIGN 3.5절, REQUIREMENTS 5장)

모든 쿼리가 user_id로 시작한다 ─ 게임 · 장르는 공유 데이터지만 내 기록을 거쳐서만 닿는다 (services/entry.py의 금고 비유)
읽기만 하므로 수정 · 삭제와 겹쳐도 잠그거나 재조회하지 않는다. 겹치면 그 순간의 숫자가 보이고, 다음 진입 때 맞는다 (DESIGN 3.5절 "화면 진입 시마다 조회")
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import cost_per_hour, percent
from app.models.entry import Entry
from app.models.game import Game, Genre, game_genres
from app.schemas.stats import CostlyGame, GenreStat, IdleGame, StatsRead

# 화면이 기본 3개를 보이고 더보기로 펼치는 최대 개수 (DESIGN 3.5절)
LIST_LIMIT = 20

# 1시간 미만이면 "사놓고 거의 안 한 게임" (REQUIREMENTS 5.2절)
ABANDONED_MINUTES = 60


def effective_today(requested: date | None, now: datetime | None = None) -> date:
    """방치일수를 셀 "오늘". 화면이 보낸 날짜를 쓴다

    서버의 오늘은 UTC라 한국 오전 9시 전에는 하루 전이다. 그대로 쓰면 목록 카드(브라우저 날짜)는 214일, 통계는 213일이 된다
    세계 어디든 UTC와 날짜 차이는 하루까지다. 그보다 멀면 PC 시계가 틀린 것이라 서버 날짜를 쓴다
    ─ 시계가 틀렸다고 통계 화면 전체를 에러로 막을 일은 아니다
    """
    server_today = (now or datetime.now(timezone.utc)).date()
    if requested is None or abs(requested - server_today) > timedelta(days=1):
        return server_today
    return requested


def round_half_up(value: Decimal) -> int:
    """평균의 반올림 ─ round()는 0.5를 짝수 쪽으로 보낸다 (core/metrics.py 참고)"""
    return int(value + Decimal("0.5"))


async def get_stats(db: AsyncSession, *, user_id: int, today: date) -> StatsRead:
    mine = Entry.user_id == user_id

    # ① 숫자 카드 ─ FILTER = 같은 행들을 조건별로 나눠 센다. 쿼리 하나로 끝난다
    counts = (
        await db.execute(
            select(
                func.count().label("total"),
                func.count().filter(Entry.status == "BACKLOG").label("backlog"),
                func.count().filter(Entry.status == "CLEARED").label("cleared"),
                func.count().filter(Entry.playtime_minutes < ABANDONED_MINUTES).label("abandoned"),
            ).where(mine)
        )
    ).one()

    # ② 오래 방치된 게임 (REQUIREMENTS 2장 방치일수) ─ 구매일을 모르면 셀 수 없어 뺀다
    idle_rows = (
        await db.execute(
            select(Entry.id, Game.title, Game.cover_url, Entry.purchased_at)
            .join(Game, Game.id == Entry.game_id)
            .where(mine, Entry.status == "BACKLOG", Entry.purchased_at.is_not(None))
            # id까지 ─ 같은 날 산 게임의 순서가 새로고침마다 바뀌지 않게
            .order_by(Entry.purchased_at, Entry.id)
            .limit(LIST_LIMIT)
        )
    ).all()

    # ③ 시간당 비용이 높은 게임 ─ 구매가가 없거나 플레이타임이 0이면 값이 없어 줄을 세울 수 없다
    # Numeric으로 ─ integer끼리 곱하면 구매가가 3,600만 원을 넘을 때 넘치고, 나누면 소수가 버려진다
    cost = cast(Entry.purchase_price, Numeric) * 60 / Entry.playtime_minutes
    cost_rows = (
        await db.execute(
            select(Entry.id, Game.title, Game.cover_url, Entry.purchase_price, Entry.playtime_minutes)
            .join(Game, Game.id == Entry.game_id)
            .where(mine, Entry.purchase_price.is_not(None), Entry.playtime_minutes > 0)
            .order_by(cost.desc(), Entry.id)
            .limit(LIST_LIMIT)
        )
    ).all()

    # ④ 장르별 (DATA_MODEL 3.3절) ─ 내 기록에서 출발하므로 남의 기록은 세지 않는다
    # 장르가 여러 개인 게임은 장르마다 세고, 장르가 없는 게임은 나오지 않는다 ─ 합계가 총 보유와 달라도 정상이다
    started_filter = Entry.status != "BACKLOG"
    genre_rows = (
        await db.execute(
            select(
                Genre.id,
                Genre.name,
                func.count().label("total"),
                func.count().filter(started_filter).label("started"),
                func.count().filter(Entry.status == "CLEARED").label("cleared"),
                func.avg(Entry.playtime_minutes).filter(started_filter).label("avg_minutes"),
            )
            .select_from(Entry)
            .join(game_genres, game_genres.c.game_id == Entry.game_id)
            .join(Genre, Genre.id == game_genres.c.genre_id)
            .where(mine)
            .group_by(Genre.id)
        )
    ).all()

    genres = [
        GenreStat(
            genre_id=r.id,
            name=r.name,
            total=r.total,
            started=r.started,
            cleared=r.cleared,
            completion_rate=percent(r.cleared, r.started),
            avg_playtime_minutes=None if r.avg_minutes is None else round_half_up(r.avg_minutes),
        )
        for r in genre_rows
    ]
    # 완주율이 높은 순, 같으면 많이 가진 장르부터. 시작한 게임이 없는 장르(None)는 맨 뒤
    genres.sort(key=lambda g: (g.completion_rate is None, -(g.completion_rate or 0), -g.total, g.genre_id))

    return StatsRead(
        total=counts.total,
        backlog=counts.backlog,
        abandoned_rate=percent(counts.abandoned, counts.total),
        # 분모에서 미시작을 뺀다 ─ 게임을 살수록 완주율이 떨어지면 안 된다 (REQUIREMENTS 5.3절)
        completion_rate=percent(counts.cleared, counts.total - counts.backlog),
        longest_idle=[
            # 미래 날짜(입력 실수)는 0일 ─ 목록 카드의 idleDays와 같은 규칙
            IdleGame(entry_id=r.id, title=r.title, cover_url=r.cover_url, idle_days=max(0, (today - r.purchased_at).days))
            for r in idle_rows
        ],
        highest_cost=[
            CostlyGame(
                entry_id=r.id,
                title=r.title,
                cover_url=r.cover_url,
                cost_per_hour=cost_per_hour(r.purchase_price, r.playtime_minutes),
            )
            for r in cost_rows
        ],
        genres=genres,
    )

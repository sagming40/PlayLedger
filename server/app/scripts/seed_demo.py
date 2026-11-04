# app/scripts/seed_demo.py
"""통계를 확인할 예시 게임 26개를 한 계정에 넣는다 (PLAN M4). 제목은 전부 지어낸 것이다

실행: server/에서 python -m app.scripts.seed_demo --email 나@example.com
계정은 화면에서 먼저 만든다. 기록이 이미 있는 계정 · 로컬이 아닌 DB에는 넣지 않는다.
구매일을 '오늘로부터 며칠 전'으로 적어서 언제 넣어도 방치일수가 같다.
손으로 계산한 기대값은 tests/test_stats.py에 있다. 여기를 고치면 그쪽도 다시 계산한다.
"""

import argparse
import asyncio
import sys
from datetime import date, timedelta
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import AsyncSessionLocal, engine
from app.models.entry import Entry
from app.models.user import User
from app.services.game import find_or_create_game
from app.services.genre import attach_genres_if_empty

# 장르 id ─ alembic seed_genres가 넣는 고정 8개 (DATA_MODEL 2.5절)
ACTION, STRATEGY, RPG, CASUAL, RACING, SPORTS, ADVENTURE, SIM = range(1, 9)


class Demo(NamedTuple):
    title: str
    status: str
    genres: list[int]
    days_ago: int | None   # 구매일이 오늘로부터 며칠 전인지. None = 모름
    price: int | None
    minutes: int
    rating: int | None = None


DEMO = [
    # 미시작 8개 ─ 방치 강조 경계(180일) · 오늘 산 게임 · 구매일 모름 · 잠깐 켜 본 게임
    Demo("[예시] 별빛 왕국", "BACKLOG", [RPG], 214, 66000, 0),
    Demo("[예시] 강철 항해", "BACKLOG", [ACTION, RPG], 180, 59000, 0),
    Demo("[예시] 깊은 동굴 탐험", "BACKLOG", [ADVENTURE], 179, 32000, 0),
    Demo("[예시] 도시 설계사", "BACKLOG", [SIM], 92, 45000, 0),
    Demo("[예시] 달빛 정원", "BACKLOG", [CASUAL], 41, 15000, 0),
    Demo("[예시] 오늘 산 퍼즐", "BACKLOG", [CASUAL], 0, 9900, 0),
    Demo("[예시] 구매일 모르는 게임", "BACKLOG", [STRATEGY], None, None, 0),
    Demo("[예시] 잠깐 켜 본 게임", "BACKLOG", [ACTION], 14, 20000, 30),
    # 플레이중 6개 ─ 사장 경계(59분 · 60분) · 무료 · 구매가 모름
    Demo("[예시] 붉은 사막 횡단", "PLAYING", [ACTION, ADVENTURE], 300, 66000, 750),
    Demo("[예시] 작은 농장 일기", "PLAYING", [CASUAL, SIM], 200, 16000, 2430),
    Demo("[예시] 서킷 챔피언", "PLAYING", [RACING], 30, 70000, 59),
    Demo("[예시] 축구 감독 시즌", "PLAYING", [SPORTS], 10, 55000, 60),
    Demo("[예시] 무료 전투장", "PLAYING", [ACTION], 5, 0, 600),
    Demo("[예시] 구매가 모르는 게임", "PLAYING", [RPG], None, None, 300),
    # 클리어 6개
    Demo("[예시] 황금 도시", "CLEARED", [ACTION, RPG], 400, 66000, 3744, 4),
    Demo("[예시] 숲속 기사단", "CLEARED", [ACTION, ADVENTURE], 380, 18000, 750, 5),
    Demo("[예시] 눈 덮인 산 오르기", "CLEARED", [ACTION, CASUAL], 350, 22000, 1098, 5),
    Demo("[예시] 은하 전략 사령부", "CLEARED", [STRATEGY], 320, 49000, 1860, 4),
    Demo("[예시] 바람의 모험", "CLEARED", [ADVENTURE, RPG], 310, 33000, 1200, 3),
    Demo("[예시] 짧은 엔딩", "CLEARED", [CASUAL], 300, 5000, 45, 3),
    # 보류 3개 ─ 장르 없는 게임 포함
    Demo("[예시] 문명의 새벽", "ON_HOLD", [STRATEGY], 250, 60000, 480),
    Demo("[예시] 전술 함대", "ON_HOLD", [STRATEGY, SIM], 240, 45000, 120),
    Demo("[예시] 장르 없는 게임", "ON_HOLD", [], 100, 10000, 600),
    # 포기 3개 ─ 시간당 비용 동점 · 플레이타임 0
    Demo("[예시] 드리프트 왕", "DROPPED", [RACING], 150, 66000, 72, 2),
    Demo("[예시] 농구 스타", "DROPPED", [SPORTS], 120, 40000, 0),
    Demo("[예시] 어둠의 탑", "DROPPED", [ACTION, RPG], 90, 52000, 240, 1),
]


async def add_demo_entries(db: AsyncSession, *, user_id: int, today: date) -> None:
    """예시 기록을 넣는다. commit은 부르는 쪽이 한다"""
    for demo in DEMO:
        # 게임을 얻는 입구는 한 곳뿐이다 (ARCHITECTURE 2.2절)
        game = await find_or_create_game(db, demo.title, owner_user_id=user_id)
        await attach_genres_if_empty(db, game.id, demo.genres)
        db.add(
            Entry(
                user_id=user_id,
                game_id=game.id,
                status=demo.status,
                purchased_at=None if demo.days_ago is None else today - timedelta(days=demo.days_ago),
                purchase_price=demo.price,
                playtime_minutes=demo.minutes,
                rating=demo.rating,
                source="MANUAL",
            )
        )
    await db.flush()


async def main(email: str) -> int:
    # 운영 DB에 예시 게임이 들어가면 공유 테이블(games)에 남는다 ─ 로컬에서만
    host = make_url(settings.database_url).host
    if host not in ("localhost", "127.0.0.1"):
        print(f"실패: 로컬 DB에만 넣는다 (지금 host: {host})", file=sys.stderr)
        return 1
    try:
        async with AsyncSessionLocal() as db:
            user_id = await db.scalar(select(User.id).where(User.email == email))
            if user_id is None:
                print("실패: 그 이메일의 계정이 없다. 화면에서 먼저 가입한다", file=sys.stderr)
                return 1
            existing = await db.scalar(select(func.count()).select_from(Entry).where(Entry.user_id == user_id))
            if existing:
                print(f"실패: 이미 기록이 {existing}개 있는 계정이다. 숫자가 섞이지 않게 빈 계정에만 넣는다", file=sys.stderr)
                return 1
            await add_demo_entries(db, user_id=user_id, today=date.today())
            await db.commit()
    finally:
        await engine.dispose()
    print(f"예시 기록 {len(DEMO)}개를 넣었다")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="통계 확인용 예시 게임을 넣는다")
    parser.add_argument("--email", required=True, help="기록을 넣을 계정 (화면에서 먼저 가입)")
    sys.exit(asyncio.run(main(parser.parse_args().email)))

"""Game 중복 판별 ─ 표기가 달라도 동일한 Game이고, 동시 등록에도 ROW가 하나만 남는다.

ERD 2.4절 판별 순서:
1단계 steam_appid / 2단계 title_norm(수동 Game) / 3단계 INSERT / 4단계 충돌 시 재조회
"""

import asyncio

from sqlalchemy import func, select

from app.models.game import Game
from app.services.game import find_or_create_game


async def count_games(session, title_norm: str) -> int:
    """동일한 정규화 제목을 가진 수동 Game의 ROW 수"""
    return await session.scalar(
        select(func.count())
        .select_from(Game)
        .where(Game.title_norm == title_norm, Game.steam_appid.is_(None))
    )


async def test_different_notation_reuses_the_same_game(session_factory):
    """공백 · 대소문자만 다른 제목은 동일한 Game으로 취급한다. (판별 2단계)

    먼저 등록한 사람이 적은 title이 그대로 남는 것까지 확인한다 ─
    나중 사람의 표기로 덮어쓰면 다른 유저의 데이터까지 건드리는 셈이다.
    """
    async with session_factory() as db:
        first = await find_or_create_game(db, "Hollow Knight")
        await db.commit()

        second = await find_or_create_game(db, "  hollow KNIGHT ")
        await db.commit()

        assert first.id == second.id, (first.id, second.id)
        assert second.title == "Hollow Knight", second.title
        assert await count_games(db, "hollowknight") == 1


async def test_concurrency_create_falls_back_to_refresh(session_factory):
    """동시에 동일 Game을 생성하려 하면, 늦은 쪽이 4단계 재조회로 먼저 생성된 ROW를 받는다.

    4단계 평소 절대 실행되지 않는 경로다. 손으로는 밟을 수 없으므로 여기서만 검증할 수 있다.
    """
    a = session_factory()
    b = session_factory()
    # 연결을 미리 열어둔다 (first query의 첫 개통 비용을 측정에서 뺀다)
    await a.execute(select(1))
    await b.execute(select(1))

    try:
        # ── A가 INSERT까지는 되어있고 아직 commit은 하지 않은 상태
        game_a = await find_or_create_game(a, "Celeste")

        # ── B도 동일 Game을 생성하려 한다
        # 2단계에서는 A의 ROW가 보이지 않으므로(아직 commit 전) "없음" 판정 →
        # 3단계 INSERT를 시도하다가, 동일한 title_norm이 심사 중이므로 대기한다
        b_task = asyncio.create_task(find_or_create_game(b, "celeste!"))

        await asyncio.sleep(0.5)
        assert not b_task.done(), "B가 대기하지 않았다 ─ 충돌 상황이 만들어지지 않았다"

        # ── A가 확정하면 B의 INSERT가 거부되고 4단계(재조회)가 돈다
        await a.commit()
        game_b = await b_task
        await b.commit()

        # ── A,B가 동일한 ROW을 가리켜야 한다
        assert game_a.id == game_b.id, (game_a.id, game_b.id)

        async with session_factory() as check:
            assert await count_games(check, "celeste") == 1

    finally:
        await a.close()
        await b.close()

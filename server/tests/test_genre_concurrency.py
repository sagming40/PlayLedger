"""Genre 연결 동시 실행 ─ FOR UPDATE가 후발 요청을 막는지 확인한다.

ERD 2.5절: Game의 Genre는 0개일 때만 채운다.
"0개인지 확인 → 채우기" 사이에 다른 유저가 끼어들면 Genre가 합쳐지므로,
그 틈을 Game 행 잠금(FOR UPDATE)으로 막는다. 이 TEST가 그 잠금을 지킨다.
"""

from sqlalchemy import func, select

from app.models.game import Game, game_genres
from app.services.genre import attach_genres_if_empty


async def count_genres(session, game_id: int) -> int:
    "Game에 붙은 Genre 수를 count 한다 (검증용)"
    return await session.scalar(
        select(func.count())
        .select_from(game_genres)
        .where(game_genres.c.game_id == game_id)
    )


async def test_second_request_is_ignored_when_first_fills_genres(session_factory):
    """두 요청이 동일 Game에 서로 다른 Genre를 동시에 붙이려 하면, 먼저 온 쪽만 반영된다.

    FOR UPDATE를 지우면 두 요청이 "0개"를 보고 INSERT하여 Genre가 2개로 합쳐진다.
    """
    # ── 준비: Genre가 0개인 Game을 1개 생성하여 commit
    async with session_factory() as setup:
        game = Game(title="Concurrency Test", title_norm="concurrencytest")
        setup.add(game)
        await setup.commit()
        game_id = game.id

    # ── SESSION 2개를 열고, 연결을 미리 데운다
    # first query는 DB 연결을 새로 뚫느라 느리다 (이 환경에서 약 2s)
    # 본 측정 전에 미리 뚫어두지 않으면 그 비용이 잠금 대기 시간처럼 보인다
    a = session_factory()
    b = session_factory()
    await a.execute(select(1))
    await b.execute(select(1))

    try:
        # ── A가 Genre 1번을 붙인다. 아직 commit하지 않아 잠금을 쥔 상태
        await attach_genres_if_empty(a, game_id, [1])

        # ── B가 Genre 2번을 붙이려 한다
        # A가 Game 행을 잠그고 있으므로 여기서 대기한다.
        # 별도 task로 띄워야 이 줄에서 test가 멈추지 않는다
        import asyncio
        b_task = asyncio.create_task(attach_genres_if_empty(b, game_id, [2]))

        # B가 대기 상태로 들어갈 시간을 준다
        await asyncio.sleep(0.5)
        assert not b_task.done(), "B가 기다리지 않고 통과했다 ─ 잠금이 걸리지 않았다"

        # ── A가 commit하면 잠금이 풀리고 B가 깨어난다
        await a.commit()
        await b_task
        await b.commit()

        # ── 최종 확인: A가 넣은 1번만 남아야 한다
        async with session_factory() as check:
            assert await count_genres(check, game_id) == 1

    finally:
        await a.close()
        await b.close()

# app/services/genre.py
"""게임에 장르를 연결하는 곳 (ERD 2.5절 장르 연결 규칙)

games는 모든 사용자가 공유하는 데이터이다. 한 사람의 입력이 다른 사람의 통계를 변형시키면 안 된다.
따라서, Genre가 비어있는 게임에만 채우고, 이미 존재하는 경우 건드리지 않는다.
비유: 도서관 책의 분류 스티커 ─ 비어있는 책에만 부착하고, 이미 부착되어 있는 책은 떼거나 덧붙이지 않는다.
"""

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game, Genre, game_genres


async def genre_ids_exist(db: AsyncSession, genre_ids: list[int]) -> bool:
    """보낸 장르 id가 전부 실제로 존재하는 장르인지 확인한다

    비유: 손님이 적어낸 메뉴 번호를 메뉴판과 하나씩 대조하기
    없는 번호가 하나라도 존재할 경우 False
    """
    # set = 중복 제거. [1, 1, 2]를 보내도 {1, 2}로 인식한다
    wanted = set(genre_ids)
    if not wanted:
        return True   # 아무것도 선택하지 않았으면 확인할 것도 없다

    # SELECT id FROM genres WHERE id IN (...)
    found = await db.scalars(select(Genre.id).where(Genre.id.in_(wanted)))

    # 찾은 id 묶음이 보낸 id 묶음과 똑같아야 전부 존재하는 것
    return set(found.all()) == wanted


async def attach_genres_if_empty(
        db: AsyncSession, game_id: int, genre_ids: list[int]
) -> None:
    """게임에 연결된 장르가 0개일 경우에만 입력한 장르를 연결한다

    commit은 하지 않는다 ─ find_or_create_game과 같다
    게임 · 장르 · 보유 기록이 하나의 트랜잭션으로 함께 저장/취소 되어야 한다
    """
    wanted = set(genre_ids)
    if not wanted:
        return   # 붙일 Genre가 존재하지 않으면 잠글 이유가 없다

    # ① Game 행을 잠근다 ─ 화장실 문 잠그기
    # FOR UPDATE = row 하나 먼저 사용 선언. 동일한 행을 FOR UPDATE로 잡으려는 다른 트랜잭션은 대기
    # 잠금은 commit 또는 rollback 할 때 까지 유지된다
    # row 내용은 필요없고 잠그는게 주 목적이라 id만 조회한다
    await db.execute(
        select(Game.id).where(Game.id == game_id).with_for_update()
    )

    # ② 잠근 상태에서 Genre 수를 센다
    # game_genres는 class가 아니라 Table 객체이기 때문에, column을 .c(column)로 꺼낸다
    count = await db.scalar(
        select(func.count())
        .select_from(game_genres)
        .where(game_genres.c.game_id == game_id)
    )
    if count:
        return   # 이미 누군가 분류해 둔 게임 → 입력 무시

    # ③ 비어 있으니 채운다
    # 목록을 넘기면 row 여러 개를 한 번에 INSERT 한다
    # sorted = 매번 같은 순서로 넣어서, log를 확인할 때 헷갈리지 않도록
    await db.execute(
        insert(game_genres),
        [{"game_id": game_id, "genre_id": gid} for gid in sorted(wanted)],
    )

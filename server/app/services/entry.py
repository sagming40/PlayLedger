# app/services/entry.py
"""보유 기록을 조회하는 곳 (DATA_MODEL 2.6절)

모든 함수는 반드시 user_id를 받는다 ─ "누구의 기록인지"가 확인되지 않으면 아무것도 꺼낼 수 없다
비유: 은행 금고. 계좌번호(entry_id)만으로는 열리지 않고, 본인 확인(user_id) 함께 있어야 열린다
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entry import Entry
from app.models.game import Game, game_genres

# 목록 조회의 최대 개수 ─ 화면이 20개씩 불러온다 (DESIGN 3.2절)
# 상한을 정해두지 않으면 limit=999999로 요청해 DB를 통으로 긁어갈 수 있다
MAX_LIMIT = 100

# 정렬 기준 (DESIGN 3.2절). 구매일은 오래된 것부터 ─ 이 앱이 보여 주려는 "오래 묵힌 게임"이 먼저 온다
# 구매일을 모르는 기록은 맨 뒤로 ─ PostgreSQL은 오름차순이면 NULL을 맨 뒤에 두지만 의도를 코드에 적는다
SORT_ORDER = {
    "updated": (Entry.updated_at.desc(),),
    "purchased": (Entry.purchased_at.asc().nulls_last(),),
    # lower ─ 대소문자를 섞어 적어도 같은 자리에 온다. "C" ─ DB 설치 설정에 따라 순서가 달라지지 않게 글자 코드 순으로 고정한다
    # 코드 순이면 영문 다음에 한글이 오고, 한글끼리는 가나다순이다
    "title": (func.lower(Game.title).collate("C").asc(),),
    "playtime": (Entry.playtime_minutes.desc(),),
}


# 함수 매개변수의 * = "*" 뒤부터는 반드시 이름을 붙여 넘겨야함
# get_entry(db, 3, 7) 같은 형식으로 작성하면 error가 난다.
# 예: get_entry(db, user_id=3, entry_id=7)
# 이유: user_id와 entry_id는 모두 int이다. ─ 순서가 바뀌어도 Python이 인식하지 못함
#      → 순서가 뒤바뀌면 "남의 기록 조회"가 될 수도 있다 → 이름표를 붙이게 끔 강제하여 막는다
async def get_entry(
    db: AsyncSession, *, user_id: int, entry_id: int, for_update: bool = False
) -> Entry | None:
    """내 보유 기록 하나를 게임 · 장르까지 함께 불러온다. 내 것이 아니거나 없으면 None.

    None 하나로 "없음"과 "다른 유저의 것"을 구분하지 않는다 → Router는 모두 상태 코드 404로 응답한다
    for_update = 이 행을 commit까지 잠근다 ─ 읽고 나서 고치는 사이 다른 기기가 지우지 못하게 (수정 API)
    """
    stmt = (
        select(Entry)
        # 조건 2개를 동시에 ─ id만 동일하면 안 됨. 그 id의 주인도 맞아야 함 (사용자 격리)
        .where(Entry.id == entry_id, Entry.user_id == user_id)
        # selectinload ─ 연결된 게임과 장르를 '미리' 한꺼번에 불러온다
        # 비유: 택배를 하나씩 따로 배송받지 않고 묶음 배송 받기
        # 비동기 SQLAlchemy는 entry.game에 처음 접근 시 몰래 조회(lazy load)하지 못 하므로
        # 응답에 사용할 관계는 반드시 미리 불러와야 한다
        .options(selectinload(Entry.game).selectinload(Game.genres))
        # populate_existing = 세션이 이미 돌고 있는 객체라도 DB의 최신 값으로 덮어쓰기
        # 방금 만든 entry는 created_at(DB에서 채운 값)을 모르고,
        # game.genres는 insert()로 DB만 바뀌어서 Python 객체가 인식하지 못한다 → 지난 값을 신뢰하지 않는다
        .execution_options(populate_existing=True)
    )
    # selectinload는 쿼리가 따로 나가므로 잠기는 것은 Entry 행뿐이다 ─ 공유하는 Game은 잠그지 않는다
    if for_update:
        stmt = stmt.with_for_update()
    return await db.scalar(stmt)


async def count_entries(db: AsyncSession, user_id: int) -> int:
    """이 사람의 기록 수"""
    return await db.scalar(select(func.count()).select_from(Entry).where(Entry.user_id == user_id))


async def entry_exists(
    db: AsyncSession, *, user_id: int, game_id: int
) -> bool:
    """이 유저가 이 게임을 이미 등록했는지 확인한다 (중복 등록 1차 방어)"""
    found = await db.scalar(
        select(Entry.id).where(Entry.user_id == user_id, Entry.game_id == game_id)
    )
    return found is not None


async def list_entries(
    db: AsyncSession,
    *,
    user_id: int,
    status: str | None = None,
    genre_id: int | None = None,
    sort: str = "updated",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Entry], int]:
    """내 보유 기록 목록과 전체 개수를 함께 반환한다.

    비유: 서류함에서 20장을 꺼내면서 "모두 몇 장인지"까지 같이 세어준다.
    개수를 각각 따로 정하는 이유: 20개만 받으면 화면에서는 "여기까지가 전부인지 더 있는건지"를 알 방법이 없다.
    """
    # 공통 조건을 변수로 빼서 목록과 개수가 같은 기준을 사용하게 한다
    # 한 쪽에만 filter를 빠뜨리면 "3개인데 전체 10개"처럼 어긋난 형태의 응답이 나간다
    conditions = [Entry.user_id == user_id]
    if status is not None:
        conditions.append(Entry.status == status)
    if genre_id is not None:
        # 장르는 게임에 붙는다 ─ 조인하면 조건에 맞는 행이 늘 수 있어 "이 장르의 게임 중 하나인가"로 묻는다
        conditions.append(
            Entry.game_id.in_(select(game_genres.c.game_id).where(game_genres.c.genre_id == genre_id))
        )

    # ① 전체 개수 ─ row를 가져오지 않고 count만 한다
    total = await db.scalar(
        select(func.count()).select_from(Entry).where(*conditions)
    )

    # ② 이번 페이지 ─ 정렬 기본값은 최근 수정순 (DESIGN 3.2절)
    # id를 마지막 기준으로 두는 이유: 값이 동일한 row끼리 순서가 매번 달라질 수 있다
    # 즉, 1페이지와 2페이지에 동일한 기록이 겹치거나 빠지는 경우가 발생한다
    stmt = (
        select(Entry)
        .join(Game, Game.id == Entry.game_id)
        .where(*conditions)
        .options(selectinload(Entry.game).selectinload(Game.genres))
        .order_by(*SORT_ORDER[sort], Entry.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = await db.scalars(stmt)
    return list(rows.all()), total

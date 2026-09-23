# app/services/entry.py
"""보유 기록을 조회하는 곳 (ERD 2.6절)

모든 함수는 반드시 user_id를 받는다 ─ "누구의 기록인지"가 확인되지 않으면 아무것도 꺼낼 수 없다
비유: 은행 금고. 계좌번호(entry_id)만으로는 열리지 않고, 본인 확인(user_id) 함께 있어야 열린다
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entry import Entry
from app.models.game import Game


# 함수 매개변수의 * = "*" 뒤부터는 반드시 이름을 붙여 넘겨야함
# get_entry(db, 3, 7) 같은 형식으로 작성하면 error가 난다.
# 예: get_entry(db, user_id=3, entry_id=7)
# 이유: user_id와 entry_id는 모두 int이다. ─ 순서가 바뀌어도 Python이 인식하지 못함
#      → 순서가 뒤바뀌면 "남의 기록 조회"가 될 수도 있다 → 이름표를 붙이게 끔 강제하여 막는다
async def get_entry(
    db: AsyncSession, *, user_id: int, entry_id: int
) -> Entry | None:
    """내 보유 기록 하나를 게임 · 장르까지 함께 불러온다. 내 것이 아니거나 없으면 None.

    None 하나로 "없음"과 "다른 유저의 것"을 구분하지 않는다 → Router는 모두 상태 코드 404로 응답한다
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
    return await db.scalar(stmt)


async def entry_exists(
    db: AsyncSession, *, user_id: int, game_id: int
) -> bool:
    """이 유저가 이 게임을 이미 등록했는지 확인한다 (중복 등록 1차 방어)"""
    found = await db.scalar(
        select(Entry.id).where(Entry.user_id == user_id, Entry.game_id == game_id)
    )
    return found is not None

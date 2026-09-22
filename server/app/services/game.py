# app/services/game.py
"""게임 마스터 데이터를 찾거나 만드는 곳 (ERD 2.4절, ARCHITECTURE 2.2절)

게임을 얻는 입구는 이 곳 한 군데 뿐이다.
등록 API · Steam 동기화 · Seed Script가 모두 이 함수를 거친다.
비유: 도서관 신착 도서 접수 창구. 어떤 누군가가 책을 가져오든
'이미 서가에 있는 책'인지 확인된 이후에만 책을 꽂는다.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.normalize import normalize_title
from app.models.game import Game


async def _find_game(
    db: AsyncSession, title_norm: str, steam_appid: int | None
) -> Game | None:
    """판별 1·2단계 ─ 이미 존재하는 게임을 찾는다. 없다면 None.

    이름 앞의 _는 '이 파일 안에서만 사용하는 함수'라는 표시이다.
    외부에서는 반드시 find_or_create_game을 거쳐야 한다. (입구는 한 곳)
    """
    if steam_appid is not None:
        # 1단계 · Steam ID가 있으면 Steam ID만 본다 (주민번호로 찾기)
        stmt = select(Game).where(Game.steam_appid == steam_appid)
    else:
        # 2단계 · 수동 등록 게임 중 정규화 제목으로 찾아낸다 (이름으로 찾기)
        # 부분 UNIQUE와 범위가 같아서 많아야 1행이다
        stmt = select(Game).where(
            Game.title_norm == title_norm,
            Game.steam_appid.is_(None),   # == None이 아닌 is_(None) → SQL의 IS NULL
        )
    return await db.scalar(stmt)


async def find_or_create_game(
    db: AsyncSession, title: str, steam_appid: int | None = None
) -> Game:
    """게임을 찾아서 돌려주고, 없다면 새로 생성하여 돌려준다. (ERD 2.4절 판별 순서)

    commit은 하지 않는다. 장바구니에 담는 것까지만 하고 계산은 부른쪽에서 한다.
    게임과 보유 기록(entry)이 함께 저장되거나 함께 취소되어야 한다.
    """
    title = title.strip()

    # 호출한 쪽만 믿지 않고 직접 계산 한다.
    # Seed Script나 Steam 동기화는 schema(입국 심사대)를 거치지 않고 바로 도착한다.
    title_norm = normalize_title(title)

    game = await _find_game(db, title_norm, steam_appid)
    if game is not None:
        return game   # 이미 존재한다 → 먼저 등록한 사람이 적은 title이 그대로 유지된다

    # 3단계 · 없으면 새로 생성한다
    game = Game(title=title, title_norm=title_norm, steam_appid=steam_appid)
    try:
        # SAVEPOINT를 찍는다 ─ BOSS전 직전 SAVE
        # 이 block 내에서 실패하면 SAVE 지점까지만 되돌아가고, 외부 작업은 살아남는다.
        async with db.begin_nested():
            db.add(game)
            # flush = INSERT를 지금 DB로 보낸다. (commit 아님)
            # UNIQUE 위반은 이때 드러나야 try에서 잡을 수 있다.
            await db.flush()
    except IntegrityError:
        # 4단계 · 찾아본 뒤(2)와 만들기(3) 사이에 어떤 유저가 같은 게임을 먼저 등록한 상황
        # 그 유저가 만든 row를 다시 찾아 쓴다
        game = await _find_game(db, title_norm, steam_appid)
        if game is None:
            # 충돌했으나 다시 찾아봐도 존재하지 않는다 = 설계상 일어날 수 없는 상황
            # 조용히 넘어가는 것이 아니라 원래 error를 그대로 터뜨린다
            raise
    return game

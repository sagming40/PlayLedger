# app/routers/genres.py
# 장르 API ─ 고정 목록이라 조회만 있다 (ERD 2.5절)

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.game import Genre
from app.schemas.genre import GenreRead

# dependencies를 라우터에 걸면, 이 라우터의 모든 endpoint가 Login 검사를 거친다
# 비유: 방마다 자물쇠를 다는 대신 층 입구에 출입 게이트를 하나 세우는 것
# 유저 정보(누구인지)는 필요 없고, 로그인 여부만 확인하면 되기 때문데 해당 방식이 효율적이다
router = APIRouter(
    prefix="/api/genres",
    tags=["genres"],
    dependencies=[Depends(get_current_user)],
)


# "/"가 아니라 "" ─ prefix와 합쳐 정확히 /api/genres가 된다
# "/"로 표기하면 주소가 /api/genres/ 와 같은 형식이 되어, redirect(307)를 한 번 거치게 된다
@router.get("", response_model=list[GenreRead])
async def list_genres(db: AsyncSession = Depends(get_db)) -> list[Genre]:
    """장르 목록 전체를 돌려준다. (등록 form의 genre 선택 chip용)

    비유: 메뉴판 보여주기. 손님은 여기 적힌 것 중에서만 고를 수 있다.
    """
    # id순 ─ steam_genre_id는 String이라 정렬하면 "18"이 "2"보다 앞에 온다
    stmt = select(Genre).order_by(Genre.id)

    # scalars = 결과의 각 행에서 첫 칸(Genre 객체)만 꺼낸다
    # execute를 사용하면 (Genre,) Tuple로 감싸져 나온다
    result = await db.scalars(stmt)
    return list(result.all())

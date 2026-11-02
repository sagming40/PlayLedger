# app/routers/steam.py
# Steam 게임 검색 API ─ 등록 폼의 자동완성 (DESIGN 3.3절)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.steam_app import SteamApp
from app.schemas.steam import SteamAppRead
from app.services.steam import SEARCH_LIMIT, search_steam_apps

# 장르 API처럼 층 입구에 게이트를 둔다. 이 API를 쓰는 S-03은 어차피 로그인 뒤에 있다
router = APIRouter(
    prefix="/api/steam",
    tags=["steam"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/apps", response_model=list[SteamAppRead])
async def search_apps(
    q: str = Query(min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> list[SteamApp]:
    """영어 제목으로 후보를 찾는다. 미러가 비어 있으면 빈 목록이고 직접 입력은 그대로 된다"""
    # 공백뿐이면 전부 걸린다 ─ min_length는 공백도 글자로 센다
    if len(q.strip()) < 2:
        return []
    return await search_steam_apps(db, q, limit=SEARCH_LIMIT)

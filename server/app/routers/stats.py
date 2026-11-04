# app/routers/stats.py
# 통계 API ─ S-05가 한 번에 받는다. 계산은 전부 서버가 한다 (ARCHITECTURE 2장, DESIGN 3.5절)

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.stats import StatsRead
from app.services.stats import effective_today, get_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsRead)
async def read_stats(
    today: date | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatsRead:
    """내 통계. today = 브라우저의 오늘('YYYY-MM-DD') ─ 방치일수를 목록 카드와 같은 날짜로 센다"""
    return await get_stats(db, user_id=user.id, today=effective_today(today))

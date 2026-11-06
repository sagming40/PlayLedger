# app/routers/steam.py
# Steam 게임 검색(등록 폼 자동완성, DESIGN 3.3절) · 라이브러리 동기화(ARCHITECTURE 5.1절)

import logging
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import steam_sync_limiter
from app.deps import ensure_not_limited, get_current_user, get_db, get_http_client
from app.models.steam_app import SteamApp
from app.models.user import User
from app.schemas.common import CleanStr
from app.schemas.steam import SteamAppRead, SteamSyncRead
from app.services.steam import (
    SEARCH_LIMIT,
    SteamProfilePrivate,
    SteamUnavailable,
    fetch_owned_games,
    search_steam_apps,
)
from app.services.steam_sync import (
    SyncNotLinked,
    SyncTooSoon,
    merge_owned_games,
    retry_after_seconds,
)

logger = logging.getLogger("playledger")

# 장르 API처럼 층 입구에 게이트를 둔다. 이 API를 쓰는 S-03 · S-06은 어차피 로그인 뒤에 있다
router = APIRouter(
    prefix="/api/steam",
    tags=["steam"],
    dependencies=[Depends(get_current_user)],
)

NOT_LINKED = "Steam 계정을 먼저 연결해 주세요"
# R-01 ─ 원인과 고칠 곳을 같이 알려 준다 (REQUIREMENTS 7장)
PRIVATE_PROFILE = "Steam 프로필의 게임 세부 정보가 비공개라 라이브러리를 볼 수 없습니다. Steam 개인정보 설정에서 '게임 세부 정보'를 공개로 바꾼 뒤 다시 시도해 주세요"


def _too_soon(wait: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="방금 동기화했어요. 잠시 후 다시 시도해 주세요",
        headers={"Retry-After": str(wait)},
    )


@router.get("/apps", response_model=list[SteamAppRead])
async def search_apps(
    # Annotated로 묶어야 CleanStr의 검사도 함께 돈다. q: CleanStr = Query(...)로 쓰면 빠진다
    q: Annotated[CleanStr, Query(min_length=2, max_length=100)],
    db: AsyncSession = Depends(get_db),
) -> list[SteamApp]:
    """영어 제목으로 후보를 찾는다. 미러가 비어 있으면 빈 목록이고 직접 입력은 그대로 된다"""
    # 공백뿐이면 전부 걸린다 ─ min_length는 공백도 글자로 센다
    if len(q.strip()) < 2:
        return []
    return await search_steam_apps(db, q, limit=SEARCH_LIMIT)


@router.post("/sync", response_model=SteamSyncRead)
async def sync_library(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    http: httpx.AsyncClient = Depends(get_http_client),
):
    """내 Steam 라이브러리를 기록에 합친다 (F-12, ARCHITECTURE 5.1절)

    순서가 중요하다: 싼 검사 → Steam 호출(잠금 밖) → 잠그고 합치기(services/steam_sync.py)
    """
    key = str(user.id)
    ensure_not_limited(steam_sync_limiter, key)

    if user.steam_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NOT_LINKED)
    # 잠그기 전에 한 번 ─ 방금 했으면 Steam을 부르지도 않는다. 잠근 뒤에 merge가 한 번 더 본다
    wait = retry_after_seconds(user.steam_synced_at, datetime.now(timezone.utc))
    if wait:
        raise _too_soon(wait)

    steam_sync_limiter.hit(key)
    steam_id = user.steam_id
    # 외부 호출 동안 DB 연결을 붙들지 않는다 ─ 읽기만 한 트랜잭션을 닫는다 (routers/entries.py _steam_game과 같음)
    await db.commit()
    try:
        owned = await fetch_owned_games(http, settings.steam_api_key, steam_id)
    except SteamProfilePrivate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=PRIVATE_PROFILE) from None
    except SteamUnavailable as e:
        # 원인은 로그에만 ─ 키 문제(401 · 403)인지 Steam 장애인지는 사용자가 고칠 수 없다
        logger.warning("Steam 동기화: 보유 게임을 받지 못함 (%s)", e)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT if e.timeout else status.HTTP_502_BAD_GATEWAY,
            detail="Steam이 응답하지 않습니다. 잠시 후 다시 시도해 주세요",
        ) from None

    try:
        return await merge_owned_games(db, user.id, steam_id, owned)
    except SyncNotLinked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NOT_LINKED) from None
    except SyncTooSoon as e:
        raise _too_soon(e.retry_after) from None

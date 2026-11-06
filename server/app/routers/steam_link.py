# app/routers/steam_link.py
"""Steam 계정 연결 · 해제 (decisions/0015, ARCHITECTURE 5.4절)

쿠키 · 주소 · 상태 코드만 여기서 다룬다. 확인서 검사와 저장은 services/steam_openid.py가 맡는다

steam.py와 라우터를 나눈 이유 ─ 그쪽은 층 입구에서 access 토큰을 검사한다.
콜백은 Steam에서 돌아오는 페이지 이동이라 access 토큰이 실릴 수 없고, state 쿠키로 사람을 알아본다
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.oauth_state import STATE_TTL_SECONDS, consume_state, create_state
from app.deps import get_current_user, get_db, get_http_client
from app.models.user import User
from app.schemas.steam import SteamLinkStart
from app.services.steam_openid import (
    SteamOpenIDUnavailable,
    build_login_url,
    link_steam_account,
    unlink_steam_account,
    verify_assertion,
)

router = APIRouter(prefix="/api/steam/link", tags=["steam"])

STATE_PURPOSE = "steam_link"
STATE_COOKIE_NAME = "pl_steam_state"
# 콜백에만 실린다. 쿠키는 이름 + 경로로 구분되므로 지울 때도 같은 경로를 준다 (auth.py REFRESH_COOKIE_PATH와 같은 이유)
STATE_COOKIE_PATH = "/api/steam/link"


def _base_url() -> str:
    return settings.public_base_url.rstrip("/")


def _return_to(nonce: str) -> str:
    """Steam이 돌려보낼 주소. 서버가 정한다 ─ 요청 헤더로 만들지 않는다 (config.py public_base_url)"""
    return f"{_base_url()}{STATE_COOKIE_PATH}/callback?state={nonce}"


@router.post("/start", response_model=SteamLinkStart)
async def start_link(
    response: Response,
    current_user: User = Depends(get_current_user),
) -> SteamLinkStart:
    """연결을 시작한다 ─ state 쿠키를 심고 Steam 로그인 주소를 돌려준다

    이미 다른 Steam이 붙어 있으면 409 ─ 덮어쓰면 옛 Steam에서 받은 기록과 새 Steam이 섞인다. 해제한 뒤에 다시 연결한다
    """
    if current_user.steam_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 Steam 계정이 연결되어 있습니다. 연결을 해제한 뒤 다시 시도해 주세요",
        )

    nonce, state = create_state(current_user.id, STATE_PURPOSE)
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        secure=True,
        # Lax ─ Steam에서 우리 콜백으로 "넘어오는 페이지 이동"에도 실려야 한다. Strict면 빠진다 (ARCHITECTURE 4.3절)
        samesite="lax",
        path=STATE_COOKIE_PATH,
        max_age=STATE_TTL_SECONDS,
    )
    return SteamLinkStart(redirect_url=build_login_url(_return_to(nonce), realm=_base_url()))


@router.get("/callback", include_in_schema=False)
async def link_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> RedirectResponse:
    """Steam에서 돌아오는 곳. 결과는 설정 화면 주소의 steam=로 알린다

    페이지 이동이라 JSON 오류를 돌려줘도 사람이 볼 수 없다 ─ 어떤 경우든 설정 화면으로 보낸다
    linked 연결됨 · taken 다른 계정이 쓰는 중 · already 이미 다른 Steam이 붙어 있음 · unavailable Steam 응답 없음 · failed 그 밖의 전부
    """
    params = dict(request.query_params)
    nonce = params.get("state")
    user_id = consume_state(request.cookies.get(STATE_COOKIE_NAME), STATE_PURPOSE, nonce)

    result = "failed"
    if user_id is not None and nonce is not None:
        try:
            steam_id = await verify_assertion(http, params, _return_to(nonce))
        except SteamOpenIDUnavailable:
            result = "unavailable"
        else:
            if steam_id is not None:
                result = await link_steam_account(db, user_id, steam_id)

    # 303 ─ "다른 곳을 GET으로 보라". 새로고침해도 콜백이 다시 불리지 않는다
    redirect = RedirectResponse(f"{_base_url()}/settings?steam={result}", status_code=status.HTTP_303_SEE_OTHER)
    # 성공이든 실패든 쪽지는 한 번 쓰면 버린다
    redirect.delete_cookie(
        key=STATE_COOKIE_NAME, path=STATE_COOKIE_PATH, httponly=True, secure=True, samesite="lax"
    )
    return redirect


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def unlink(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """연결을 푼다. 기록은 남는다. 이미 풀려 있어도 204 (logout과 같은 멱등성)"""
    await unlink_steam_account(db, current_user.id)

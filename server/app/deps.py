# app/deps.py
"""요청마다 필요한 준비물. 계층이 아니라, 계층을 가로지른다. (ARCHITECTURE 2.2절)"""

from collections.abc import AsyncGenerator

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.core.rate_limit import RateLimiter
from app.core.security import decode_access_token
from app.models.user import User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """요청 하나가 사용할 DB 세션을 빌려주고, 사용이 끝나면 반납한다.

    return이 아닌 yield을 사용한 것이 핵심이다.
    yield ─ "여기까지 만들어서 건네주고, 사용하는 쪽이 끝나면 이 줄 다음부터 이어서 실행"
    비유: 도서관 사서가 책을 대여해주고 반납되면 다시 서가 제자리에 꽂아두는 것과 같다.
    async with가 반납(close)을 자동으로 맡는다.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """외부 API(Steam)를 부를 때 쓰는 전화기. 테스트는 이것만 바꿔치기해 진짜 Steam을 부르지 않는다

    서버가 켜질 때 하나 만들어 돌려 쓴다 (main.py lifespan)
    """
    return request.app.state.http


def client_ip(request: Request) -> str:
    """요청을 보낸 곳. 프록시 뒤에서는 uvicorn --proxy-headers가 진짜 IP로 바꿔 준다 (M5)"""
    return request.client.host if request.client else "unknown"


def ensure_not_limited(limiter: RateLimiter, key: str) -> None:
    """횟수를 넘겼으면 429. 몇 초 뒤에 다시 오라고 알려 준다"""
    wait = limiter.retry_after(key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도해 주세요",
            headers={"Retry-After": str(wait)},
        )


def reject_other_sites(request: Request) -> None:
    """쿠키로 인증하는 경로(refresh · logout)는 우리 화면에서 온 요청만 받는다

    SameSite=Strict는 다른 사이트만 막는다. 같은 sagming.com 아래 다른 앱이 뚫리면 그쪽에서 온 요청에는 쿠키가 붙는다
    브라우저가 스스로 적어 주는 Sec-Fetch-Site는 페이지의 코드가 바꿀 수 없다. 이 헤더가 없는 도구(curl)는 쿠키도 직접 넣어야 하니 막을 이유가 없다
    """
    if request.headers.get("sec-fetch-site") in ("cross-site", "same-site"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="허용되지 않은 요청입니다",
        )


# Authorization Header에서 "Bearer {토큰}"을 꺼내주는 도구
# auto_error=False, Header가 없을 때 이 도구가 멋대로 403을 throw하지 않게 막는다
# 기본값일 경우 ─ 403 → PlayLedger 규칙 ─ "인증 실패는 전부 401"
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """access 토큰을 확인하고 '지금 요청한 사람'을 돌려준다.

    비유: 놀이기구 앞 직원. 손목 밴드(access 토큰)의 도장과 기한을 확인하고
    "몇 번 손님"인지 확정해서 들여보낸다.
    보호된 API는 전부 이 직원을 거쳐야 실행된다. (ARCHITECTURE 3.8절 1번 방어선)
    """
    # 실패 사유를 하나로 통일한다. 만료 / 위조 / 없는 사용자를 구분해 알려주면 HINT가 된다.
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증이 필요합니다",
        headers={"WWW-Authenticate": "Bearer"},   # 표준: "Bearer 방식으로 인증하라"는 안내
    )

    if credentials is None:
        raise credentials_error

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:   # 서명 위조 · 만료 · 형식 오류가 전부 이 곳으로 모인다
        raise credentials_error

    # 토큰이 진짜여도 DB를 한 번 확인한다. 발급 후에 계정이 삭제되었을 수도 있다.
    # 종이(토큰)만 믿으면 존재하지 않는 사람이 통과한다.
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_error

    return user

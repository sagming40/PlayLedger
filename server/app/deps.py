# app/deps.py
"""요청마다 필요한 준비물. 계층이 아니라, 계층을 가로지른다. (ARCHITECTURE 2.2절)"""

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
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
    보호된 API는 전부 이 직원을 거쳐야 실행된다. (문서 02 ─ 4.2절 1번 방어선)
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

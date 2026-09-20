# app/routers/auth.py
"""인증 관련 URL. 판단 X. 넘기기만. (ARCHITECTURE 2.2절)"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token,
    hash_password, hash_refresh_token, verify_password,
)
from app.deps import get_db
from app.models.user import RefreshToken, User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead

# prefix를 여기 한 번 붙이면 아래 함수들은 그 뒷부분만 적으면 된다.
# 나중에 주소 체계가 바뀌어도 이 한 줄만 수정하면 된다.
router = APIRouter(prefix="/api/auth", tags=["auth"])

# 존재하지 않는 계정으로 Login을 시도하더라도 hashing을 1번 돌리기 위한 가짜 hash
# 결과는 항상 False. 오직 시간을 쓰는 용도이다. 서버 시작 시 최초 1회만 생성하여 재사용한다.
DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-defense")

# Cookie 이름에 project 접두사를 붙인다.
# Browser Cookie는 port를 구분하지 않으므로, 동일한 localhost를 사용하는
# 다른 project와 서로 덮어쓸 수 있다.
REFRESH_COOKIE_NAME = "pl_refresh_token"


@router.post(
    "/register",
    response_model=UserRead,               # 이 모양 안에 해당되지 않으면 밖으로 나가지 못한다
    status_code=status.HTTP_201_CREATED,   # "만들었다"는 201 → 200이 아니다
)
async def register(
    payload: UserCreate,                   # 심사에 통과한 요청들만 여기에 들어올 수 있다
    db: AsyncSession = Depends(get_db)     # 도서관 사서에게 책 한 권 빌리기
) -> User:
    """새 계정을 만든다"""

    # 1차 확인 ─ 이미 사용중인 email 인지 먼저 물어본다
    # 흔한 경우를 메시지로 처리하기 위한 것이다. 방어선은 아니다.
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다",
        )

    user = User(
        email=payload.email,                             # schema에서 이미 소문자로 정규화됨
        password_hash=hash_password(payload.password),   # 원문은 여기서 버려진다
        nickname=payload.nickname,
    )

    db.add(user)   # DB에 아직 도착하지 않았다. 장바구니에만 담긴 상태.
    try:
        await db.commit()   # 계산대. 여기서 실제 query가(INSERT) 나간다.
    except IntegrityError:
        # 2차 방어선 ─ 1차 확인과 INSERT 사이 그 찰나에 다른 요청이 먼저 가입한 경우
        # DB의 UNIQUE 제약이 막아주고, 그 응답이 IntegrityError이다.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다",
        )

    # DB가 채워준 값(id, created_at)을 객체로 다시 읽어온다.
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, response: Response,  # cookie를 심을 응답 객체
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Email과 Password를 확인하고 Token 2개를 발급한다."""
    
    # 가입 때와 같은 규칙으로 정규화해야 찾을 수 있다.
    # LoginRequest에는 validator가 없으므로 직접 맞춘다.
    email = payload.email.strip().lower()
    
    user = await db.scalar(select(User).where(User.email == email))
    
    # ── 실패 경로 2가지를 한 덩어리로 처리한다 ──
    # 계정이 없거나 (Discord 전용 계정이라 비밀번호가 없는 경우 포함),
    # 비밀번호 오류거나 외부에서는 구분할 수 없어야 한다.
    if user is None or user.password_hash is None:
        # 계정이 없어도 hashing을 1번 돌려 응답 timing을 맞춘다.
        # 식당에서 재료가 없어도 모든 손님을 동일한 시간동안 기다리게 하는 것과 같다.
        # 응답 시간만으로 "없는 계정"임을 유추할 수 있게 되는 경우를 대비한다.
        verify_password(payload.password, DUMMY_PASSWORD_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )
    
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )
    
    # ─── ↓ 본인 확인이 끝난 상태 ───
    
    access_token = create_access_token(user.id)
    
    # refresh 토큰은 원문을 사용자에게 발급하고, DB에는 HASH만 남긴다.
    refresh_token = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()
    
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,        # 원문. DB에 저장된 값은 원문의 HASH이다.
        httponly=True,              # JS가 읽지 못한다 → XSS로 탈취 불가
        secure=True,                # HTTPS에서만 전송 (localhost는 예외로 허용됨)
        samesite="strict",          # 다른 사이트에서 시작된 요청에는 붙지 않는다.
        path="/api/auth",           # 인증 API에만 붙는다. 게임 목록 요청엔 붙지 않음
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,   #초 단위
    )
    
    return TokenResponse(access_token=access_token)

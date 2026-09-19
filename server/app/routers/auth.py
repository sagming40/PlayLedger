# app/routers/auth.py
"""인증 관련 URL. 판단 X. 넘기기만. (ARCHITECTURE 2.2절)"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.deps import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead

# prefix를 여기 한 번 붙이면 아래 함수들은 그 뒷부분만 적으면 된다.
# 나중에 주소 체계가 바뀌어도 이 한 줄만 수정하면 된다.
router = APIRouter(prefix="/api/auth", tags=["auth"])


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

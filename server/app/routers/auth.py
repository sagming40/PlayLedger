# app/routers/auth.py
"""인증 관련 URL. 판단 X. 넘기기만. (ARCHITECTURE 2.2절)"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token,
    hash_password, hash_refresh_token, verify_password,
)
from app.deps import get_current_user, get_db
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

# Cookie는 (이름 · 도메인 · 경로) 3가지로 식별된다.
# 삭제할 때도 동일한 경로를 줘야 한다. ─ 상수로 뽑아둠
REFRESH_COOKIE_PATH = "/api/auth"


def set_refresh_cookie(response: Response, token: str) -> None:
    """refresh 토큰을 cookie로 심는다.

    login과 refresh 2곳에서 동일한 속성으로 심어야 하므로 한 군데에 모아둔다.
    비유: 도장을 두 창구에서 각각 따로 파면, 똑같은 모양으로 파달라고 요청 했더라도
    100% 동일할 수 없다. (미세하게라도 서로 달라질 수 밖에 없음)
    """
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,                # 원문. DB에 저장된 값은 원문의 HASH이다.
        httponly=True,              # JS가 읽지 못한다 → XSS로 탈취 불가
        secure=True,                # HTTPS에서만 전송 (localhost는 예외로 허용됨)
        samesite="strict",          # 다른 사이트에서 시작된 요청에는 붙지 않는다.
        path=REFRESH_COOKIE_PATH,   # 인증 API에만 붙는다. game 목록 요청엔 붙지 않음
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,  # 초 단위
    )


def clear_refresh_cookie(response: Response) -> None:
    """refresh 쿠키를 지운다.

    경로를 반드시 심을 때와 똑같이 줘야 한다.
    Browser는 Cookie를 '이름'이 아니라 '이름 + 도메인 + 경로'로 구분하기 때문에,
    경로가 다르면 '다른 쿠키는 지워야 한다'는 요청이 되어 원본이 그대로 살아남는다.
    비유: 동일한 이름의 사물함이 층마다 있는데, 층수를 밝히지 않고 "비워달라"고 하는 것
    """
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite="strict",
    )


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

    set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,    # cookie를 읽을 요청 객체
    response: Response,  # 새 cookie를 심을 응답 객체
    db: AsyncSession = Depends(get_db),
) -> TokenResponse | JSONResponse:
    """refresh 토큰을 새로운 토큰 한 쌍으로 교환한다 (rotation, 문서 02 ─ 4.1절)"""

    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 없습니다",
        )

    token_hash = hash_refresh_token(raw_token)
    now = datetime.now(timezone.utc)

    # 찾기 + 유효성 확인 + 폐기를 UPDATE 한 문장으로 처리한다.
    # 각각 갈라버리면 그 갈라진 틈으로 동일한 토큰이 중복 통과할 수 있다.
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),       # 아직 폐기되지 않음
            RefreshToken.expires_at > now,           # 아직 만료되지 않음
        )
        .values(revoked_at=now)
        .returning(RefreshToken.user_id)             # 바꾼 행의 주인을 돌려받는다
        # session 메모리에 올라온 객체를 DB와 맞추는 option이다.
        # 이 요청은 방금 시작된 요청이라 session에 맞출 대상이 아무것도 없다.
        .execution_options(synchronize_session=False)
    )
    user_id = result.scalar_one_or_none()   # 1행이면 값, 0행이면 None

    # ──── 실패 경로 ──── 왜 실패했는지 한 번 더 확인한다
    if user_id is None:
        used = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

        # 존재하지만 이미 폐기된 토큰 = 정상 흐름에선 나올 수 없는 상황
        # 누군가 옛 토큰을 들고 왔다는 신호다. (문서 03 ─ 2.2절)
        if used is not None and used.revoked_at is not None:
            # 이 유저의 살아 있는 토큰을 전부 폐기한다.
            # 공격자가 이미 받아간 새 토큰 까지 같이 죽이기 위함이다.
            await db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == used.user_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
                .execution_options(synchronize_session=False)
            )

        await db.commit()   # 폐기 기록을 실제로 남긴다

        # HTTPException으로 raise하면 인자로 받은 response는 버려진다.
        # (예외 처리기가 응답을 새로 만들기 때문. 비상구로 나가면 짐이 안 실린다)
        # 그래서 실패 응답을 직접 만들고, 쿠키 삭제를 그 위에 얹어서 return한다.
        failure = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "다시 로그인해 주세요"},
        )
        clear_refresh_cookie(failure)
        return failure

    # ─── ↓ 옛 토큰이 방금 폐기된 상태. 새 토큰을 내어준다 ───

    new_refresh_token = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(new_refresh_token),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()

    set_refresh_cookie(response, new_refresh_token)
    return TokenResponse(access_token=create_access_token(user_id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> None:
    """refresh 토큰을 폐기하고 cookie를 지운다

    get_current_user를 붙이지 않는다.
    access 토큰이 만료된 사람도 logout할 수 있어야 한다.
    """

    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)

    # cookie가 없어도 error를 내지 않는다.
    # 로그아웃의 목적은 '로그아웃이 된 상태'지 '토큰 찾기'가 아니다.
    # 몇번을 눌러도 결과가 같다.(멱등성) 엘리베이터 버튼을 또 눌러도 아무도 화내는 사람이 없는 것처럼
    if raw_token is not None:
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == hash_refresh_token(raw_token),
                RefreshToken.revoked_at.is_(None),   # 이미 폐기된 행의 시각은 보존
            )
            .values(revoked_at=datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        await db.commit()

    clear_refresh_cookie(response)


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    """지금 로그인한 사용자 정보. 인증 검사는 get_current_user가 전부 맡는다."""
    return current_user

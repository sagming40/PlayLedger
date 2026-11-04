# app/routers/auth.py
"""인증 관련 URL. 판단 X. 넘기기만. (ARCHITECTURE 2.2절)

쿠키 · 상태 코드 · 요청 제한만 여기서 다룬다. 계정과 토큰의 판단은 services/auth.py가 맡는다
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import (
    login_failure_limiter,
    login_ip_limiter,
    register_limiter,
)
from app.core.security import create_access_token
from app.deps import client_ip, ensure_not_limited, get_current_user, get_db, reject_other_sites
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead
from app.services.auth import (
    authenticate,
    issue_refresh_token,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)

# prefix를 여기 한 번 붙이면 아래 함수들은 그 뒷부분만 적으면 된다.
# 나중에 주소 체계가 바뀌어도 이 한 줄만 수정하면 된다.
router = APIRouter(prefix="/api/auth", tags=["auth"])

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
    request: Request,
    db: AsyncSession = Depends(get_db),    # 도서관 사서에게 책 한 권 빌리기
) -> User:
    """새 계정을 만든다"""
    ip = client_ip(request)
    ensure_not_limited(register_limiter, ip)
    register_limiter.hit(ip)

    user = await register_user(db, payload)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다",
        )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,   # cookie를 심을 응답 객체
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Email과 Password를 확인하고 Token 2개를 발급한다."""
    ip = client_ip(request)
    failure_key = f"{ip}|{payload.email}"
    # 해시를 돌리기 전에 막는다 ─ 해시가 비싸서 그 자체가 공격 대상이 된다
    ensure_not_limited(login_ip_limiter, ip)
    ensure_not_limited(login_failure_limiter, failure_key)
    login_ip_limiter.hit(ip)

    user = await authenticate(db, payload.email, payload.password)
    if user is None:
        login_failure_limiter.hit(failure_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    # ─── ↓ 본인 확인이 끝난 상태 ───
    login_failure_limiter.reset(failure_key)
    refresh_token = await issue_refresh_token(db, user.id)
    set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(reject_other_sites)])
async def refresh(
    request: Request,    # cookie를 읽을 요청 객체
    response: Response,  # 새 cookie를 심을 응답 객체
    db: AsyncSession = Depends(get_db),
) -> TokenResponse | JSONResponse:
    """refresh 토큰을 새로운 토큰 한 쌍으로 교환한다 (rotation, ARCHITECTURE 3.3절)"""

    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 없습니다",
        )

    rotated = await rotate_refresh_token(db, raw_token)
    if rotated is None:
        # HTTPException으로 raise하면 인자로 받은 response는 버려진다.
        # (예외 처리기가 응답을 새로 만들기 때문. 비상구로 나가면 짐이 안 실린다)
        # 그래서 실패 응답을 직접 만들고, 쿠키 삭제를 그 위에 얹어서 return한다.
        failure = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "다시 로그인해 주세요"},
        )
        clear_refresh_cookie(failure)
        return failure

    user_id, new_refresh_token = rotated
    set_refresh_cookie(response, new_refresh_token)
    return TokenResponse(access_token=create_access_token(user_id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(reject_other_sites)])
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
        await revoke_refresh_token(db, raw_token)

    clear_refresh_cookie(response)


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    """지금 로그인한 사용자 정보. 인증 검사는 get_current_user가 전부 맡는다."""
    return current_user

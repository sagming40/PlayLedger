# app/services/auth.py
"""계정 · 토큰의 판단과 저장 (ARCHITECTURE 2.2절). 쿠키 · 상태 코드는 Router가 맡는다

여기서 실패는 전부 None · False로 돌려준다 ─ 어떤 응답으로 바꿀지는 Router가 정한다
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_refresh_token,
    hash_password_async,
    hash_password,
    hash_refresh_token,
    verify_password_async,
)
from app.models.entry import Entry
from app.models.game import Game
from app.models.user import RefreshToken, User
from app.schemas.common import contains_broken_text
from app.schemas.user import UserCreate

# 존재하지 않는 계정으로 Login을 시도하더라도 hashing을 1번 돌리기 위한 가짜 hash
# 결과는 항상 False. 오직 시간을 쓰는 용도이다. 서버 시작 시 최초 1회만 생성하여 재사용한다.
DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-defense")

# RFC 5321의 이메일 길이 상한. 그보다 긴 값은 DB에 물어볼 필요도 없다
MAX_EMAIL_LENGTH = 254


async def register_user(db: AsyncSession, payload: UserCreate) -> User | None:
    """새 계정을 만든다. 이미 쓰는 이메일이면 None"""
    # 1차 확인 ─ 이미 사용중인 email 인지 먼저 물어본다
    # 흔한 경우를 메시지로 처리하기 위한 것이다. 방어선은 아니다.
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        return None

    user = User(
        email=payload.email,                                    # schema에서 이미 소문자로 정규화됨
        password_hash=await hash_password_async(payload.password),   # 원문은 여기서 버려진다
        nickname=payload.nickname,
    )
    db.add(user)   # DB에 아직 도착하지 않았다. 장바구니에만 담긴 상태.
    try:
        await db.commit()   # 계산대. 여기서 실제 query가(INSERT) 나간다.
    except IntegrityError:
        # 2차 방어선 ─ 1차 확인과 INSERT 사이 그 찰나에 다른 요청이 먼저 가입한 경우
        # DB의 UNIQUE 제약이 막아주고, 그 응답이 IntegrityError이다.
        await db.rollback()
        return None

    # DB가 채워준 값(id, created_at)을 객체로 다시 읽어온다.
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    """이메일과 비밀번호를 확인한다. 실패 이유는 밖으로 나가지 않는다

    계정이 없거나 (Discord 전용 계정이라 비밀번호가 없는 경우 포함), 비밀번호 오류거나 외부에서는 구분할 수 없어야 한다.
    """
    # 깨진 글자 · 터무니없는 길이는 DB에 물어보면 500이다. 없는 계정과 같이 다룬다
    user = None
    if len(email) <= MAX_EMAIL_LENGTH and not contains_broken_text(email):
        user = await db.scalar(select(User).where(User.email == email))

    if user is None or user.password_hash is None:
        # 계정이 없어도 hashing을 1번 돌려 응답 timing을 맞춘다.
        # 식당에서 재료가 없어도 모든 손님을 동일한 시간동안 기다리게 하는 것과 같다.
        # 응답 시간만으로 "없는 계정"임을 유추할 수 있게 되는 경우를 대비한다.
        await verify_password_async(password, DUMMY_PASSWORD_HASH)
        return None

    return user if await verify_password_async(password, user.password_hash) else None


def _new_refresh_row(user_id: int, now: datetime) -> tuple[str, RefreshToken]:
    """토큰 원문과 저장할 행. 원문은 사용자에게만 주고, DB에는 HASH만 남긴다"""
    raw = create_refresh_token()
    return raw, RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )


async def delete_account(db: AsyncSession, user_id: int) -> None:
    """계정과 그 사람의 흔적을 지운다. 공유하는 Steam 게임은 남는다 (decisions/0011)

    순서가 중요하다 ─ entries.game_id가 RESTRICT라 기록을 먼저 지워야 게임을 지울 수 있다
    refresh 토큰은 users FK CASCADE로 함께 지워진다
    """
    # 먼저 잠근다 ─ 다른 탭에서 등록 중이면 끝나기를 기다렸다가 그 기록까지 본다
    # 이후의 등록은 FK 검사가 이 잠금을 기다리다가 실패한다
    await db.execute(select(User.id).where(User.id == user_id).with_for_update())
    await db.execute(delete(Entry).where(Entry.user_id == user_id))
    await db.execute(delete(Game).where(Game.owner_user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


async def issue_refresh_token(db: AsyncSession, user_id: int) -> str:
    """로그인 때 새 refresh 토큰을 발급한다"""
    now = datetime.now(timezone.utc)
    # 만료된 행은 재사용 감지에도 쓸 일이 없다 ─ 로그인할 때 그 사람 몫만 치운다 (F-28)
    # 폐기됐지만 아직 안 만료된 행은 남긴다. 그것이 재사용 감지의 근거다
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.expires_at <= now))
    raw, row = _new_refresh_row(user_id, now)
    db.add(row)
    await db.commit()
    return raw


async def rotate_refresh_token(db: AsyncSession, raw_token: str) -> tuple[int, str] | None:
    """refresh 토큰을 새 것으로 바꾼다 (rotation, ARCHITECTURE 3.3절). (user_id, 새 토큰), 실패하면 None"""
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
        used = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

        # 존재하지만 이미 폐기된 토큰 = 정상 흐름에선 나올 수 없는 상황
        # 누군가 옛 토큰을 들고 왔다는 신호다. (DATA_MODEL 2.2절)
        if used is not None and used.revoked_at is not None:
            # 이 유저의 살아 있는 토큰을 전부 폐기한다.
            # 공격자가 이미 받아간 새 토큰 까지 같이 죽이기 위함이다.
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == used.user_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=now)
                .execution_options(synchronize_session=False)
            )
        await db.commit()   # 폐기 기록을 실제로 남긴다
        return None

    # ─── ↓ 옛 토큰이 방금 폐기된 상태. 새 토큰을 내어준다 ───
    raw, row = _new_refresh_row(user_id, now)
    db.add(row)
    await db.commit()
    return user_id, raw


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    """로그아웃 ─ 이 토큰만 폐기한다. 이미 폐기된 행의 시각은 보존"""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token), RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    await db.commit()

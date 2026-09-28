# ============================================================
# user / refresh_tokens
# 로그인하는 사람, 그 유저에게 발급된 재발급 티켓
# ============================================================

from datetime import datetime

from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Discord 전용 계정은 이메일이 없을 수도 있어서 NULL 허용
    # 저장 전 소문자 정규화는 server가 담당한다. (ERD 2.1절)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    
    # 비밀번호 원문은 절대 들어오지 않는다. hash만 허용
    password_hash: Mapped[str | None] = mapped_column(String(255))
    
    nickname: Mapped[str] = mapped_column(String(30))
    
    # Steam ID는 64bit Integer지만 String으로 받는다. (ERD 2.0절 공통 규칙)
    steam_id: Mapped[str | None] = mapped_column(String(20), unique=True)
    
    # server_default = 값을 주지 않으면 DB가 자동으로 지금 시각을 넣는다
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    __table_args__ = (
        # 비밀번호로 로그인하는 계정은 이메일이 반드시 있어야 한다
        # 서버 코드를 거치지 않고 직접 SQL로 입력해도 DB가 막아준다
        CheckConstraint(
            "password_hash IS NULL OR email IS NOT NULL",
            name="password_needs_email",
        ),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # ondelete="CASCADE" = 부모(users)가 지워지면 DB가 이 행도 같이 지운다
    # index=True는 "해당 사용자의 tokens 전부 폐기" 조회용 (ERD 4장)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    
    # SHA-256 hash는 16진수 64글자로 항상 길이가 고정이다
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # 지우지 않고 폐기 시각을 남긴다. NULL이면 아직 유효 (ERD 2.2절)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

# ============================================================
# entries ─ 특정 사용자가 특정 게임을 보유한 기록
# PlayLedger의 중심 테이블 (ERD 2.6절)
# ============================================================

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index,
    SmallInteger, String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# TYPE 표시용 ─ 실행 시에는 이 import가 무시된다
# 비유: 설계도에 "이 곳이 Game이 들어올 자리다"라고 표시만 해두는 것. 실제 부품은 조립할 때 가져온다
# 이유: game.py와 entry.py가 서로를 import 하게 되면 순환 참조가 생길 수 있다
if TYPE_CHECKING:
    from app.models.game import Game


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 유저가 탈퇴를 하면 그 유저의 기록도 함께 삭제된다
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    # 게임은 여러 사용자가 공유하는 마스터 데이터이기 때문에 쉽게 삭제되면 안된다.
    # RESTRICT = 누군가가 참조 중이면 삭제 자체를 거부한다. (ERD 2.0절)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="RESTRICT")
    )

    # 진행 상태 ─ ENUM 타입 대신 varchar + CHECK (ERD 2.0절 공통 규칙)
    status: Mapped[str] = mapped_column(String(10))

    purchased_at: Mapped[date | None]

    # 원 단위 정수 ─ 소수점이 필요 없다
    purchase_price: Mapped[int | None]

    # 분 단위 정수 ─ Steam이 분(minute)을 반환하고, 시간(hour) 소수로 변환하면
    # 증가분 계산에서 반올림 오차가 쌓인다 (ERD 2.6절)
    playtime_minutes: Mapped[int] = mapped_column(server_default="0")

    # "평가되지 않음(NULL)"과 "0"점은 엄연히 다르다. 평균 계산 시 NULL은 자동으로 제외된다.
    rating: Mapped[int | None] = mapped_column(SmallInteger)

    review: Mapped[str | None] = mapped_column(String(200))

    # 이 컬럼 하나가 "Steam이 수기 입력을 덮어 쓰는 문제"를 통째로 막는다
    source: Mapped[str] = mapped_column(String(10), server_default="MANUAL")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # onupdate = 행이 수정될 때마다 SQLAlchemy가 현재 시각으로 갱신한다
    # PostgreSQL엔 MariaDB의 ON UPDATE CURRENT_TIMESTAMP가 없어서 ORM이 대신한다
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # entry.game으로 게임 정보(제목, 장르)를 꺼낸다
    # "Game"을 따옴표로 사용하는 이유: 실행 시점엔 위 import가 없으므로 이름(String)으로 찾게 한다
    game: Mapped["Game"] = relationship()

    __table_args__ = (
        # 같은 사용자가 같은 게임을 중복 등록할 수 없다
        # UNIQUE는 INDEX 역할도 겸하기 때문에 유저별 조회에도 사용된다 (ERD 4장)
        UniqueConstraint("user_id", "game_id"),

        # 상태별 필터링이 가장 잦은 조회 (ERD 4장)
        Index("ix_entries_user_status", "user_id", "status"),

        # 최후 방어선 ─ 아래 5개 CHECK는 서버 코드를 거치지 않는 경로로도 막는다.
        CheckConstraint(
            "status IN ('BACKLOG', 'PLAYING', 'CLEARED', 'ON_HOLD', 'DROPPED')",
            name="status_allowed",
        ),
        CheckConstraint("source IN ('MANUAL', 'STEAM')", name="source_allowed"),
        CheckConstraint("purchase_price >= 0", name="price_not_negative"),
        CheckConstraint("playtime_minutes >= 0", name="playtime_not_negative"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    )

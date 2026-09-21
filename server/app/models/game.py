# ============================================================
# games / genres / game_genres
# 게임 마스터 데이터 ─ 모든 사용자가 공유한다 (ERD 2.4절)
# ============================================================

from datetime import date, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# ────── 연결 테이블 (N:M) ──────
# class가 아닌 Table 객체 ─ column이 두 개뿐이고 적을 정보가 없기 때문
game_genres = Table(
    "game_genres",
    Base.metadata,  # class가 아니라 직접 등록해야 한다
    Column(
        "game_id",
        Integer,
        ForeignKey("games.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        Integer,
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,  # 장르로 게임 찾기 조회용 (ERD 4장)
    ),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    # Steam 공식 장르 ID (ERD 2.5절) 추후 Steam 동기화 시 장르를 자동으로 붙이는 기준이다.
    # 이름표(name)는 언어설정 마다 바뀌지만 사물함 번호(ID)는 바뀌지 않는 것과 같다.
    # Mapped[str]에 Optional(| None)이 없으므로 NOT NULL로 만들어진다.
    steam_genre_id: Mapped[str] = mapped_column(String(10), unique=True)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 화면에 보여줄 원본 제목
    title: Mapped[str] = mapped_column(String(200))

    # 중복 판별용 정규화 제목. 공백 제거 → 소문자 → 특수문자 제거.
    # 사람이 다루게 하지 않고 항상 서버에서 계산한다
    title_norm: Mapped[str] = mapped_column(String(200), index=True)

    # 수동 등록 게임은 Steam ID가 없다
    steam_appid: Mapped[int | None] = mapped_column(unique=True)

    released_at: Mapped[date | None]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

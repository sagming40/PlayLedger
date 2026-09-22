# ============================================================
# games / genres / game_genres
# 게임 마스터 데이터 ─ 모든 사용자가 공유한다 (ERD 2.4절)
# ============================================================

from datetime import date, datetime

from sqlalchemy import (
    Column, DateTime, ForeignKey, Index,
    Integer, String, Table, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # 수동 등록 게임(steam_appid 없음)끼리만 title_norm 중복을 금지한다 (ERD 2.4절)
    # 비유: 주민번호(steam_appid)가 없는 손님은 이름으로만 구분이 가능하므로 동일한 이름이
    # 중복으로 적히면 구분할 방법이 없다. 주민번호가 있는 손님은 번호로 구분가능 하므로 이 규칙에서 제외시킨다.
    # UNIQUE '제약'이 아니라 UNIQUE '인덱스'로 만든다
    # ─ PostgreSQL 특성 상 제약에는 WHERE 절을 붙일 수 없다.
    __table_args__ = (
        Index(
            "uq_games_title_norm_manual",
            "title_norm",
            unique=True,
            postgresql_where=text("steam_appid IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # 화면에 보여줄 원본 제목
    title: Mapped[str] = mapped_column(String(200))

    # 중복 판별용 정규화 제목. NFKC → casefold → 글자·숫자만 (app/core/normalize.py)
    # 사람이 다루게 하지 않고 항상 서버에서 계산한다
    title_norm: Mapped[str] = mapped_column(String(200), index=True)

    # 수동 등록 게임은 Steam ID가 없다
    steam_appid: Mapped[int | None] = mapped_column(unique=True)

    released_at: Mapped[date | None]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Python 안내선 ─ game.genres로 연결된 Genre 목록을 꺼낸다 (DB 구조는 그대로)
    # secondary = 요청 중간에 연결 테이블(game_genres)을 거쳐 찾아가게 하는 것
    # order_by = 장르 목록 API와 같은 순서(id순)로 나오게 한다
    genres: Mapped[list["Genre"]] = relationship(
        secondary=game_genres, order_by="Genre.id"
    )

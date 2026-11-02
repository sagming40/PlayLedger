# ============================================================
# steam_apps ─ Steam 게임 목록의 사본 (DATA_MODEL 2.9절)
# 검색 전용 창고. 고른 게임만 find_or_create_game을 거쳐 games로 들어간다
# ============================================================

from sqlalchemy import Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SteamApp(Base):
    __tablename__ = "steam_apps"

    # Steam이 정한 번호를 그대로 쓴다 ─ DB가 번호를 새로 매기지 않는다
    # 비유: 도서관 자체 번호가 아니라 책에 이미 찍혀 있는 ISBN을 쓰는 것
    appid: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)

    # 길이를 제한하지 않는다 ─ Steam에 414자짜리 이름이 실제로 있다 (decisions/0008)
    # games.title의 200자 제한은 등록할 때 검사한다
    name: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        # GIN + gin_trgm_ops ─ 제목을 세 글자씩 쪼개 색인한다 (DATA_MODEL 4장)
        # 비유: 책 맨 뒤의 찾아보기. 제목 첫 글자로만 찾는 일반 인덱스와 달리 중간 글자로도 찾는다
        Index(
            "ix_steam_apps_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

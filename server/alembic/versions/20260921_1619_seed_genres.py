"""seed genres

Revision ID: 43b0fb42aaa8
Revises: bfea2aef6bcb
Create Date: 2026-09-21 16:19:52.444920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43b0fb42aaa8'
down_revision: Union[str, Sequence[str], None] = 'bfea2aef6bcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ─── MIGRATION 시점의 genres의 "snapshot" ───
# app.models의 Genre를 import하지 않고, 모양을 이 파일에 따로 적는다
# Model은 앞으로 계속 바뀌지만(실물), 이 파일은 2026-09-21의 모습 그대로 고정되어야 하기 때문이다
# 소문자 sa.table은 출석부(Base.metadata)에 등록되지 않는 가벼운 frame이라
# autogenerate가 진짜 Table로 착각할 경우도 없다.
genres_table = sa.table(
    "genres",
    sa.column("name", sa.String),
    sa.column("steam_genre_id", sa.String),
)

# ERD 2.5절 장르 목록과 같은 순서 · 값 (문서가 원본. 파일은 복사본)
# id는 적지 않는다 ─ SERIAL이 번호를 자동으로 매기도록 둔다.
GENRES = [
    {"steam_genre_id": "1", "name": "액션"},
    {"steam_genre_id": "2", "name": "전략"},
    {"steam_genre_id": "3", "name": "RPG"},
    {"steam_genre_id": "4", "name": "캐주얼"},
    {"steam_genre_id": "9", "name": "레이싱"},
    {"steam_genre_id": "18", "name": "스포츠"},
    {"steam_genre_id": "25", "name": "어드벤처"},
    {"steam_genre_id": "28", "name": "시뮬레이션"},
]


def upgrade() -> None:
    """8개 Genre를 넣는다"""
    # 택배 여러 개를 한 번에 트럭에 싣는 것 ─ row마다 각각 INSERT를 호출하지 않는다
    op.bulk_insert(genres_table, GENRES)


def downgrade() -> None:
    """파일에 적힌 Genre만 되돌린다"""
    # Table을 통으로 비우지(DELETE FROM genres) 않고, 직접 지정한 8개만 골라서 지운다
    # 추후 다른 MIGRATION이 Genre를 Add해도 지정한 8개 Genre는 건드리지 않도록 한다
    seeded_ids = [g["steam_genre_id"] for g in GENRES]
    op.execute(
        genres_table.delete().where(genres_table.c.steam_genre_id.in_(seeded_ids))
    )

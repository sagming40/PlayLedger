"""separate manual games by owner

Revision ID: 8c2f4a71d9e3
Revises: 471f3f2597b9
Create Date: 2026-11-04 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c2f4a71d9e3'
down_revision: Union[str, Sequence[str], None] = '471f3f2597b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """수동 게임을 기록의 주인별로 나눈다 (decisions/0011)

    첫 기록의 주인이 원래 행을 갖고, 나머지 사람은 제목과 장르를 복사한 자기 행을 받는다.
    기록이 없는 수동 게임은 주인을 정할 수 없고 아무도 보지 않으니 지운다.
    """
    op.add_column('games', sa.Column('owner_user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_games_owner_user_id'), 'games', ['owner_user_id'], unique=False)
    op.create_foreign_key(
        op.f('fk_games_owner_user_id_users'), 'games', 'users', ['owner_user_id'], ['id'], ondelete='CASCADE'
    )

    # 같은 제목을 복제해야 하니 옛 UNIQUE를 먼저 치운다. 실패해도 트랜잭션째 되돌아간다
    op.drop_index(
        'uq_games_title_norm_manual', table_name='games', postgresql_where=sa.text('steam_appid IS NULL')
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("""
        SELECT e.id AS entry_id, e.user_id, e.game_id
        FROM entries e JOIN games g ON g.id = e.game_id
        WHERE g.steam_appid IS NULL
        ORDER BY e.game_id, e.id
    """)).all()

    seen: set[int] = set()
    for row in rows:
        if row.game_id not in seen:
            seen.add(row.game_id)
            conn.execute(
                sa.text("UPDATE games SET owner_user_id = :user WHERE id = :game"),
                {"user": row.user_id, "game": row.game_id},
            )
            continue
        new_id = conn.execute(
            sa.text("""
                INSERT INTO games (title, title_norm, released_at, cover_url, created_at, owner_user_id)
                SELECT title, title_norm, released_at, cover_url, created_at, :user
                FROM games WHERE id = :game
                RETURNING id
            """),
            {"user": row.user_id, "game": row.game_id},
        ).scalar_one()
        conn.execute(
            sa.text("""
                INSERT INTO game_genres (game_id, genre_id)
                SELECT :new_id, genre_id FROM game_genres WHERE game_id = :game
            """),
            {"new_id": new_id, "game": row.game_id},
        )
        # SQL로 바꾸므로 updated_at은 그대로다 ─ 사용자가 고친 게 아니라 "최근 수정순"이 흔들리면 안 된다
        conn.execute(
            sa.text("UPDATE entries SET game_id = :new_id WHERE id = :entry"),
            {"new_id": new_id, "entry": row.entry_id},
        )

    conn.execute(sa.text("DELETE FROM games WHERE steam_appid IS NULL AND owner_user_id IS NULL"))

    op.create_index(
        'uq_games_owner_title_norm_manual',
        'games',
        ['owner_user_id', 'title_norm'],
        unique=True,
        postgresql_where=sa.text('steam_appid IS NULL'),
    )
    op.create_check_constraint(
        op.f('ck_games_owner_only_manual'), 'games', '(steam_appid IS NULL) = (owner_user_id IS NOT NULL)'
    )


def downgrade() -> None:
    """같은 제목의 수동 게임을 다시 한 행으로 합친다

    한 사람 안에서는 제목이 겹치지 않으니 (user_id, game_id) UNIQUE에 걸리지 않는다.
    합칠 때 가장 먼저 만들어진 행의 제목 · 장르만 남고 나머지 사람의 표기는 사라진다.
    """
    conn = op.get_bind()
    op.drop_constraint(op.f('ck_games_owner_only_manual'), 'games', type_='check')
    op.drop_index(
        'uq_games_owner_title_norm_manual', table_name='games', postgresql_where=sa.text('steam_appid IS NULL')
    )
    conn.execute(sa.text("""
        UPDATE entries e SET game_id = keep.id
        FROM games g
        JOIN (
            SELECT title_norm, MIN(id) AS id FROM games WHERE steam_appid IS NULL GROUP BY title_norm
        ) keep ON keep.title_norm = g.title_norm
        WHERE e.game_id = g.id AND g.steam_appid IS NULL AND g.id <> keep.id
    """))
    conn.execute(sa.text("""
        DELETE FROM games g
        WHERE g.steam_appid IS NULL
          AND g.id <> (SELECT MIN(id) FROM games o WHERE o.steam_appid IS NULL AND o.title_norm = g.title_norm)
    """))
    op.create_index(
        'uq_games_title_norm_manual',
        'games',
        ['title_norm'],
        unique=True,
        postgresql_where=sa.text('steam_appid IS NULL'),
    )
    op.drop_constraint(op.f('fk_games_owner_user_id_users'), 'games', type_='foreignkey')
    op.drop_index(op.f('ix_games_owner_user_id'), table_name='games')
    op.drop_column('games', 'owner_user_id')

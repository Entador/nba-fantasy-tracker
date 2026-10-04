"""add games.season

Makes the season each game belongs to explicit so queries can scope to the
current one. It was previously only implicit in nba_game_id (digits 4-5 are the
season start year), which meant every read mixed seasons together once a second
season landed in the DB.

Backfilled from nba_game_id, then set NOT NULL: a game with an unknown season
would silently disappear from the cache, so it's better to fail the insert.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('games', sa.Column('season', sa.String(length=7), nullable=True))

    # Backfill from the ID's season digits, one UPDATE per distinct season.
    # The formatting is duplicated from core.season on purpose — migrations are
    # frozen snapshots and must not depend on application code that may change.
    conn = op.get_bind()
    years = conn.execute(
        sa.text("SELECT DISTINCT substr(nba_game_id, 4, 2) AS yy FROM games")
    ).fetchall()
    for (yy,) in years:
        start_year = 2000 + int(yy)
        conn.execute(
            sa.text(
                "UPDATE games SET season = :season "
                "WHERE substr(nba_game_id, 4, 2) = :yy"
            ),
            {"season": f"{start_year}-{(start_year + 1) % 100:02d}", "yy": yy},
        )

    op.alter_column('games', 'season', nullable=False)
    op.create_index('ix_games_season', 'games', ['season'])


def downgrade() -> None:
    op.drop_index('ix_games_season', table_name='games')
    op.drop_column('games', 'season')

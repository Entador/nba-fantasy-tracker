"""add teams.stats_season

Team stats (record, pace, defensive rating, opponent averages) are
season-specific, but nothing recorded which season they came from — so a new
season opened by showing last season's numbers next to teams that had played
one game. This column lets the daily update clear stats it hasn't collected for
the current season yet.

Left NULL on existing rows, which reads as "unknown season" and makes the next
daily update clear them once.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('teams', sa.Column('stats_season', sa.String(length=7), nullable=True))


def downgrade() -> None:
    op.drop_column('teams', 'stats_season')

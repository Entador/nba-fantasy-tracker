"""nullable pick player_id (NULL = skipped night)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow picks.player_id to be NULL, representing a deliberately skipped night."""
    op.alter_column('picks', 'player_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    """Revert to NOT NULL. Skip rows (player_id IS NULL) must be cleared first."""
    op.execute("DELETE FROM picks WHERE player_id IS NULL")
    op.alter_column('picks', 'player_id', existing_type=sa.Integer(), nullable=False)

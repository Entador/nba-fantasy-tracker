"""add app_metadata

The AppMetadata model has existed since the injury-report work but never had a
migration: the table only ever got created by `Base.metadata.create_all`, the
documented local setup step. Databases built the supported way — alembic
upgrade head — never had it, so GET /api/snapshot raised UndefinedTable on
every request once it started reading `injury_updated_at`.

Uses IF NOT EXISTS so it's a no-op where create_all already made the table,
rather than failing the upgrade on existing dev databases.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'app_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=True),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    # unique=True + index=True on the model's `key` is a single unique index.
    op.create_index('ix_app_metadata_id', 'app_metadata', ['id'], if_not_exists=True)
    op.create_index('ix_app_metadata_key', 'app_metadata', ['key'], unique=True, if_not_exists=True)


def downgrade() -> None:
    op.drop_index('ix_app_metadata_key', table_name='app_metadata', if_exists=True)
    op.drop_index('ix_app_metadata_id', table_name='app_metadata', if_exists=True)
    op.drop_table('app_metadata', if_exists=True)

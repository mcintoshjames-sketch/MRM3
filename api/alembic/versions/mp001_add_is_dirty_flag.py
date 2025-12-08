"""add is_dirty flag to monitoring_plans

Revision ID: mp001_is_dirty
Revises: hf871496f680
Create Date: 2025-12-07 18:00:00.000000

This migration adds an is_dirty boolean flag to monitoring_plans table.
The flag tracks whether the plan has unpublished changes to metrics or models,
eliminating the need for expensive diff queries on every read.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'mp001_is_dirty'
down_revision: Union[str, None] = 'hf871496f680'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_dirty column with default False
    op.add_column('monitoring_plans',
        sa.Column('is_dirty', sa.Boolean(), nullable=False, server_default=sa.text('false'),
                  comment='True when metrics or models have been changed since last version publish')
    )
    op.create_index('ix_monitoring_plans_is_dirty', 'monitoring_plans', ['is_dirty'])


def downgrade() -> None:
    op.drop_index('ix_monitoring_plans_is_dirty', table_name='monitoring_plans')
    op.drop_column('monitoring_plans', 'is_dirty')

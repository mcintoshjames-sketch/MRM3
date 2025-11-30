"""Add requires_action_plan to priority config

Revision ID: b18069c182f0
Revises: a07058b071de
Create Date: 2025-11-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b18069c182f0'
down_revision: Union[str, None] = 'a07058b071de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add requires_action_plan column with default True
    op.add_column(
        'recommendation_priority_configs',
        sa.Column('requires_action_plan', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    op.drop_column('recommendation_priority_configs', 'requires_action_plan')

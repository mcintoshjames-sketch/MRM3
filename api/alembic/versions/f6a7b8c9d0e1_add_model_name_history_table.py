"""add model name history table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2025-11-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'model_name_history',
        sa.Column('history_id', sa.Integer(), primary_key=True),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('old_name', sa.String(255), nullable=False),
        sa.Column('new_name', sa.String(255), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('model_name_history')

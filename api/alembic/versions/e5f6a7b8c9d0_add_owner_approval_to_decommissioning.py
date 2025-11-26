"""add owner approval to decommissioning

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2025-11-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add owner approval columns to decommissioning_requests
    op.add_column(
        'decommissioning_requests',
        sa.Column('owner_approval_required', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'decommissioning_requests',
        sa.Column('owner_reviewed_by_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    )
    op.add_column(
        'decommissioning_requests',
        sa.Column('owner_reviewed_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'decommissioning_requests',
        sa.Column('owner_comment', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('decommissioning_requests', 'owner_comment')
    op.drop_column('decommissioning_requests', 'owner_reviewed_at')
    op.drop_column('decommissioning_requests', 'owner_reviewed_by_id')
    op.drop_column('decommissioning_requests', 'owner_approval_required')

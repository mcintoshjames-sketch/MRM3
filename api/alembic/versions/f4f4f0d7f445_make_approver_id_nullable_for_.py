"""make_approver_id_nullable_for_conditional_approvals

Revision ID: f4f4f0d7f445
Revises: edab17d6ee8f
Create Date: 2025-11-24 17:36:46.354035

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4f4f0d7f445'
down_revision: Union[str, None] = 'edab17d6ee8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make approver_id nullable to support conditional approvals
    # For conditional approvals, approver_id is NULL until Admin submits the approval
    op.alter_column('validation_approvals', 'approver_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    # Revert approver_id to NOT NULL
    # Note: This will fail if there are any NULL values in the column
    op.alter_column('validation_approvals', 'approver_id',
                    existing_type=sa.Integer(),
                    nullable=False)

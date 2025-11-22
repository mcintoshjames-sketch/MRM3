"""add_completion_date_to_validation_requests

Revision ID: 4c8d44efb86a
Revises: c26020fa6b4d
Create Date: 2025-11-22 00:05:55.079695

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c8d44efb86a'
down_revision: Union[str, None] = 'c26020fa6b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add completion_date column to validation_requests table
    op.add_column('validation_requests',
        sa.Column('completion_date', sa.TIMESTAMP(timezone=True), nullable=True)
    )

    # Create index for performance (filtering/sorting by completion date)
    op.create_index(
        'idx_validation_requests_completion_date',
        'validation_requests',
        ['completion_date']
    )

    # Backfill completion_date for existing APPROVED validation requests
    # This SQL will calculate the max(approved_at) from validation_approvals
    # where approval_status = 'Approved' for each validation request
    op.execute("""
        UPDATE validation_requests vr
        SET completion_date = (
            SELECT MAX(va.approved_at)
            FROM validation_approvals va
            WHERE va.request_id = vr.request_id
            AND va.approval_status = 'Approved'
        )
        WHERE vr.request_id IN (
            SELECT DISTINCT request_id
            FROM validation_approvals
            WHERE approval_status = 'Approved'
        )
    """)


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_validation_requests_completion_date', 'validation_requests')

    # Remove column
    op.drop_column('validation_requests', 'completion_date')

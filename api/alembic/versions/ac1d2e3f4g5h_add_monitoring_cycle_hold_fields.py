"""add_monitoring_cycle_hold_fields

Revision ID: ac1d2e3f4g5h
Revises: ab1c2d3e4f5a
Create Date: 2025-12-02 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac1d2e3f4g5h'
down_revision: Union[str, None] = 'ab1c2d3e4f5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'monitoring_cycles',
        sa.Column('hold_reason', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'monitoring_cycles',
        sa.Column('hold_start_date', sa.Date(), nullable=True)
    )
    op.add_column(
        'monitoring_cycles',
        sa.Column('original_due_date', sa.Date(), nullable=True)
    )
    op.add_column(
        'monitoring_cycles',
        sa.Column('postponed_due_date', sa.Date(), nullable=True)
    )
    op.add_column(
        'monitoring_cycles',
        sa.Column('postponement_count', sa.Integer(), nullable=False, server_default='0')
    )

    op.execute(
        "UPDATE monitoring_cycles "
        "SET original_due_date = submission_due_date "
        "WHERE original_due_date IS NULL"
    )


def downgrade() -> None:
    op.drop_column('monitoring_cycles', 'postponement_count')
    op.drop_column('monitoring_cycles', 'postponed_due_date')
    op.drop_column('monitoring_cycles', 'original_due_date')
    op.drop_column('monitoring_cycles', 'hold_start_date')
    op.drop_column('monitoring_cycles', 'hold_reason')

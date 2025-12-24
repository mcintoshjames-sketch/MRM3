"""remove_grace_period_days_from_mrsa_review_policies

Revision ID: mrsa003_remove_grace_period_days
Revises: mrsa002_review_policies
Create Date: 2025-12-24 15:48:30.000000

Removes grace_period_days from MRSA review policies now that overdue
status is no longer split into grace/critical bands.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'mrsa003_remove_grace_period_days'
down_revision: Union[str, None] = 'mrsa002_review_policies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('mrsa_review_policies', 'grace_period_days')


def downgrade() -> None:
    op.add_column(
        'mrsa_review_policies',
        sa.Column(
            'grace_period_days',
            sa.Integer(),
            nullable=False,
            server_default='30',
            comment='Days after due date before escalation (overdue threshold)'
        )
    )
    op.alter_column('mrsa_review_policies', 'grace_period_days', server_default=None)

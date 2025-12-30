"""add_data_submission_lead_days_to_monitoring_plans

Revision ID: ab1c2d3e4f5a
Revises: z6a7b8c9d0e1
Create Date: 2025-12-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab1c2d3e4f5a'
down_revision: Union[str, None] = 'z6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'monitoring_plans',
        sa.Column(
            'data_submission_lead_days',
            sa.Integer(),
            nullable=False,
            server_default='15',
            comment='Days between period end date and data submission due date'
        )
    )


def downgrade() -> None:
    op.drop_column('monitoring_plans', 'data_submission_lead_days')

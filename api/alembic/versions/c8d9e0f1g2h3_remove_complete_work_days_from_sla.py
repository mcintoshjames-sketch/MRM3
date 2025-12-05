"""remove complete_work_days from validation workflow sla

Revision ID: c8d9e0f1g2h3
Revises: 1a3f6a13e6d7
Create Date: 2025-12-04

This migration removes the complete_work_days column from validation_workflow_slas.
The work completion lead time is now determined per validation request based on the
model's risk tier policy (model_change_lead_time_days in validation_policies table).

For multi-model validation requests, the maximum lead time across all models' policies
is used (most conservative approach).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1g2h3'
down_revision: Union[str, None] = '1a3f6a13e6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove the complete_work_days column - this is now calculated per-request
    # based on the validation policy's model_change_lead_time_days for the model's risk tier
    op.drop_column('validation_workflow_slas', 'complete_work_days')


def downgrade() -> None:
    # Re-add complete_work_days with default value of 80 days
    op.add_column('validation_workflow_slas',
        sa.Column('complete_work_days', sa.Integer(), nullable=False, server_default='80')
    )
    # Remove the server default after the column is populated
    op.alter_column('validation_workflow_slas', 'complete_work_days', server_default=None)

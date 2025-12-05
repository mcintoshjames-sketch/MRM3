"""remove model_change_lead_time_days from validation workflow sla

Revision ID: d9e0f1g2h3i4
Revises: c8d9e0f1g2h3
Create Date: 2025-12-04

This migration removes the model_change_lead_time_days column from validation_workflow_slas.
This field was a global lead time value, but lead time is now determined per validation
request based on the associated models' risk tier policies (model_change_lead_time_days
in validation_policies table).

For multi-model validation requests, the maximum lead time across all models' policies
is used (most conservative approach). This is computed by the ValidationRequest.applicable_lead_time_days
property.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e0f1g2h3i4'
down_revision: Union[str, None] = 'c8d9e0f1g2h3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove the model_change_lead_time_days column from SLA table
    # This lead time is now per-request based on models' risk tier policies
    op.drop_column('validation_workflow_slas', 'model_change_lead_time_days')


def downgrade() -> None:
    # Re-add model_change_lead_time_days with default value of 90 days
    op.add_column('validation_workflow_slas',
        sa.Column('model_change_lead_time_days', sa.Integer(), nullable=False, server_default='90')
    )
    # Remove the server default after the column is populated
    op.alter_column('validation_workflow_slas', 'model_change_lead_time_days', server_default=None)

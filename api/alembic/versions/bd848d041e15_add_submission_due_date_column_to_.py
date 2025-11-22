"""Add submission_due_date column to validation_requests

Revision ID: bd848d041e15
Revises: 4c8d44efb86a
Create Date: 2025-11-22 02:24:48.477994

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bd848d041e15'
down_revision: Union[str, None] = '4c8d44efb86a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add submission_due_date column
    op.add_column('validation_requests', sa.Column('submission_due_date', sa.Date(), nullable=True, comment='Date by which model owner must submit documentation (locked at request creation)'))

    # Backfill submission_due_date for existing revalidation requests
    # This SQL calculates submission_due_date from prior validation + policy frequency
    op.execute("""
        UPDATE validation_requests vr
        SET submission_due_date = (
            SELECT
                CASE
                    WHEN prior_vr.completion_date IS NOT NULL THEN
                        (prior_vr.completion_date::date + (vp.frequency_months || ' months')::interval)::date
                    ELSE
                        (prior_vr.updated_at::date + (vp.frequency_months || ' months')::interval)::date
                END
            FROM validation_requests prior_vr
            JOIN validation_request_models vrm ON vrm.request_id = vr.request_id
            JOIN models m ON m.model_id = vrm.model_id
            JOIN validation_policies vp ON vp.risk_tier_id = m.risk_tier_id
            JOIN taxonomy_values tv ON tv.value_id = vr.validation_type_id
            WHERE prior_vr.request_id = vr.prior_validation_request_id
                AND tv.code IN ('COMPREHENSIVE', 'ANNUAL')
                AND prior_vr.current_status_id IN (
                    SELECT value_id FROM taxonomy_values WHERE code = 'APPROVED'
                )
            LIMIT 1
        )
        WHERE vr.prior_validation_request_id IS NOT NULL
            AND vr.validation_type_id IN (
                SELECT value_id FROM taxonomy_values WHERE code IN ('COMPREHENSIVE', 'ANNUAL')
            );
    """)


def downgrade() -> None:
    # Remove submission_due_date column
    op.drop_column('validation_requests', 'submission_due_date')

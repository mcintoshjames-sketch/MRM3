"""add_validated_risk_tier_to_validation_requests

Revision ID: y5z6a7b8c9d0
Revises: 753a34899e81
Create Date: 2025-12-01

This migration:
1. Adds validated_risk_tier_id column to validation_requests table
2. Backfills the column for approved validation requests using the model's current risk_tier_id
   (or infers from the most conservative risk tier among associated models if multiple)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'y5z6a7b8c9d0'
down_revision: Union[str, None] = '753a34899e81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add the column
    op.add_column(
        'validation_requests',
        sa.Column(
            'validated_risk_tier_id',
            sa.Integer(),
            sa.ForeignKey('taxonomy_values.value_id', ondelete='SET NULL'),
            nullable=True,
            comment='Snapshot of model\'s risk tier at the moment of validation approval'
        )
    )

    # Step 2: Create index for efficient lookups
    op.create_index(
        'ix_validation_requests_validated_risk_tier_id',
        'validation_requests',
        ['validated_risk_tier_id']
    )

    # Step 3: Backfill for APPROVED validation requests
    # For each approved validation request, set validated_risk_tier_id to the most conservative
    # (highest) risk tier among its associated models. This uses sort_order from taxonomy_values
    # where lower sort_order = higher risk (TIER_1=1, TIER_2=2, etc.)
    conn = op.get_bind()

    # Get the APPROVED status value_id
    result = conn.execute(sa.text("""
        SELECT tv.value_id
        FROM taxonomy_values tv
        JOIN taxonomies t ON tv.taxonomy_id = t.taxonomy_id
        WHERE t.name = 'Validation Request Status' AND tv.code = 'APPROVED'
    """))
    approved_row = result.fetchone()

    if approved_row:
        approved_status_id = approved_row[0]

        # Backfill: For each approved request, find the most conservative risk tier
        # among its associated models (minimum sort_order = highest risk)
        conn.execute(sa.text("""
            UPDATE validation_requests vr
            SET validated_risk_tier_id = (
                SELECT m.risk_tier_id
                FROM validation_request_models vrm
                JOIN models m ON vrm.model_id = m.model_id
                JOIN taxonomy_values tv ON m.risk_tier_id = tv.value_id
                WHERE vrm.request_id = vr.request_id
                AND m.risk_tier_id IS NOT NULL
                ORDER BY tv.sort_order ASC
                LIMIT 1
            )
            WHERE vr.current_status_id = :approved_status_id
            AND vr.validated_risk_tier_id IS NULL
        """), {"approved_status_id": approved_status_id})

        print(f"Backfilled validated_risk_tier_id for approved validation requests")


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_validation_requests_validated_risk_tier_id', table_name='validation_requests')

    # Drop column
    op.drop_column('validation_requests', 'validated_risk_tier_id')

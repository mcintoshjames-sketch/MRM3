"""backfill risk_tiers from assessments

Revision ID: bf001_backfill_risk_tiers
Revises: irp001_certified_by_email
Create Date: 2026-02-11

Data-only migration: syncs model.risk_tier_id with the global risk assessment's
final_tier_id for any models where they are out of sync. This is a pure data
correction — no validation-plan resets or audit-log entries are created.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf001_backfill_risk_tiers'
down_revision: Union[str, None] = 'irp001_certified_by_email'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Find all global assessments (region_id IS NULL) where the model's
    # risk_tier_id doesn't match the assessment's final_tier_id.
    rows = conn.execute(sa.text("""
        SELECT a.model_id, a.final_tier_id
        FROM model_risk_assessments a
        JOIN models m ON m.model_id = a.model_id
        WHERE a.region_id IS NULL
          AND a.final_tier_id IS NOT NULL
          AND (m.risk_tier_id IS NULL OR m.risk_tier_id != a.final_tier_id)
    """)).fetchall()

    for model_id, final_tier_id in rows:
        conn.execute(sa.text(
            "UPDATE models SET risk_tier_id = :tier_id WHERE model_id = :model_id"
        ), {"tier_id": final_tier_id, "model_id": model_id})

    if rows:
        print(f"  Backfilled risk_tier_id for {len(rows)} model(s) from global assessments")


def downgrade() -> None:
    # Data-only migration — no structural rollback needed.
    # The previous risk_tier_id values are not recoverable, but the sync
    # mechanism in risk_assessment.py will keep them correct going forward.
    pass

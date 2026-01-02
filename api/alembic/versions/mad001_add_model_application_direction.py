"""add_model_application_direction

Revision ID: mad001
Revises: q7r8s9t0u1v2
Create Date: 2026-01-02 00:00:01.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "mad001"
down_revision: Union[str, None] = "q7r8s9t0u1v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "model_applications",
        sa.Column(
            "relationship_direction",
            sa.String(length=20),
            nullable=True,
            server_default="UNKNOWN",
            comment="Direction relative to model: UPSTREAM, DOWNSTREAM, or UNKNOWN",
        ),
    )
    op.create_check_constraint(
        "chk_model_application_direction",
        "model_applications",
        "relationship_direction IN ('UPSTREAM', 'DOWNSTREAM', 'UNKNOWN') OR relationship_direction IS NULL",
    )

    # Backfill known directions based on relationship type codes
    op.execute(
        """
        UPDATE model_applications
        SET relationship_direction = 'UPSTREAM'
        WHERE relationship_type_id IN (
            SELECT value_id FROM taxonomy_values WHERE code = 'DATA_SOURCE'
        )
        """
    )
    op.execute(
        """
        UPDATE model_applications
        SET relationship_direction = 'DOWNSTREAM'
        WHERE relationship_type_id IN (
            SELECT value_id FROM taxonomy_values WHERE code IN ('OUTPUT_CONSUMER', 'REPORTING')
        )
        """
    )
    op.execute(
        """
        UPDATE model_applications
        SET relationship_direction = 'UNKNOWN'
        WHERE relationship_direction IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "chk_model_application_direction",
        "model_applications",
        type_="check",
    )
    op.drop_column("model_applications", "relationship_direction")

"""add_applied_rule_fields_to_attestations

Revision ID: att001
Revises: aarol3
Create Date: 2026-01-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "att001"
down_revision: Union[str, None] = "aarol3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attestation_records",
        sa.Column("applied_rule_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "attestation_records",
        sa.Column("applied_frequency", sa.String(length=20), nullable=True)
    )
    op.create_foreign_key(
        "fk_attestation_records_applied_rule_id",
        "attestation_records",
        "attestation_scheduling_rules",
        ["applied_rule_id"],
        ["rule_id"],
        ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_attestation_records_applied_rule_id",
        "attestation_records",
        type_="foreignkey"
    )
    op.drop_column("attestation_records", "applied_frequency")
    op.drop_column("attestation_records", "applied_rule_id")

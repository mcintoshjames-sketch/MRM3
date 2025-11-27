"""Add category_type to kpm_categories table

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2025-01-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j0e1f2g3h4i5'
down_revision: Union[str, None] = 'i9d0e1f2g3h4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add category_type column to kpm_categories table
    # Default to 'Quantitative' for existing categories
    op.add_column(
        'kpm_categories',
        sa.Column(
            'category_type',
            sa.String(length=50),
            nullable=False,
            server_default='Quantitative',
            comment='Category type: Quantitative or Qualitative'
        )
    )

    # Update qualitative categories to have the correct type
    # These are the categories that contain only qualitative KPMs
    op.execute("""
        UPDATE kpm_categories
        SET category_type = 'Qualitative'
        WHERE code IN (
            'attestation_based',
            'governance_usage_alignment',
            'expert_judgment_assessments',
            'model_conditions_exceptions',
            'algorithmic_qualitative_classification'
        )
    """)


def downgrade() -> None:
    op.drop_column('kpm_categories', 'category_type')

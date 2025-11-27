"""Add evaluation_type to kpms table

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2025-01-21 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i9d0e1f2g3h4'
down_revision: Union[str, None] = 'h8c9d0e1f2g3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add evaluation_type column to kpms table
    # Default to 'Quantitative' for existing KPMs (all current ones are quantitative)
    op.add_column(
        'kpms',
        sa.Column(
            'evaluation_type',
            sa.String(length=50),
            nullable=False,
            server_default='Quantitative',
            comment='How this KPM is evaluated: Quantitative (thresholds), Qualitative (rules/judgment), Outcome Only (direct R/Y/G)'
        )
    )


def downgrade() -> None:
    op.drop_column('kpms', 'evaluation_type')

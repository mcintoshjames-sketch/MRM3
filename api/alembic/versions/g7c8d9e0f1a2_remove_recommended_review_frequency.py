"""Remove recommended_review_frequency from validation_outcomes

The recommended_review_frequency field is redundant because actual
revalidation scheduling is driven by ValidationPolicy.frequency_months
based on risk tier, not individual validation outcomes.

Revision ID: g7c8d9e0f1a2
Revises: f6a7b8c9d0e2
Create Date: 2025-12-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7c8d9e0f1a2'
down_revision: Union[str, None] = 'f6a7b8c9d0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('validation_outcomes', 'recommended_review_frequency')


def downgrade() -> None:
    op.add_column('validation_outcomes', sa.Column('recommended_review_frequency', sa.Integer(), nullable=False, server_default='12'))
    # Remove the server default after adding the column
    op.alter_column('validation_outcomes', 'recommended_review_frequency', server_default=None)

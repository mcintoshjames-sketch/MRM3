"""Add overall_assessment_narrative to validation_scorecard_results.

Revision ID: sc001_overall_narrative
Revises: rec001_add_plan_metric_id_to_recommendations
Create Date: 2025-12-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'sc001'
down_revision: Union[str, None] = 'rec001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add overall_assessment_narrative column to validation_scorecard_results."""
    op.add_column(
        'validation_scorecard_results',
        sa.Column(
            'overall_assessment_narrative',
            sa.Text(),
            nullable=True,
            comment='Free-text narrative for overall scorecard assessment'
        )
    )


def downgrade() -> None:
    """Remove overall_assessment_narrative column."""
    op.drop_column('validation_scorecard_results', 'overall_assessment_narrative')

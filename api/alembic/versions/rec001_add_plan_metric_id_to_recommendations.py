"""Add plan_metric_id to recommendations table.

Revision ID: rec001
Revises: exc001
Create Date: 2025-01-10 14:00:00.000000

This migration adds the plan_metric_id column to link recommendations
to specific monitoring plan metrics, enabling metric-level matching
for Type 1 exception detection.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'rec001'
down_revision = 'exc001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add plan_metric_id column to recommendations table
    # Note: index=True in add_column auto-creates ix_recommendations_plan_metric_id
    op.add_column(
        'recommendations',
        sa.Column(
            'plan_metric_id',
            sa.Integer(),
            nullable=True,
            comment='Link to specific metric that triggered this recommendation (if applicable)'
        )
    )

    # Create index explicitly (add_column index=True doesn't work reliably with ForeignKey)
    op.create_index(
        'ix_recommendations_plan_metric_id',
        'recommendations',
        ['plan_metric_id']
    )

    # Add foreign key constraint separately
    op.create_foreign_key(
        'fk_recommendations_plan_metric_id',
        'recommendations',
        'monitoring_plan_metrics',
        ['plan_metric_id'],
        ['metric_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key first
    op.drop_constraint('fk_recommendations_plan_metric_id', 'recommendations', type_='foreignkey')

    # Drop index
    op.drop_index('ix_recommendations_plan_metric_id', 'recommendations')

    # Drop column
    op.drop_column('recommendations', 'plan_metric_id')

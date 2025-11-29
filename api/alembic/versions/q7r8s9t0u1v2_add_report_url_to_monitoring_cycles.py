"""Add report_url to monitoring_cycles.

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2025-01-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'q7r8s9t0u1v2'
down_revision = 'p6q7r8s9t0u1'
branch_labels = None
depends_on = None


def upgrade():
    # Add report_url column to monitoring_cycles
    op.add_column(
        'monitoring_cycles',
        sa.Column(
            'report_url',
            sa.String(500),
            nullable=True,
            comment='URL to the final monitoring report document for approvers to review'
        )
    )


def downgrade():
    op.drop_column('monitoring_cycles', 'report_url')

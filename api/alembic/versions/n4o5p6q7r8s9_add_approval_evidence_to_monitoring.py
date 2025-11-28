"""Add approval_evidence to monitoring cycle approvals.

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'n4o5p6q7r8s9'
down_revision = 'm3n4o5p6q7r8'
branch_labels = None
depends_on = None


def upgrade():
    # Add approval_evidence column to monitoring_cycle_approvals table
    # This field is used when Admin approves on behalf of the appropriate role
    # (Global Approver or Regional Approver with authorized regions)
    op.add_column('monitoring_cycle_approvals', sa.Column(
        'approval_evidence',
        sa.Text(),
        nullable=True,
        comment='Evidence description for Admin proxy approvals (meeting minutes, email, etc.)'
    ))


def downgrade():
    op.drop_column('monitoring_cycle_approvals', 'approval_evidence')

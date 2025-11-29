"""Add monitoring plan model snapshots table.

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'o5p6q7r8s9t0'
down_revision = 'n4o5p6q7r8s9'
branch_labels = None
depends_on = None


def upgrade():
    # Create monitoring_plan_model_snapshots table
    # This captures the models in scope at each version of a monitoring plan
    op.create_table(
        'monitoring_plan_model_snapshots',
        sa.Column('snapshot_id', sa.Integer(), primary_key=True),
        sa.Column('version_id', sa.Integer(),
                  sa.ForeignKey('monitoring_plan_versions.version_id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('model_id', sa.Integer(),
                  sa.ForeignKey('models.model_id', ondelete='CASCADE'),
                  nullable=False),
        # Model metadata snapshot (captured at time of version publish)
        sa.Column('model_name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('version_id', 'model_id', name='uq_version_model')
    )


def downgrade():
    op.drop_table('monitoring_plan_model_snapshots')

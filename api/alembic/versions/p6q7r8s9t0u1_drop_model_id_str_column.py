"""Drop model_id_str column from monitoring_plan_model_snapshots.

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'p6q7r8s9t0u1'
down_revision = 'o5p6q7r8s9t0'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the model_id_str column (Model class doesn't have this attribute)
    # Use raw SQL with IF EXISTS to handle fresh databases where column may not exist
    op.execute('ALTER TABLE monitoring_plan_model_snapshots DROP COLUMN IF EXISTS model_id_str')


def downgrade():
    # Re-add the column for rollback
    op.add_column(
        'monitoring_plan_model_snapshots',
        sa.Column('model_id_str', sa.String(50), nullable=True)
    )

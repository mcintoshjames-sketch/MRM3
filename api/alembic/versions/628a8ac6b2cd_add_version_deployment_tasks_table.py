"""add version deployment tasks table

Revision ID: 628a8ac6b2cd
Revises: 2f2022f1346b
Create Date: 2025-11-21 20:01:11.448527

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '628a8ac6b2cd'
down_revision: Union[str, None] = '2f2022f1346b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create version_deployment_tasks table
    op.create_table(
        'version_deployment_tasks',
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('region_id', sa.Integer(), nullable=True, comment='NULL for global deployment'),

        # Task details
        sa.Column('planned_production_date', sa.Date(), nullable=False),
        sa.Column('actual_production_date', sa.Date(), nullable=True),

        # Assignment
        sa.Column('assigned_to_id', sa.Integer(), nullable=False, comment='Model Owner or delegate'),

        # Status
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('confirmation_notes', sa.Text(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('confirmed_by_id', sa.Integer(), nullable=True),

        # Validation override tracking
        sa.Column('deployed_before_validation_approved', sa.Boolean(), nullable=False, server_default='false',
                  comment='True if deployed before validation was approved'),
        sa.Column('validation_override_reason', sa.Text(), nullable=True,
                  comment='Justification for deploying before validation approval'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        # Primary key and foreign keys
        sa.PrimaryKeyConstraint('task_id'),
        sa.ForeignKeyConstraint(['version_id'], ['model_versions.version_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.region_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['confirmed_by_id'], ['users.user_id']),
    )

    # Create indexes for common queries
    op.create_index('ix_version_deployment_tasks_assigned_to_id', 'version_deployment_tasks', ['assigned_to_id'])
    op.create_index('ix_version_deployment_tasks_status', 'version_deployment_tasks', ['status'])
    op.create_index('ix_version_deployment_tasks_planned_date', 'version_deployment_tasks', ['planned_production_date'])


def downgrade() -> None:
    op.drop_index('ix_version_deployment_tasks_planned_date', table_name='version_deployment_tasks')
    op.drop_index('ix_version_deployment_tasks_status', table_name='version_deployment_tasks')
    op.drop_index('ix_version_deployment_tasks_assigned_to_id', table_name='version_deployment_tasks')
    op.drop_table('version_deployment_tasks')

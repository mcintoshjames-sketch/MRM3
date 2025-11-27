"""Add monitoring tables

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2025-01-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h8c9d0e1f2g3'
down_revision: Union[str, None] = 'g7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create monitoring_teams table
    op.create_table(
        'monitoring_teams',
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('team_id'),
        sa.UniqueConstraint('name')
    )

    # Create monitoring_team_members junction table
    op.create_table(
        'monitoring_team_members',
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['monitoring_teams.team_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('team_id', 'user_id')
    )

    # Create monitoring_plans table
    op.create_table(
        'monitoring_plans',
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('frequency', sa.String(length=50), nullable=False, server_default='Quarterly'),
        sa.Column('monitoring_team_id', sa.Integer(), nullable=True),
        sa.Column('data_provider_user_id', sa.Integer(), nullable=True),
        sa.Column('reporting_lead_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('next_submission_due_date', sa.Date(), nullable=True),
        sa.Column('next_report_due_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['monitoring_team_id'], ['monitoring_teams.team_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['data_provider_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('plan_id')
    )

    # Create monitoring_plan_models junction table (scope)
    op.create_table(
        'monitoring_plan_models',
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['monitoring_plans.plan_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('plan_id', 'model_id')
    )

    # Create monitoring_plan_metrics table
    op.create_table(
        'monitoring_plan_metrics',
        sa.Column('metric_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('kpm_id', sa.Integer(), nullable=False),
        sa.Column('yellow_min', sa.Float(), nullable=True),
        sa.Column('yellow_max', sa.Float(), nullable=True),
        sa.Column('red_min', sa.Float(), nullable=True),
        sa.Column('red_max', sa.Float(), nullable=True),
        sa.Column('qualitative_guidance', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['plan_id'], ['monitoring_plans.plan_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kpm_id'], ['kpms.kpm_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('metric_id')
    )
    op.create_index('ix_monitoring_plan_metrics_plan_id', 'monitoring_plan_metrics', ['plan_id'])
    op.create_index('ix_monitoring_plan_metrics_kpm_id', 'monitoring_plan_metrics', ['kpm_id'])


def downgrade() -> None:
    op.drop_index('ix_monitoring_plan_metrics_kpm_id', table_name='monitoring_plan_metrics')
    op.drop_index('ix_monitoring_plan_metrics_plan_id', table_name='monitoring_plan_metrics')
    op.drop_table('monitoring_plan_metrics')
    op.drop_table('monitoring_plan_models')
    op.drop_table('monitoring_plans')
    op.drop_table('monitoring_team_members')
    op.drop_table('monitoring_teams')

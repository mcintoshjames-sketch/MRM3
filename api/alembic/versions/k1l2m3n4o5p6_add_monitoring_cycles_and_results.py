"""Add monitoring cycles, approvals, and results tables.

Revision ID: k1l2m3n4o5p6
Revises: j0e1f2g3h4i5
Create Date: 2025-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'j0e1f2g3h4i5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create monitoring_cycles table
    op.create_table(
        'monitoring_cycles',
        sa.Column('cycle_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('period_start_date', sa.Date(), nullable=False),
        sa.Column('period_end_date', sa.Date(), nullable=False),
        sa.Column('submission_due_date', sa.Date(), nullable=False),
        sa.Column('report_due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('assigned_to_user_id', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_by_user_id', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('cycle_id'),
        sa.ForeignKeyConstraint(['plan_id'], ['monitoring_plans.plan_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['completed_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.CheckConstraint('period_end_date >= period_start_date', name='valid_period'),
        sa.CheckConstraint('report_due_date >= submission_due_date', name='valid_due_dates'),
    )
    op.create_index('idx_monitoring_cycles_plan_id', 'monitoring_cycles', ['plan_id'])
    op.create_index('idx_monitoring_cycles_status', 'monitoring_cycles', ['status'])

    # Create monitoring_cycle_approvals table
    op.create_table(
        'monitoring_cycle_approvals',
        sa.Column('approval_id', sa.Integer(), nullable=False),
        sa.Column('cycle_id', sa.Integer(), nullable=False),
        sa.Column('approver_id', sa.Integer(), nullable=True),
        sa.Column('approval_type', sa.String(20), nullable=False, server_default='Global'),
        sa.Column('region_id', sa.Integer(), nullable=True),
        sa.Column('represented_region_id', sa.Integer(), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('approval_status', sa.String(50), nullable=False, server_default='Pending'),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('voided_by_id', sa.Integer(), nullable=True),
        sa.Column('void_reason', sa.Text(), nullable=True),
        sa.Column('voided_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('approval_id'),
        sa.ForeignKeyConstraint(['cycle_id'], ['monitoring_cycles.cycle_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approver_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.region_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['represented_region_id'], ['regions.region_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['voided_by_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.UniqueConstraint('cycle_id', 'approval_type', 'region_id', name='unique_cycle_approval'),
    )
    op.create_index('idx_monitoring_cycle_approvals_cycle', 'monitoring_cycle_approvals', ['cycle_id'])
    op.create_index('idx_monitoring_cycle_approvals_status', 'monitoring_cycle_approvals', ['approval_status'])

    # Create monitoring_results table
    op.create_table(
        'monitoring_results',
        sa.Column('result_id', sa.Integer(), nullable=False),
        sa.Column('cycle_id', sa.Integer(), nullable=False),
        sa.Column('plan_metric_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=True),
        sa.Column('numeric_value', sa.Float(), nullable=True),
        sa.Column('outcome_value_id', sa.Integer(), nullable=True),
        sa.Column('calculated_outcome', sa.String(20), nullable=True),
        sa.Column('narrative', sa.Text(), nullable=True),
        sa.Column('supporting_data', sa.JSON(), nullable=True),
        sa.Column('entered_by_user_id', sa.Integer(), nullable=False),
        sa.Column('entered_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('result_id'),
        sa.ForeignKeyConstraint(['cycle_id'], ['monitoring_cycles.cycle_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_metric_id'], ['monitoring_plan_metrics.metric_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outcome_value_id'], ['taxonomy_values.value_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['entered_by_user_id'], ['users.user_id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('cycle_id', 'plan_metric_id', 'model_id', name='unique_result'),
    )
    op.create_index('idx_monitoring_results_cycle', 'monitoring_results', ['cycle_id'])
    op.create_index('idx_monitoring_results_metric', 'monitoring_results', ['plan_metric_id'])
    op.create_index('idx_monitoring_results_model', 'monitoring_results', ['model_id'])
    op.create_index('idx_monitoring_results_outcome', 'monitoring_results', ['calculated_outcome'])


def downgrade() -> None:
    # Drop indexes and tables in reverse order
    op.drop_index('idx_monitoring_results_outcome', table_name='monitoring_results')
    op.drop_index('idx_monitoring_results_model', table_name='monitoring_results')
    op.drop_index('idx_monitoring_results_metric', table_name='monitoring_results')
    op.drop_index('idx_monitoring_results_cycle', table_name='monitoring_results')
    op.drop_table('monitoring_results')

    op.drop_index('idx_monitoring_cycle_approvals_status', table_name='monitoring_cycle_approvals')
    op.drop_index('idx_monitoring_cycle_approvals_cycle', table_name='monitoring_cycle_approvals')
    op.drop_table('monitoring_cycle_approvals')

    op.drop_index('idx_monitoring_cycles_status', table_name='monitoring_cycles')
    op.drop_index('idx_monitoring_cycles_plan_id', table_name='monitoring_cycles')
    op.drop_table('monitoring_cycles')

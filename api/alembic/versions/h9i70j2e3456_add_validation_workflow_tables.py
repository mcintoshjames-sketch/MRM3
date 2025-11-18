"""add_validation_workflow_tables

Revision ID: h9i70j2e3456
Revises: c7d28f6f1366
Create Date: 2025-11-17 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h9i70j2e3456'
down_revision: Union[str, None] = 'c7d28f6f1366'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create validation_requests table
    op.create_table(
        'validation_requests',
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('request_date', sa.Date(), nullable=False),
        sa.Column('requestor_id', sa.Integer(), nullable=False),
        sa.Column('validation_type_id', sa.Integer(), nullable=False),
        sa.Column('priority_id', sa.Integer(), nullable=False),
        sa.Column('target_completion_date', sa.Date(), nullable=False),
        sa.Column('trigger_reason', sa.Text(), nullable=True),
        sa.Column('business_justification', sa.Text(), nullable=False),
        sa.Column('current_status_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requestor_id'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['validation_type_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['priority_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['current_status_id'], ['taxonomy_values.value_id'], ),
        sa.PrimaryKeyConstraint('request_id')
    )

    # Create validation_status_history table
    op.create_table(
        'validation_status_history',
        sa.Column('history_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('old_status_id', sa.Integer(), nullable=True),
        sa.Column('new_status_id', sa.Integer(), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=False),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['validation_requests.request_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['old_status_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['new_status_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('history_id')
    )

    # Create validation_assignments table
    op.create_table(
        'validation_assignments',
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('validator_id', sa.Integer(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.Column('assignment_date', sa.Date(), nullable=False),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('actual_hours', sa.Float(), nullable=True),
        sa.Column('independence_attestation', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['validation_requests.request_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['validator_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('assignment_id')
    )

    # Create validation_work_components table
    op.create_table(
        'validation_work_components',
        sa.Column('component_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('component_type_id', sa.Integer(), nullable=False),
        sa.Column('status_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['validation_requests.request_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['component_type_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['status_id'], ['taxonomy_values.value_id'], ),
        sa.PrimaryKeyConstraint('component_id')
    )

    # Create validation_outcomes table
    op.create_table(
        'validation_outcomes',
        sa.Column('outcome_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('overall_rating_id', sa.Integer(), nullable=False),
        sa.Column('executive_summary', sa.Text(), nullable=False),
        sa.Column('recommended_review_frequency', sa.Integer(), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['validation_requests.request_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['overall_rating_id'], ['taxonomy_values.value_id'], ),
        sa.PrimaryKeyConstraint('outcome_id'),
        sa.UniqueConstraint('request_id')
    )

    # Create validation_approvals table
    op.create_table(
        'validation_approvals',
        sa.Column('approval_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('approver_id', sa.Integer(), nullable=False),
        sa.Column('approver_role', sa.String(length=100), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=False),
        sa.Column('approval_status', sa.String(length=50), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['validation_requests.request_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approver_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('approval_id')
    )


def downgrade() -> None:
    op.drop_table('validation_approvals')
    op.drop_table('validation_outcomes')
    op.drop_table('validation_work_components')
    op.drop_table('validation_assignments')
    op.drop_table('validation_status_history')
    op.drop_table('validation_requests')

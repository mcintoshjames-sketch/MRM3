"""add decommissioning tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2025-11-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create decommissioning_requests table
    op.create_table(
        'decommissioning_requests',
        sa.Column('request_id', sa.Integer(), primary_key=True),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', sa.String(30), nullable=False, default='PENDING'),
        sa.Column('reason_id', sa.Integer(), sa.ForeignKey('taxonomy_values.value_id'), nullable=False),
        sa.Column('replacement_model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='SET NULL'), nullable=True),
        sa.Column('last_production_date', sa.Date(), nullable=False),
        sa.Column('gap_justification', sa.Text(), nullable=True),
        sa.Column('archive_location', sa.Text(), nullable=False),
        sa.Column('downstream_impact_verified', sa.Boolean(), nullable=False, default=False),

        # Creation
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.user_id'), nullable=False),

        # Validator review (Stage 1)
        sa.Column('validator_reviewed_by_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('validator_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('validator_comment', sa.Text(), nullable=True),

        # Final status tracking
        sa.Column('final_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),

        # Constraint: model cannot be its own replacement
        sa.CheckConstraint('model_id != replacement_model_id', name='chk_different_models'),
    )

    # Create decommissioning_status_history table
    op.create_table(
        'decommissioning_status_history',
        sa.Column('history_id', sa.Integer(), primary_key=True),
        sa.Column('request_id', sa.Integer(), sa.ForeignKey('decommissioning_requests.request_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('old_status', sa.String(30), nullable=True),
        sa.Column('new_status', sa.String(30), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    # Create decommissioning_approvals table (for Global/Regional approvers - Stage 2)
    op.create_table(
        'decommissioning_approvals',
        sa.Column('approval_id', sa.Integer(), primary_key=True),
        sa.Column('request_id', sa.Integer(), sa.ForeignKey('decommissioning_requests.request_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('approver_type', sa.String(20), nullable=False),  # GLOBAL, REGIONAL
        sa.Column('region_id', sa.Integer(), sa.ForeignKey('regions.region_id', ondelete='CASCADE'), nullable=True),  # NULL for GLOBAL
        sa.Column('approved_by_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=True),  # NULL=pending, TRUE=approved, FALSE=rejected
        sa.Column('comment', sa.Text(), nullable=True),

        # Unique constraint: one approval record per type/region combination
        sa.UniqueConstraint('request_id', 'approver_type', 'region_id', name='uq_decom_approval_type_region'),
    )

    # Create indexes for common queries
    op.create_index('ix_decom_requests_status', 'decommissioning_requests', ['status'])
    op.create_index('ix_decom_approvals_pending', 'decommissioning_approvals', ['request_id', 'is_approved'])


def downgrade() -> None:
    op.drop_index('ix_decom_approvals_pending', table_name='decommissioning_approvals')
    op.drop_index('ix_decom_requests_status', table_name='decommissioning_requests')
    op.drop_table('decommissioning_approvals')
    op.drop_table('decommissioning_status_history')
    op.drop_table('decommissioning_requests')

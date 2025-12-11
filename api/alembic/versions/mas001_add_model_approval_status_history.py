"""add_model_approval_status_history

Revision ID: mas001_approval_status
Revises: rsr001_standalone_rating
Create Date: 2025-12-10 10:00:00.000000

This migration creates the model_approval_status_history table for tracking
changes to model approval status over time (NEVER_VALIDATED, APPROVED,
INTERIM_APPROVED, VALIDATION_IN_PROGRESS, EXPIRED).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'mas001_approval_status'
down_revision: Union[str, None] = 'rsr001_standalone_rating'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create model_approval_status_history table
    op.create_table(
        'model_approval_status_history',
        sa.Column('history_id', sa.Integer(), primary_key=True),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='CASCADE'), nullable=False),
        sa.Column('old_status', sa.String(30), nullable=True,
                  comment='Previous approval status (NULL for initial status)'),
        sa.Column('new_status', sa.String(30), nullable=False,
                  comment='New approval status'),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('trigger_type', sa.String(50), nullable=False,
                  comment='What triggered this change: VALIDATION_APPROVED, VALIDATION_STATUS_CHANGE, APPROVAL_SUBMITTED, EXPIRATION_CHECK, BACKFILL, MANUAL'),
        sa.Column('trigger_entity_type', sa.String(50), nullable=True,
                  comment='Entity type that triggered change: ValidationRequest, ValidationApproval, etc.'),
        sa.Column('trigger_entity_id', sa.Integer(), nullable=True,
                  comment='ID of the entity that triggered the change'),
        sa.Column('notes', sa.Text(), nullable=True,
                  comment='Additional context about the status change'),
    )

    # Create indexes for common query patterns
    op.create_index(
        'ix_model_approval_status_history_model_id',
        'model_approval_status_history',
        ['model_id']
    )
    op.create_index(
        'ix_model_approval_status_history_changed_at',
        'model_approval_status_history',
        ['changed_at']
    )
    op.create_index(
        'ix_model_approval_status_history_model_changed',
        'model_approval_status_history',
        ['model_id', 'changed_at']
    )


def downgrade() -> None:
    op.drop_index('ix_model_approval_status_history_model_changed', table_name='model_approval_status_history')
    op.drop_index('ix_model_approval_status_history_changed_at', table_name='model_approval_status_history')
    op.drop_index('ix_model_approval_status_history_model_id', table_name='model_approval_status_history')
    op.drop_table('model_approval_status_history')

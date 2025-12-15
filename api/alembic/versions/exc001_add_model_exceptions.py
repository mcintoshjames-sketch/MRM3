"""Add model exceptions tables and is_system_protected to taxonomy_values

Revision ID: exc001
Revises: 671ed8be0fa4
Create Date: 2025-01-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'exc001'
down_revision: Union[str, None] = '671ed8be0fa4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_system_protected column to taxonomy_values
    op.add_column(
        'taxonomy_values',
        sa.Column(
            'is_system_protected',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='If True, this value cannot be deleted or deactivated (used for exception detection questions)'
        )
    )

    # Create model_exceptions table
    op.create_table(
        'model_exceptions',
        sa.Column('exception_id', sa.Integer(), primary_key=True),
        sa.Column('exception_code', sa.String(16), unique=True, nullable=False, index=True),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column(
            'exception_type',
            sa.String(50),
            nullable=False,
            comment='UNMITIGATED_PERFORMANCE | OUTSIDE_INTENDED_PURPOSE | USE_PRIOR_TO_VALIDATION'
        ),
        # Source tracking FKs
        sa.Column('monitoring_result_id', sa.Integer(), sa.ForeignKey('monitoring_results.result_id', ondelete='SET NULL'), nullable=True),
        sa.Column('attestation_response_id', sa.Integer(), sa.ForeignKey('attestation_responses.response_id', ondelete='SET NULL'), nullable=True),
        sa.Column('deployment_task_id', sa.Integer(), sa.ForeignKey('version_deployment_tasks.task_id', ondelete='SET NULL'), nullable=True),
        # Status
        sa.Column('status', sa.String(20), nullable=False, server_default='OPEN', index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column(
            'auto_closed',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='True if closed automatically by system, False if closed manually by Admin'
        ),
        # Acknowledgment
        sa.Column('acknowledged_by_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledgment_notes', sa.Text(), nullable=True),
        # Closure
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column(
            'closed_by_id',
            sa.Integer(),
            sa.ForeignKey('users.user_id', ondelete='SET NULL'),
            nullable=True,
            comment='NULL for auto-closed exceptions'
        ),
        sa.Column('closure_narrative', sa.Text(), nullable=True, comment='Required when closing (min 10 chars)'),
        sa.Column(
            'closure_reason_id',
            sa.Integer(),
            sa.ForeignKey('taxonomy_values.value_id', ondelete='RESTRICT'),
            nullable=True,
            comment='FK to Exception Closure Reason taxonomy, required when closing'
        ),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        # Check constraints
        sa.CheckConstraint(
            "exception_type IN ('UNMITIGATED_PERFORMANCE', 'OUTSIDE_INTENDED_PURPOSE', 'USE_PRIOR_TO_VALIDATION')",
            name='ck_model_exceptions_type'
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'ACKNOWLEDGED', 'CLOSED')",
            name='ck_model_exceptions_status'
        ),
    )

    # Create partial unique indexes for source entity deduplication
    op.create_index(
        'ix_model_exceptions_monitoring_result_unique',
        'model_exceptions',
        ['monitoring_result_id'],
        unique=True,
        postgresql_where=sa.text('monitoring_result_id IS NOT NULL')
    )
    op.create_index(
        'ix_model_exceptions_attestation_response_unique',
        'model_exceptions',
        ['attestation_response_id'],
        unique=True,
        postgresql_where=sa.text('attestation_response_id IS NOT NULL')
    )
    op.create_index(
        'ix_model_exceptions_deployment_task_unique',
        'model_exceptions',
        ['deployment_task_id'],
        unique=True,
        postgresql_where=sa.text('deployment_task_id IS NOT NULL')
    )

    # Create model_exception_status_history table
    op.create_table(
        'model_exception_status_history',
        sa.Column('history_id', sa.Integer(), primary_key=True),
        sa.Column('exception_id', sa.Integer(), sa.ForeignKey('model_exceptions.exception_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('old_status', sa.String(20), nullable=True, comment='NULL for initial creation'),
        sa.Column('new_status', sa.String(20), nullable=False),
        sa.Column(
            'changed_by_id',
            sa.Integer(),
            sa.ForeignKey('users.user_id', ondelete='SET NULL'),
            nullable=True,
            comment='NULL for system-initiated changes'
        ),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # Drop status history table first (depends on exceptions)
    op.drop_table('model_exception_status_history')

    # Drop indexes before dropping table
    op.drop_index('ix_model_exceptions_deployment_task_unique', table_name='model_exceptions')
    op.drop_index('ix_model_exceptions_attestation_response_unique', table_name='model_exceptions')
    op.drop_index('ix_model_exceptions_monitoring_result_unique', table_name='model_exceptions')

    # Drop exceptions table
    op.drop_table('model_exceptions')

    # Remove is_system_protected column from taxonomy_values
    op.drop_column('taxonomy_values', 'is_system_protected')

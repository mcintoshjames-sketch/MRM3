"""add_bulk_attestation_support

Revision ID: bc3d4e5f6g7h
Revises: ab2c3d4e5f6g
Create Date: 2025-12-03 12:00:00.000000

This migration adds support for bulk attestation submissions:
1. Creates attestation_bulk_submissions table to track bulk submission sessions and drafts
2. Adds bulk_submission_id and is_excluded columns to attestation_records
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'bc3d4e5f6g7h'
down_revision: Union[str, None] = 'ab2c3d4e5f6g'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create attestation_bulk_submissions table
    op.create_table(
        'attestation_bulk_submissions',
        sa.Column('bulk_submission_id', sa.Integer(), primary_key=True),
        sa.Column('cycle_id', sa.Integer(), sa.ForeignKey('attestation_cycles.cycle_id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),

        # Draft state
        sa.Column('status', sa.String(20), nullable=False, server_default='DRAFT',
                  comment='DRAFT or SUBMITTED'),

        # Snapshot of selections (for draft persistence)
        sa.Column('selected_model_ids', postgresql.JSONB(), nullable=True,
                  comment='Array of model IDs selected for bulk attestation'),
        sa.Column('excluded_model_ids', postgresql.JSONB(), nullable=True,
                  comment='Array of model IDs explicitly excluded'),
        sa.Column('draft_responses', postgresql.JSONB(), nullable=True,
                  comment='Array of {question_id, answer, comment} objects'),
        sa.Column('draft_comment', sa.Text(), nullable=True,
                  comment='Overall comment saved in draft'),

        # Submission tracking
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('attestation_count', sa.Integer(), nullable=True,
                  comment='Number of attestation records created on submit'),

        # Audit timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        # Unique constraint: one bulk submission per user per cycle
        sa.UniqueConstraint('cycle_id', 'user_id', name='uq_bulk_submission_cycle_user'),
    )

    # Create indexes for bulk_submissions
    op.create_index('ix_bulk_submissions_cycle_id', 'attestation_bulk_submissions', ['cycle_id'])
    op.create_index('ix_bulk_submissions_user_id', 'attestation_bulk_submissions', ['user_id'])
    op.create_index('ix_bulk_submissions_status', 'attestation_bulk_submissions', ['status'])

    # Add columns to attestation_records
    op.add_column('attestation_records',
        sa.Column('bulk_submission_id', sa.Integer(),
                  sa.ForeignKey('attestation_bulk_submissions.bulk_submission_id', ondelete='SET NULL'),
                  nullable=True,
                  comment='Links to bulk submission that created this record (NULL for individual)')
    )
    op.add_column('attestation_records',
        sa.Column('is_excluded', sa.Boolean(), nullable=False, server_default='false',
                  comment='True if model was excluded from bulk attestation')
    )

    # Create index on bulk_submission_id for efficient lookups
    op.create_index('ix_attestation_records_bulk_submission_id', 'attestation_records', ['bulk_submission_id'])


def downgrade() -> None:
    # Drop indexes from attestation_records
    op.drop_index('ix_attestation_records_bulk_submission_id', table_name='attestation_records')

    # Drop columns from attestation_records
    op.drop_column('attestation_records', 'is_excluded')
    op.drop_column('attestation_records', 'bulk_submission_id')

    # Drop indexes from bulk_submissions
    op.drop_index('ix_bulk_submissions_status', table_name='attestation_bulk_submissions')
    op.drop_index('ix_bulk_submissions_user_id', table_name='attestation_bulk_submissions')
    op.drop_index('ix_bulk_submissions_cycle_id', table_name='attestation_bulk_submissions')

    # Drop bulk_submissions table
    op.drop_table('attestation_bulk_submissions')

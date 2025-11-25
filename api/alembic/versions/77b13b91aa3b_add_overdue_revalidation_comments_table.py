"""add_overdue_revalidation_comments_table

Revision ID: 77b13b91aa3b
Revises: a1b2c3d4e5f6
Create Date: 2025-11-25 05:43:30.341248

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77b13b91aa3b'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create overdue_revalidation_comments table
    op.create_table('overdue_revalidation_comments',
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('validation_request_id', sa.Integer(), nullable=False),
        sa.Column('overdue_type', sa.String(length=30), nullable=False,
                  comment='PRE_SUBMISSION or VALIDATION_IN_PROGRESS'),
        sa.Column('reason_comment', sa.Text(), nullable=False,
                  comment='Explanation for the overdue status'),
        sa.Column('target_date', sa.Date(), nullable=False,
                  comment='Target Submission Date (PRE_SUBMISSION) or Target Completion Date (VALIDATION_IN_PROGRESS)'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False, default=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by_comment_id', sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "overdue_type IN ('PRE_SUBMISSION', 'VALIDATION_IN_PROGRESS')",
            name='check_overdue_type_valid'
        ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(
            ['superseded_by_comment_id'],
            ['overdue_revalidation_comments.comment_id']
        ),
        sa.ForeignKeyConstraint(
            ['validation_request_id'],
            ['validation_requests.request_id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('comment_id')
    )

    # Create indexes for fast lookup
    op.create_index(
        'ix_overdue_comments_request_current',
        'overdue_revalidation_comments',
        ['validation_request_id', 'is_current'],
        unique=False
    )
    op.create_index(
        'ix_overdue_comments_created_by',
        'overdue_revalidation_comments',
        ['created_by_user_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_overdue_comments_created_by', table_name='overdue_revalidation_comments')
    op.drop_index('ix_overdue_comments_request_current', table_name='overdue_revalidation_comments')
    op.drop_table('overdue_revalidation_comments')

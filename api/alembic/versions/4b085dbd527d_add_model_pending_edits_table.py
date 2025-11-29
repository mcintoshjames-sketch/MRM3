"""Add model_pending_edits table for edit approval workflow.

Revision ID: 4b085dbd527d
Revises: bd848d041e15
Create Date: 2024-11-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b085dbd527d'
down_revision: Union[str, None] = 'bd848d041e15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'model_pending_edits',
        sa.Column('pending_edit_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('requested_by_id', sa.Integer(), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('proposed_changes', sa.JSON(), nullable=False),
        sa.Column('original_values', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('pending_edit_id')
    )
    op.create_index('ix_model_pending_edits_model_id', 'model_pending_edits', ['model_id'])
    op.create_index('ix_model_pending_edits_status', 'model_pending_edits', ['status'])


def downgrade() -> None:
    op.drop_index('ix_model_pending_edits_status', table_name='model_pending_edits')
    op.drop_index('ix_model_pending_edits_model_id', table_name='model_pending_edits')
    op.drop_table('model_pending_edits')

"""add validation review outcomes table

Revision ID: 9abe3ff712a2
Revises: 99e85eb5e063
Create Date: 2025-11-19 06:11:39.218201

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9abe3ff712a2'
down_revision: Union[str, None] = '99e85eb5e063'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'validation_review_outcomes',
        sa.Column('review_outcome_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('agrees_with_rating', sa.Boolean(), nullable=True),
        sa.Column('review_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['validation_requests.request_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('review_outcome_id'),
        sa.UniqueConstraint('request_id')
    )


def downgrade() -> None:
    op.drop_table('validation_review_outcomes')

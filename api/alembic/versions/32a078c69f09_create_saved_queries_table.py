"""create_saved_queries_table

Revision ID: 32a078c69f09
Revises: 42617ec50a54
Create Date: 2025-11-22 04:11:39.370265

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32a078c69f09'
down_revision: Union[str, None] = '42617ec50a54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create saved_queries table
    op.create_table(
        'saved_queries',
        sa.Column('query_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('query_name', sa.String(length=255), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('query_id')
    )


def downgrade() -> None:
    # Drop saved_queries table
    op.drop_table('saved_queries')

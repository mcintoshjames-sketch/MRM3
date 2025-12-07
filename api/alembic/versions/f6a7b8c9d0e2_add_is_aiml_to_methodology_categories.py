"""add_is_aiml_to_methodology_categories

Revision ID: f6a7b8c9d0e2
Revises: 65ab50acfc7c
Create Date: 2025-12-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e2'
down_revision: Union[str, None] = '65ab50acfc7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_aiml column with server default to handle existing rows
    op.add_column(
        'methodology_categories',
        sa.Column('is_aiml', sa.Boolean(), nullable=False, server_default='false')
    )
    # Remove the server default after existing rows are populated
    op.alter_column('methodology_categories', 'is_aiml', server_default=None)

    # Pre-flag existing AI/ML categories
    op.execute("""
        UPDATE methodology_categories
        SET is_aiml = true
        WHERE code IN ('AIML_TABULAR', 'AIML_TIMESERIES', 'AIML_NLP', 'AIML_RL')
    """)


def downgrade() -> None:
    op.drop_column('methodology_categories', 'is_aiml')

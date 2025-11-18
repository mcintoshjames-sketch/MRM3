"""add_ownership_type_to_models

Revision ID: 4869cf03f134
Revises: a10c8da9e1ed
Create Date: 2025-11-18 00:36:02.385388

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4869cf03f134'
down_revision: Union[str, None] = 'a10c8da9e1ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ownership_type_id column to models table
    op.add_column('models', sa.Column('ownership_type_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_models_ownership_type', 'models', 'taxonomy_values', ['ownership_type_id'], ['value_id'])


def downgrade() -> None:
    # Remove foreign key and column
    op.drop_constraint('fk_models_ownership_type', 'models', type_='foreignkey')
    op.drop_column('models', 'ownership_type_id')

"""add_ownership_type_to_models

Revision ID: 860eefd8f744
Revises: 38b64e3a491e
Create Date: 2025-11-18 01:18:18.707409

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '860eefd8f744'
down_revision: Union[str, None] = '38b64e3a491e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ownership_type_id column to models table (nullable for backward compatibility)
    op.add_column('models', sa.Column('ownership_type_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_models_ownership_type', 'models', 'taxonomy_values', ['ownership_type_id'], ['value_id'])

    # Set default to GLOBAL for existing models (will be populated after taxonomy is seeded)
    # Note: The actual default value update will happen via seed.py after the taxonomy is created


def downgrade() -> None:
    # Remove foreign key and column
    op.drop_constraint('fk_models_ownership_type', 'models', type_='foreignkey')
    op.drop_column('models', 'ownership_type_id')

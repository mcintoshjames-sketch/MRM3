"""add_model_wholly_owned_region

Revision ID: 64ca7ffe0f97
Revises: 872862f30809
Create Date: 2025-11-19 22:37:23.088419

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64ca7ffe0f97'
down_revision: Union[str, None] = '872862f30809'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add wholly_owned_region_id column to models table
    op.add_column('models', sa.Column('wholly_owned_region_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_models_wholly_owned_region',
        'models', 'regions',
        ['wholly_owned_region_id'], ['region_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop the foreign key and column
    op.drop_constraint('fk_models_wholly_owned_region', 'models', type_='foreignkey')
    op.drop_column('models', 'wholly_owned_region_id')

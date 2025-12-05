"""add_methodology_id_to_models

Revision ID: 65ab50acfc7c
Revises: c9e11e17c9e0
Create Date: 2025-12-05 16:04:17.123315

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '65ab50acfc7c'
down_revision: Union[str, None] = 'c9e11e17c9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add methodology_id FK column to models table
    op.add_column('models', sa.Column('methodology_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_models_methodology_id',
        'models', 'methodologies',
        ['methodology_id'], ['methodology_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_models_methodology_id', 'models', type_='foreignkey')
    op.drop_column('models', 'methodology_id')

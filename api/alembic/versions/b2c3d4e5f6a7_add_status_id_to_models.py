"""Add status_id to models table

Revision ID: b2c3d4e5f6a7
Revises: 0a7a0b86ae95
Create Date: 2025-11-25 23:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '0a7a0b86ae95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status_id column (nullable initially)
    op.add_column('models', sa.Column('status_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_models_status_id',
        'models', 'taxonomy_values',
        ['status_id'], ['value_id']
    )

    # Migrate existing status enum values to new status_id
    # Map: 'Active' -> 157, 'In Development' -> 154, 'Retired' -> 160
    op.execute("""
        UPDATE models
        SET status_id = CASE
            WHEN status = 'Active' THEN 157
            WHEN status = 'In Development' THEN 154
            WHEN status = 'Retired' THEN 160
            ELSE 154  -- Default to In Development for any unexpected values
        END
    """)

    # Note: We keep the old 'status' column for now to avoid breaking existing code
    # It can be dropped in a future migration after all code is updated


def downgrade() -> None:
    # Drop the foreign key and column
    op.drop_constraint('fk_models_status_id', 'models', type_='foreignkey')
    op.drop_column('models', 'status_id')

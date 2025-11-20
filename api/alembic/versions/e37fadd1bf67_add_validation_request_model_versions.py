"""add_validation_request_model_versions

Revision ID: e37fadd1bf67
Revises: 64ca7ffe0f97
Create Date: 2025-11-20 04:23:29.049978

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e37fadd1bf67'
down_revision: Union[str, None] = '64ca7ffe0f97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add version_id column to validation_request_models association table
    op.add_column('validation_request_models',
        sa.Column('version_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint to model_versions table
    op.create_foreign_key(
        'fk_validation_request_models_version',
        'validation_request_models', 'model_versions',
        ['version_id'], ['version_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_validation_request_models_version', 'validation_request_models', type_='foreignkey')

    # Drop version_id column
    op.drop_column('validation_request_models', 'version_id')

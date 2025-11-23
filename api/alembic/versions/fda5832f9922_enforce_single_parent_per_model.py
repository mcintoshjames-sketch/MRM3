"""enforce_single_parent_per_model

Revision ID: fda5832f9922
Revises: 3d1d60cd95d2
Create Date: 2025-11-23 20:28:06.483023

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fda5832f9922'
down_revision: Union[str, None] = '3d1d60cd95d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint on child_model_id to enforce single parent per model
    # Business rule: A sub-model can only have ONE parent model for clear ownership and governance
    op.create_unique_constraint(
        'uq_model_hierarchy_child_model_id',
        'model_hierarchy',
        ['child_model_id']
    )


def downgrade() -> None:
    # Remove unique constraint to allow multiple parents (not recommended)
    op.drop_constraint(
        'uq_model_hierarchy_child_model_id',
        'model_hierarchy',
        type_='unique'
    )

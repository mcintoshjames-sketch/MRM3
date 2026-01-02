"""add products covered to models

Revision ID: pc001
Revises: 359ef41b0bd8
Create Date: 2026-01-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'pc001'
down_revision: Union[str, None] = '359ef41b0bd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('models', sa.Column('products_covered', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('models', 'products_covered')

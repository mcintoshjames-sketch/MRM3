"""merge_sendback_branch

Revision ID: 5b2648700ba6
Revises: b8c9d0e1f2g3, g7c8d9e0f1a2
Create Date: 2025-12-06 23:35:34.717936

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b2648700ba6'
down_revision: Union[str, None] = ('b8c9d0e1f2g3', 'g7c8d9e0f1a2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

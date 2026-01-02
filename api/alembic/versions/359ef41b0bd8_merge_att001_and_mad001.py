"""merge att001 and mad001

Revision ID: 359ef41b0bd8
Revises: att001, mad001
Create Date: 2026-01-02 01:44:46.325301

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '359ef41b0bd8'
down_revision: Union[str, None] = ('att001', 'mad001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

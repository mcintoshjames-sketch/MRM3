"""merge_pc001_and_teams

Revision ID: 02ece2c0ef80
Revises: pc001, t1e2a3m4s5x6
Create Date: 2026-01-03 09:56:41.319721

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02ece2c0ef80'
down_revision: Union[str, Sequence[str], None] = ('pc001', 't1e2a3m4s5x6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

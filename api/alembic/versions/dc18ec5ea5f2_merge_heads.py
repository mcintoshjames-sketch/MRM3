"""merge heads

Revision ID: dc18ec5ea5f2
Revises: mp002_add_monitoring_memberships_and_cycle_scopes, n5o6p7q8r9s0
Create Date: 2026-01-11 15:02:48.484758

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc18ec5ea5f2'
down_revision: Union[str, None] = ('mp002_add_monitoring_memberships_and_cycle_scopes', 'n5o6p7q8r9s0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

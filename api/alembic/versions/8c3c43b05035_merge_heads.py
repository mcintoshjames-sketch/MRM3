"""merge heads

Revision ID: 8c3c43b05035
Revises: 80e8411345e1, ma001_add_manual_approval_fields
Create Date: 2026-01-11 17:40:01.959869

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c3c43b05035'
down_revision: Union[str, None] = ('80e8411345e1', 'ma001_add_manual_approval_fields')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

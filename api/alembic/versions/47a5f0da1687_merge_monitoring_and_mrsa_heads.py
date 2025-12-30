"""merge monitoring and mrsa heads

Revision ID: 47a5f0da1687
Revises: ac1d2e3f4g5h, mrsa003_remove_grace_period_days
Create Date: 2025-12-30 06:44:02.051969

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47a5f0da1687'
down_revision: Union[str, None] = ('ac1d2e3f4g5h', 'mrsa003_remove_grace_period_days')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

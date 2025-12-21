"""merge sc001 and validation_findings

Revision ID: 230e85633b3d
Revises: 5809df3fd79c, sc001
Create Date: 2025-12-18 19:18:14.671984

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '230e85633b3d'
down_revision: Union[str, None] = ('5809df3fd79c', 'sc001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""merge_heads

Revision ID: f36f4f06ec65
Revises: 4b085dbd527d, q7r8s9t0u1v2
Create Date: 2025-11-30 13:10:12.761463

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f36f4f06ec65'
down_revision: Union[str, None] = ('4b085dbd527d', 'q7r8s9t0u1v2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""add enforce_validation_plan flag to regions

Revision ID: j1k2l3m4n5
Revises: 6105c56a44ec
Create Date: 2025-11-22 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j1k2l3m4n5'
down_revision: Union[str, None] = 'df64c68f39b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'regions',
        sa.Column(
            'enforce_validation_plan',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        )
    )


def downgrade() -> None:
    op.drop_column('regions', 'enforce_validation_plan')

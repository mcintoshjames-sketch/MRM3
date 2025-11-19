"""set_regions_require_approval

Revision ID: 872862f30809
Revises: 5c8561c8fca3
Create Date: 2025-11-19 21:31:54.014401

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '872862f30809'
down_revision: Union[str, None] = '5c8561c8fca3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Set requires_regional_approval to True for all existing regions
    op.execute("""
        UPDATE regions
        SET requires_regional_approval = true
        WHERE requires_regional_approval = false
    """)


def downgrade() -> None:
    # Revert requires_regional_approval back to False
    op.execute("""
        UPDATE regions
        SET requires_regional_approval = false
        WHERE requires_regional_approval = true
    """)

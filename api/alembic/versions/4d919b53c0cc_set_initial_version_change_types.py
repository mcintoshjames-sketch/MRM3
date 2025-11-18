"""set_initial_version_change_types

Revision ID: 4d919b53c0cc
Revises: 026d874c626f
Create Date: 2025-11-18 03:04:37.208014

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d919b53c0cc'
down_revision: Union[str, None] = '026d874c626f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Set change_type_id = 1 (New Model Development) for all version 1.0 records
    # These represent initial model versions created before the taxonomy was introduced
    op.execute("""
        UPDATE model_versions
        SET change_type_id = 1
        WHERE version_number = '1.0'
          AND change_type_id IS NULL
    """)


def downgrade() -> None:
    # Revert change_type_id to NULL for version 1.0 records
    op.execute("""
        UPDATE model_versions
        SET change_type_id = NULL
        WHERE version_number = '1.0'
          AND change_type_id = 1
    """)

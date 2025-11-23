"""add_mv_approval_snapshot_to_versions

Revision ID: 4b1d659c419b
Revises: 594bfb3d1385
Create Date: 2025-11-23 15:20:09.441070

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b1d659c419b'
down_revision: Union[str, None] = '594bfb3d1385'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add point-in-time snapshot for MV approval requirement compliance tracking.

    This allows reporting on whether a change complied with approval requirements
    IN PLACE AT THE TIME OF THE CHANGE, even if taxonomy changes later.
    """
    # Add column as nullable initially (for backfill)
    op.add_column(
        'model_versions',
        sa.Column(
            'change_requires_mv_approval',
            sa.Boolean(),
            nullable=True,
            comment='Point-in-time snapshot: Did this change require MV approval at submission time?'
        )
    )

    # Backfill existing data from current change type state
    # This uses current taxonomy state as best approximation of historical requirements
    op.execute("""
        UPDATE model_versions
        SET change_requires_mv_approval = model_change_types.requires_mv_approval
        FROM model_change_types
        WHERE model_versions.change_type_id = model_change_types.change_type_id
    """)

    # For versions without change_type_id (legacy), use legacy MAJOR/MINOR logic
    # MAJOR changes require validation, MINOR do not
    op.execute("""
        UPDATE model_versions
        SET change_requires_mv_approval = (change_type = 'MAJOR')
        WHERE change_type_id IS NULL
    """)


def downgrade() -> None:
    """Remove the compliance snapshot column."""
    op.drop_column('model_versions', 'change_requires_mv_approval')

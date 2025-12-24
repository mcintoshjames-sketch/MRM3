"""Protect CHANGE validation type from deletion.

Since the CHANGE validation type (code='CHANGE') is now referenced in
system logic for version-requirement enforcement, it must be protected
from accidental deletion by administrators.

Revision ID: chg001
Revises: 230e85633b3d
Create Date: 2025-12-23

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'chg001'
down_revision: Union[str, None] = '230e85633b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Protect CHANGE validation type from deletion."""
    op.execute("""
        UPDATE taxonomy_values
        SET is_system_protected = true
        WHERE code = 'CHANGE'
        AND taxonomy_id = (
            SELECT taxonomy_id FROM taxonomies WHERE name = 'Validation Type'
        )
    """)


def downgrade() -> None:
    """Remove protection from CHANGE validation type."""
    op.execute("""
        UPDATE taxonomy_values
        SET is_system_protected = false
        WHERE code = 'CHANGE'
        AND taxonomy_id = (
            SELECT taxonomy_id FROM taxonomies WHERE name = 'Validation Type'
        )
    """)

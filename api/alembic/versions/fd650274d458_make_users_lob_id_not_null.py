"""make_users_lob_id_not_null

Revision ID: fd650274d458
Revises: lob001
Create Date: 2025-12-07 16:21:55.633401

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd650274d458'
down_revision: Union[str, None] = 'lob001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make users.lob_id NOT NULL after ensuring all users have LOB assigned.

    The previous migration (lob001) already assigns LOB to all existing users
    via round-robin distribution. This migration enforces the NOT NULL constraint
    to ensure all future users must have a LOB assignment.
    """
    # Safety check: Ensure no users have NULL lob_id before applying constraint
    # This handles any edge cases where users were created between migrations
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT COUNT(*) FROM users WHERE lob_id IS NULL"
    ))
    null_count = result.scalar() or 0

    if null_count > 0:
        # Assign any remaining NULL users to the first available LOB unit
        conn.execute(sa.text("""
            UPDATE users
            SET lob_id = (SELECT lob_id FROM lob_units WHERE is_active = true ORDER BY lob_id LIMIT 1)
            WHERE lob_id IS NULL
        """))

    # Now safely set NOT NULL constraint
    op.alter_column('users', 'lob_id',
                    existing_type=sa.Integer(),
                    nullable=False)


def downgrade() -> None:
    """Revert lob_id back to nullable."""
    op.alter_column('users', 'lob_id',
                    existing_type=sa.Integer(),
                    nullable=True)

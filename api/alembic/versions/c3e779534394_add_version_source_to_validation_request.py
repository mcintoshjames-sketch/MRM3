"""add_version_source_to_validation_request

Revision ID: c3e779534394
Revises: exc002
Create Date: 2025-12-17 18:24:21.136935

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e779534394'
down_revision: Union[str, None] = 'exc002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add version_source column to validation_requests table."""
    op.add_column(
        'validation_requests',
        sa.Column(
            'version_source',
            sa.String(length=20),
            nullable=True,
            comment="How version was linked: 'explicit' (user selected) or 'inferred' (system auto-suggested)"
        )
    )


def downgrade() -> None:
    """Remove version_source column from validation_requests table."""
    op.drop_column('validation_requests', 'version_source')

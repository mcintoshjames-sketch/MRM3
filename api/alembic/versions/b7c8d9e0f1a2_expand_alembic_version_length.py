"""expand alembic version length

Revision ID: b7c8d9e0f1a2
Revises: mo001_add_model_overlays
Create Date: 2026-01-11 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "mo001_add_model_overlays"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        type_=sa.String(length=128),
        existing_type=sa.String(length=32),
        existing_nullable=False
    )


def downgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        type_=sa.String(length=32),
        existing_type=sa.String(length=128),
        existing_nullable=False
    )

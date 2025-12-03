"""Merge migration branches.

Revision ID: b9c0d1e2f3a4
Revises: a0b1c2d3e4f5, a8b9c0d1e2f3
Create Date: 2025-12-02

This migration merges the two branches:
- a0b1c2d3e4f5 (simplify validation priority)
- a8b9c0d1e2f3 (add downgrade_notches)
"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b9c0d1e2f3a4'
down_revision: tuple = ('a0b1c2d3e4f5', 'a8b9c0d1e2f3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

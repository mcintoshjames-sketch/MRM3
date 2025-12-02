"""add_taxonomy_bucket_fields

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2025-12-02 10:00:00.000000

This migration adds support for bucket-based taxonomies (like Past Due Level)
by adding:
1. taxonomy_type column to taxonomies table ('standard' or 'bucket')
2. min_days and max_days columns to taxonomy_values for range-based buckets
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add taxonomy_type column to taxonomies table
    op.add_column(
        'taxonomies',
        sa.Column(
            'taxonomy_type',
            sa.String(20),
            nullable=False,
            server_default='standard',
            comment="Type of taxonomy: 'standard' or 'bucket' (range-based)"
        )
    )

    # Add min_days and max_days columns to taxonomy_values table
    op.add_column(
        'taxonomy_values',
        sa.Column(
            'min_days',
            sa.Integer(),
            nullable=True,
            comment="Minimum days (inclusive) for bucket. NULL means unbounded (negative infinity)."
        )
    )
    op.add_column(
        'taxonomy_values',
        sa.Column(
            'max_days',
            sa.Integer(),
            nullable=True,
            comment="Maximum days (inclusive) for bucket. NULL means unbounded (positive infinity)."
        )
    )


def downgrade() -> None:
    # Remove the columns
    op.drop_column('taxonomy_values', 'max_days')
    op.drop_column('taxonomy_values', 'min_days')
    op.drop_column('taxonomies', 'taxonomy_type')

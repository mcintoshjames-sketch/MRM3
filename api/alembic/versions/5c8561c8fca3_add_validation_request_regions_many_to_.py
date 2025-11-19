"""add_validation_request_regions_many_to_many

Revision ID: 5c8561c8fca3
Revises: 4ed613a27144
Create Date: 2025-11-19 20:00:57.978843

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c8561c8fca3'
down_revision: Union[str, None] = '4ed613a27144'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create association table for many-to-many relationship
    op.create_table(
        'validation_request_regions',
        sa.Column('request_id', sa.Integer(), sa.ForeignKey('validation_requests.request_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('region_id', sa.Integer(), sa.ForeignKey('regions.region_id', ondelete='CASCADE'), primary_key=True)
    )

    # Migrate existing data from region_id column to association table
    op.execute("""
        INSERT INTO validation_request_regions (request_id, region_id)
        SELECT request_id, region_id
        FROM validation_requests
        WHERE region_id IS NOT NULL
    """)

    # Drop the old region_id column
    op.drop_column('validation_requests', 'region_id')


def downgrade() -> None:
    # Add back the region_id column
    op.add_column('validation_requests', sa.Column('region_id', sa.Integer(), sa.ForeignKey('regions.region_id', ondelete='SET NULL'), nullable=True))

    # Migrate data back (take first region if multiple)
    op.execute("""
        UPDATE validation_requests vr
        SET region_id = (
            SELECT region_id
            FROM validation_request_regions vrr
            WHERE vrr.request_id = vr.request_id
            LIMIT 1
        )
    """)

    # Drop the association table
    op.drop_table('validation_request_regions')

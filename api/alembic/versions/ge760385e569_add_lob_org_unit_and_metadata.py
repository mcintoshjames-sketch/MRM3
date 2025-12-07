"""add LOB org_unit and metadata fields

Revision ID: ge760385e569
Revises: fd650274d458
Create Date: 2025-12-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ge760385e569'
down_revision: Union[str, None] = 'fd650274d458'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns (nullable initially for org_unit to allow backfill)
    op.add_column('lob_units', sa.Column('org_unit', sa.String(5), nullable=True))
    op.add_column('lob_units', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('lob_units', sa.Column('contact_name', sa.String(255), nullable=True))
    op.add_column('lob_units', sa.Column('org_description', sa.Text(), nullable=True))
    op.add_column('lob_units', sa.Column('legal_entity_id', sa.String(50), nullable=True))
    op.add_column('lob_units', sa.Column('legal_entity_name', sa.String(255), nullable=True))
    op.add_column('lob_units', sa.Column('short_name', sa.String(100), nullable=True))
    op.add_column('lob_units', sa.Column('status_code', sa.String(20), nullable=True))
    op.add_column('lob_units', sa.Column('tier', sa.String(50), nullable=True))

    # 2. Backfill org_unit for existing rows with synthetic S#### values
    # Format: S0001, S0002, etc. - alpha prefix guarantees no collision with real numeric codes
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT lob_id FROM lob_units ORDER BY lob_id"))
    rows = list(result)
    for i, row in enumerate(rows, start=1):
        synthetic_org_unit = f"S{i:04d}"  # S0001, S0002, ..., S9999
        conn.execute(
            sa.text("UPDATE lob_units SET org_unit = :org_unit WHERE lob_id = :lob_id"),
            {"org_unit": synthetic_org_unit, "lob_id": row[0]}
        )

    # 3. Make org_unit NOT NULL after backfill
    op.alter_column('lob_units', 'org_unit', nullable=False)

    # 4. Add unique constraint and index for org_unit
    op.create_unique_constraint('uq_lob_units_org_unit', 'lob_units', ['org_unit'])
    op.create_index('ix_lob_units_org_unit', 'lob_units', ['org_unit'])


def downgrade() -> None:
    op.drop_index('ix_lob_units_org_unit', table_name='lob_units')
    op.drop_constraint('uq_lob_units_org_unit', 'lob_units', type_='unique')
    op.drop_column('lob_units', 'tier')
    op.drop_column('lob_units', 'status_code')
    op.drop_column('lob_units', 'short_name')
    op.drop_column('lob_units', 'legal_entity_name')
    op.drop_column('lob_units', 'legal_entity_id')
    op.drop_column('lob_units', 'org_description')
    op.drop_column('lob_units', 'contact_name')
    op.drop_column('lob_units', 'description')
    op.drop_column('lob_units', 'org_unit')

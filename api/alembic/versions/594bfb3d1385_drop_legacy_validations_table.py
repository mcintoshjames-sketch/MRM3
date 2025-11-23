"""drop_legacy_validations_table

Revision ID: 594bfb3d1385
Revises: j1k2l3m4n5
Create Date: 2025-11-23 14:31:02.937106

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '594bfb3d1385'
down_revision: Union[str, None] = 'j1k2l3m4n5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the legacy validations table if it exists
    # This table was replaced by the validation_requests workflow system
    # Note: Table may not exist in all databases (it was never actually used)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)

    if 'validations' in inspector.get_table_names():
        op.drop_table('validations')


def downgrade() -> None:
    # Recreate the validations table if we need to rollback
    # (Structure based on original creation migration)
    op.create_table('validations',
        sa.Column('validation_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('validation_date', sa.Date(), nullable=False),
        sa.Column('validator_id', sa.Integer(), nullable=False),
        sa.Column('validation_type_id', sa.Integer(), nullable=False),
        sa.Column('outcome_id', sa.Integer(), nullable=False),
        sa.Column('scope_id', sa.Integer(), nullable=False),
        sa.Column('findings_summary', sa.Text(), nullable=True),
        sa.Column('report_reference', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('region_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outcome_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['region_id'], ['regions.region_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scope_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['validation_type_id'], ['taxonomy_values.value_id'], ),
        sa.ForeignKeyConstraint(['validator_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('validation_id')
    )
    op.create_index('ix_validations_region_id', 'validations', ['region_id'], unique=False)

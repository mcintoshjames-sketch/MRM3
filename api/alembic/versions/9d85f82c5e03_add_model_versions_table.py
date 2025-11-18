"""add_model_versions_table

Revision ID: 9d85f82c5e03
Revises: 8561686cdb50
Create Date: 2025-11-18 01:55:38.570074

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d85f82c5e03'
down_revision: Union[str, None] = '8561686cdb50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create model_versions table
    op.create_table(
        'model_versions',
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.String(length=50), nullable=False),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('change_description', sa.Text(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('production_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('validation_request_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('version_id'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.user_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['validation_request_id'], ['validation_requests.request_id'], ondelete='SET NULL'),
        sa.UniqueConstraint('model_id', 'version_number', name='uq_model_version_number')
    )
    op.create_index(op.f('ix_model_versions_model_id'), 'model_versions', ['model_id'], unique=False)
    op.create_index(op.f('ix_model_versions_status'), 'model_versions', ['status'], unique=False)

    # Seed version 1.0 for all existing models
    # Get all models and create initial version for each
    op.execute("""
        INSERT INTO model_versions (model_id, version_number, change_type, change_description,
                                   created_by_id, created_at, production_date, status)
        SELECT
            model_id,
            '1.0' as version_number,
            'MAJOR' as change_type,
            'Initial model version' as change_description,
            owner_id as created_by_id,
            created_at,
            created_at as production_date,
            'ACTIVE' as status
        FROM models
    """)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_model_versions_status'), table_name='model_versions')
    op.drop_index(op.f('ix_model_versions_model_id'), table_name='model_versions')
    # Drop table
    op.drop_table('model_versions')

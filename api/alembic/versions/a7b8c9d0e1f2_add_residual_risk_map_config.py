"""Add residual risk map config table.

Revision ID: a7b8c9d0e1f2
Revises: z6a7b8c9d0e1
Create Date: 2025-12-01

This migration creates the residual_risk_map_configs table for storing
the configurable residual risk map matrix.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = 'z6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'residual_risk_map_configs',
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('version_name', sa.String(200), nullable=True),
        sa.Column('matrix_config', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('config_id'),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'],
            ['users.user_id'],
            ondelete='SET NULL'
        ),
    )

    # Create index for active config lookup
    op.create_index(
        'ix_residual_risk_map_configs_is_active',
        'residual_risk_map_configs',
        ['is_active']
    )


def downgrade() -> None:
    op.drop_index('ix_residual_risk_map_configs_is_active', table_name='residual_risk_map_configs')
    op.drop_table('residual_risk_map_configs')

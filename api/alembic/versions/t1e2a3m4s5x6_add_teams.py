"""Add teams and team assignment for LOB units.

Revision ID: t1e2a3m4s5x6
Revises: z6a7b8c9d0e1
Create Date: 2025-12-01
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 't1e2a3m4s5x6'
down_revision = 'z6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'teams',
        sa.Column('team_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.add_column('lob_units', sa.Column('team_id', sa.Integer(), nullable=True))
    op.create_index('ix_lob_units_team_id', 'lob_units', ['team_id'])
    op.create_foreign_key(
        'fk_lob_units_team_id',
        'lob_units',
        'teams',
        ['team_id'],
        ['team_id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint('fk_lob_units_team_id', 'lob_units', type_='foreignkey')
    op.drop_index('ix_lob_units_team_id', table_name='lob_units')
    op.drop_column('lob_units', 'team_id')
    op.drop_table('teams')

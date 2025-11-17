"""Add vendor and model enhancements

Revision ID: c4d25e6f7891
Revises: b3ab15c4c70f
Create Date: 2025-11-16 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d25e6f7891'
down_revision: Union[str, None] = 'b3ab15c4c70f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create vendors table
    op.create_table('vendors',
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('contact_info', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('vendor_id'),
        sa.UniqueConstraint('name')
    )

    # Add new columns to models table
    op.add_column('models', sa.Column('development_type', sa.String(length=50), nullable=False, server_default='In-House'))
    op.add_column('models', sa.Column('developer_id', sa.Integer(), nullable=True))
    op.add_column('models', sa.Column('vendor_id', sa.Integer(), nullable=True))

    # Add foreign key constraints
    op.create_foreign_key('fk_models_developer_id', 'models', 'users', ['developer_id'], ['user_id'])
    op.create_foreign_key('fk_models_vendor_id', 'models', 'vendors', ['vendor_id'], ['vendor_id'])

    # Create model_users junction table
    op.create_table('model_users',
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('model_id', 'user_id')
    )


def downgrade() -> None:
    # Drop model_users table
    op.drop_table('model_users')

    # Drop foreign key constraints
    op.drop_constraint('fk_models_vendor_id', 'models', type_='foreignkey')
    op.drop_constraint('fk_models_developer_id', 'models', type_='foreignkey')

    # Drop new columns from models table
    op.drop_column('models', 'vendor_id')
    op.drop_column('models', 'developer_id')
    op.drop_column('models', 'development_type')

    # Drop vendors table
    op.drop_table('vendors')

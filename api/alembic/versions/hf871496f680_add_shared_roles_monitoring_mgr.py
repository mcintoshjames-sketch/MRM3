"""add shared roles and monitoring manager

Revision ID: hf871496f680
Revises: ge760385e569
Create Date: 2025-01-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'hf871496f680'
down_revision: Union[str, None] = 'ge760385e569'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add shared_owner_id column
    op.add_column('models', sa.Column('shared_owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_models_shared_owner',
        'models', 'users',
        ['shared_owner_id'], ['user_id'],
        ondelete='SET NULL'
    )

    # Add shared_developer_id column
    op.add_column('models', sa.Column('shared_developer_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_models_shared_developer',
        'models', 'users',
        ['shared_developer_id'], ['user_id'],
        ondelete='SET NULL'
    )

    # Add monitoring_manager_id column
    op.add_column('models', sa.Column('monitoring_manager_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_models_monitoring_manager',
        'models', 'users',
        ['monitoring_manager_id'], ['user_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_models_monitoring_manager', 'models', type_='foreignkey')
    op.drop_column('models', 'monitoring_manager_id')

    op.drop_constraint('fk_models_shared_developer', 'models', type_='foreignkey')
    op.drop_column('models', 'shared_developer_id')

    op.drop_constraint('fk_models_shared_owner', 'models', type_='foreignkey')
    op.drop_column('models', 'shared_owner_id')

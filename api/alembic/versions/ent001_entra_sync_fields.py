"""entra_sync_fields

Revision ID: ent001
Revises: c1d2e3f4a5b6
Create Date: 2026-01-15

This migration:
1. Adds in_recycle_bin and deleted_datetime to entra_users table
2. Renames entra_id -> object_id in entra_users table
3. Adds azure_state, local_status, azure_deleted_on to users table
4. Renames entra_id -> azure_object_id in users table (drops FK)
5. Backfills existing data to prevent auth lockouts
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ent001'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection for checking constraints
    conn = op.get_bind()

    # 1. Add new columns to entra_users
    op.add_column('entra_users', sa.Column('in_recycle_bin', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('entra_users', sa.Column('deleted_datetime', sa.DateTime(), nullable=True))

    # 2. Rename entra_id -> object_id in entra_users
    op.alter_column('entra_users', 'entra_id', new_column_name='object_id')

    # 3. Drop FK constraint from users table first (if exists)
    # Check if constraint exists before trying to drop it
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'users_entra_id_fkey'
        AND table_name = 'users'
    """))
    if result.fetchone():
        op.drop_constraint('users_entra_id_fkey', 'users', type_='foreignkey')

    # 4. Rename entra_id -> azure_object_id in users
    op.alter_column('users', 'entra_id', new_column_name='azure_object_id')

    # 5. Add new columns to users with defaults
    op.add_column('users', sa.Column('azure_state', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('local_status', sa.String(20), nullable=False, server_default='ENABLED'))
    op.add_column('users', sa.Column('azure_deleted_on', sa.DateTime(), nullable=True))

    # 6. BACKFILL: Set azure_state='EXISTS' for all Entra-linked users
    op.execute("""
        UPDATE users
        SET azure_state = 'EXISTS'
        WHERE azure_object_id IS NOT NULL
    """)


def downgrade() -> None:
    # Reverse the changes

    # 1. Drop new columns from users
    op.drop_column('users', 'azure_deleted_on')
    op.drop_column('users', 'local_status')
    op.drop_column('users', 'azure_state')

    # 2. Rename azure_object_id -> entra_id in users
    op.alter_column('users', 'azure_object_id', new_column_name='entra_id')

    # 3. Rename object_id -> entra_id in entra_users
    op.alter_column('entra_users', 'object_id', new_column_name='entra_id')

    # 4. Re-add FK constraint
    op.create_foreign_key(
        'users_entra_id_fkey',
        'users',
        'entra_users',
        ['entra_id'],
        ['entra_id'],
        ondelete='SET NULL'
    )

    # 5. Drop new columns from entra_users
    op.drop_column('entra_users', 'deleted_datetime')
    op.drop_column('entra_users', 'in_recycle_bin')

"""Refactor attestation_change_proposals to attestation_change_links

Revision ID: cd4e5f6g7h8i
Revises: bc3d4e5f6g7h
Create Date: 2025-12-03

This migration simplifies the change proposal system to a lightweight link tracking table:
1. Renames table attestation_change_proposals -> attestation_change_links
2. Renames primary key proposal_id -> link_id
3. Drops columns: proposed_data, status, admin_comment, decided_by_user_id, decided_at
4. Adds column: decommissioning_request_id (FK to decommissioning_requests)
5. Updates change_type values: UPDATE_EXISTING -> MODEL_EDIT
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd4e5f6g7h8i'
down_revision: Union[str, None] = 'bc3d4e5f6g7h'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Update change_type values before schema changes
    op.execute(
        "UPDATE attestation_change_proposals SET change_type = 'MODEL_EDIT' WHERE change_type = 'UPDATE_EXISTING'"
    )

    # Step 2: Drop old indexes
    op.drop_index('ix_attestation_change_proposals_status', table_name='attestation_change_proposals')
    op.drop_index('ix_attestation_change_proposals_attestation_id', table_name='attestation_change_proposals')

    # Step 3: Drop foreign key constraint for decided_by_user_id
    op.drop_constraint(
        'attestation_change_proposals_decided_by_user_id_fkey',
        'attestation_change_proposals',
        type_='foreignkey'
    )

    # Step 4: Drop unnecessary columns
    op.drop_column('attestation_change_proposals', 'proposed_data')
    op.drop_column('attestation_change_proposals', 'status')
    op.drop_column('attestation_change_proposals', 'admin_comment')
    op.drop_column('attestation_change_proposals', 'decided_by_user_id')
    op.drop_column('attestation_change_proposals', 'decided_at')

    # Step 5: Add decommissioning_request_id column
    op.add_column(
        'attestation_change_proposals',
        sa.Column('decommissioning_request_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'attestation_change_links_decommissioning_request_id_fkey',
        'attestation_change_proposals',
        'decommissioning_requests',
        ['decommissioning_request_id'],
        ['request_id'],
        ondelete='SET NULL'
    )

    # Step 6: Rename primary key column
    op.alter_column('attestation_change_proposals', 'proposal_id',
                    new_column_name='link_id')

    # Step 7: Rename table
    op.rename_table('attestation_change_proposals', 'attestation_change_links')

    # Step 8: Recreate index with new name
    op.create_index('ix_attestation_change_links_attestation_id', 'attestation_change_links', ['attestation_id'])


def downgrade() -> None:
    # Step 1: Drop new index
    op.drop_index('ix_attestation_change_links_attestation_id', table_name='attestation_change_links')

    # Step 2: Rename table back
    op.rename_table('attestation_change_links', 'attestation_change_proposals')

    # Step 3: Rename primary key column back
    op.alter_column('attestation_change_proposals', 'link_id',
                    new_column_name='proposal_id')

    # Step 4: Drop decommissioning_request_id
    op.drop_constraint(
        'attestation_change_links_decommissioning_request_id_fkey',
        'attestation_change_proposals',
        type_='foreignkey'
    )
    op.drop_column('attestation_change_proposals', 'decommissioning_request_id')

    # Step 5: Add back the dropped columns
    op.add_column(
        'attestation_change_proposals',
        sa.Column('proposed_data', sa.JSON(), nullable=True)
    )
    op.add_column(
        'attestation_change_proposals',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING')
    )
    op.add_column(
        'attestation_change_proposals',
        sa.Column('admin_comment', sa.Text(), nullable=True)
    )
    op.add_column(
        'attestation_change_proposals',
        sa.Column('decided_by_user_id', sa.Integer(), nullable=True)
    )
    op.add_column(
        'attestation_change_proposals',
        sa.Column('decided_at', sa.DateTime(), nullable=True)
    )

    # Step 6: Add back foreign key for decided_by_user_id
    op.create_foreign_key(
        'attestation_change_proposals_decided_by_user_id_fkey',
        'attestation_change_proposals',
        'users',
        ['decided_by_user_id'],
        ['user_id'],
        ondelete='SET NULL'
    )

    # Step 7: Recreate old indexes
    op.create_index('ix_attestation_change_proposals_attestation_id', 'attestation_change_proposals', ['attestation_id'])
    op.create_index('ix_attestation_change_proposals_status', 'attestation_change_proposals', ['status'])

    # Step 8: Revert change_type values
    op.execute(
        "UPDATE attestation_change_proposals SET change_type = 'UPDATE_EXISTING' WHERE change_type = 'MODEL_EDIT'"
    )

"""fix_duplicate_model_versions_add_unique_constraint

Revision ID: 753a34899e81
Revises: x4y5z6a7b8c9
Create Date: 2025-12-01 17:32:04.578386

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '753a34899e81'
down_revision: Union[str, None] = 'x4y5z6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Find and delete duplicate model versions
    # For each (model_id, version_number) combination, keep the record with the lowest version_id
    # First, delete related records that reference the duplicate versions

    conn = op.get_bind()

    # Find duplicate version_ids to delete (keep the one with lowest version_id)
    result = conn.execute(sa.text("""
        SELECT version_id FROM model_versions mv1
        WHERE EXISTS (
            SELECT 1 FROM model_versions mv2
            WHERE mv2.model_id = mv1.model_id
            AND mv2.version_number = mv1.version_number
            AND mv2.version_id < mv1.version_id
        )
    """))
    duplicate_ids = [row[0] for row in result.fetchall()]

    if duplicate_ids:
        # Convert to tuple string for SQL IN clause
        ids_str = ','.join(str(id) for id in duplicate_ids)

        # Delete references in model_regions (SET NULL on version_id)
        conn.execute(sa.text(f"""
            UPDATE model_regions SET version_id = NULL
            WHERE version_id IN ({ids_str})
        """))

        # Delete references in model_version_regions
        conn.execute(sa.text(f"""
            DELETE FROM model_version_regions
            WHERE version_id IN ({ids_str})
        """))

        # Delete references in validation_request_models
        conn.execute(sa.text(f"""
            DELETE FROM validation_request_models
            WHERE version_id IN ({ids_str})
        """))

        # Delete references in version_deployment_tasks
        conn.execute(sa.text(f"""
            DELETE FROM version_deployment_tasks
            WHERE version_id IN ({ids_str})
        """))

        # Now delete the duplicate model_versions
        conn.execute(sa.text(f"""
            DELETE FROM model_versions
            WHERE version_id IN ({ids_str})
        """))

        print(f"Deleted {len(duplicate_ids)} duplicate model version records: {duplicate_ids}")

    # Step 2: Add unique constraint on (model_id, version_number)
    op.create_unique_constraint(
        'uq_model_versions_model_id_version_number',
        'model_versions',
        ['model_id', 'version_number']
    )


def downgrade() -> None:
    # Remove the unique constraint
    op.drop_constraint(
        'uq_model_versions_model_id_version_number',
        'model_versions',
        type_='unique'
    )

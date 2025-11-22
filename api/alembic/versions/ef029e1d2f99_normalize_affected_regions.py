"""normalize_affected_regions

Revision ID: ef029e1d2f99
Revises: 32a078c69f09
Create Date: 2025-11-22 04:41:28.416666

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef029e1d2f99'
down_revision: Union[str, None] = '32a078c69f09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the model_version_regions join table
    op.create_table(
        'model_version_regions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('region_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['version_id'], ['model_versions.version_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.region_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version_id', 'region_id', name='uq_version_region')
    )

    # 2. Create indexes for better query performance
    op.create_index('ix_model_version_regions_version_id', 'model_version_regions', ['version_id'])
    op.create_index('ix_model_version_regions_region_id', 'model_version_regions', ['region_id'])

    # 3. Migrate existing data from affected_region_ids JSON to join table
    # This uses raw SQL to parse the JSON and insert rows
    connection = op.get_bind()

    # Get all versions with affected_region_ids
    # We'll filter in Python to handle various JSON formats safely
    result = connection.execute(sa.text("""
        SELECT version_id, affected_region_ids
        FROM model_versions
        WHERE affected_region_ids IS NOT NULL
    """))

    # For each version, parse the JSON and insert into join table
    import json
    for row in result:
        version_id = row[0]
        affected_region_ids_json = row[1]

        try:
            # Parse the JSON array
            if isinstance(affected_region_ids_json, str):
                region_ids = json.loads(affected_region_ids_json)
            elif isinstance(affected_region_ids_json, list):
                # Already a list (psycopg2 might have already parsed it)
                region_ids = affected_region_ids_json
            else:
                # Unknown format, skip
                print(f"Warning: Unexpected format for affected_region_ids in version_id={version_id}: {type(affected_region_ids_json)}")
                continue

            # Only process if it's a non-empty list
            if isinstance(region_ids, list) and len(region_ids) > 0:
                for region_id in region_ids:
                    # Ensure region_id is an integer
                    if isinstance(region_id, (int, float)):
                        connection.execute(sa.text("""
                            INSERT INTO model_version_regions (version_id, region_id)
                            VALUES (:version_id, :region_id)
                            ON CONFLICT (version_id, region_id) DO NOTHING
                        """), {"version_id": version_id, "region_id": int(region_id)})
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            # Skip invalid JSON
            print(f"Warning: Could not parse affected_region_ids for version_id={version_id}: {e}")
            continue

    # 4. Drop the old affected_region_ids column
    op.drop_column('model_versions', 'affected_region_ids')


def downgrade() -> None:
    # 1. Re-add the affected_region_ids column
    from sqlalchemy.dialects import postgresql
    op.add_column('model_versions',
        sa.Column('affected_region_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True,
                  comment='List of region IDs affected by this change (for REGIONAL scope)')
    )

    # 2. Migrate data back from join table to JSON column
    connection = op.get_bind()

    # Get all version-region mappings
    result = connection.execute(sa.text("""
        SELECT version_id, array_agg(region_id ORDER BY region_id) as region_ids
        FROM model_version_regions
        GROUP BY version_id
    """))

    # Update each version with the JSON array
    import json
    for row in result:
        version_id = row[0]
        region_ids = list(row[1]) if row[1] else []

        connection.execute(sa.text("""
            UPDATE model_versions
            SET affected_region_ids = :region_ids_json
            WHERE version_id = :version_id
        """), {"version_id": version_id, "region_ids_json": json.dumps(region_ids)})

    # 3. Drop indexes
    op.drop_index('ix_model_version_regions_region_id', table_name='model_version_regions')
    op.drop_index('ix_model_version_regions_version_id', table_name='model_version_regions')

    # 4. Drop the join table
    op.drop_table('model_version_regions')

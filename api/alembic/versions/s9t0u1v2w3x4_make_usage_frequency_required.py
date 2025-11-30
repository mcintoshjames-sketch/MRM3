"""Make usage_frequency_id required.

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select


# revision identifiers, used by Alembic.
revision = 's9t0u1v2w3x4'
down_revision = 'r8s9t0u1v2w3'
branch_labels = None
depends_on = None


def upgrade():
    # Get a connection
    conn = op.get_bind()

    # Find the "Monthly" usage frequency value (a reasonable default)
    # First, find the taxonomy_id for "Model Usage Frequency"
    result = conn.execute(
        sa.text("SELECT taxonomy_id FROM taxonomies WHERE name = 'Model Usage Frequency'")
    ).fetchone()

    if result:
        taxonomy_id = result[0]
        # Get the value_id for "MONTHLY"
        value_result = conn.execute(
            sa.text(
                "SELECT value_id FROM taxonomy_values "
                "WHERE taxonomy_id = :tid AND code = 'MONTHLY'"
            ),
            {"tid": taxonomy_id}
        ).fetchone()

        if value_result:
            default_value_id = value_result[0]
            # Update all models with NULL usage_frequency_id to Monthly
            conn.execute(
                sa.text(
                    "UPDATE models SET usage_frequency_id = :vid "
                    "WHERE usage_frequency_id IS NULL"
                ),
                {"vid": default_value_id}
            )

    # Now make the column NOT NULL
    op.alter_column(
        'models',
        'usage_frequency_id',
        existing_type=sa.Integer(),
        nullable=False
    )


def downgrade():
    # Make the column nullable again
    op.alter_column(
        'models',
        'usage_frequency_id',
        existing_type=sa.Integer(),
        nullable=True
    )

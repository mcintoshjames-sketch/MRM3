"""Simplify validation priority to Urgent/Standard.

Revision ID: a0b1c2d3e4f5
Revises: z6a7b8c9d0e1
Create Date: 2025-12-02

Maps:
- HIGH -> URGENT
- CRITICAL, MEDIUM, LOW -> STANDARD
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Find the Validation Priority taxonomy
    result = conn.execute(
        sa.text("SELECT taxonomy_id FROM taxonomies WHERE name = 'Validation Priority'")
    ).fetchone()

    if not result:
        print("Validation Priority taxonomy not found - skipping migration")
        return

    taxonomy_id = result[0]

    # Get existing priority values
    old_values = conn.execute(
        sa.text("""
            SELECT value_id, code FROM taxonomy_values
            WHERE taxonomy_id = :taxonomy_id
        """),
        {"taxonomy_id": taxonomy_id}
    ).fetchall()

    old_value_map = {row[1]: row[0] for row in old_values}

    # Create new URGENT value (if not exists)
    urgent_id = old_value_map.get("URGENT")
    if not urgent_id:
        conn.execute(
            sa.text("""
                INSERT INTO taxonomy_values (taxonomy_id, code, label, description, sort_order, is_active, created_at)
                VALUES (:taxonomy_id, 'URGENT', 'Urgent', 'Time-sensitive validation requiring prioritized resources', 1, true, NOW())
            """),
            {"taxonomy_id": taxonomy_id}
        )
        urgent_row = conn.execute(
            sa.text("SELECT value_id FROM taxonomy_values WHERE taxonomy_id = :taxonomy_id AND code = 'URGENT'"),
            {"taxonomy_id": taxonomy_id}
        ).fetchone()
        if urgent_row is None:
            raise RuntimeError("Failed to create URGENT validation priority")
        urgent_id = urgent_row[0]

    # Create new STANDARD value (if not exists)
    standard_id = old_value_map.get("STANDARD")
    if not standard_id:
        conn.execute(
            sa.text("""
                INSERT INTO taxonomy_values (taxonomy_id, code, label, description, sort_order, is_active, created_at)
                VALUES (:taxonomy_id, 'STANDARD', 'Standard', 'Normal priority - standard processing timeline', 2, true, NOW())
            """),
            {"taxonomy_id": taxonomy_id}
        )
        standard_row = conn.execute(
            sa.text("SELECT value_id FROM taxonomy_values WHERE taxonomy_id = :taxonomy_id AND code = 'STANDARD'"),
            {"taxonomy_id": taxonomy_id}
        ).fetchone()
        if standard_row is None:
            raise RuntimeError("Failed to create STANDARD validation priority")
        standard_id = standard_row[0]

    # Map HIGH -> URGENT
    high_id = old_value_map.get("HIGH")
    if high_id:
        conn.execute(
            sa.text("""
                UPDATE validation_requests
                SET priority_id = :urgent_id
                WHERE priority_id = :high_id
            """),
            {"urgent_id": urgent_id, "high_id": high_id}
        )

    # Map CRITICAL, MEDIUM, LOW -> STANDARD
    for code in ["CRITICAL", "MEDIUM", "LOW"]:
        old_id = old_value_map.get(code)
        if old_id:
            conn.execute(
                sa.text("""
                    UPDATE validation_requests
                    SET priority_id = :standard_id
                    WHERE priority_id = :old_id
                """),
                {"standard_id": standard_id, "old_id": old_id}
            )

    # Deactivate old taxonomy values (don't delete to preserve audit history)
    for code in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        old_id = old_value_map.get(code)
        if old_id:
            conn.execute(
                sa.text("""
                    UPDATE taxonomy_values
                    SET is_active = false
                    WHERE value_id = :value_id
                """),
                {"value_id": old_id}
            )


def downgrade() -> None:
    conn = op.get_bind()

    # Find the Validation Priority taxonomy
    result = conn.execute(
        sa.text("SELECT taxonomy_id FROM taxonomies WHERE name = 'Validation Priority'")
    ).fetchone()

    if not result:
        return

    taxonomy_id = result[0]

    # Get current values
    values = conn.execute(
        sa.text("""
            SELECT value_id, code FROM taxonomy_values
            WHERE taxonomy_id = :taxonomy_id
        """),
        {"taxonomy_id": taxonomy_id}
    ).fetchall()

    value_map = {row[1]: row[0] for row in values}

    # Reactivate old values
    for code in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        old_id = value_map.get(code)
        if old_id:
            conn.execute(
                sa.text("""
                    UPDATE taxonomy_values
                    SET is_active = true
                    WHERE value_id = :value_id
                """),
                {"value_id": old_id}
            )

    # Map URGENT back to HIGH
    urgent_id = value_map.get("URGENT")
    high_id = value_map.get("HIGH")
    if urgent_id and high_id:
        conn.execute(
            sa.text("""
                UPDATE validation_requests
                SET priority_id = :high_id
                WHERE priority_id = :urgent_id
            """),
            {"high_id": high_id, "urgent_id": urgent_id}
        )

    # Map STANDARD back to MEDIUM
    standard_id = value_map.get("STANDARD")
    medium_id = value_map.get("MEDIUM")
    if standard_id and medium_id:
        conn.execute(
            sa.text("""
                UPDATE validation_requests
                SET priority_id = :medium_id
                WHERE priority_id = :standard_id
            """),
            {"medium_id": medium_id, "standard_id": standard_id}
        )

    # Deactivate new values
    for code in ["URGENT", "STANDARD"]:
        new_id = value_map.get(code)
        if new_id:
            conn.execute(
                sa.text("""
                    UPDATE taxonomy_values
                    SET is_active = false
                    WHERE value_id = :value_id
                """),
                {"value_id": new_id}
            )

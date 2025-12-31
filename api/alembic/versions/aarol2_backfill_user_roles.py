"""backfill_user_roles

Revision ID: aarol2
Revises: aarol1
Create Date: 2025-12-31 00:10:00.000000
"""
from typing import Sequence, Union
from datetime import datetime, timezone
import os
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aarol2"
down_revision: Union[str, None] = "aarol1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_CODE_TO_DISPLAY = {
    "ADMIN": "Admin",
    "USER": "User",
    "VALIDATOR": "Validator",
    "GLOBAL_APPROVER": "Global Approver",
    "REGIONAL_APPROVER": "Regional Approver"
}

ROLE_DISPLAY_TO_CODE = {
    "admin": "ADMIN",
    "administrator": "ADMIN",
    "user": "USER",
    "validator": "VALIDATOR",
    "global approver": "GLOBAL_APPROVER",
    "global_approver": "GLOBAL_APPROVER",
    "regional approver": "REGIONAL_APPROVER",
    "regional_approver": "REGIONAL_APPROVER"
}


def normalize_role_code(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    upper = normalized.upper().replace(" ", "_")
    if upper in ROLE_CODE_TO_DISPLAY:
        return upper
    return ROLE_DISPLAY_TO_CODE.get(normalized.strip().lower())


def upgrade() -> None:
    conn = op.get_bind()

    op.create_table(
        "role_backfill_audit",
        sa.Column("audit_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("legacy_role", sa.String(length=100), nullable=True),
        sa.Column("resolved_role_code", sa.String(length=50), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("was_fallback", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False)
    )

    allow_fallback = os.getenv(
        "ROLE_BACKFILL_ALLOW_FALLBACK", "").strip().lower() in {"1", "true", "yes"}

    role_rows = conn.execute(
        sa.text("SELECT role_id, code FROM roles")).fetchall()
    role_id_map = {row.code: row.role_id for row in role_rows}

    user_rows = conn.execute(
        sa.text("SELECT user_id, role FROM users")).fetchall()
    distinct_roles = conn.execute(
        sa.text("SELECT DISTINCT role FROM users")).fetchall()
    normalized_role_map: dict[str, str] = {}
    unknown_roles: list[str] = []
    for row in distinct_roles:
        legacy_role = row[0]
        normalized_key = legacy_role.strip().lower() if legacy_role else ""
        code = normalize_role_code(legacy_role)
        if not code:
            unknown_roles.append(legacy_role)
            continue
        normalized_role_map[normalized_key] = code

    if unknown_roles and not allow_fallback:
        raise RuntimeError(
            "Unmapped user roles found; set ROLE_BACKFILL_ALLOW_FALLBACK=true to coerce to USER. "
            f"Unmapped roles: {sorted(set(unknown_roles))}"
        )

    for normalized_key, code in normalized_role_map.items():
        display_name = ROLE_CODE_TO_DISPLAY[code]
        conn.execute(
            sa.text(
                """
                UPDATE users
                SET role_id = (SELECT role_id FROM roles WHERE code = :code),
                    role = :display_name
                WHERE lower(trim(role)) = :normalized_key
                """
            ),
            {"code": code, "display_name": display_name,
                "normalized_key": normalized_key}
        )

    if allow_fallback:
        fallback_code = "USER"
        conn.execute(
            sa.text(
                """
                UPDATE users
                SET role_id = (SELECT role_id FROM roles WHERE code = :code),
                    role = :display_name
                WHERE role_id IS NULL
                """
            ),
            {"code": fallback_code,
                "display_name": ROLE_CODE_TO_DISPLAY[fallback_code]}
        )

    remaining = conn.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE role_id IS NULL")).scalar()
    if remaining:
        raise RuntimeError(
            "Role backfill incomplete; users remain with NULL role_id.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    audit_rows = []
    for row in user_rows:
        user_id = row.user_id
        legacy_role = row.role
        resolved_code = normalize_role_code(legacy_role) or "USER"
        fallback_used = resolved_code == "USER" and legacy_role and legacy_role.strip(
        ).lower() not in ROLE_DISPLAY_TO_CODE
        audit_rows.append(
            {
                "user_id": user_id,
                "legacy_role": legacy_role,
                "resolved_role_code": resolved_code,
                "role_id": role_id_map[resolved_code],
                "was_fallback": fallback_used,
                "created_at": now
            }
        )

    audit_table = sa.table(
        "role_backfill_audit",
        sa.column("user_id", sa.Integer),
        sa.column("legacy_role", sa.String),
        sa.column("resolved_role_code", sa.String),
        sa.column("role_id", sa.Integer),
        sa.column("was_fallback", sa.Boolean),
        sa.column("created_at", sa.DateTime)
    )
    if audit_rows:
        op.bulk_insert(audit_table, audit_rows)

    op.alter_column("role_backfill_audit", "was_fallback", server_default=None)


def downgrade() -> None:
    op.drop_table("role_backfill_audit")

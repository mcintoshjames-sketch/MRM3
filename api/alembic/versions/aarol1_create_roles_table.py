"""create_roles_table

Revision ID: aarol1
Revises: 47a5f0da1687
Create Date: 2025-12-31 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aarol1"
down_revision: Union[str, None] = "47a5f0da1687"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("role_id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  server_default=sa.text("true"))
    )
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)
    op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_role_id", "users", ["role_id"], unique=False)

    roles_table = sa.table(
        "roles",
        sa.column("code", sa.String),
        sa.column("display_name", sa.String),
        sa.column("is_system", sa.Boolean),
        sa.column("is_active", sa.Boolean)
    )
    op.bulk_insert(
        roles_table,
        [
            {"code": "ADMIN", "display_name": "Admin",
                "is_system": True, "is_active": True},
            {"code": "USER", "display_name": "User",
                "is_system": True, "is_active": True},
            {"code": "VALIDATOR", "display_name": "Validator",
                "is_system": True, "is_active": True},
            {"code": "GLOBAL_APPROVER", "display_name": "Global Approver",
                "is_system": True, "is_active": True},
            {"code": "REGIONAL_APPROVER", "display_name": "Regional Approver",
                "is_system": True, "is_active": True}
        ]
    )

    op.alter_column("roles", "is_system", server_default=None)
    op.alter_column("roles", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_column("users", "role_id")
    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_table("roles")

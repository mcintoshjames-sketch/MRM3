"""enforce_role_fk_drop_legacy_role

Revision ID: aarol3
Revises: aarol2
Create Date: 2025-12-31 00:20:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aarol3"
down_revision: Union[str, None] = "aarol2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_DEFAULT = "User"


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "role_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_users_role_id_roles",
            "roles",
            ["role_id"],
            ["role_id"],
            ondelete="RESTRICT"
        )
        batch_op.drop_column("role")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(length=50), nullable=True))

    conn = op.get_bind()
    conn.execute(sa.text(
        """
        UPDATE users
        SET role = (
            SELECT display_name
            FROM roles
            WHERE roles.role_id = users.role_id
        )
        """
    ))

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", existing_type=sa.String(
            length=50), nullable=False, server_default=ROLE_DEFAULT)
        batch_op.alter_column(
            "role_id", existing_type=sa.Integer(), nullable=True)
        batch_op.drop_constraint("fk_users_role_id_roles", type_="foreignkey")

    op.alter_column("users", "role", server_default=None)

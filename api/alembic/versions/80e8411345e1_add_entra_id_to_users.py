"""add entra id to users

Revision ID: 80e8411345e1
Revises: dc18ec5ea5f2
Create Date: 2026-01-11 15:50:34.640499

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80e8411345e1'
down_revision: Union[str, None] = 'dc18ec5ea5f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("entra_id", sa.String(length=36), nullable=True))
    op.create_index("ix_users_entra_id", "users", ["entra_id"])
    op.create_foreign_key(
        "fk_users_entra_id",
        "users",
        "entra_users",
        ["entra_id"],
        ["entra_id"],
        ondelete="SET NULL"
    )

    bind = op.get_bind()
    users_table = sa.table(
        "users",
        sa.column("user_id", sa.Integer),
        sa.column("email", sa.String),
        sa.column("full_name", sa.String),
        sa.column("entra_id", sa.String),
    )
    entra_table = sa.table(
        "entra_users",
        sa.column("entra_id", sa.String),
        sa.column("user_principal_name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("mail", sa.String),
        sa.column("account_enabled", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )

    entra_rows = bind.execute(
        sa.select(
            entra_table.c.entra_id,
            entra_table.c.mail,
            entra_table.c.user_principal_name,
        )
    ).fetchall()
    entra_map: dict[str, str] = {}
    for row in entra_rows:
        mail = (row.mail or "").lower()
        upn = (row.user_principal_name or "").lower()
        if mail:
            entra_map[mail] = row.entra_id
        if upn:
            entra_map[upn] = row.entra_id

    user_rows = bind.execute(
        sa.select(
            users_table.c.user_id,
            users_table.c.email,
            users_table.c.full_name,
            users_table.c.entra_id,
        )
    ).fetchall()

    created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in user_rows:
        if row.entra_id:
            continue
        email = row.email
        if not email:
            continue
        key = email.lower()
        entra_id = entra_map.get(key)
        if not entra_id:
            entra_id = str(uuid.uuid4())
            display_name = row.full_name or email
            bind.execute(
                entra_table.insert().values(
                    entra_id=entra_id,
                    user_principal_name=email,
                    display_name=display_name,
                    mail=email,
                    account_enabled=True,
                    created_at=created_at,
                )
            )
            entra_map[key] = entra_id
        bind.execute(
            users_table.update()
            .where(users_table.c.user_id == row.user_id)
            .values(entra_id=entra_id)
        )


def downgrade() -> None:
    op.drop_constraint("fk_users_entra_id", "users", type_="foreignkey")
    op.drop_index("ix_users_entra_id", table_name="users")
    op.drop_column("users", "entra_id")

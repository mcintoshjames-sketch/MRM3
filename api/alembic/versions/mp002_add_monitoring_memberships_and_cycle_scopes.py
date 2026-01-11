"""add monitoring plan memberships and cycle scopes

Revision ID: mp002_add_monitoring_memberships_and_cycle_scopes
Revises: b7c8d9e0f1a2
Create Date: 2026-01-06 00:00:00.000000
"""
from typing import Sequence, Union
from datetime import datetime, date, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "mp002_add_monitoring_memberships_and_cycle_scopes"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "monitoring_plan_memberships",
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_monitoring_membership_effective_range"
        ),
        sa.ForeignKeyConstraint(["model_id"], ["models.model_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["monitoring_plans.plan_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("membership_id"),
    )

    op.create_table(
        "monitoring_cycle_model_scopes",
        sa.Column("cycle_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=False),
        sa.Column("scope_source", sa.String(length=50), nullable=False),
        sa.Column("source_details", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["cycle_id"], ["monitoring_cycles.cycle_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], ["models.model_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cycle_id", "model_id"),
    )

    connection = op.get_bind()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Backfill memberships from monitoring_plan_models.
    plan_model_rows = connection.execute(
        text("SELECT plan_id, model_id FROM monitoring_plan_models")
    ).fetchall()

    if plan_model_rows:
        plan_latest_cycles = connection.execute(text("""
            SELECT plan_id, MAX(period_end_date) AS latest_end
            FROM monitoring_cycles
            GROUP BY plan_id
        """)).fetchall()
        latest_cycle_by_plan = {row[0]: row[1] for row in plan_latest_cycles}

        models_by_id: dict[int, list[int]] = {}
        for plan_id, model_id in plan_model_rows:
            models_by_id.setdefault(model_id, []).append(plan_id)

        membership_table = sa.table(
            "monitoring_plan_memberships",
            sa.column("membership_id", sa.Integer),
            sa.column("model_id", sa.Integer),
            sa.column("plan_id", sa.Integer),
            sa.column("effective_from", sa.DateTime),
            sa.column("effective_to", sa.DateTime),
            sa.column("reason", sa.Text),
            sa.column("changed_by_user_id", sa.Integer),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        )

        membership_rows = []
        for model_id, plan_ids in models_by_id.items():
            def plan_sort_key(pid: int) -> tuple[date, int]:
                return (latest_cycle_by_plan.get(pid) or date.min, pid)

            active_plan_id = max(plan_ids, key=plan_sort_key)
            for plan_id in plan_ids:
                is_active = plan_id == active_plan_id
                membership_rows.append({
                    "model_id": model_id,
                    "plan_id": plan_id,
                    "effective_from": now,
                    "effective_to": None if is_active else now,
                    "reason": (
                        "Backfilled from monitoring_plan_models"
                        if is_active
                        else "Backfilled from monitoring_plan_models (closed due to multiple plan memberships)"
                    ),
                    "changed_by_user_id": None,
                    "created_at": now,
                    "updated_at": now,
                })

        if membership_rows:
            connection.execute(membership_table.insert(), membership_rows)

        # Align projection table with active memberships (one plan per model).
        connection.execute(text("""
            DELETE FROM monitoring_plan_models ppm
            WHERE NOT EXISTS (
                SELECT 1 FROM monitoring_plan_memberships m
                WHERE m.plan_id = ppm.plan_id
                  AND m.model_id = ppm.model_id
                  AND m.effective_to IS NULL
            )
        """))

    # Add indexes/constraints after backfill to avoid conflicts.
    op.create_index(
        "idx_monitoring_plan_memberships_model_id",
        "monitoring_plan_memberships",
        ["model_id"],
        unique=False,
    )
    op.create_index(
        "idx_monitoring_plan_memberships_plan_id",
        "monitoring_plan_memberships",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        "uq_monitoring_plan_memberships_active_model",
        "monitoring_plan_memberships",
        ["model_id"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
    )
    op.create_index(
        "uq_monitoring_plan_memberships_active_plan_model",
        "monitoring_plan_memberships",
        ["plan_id", "model_id"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
    )

    # Backfill cycle scopes.
    model_rows = connection.execute(
        text("SELECT model_id, model_name FROM models")
    ).fetchall()
    model_name_by_id = {row[0]: row[1] for row in model_rows}

    snapshot_rows = connection.execute(text("""
        SELECT version_id, model_id, model_name
        FROM monitoring_plan_model_snapshots
    """)).fetchall()
    snapshots_by_version: dict[int, list[tuple[int, str]]] = {}
    for version_id, model_id, model_name in snapshot_rows:
        snapshots_by_version.setdefault(version_id, []).append((model_id, model_name))

    plan_model_rows = connection.execute(text("""
        SELECT ppm.plan_id, ppm.model_id, m.model_name
        FROM monitoring_plan_models ppm
        JOIN models m ON m.model_id = ppm.model_id
    """)).fetchall()
    plan_models_by_plan: dict[int, list[tuple[int, str]]] = {}
    for plan_id, model_id, model_name in plan_model_rows:
        plan_models_by_plan.setdefault(plan_id, []).append((model_id, model_name))

    result_rows = connection.execute(text("""
        SELECT DISTINCT cycle_id, model_id
        FROM monitoring_results
        WHERE model_id IS NOT NULL
    """)).fetchall()
    results_by_cycle: dict[int, set[int]] = {}
    for cycle_id, model_id in result_rows:
        results_by_cycle.setdefault(cycle_id, set()).add(model_id)

    cycle_rows = connection.execute(text("""
        SELECT cycle_id, plan_id, plan_version_id, version_locked_at, created_at
        FROM monitoring_cycles
    """)).fetchall()

    scope_table = sa.table(
        "monitoring_cycle_model_scopes",
        sa.column("cycle_id", sa.Integer),
        sa.column("model_id", sa.Integer),
        sa.column("model_name", sa.String),
        sa.column("locked_at", sa.DateTime),
        sa.column("scope_source", sa.String),
        sa.column("source_details", sa.JSON),
    )

    scope_rows = []
    for cycle_id, plan_id, plan_version_id, version_locked_at, created_at in cycle_rows:
        locked_at = version_locked_at or created_at or now
        models: list[tuple[int, str | None]] = []
        scope_source = None
        source_details = None

        if plan_version_id and snapshots_by_version.get(plan_version_id):
            models = snapshots_by_version[plan_version_id]
            scope_source = "version_snapshot"
            source_details = {"plan_version_id": plan_version_id}
        else:
            current_models = plan_models_by_plan.get(plan_id, [])
            if len(current_models) == 1:
                models = current_models
                scope_source = "current_membership_inference"
                source_details = {"plan_id": plan_id}
            else:
                result_model_ids = results_by_cycle.get(cycle_id, set())
                if result_model_ids:
                    models = [
                        (model_id, model_name_by_id.get(model_id))
                        for model_id in result_model_ids
                    ]
                    scope_source = "results_inference"
                    source_details = {"cycle_id": cycle_id}
                elif current_models:
                    models = current_models
                    scope_source = "current_membership_inference"
                    source_details = {"plan_id": plan_id}
                else:
                    scope_source = "unknown"
                    source_details = {"cycle_id": cycle_id}

        if not models:
            continue

        for model_id, model_name in models:
            scope_rows.append({
                "cycle_id": cycle_id,
                "model_id": model_id,
                "model_name": model_name,
                "locked_at": locked_at,
                "scope_source": scope_source,
                "source_details": source_details,
            })

    if scope_rows:
        connection.execute(scope_table.insert(), scope_rows)

    op.create_index(
        "idx_monitoring_cycle_model_scopes_model_id",
        "monitoring_cycle_model_scopes",
        ["model_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_monitoring_cycle_model_scopes_model_id",
        table_name="monitoring_cycle_model_scopes"
    )
    op.drop_table("monitoring_cycle_model_scopes")

    op.drop_index(
        "uq_monitoring_plan_memberships_active_plan_model",
        table_name="monitoring_plan_memberships"
    )
    op.drop_index(
        "uq_monitoring_plan_memberships_active_model",
        table_name="monitoring_plan_memberships"
    )
    op.drop_index(
        "idx_monitoring_plan_memberships_plan_id",
        table_name="monitoring_plan_memberships"
    )
    op.drop_index(
        "idx_monitoring_plan_memberships_model_id",
        table_name="monitoring_plan_memberships"
    )
    op.drop_table("monitoring_plan_memberships")

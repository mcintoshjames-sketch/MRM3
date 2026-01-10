"""Helpers for resolving monitoring cycle model scope."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.model import Model
from app.models.monitoring import (
    MonitoringCycle,
    MonitoringCycleModelScope,
    MonitoringPlanMembership,
    MonitoringPlanModelSnapshot,
    MonitoringResult,
)


def get_cycle_scope_models(db: Session, cycle: MonitoringCycle) -> List[dict]:
    """Return model scope for a cycle with best-effort fallbacks."""
    scope_rows = db.query(MonitoringCycleModelScope).filter(
        MonitoringCycleModelScope.cycle_id == cycle.cycle_id
    ).all()

    if scope_rows:
        model_ids = {row.model_id for row in scope_rows}
        names_by_id = {row.model_id: row.model_name for row in scope_rows if row.model_name}
        missing_ids = [model_id for model_id in model_ids if model_id not in names_by_id]
        if missing_ids:
            models = db.query(Model).filter(Model.model_id.in_(missing_ids)).all()
            for model in models:
                names_by_id[model.model_id] = model.model_name
        return [
            {"model_id": model_id, "model_name": names_by_id.get(model_id)}
            for model_id in sorted(model_ids)
        ]

    if cycle.plan_version_id:
        snapshots = db.query(MonitoringPlanModelSnapshot).filter(
            MonitoringPlanModelSnapshot.version_id == cycle.plan_version_id
        ).all()
        if snapshots:
            return [
                {"model_id": snapshot.model_id, "model_name": snapshot.model_name}
                for snapshot in sorted(snapshots, key=lambda s: s.model_id)
            ]

    result_model_ids = [
        row[0]
        for row in db.query(MonitoringResult.model_id).filter(
            MonitoringResult.cycle_id == cycle.cycle_id,
            MonitoringResult.model_id.isnot(None),
        ).distinct().all()
    ]
    if result_model_ids:
        models = db.query(Model).filter(Model.model_id.in_(result_model_ids)).all()
        names_by_id = {model.model_id: model.model_name for model in models}
        return [
            {"model_id": model_id, "model_name": names_by_id.get(model_id)}
            for model_id in sorted(set(result_model_ids))
        ]

    memberships = db.query(MonitoringPlanMembership).filter(
        MonitoringPlanMembership.plan_id == cycle.plan_id,
        MonitoringPlanMembership.effective_to.is_(None),
    ).all()
    if memberships:
        model_ids = [membership.model_id for membership in memberships]
        models = db.query(Model).filter(Model.model_id.in_(model_ids)).all()
        names_by_id = {model.model_id: model.model_name for model in models}
        return [
            {"model_id": model_id, "model_name": names_by_id.get(model_id)}
            for model_id in sorted(set(model_ids))
        ]

    return []


def get_cycle_scope_model_ids(db: Session, cycle: MonitoringCycle) -> Set[int]:
    """Return model IDs for a cycle scope with fallbacks."""
    return {entry["model_id"] for entry in get_cycle_scope_models(db, cycle)}


def materialize_cycle_scope(
    db: Session,
    cycle: MonitoringCycle,
    memberships: List[MonitoringPlanMembership],
    locked_at: Optional[datetime] = None,
    scope_source: str = "membership_ledger",
    source_details: Optional[dict] = None,
) -> None:
    """Insert cycle scope rows from memberships if not already present."""
    existing = db.query(MonitoringCycleModelScope).filter(
        MonitoringCycleModelScope.cycle_id == cycle.cycle_id
    ).first()
    if existing:
        return

    locked_at = locked_at or cycle.version_locked_at or utc_now()
    source_details = source_details or {"plan_id": cycle.plan_id}

    if not memberships:
        return

    model_ids = [membership.model_id for membership in memberships]
    models = db.query(Model).filter(Model.model_id.in_(model_ids)).all()
    names_by_id = {model.model_id: model.model_name for model in models}

    for membership in memberships:
        db.add(MonitoringCycleModelScope(
            cycle_id=cycle.cycle_id,
            model_id=membership.model_id,
            model_name=names_by_id.get(membership.model_id),
            locked_at=locked_at,
            scope_source=scope_source,
            source_details=source_details,
        ))

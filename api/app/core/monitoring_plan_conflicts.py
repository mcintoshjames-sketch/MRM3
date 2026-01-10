"""Helpers for monitoring plan frequency overlap rules."""
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.model import Model
from app.models.monitoring import MonitoringPlan, MonitoringPlanMembership


def _normalize_frequency(frequency) -> str:
    return getattr(frequency, "value", frequency)


def find_monitoring_plan_frequency_conflicts(
    db: Session,
    model_ids: List[int],
    frequency,
    exclude_plan_id: Optional[int] = None,
    active_only: bool = True
) -> List[Dict]:
    """Return models with monitoring plan conflicts for the requested frequency."""
    if not model_ids:
        return []

    frequency_value = _normalize_frequency(frequency)

    query = db.query(
        Model.model_id,
        Model.model_name,
        MonitoringPlan.plan_id,
        MonitoringPlan.name,
        MonitoringPlan.frequency,
        MonitoringPlan.is_active
    ).join(
        MonitoringPlanMembership,
        MonitoringPlanMembership.model_id == Model.model_id
    ).join(
        MonitoringPlan,
        MonitoringPlan.plan_id == MonitoringPlanMembership.plan_id
    ).filter(
        Model.model_id.in_(model_ids),
        MonitoringPlan.frequency == frequency_value,
        MonitoringPlanMembership.effective_to.is_(None)
    )

    if active_only:
        query = query.filter(MonitoringPlan.is_active.is_(True))

    if exclude_plan_id is not None:
        query = query.filter(MonitoringPlan.plan_id != exclude_plan_id)

    rows = query.all()
    if not rows:
        return []

    by_model: Dict[int, Dict] = {}
    for row in rows:
        plan_entry = {
            "plan_id": row.plan_id,
            "plan_name": row.name,
            "frequency": row.frequency,
            "is_active": row.is_active
        }
        model_entry = by_model.setdefault(
            row.model_id,
            {
                "model_id": row.model_id,
                "model_name": row.model_name,
                "plans": []
            }
        )
        model_entry["plans"].append(plan_entry)

    return list(by_model.values())


def build_monitoring_plan_conflict_message(
    conflicts: List[Dict],
    frequency
) -> str:
    """Build a user-facing conflict message from overlap results."""
    if not conflicts:
        return ""

    frequency_value = _normalize_frequency(frequency)
    parts = []
    for conflict in conflicts:
        details = ", ".join(
            f"#{entry['plan_id']} {entry['plan_name']}"
            for entry in conflict["plans"]
        )
        parts.append(
            f"Model '{conflict['model_name']}' (ID: {conflict['model_id']}) "
            f"already belongs to active monitoring plan(s) with frequency {frequency_value}: {details}."
        )

    rule = "A model can only be in one active monitoring plan per frequency."
    return " ".join(parts + [rule])

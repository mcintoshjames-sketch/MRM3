"""Helpers for validation overlap rules."""
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models import Model, Taxonomy, TaxonomyValue, ValidationRequest, ValidationRequestModelVersion


CLOSED_STATUS_CODES = {"APPROVED", "CANCELLED"}


def find_active_validation_conflicts(
    db: Session,
    model_ids: List[int],
    new_validation_type_code: Optional[str],
    exclude_request_id: Optional[int] = None
) -> List[Dict]:
    """Return models with active validation conflicts for the requested type."""
    if not model_ids:
        return []

    closed_status_ids = db.query(TaxonomyValue.value_id).join(
        Taxonomy, TaxonomyValue.taxonomy_id == Taxonomy.taxonomy_id
    ).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code.in_(CLOSED_STATUS_CODES)
    ).subquery()

    status_value = aliased(TaxonomyValue)
    type_value = aliased(TaxonomyValue)

    query = db.query(
        Model.model_id,
        Model.model_name,
        ValidationRequest.request_id,
        status_value.code.label("status_code"),
        status_value.label.label("status_label"),
        type_value.code.label("type_code"),
        type_value.label.label("type_label")
    ).join(
        ValidationRequestModelVersion,
        ValidationRequestModelVersion.model_id == Model.model_id
    ).join(
        ValidationRequest,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).join(
        status_value,
        status_value.value_id == ValidationRequest.current_status_id
    ).join(
        type_value,
        type_value.value_id == ValidationRequest.validation_type_id
    ).filter(
        Model.model_id.in_(model_ids),
        ~ValidationRequest.current_status_id.in_(select(closed_status_ids))
    )

    if exclude_request_id is not None:
        query = query.filter(ValidationRequest.request_id != exclude_request_id)

    rows = query.all()
    if not rows:
        return []

    by_model: Dict[int, Dict] = {}
    for row in rows:
        entry = {
            "request_id": row.request_id,
            "type_code": row.type_code,
            "type_label": row.type_label,
            "status_code": row.status_code,
            "status_label": row.status_label
        }
        model_entry = by_model.setdefault(
            row.model_id,
            {
                "model_id": row.model_id,
                "model_name": row.model_name,
                "non_targeted": [],
                "targeted": []
            }
        )
        if row.type_code == "TARGETED":
            model_entry["targeted"].append(entry)
        else:
            model_entry["non_targeted"].append(entry)

    conflicts = []
    for model_entry in by_model.values():
        non_targeted_count = len(model_entry["non_targeted"])
        if new_validation_type_code == "TARGETED":
            if non_targeted_count > 1:
                conflicts.append(model_entry)
        else:
            if non_targeted_count >= 1:
                conflicts.append(model_entry)

    return conflicts


def build_validation_conflict_message(
    conflicts: List[Dict],
    new_validation_type_code: Optional[str]
) -> str:
    """Build a user-facing conflict message from overlap results."""
    if not conflicts:
        return ""

    parts = []
    for conflict in conflicts:
        non_targeted = conflict["non_targeted"]
        details = ", ".join(
            f"#{entry['request_id']} ({entry['type_label'] or entry['type_code']}, "
            f"{entry['status_label'] or entry['status_code']})"
            for entry in non_targeted
        )
        parts.append(
            f"Model '{conflict['model_name']}' (ID: {conflict['model_id']}) "
            f"already has active non-targeted validation(s): {details}."
        )

    if new_validation_type_code == "TARGETED":
        rule = "TARGETED validations can overlap, but a model may only be in one active non-targeted validation at a time."
    else:
        rule = "A model may only be in one active non-targeted validation at a time; TARGETED validations can overlap."

    return " ".join(parts + [rule])

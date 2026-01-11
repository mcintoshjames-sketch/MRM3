"""Models routes."""
import csv
import io
import json
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, cast
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_
from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.core.validation_conflicts import (
    find_active_validation_conflicts,
    build_validation_conflict_message
)
from app.models.user import User
from app.models.model import Model
from app.models.vendor import Vendor
from app.models.region import Region
from app.models.lob import LOBUnit
from app.models.audit_log import AuditLog
from app.models.taxonomy import TaxonomyValue, Taxonomy
from app.models.model_version import ModelVersion
from app.models.model_region import ModelRegion
from app.models.validation_grouping import ValidationGroupingMemory
from app.models.model_hierarchy import ModelHierarchy
from app.models.monitoring import (
    MonitoringCycle,
    MonitoringCycleApproval,
    MonitoringPlan,
    MonitoringCycleModelScope,
    MonitoringPlanModelSnapshot,
    MonitoringResult,
)
from app.models.methodology import Methodology
from app.models.risk_assessment import ModelRiskAssessment
from app.models.irp import IRP
from app.models.model_exception import ModelException, ModelExceptionStatusHistory
from app.models.team import Team
from app.schemas.model_exception import ModelExceptionListResponse
from app.schemas.model import (
    ModelCreate, ModelUpdate, ModelDetailResponse, ValidationGroupingSuggestion, ModelCreateResponse,
    ModelNameHistoryItem, ModelNameHistoryResponse, NameChangeStatistics,
    ModelRolesWithLOB, UserWithLOBRollup,
    ModelApprovalStatusResponse, ModelApprovalStatusHistoryItem, ModelApprovalStatusHistoryResponse,
    BulkApprovalStatusRequest, BulkApprovalStatusItem, BulkApprovalStatusResponse,
    ModelListResponse, UserListItem, VendorListItem, TaxonomyListItem, MethodologyListItem,
    ModelTypeListItem, ModelRegionListItem
)
from app.schemas.user_lookup import ModelAssigneeResponse
from app.core.lob_utils import get_user_lob_rollup_name
from app.core.team_utils import build_lob_team_map
from app.schemas.submission_action import SubmissionAction, SubmissionFeedback, SubmissionCommentCreate
from app.schemas.activity_timeline import ActivityTimelineItem, ActivityTimelineResponse
from app.models.model_name_history import ModelNameHistory
from app.api.risk_assessment import get_global_assessment_status

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict | None = None):
    """Create an audit log entry."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)
    # Note: commit happens with the main transaction


def _get_initial_version(db: Session, model_id: int) -> Optional[ModelVersion]:
    """Get the initial model version (change_type_id=1) with a fallback to earliest version."""
    initial_version = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id,
        ModelVersion.change_type_id == 1
    ).order_by(ModelVersion.created_at.asc()).first()
    if initial_version:
        return initial_version
    return db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id
    ).order_by(ModelVersion.created_at.asc()).first()


def _get_initial_implementation_date(version: ModelVersion) -> Optional[date]:
    """Return the stored initial implementation date from the version fields."""
    return version.production_date or version.actual_production_date or version.planned_production_date


def _get_or_create_initial_version(
    db: Session,
    model: Model,
    created_by_id: int,
    initial_date: Optional[date]
) -> tuple[Optional[ModelVersion], bool]:
    """Get the initial version, creating a placeholder when missing."""
    initial_version = _get_initial_version(db, model.model_id)
    if initial_version:
        return initial_version, False
    if initial_date is None:
        return None, False

    is_active_model = model.status == "Active"
    planned_production_date = None if is_active_model else initial_date
    actual_production_date = initial_date if is_active_model else None

    initial_version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Auto-created initial version",
        created_by_id=created_by_id,
        planned_production_date=planned_production_date,
        actual_production_date=actual_production_date,
        production_date=initial_date,
        status="ACTIVE" if is_active_model else "DRAFT"
    )
    db.add(initial_version)
    db.flush()
    create_audit_log(
        db=db,
        entity_type="ModelVersion",
        entity_id=initial_version.version_id,
        action="CREATE",
        user_id=created_by_id,
        changes={"version_number": "1.0", "change_type_id": 1, "auto_created": True}
    )
    return initial_version, True


def _apply_initial_implementation_date(
    model: Model,
    version: ModelVersion,
    new_date: date
) -> dict[str, dict[str, Optional[str]]]:
    """Update initial version dates and return audit-friendly change details."""
    changes: dict[str, dict[str, Optional[str]]] = {}

    def record_change(field: str, old_value: Optional[date], updated_value: Optional[date]) -> None:
        if old_value != updated_value:
            changes[field] = {
                "old": str(old_value) if old_value else None,
                "new": str(updated_value) if updated_value else None
            }

    old_production = version.production_date
    version.production_date = new_date
    record_change("production_date", old_production, version.production_date)

    if version.actual_production_date is not None:
        old_actual = version.actual_production_date
        version.actual_production_date = new_date
        record_change("actual_production_date", old_actual, version.actual_production_date)
    elif version.planned_production_date is not None:
        old_planned = version.planned_production_date
        version.planned_production_date = new_date
        record_change("planned_production_date", old_planned, version.planned_production_date)
    else:
        if model.status == "Active" or version.status == "ACTIVE":
            record_change("actual_production_date", version.actual_production_date, new_date)
            version.actual_production_date = new_date
        else:
            record_change("planned_production_date", version.planned_production_date, new_date)
            version.planned_production_date = new_date

    return changes


def get_model_last_updated(model: Model) -> Optional[date]:
    """Get actual production date from model's latest ACTIVE version.

    Returns the actual_production_date of the latest ACTIVE version.
    Returns None if no ACTIVE version exists or if actual_production_date is not set.

    Note: Only uses actual_production_date (not planned_production_date or legacy
    production_date) to ensure we display when the model was actually deployed,
    not future planned dates.
    """
    # versions relationship is ordered by created_at DESC
    active_version = next(
        (v for v in model.versions if v.status == "ACTIVE"),
        None
    )
    if active_version:
        return active_version.actual_production_date
    return None


def _normalize_model_region_payload(
    region_ids: Optional[List[int]],
    model_regions: Optional[List[Any]],
    wholly_owned_region_id: Optional[int]
) -> List[dict[str, Optional[int]]]:
    payload: dict[int, Optional[int]] = {}
    if model_regions is not None:
        for item in model_regions:
            if isinstance(item, dict):
                region_id = item.get("region_id")
                owner_id = item.get("shared_model_owner_id")
            else:
                region_id = item.region_id
                owner_id = item.shared_model_owner_id
            if region_id is not None:
                payload[region_id] = owner_id
    elif region_ids is not None:
        for region_id in region_ids:
            payload[region_id] = None

    if wholly_owned_region_id is not None:
        payload.setdefault(wholly_owned_region_id, None)

    return [
        {"region_id": region_id, "shared_model_owner_id": owner_id}
        for region_id, owner_id in payload.items()
    ]


def _validate_model_region_payload(db: Session, payload: List[dict[str, Optional[int]]]) -> None:
    if not payload:
        return

    region_ids = {item["region_id"] for item in payload}
    regions = db.query(Region).filter(Region.region_id.in_(region_ids)).all()
    if len(regions) != len(region_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more regions not found"
        )

    owner_ids = {item["shared_model_owner_id"] for item in payload if item["shared_model_owner_id"] is not None}
    if owner_ids:
        owners = db.query(User).filter(User.user_id.in_(owner_ids)).all()
        if len(owners) != len(owner_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more shared model owners not found"
            )


def _sync_model_regions(db: Session, model_id: int, payload: List[dict[str, Optional[int]]]) -> bool:
    existing_regions = db.query(ModelRegion).filter(
        ModelRegion.model_id == model_id
    ).all()
    existing_by_region = {mr.region_id: mr for mr in existing_regions}
    desired_region_ids = {item["region_id"] for item in payload}
    changed = False

    for item in payload:
        existing = existing_by_region.get(item["region_id"])
        if existing:
            if existing.shared_model_owner_id != item["shared_model_owner_id"]:
                existing.shared_model_owner_id = item["shared_model_owner_id"]
                changed = True
        else:
            db.add(ModelRegion(
                model_id=model_id,
                region_id=item["region_id"],
                shared_model_owner_id=item["shared_model_owner_id"],
                created_at=utc_now()
            ))
            changed = True

    for existing in existing_regions:
        if existing.region_id not in desired_region_ids:
            db.delete(existing)
            changed = True

    return changed


def _format_audit_changes(changes: dict, db: Session) -> Optional[str]:
    """Convert audit log changes dict to human-readable description with resolved names.

    Args:
        changes: Dict from audit log, format: {"field": {"old": value, "new": value}} or {"field": "modified"}
        db: Database session for resolving IDs to names

    Returns:
        Human-readable description string or None if no changes
    """
    if not changes:
        return None

    # Field display names (snake_case -> readable)
    field_names = {
        "model_name": "Name",
        "external_model_id": "External Model ID",
        "description": "Description",
        "products_covered": "Products Covered",
        "development_type": "Development Type",
        "status": "Status",
        "owner_id": "Owner",
        "developer_id": "Developer",
        "shared_owner_id": "Shared Owner",
        "monitoring_manager_id": "Monitoring Manager",
        "risk_tier_id": "Risk Tier",
        "vendor_id": "Vendor",
        "wholly_owned_region_id": "Wholly Owned Region",
        "lob_id": "LOB",
        "user_ids": "Model Users",
        "regulatory_category_ids": "Regulatory Categories",
        "validation_plans_reset": "Validation Plans Reset",
        "approvals_voided": "Approvals Voided",
    }

    # Fields that need ID resolution
    user_fields = {"owner_id", "developer_id", "shared_owner_id", "monitoring_manager_id"}

    # Collect all IDs that need resolution
    user_ids_to_resolve = set()
    taxonomy_ids_to_resolve = set()
    vendor_ids_to_resolve = set()
    region_ids_to_resolve = set()
    lob_ids_to_resolve = set()

    for field, value in changes.items():
        if isinstance(value, dict) and "old" in value and "new" in value:
            if field in user_fields:
                if value["old"]: user_ids_to_resolve.add(value["old"])
                if value["new"]: user_ids_to_resolve.add(value["new"])
            elif field == "risk_tier_id":
                if value["old"]: taxonomy_ids_to_resolve.add(value["old"])
                if value["new"]: taxonomy_ids_to_resolve.add(value["new"])
            elif field == "vendor_id":
                if value["old"]: vendor_ids_to_resolve.add(value["old"])
                if value["new"]: vendor_ids_to_resolve.add(value["new"])
            elif field == "wholly_owned_region_id":
                if value["old"]: region_ids_to_resolve.add(value["old"])
                if value["new"]: region_ids_to_resolve.add(value["new"])
            elif field == "lob_id":
                if value["old"]: lob_ids_to_resolve.add(value["old"])
                if value["new"]: lob_ids_to_resolve.add(value["new"])

    # Batch fetch lookups
    user_map = {}
    if user_ids_to_resolve:
        users = db.query(User).filter(User.user_id.in_(user_ids_to_resolve)).all()
        user_map = {u.user_id: u.full_name for u in users}

    taxonomy_map = {}
    if taxonomy_ids_to_resolve:
        values = db.query(TaxonomyValue).filter(TaxonomyValue.value_id.in_(taxonomy_ids_to_resolve)).all()
        taxonomy_map = {v.value_id: v.label for v in values}

    vendor_map = {}
    if vendor_ids_to_resolve:
        vendors = db.query(Vendor).filter(Vendor.vendor_id.in_(vendor_ids_to_resolve)).all()
        vendor_map = {v.vendor_id: v.name for v in vendors}

    region_map = {}
    if region_ids_to_resolve:
        regions = db.query(Region).filter(Region.region_id.in_(region_ids_to_resolve)).all()
        region_map = {r.region_id: r.name for r in regions}

    lob_map = {}
    if lob_ids_to_resolve:
        lobs = db.query(LOBUnit).filter(LOBUnit.lob_id.in_(lob_ids_to_resolve)).all()
        lob_map = {l.lob_id: l.name for l in lobs}

    def resolve_value(field: str, value) -> str:
        """Resolve a single value to its display string."""
        if value is None:
            return "(empty)"
        if field in user_fields:
            return user_map.get(value, f"User #{value}")
        if field == "risk_tier_id":
            return taxonomy_map.get(value, f"Tier #{value}")
        if field == "vendor_id":
            return vendor_map.get(value, f"Vendor #{value}")
        if field == "wholly_owned_region_id":
            return region_map.get(value, f"Region #{value}")
        if field == "lob_id":
            return lob_map.get(value, f"LOB #{value}")
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, str) and len(value) > 50:
            return f"'{value[:47]}...'"
        if isinstance(value, str):
            return f"'{value}'"
        return str(value)

    # Build description parts
    parts = []

    # Skip internal tracking fields that don't need display
    skip_fields = {"validation_plans_reset", "approvals_voided"}

    for field, value in changes.items():
        if field in skip_fields:
            continue

        display_name = field_names.get(field, field.replace("_", " ").title())

        if isinstance(value, dict) and "old" in value and "new" in value:
            old_display = resolve_value(field, value["old"])
            new_display = resolve_value(field, value["new"])
            parts.append(f"{display_name}: {old_display} → {new_display}")
        elif value == "modified":
            parts.append(f"{display_name}: modified")
        else:
            # Handle other value types (e.g., counts)
            parts.append(f"{display_name}: {value}")

    if not parts:
        return None

    return ", ".join(parts)


def _format_risk_assessment_changes(changes: dict, action: str, db: Session) -> Optional[str]:
    """Format risk assessment audit log changes for display.

    Risk assessment changes have different structures:
    - CREATE: flat dict with field values
    - UPDATE: {"old": {...}, "new": {...}}
    """
    if not changes:
        return None

    # Field display names
    field_names = {
        "quantitative_rating": "Quantitative Rating",
        "quantitative_override": "Quantitative Override",
        "qualitative_override": "Qualitative Override",
        "derived_risk_tier": "Derived Risk Tier",
        "derived_risk_tier_override": "Final Risk Tier Override",
        "region_id": "Region",
    }

    # Skip fields that are not user-facing
    skip_fields = {"model_id", "quantitative_override_comment", "qualitative_override_comment",
                   "derived_risk_tier_override_comment"}

    parts = []

    if action == "CREATE":
        # For CREATE, show key initial values
        for field in ["quantitative_rating", "derived_risk_tier", "derived_risk_tier_override"]:
            if field in changes and changes[field]:
                display_name = field_names.get(field, field.replace("_", " ").title())
                parts.append(f"{display_name}: {changes[field]}")

    elif action == "UPDATE" and "old" in changes and "new" in changes:
        old_vals = changes["old"]
        new_vals = changes["new"]

        # Compare old and new values
        all_fields = set(old_vals.keys()) | set(new_vals.keys())
        for field in all_fields:
            if field in skip_fields:
                continue

            old_val = old_vals.get(field)
            new_val = new_vals.get(field)

            if old_val != new_val:
                display_name = field_names.get(field, field.replace("_", " ").title())
                old_display = old_val if old_val else "(empty)"
                new_display = new_val if new_val else "(empty)"
                parts.append(f"{display_name}: {old_display} → {new_display}")

    if not parts:
        return None

    return ", ".join(parts)


def _build_user_list_item(user: Optional[User]) -> Optional[dict]:
    """Build lightweight user dict for list views."""
    if not user:
        return None
    lob_dict = None
    if user.lob:
        lob_dict = {"lob_id": user.lob.lob_id, "name": user.lob.name}
    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "email": user.email,
        "lob": lob_dict
    }


def _build_model_list_response(
    model: Model,
    include_computed_fields: bool,
    db: Session,
    team_map: Optional[Dict[int, Optional[dict]]] = None
) -> dict:
    """Build lightweight model response dict without Pydantic validation overhead."""
    # Build lightweight nested objects directly
    owner_dict = _build_user_list_item(model.owner)
    developer_dict = _build_user_list_item(model.developer)
    shared_owner_dict = _build_user_list_item(model.shared_owner)
    shared_developer_dict = _build_user_list_item(model.shared_developer)
    monitoring_manager_dict = _build_user_list_item(model.monitoring_manager)

    vendor_dict = None
    if model.vendor:
        vendor_dict = {"vendor_id": model.vendor.vendor_id, "name": model.vendor.name}

    risk_tier_dict = None
    if model.risk_tier:
        risk_tier_dict = {"value_id": model.risk_tier.value_id, "label": model.risk_tier.label, "code": model.risk_tier.code}

    methodology_dict = None
    if model.methodology:
        methodology_dict = {"methodology_id": model.methodology.methodology_id, "name": model.methodology.name}

    ownership_type_dict = None
    if model.ownership_type:
        ownership_type_dict = {"value_id": model.ownership_type.value_id, "label": model.ownership_type.label, "code": model.ownership_type.code}

    model_type_dict = None
    if model.model_type:
        model_type_dict = {"type_id": model.model_type.type_id, "name": model.model_type.name}

    wholly_owned_region_dict = None
    if model.wholly_owned_region:
        wholly_owned_region_dict = {
            "region_id": model.wholly_owned_region.region_id,
            "region_code": model.wholly_owned_region.code,
            "region_name": model.wholly_owned_region.name
        }

    # Build regions list from model_regions relationship
    regions_list = []
    for mr in model.model_regions:
        if mr.region:
            regions_list.append({
                "region_id": mr.region.region_id,
                "region_code": mr.region.code,
                "region_name": mr.region.name
            })

    # Build users list
    users_list = [
        user_item for user_item in (_build_user_list_item(u) for u in model.users)
        if user_item
    ] if model.users else []

    # Build regulatory categories list
    reg_cats_list = []
    for rc in model.regulatory_categories:
        reg_cats_list.append({"value_id": rc.value_id, "label": rc.label, "code": rc.code})

    # Build MRSA risk level dict
    mrsa_risk_level_dict = None
    if model.mrsa_risk_level:
        mrsa_risk_level_dict = {
            "value_id": model.mrsa_risk_level.value_id,
            "label": model.mrsa_risk_level.label,
            "code": model.mrsa_risk_level.code,
            "requires_irp": model.mrsa_risk_level.requires_irp
        }

    # Build usage frequency dict
    usage_frequency_dict = None
    if model.usage_frequency:
        usage_frequency_dict = {
            "value_id": model.usage_frequency.value_id,
            "label": model.usage_frequency.label,
            "code": model.usage_frequency.code
        }

    # Build IRPs list for MRSAs
    irps_list = []
    for irp in model.irps:
        irp_dict = {
            "irp_id": irp.irp_id,
            "process_name": irp.process_name,
            "description": irp.description,
            "is_active": irp.is_active,
            "contact_user_id": irp.contact_user_id,
            "contact_user": None
        }
        if irp.contact_user:
            irp_dict["contact_user"] = {
                "user_id": irp.contact_user.user_id,
                "email": irp.contact_user.email,
                "full_name": irp.contact_user.full_name
            }
        irps_list.append(irp_dict)

    # Compute business_line_name from owner's LOB chain
    business_line = None
    if model.owner:
        business_line = get_user_lob_rollup_name(model.owner)

    # Compute is_aiml from methodology category
    is_aiml = None
    if model.methodology and model.methodology.category:
        is_aiml = model.methodology.category.name == "AI/ML"

    result = {
        "model_id": model.model_id,
        "model_name": model.model_name,
        "external_model_id": model.external_model_id,
        "description": model.description,
        "products_covered": model.products_covered,
        "development_type": model.development_type,
        "status": model.status,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
        "is_model": model.is_model,
        "is_aiml": is_aiml,
        "is_mrsa": model.is_mrsa,
        "mrsa_risk_level_id": model.mrsa_risk_level_id,
        "mrsa_risk_level": mrsa_risk_level_dict,
        "mrsa_risk_rationale": model.mrsa_risk_rationale,
        "row_approval_status": model.row_approval_status,
        "business_line_name": business_line,
        "model_last_updated": get_model_last_updated(model),
        "team": team_map.get(model.model_id) if team_map else None,
        "owner_id": model.owner_id,
        "developer_id": model.developer_id,
        "vendor_id": model.vendor_id,
        "risk_tier_id": model.risk_tier_id,
        "usage_frequency_id": model.usage_frequency_id,
        "owner": owner_dict,
        "developer": developer_dict,
        "shared_owner": shared_owner_dict,
        "shared_developer": shared_developer_dict,
        "monitoring_manager": monitoring_manager_dict,
        "vendor": vendor_dict,
        "risk_tier": risk_tier_dict,
        "methodology": methodology_dict,
        "ownership_type": ownership_type_dict,
        "model_type": model_type_dict,
        "wholly_owned_region": wholly_owned_region_dict,
        "usage_frequency": usage_frequency_dict,
        "regions": regions_list,
        "users": users_list,
        "regulatory_categories": reg_cats_list,
        "irps": irps_list,
        "scorecard_outcome": None,
        "residual_risk": None,
        "approval_status": None,
        "approval_status_label": None,
        # Revalidation fields (populated by batch computation)
        "validation_status": None,
        "next_validation_due_date": None,
        "days_until_validation_due": None,
        "last_validation_date": None,
        "days_overdue": 0,
        "penalty_notches": 0,
        "adjusted_scorecard_outcome": None,
    }

    if include_computed_fields:
        from app.core.final_rating import compute_final_model_risk_ranking
        from app.core.model_approval_status import compute_model_approval_status, get_status_label

        risk_ranking = compute_final_model_risk_ranking(db, model.model_id)
        if risk_ranking:
            result['scorecard_outcome'] = risk_ranking.get('original_scorecard')
            result['residual_risk'] = risk_ranking.get('final_rating')

        status_code, context = compute_model_approval_status(model, db)
        result['approval_status'] = status_code
        result['approval_status_label'] = get_status_label(status_code)

    return result


@router.get("/", response_model=List[ModelListResponse])
def list_models(
    exclude_sub_models: bool = False,
    include_computed_fields: bool = False,
    model_ids: Optional[str] = Query(None, description="Comma-separated model IDs to filter (for KPI drill-down)"),
    is_mrsa: Optional[bool] = Query(None, description="Filter by MRSA status: True=MRSAs only, False=Models only, None=All"),
    team_id: Optional[int] = Query(None, description="Filter by team ID (0 = Unassigned)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List models with details.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: See all models
    - User: Only see models where they are owner, developer, or delegate

    Query Parameters:
    - exclude_sub_models: If True, exclude models that are sub-models (children) in hierarchy
    - include_computed_fields: If True, include expensive computed fields (scorecard_outcome,
      residual_risk, approval_status). Default False for better performance.
    - model_ids: Comma-separated model IDs to filter (for KPI drill-down links)
    - is_mrsa: Filter by MRSA status - True shows only MRSAs, False shows only models, None shows all
    - team_id: Filter by effective team ID (0 = Unassigned)
    """
    from app.core.rls import apply_model_rls
    from app.models.lob import LOBUnit

    query = db.query(Model).options(
        # Single-value relationships: use joinedload (efficient for 1:1/N:1)
        joinedload(Model.owner).joinedload(User.lob).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent),
        joinedload(Model.developer).joinedload(User.lob),
        joinedload(Model.shared_owner).joinedload(User.lob),
        joinedload(Model.shared_developer).joinedload(User.lob),
        joinedload(Model.monitoring_manager).joinedload(User.lob),
        joinedload(Model.vendor),
        joinedload(Model.risk_tier),
        joinedload(Model.mrsa_risk_level),
        joinedload(Model.model_type),
        joinedload(Model.methodology).joinedload(Methodology.category),
        joinedload(Model.wholly_owned_region),
        joinedload(Model.ownership_type),
        # Collections: use selectinload to avoid Cartesian product explosion
        selectinload(Model.users).joinedload(User.lob),
        selectinload(Model.regulatory_categories),
        selectinload(Model.model_regions).joinedload(ModelRegion.region),
        selectinload(Model.versions),
        # IRPs for MRSAs - load contact user for display
        selectinload(Model.irps).joinedload(IRP.contact_user)
    )

    # Apply row-level security filtering
    query = apply_model_rls(query, current_user, db)

    # Filter by model_ids if provided (for KPI drill-down)
    if model_ids:
        ids = [int(id.strip()) for id in model_ids.split(',') if id.strip().isdigit()]
        if ids:
            query = query.filter(Model.model_id.in_(ids))

    # Filter by is_mrsa if provided
    if is_mrsa is not None:
        query = query.filter(Model.is_mrsa == is_mrsa)

    models = query.all()

    # Build LOB → Team map once for this request
    lob_team_map = build_lob_team_map(db)

    # Apply team filter if requested
    if team_id is not None:
        if team_id == 0:
            models = [
                model for model in models
                if not (model.owner and lob_team_map.get(model.owner.lob_id))
            ]
        else:
            models = [
                model for model in models
                if model.owner and lob_team_map.get(model.owner.lob_id) == team_id
            ]

    # Filter out sub-models if requested
    if exclude_sub_models:
        from sqlalchemy import func
        sub_model_ids = db.query(ModelHierarchy.child_model_id).filter(
            (ModelHierarchy.end_date == None) | (
                ModelHierarchy.end_date >= func.current_date())
        ).distinct().all()
        sub_model_ids = [row[0] for row in sub_model_ids]
        models = [m for m in models if m.model_id not in sub_model_ids]

    # Build lightweight responses without Pydantic validation overhead
    team_ids = set()
    model_team_ids: Dict[int, Optional[int]] = {}
    for model in models:
        owner_lob_id = model.owner.lob_id if model.owner else None
        effective_team_id = lob_team_map.get(owner_lob_id) if owner_lob_id else None
        model_team_ids[model.model_id] = effective_team_id
        if effective_team_id:
            team_ids.add(effective_team_id)

    team_info = {}
    if team_ids:
        teams = db.query(Team).filter(Team.team_id.in_(team_ids)).all()
        team_info = {team.team_id: {"team_id": team.team_id, "name": team.name} for team in teams}

    model_team_map = {
        model_id: team_info.get(team_id) if team_id else None
        for model_id, team_id in model_team_ids.items()
    }

    results = [_build_model_list_response(m, include_computed_fields, db, model_team_map) for m in models]

    # Batch compute revalidation fields (only when include_computed_fields is True)
    if include_computed_fields and models:
        from app.core.batch_revalidation import compute_batch_revalidation_fields
        compute_batch_revalidation_fields(db, models, results)

    return results


@router.post("/", response_model=ModelCreateResponse, status_code=status.HTTP_201_CREATED)
def create_model(
    model_data: ModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new model."""
    # Check if user is Admin
    is_admin_user = is_admin(current_user)

    # Non-Admin users must include themselves as owner, developer, or model user
    if not is_admin_user:
        user_ids = model_data.user_ids or []
        is_owner = model_data.owner_id == current_user.user_id
        is_developer = model_data.developer_id == current_user.user_id
        is_model_user = current_user.user_id in user_ids

        if not (is_owner or is_developer or is_model_user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must include yourself as the Owner, Developer, or a Model User when creating a model."
            )

    # Validate vendor requirement for third-party models
    if model_data.development_type == "Third-Party" and not model_data.vendor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor is required for third-party models"
        )

    # Validate developer requirement for in-house models
    if model_data.development_type == "In-House" and not model_data.developer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Developer is required for in-house models"
        )

    # Validate vendor exists if provided
    if model_data.vendor_id:
        vendor = db.query(Vendor).filter(
            Vendor.vendor_id == model_data.vendor_id).first()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

    # Validate owner exists
    owner = db.query(User).filter(User.user_id == model_data.owner_id).first()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner user not found"
        )

    # Validate developer exists if provided
    if model_data.developer_id:
        developer = db.query(User).filter(
            User.user_id == model_data.developer_id).first()
        if not developer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer user not found"
            )

    # Validate shared_owner exists and is different from owner if provided
    if model_data.shared_owner_id:
        if model_data.shared_owner_id == model_data.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shared owner must be different from the primary owner"
            )
        shared_owner = db.query(User).filter(
            User.user_id == model_data.shared_owner_id).first()
        if not shared_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared owner user not found"
            )

    # Validate shared_developer exists and is different from developer if provided
    if model_data.shared_developer_id:
        if model_data.developer_id and model_data.shared_developer_id == model_data.developer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shared developer must be different from the primary developer"
            )
        shared_developer = db.query(User).filter(
            User.user_id == model_data.shared_developer_id).first()
        if not shared_developer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared developer user not found"
            )

    # Validate monitoring_manager exists if provided
    if model_data.monitoring_manager_id:
        monitoring_manager = db.query(User).filter(
            User.user_id == model_data.monitoring_manager_id).first()
        if not monitoring_manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitoring manager user not found"
            )

    # Extract user_ids, regulatory_category_ids, region_ids/model_regions, irp_ids,
    # initial_version_number, initial_implementation_date, and validation request fields before creating model
    user_ids = model_data.user_ids or []
    regulatory_category_ids = model_data.regulatory_category_ids or []
    region_ids = model_data.region_ids
    model_regions_payload = model_data.model_regions
    irp_ids = model_data.irp_ids or []
    initial_version_number = model_data.initial_version_number or "1.0"
    initial_implementation_date = model_data.initial_implementation_date
    auto_create_validation = model_data.auto_create_validation
    validation_request_data = {
        'type_id': model_data.validation_request_type_id,
        'priority_id': model_data.validation_request_priority_id,
        'target_date': model_data.validation_request_target_date,
        'trigger_reason': model_data.validation_request_trigger_reason
    }
    model_dict = model_data.model_dump(exclude={
        'user_ids', 'regulatory_category_ids', 'region_ids', 'model_regions', 'irp_ids',
        'initial_version_number', 'initial_implementation_date',
        'auto_create_validation', 'validation_request_type_id',
        'validation_request_priority_id', 'validation_request_target_date',
        'validation_request_trigger_reason'
    })

    model = Model(**model_dict)

    # Set row approval status for non-Admin users
    if not is_admin_user:
        model.row_approval_status = "Draft"
        model.submitted_by_user_id = current_user.user_id
        model.submitted_at = utc_now()

    # Add model users
    if user_ids:
        users = db.query(User).filter(User.user_id.in_(user_ids)).all()
        if len(users) != len(user_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more model users not found"
            )
        model.users = users

    # Add regulatory categories
    if regulatory_category_ids:
        categories = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id.in_(regulatory_category_ids)).all()
        if len(categories) != len(regulatory_category_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more regulatory categories not found"
            )
        model.regulatory_categories = categories

    # Add IRP coverage for MRSAs
    if irp_ids:
        from app.models.irp import IRP
        irps = db.query(IRP).filter(IRP.irp_id.in_(irp_ids)).all()
        if len(irps) != len(irp_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more IRPs not found"
            )
        model.irps = irps

    db.add(model)
    db.commit()
    db.refresh(model)

    # Add deployment regions (with optional regional owners)
    region_payload = _normalize_model_region_payload(
        region_ids,
        model_regions_payload,
        model.wholly_owned_region_id
    )
    if region_payload:
        _validate_model_region_payload(db, region_payload)
        for item in region_payload:
            db.add(ModelRegion(
                model_id=model.model_id,
                region_id=item["region_id"],
                shared_model_owner_id=item["shared_model_owner_id"],
                created_at=utc_now()
            ))
        db.commit()

    # Create initial version with change_type_id = 1 (New Model Development)
    # Use custom version number if provided, otherwise default to "1.0"
    # Use implementation date as planned or actual based on model status
    is_active_model = model_data.status == "Active"
    version_status = "ACTIVE" if is_active_model else "DRAFT"
    planned_production_date = None if is_active_model else initial_implementation_date
    actual_production_date = initial_implementation_date if is_active_model else None
    initial_version = ModelVersion(
        model_id=model.model_id,
        version_number=initial_version_number,
        change_type="MAJOR",  # New models are MAJOR changes
        change_type_id=1,  # Code 1 = "New Model Development"
        change_description="Initial model version",
        created_by_id=current_user.user_id,
        planned_production_date=planned_production_date,
        actual_production_date=actual_production_date,
        production_date=initial_implementation_date,
        status=version_status
    )
    db.add(initial_version)
    db.commit()
    db.refresh(initial_version)

    # Audit log for model creation
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model.model_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"model_name": model.model_name, "status": model.status,
                 "development_type": model.development_type}
    )

    # Audit log for initial version
    create_audit_log(
        db=db,
        entity_type="ModelVersion",
        entity_id=initial_version.version_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"version_number": initial_version_number,
                 "change_type_id": 1, "auto_created": True}
    )

    # Create initial submission comment for non-Admin users
    if not is_admin_user:
        from app.models import ModelSubmissionComment
        initial_comment = ModelSubmissionComment(
            model_id=model.model_id,
            user_id=current_user.user_id,
            comment_text=f"Model '{model.model_name}' submitted for admin approval.",
            action_taken="submitted",
            created_at=utc_now()
        )
        db.add(initial_comment)

    db.commit()

    # Validate implementation date vs validation timing
    warnings = []
    if auto_create_validation and initial_implementation_date:
        # Get validation type to check if it's Interim Review
        validation_type = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == validation_request_data['type_id']
        ).first()
        is_interim = validation_type and (
            'interim' in validation_type.label.lower() or validation_type.code == 'INTERIM')

        # Check if implementation date is before validation target completion date
        if validation_request_data['target_date']:
            target_date = validation_request_data['target_date']
            if initial_implementation_date < target_date:
                if not is_interim:
                    warnings.append({
                        'type': 'IMPLEMENTATION_BEFORE_VALIDATION',
                        'message': f"Implementation date ({initial_implementation_date}) is before validation target completion date ({target_date}). Consider: (1) using 'Interim Review' validation type for faster approval, (2) setting an earlier validation target date, or (3) delaying implementation to {target_date} or later."
                    })

        # Check if implementation date is within policy lead time
        if model.risk_tier_id:
            from app.models import ValidationPolicy
            policy = db.query(ValidationPolicy).filter(
                ValidationPolicy.risk_tier_id == model.risk_tier_id
            ).first()

            if policy:
                lead_time_days = policy.model_change_lead_time_days
                days_until_implementation = (
                    initial_implementation_date - date.today()).days

                if days_until_implementation < lead_time_days:
                    # Warn if not using Interim Review
                    if not is_interim:
                        suggested_impl_date = date.today() + timedelta(days=lead_time_days)
                        warnings.append({
                            'type': 'LEAD_TIME_WARNING',
                            'message': f"Implementation date is only {days_until_implementation} days away, but policy requires {lead_time_days} days lead time for this risk tier. Consider using 'Interim Review' validation type or delaying implementation to {suggested_impl_date.isoformat()}."
                        })

    # Auto-create validation request if requested
    if auto_create_validation and validation_request_data['type_id'] and validation_request_data['priority_id']:
        from app.models import ValidationRequest, ValidationRequestModelVersion
        # datetime is already imported at module level

        # Get INTAKE status
        intake_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Validation Request Status",
            TaxonomyValue.code == "INTAKE"
        ).first()

        if intake_status:
            # Create validation request
            validation_request = ValidationRequest(
                request_date=date.today(),
                requestor_id=current_user.user_id,
                validation_type_id=validation_request_data['type_id'],
                priority_id=validation_request_data['priority_id'],
                target_completion_date=validation_request_data['target_date'],
                trigger_reason=validation_request_data['trigger_reason'] or "Auto-created with new model",
                current_status_id=intake_status.value_id,
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(validation_request)
            db.flush()

            # Associate model with validation request, including version if implementation date was set
            assoc = ValidationRequestModelVersion(
                request_id=validation_request.request_id,
                model_id=model.model_id,
                version_id=initial_version.version_id if initial_implementation_date else None
            )
            db.add(assoc)

            # Create initial status history entry
            from app.models import ValidationStatusHistory
            status_history = ValidationStatusHistory(
                request_id=validation_request.request_id,
                old_status_id=None,
                new_status_id=intake_status.value_id,
                changed_by_id=current_user.user_id,
                changed_at=utc_now(),
                change_reason="Auto-created with new model"
            )
            db.add(status_history)

            # Create audit log for validation request
            validation_audit = AuditLog(
                entity_type="ValidationRequest",
                entity_id=validation_request.request_id,
                action="CREATE",
                user_id=current_user.user_id,
                changes={
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "auto_created": True
                },
                timestamp=utc_now()
            )
            db.add(validation_audit)
            db.commit()

    # Reload with relationships
    from app.models import ModelSubmissionComment
    from app.models.lob import LOBUnit
    model = db.query(Model).options(
        # Owner with LOB chain for business_line_name computation
        joinedload(Model.owner).joinedload(User.lob).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.methodology).joinedload(Methodology.category),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.usage_frequency),
        joinedload(Model.ownership_type),
        joinedload(Model.status_value),
        joinedload(Model.wholly_owned_region),
        joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(Model.submission_comments).joinedload(
            ModelSubmissionComment.user),
        joinedload(Model.shared_owner),
        joinedload(Model.shared_developer),
        joinedload(Model.monitoring_manager),
        joinedload(Model.versions)  # For model_last_updated computation
    ).filter(Model.model_id == model.model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Return model with warnings if any
    # Convert model to dict and add warnings
    from pydantic import TypeAdapter
    model_dict = ModelCreateResponse.model_validate(model).model_dump()
    team_id = None
    if model.owner:
        team_id = build_lob_team_map(db).get(model.owner.lob_id)
    if team_id:
        team = db.query(Team).filter(Team.team_id == team_id).first()
        model_dict["team"] = {"team_id": team.team_id, "name": team.name} if team else None
    else:
        model_dict["team"] = None
    if warnings:
        model_dict['warnings'] = warnings
    return model_dict


# ============================================================================
# Model Submission Approval Workflow Endpoints
# ============================================================================


@router.get("/name-changes/stats", response_model=NameChangeStatistics)
def get_name_change_statistics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics on model name changes.

    Query Parameters:
    - start_date: Filter changes on or after this date (YYYY-MM-DD)
    - end_date: Filter changes on or before this date (YYYY-MM-DD)

    Returns:
    - Total models with name changes (all time)
    - Models with name changes in last 90 days
    - Models with name changes in last 30 days
    - Total number of name changes
    - Recent name changes (filtered by date range if provided)
    """
    from sqlalchemy import func, distinct

    now = utc_now()
    ninety_days_ago = now - timedelta(days=90)
    thirty_days_ago = now - timedelta(days=30)

    # Total models that have ever had a name change
    total_models_with_changes = db.query(
        func.count(distinct(ModelNameHistory.model_id))
    ).scalar() or 0

    # Models with name changes in last 90 days
    models_changed_90 = db.query(
        func.count(distinct(ModelNameHistory.model_id))
    ).filter(
        ModelNameHistory.changed_at >= ninety_days_ago
    ).scalar() or 0

    # Models with name changes in last 30 days
    models_changed_30 = db.query(
        func.count(distinct(ModelNameHistory.model_id))
    ).filter(
        ModelNameHistory.changed_at >= thirty_days_ago
    ).scalar() or 0

    # Total name changes
    total_changes = db.query(func.count(
        ModelNameHistory.history_id)).scalar() or 0

    # Build query for recent changes with optional date filtering
    changes_query = db.query(ModelNameHistory).options(
        joinedload(ModelNameHistory.changed_by)
    )

    if start_date:
        changes_query = changes_query.filter(
            ModelNameHistory.changed_at >= datetime.combine(
                start_date, datetime.min.time())
        )
    if end_date:
        changes_query = changes_query.filter(
            ModelNameHistory.changed_at <= datetime.combine(
                end_date, datetime.max.time())
        )

    recent = changes_query.order_by(
        ModelNameHistory.changed_at.desc()).limit(100).all()

    recent_changes = [
        ModelNameHistoryItem(
            history_id=h.history_id,
            model_id=h.model_id,
            old_name=h.old_name,
            new_name=h.new_name,
            changed_by_id=h.changed_by_id,
            changed_by_name=h.changed_by.full_name if h.changed_by else None,
            changed_at=h.changed_at,
            change_reason=h.change_reason
        )
        for h in recent
    ]

    return NameChangeStatistics(
        total_models_with_changes=total_models_with_changes,
        models_changed_last_90_days=models_changed_90,
        models_changed_last_30_days=models_changed_30,
        total_name_changes=total_changes,
        recent_changes=recent_changes
    )


@router.get("/pending-submissions", response_model=List[ModelDetailResponse])
def get_pending_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all models pending admin approval.

    Admin only. Returns models with row_approval_status IN ('Draft', 'needs_revision').
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view pending submissions"
        )

    from app.models import ModelSubmissionComment
    models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.submitted_by_user),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(Model.submission_comments).joinedload(
            ModelSubmissionComment.user)
    ).filter(
        Model.row_approval_status.in_(['Draft', 'needs_revision'])
    ).order_by(Model.submitted_at.desc()).all()

    return models


@router.get("/my-submissions", response_model=List[ModelDetailResponse])
def get_my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's model submissions (pending/needs_revision/rejected).

    Non-Admin users can see their own submissions.
    """
    from app.models import ModelSubmissionComment
    models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.submitted_by_user),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(Model.submission_comments).joinedload(
            ModelSubmissionComment.user)
    ).filter(
        Model.submitted_by_user_id == current_user.user_id,
        Model.row_approval_status != None  # Not approved yet
    ).order_by(Model.submitted_at.desc()).all()

    return models


@router.post("/approval-status/bulk", response_model=BulkApprovalStatusResponse)
def bulk_compute_approval_status(
    request: BulkApprovalStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compute approval status for multiple models in a single request.

    This endpoint is useful for dashboard displays and batch operations where
    you need to know the approval status of many models at once without making
    individual API calls.

    Returns status information including:
    - Current approval status (NEVER_VALIDATED, APPROVED, INTERIM_APPROVED, VALIDATION_IN_PROGRESS, EXPIRED)
    - Whether the model is overdue for revalidation
    - Days until next validation due
    """
    from app.core.model_approval_status import compute_model_approval_status, get_status_label

    max_model_ids = 200
    if len(request.model_ids) > max_model_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many model_ids (max {max_model_ids})."
        )

    models = db.query(Model).filter(
        Model.model_id.in_(request.model_ids)
    ).all()
    models_by_id = {model.model_id: model for model in models}

    results = []
    found_count = 0

    for model_id in request.model_ids:
        model = models_by_id.get(model_id)

        if not model:
            results.append(BulkApprovalStatusItem(
                model_id=model_id,
                error=f"Model {model_id} not found"
            ))
            continue

        found_count += 1

        try:
            status_code, context = compute_model_approval_status(model, db)
            results.append(BulkApprovalStatusItem(
                model_id=model_id,
                model_name=model.model_name,
                approval_status=status_code,
                approval_status_label=get_status_label(status_code),
                is_overdue=context.get("is_overdue", False),
                next_validation_due=context.get("next_validation_due"),
                days_until_due=context.get("days_until_due")
            ))
        except Exception as e:
            results.append(BulkApprovalStatusItem(
                model_id=model_id,
                model_name=model.model_name,
                error=str(e)
            ))

    return BulkApprovalStatusResponse(
        total_requested=len(request.model_ids),
        total_found=found_count,
        results=results
    )


@router.post("/approval-status/backfill")
def backfill_approval_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Backfill initial approval status history records for all models.

    This is an admin-only endpoint that creates initial ModelApprovalStatusHistory
    records for any models that don't already have them. This should typically be
    run once after the feature is deployed to populate history for existing models.

    Returns:
    - records_created: Number of new history records created
    - message: Summary of the operation
    """
    # Admin only
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can run the backfill"
        )

    from app.core.model_approval_status import backfill_model_approval_status

    try:
        count = backfill_model_approval_status(db)
        return {
            "records_created": count,
            "message": f"Successfully created {count} initial approval status history records"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backfill failed: {str(e)}"
        )


@router.get("/{model_id}", response_model=ModelDetailResponse)
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific model with details.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can access any model
    - User: Can only access models where they are owner, developer, or delegate
    """
    from app.core.rls import can_access_model
    from app.models.lob import LOBUnit

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model = db.query(Model).options(
        # Owner with LOB chain for business_line_name computation
        joinedload(Model.owner).joinedload(User.lob).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent),
        joinedload(Model.developer),
        joinedload(Model.shared_owner),
        joinedload(Model.shared_developer),
        joinedload(Model.monitoring_manager),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.methodology).joinedload(Methodology.category),
        joinedload(Model.wholly_owned_region),
        joinedload(Model.regulatory_categories),
        joinedload(Model.versions)  # For model_last_updated computation
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Convert model to dict and add computed fields
    model_dict = ModelDetailResponse.model_validate(model).model_dump()

    # Compute final risk ranking (scorecard_outcome and residual_risk)
    from app.core.final_rating import compute_final_model_risk_ranking
    risk_ranking = compute_final_model_risk_ranking(db, model.model_id)
    if risk_ranking:
        model_dict['scorecard_outcome'] = risk_ranking.get('original_scorecard')
        model_dict['residual_risk'] = risk_ranking.get('final_rating')
    else:
        model_dict['scorecard_outcome'] = None
        model_dict['residual_risk'] = None

    # Compute approval status
    from app.core.model_approval_status import compute_model_approval_status, get_status_label
    approval_status_code, _ = compute_model_approval_status(model, db)
    model_dict['approval_status'] = approval_status_code
    model_dict['approval_status_label'] = get_status_label(approval_status_code)

    # Compute model last updated from latest ACTIVE version
    model_dict['model_last_updated'] = get_model_last_updated(model)

    # Compute effective team from owner's LOB chain
    team_id = None
    if model.owner:
        team_id = build_lob_team_map(db).get(model.owner.lob_id)
    if team_id:
        team = db.query(Team).filter(Team.team_id == team_id).first()
        model_dict["team"] = {"team_id": team.team_id, "name": team.name} if team else None
    else:
        model_dict["team"] = None

    # Compute open exception count for UI badge
    from sqlalchemy import func
    open_exception_count = db.query(func.count(ModelException.exception_id)).filter(
        ModelException.model_id == model_id,
        ModelException.status == 'OPEN'
    ).scalar() or 0
    model_dict['open_exception_count'] = open_exception_count

    return model_dict


@router.get("/{model_id}/assignees", response_model=List[ModelAssigneeResponse])
def get_model_assignees(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return model-scoped recommendation assignees and assigned validators."""
    from app.core.rls import can_access_model
    from app.models.model_delegate import ModelDelegate
    from app.models.validation import ValidationAssignment, ValidationRequestModelVersion

    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.shared_owner),
        joinedload(Model.shared_developer)
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    assignees: dict[int, User] = {}

    def add_user(user: User | None) -> None:
        if user and user.user_id not in assignees:
            assignees[user.user_id] = user

    add_user(model.owner)
    add_user(model.developer)
    add_user(model.shared_owner)
    add_user(model.shared_developer)

    delegates = db.query(ModelDelegate).options(
        joinedload(ModelDelegate.user)
    ).filter(
        ModelDelegate.model_id == model_id,
        ModelDelegate.revoked_at == None
    ).all()
    for delegate in delegates:
        add_user(delegate.user)

    shared_region_owners = db.query(ModelRegion).options(
        joinedload(ModelRegion.shared_model_owner)
    ).filter(
        ModelRegion.model_id == model_id,
        ModelRegion.shared_model_owner_id.isnot(None)
    ).all()
    for region_link in shared_region_owners:
        add_user(region_link.shared_model_owner)

    assignments = db.query(ValidationAssignment).options(
        joinedload(ValidationAssignment.validator)
    ).join(
        ValidationRequestModelVersion,
        ValidationAssignment.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequestModelVersion.model_id == model_id
    ).all()
    for assignment in assignments:
        add_user(assignment.validator)

    return sorted(
        assignees.values(),
        key=lambda u: (u.full_name or "").lower()
    )


@router.get("/{model_id}/roles-with-lob", response_model=ModelRolesWithLOB)
def get_model_roles_with_lob(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all model roles with LOB names rolled up to LOB4 level.

    Returns the owner, shared_owner, developer, shared_developer, and monitoring_manager
    with their user info and LOB name rolled up to LOB4 (or actual level if LOB3 or higher).
    """
    from app.core.rls import can_access_model
    from app.models.lob import LOBUnit

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Query model with all user relationships and their LOB data
    model = db.query(Model).options(
        joinedload(Model.owner).joinedload(User.lob).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent),
        joinedload(Model.shared_owner).joinedload(User.lob).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent),
        joinedload(Model.developer).joinedload(User.lob).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent),
        joinedload(Model.shared_developer).joinedload(User.lob).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent),
        joinedload(Model.monitoring_manager).joinedload(User.lob).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent).joinedload(LOBUnit.parent),
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    def build_user_with_lob(user: User) -> UserWithLOBRollup:
        """Build UserWithLOBRollup from user with LOB data."""
        return UserWithLOBRollup(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role_display or "Unknown",
            lob_id=user.lob_id,
            lob_name=user.lob.name if user.lob else None,
            lob_rollup_name=get_user_lob_rollup_name(user)
        )

    return ModelRolesWithLOB(
        owner=build_user_with_lob(model.owner),
        shared_owner=build_user_with_lob(model.shared_owner) if model.shared_owner else None,
        developer=build_user_with_lob(model.developer) if model.developer else None,
        shared_developer=build_user_with_lob(model.shared_developer) if model.shared_developer else None,
        monitoring_manager=build_user_with_lob(model.monitoring_manager) if model.monitoring_manager else None
    )


@router.get("/{model_id}/revalidation-status")
def get_model_revalidation_status(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get revalidation status for a specific model.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can access any model's status
    - User: Can only access status for models they have access to
    """
    from app.api.validation_workflow import calculate_model_revalidation_status
    from app.core.rls import can_access_model

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    return calculate_model_revalidation_status(model, db)


@router.get("/{model_id}/validation-suggestions", response_model=ValidationGroupingSuggestion)
def get_validation_grouping_suggestions(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get suggested models for validation based on previous groupings.

    Returns models that were previously validated together with this model
    in the most recent regular validation (Comprehensive, etc.).
    Targeted validations are excluded from suggestions.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can access any model's suggestions
    - User: Can only access suggestions for models they have access to
    """
    from app.core.rls import can_access_model

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Look up grouping memory
    grouping_memory = db.query(ValidationGroupingMemory).filter(
        ValidationGroupingMemory.model_id == model_id
    ).first()

    # If no grouping memory, return empty suggestion
    if not grouping_memory:
        return ValidationGroupingSuggestion(
            suggested_model_ids=[],
            suggested_models=[],
            last_validation_request_id=None,
            last_grouped_at=None
        )

    # Parse grouped model IDs from JSON
    try:
        grouped_model_ids = json.loads(grouping_memory.grouped_model_ids)
    except (json.JSONDecodeError, TypeError):
        # If JSON is invalid, return empty suggestion
        return ValidationGroupingSuggestion(
            suggested_model_ids=[],
            suggested_models=[],
            last_validation_request_id=grouping_memory.last_validation_request_id,
            last_grouped_at=grouping_memory.updated_at
        )

    # Fetch the suggested models with full details
    suggested_models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories)
    ).filter(Model.model_id.in_(grouped_model_ids)).all()

    return ValidationGroupingSuggestion(
        suggested_model_ids=grouped_model_ids,
        suggested_models=[
            ModelDetailResponse.model_validate(model_item)
            for model_item in suggested_models
        ],
        last_validation_request_id=grouping_memory.last_validation_request_id,
        last_grouped_at=grouping_memory.updated_at
    )


@router.get("/{model_id}/exceptions", response_model=List[ModelExceptionListResponse])
def get_model_exceptions(
    model_id: int,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: OPEN, ACKNOWLEDGED, CLOSED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get exceptions for a model (convenience endpoint).

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can access any model
    - User: Can only access models where they are owner, developer, or delegate
    """
    from app.core.rls import can_access_model
    from app.schemas.model_exception import EXCEPTION_STATUSES, ModelBrief

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    query = db.query(ModelException).options(
        joinedload(ModelException.model)
    ).filter(ModelException.model_id == model_id)

    # Apply status filter if provided
    if status_filter:
        if status_filter not in EXCEPTION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {EXCEPTION_STATUSES}",
            )
        query = query.filter(ModelException.status == status_filter)

    exceptions = query.order_by(ModelException.detected_at.desc()).all()

    # Build response with proper model nested object
    result = []
    for exc in exceptions:
        result.append(ModelExceptionListResponse(
            exception_id=exc.exception_id,
            exception_code=exc.exception_code,
            model_id=exc.model_id,
            model=ModelBrief(
                model_id=exc.model.model_id,
                model_name=exc.model.model_name,
                model_code=None
            ),
            exception_type=exc.exception_type,
            status=exc.status,
            description=exc.description,
            detected_at=exc.detected_at,
            auto_closed=exc.auto_closed,
            acknowledged_at=exc.acknowledged_at,
            closed_at=exc.closed_at,
            created_at=exc.created_at,
            updated_at=exc.updated_at
        ))
    return result


@router.get("/{model_id}/exceptions/count")
def get_model_exception_count(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get exception counts for a model by status.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can access any model
    - User: Can only access models where they are owner, developer, or delegate
    """
    from app.core.rls import can_access_model
    from sqlalchemy import func

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Query counts by status
    counts = db.query(
        ModelException.status,
        func.count(ModelException.exception_id)
    ).filter(
        ModelException.model_id == model_id
    ).group_by(ModelException.status).all()

    return {
        "model_id": model_id,
        "open": next((c for s, c in counts if s == 'OPEN'), 0),
        "acknowledged": next((c for s, c in counts if s == 'ACKNOWLEDGED'), 0),
        "closed": next((c for s, c in counts if s == 'CLOSED'), 0),
    }


@router.patch("/{model_id}")
def update_model(
    model_id: int,
    model_data: ModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a model.

    For approved models edited by non-admins, changes are held for admin approval.
    Returns 202 Accepted with pending edit details in that case.

    Row-Level Security:
    - Admin: Can update any model directly
    - Owner/Developer/Delegate: Can update pending/needs_revision models directly;
      for approved models, changes are held for admin approval
    """
    from app.core.rls import can_access_model, can_modify_model
    from app.models.model_pending_edit import ModelPendingEdit
    from app.schemas.model import ModelUpdateWithPendingResponse
    from datetime import datetime, UTC

    # Check RLS access first (can user see this model?)
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    is_admin_user = is_admin(current_user)
    update_data = model_data.model_dump(exclude_unset=True)
    initial_version = None
    initial_version_created = False
    current_initial_date = None
    if "initial_implementation_date" in update_data:
        initial_version = _get_initial_version(db, model_id)
        if initial_version:
            current_initial_date = _get_initial_implementation_date(initial_version)

    if "description" in update_data and model.description:
        new_description = update_data.get("description")
        if new_description is None or not str(new_description).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Description cannot be cleared once set"
            )

    if "developer_id" in update_data and model.developer_id is not None:
        new_developer_id = update_data.get("developer_id")
        if not new_developer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Developer cannot be cleared once set"
            )

    if "usage_frequency_id" in update_data and model.usage_frequency_id is not None:
        new_usage_frequency = update_data.get("usage_frequency_id")
        if new_usage_frequency is None or new_usage_frequency == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usage frequency cannot be cleared once set"
            )

    if "initial_implementation_date" in update_data and current_initial_date is not None:
        new_initial_date = update_data.get("initial_implementation_date")
        if new_initial_date is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Initial implementation date cannot be cleared once set"
            )

    # For non-admins editing APPROVED models, create a pending edit instead
    if not is_admin_user and model.row_approval_status is None:
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes provided"
            )

        if "initial_implementation_date" in update_data:
            pending_date = update_data.get("initial_implementation_date")
            if isinstance(pending_date, date):
                update_data["initial_implementation_date"] = pending_date.isoformat()

        # Capture original values for the fields being changed
        original_values = {}
        for field in update_data.keys():
            if field == 'user_ids':
                original_values[field] = [u.user_id for u in model.users]
            elif field == 'regulatory_category_ids':
                original_values[field] = [c.value_id for c in model.regulatory_categories]
            elif field == 'initial_implementation_date':
                original_values[field] = current_initial_date.isoformat() if current_initial_date else None
            elif field == 'region_ids':
                original_values[field] = [mr.region_id for mr in model.model_regions]
            elif field == 'model_regions':
                original_values[field] = [
                    {
                        "region_id": mr.region_id,
                        "shared_model_owner_id": mr.shared_model_owner_id
                    }
                    for mr in model.model_regions
                ]
            else:
                original_values[field] = getattr(model, field, None)

        # Create pending edit record
        pending_edit = ModelPendingEdit(
            model_id=model_id,
            requested_by_id=current_user.user_id,
            requested_at=datetime.now(UTC),
            proposed_changes=update_data,
            original_values=original_values,
            status="pending"
        )
        db.add(pending_edit)

        # Create audit log for pending edit creation
        create_audit_log(
            db=db,
            entity_type="ModelPendingEdit",
            entity_id=model_id,
            action="CREATE",
            user_id=current_user.user_id,
            changes={"proposed_changes": update_data, "model_name": model.model_name}
        )

        db.commit()
        db.refresh(pending_edit)

        # Return 202 Accepted with pending edit info
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Your changes have been submitted for admin approval.",
                "pending_edit_id": pending_edit.pending_edit_id,
                "status": "pending",
                "proposed_changes": update_data,
                "model_id": model_id
            }
        )

    # For admins or non-approved models, check standard modification rights
    if not can_modify_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this model"
        )

    initial_implementation_date = update_data.pop("initial_implementation_date", None)

    # Block direct risk_tier_id changes if a global risk assessment exists
    # Users should update the risk assessment instead of directly changing the tier
    if 'risk_tier_id' in update_data:
        assessment_status = get_global_assessment_status(db, model_id)
        if assessment_status["has_assessment"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot directly change risk tier when a risk assessment exists. "
                       "Please update the Risk Assessment to change the model's risk tier."
            )

    # Handle development_type and vendor_id together
    new_dev_type = update_data.get('development_type', model.development_type)
    new_vendor_id = update_data.get('vendor_id', model.vendor_id)

    if new_dev_type == "Third-Party" and new_vendor_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor is required for third-party models"
        )

    # Validate vendor exists if provided
    if 'vendor_id' in update_data and update_data['vendor_id'] is not None:
        vendor = db.query(Vendor).filter(Vendor.vendor_id ==
                                         update_data['vendor_id']).first()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

    # Validate owner exists if provided
    if 'owner_id' in update_data:
        owner = db.query(User).filter(
            User.user_id == update_data['owner_id']).first()
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Owner user not found"
            )

    # Validate developer exists if provided
    if 'developer_id' in update_data and update_data['developer_id'] is not None:
        developer = db.query(User).filter(
            User.user_id == update_data['developer_id']).first()
        if not developer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer user not found"
            )

    # Validate shared_owner exists and is different from owner if provided
    if 'shared_owner_id' in update_data and update_data['shared_owner_id'] is not None:
        owner_id = update_data.get('owner_id', model.owner_id)
        if update_data['shared_owner_id'] == owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shared owner must be different from the primary owner"
            )
        shared_owner = db.query(User).filter(
            User.user_id == update_data['shared_owner_id']).first()
        if not shared_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared owner user not found"
            )

    # Validate shared_developer exists and is different from developer if provided
    if 'shared_developer_id' in update_data and update_data['shared_developer_id'] is not None:
        developer_id = update_data.get('developer_id', model.developer_id)
        if developer_id and update_data['shared_developer_id'] == developer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shared developer must be different from the primary developer"
            )
        shared_developer = db.query(User).filter(
            User.user_id == update_data['shared_developer_id']).first()
        if not shared_developer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared developer user not found"
            )

    # Validate monitoring_manager exists if provided
    if 'monitoring_manager_id' in update_data and update_data['monitoring_manager_id'] is not None:
        monitoring_manager = db.query(User).filter(
            User.user_id == update_data['monitoring_manager_id']).first()
        if not monitoring_manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitoring manager user not found"
            )

    # Handle user_ids separately
    user_ids_changed = False
    if 'user_ids' in update_data:
        user_ids = update_data.pop('user_ids')
        if user_ids is not None:
            users = db.query(User).filter(User.user_id.in_(user_ids)).all()
            if len(users) != len(user_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more model users not found"
                )
            model.users = users
            user_ids_changed = True

    # Handle regulatory_category_ids separately
    regulatory_categories_changed = False
    if 'regulatory_category_ids' in update_data:
        category_ids = update_data.pop('regulatory_category_ids')
        if category_ids is not None:
            categories = db.query(TaxonomyValue).filter(
                TaxonomyValue.value_id.in_(category_ids)).all()
            if len(categories) != len(category_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more regulatory categories not found"
                )
            model.regulatory_categories = categories
            regulatory_categories_changed = True

    # Handle irp_ids separately (IRP coverage for MRSAs)
    irps_changed = False
    if 'irp_ids' in update_data:
        irp_ids = update_data.pop('irp_ids')
        if irp_ids is not None:
            from app.models.irp import IRP
            irps = db.query(IRP).filter(IRP.irp_id.in_(irp_ids)).all()
            if len(irps) != len(irp_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more IRPs not found"
                )
            model.irps = irps
            irps_changed = True

    # Handle deployment regions (region_ids/model_regions)
    regions_changed = False
    regions_sync_applied = False
    if 'model_regions' in update_data or 'region_ids' in update_data:
        model_regions_payload = update_data.pop('model_regions', None)
        region_ids = update_data.pop('region_ids', None)
        region_payload = None
        new_wholly_owned_region_id = update_data.get(
            'wholly_owned_region_id',
            model.wholly_owned_region_id
        )

        if model_regions_payload is not None:
            region_payload = _normalize_model_region_payload(
                None,
                model_regions_payload,
                new_wholly_owned_region_id
            )
        elif region_ids is not None:
            existing_owner_map = {
                mr.region_id: mr.shared_model_owner_id
                for mr in db.query(ModelRegion).filter(ModelRegion.model_id == model_id).all()
            }
            payload_map = {
                region_id: existing_owner_map.get(region_id)
                for region_id in region_ids
            }
            if new_wholly_owned_region_id is not None:
                payload_map.setdefault(
                    new_wholly_owned_region_id,
                    existing_owner_map.get(new_wholly_owned_region_id)
                )
            region_payload = [
                {"region_id": region_id, "shared_model_owner_id": owner_id}
                for region_id, owner_id in payload_map.items()
            ]

        if region_payload is not None:
            _validate_model_region_payload(db, region_payload)
            regions_changed = _sync_model_regions(db, model_id, region_payload)
            regions_sync_applied = True

    # Track changes for audit log
    changes_made = {}
    risk_tier_changed = False
    old_risk_tier_id = model.risk_tier_id

    # Track name change specifically for history
    old_model_name = model.model_name
    name_changed = False

    for field, value in update_data.items():
        old_value = getattr(model, field, None)
        if old_value != value:
            changes_made[field] = {"old": old_value, "new": value}
            if field == "risk_tier_id":
                risk_tier_changed = True
            if field == "model_name":
                name_changed = True
        setattr(model, field, value)

    version_changes = {}
    if initial_implementation_date is not None:
        if not initial_version:
            initial_version, initial_version_created = _get_or_create_initial_version(
                db, model, current_user.user_id, initial_implementation_date
            )
        if not initial_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Initial model version not found for implementation date update"
            )
        current_initial_date = _get_initial_implementation_date(initial_version)
        if initial_version_created:
            changes_made["initial_implementation_date"] = {
                "old": None,
                "new": str(initial_implementation_date)
            }
        elif current_initial_date != initial_implementation_date:
            version_changes = _apply_initial_implementation_date(
                model, initial_version, initial_implementation_date
            )
            changes_made["initial_implementation_date"] = {
                "old": str(current_initial_date) if current_initial_date else None,
                "new": str(initial_implementation_date)
            }

    if user_ids_changed:
        changes_made["user_ids"] = "modified"

    if regulatory_categories_changed:
        changes_made["regulatory_category_ids"] = "modified"

    if irps_changed:
        changes_made["irp_ids"] = "modified"

    if regions_changed:
        changes_made["region_ids"] = "modified"

    # Auto-sync deployment regions when wholly_owned_region_id changes
    if (
        not regions_sync_applied
        and 'wholly_owned_region_id' in update_data
        and update_data['wholly_owned_region_id'] is not None
    ):
        new_region_id = update_data['wholly_owned_region_id']

        # Check if this region already exists in deployment regions
        existing_region = db.query(ModelRegion).filter(
            ModelRegion.model_id == model_id,
            ModelRegion.region_id == new_region_id
        ).first()

        # If not, add it
        if not existing_region:
            new_model_region = ModelRegion(
                model_id=model_id,
                region_id=new_region_id,
                created_at=utc_now()
            )
            db.add(new_model_region)
            changes_made["auto_added_deployment_region"] = new_region_id

    # Audit log for model update
    if changes_made:
        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=model_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes_made
        )

    if version_changes and initial_version:
        create_audit_log(
            db=db,
            entity_type="ModelVersion",
            entity_id=initial_version.version_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=version_changes
        )

    # Create name history record if name changed
    if name_changed:
        name_history = ModelNameHistory(
            model_id=model_id,
            old_name=old_model_name,
            new_name=model.model_name,
            changed_by_id=current_user.user_id,
            changed_at=utc_now()
        )
        db.add(name_history)

    db.commit()
    db.refresh(model)

    # Force reset validation plans if risk tier changed (voids approvals, regenerates components)
    if risk_tier_changed:
        from app.api.validation_workflow import reset_validation_plan_for_tier_change
        new_tier_id = model.risk_tier_id  # Could be None if tier was cleared
        if new_tier_id is not None:
            reset_result = reset_validation_plan_for_tier_change(
                db=db,
                model_id=model_id,
                new_tier_id=new_tier_id,
                user_id=current_user.user_id,
                force=True
            )
            if reset_result["reset_count"] > 0:
                changes_made["validation_plans_reset"] = reset_result["reset_count"]
                changes_made["approvals_voided"] = reset_result["approvals_voided"]
                db.commit()  # Commit the reset changes

    # Reload with relationships
    from app.models import ModelSubmissionComment
    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.submission_comments).joinedload(
            ModelSubmissionComment.user)
    ).filter(Model.model_id == model.model_id).first()

    return model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a model.

    Row-Level Security:
    - Admin: Can delete any model
    - Owner: Can delete their models
    - Developer: Can delete models they develop
    - Delegate with can_submit_changes: Can delete delegated models
    """
    from app.core.rls import can_access_model, can_modify_model

    # Check RLS access first (can user see this model?)
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Check modification rights
    if not can_modify_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this model"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Audit log for model deletion (before delete)
    model_name = model.model_name
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"model_name": model_name}
    )

    db.delete(model)
    db.commit()
    return None


@router.get("/export/csv")
def export_models_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export models to CSV.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Export all models
    - User: Export only models where they are owner, developer, or delegate
    """
    from app.core.rls import apply_model_rls

    query = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.users),
        joinedload(Model.regulatory_categories)
    )

    # Apply row-level security filtering
    query = apply_model_rls(query, current_user, db)
    models = query.all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Model ID",
        "Model Name",
        "Description",
        "Products Covered",
        "Development Type",
        "Model Type",
        "Status",
        "Owner",
        "Owner Email",
        "Developer",
        "Developer Email",
        "Vendor",
        "Risk Tier",
        "Validation Type",
        "Regulatory Categories",
        "Model Users",
        "Created At",
        "Updated At"
    ])

    # Write data rows
    for model in models:
        # Format model users as comma-separated list
        model_users_str = ", ".join(
            [u.full_name for u in model.users]) if model.users else ""
        # Format regulatory categories as comma-separated list
        reg_categories_str = ", ".join(
            [c.label for c in model.regulatory_categories]) if model.regulatory_categories else ""

        writer.writerow([
            model.model_id,
            model.model_name,
            model.description or "",
            model.products_covered or "",
            model.development_type,
            model.model_type.label if model.model_type else "",
            model.status,
            model.owner.full_name if model.owner else "",
            model.owner.email if model.owner else "",
            model.developer.full_name if model.developer else "",
            model.developer.email if model.developer else "",
            model.vendor.name if model.vendor else "",
            model.risk_tier.label if model.risk_tier else "",
            model.validation_type.label if model.validation_type else "",
            reg_categories_str,
            model_users_str,
            model.created_at.isoformat() if model.created_at else "",
            model.updated_at.isoformat() if model.updated_at else ""
        ])

    # Reset stream position
    output.seek(0)

    # Return as streaming response
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=models_export.csv"
        }
    )


@router.get("/{model_id}/submission-thread")
def get_submission_thread(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get submission comment thread for a model."""
    from app.core.rls import can_access_model
    from app.models import ModelSubmissionComment
    from app.schemas.model_submission_comment import ModelSubmissionCommentResponse

    # Check access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Get comments
    comments = db.query(ModelSubmissionComment).options(
        joinedload(ModelSubmissionComment.user)
    ).filter(
        ModelSubmissionComment.model_id == model_id
    ).order_by(ModelSubmissionComment.created_at.asc()).all()

    return [ModelSubmissionCommentResponse.model_validate(c) for c in comments]


@router.post("/{model_id}/comments")
def add_submission_comment(
    model_id: int,
    comment_data: SubmissionCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a comment to the submission thread."""
    from app.core.rls import can_access_model
    from app.models import ModelSubmissionComment

    # Check access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Only allow comments on Draft/needs_revision models
    if model.row_approval_status not in ('Draft', 'needs_revision'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only comment on Draft or needs_revision models"
        )

    comment = ModelSubmissionComment(
        model_id=model_id,
        user_id=current_user.user_id,
        comment_text=comment_data.comment_text,
        action_taken=None,
        created_at=utc_now()
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {"message": "Comment added", "comment_id": comment.comment_id}


@router.post("/{model_id}/approve", response_model=ModelDetailResponse)
def approve_model_submission(
    model_id: int,
    action: SubmissionAction,
    create_validation: bool = False,
    validation_type_id: int | None = None,
    validation_priority_id: int | None = None,
    validation_target_date: str | None = None,
    validation_trigger_reason: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a model submission (Admin only).

    Optionally creates a validation request for the approved model.
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve models"
        )

    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.submission_comments)
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if model.row_approval_status not in ('Draft', 'needs_revision'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model is not pending approval"
        )

    # Approve the model
    model.row_approval_status = None

    # Add approval comment
    from app.models import ModelSubmissionComment
    comment_text = action.comment or f"Model approved by {current_user.full_name} and added to inventory."
    approval_comment = ModelSubmissionComment(
        model_id=model_id,
        user_id=current_user.user_id,
        comment_text=comment_text,
        action_taken="approved",
        created_at=utc_now()
    )
    db.add(approval_comment)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="APPROVE",
        user_id=current_user.user_id,
        changes={"row_approval_status": "approved",
                 "approved_by": current_user.full_name}
    )

    db.commit()

    # Optionally create validation request
    if create_validation and validation_type_id and validation_priority_id:
        from app.models import ValidationRequest, ValidationRequestModelVersion

        # Get INTAKE status
        intake_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Validation Request Status",
            TaxonomyValue.code == "INTAKE"
        ).first()

        if not intake_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="INTAKE status not found in taxonomy"
            )

        validation_type = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == validation_type_id
        ).first()
        if not validation_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation type not found"
            )

        conflicts = find_active_validation_conflicts(
            db,
            [model_id],
            validation_type.code
        )
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=build_validation_conflict_message(conflicts, validation_type.code)
            )

        # Get current version
        current_version = db.query(ModelVersion).filter(
            ModelVersion.model_id == model_id,
            ModelVersion.status == "ACTIVE"
        ).order_by(ModelVersion.created_at.desc()).first()

        if not current_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active model version found"
            )

        # Create validation request
        validation_request = ValidationRequest(
            request_date=date.today(),
            type_id=validation_type_id,
            priority_id=validation_priority_id,
            status_id=intake_status.value_id,
            target_completion_date=date.fromisoformat(
                validation_target_date) if validation_target_date else None,
            trigger_reason=validation_trigger_reason or f"Initial validation for approved model {model.model_name}",
            created_by_id=current_user.user_id
        )
        db.add(validation_request)
        db.commit()
        db.refresh(validation_request)

        # Link model version
        link = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model_id,
            version_id=current_version.version_id
        )
        db.add(link)
        db.commit()

    # Reload model to ensure all relationships are populated for response
    db.refresh(model)
    return model


@router.post("/{model_id}/send-back", response_model=ModelDetailResponse)
def send_back_model_submission(
    model_id: int,
    feedback: SubmissionFeedback,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a model submission back to submitter with feedback (Admin only)."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can send back models"
        )

    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.submission_comments)
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if model.row_approval_status != 'Draft':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only send back Draft models"
        )

    # Change status to needs_revision
    model.row_approval_status = 'needs_revision'

    # Add feedback comment
    from app.models import ModelSubmissionComment
    feedback_comment = ModelSubmissionComment(
        model_id=model_id,
        user_id=current_user.user_id,
        comment_text=feedback.comment,
        action_taken="sent_back",
        created_at=utc_now()
    )
    db.add(feedback_comment)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="SEND_BACK",
        user_id=current_user.user_id,
        changes={"row_approval_status": "needs_revision",
                 "feedback": feedback.comment}
    )

    db.commit()
    db.refresh(model)
    return model


@router.post("/{model_id}/resubmit", response_model=ModelDetailResponse)
def resubmit_model(
    model_id: int,
    action: SubmissionAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resubmit a model after addressing feedback (Submitter only)."""
    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.submission_comments)
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Only submitter can resubmit
    if model.submitted_by_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the submitter can resubmit this model"
        )

    if model.row_approval_status != 'needs_revision':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only resubmit models that need revision"
        )

    # Change status back to Draft
    model.row_approval_status = 'Draft'

    # Add resubmission comment
    from app.models import ModelSubmissionComment
    note_text = action.comment or "Model resubmitted after addressing feedback."
    resubmit_comment = ModelSubmissionComment(
        model_id=model_id,
        user_id=current_user.user_id,
        comment_text=note_text,
        action_taken="resubmitted",
        created_at=utc_now()
    )
    db.add(resubmit_comment)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="RESUBMIT",
        user_id=current_user.user_id,
        changes={"row_approval_status": "Draft"}
    )

    db.commit()
    db.refresh(model)
    return model


@router.get("/{model_id}/activity-timeline", response_model=ActivityTimelineResponse)
def get_model_activity_timeline(
    model_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive activity timeline for a model.

    Includes:
    - Model created/updated (audit logs)
    - Versions created
    - Validation requests created/status changes
    - Validation approvals
    - Delegates added/removed
    - Comments added
    - Deployment tasks confirmed
    - Decommissioning requests/reviews/approvals
    - Monitoring cycles (created/submitted/completed/approvals)
    - Risk assessment changes
    - Model exceptions (detected/acknowledged/closed)
    - Pending edits (submitted/approved/rejected)
    """
    from app.core.rls import can_access_model
    from app.models.model_delegate import ModelDelegate
    from app.models.model_submission_comment import ModelSubmissionComment
    from app.models.validation import ValidationRequest, ValidationStatusHistory, ValidationApproval
    from app.models.version_deployment_task import VersionDeploymentTask

    # Check model exists and user has access
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if not can_access_model(model.model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this model"
        )

    activities = []

    # 1. Model audit logs (created, updated)
    model_audits = db.query(AuditLog).options(
        joinedload(AuditLog.user)
    ).filter(
        AuditLog.entity_type == "Model",
        AuditLog.entity_id == model_id
    ).all()

    for audit in model_audits:
        icon = "📝"
        title = f"Model {audit.action.lower()}"
        description = None
        if audit.action == "CREATE":
            title = "Model created"
            icon = "✨"
        elif audit.action == "UPDATE":
            title = "Model updated"
            icon = "📝"
            # Format change details for display
            description = _format_audit_changes(audit.changes, db)
        elif audit.action == "SUBMIT":
            title = "Model submitted for approval"
            icon = "📤"
        elif audit.action == "APPROVE":
            title = "Model approved"
            icon = "✅"
        elif audit.action == "REJECT":
            title = "Model submission rejected"
            icon = "❌"
        elif audit.action == "RESUBMIT":
            title = "Model resubmitted"
            icon = "🔄"

        activities.append(ActivityTimelineItem(
            timestamp=audit.timestamp,
            activity_type=f"model_{audit.action.lower()}",
            title=title,
            description=description,
            user_name=audit.user.full_name if audit.user else None,
            user_id=audit.user_id,
            entity_type="Model",
            entity_id=model_id,
            icon=icon
        ))

    # 2. Model versions created
    versions = db.query(ModelVersion).options(
        joinedload(ModelVersion.created_by)
    ).filter(
        ModelVersion.model_id == model_id
    ).all()

    for version in versions:
        scope_text = f" ({version.scope})" if version.scope != "GLOBAL" else ""
        activities.append(ActivityTimelineItem(
            timestamp=version.created_at,
            activity_type="version_created",
            title=f"Version {version.version_number} created{scope_text}",
            description=version.change_description,
            user_name=version.created_by.full_name if version.created_by else None,
            user_id=version.created_by_id,
            entity_type="ModelVersion",
            entity_id=version.version_id,
            icon="🚀"
        ))

    # 3. Validation requests for this model
    validation_requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.current_status)
    ).join(
        ValidationRequest.models
    ).filter(
        Model.model_id == model_id
    ).all()

    for req in validation_requests:
        activities.append(ActivityTimelineItem(
            timestamp=req.created_at,
            activity_type="validation_request_created",
            title=f"Validation request #{req.request_id} created",
            description=None,
            user_name=req.requestor.full_name if req.requestor else None,
            user_id=req.requestor_id,
            entity_type="ValidationRequest",
            entity_id=req.request_id,
            icon="🔍"
        ))

        # Get status history for this request
        status_history = db.query(ValidationStatusHistory).options(
            joinedload(ValidationStatusHistory.changed_by),
            joinedload(ValidationStatusHistory.new_status)
        ).filter(
            ValidationStatusHistory.request_id == req.request_id
        ).all()

        for history in status_history:
            activities.append(ActivityTimelineItem(
                timestamp=history.changed_at,
                activity_type="validation_status_change",
                title=f"Validation #{req.request_id} status changed to {history.new_status.label if history.new_status else 'Unknown'}",
                description=history.change_reason,
                user_name=history.changed_by.full_name if history.changed_by else None,
                user_id=history.changed_by_id,
                entity_type="ValidationRequest",
                entity_id=req.request_id,
                icon="🔄"
            ))

    # 4. Validation approvals
    approvals = db.query(ValidationApproval).options(
        joinedload(ValidationApproval.approver),
        joinedload(ValidationApproval.request)
    ).join(
        ValidationApproval.request
    ).join(
        ValidationRequest.models
    ).filter(
        Model.model_id == model_id,
        ValidationApproval.approved_at.isnot(None)
    ).all()

    for approval in approvals:
        status_icon = "✅" if approval.approval_status == "Approved" else "❌"
        approved_at = cast(datetime, approval.approved_at)
        activities.append(ActivityTimelineItem(
            timestamp=approved_at,
            activity_type="validation_approval",
            title=f"Validation #{approval.request_id} {approval.approval_status.lower()}",
            description=approval.comments,
            user_name=approval.approver.full_name if approval.approver else None,
            user_id=approval.approver_id,
            entity_type="ValidationApproval",
            entity_id=approval.approval_id,
            icon=status_icon
        ))

    # 5. Delegates added/removed
    delegates = db.query(ModelDelegate).options(
        joinedload(ModelDelegate.user),
        joinedload(ModelDelegate.delegated_by),
        joinedload(ModelDelegate.revoked_by)
    ).filter(
        ModelDelegate.model_id == model_id
    ).all()

    for delegate in delegates:
        # Delegate added
        activities.append(ActivityTimelineItem(
            timestamp=delegate.delegated_at,
            activity_type="delegate_added",
            title=f"{delegate.user.full_name} added as delegate",
            description=None,
            user_name=delegate.delegated_by.full_name if delegate.delegated_by else None,
            user_id=delegate.delegated_by_id,
            entity_type="ModelDelegate",
            entity_id=delegate.delegate_id,
            icon="👤"
        ))

        # Delegate removed (if revoked)
        if delegate.revoked_at:
            activities.append(ActivityTimelineItem(
                timestamp=delegate.revoked_at,
                activity_type="delegate_removed",
                title=f"{delegate.user.full_name} removed as delegate",
                description=None,
                user_name=delegate.revoked_by.full_name if delegate.revoked_by else None,
                user_id=delegate.revoked_by_id,
                entity_type="ModelDelegate",
                entity_id=delegate.delegate_id,
                icon="👤"
            ))

    # 6. Submission comments
    comments = db.query(ModelSubmissionComment).options(
        joinedload(ModelSubmissionComment.user)
    ).filter(
        ModelSubmissionComment.model_id == model_id
    ).all()

    for comment in comments:
        activities.append(ActivityTimelineItem(
            timestamp=comment.created_at,
            activity_type="comment_added",
            title=f"Comment added by {comment.user.full_name if comment.user else 'Unknown'}",
            description=comment.comment_text[:100] + "..." if len(
                comment.comment_text) > 100 else comment.comment_text,
            user_name=comment.user.full_name if comment.user else None,
            user_id=comment.user_id,
            entity_type="ModelSubmissionComment",
            entity_id=comment.comment_id,
            icon="💬"
        ))

    # 7. Deployment tasks confirmed
    deployment_tasks = db.query(VersionDeploymentTask).options(
        joinedload(VersionDeploymentTask.version),
        joinedload(VersionDeploymentTask.confirmed_by),
        joinedload(VersionDeploymentTask.region)
    ).filter(
        VersionDeploymentTask.model_id == model_id,
        VersionDeploymentTask.confirmed_at.isnot(None)
    ).all()

    for task in deployment_tasks:
        region_text = f" to {task.region.name}" if task.region else ""
        confirmed_at = cast(datetime, task.confirmed_at)
        activities.append(ActivityTimelineItem(
            timestamp=confirmed_at,
            activity_type="deployment_confirmed",
            title=f"Version {task.version.version_number} deployed{region_text}",
            description=task.confirmation_notes,
            user_name=task.confirmed_by.full_name if task.confirmed_by else None,
            user_id=task.confirmed_by_id,
            entity_type="VersionDeploymentTask",
            entity_id=task.task_id,
            icon="🚀"
        ))

    # 8. Decommissioning requests
    from app.models.decommissioning import DecommissioningRequest, DecommissioningStatusHistory, DecommissioningApproval

    decom_requests = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.created_by),
        joinedload(DecommissioningRequest.reason),
        joinedload(DecommissioningRequest.validator_reviewed_by),
        joinedload(DecommissioningRequest.owner_reviewed_by),
        joinedload(DecommissioningRequest.status_history).joinedload(
            DecommissioningStatusHistory.changed_by),
        joinedload(DecommissioningRequest.approvals).joinedload(
            DecommissioningApproval.approved_by)
    ).filter(
        DecommissioningRequest.model_id == model_id
    ).all()

    for decom in decom_requests:
        # Decommissioning request created
        reason_text = decom.reason.label if decom.reason else "Unknown reason"
        activities.append(ActivityTimelineItem(
            timestamp=decom.created_at,
            activity_type="decommissioning_request_created",
            title=f"Decommissioning request #{decom.request_id} created",
            description=f"Reason: {reason_text}",
            user_name=decom.created_by.full_name if decom.created_by else None,
            user_id=decom.created_by_id,
            entity_type="DecommissioningRequest",
            entity_id=decom.request_id,
            icon="🗑️"
        ))

        # Validator review (if completed)
        if decom.validator_reviewed_at:
            activities.append(ActivityTimelineItem(
                timestamp=decom.validator_reviewed_at,
                activity_type="decommissioning_validator_review",
                title=f"Decommissioning #{decom.request_id} validator review",
                description=decom.validator_comment,
                user_name=decom.validator_reviewed_by.full_name if decom.validator_reviewed_by else None,
                user_id=decom.validator_reviewed_by_id,
                entity_type="DecommissioningRequest",
                entity_id=decom.request_id,
                icon="✍️"
            ))

        # Owner review (if completed and was required)
        if decom.owner_approval_required and decom.owner_reviewed_at:
            activities.append(ActivityTimelineItem(
                timestamp=decom.owner_reviewed_at,
                activity_type="decommissioning_owner_review",
                title=f"Decommissioning #{decom.request_id} owner review",
                description=decom.owner_comment,
                user_name=decom.owner_reviewed_by.full_name if decom.owner_reviewed_by else None,
                user_id=decom.owner_reviewed_by_id,
                entity_type="DecommissioningRequest",
                entity_id=decom.request_id,
                icon="👤"
            ))

        # Status changes (from history)
        for history in decom.status_history:
            # Skip the initial creation record (already covered above)
            if history.old_status is None:
                continue
            status_icon = "🔄"
            if history.new_status == "APPROVED":
                status_icon = "✅"
            elif history.new_status == "REJECTED":
                status_icon = "❌"
            elif history.new_status == "WITHDRAWN":
                status_icon = "↩️"
            elif history.new_status == "VALIDATOR_APPROVED":
                status_icon = "📋"

            activities.append(ActivityTimelineItem(
                timestamp=history.changed_at,
                activity_type="decommissioning_status_change",
                title=f"Decommissioning #{decom.request_id} status: {history.new_status}",
                description=history.notes,
                user_name=history.changed_by.full_name if history.changed_by else None,
                user_id=history.changed_by_id,
                entity_type="DecommissioningRequest",
                entity_id=decom.request_id,
                icon=status_icon
            ))

        # Stage 2 approvals (Global/Regional)
        for approval in decom.approvals:
            if approval.approved_at:
                region_text = f" ({approval.region.name})" if approval.region else ""
                approval_status = "approved" if approval.is_approved else "rejected"
                activities.append(ActivityTimelineItem(
                    timestamp=approval.approved_at,
                    activity_type="decommissioning_approval",
                    title=f"Decommissioning #{decom.request_id} {approval.approver_type}{region_text} {approval_status}",
                    description=approval.comment,
                    user_name=approval.approved_by.full_name if approval.approved_by else None,
                    user_id=approval.approved_by_id,
                    entity_type="DecommissioningApproval",
                    entity_id=approval.approval_id,
                    icon="✅" if approval.is_approved else "❌"
                ))

    # 9. Monitoring cycles (performance monitoring)
    # Find monitoring plans that include this model
    scope_exists = db.query(MonitoringCycleModelScope.cycle_id).filter(
        MonitoringCycleModelScope.cycle_id == MonitoringCycle.cycle_id,
        MonitoringCycleModelScope.model_id == model_id
    ).exists()
    snapshot_exists = db.query(MonitoringPlanModelSnapshot.snapshot_id).filter(
        MonitoringPlanModelSnapshot.version_id == MonitoringCycle.plan_version_id,
        MonitoringPlanModelSnapshot.model_id == model_id
    ).exists()
    result_exists = db.query(MonitoringResult.result_id).filter(
        MonitoringResult.cycle_id == MonitoringCycle.cycle_id,
        MonitoringResult.model_id == model_id
    ).exists()

    monitoring_cycles = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.plan),
        joinedload(MonitoringCycle.submitted_by),
        joinedload(MonitoringCycle.completed_by),
        joinedload(MonitoringCycle.approvals).joinedload(MonitoringCycleApproval.approver),
        joinedload(MonitoringCycle.approvals).joinedload(MonitoringCycleApproval.region)
    ).filter(
        or_(scope_exists, snapshot_exists, result_exists)
    ).all()

    for cycle in monitoring_cycles:
        plan_name = cycle.plan.name if cycle.plan else "Unknown Plan"
        period_text = f"{cycle.period_start_date} to {cycle.period_end_date}"

        # Cycle created
        activities.append(ActivityTimelineItem(
            timestamp=cycle.created_at,
            activity_type="monitoring_cycle_created",
            title=f"Monitoring cycle started: {plan_name}",
            description=f"Period: {period_text}",
            user_name=None,
            user_id=None,
            entity_type="MonitoringCycle",
            entity_id=cycle.cycle_id,
            icon="📊"
        ))

        # Cycle submitted (if submitted)
        if cycle.submitted_at:
            activities.append(ActivityTimelineItem(
                timestamp=cycle.submitted_at,
                activity_type="monitoring_cycle_submitted",
                title=f"Monitoring data submitted: {plan_name}",
                description=f"Period: {period_text}",
                user_name=cycle.submitted_by.full_name if cycle.submitted_by else None,
                user_id=cycle.submitted_by_user_id,
                entity_type="MonitoringCycle",
                entity_id=cycle.cycle_id,
                icon="📤"
            ))

        # Cycle completed/approved (if completed)
        if cycle.completed_at and cycle.status == "APPROVED":
            activities.append(ActivityTimelineItem(
                timestamp=cycle.completed_at,
                activity_type="monitoring_cycle_completed",
                title=f"Monitoring cycle completed: {plan_name}",
                description=f"Period: {period_text}",
                user_name=cycle.completed_by.full_name if cycle.completed_by else None,
                user_id=cycle.completed_by_user_id,
                entity_type="MonitoringCycle",
                entity_id=cycle.cycle_id,
                icon="✅"
            ))

        # Individual approvals
        for approval in cycle.approvals:
            if approval.approved_at and approval.approval_status in ["Approved", "Rejected"]:
                region_text = f" ({approval.region.name})" if approval.region else ""
                approval_status = "approved" if approval.approval_status == "Approved" else "rejected"
                activities.append(ActivityTimelineItem(
                    timestamp=approval.approved_at,
                    activity_type="monitoring_cycle_approval",
                    title=f"Monitoring {approval.approval_type}{region_text} {approval_status}: {plan_name}",
                    description=approval.comments,
                    user_name=approval.approver.full_name if approval.approver else None,
                    user_id=approval.approver_id,
                    entity_type="MonitoringCycleApproval",
                    entity_id=approval.approval_id,
                    icon="✅" if approval.approval_status == "Approved" else "❌"
                ))

    # 10. Risk assessment changes
    # Get all assessments for this model
    assessments = db.query(ModelRiskAssessment).filter(
        ModelRiskAssessment.model_id == model_id
    ).all()

    assessment_ids = [a.assessment_id for a in assessments]

    if assessment_ids:
        risk_audits = db.query(AuditLog).options(
            joinedload(AuditLog.user)
        ).filter(
            AuditLog.entity_type == "ModelRiskAssessment",
            AuditLog.entity_id.in_(assessment_ids)
        ).all()

        # Build assessment_id -> region lookup for better titles
        assessment_region_map = {}
        for a in assessments:
            if a.region_id:
                region = db.query(Region).filter(Region.region_id == a.region_id).first()
                assessment_region_map[a.assessment_id] = region.name if region else f"Region #{a.region_id}"
            else:
                assessment_region_map[a.assessment_id] = "Global"

        for audit in risk_audits:
            region_name = assessment_region_map.get(audit.entity_id, "")
            scope_text = f" ({region_name})" if region_name else ""

            if audit.action == "CREATE":
                title = f"Risk assessment created{scope_text}"
                icon = "📊"
            elif audit.action == "UPDATE":
                title = f"Risk assessment updated{scope_text}"
                icon = "📊"
            elif audit.action == "DELETE":
                title = f"Risk assessment deleted{scope_text}"
                icon = "🗑️"
            else:
                title = f"Risk assessment {audit.action.lower()}{scope_text}"
                icon = "📊"

            description = _format_risk_assessment_changes(audit.changes, audit.action, db)

            activities.append(ActivityTimelineItem(
                timestamp=audit.timestamp,
                activity_type=f"risk_assessment_{audit.action.lower()}",
                title=title,
                description=description,
                user_name=audit.user.full_name if audit.user else None,
                user_id=audit.user_id,
                entity_type="ModelRiskAssessment",
                entity_id=audit.entity_id,
                icon=icon
            ))

    # 11. Model exceptions (opened, acknowledged, closed)
    exceptions = db.query(ModelException).options(
        joinedload(ModelException.acknowledged_by),
        joinedload(ModelException.closed_by),
        joinedload(ModelException.status_history).joinedload(ModelExceptionStatusHistory.changed_by)
    ).filter(
        ModelException.model_id == model_id
    ).all()

    exception_type_labels = {
        "UNMITIGATED_PERFORMANCE": "Unmitigated Performance Problem",
        "OUTSIDE_INTENDED_PURPOSE": "Model Used Outside Intended Purpose",
        "USE_PRIOR_TO_VALIDATION": "Model In Use Prior to Full Validation"
    }

    for exc in exceptions:
        type_label = exception_type_labels.get(exc.exception_type, exc.exception_type)

        # Exception created (detected)
        activities.append(ActivityTimelineItem(
            timestamp=exc.detected_at,
            activity_type="exception_detected",
            title=f"Exception detected: {type_label}",
            description=exc.description,
            user_name=None,  # System-detected
            user_id=None,
            entity_type="ModelException",
            entity_id=exc.exception_id,
            icon="🚨"
        ))

        # Exception acknowledged (if acknowledged)
        if exc.acknowledged_at:
            activities.append(ActivityTimelineItem(
                timestamp=exc.acknowledged_at,
                activity_type="exception_acknowledged",
                title=f"Exception #{exc.exception_code} acknowledged",
                description=exc.acknowledgment_notes,
                user_name=exc.acknowledged_by.full_name if exc.acknowledged_by else None,
                user_id=exc.acknowledged_by_id,
                entity_type="ModelException",
                entity_id=exc.exception_id,
                icon="👁️"
            ))

        # Exception closed (if closed)
        if exc.closed_at:
            close_method = "Auto-closed" if exc.auto_closed else "Closed"
            activities.append(ActivityTimelineItem(
                timestamp=exc.closed_at,
                activity_type="exception_closed",
                title=f"Exception #{exc.exception_code} {close_method.lower()}",
                description=exc.closure_narrative,
                user_name=exc.closed_by.full_name if exc.closed_by else "System",
                user_id=exc.closed_by_id,
                entity_type="ModelException",
                entity_id=exc.exception_id,
                icon="✅"
            ))

    # 12. Model pending edits (edit requests and their outcomes)
    from app.models.model_pending_edit import ModelPendingEdit

    pending_edits = db.query(ModelPendingEdit).options(
        joinedload(ModelPendingEdit.requested_by),
        joinedload(ModelPendingEdit.reviewed_by)
    ).filter(
        ModelPendingEdit.model_id == model_id
    ).all()

    for pe in pending_edits:
        # Pending edit submitted
        if pe.requested_at:
            # Summarize the fields being changed
            changed_fields = list((pe.proposed_changes or {}).keys())
            field_summary = ", ".join(changed_fields[:3])
            if len(changed_fields) > 3:
                field_summary += f" (+{len(changed_fields) - 3} more)"

            activities.append(ActivityTimelineItem(
                timestamp=pe.requested_at,
                activity_type="pending_edit_submitted",
                title="Model edit submitted for approval",
                description=f"Proposed changes to: {field_summary}" if field_summary else None,
                user_name=pe.requested_by.full_name if pe.requested_by else None,
                user_id=pe.requested_by.user_id if pe.requested_by else None,
                entity_type="ModelPendingEdit",
                entity_id=pe.pending_edit_id,
                icon="📝"
            ))

        # Pending edit reviewed (approved or rejected)
        if pe.reviewed_at and pe.status in ("approved", "rejected"):
            if pe.status == "approved":
                title = "Model edit approved and applied"
                icon = "✅"
            else:
                title = "Model edit rejected"
                icon = "❌"

            activities.append(ActivityTimelineItem(
                timestamp=pe.reviewed_at,
                activity_type=f"pending_edit_{pe.status}",
                title=title,
                description=pe.review_comment,
                user_name=pe.reviewed_by.full_name if pe.reviewed_by else None,
                user_id=pe.reviewed_by.user_id if pe.reviewed_by else None,
                entity_type="ModelPendingEdit",
                entity_id=pe.pending_edit_id,
                icon=icon
            ))

    # Sort all activities by timestamp (newest first)
    activities.sort(key=lambda x: x.timestamp, reverse=True)

    # Apply limit
    activities = activities[:limit]

    return ActivityTimelineResponse(
        model_id=model_id,
        model_name=model.model_name,
        activities=activities,
        total_count=len(activities)
    )


@router.get("/{model_id}/name-history", response_model=ModelNameHistoryResponse)
def get_model_name_history(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the name change history for a specific model.

    Returns all name changes in reverse chronological order.
    """
    from app.core.rls import can_access_model

    # Check model exists and user has access
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if not can_access_model(model.model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this model"
        )

    # Get name history
    history = db.query(ModelNameHistory).options(
        joinedload(ModelNameHistory.changed_by)
    ).filter(
        ModelNameHistory.model_id == model_id
    ).order_by(ModelNameHistory.changed_at.desc()).all()

    history_items = [
        ModelNameHistoryItem(
            history_id=h.history_id,
            model_id=h.model_id,
            old_name=h.old_name,
            new_name=h.new_name,
            changed_by_id=h.changed_by_id,
            changed_by_name=h.changed_by.full_name if h.changed_by else None,
            changed_at=h.changed_at,
            change_reason=h.change_reason
        )
        for h in history
    ]

    return ModelNameHistoryResponse(
        model_id=model_id,
        current_name=model.model_name,
        history=history_items,
        total_changes=len(history_items)
    )


# ============================================================================
# Pending Edit Endpoints (Model Edit Approval Workflow)
# ============================================================================

@router.get("/pending-edits/all", response_model=List[dict])
def list_all_pending_edits(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all pending model edits across all models (Admin only).

    Used for admin dashboard to review pending changes.
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    from app.models.model_pending_edit import ModelPendingEdit

    query = db.query(ModelPendingEdit).options(
        joinedload(ModelPendingEdit.model).joinedload(Model.owner),
        joinedload(ModelPendingEdit.requested_by),
        joinedload(ModelPendingEdit.reviewed_by)
    )

    if status_filter:
        query = query.filter(ModelPendingEdit.status == status_filter)
    else:
        # Default to pending only
        query = query.filter(ModelPendingEdit.status == "pending")

    pending_edits = query.order_by(ModelPendingEdit.requested_at.desc()).all()

    results = []
    for pe in pending_edits:
        requested_at = cast(Optional[datetime], pe.requested_at)
        reviewed_at = cast(Optional[datetime], pe.reviewed_at)
        results.append({
            "pending_edit_id": pe.pending_edit_id,
            "model_id": pe.model_id,
            "model_name": pe.model.model_name,
            "model_owner": {
                "user_id": pe.model.owner.user_id,
                "full_name": pe.model.owner.full_name,
                "email": pe.model.owner.email
            } if pe.model.owner else None,
            "requested_by": {
                "user_id": pe.requested_by.user_id,
                "full_name": pe.requested_by.full_name,
                "email": pe.requested_by.email
            },
            "requested_at": requested_at.isoformat() if requested_at else None,
            "proposed_changes": pe.proposed_changes,
            "original_values": pe.original_values,
            "status": pe.status,
            "reviewed_by": {
                "user_id": pe.reviewed_by.user_id,
                "full_name": pe.reviewed_by.full_name,
                "email": pe.reviewed_by.email
            } if pe.reviewed_by else None,
            "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
            "review_comment": pe.review_comment
        })
    return results


def _resolve_pending_edit_values(
    db: Session,
    values: Dict[str, Any]
) -> Dict[str, str]:
    """
    Resolve ID values in pending edit to human-readable labels.
    Returns a dict mapping field names to resolved string values.
    """
    from app.models.model_type_taxonomy import ModelType

    if not values:
        return {}

    resolved: Dict[str, str] = {}

    # Collect all user IDs to fetch in one query
    user_id_fields = ['owner_id', 'developer_id', 'shared_owner_id', 'shared_developer_id', 'monitoring_manager_id']
    user_ids_to_fetch = set()
    for field in user_id_fields:
        if field in values and values[field] is not None:
            user_ids_to_fetch.add(values[field])
    if 'user_ids' in values and values['user_ids']:
        user_ids_to_fetch.update(values['user_ids'])

    # Fetch users in bulk
    user_map: Dict[int, str] = {}
    if user_ids_to_fetch:
        users = db.query(User).filter(User.user_id.in_(user_ids_to_fetch)).all()
        user_map = {u.user_id: u.full_name for u in users}

    # Resolve user ID fields
    for field in user_id_fields:
        if field in values:
            val = values[field]
            if val is None:
                resolved[field] = ""
            else:
                resolved[field] = user_map.get(val, str(val))

    # Resolve user_ids array
    if 'user_ids' in values:
        user_ids = values['user_ids']
        if user_ids:
            names = [user_map.get(uid, str(uid)) for uid in user_ids]
            resolved['user_ids'] = ", ".join(names)
        else:
            resolved['user_ids'] = ""

    # Vendor lookup
    if 'vendor_id' in values:
        val = values['vendor_id']
        if val is None:
            resolved['vendor_id'] = ""
        else:
            vendor = db.query(Vendor).filter(Vendor.vendor_id == val).first()
            resolved['vendor_id'] = vendor.name if vendor else str(val)

    # Region lookup
    if 'wholly_owned_region_id' in values:
        val = values['wholly_owned_region_id']
        if val is None:
            resolved['wholly_owned_region_id'] = ""
        else:
            region = db.query(Region).filter(Region.region_id == val).first()
            resolved['wholly_owned_region_id'] = region.name if region else str(val)

    # Model type lookup
    if 'model_type_id' in values:
        val = values['model_type_id']
        if val is None:
            resolved['model_type_id'] = ""
        else:
            model_type = db.query(ModelType).filter(ModelType.type_id == val).first()
            resolved['model_type_id'] = model_type.name if model_type else str(val)

    # Taxonomy value lookups
    taxonomy_fields = {
        'risk_tier_id': 'Model Risk Tier',
        'validation_type_id': 'Validation Type',
        'status_id': 'Model Status',
        'usage_frequency_id': 'Model Usage Frequency',
    }

    taxonomy_ids_to_fetch = set()
    for field in taxonomy_fields:
        if field in values and values[field] is not None:
            taxonomy_ids_to_fetch.add(values[field])
    if 'regulatory_category_ids' in values and values['regulatory_category_ids']:
        taxonomy_ids_to_fetch.update(values['regulatory_category_ids'])

    # Fetch taxonomy values in bulk
    tax_value_map: Dict[int, str] = {}
    if taxonomy_ids_to_fetch:
        tax_values = db.query(TaxonomyValue).filter(TaxonomyValue.value_id.in_(taxonomy_ids_to_fetch)).all()
        tax_value_map = {tv.value_id: tv.label for tv in tax_values}

    for field in taxonomy_fields:
        if field in values:
            val = values[field]
            if val is None:
                resolved[field] = ""
            else:
                resolved[field] = tax_value_map.get(val, str(val))

    # Regulatory category IDs array
    if 'regulatory_category_ids' in values:
        cat_ids = values['regulatory_category_ids']
        if cat_ids:
            labels = [tax_value_map.get(cid, str(cid)) for cid in cat_ids]
            resolved['regulatory_category_ids'] = ", ".join(labels)
        else:
            resolved['regulatory_category_ids'] = ""

    # Pass through non-ID fields as strings
    for field, val in values.items():
        if field not in resolved:
            if val is None:
                resolved[field] = ""
            elif isinstance(val, bool):
                resolved[field] = "Yes" if val else "No"
            else:
                resolved[field] = str(val)

    return resolved


@router.get("/{model_id}/pending-edits", response_model=List[dict])
def list_model_pending_edits(
    model_id: int,
    include_all: bool = Query(False, description="Include approved/rejected edits"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List pending edits for a specific model.

    Accessible by model owners, developers, delegates, and admins.
    Includes resolved_original_values and resolved_proposed_changes
    with human-readable labels for ID fields.
    """
    from app.core.rls import can_access_model
    from app.models.model_pending_edit import ModelPendingEdit

    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    query = db.query(ModelPendingEdit).options(
        joinedload(ModelPendingEdit.requested_by),
        joinedload(ModelPendingEdit.reviewed_by)
    ).filter(ModelPendingEdit.model_id == model_id)

    if not include_all:
        query = query.filter(ModelPendingEdit.status == "pending")

    pending_edits = query.order_by(ModelPendingEdit.requested_at.desc()).all()

    results = []
    for pe in pending_edits:
        requested_at = cast(Optional[datetime], pe.requested_at)
        reviewed_at = cast(Optional[datetime], pe.reviewed_at)

        # Resolve ID values to human-readable labels
        original_values = pe.original_values or {}
        proposed_changes = pe.proposed_changes or {}
        resolved_original = _resolve_pending_edit_values(db, original_values)
        resolved_proposed = _resolve_pending_edit_values(db, proposed_changes)

        results.append({
            "pending_edit_id": pe.pending_edit_id,
            "model_id": pe.model_id,
            "requested_by": {
                "user_id": pe.requested_by.user_id,
                "full_name": pe.requested_by.full_name,
                "email": pe.requested_by.email
            },
            "requested_at": requested_at.isoformat() if requested_at else None,
            "proposed_changes": proposed_changes,
            "original_values": original_values,
            "resolved_original_values": resolved_original,
            "resolved_proposed_changes": resolved_proposed,
            "status": pe.status,
            "reviewed_by": {
                "user_id": pe.reviewed_by.user_id,
                "full_name": pe.reviewed_by.full_name,
                "email": pe.reviewed_by.email
            } if pe.reviewed_by else None,
            "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
            "review_comment": pe.review_comment
        })
    return results


@router.post("/{model_id}/pending-edits/{edit_id}/approve")
def approve_pending_edit(
    model_id: int,
    edit_id: int,
    review_data: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a pending edit and apply the changes to the model.

    Admin only.
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    from app.models.model_pending_edit import ModelPendingEdit
    from datetime import datetime, UTC

    pending_edit = db.query(ModelPendingEdit).filter(
        ModelPendingEdit.pending_edit_id == edit_id,
        ModelPendingEdit.model_id == model_id
    ).first()

    if not pending_edit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending edit not found"
        )

    pending_edit_status = cast(str, pending_edit.status)
    if pending_edit_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve edit with status '{pending_edit_status}'"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Apply the proposed changes to the model
    proposed_changes = dict(pending_edit.proposed_changes or {})
    changes_applied = {}
    version_changes = {}
    initial_version = None
    initial_version_created = False
    regions_changed = False
    regions_sync_applied = False

    if "model_regions" in proposed_changes or "region_ids" in proposed_changes:
        model_regions_payload = proposed_changes.pop("model_regions", None)
        region_ids = proposed_changes.pop("region_ids", None)
        new_wholly_owned_region_id = proposed_changes.get(
            "wholly_owned_region_id",
            model.wholly_owned_region_id
        )
        region_payload = None

        if model_regions_payload is not None:
            region_payload = _normalize_model_region_payload(
                None,
                model_regions_payload,
                new_wholly_owned_region_id
            )
        elif region_ids is not None:
            existing_owner_map = {
                mr.region_id: mr.shared_model_owner_id
                for mr in db.query(ModelRegion).filter(ModelRegion.model_id == model_id).all()
            }
            payload_map = {
                region_id: existing_owner_map.get(region_id)
                for region_id in region_ids
            }
            if new_wholly_owned_region_id is not None:
                payload_map.setdefault(
                    new_wholly_owned_region_id,
                    existing_owner_map.get(new_wholly_owned_region_id)
                )
            region_payload = [
                {"region_id": region_id, "shared_model_owner_id": owner_id}
                for region_id, owner_id in payload_map.items()
            ]

        if region_payload is not None:
            _validate_model_region_payload(db, region_payload)
            regions_changed = _sync_model_regions(db, model_id, region_payload)
            regions_sync_applied = True

    for field, value in proposed_changes.items():
        if field == 'user_ids':
            # Handle user_ids separately - only log if actually changed
            if value is not None:
                old_user_ids = sorted([u.user_id for u in model.users])
                new_user_ids = sorted(value)
                if old_user_ids != new_user_ids:
                    users = db.query(User).filter(User.user_id.in_(value)).all()
                    model.users = users
                    changes_applied[field] = {"old": old_user_ids, "new": new_user_ids}
        elif field == 'regulatory_category_ids':
            # Handle regulatory_category_ids separately - only log if actually changed
            if value is not None:
                old_category_ids = sorted([c.value_id for c in model.regulatory_categories])
                new_category_ids = sorted(value)
                if old_category_ids != new_category_ids:
                    categories = db.query(TaxonomyValue).filter(
                        TaxonomyValue.value_id.in_(value)).all()
                    model.regulatory_categories = categories
                    changes_applied[field] = {"old": old_category_ids, "new": new_category_ids}
        elif field == 'initial_implementation_date':
            if isinstance(value, str):
                value = date.fromisoformat(value)
            if value is None:
                if not initial_version:
                    initial_version = _get_initial_version(db, model_id)
                current_initial_date = _get_initial_implementation_date(initial_version) if initial_version else None
                if current_initial_date is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Initial implementation date cannot be cleared once set"
                    )
                continue

            if not initial_version:
                initial_version, initial_version_created = _get_or_create_initial_version(
                    db, model, current_user.user_id, value
                )
            if not initial_version:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Initial model version not found for implementation date update"
                )
            current_initial_date = _get_initial_implementation_date(initial_version)
            if initial_version_created:
                changes_applied[field] = {
                    "old": None,
                    "new": str(value)
                }
            elif current_initial_date != value:
                version_changes = _apply_initial_implementation_date(model, initial_version, value)
                changes_applied[field] = {
                    "old": str(current_initial_date) if current_initial_date else None,
                    "new": str(value)
                }
        else:
            old_value = getattr(model, field, None)
            if old_value != value:
                setattr(model, field, value)
                changes_applied[field] = {"old": old_value, "new": value}

    if regions_changed:
        changes_applied["region_ids"] = "modified"

    if (
        not regions_sync_applied
        and "wholly_owned_region_id" in proposed_changes
        and proposed_changes["wholly_owned_region_id"] is not None
    ):
        new_region_id = proposed_changes["wholly_owned_region_id"]
        existing_region = db.query(ModelRegion).filter(
            ModelRegion.model_id == model_id,
            ModelRegion.region_id == new_region_id
        ).first()
        if not existing_region:
            db.add(ModelRegion(
                model_id=model_id,
                region_id=new_region_id,
                created_at=utc_now()
            ))
            changes_applied["auto_added_deployment_region"] = new_region_id

    # Update pending edit status
    review_comment = review_data.get("comment") if review_data else None
    pending_edit_any = cast(Any, pending_edit)
    pending_edit_any.status = "approved"
    pending_edit_any.reviewed_by_id = current_user.user_id
    pending_edit_any.reviewed_at = datetime.now(UTC)
    pending_edit_any.review_comment = review_comment

    # Audit log for approval
    create_audit_log(
        db=db,
        entity_type="ModelPendingEdit",
        entity_id=edit_id,
        action="APPROVE",
        user_id=current_user.user_id,
        changes={"model_id": model_id, "changes_applied": changes_applied}
    )

    # Audit log for model update
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={"approved_pending_edit_id": edit_id, **changes_applied}
    )

    if version_changes and initial_version:
        create_audit_log(
            db=db,
            entity_type="ModelVersion",
            entity_id=initial_version.version_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=version_changes
        )

    db.commit()

    return {
        "message": "Pending edit approved and changes applied",
        "pending_edit_id": edit_id,
        "status": "approved",
        "model_id": model_id
    }


@router.post("/{model_id}/pending-edits/{edit_id}/reject")
def reject_pending_edit(
    model_id: int,
    edit_id: int,
    review_data: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject a pending edit.

    Admin only. The proposed changes are NOT applied.
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    from app.models.model_pending_edit import ModelPendingEdit
    from datetime import datetime, UTC

    pending_edit = db.query(ModelPendingEdit).filter(
        ModelPendingEdit.pending_edit_id == edit_id,
        ModelPendingEdit.model_id == model_id
    ).first()

    if not pending_edit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending edit not found"
        )

    pending_edit_status = cast(str, pending_edit.status)
    if pending_edit_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject edit with status '{pending_edit_status}'"
        )

    # Update pending edit status
    review_comment = review_data.get("comment") if review_data else None
    pending_edit_any = cast(Any, pending_edit)
    pending_edit_any.status = "rejected"
    pending_edit_any.reviewed_by_id = current_user.user_id
    pending_edit_any.reviewed_at = datetime.now(UTC)
    pending_edit_any.review_comment = review_comment

    # Audit log for rejection
    create_audit_log(
        db=db,
        entity_type="ModelPendingEdit",
        entity_id=edit_id,
        action="REJECT",
        user_id=current_user.user_id,
        changes={
            "model_id": model_id,
            "rejected_changes": pending_edit.proposed_changes,
            "comment": review_comment
        }
    )

    db.commit()

    return {
        "message": "Pending edit rejected",
        "pending_edit_id": edit_id,
        "status": "rejected",
        "model_id": model_id
    }


# =============================================================================
# Final Model Risk Ranking
# =============================================================================

class FinalRiskRankingResponse(BaseModel):
    """Response schema for Final Model Risk Ranking computation."""
    original_scorecard: str
    days_overdue: int
    past_due_level: str
    past_due_level_code: str
    downgrade_notches: int
    adjusted_scorecard: str
    inherent_risk_tier: str
    inherent_risk_tier_label: Optional[str] = None
    final_rating: Optional[str] = None
    residual_risk_without_penalty: Optional[str] = None


@router.get("/{model_id}/final-risk-ranking", response_model=FinalRiskRankingResponse)
def get_final_risk_ranking(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the Final Model Risk Ranking for a model.

    The Final Risk Ranking reflects both the model's inherent risk characteristics
    AND its validation compliance status. It is computed by:

    1. Taking the model's most recent validation scorecard outcome
    2. Applying a past-due downgrade penalty based on days overdue
    3. Using the adjusted scorecard + inherent risk tier in the Residual Risk Map

    The downgrade notches are configured in the Past Due Level taxonomy:
    - Current (not overdue): 0 notches
    - Minimal (< 1 year): 1 notch
    - Moderate (1-2 years): 2 notches
    - Significant/Critical/Obsolete (> 2 years): 3 notches

    Returns computation details including both the penalized and unpenalized ratings.
    """
    from app.core.final_rating import compute_final_model_risk_ranking

    result = compute_final_model_risk_ranking(db, model_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unable to compute final risk ranking. Model may be missing validation data or risk tier assignment."
        )

    return FinalRiskRankingResponse(**result)


# =============================================================================
# Model Approval Status
# =============================================================================

@router.get("/{model_id}/approval-status", response_model=ModelApprovalStatusResponse)
def get_model_approval_status(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current approval status for a model.

    The approval status answers: "Is this model currently approved for use
    based on its validation history?"

    Status values:
    - NEVER_VALIDATED: No validation has ever been approved for this model
    - APPROVED: Most recent validation is APPROVED with all required approvals complete
    - INTERIM_APPROVED: Most recent completed validation was of INTERIM type
    - VALIDATION_IN_PROGRESS: Model is overdue but has active validation in substantive stage
    - EXPIRED: Model is overdue with no active validation or validation still in INTAKE
    """
    from app.core.model_approval_status import (
        compute_model_approval_status,
        get_status_label
    )

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Compute current status
    status_code, context = compute_model_approval_status(model, db)

    return ModelApprovalStatusResponse(
        model_id=model.model_id,
        model_name=model.model_name,
        is_model=getattr(model, 'is_model', True),
        approval_status=status_code,
        approval_status_label=get_status_label(status_code),
        status_determined_at=context.get("computed_at") or utc_now(),
        latest_approved_validation_id=context.get("latest_approved_validation_id"),
        latest_approved_validation_date=context.get("latest_approved_date"),
        latest_approved_validation_type=context.get("validation_type_label"),
        active_validation_id=context.get("active_validation_id"),
        active_validation_status=context.get("active_validation_status"),
        all_approvals_complete=context.get("approvals_complete", True),
        pending_approval_count=context.get("pending_approval_count", 0),
        next_validation_due_date=context.get("next_validation_due"),
        days_until_due=context.get("days_until_due"),
        is_overdue=context.get("is_overdue", False),
    )


@router.get("/{model_id}/approval-status/history", response_model=ModelApprovalStatusHistoryResponse)
def get_model_approval_status_history(
    model_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the approval status history for a specific model.

    Returns all status changes in reverse chronological order.
    """
    from app.models.model_approval_status_history import ModelApprovalStatusHistory
    from app.core.model_approval_status import get_status_label

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Get total count
    total_count = db.query(ModelApprovalStatusHistory).filter(
        ModelApprovalStatusHistory.model_id == model_id
    ).count()

    # Get paginated history
    history_records = db.query(ModelApprovalStatusHistory).filter(
        ModelApprovalStatusHistory.model_id == model_id
    ).order_by(
        ModelApprovalStatusHistory.changed_at.desc()
    ).offset(offset).limit(limit).all()

    history_items = [
        ModelApprovalStatusHistoryItem(
            history_id=record.history_id,
            old_status=record.old_status,
            old_status_label=get_status_label(record.old_status),
            new_status=record.new_status,
            new_status_label=get_status_label(record.new_status) or record.new_status,
            changed_at=record.changed_at,
            trigger_type=record.trigger_type,
            trigger_entity_type=record.trigger_entity_type,
            trigger_entity_id=record.trigger_entity_id,
            notes=record.notes,
        )
        for record in history_records
    ]

    return ModelApprovalStatusHistoryResponse(
        model_id=model.model_id,
        model_name=model.model_name,
        total_count=total_count,
        history=history_items,
    )

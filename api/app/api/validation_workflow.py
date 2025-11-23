"""Validation workflow API endpoints."""
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Union, Dict, Tuple
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_, func
from fpdf import FPDF
import tempfile
import os

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    User, Model, TaxonomyValue, Taxonomy, AuditLog, Region,
    ValidationRequest, ValidationRequestModelVersion, ValidationStatusHistory, ValidationAssignment,
    ValidationOutcome, ValidationReviewOutcome, ValidationApproval, ValidationGroupingMemory,
    ValidationPolicy, ModelRegion, Region,
    ValidationComponentDefinition, ValidationPlan, ValidationPlanComponent,
    ComponentDefinitionConfiguration, ComponentDefinitionConfigItem
)
from app.schemas.validation import (
    ValidationRequestCreate, ValidationRequestUpdate, ValidationRequestStatusUpdate,
    ValidationRequestDecline, ValidationRequestMarkSubmission, ValidationApprovalUnlink,
    ValidationWarning, ValidationRequestWarningsResponse,
    ValidationRequestResponse, ValidationRequestDetailResponse, ValidationRequestListResponse,
    ValidationAssignmentCreate, ValidationAssignmentUpdate, ValidationAssignmentResponse,
    ReviewerSignOffRequest,
    ValidationOutcomeCreate, ValidationOutcomeUpdate, ValidationOutcomeResponse,
    ValidationReviewOutcomeCreate, ValidationReviewOutcomeUpdate, ValidationReviewOutcomeResponse,
    ValidationApprovalCreate, ValidationApprovalUpdate, ValidationApprovalResponse,
    ValidationStatusHistoryResponse,
    ValidationComponentDefinitionResponse, ValidationComponentDefinitionUpdate,
    ValidationPlanCreate, ValidationPlanUpdate, ValidationPlanResponse,
    PlanTemplateSuggestion, PlanTemplateSuggestionsResponse,
    ConfigurationResponse, ConfigurationDetailResponse, ConfigurationItemResponse, ConfigurationPublishRequest
)

router = APIRouter()


# ==================== HELPER FUNCTIONS ====================

def check_validator_or_admin(user: User):
    """Check if user has Validator or Admin role."""
    if user.role not in ("Validator", "Admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Validators and Admins can perform this action"
        )


def check_admin(user: User):
    """Check if user has Admin role."""
    if user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can perform this action"
        )


def check_target_completion_date_warnings(
    db: Session,
    request_data: ValidationRequestCreate
) -> List[ValidationWarning]:
    """
    Check for warnings/issues with the target completion date.

    Returns list of warnings for:
    1. Model change lead time violations
    2. Implementation date conflicts
    3. Revalidation overdue scenarios
    """
    from app.models import Model, ValidationPolicy, ValidationWorkflowSLA, ModelVersion
    from app.models.validation import validation_request_models
    from datetime import timedelta

    warnings = []
    target_date = request_data.target_completion_date
    model_versions_dict = request_data.model_versions or {}

    # Get SLA configuration for lead time
    sla = db.query(ValidationWorkflowSLA).first()
    default_lead_time = sla.model_change_lead_time_days if sla else 90

    # Load models with their versions
    models = db.query(Model).filter(
        Model.model_id.in_(request_data.model_ids)).all()

    for model in models:
        version_id = model_versions_dict.get(model.model_id)
        version = None

        if version_id:
            version = db.query(ModelVersion).filter(
                ModelVersion.version_id == version_id).first()

        # Check 2: Implementation date already passed
        if version and version.production_date and target_date > version.production_date:
            warnings.append(ValidationWarning(
                warning_type="IMPLEMENTATION_DATE",
                severity="ERROR",
                model_id=model.model_id,
                model_name=model.model_name,
                version_number=version.version_number,
                message=f"Target completion date ({target_date.isoformat()}) is after the implementation date ({version.production_date.isoformat()}). Validation must be completed prior to implementation.",
                details={
                    "implementation_date": version.production_date.isoformat(),
                    "target_completion_date": target_date.isoformat()
                }
            ))

        # Check 3: Revalidation overdue
        # Get the last completed validation for this model
        # Find APPROVED status
        approved_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Validation Request Status",
            TaxonomyValue.code == "APPROVED"
        ).first()

        if approved_status:
            last_validation = db.query(ValidationRequest).join(
                validation_request_models
            ).filter(
                validation_request_models.c.model_id == model.model_id,
                ValidationRequest.current_status_id == approved_status.value_id
            ).order_by(desc(ValidationRequest.updated_at)).first()
        else:
            last_validation = None

        if last_validation and model.risk_tier_id:
            policy = db.query(ValidationPolicy).filter(
                ValidationPolicy.risk_tier_id == model.risk_tier_id
            ).first()

            if policy:
                # Calculate when next validation is due
                next_validation_due = last_validation.updated_at.date(
                ) + timedelta(days=policy.frequency_months * 30)
                grace_period_days = 30  # Allow 30 day grace period
                overdue_date = next_validation_due + \
                    timedelta(days=grace_period_days)

                if target_date > overdue_date:
                    warnings.append(ValidationWarning(
                        warning_type="REVALIDATION_OVERDUE",
                        severity="WARNING",
                        model_id=model.model_id,
                        model_name=model.model_name,
                        version_number=version.version_number if version else None,
                        message=f"Target completion date would result in model being overdue for revalidation (due {next_validation_due.isoformat()}, grace period until {overdue_date.isoformat()}).",
                        details={
                            "last_validation_date": last_validation.updated_at.date().isoformat(),
                            "next_due_date": next_validation_due.isoformat(),
                            "grace_period_end": overdue_date.isoformat(),
                            "target_completion_date": target_date.isoformat(),
                            "frequency_months": policy.frequency_months
                        }
                    ))

    return warnings


def get_taxonomy_value_by_code(db: Session, taxonomy_name: str, code: str) -> TaxonomyValue:
    """Get taxonomy value by taxonomy name and code."""
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == taxonomy_name).first()
    if not taxonomy:
        raise HTTPException(
            status_code=404, detail=f"Taxonomy '{taxonomy_name}' not found")

    value = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.code == code
    ).first()
    if not value:
        raise HTTPException(
            status_code=404, detail=f"Taxonomy value '{code}' not found in '{taxonomy_name}'")
    return value


def get_allowed_approval_roles(db: Session) -> List[str]:
    """Fetch active approval role labels from the Approval Role taxonomy."""
    taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Approval Role"
    ).first()
    if not taxonomy:
        return []

    return [
        value.label for value in db.query(TaxonomyValue)
        .filter(TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id, TaxonomyValue.is_active == True)
        .order_by(TaxonomyValue.sort_order, TaxonomyValue.label)
    ]


def is_valid_approver_role(role: str, allowed_roles: List[str]) -> bool:
    """Check if a role matches an allowed base role (supports region-coded prefixes)."""
    if not allowed_roles:
        return True  # Do not block if taxonomy not seeded

    for base in allowed_roles:
        if role == base:
            return True
        if role.startswith(f"{base} "):
            return True
        if role.startswith(f"{base}-"):
            return True
        if role.startswith(f"{base}("):
            return True
        if role.startswith(f"{base} -"):
            return True
    return False


def validate_approver_role_or_raise(db: Session, approver_role: str):
    """Validate approver role against Approval Role taxonomy."""
    allowed_roles = get_allowed_approval_roles(db)
    if not is_valid_approver_role(approver_role, allowed_roles):
        raise HTTPException(
            status_code=400,
            detail=f"approver_role must align with Approval Role taxonomy values: {allowed_roles}"
        )


def normalize_region_fields_for_approval(
    approval_type: str,
    region_id: Optional[int],
    represented_region_id: Optional[int]
) -> Tuple[str, Optional[int], Optional[int]]:
    """Ensure regional approvals carry region context and global approvals stay null."""
    approval_type = approval_type or "Global"

    if approval_type == "Regional":
        if region_id is None:
            raise HTTPException(
                status_code=400,
                detail="region_id is required when approval_type is 'Regional'"
            )
        represented_region_id = represented_region_id or region_id
    else:
        region_id = None
        represented_region_id = None

    return approval_type, region_id, represented_region_id


def check_valid_status_transition(old_status_code: Optional[str], new_status_code: str) -> bool:
    """Validate status transition according to workflow rules."""
    # Define valid transitions
    valid_transitions = {
        None: ["INTAKE"],  # Initial creation
        "INTAKE": ["PLANNING", "CANCELLED", "ON_HOLD"],
        "PLANNING": ["IN_PROGRESS", "CANCELLED", "ON_HOLD"],
        "IN_PROGRESS": ["REVIEW", "CANCELLED", "ON_HOLD"],
        "REVIEW": ["PENDING_APPROVAL", "IN_PROGRESS", "CANCELLED", "ON_HOLD"],
        "PENDING_APPROVAL": ["APPROVED", "REVIEW", "CANCELLED", "ON_HOLD"],
        "APPROVED": [],  # Terminal state
        "ON_HOLD": ["INTAKE", "PLANNING", "IN_PROGRESS", "REVIEW", "PENDING_APPROVAL", "CANCELLED"],
        "CANCELLED": [],  # Terminal state
    }

    allowed = valid_transitions.get(old_status_code, [])
    return new_status_code in allowed


def create_status_history_entry(
    db: Session,
    request_id: int,
    old_status_id: Optional[int],
    new_status_id: int,
    changed_by_id: int,
    change_reason: Optional[str] = None
):
    """Create a status history entry."""
    history = ValidationStatusHistory(
        request_id=request_id,
        old_status_id=old_status_id,
        new_status_id=new_status_id,
        changed_by_id=changed_by_id,
        change_reason=change_reason,
        changed_at=datetime.utcnow()
    )
    db.add(history)


def update_version_statuses_for_validation(
    db: Session,
    validation_request: ValidationRequest,
    new_validation_status: str,
    current_user: User
):
    """
    Auto-update linked model version statuses based on validation request status changes.

    Lifecycle transitions:
    - INTAKE/PLANNING -> IN_PROGRESS: Version moves DRAFT -> IN_VALIDATION
    - Any status -> APPROVED: Version moves IN_VALIDATION -> APPROVED
    - Any status -> CANCELLED/ON_HOLD: Version returns to DRAFT (if not yet approved)
    """
    from app.models.model_version import ModelVersion
    from app.schemas.model_version import VersionStatus

    # Get all linked versions via association table
    for model_version_assoc in validation_request.model_versions_assoc:
        if not model_version_assoc.version_id:
            continue  # Skip if no version linked

        version = db.query(ModelVersion).filter(
            ModelVersion.version_id == model_version_assoc.version_id
        ).first()

        if not version:
            continue

        old_version_status = version.status
        new_version_status = None

        # Determine new version status based on validation status
        if new_validation_status == "IN_PROGRESS":
            # When validation work begins, move version to IN_VALIDATION
            if version.status == VersionStatus.DRAFT:
                new_version_status = VersionStatus.IN_VALIDATION

        elif new_validation_status == "APPROVED":
            # When validation is approved, move version to APPROVED
            if version.status == VersionStatus.IN_VALIDATION:
                new_version_status = VersionStatus.APPROVED

        elif new_validation_status in ["CANCELLED", "ON_HOLD"]:
            # If validation is cancelled or on hold, revert to DRAFT (unless already approved)
            if version.status == VersionStatus.IN_VALIDATION:
                new_version_status = VersionStatus.DRAFT

        # Apply status change if determined
        if new_version_status and new_version_status != old_version_status:
            version.status = new_version_status

            # Create audit log for version status change
            from app.core.audit import create_audit_log
            create_audit_log(
                db=db,
                entity_type="ModelVersion",
                entity_id=version.version_id,
                action="AUTO_STATUS_UPDATE",
                user_id=current_user.user_id,
                changes={
                    "status": {
                        "old": old_version_status,
                        "new": new_version_status
                    },
                    "trigger": f"Validation request {validation_request.request_id} status changed to {new_validation_status}"
                }
            )


def check_validator_independence(db: Session, model_ids: List[int], validator_id: int) -> bool:
    """Check if validator is independent from all models (not owner or developer of any)."""
    models = db.query(Model).filter(Model.model_id.in_(model_ids)).all()
    if not models or len(models) != len(model_ids):
        return False

    # Validator cannot be model owner or developer of any of the models
    for model in models:
        if model.owner_id == validator_id or model.developer_id == validator_id:
            return False

    return True


def calculate_days_in_status(request: ValidationRequest) -> int:
    """Calculate how many days the request has been in current status.

    Uses pre-loaded status_history to avoid N+1 queries.
    """
    # Find latest history entry for current status (already loaded via eager-loading)
    latest_history = next(
        (h for h in sorted(request.status_history, key=lambda x: x.changed_at, reverse=True)
         if h.new_status_id == request.current_status_id),
        None
    )

    if latest_history:
        delta = datetime.utcnow() - latest_history.changed_at
        return delta.days
    else:
        # If no history, use creation date
        delta = datetime.utcnow() - request.created_at
        return delta.days


def update_grouping_memory(db: Session, validation_request: ValidationRequest, models: List[Model]):
    """Update validation grouping memory for multi-model regular validations.

    Only updates for regular validations (INITIAL, ANNUAL, COMPREHENSIVE, ONGOING).
    Skips targeted validations (TARGETED, INTERIM).
    Only updates if 2 or more models are being validated together.
    """
    # Regular validation type codes that should update grouping memory
    REGULAR_VALIDATION_TYPES = ["INITIAL",
                                "ANNUAL", "COMPREHENSIVE", "ONGOING"]

    # Check if this is a multi-model validation
    if len(models) < 2:
        return

    # Get validation type code
    validation_type = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == validation_request.validation_type_id
    ).first()

    if not validation_type or validation_type.code not in REGULAR_VALIDATION_TYPES:
        return

    # For each model, update or create grouping memory
    model_ids = [m.model_id for m in models]

    for model in models:
        # Get other model IDs (exclude current model)
        other_model_ids = [mid for mid in model_ids if mid != model.model_id]

        # Check if grouping memory exists for this model
        existing_memory = db.query(ValidationGroupingMemory).filter(
            ValidationGroupingMemory.model_id == model.model_id
        ).first()

        if existing_memory:
            # Update existing record
            existing_memory.last_validation_request_id = validation_request.request_id
            existing_memory.grouped_model_ids = json.dumps(other_model_ids)
            existing_memory.is_regular_validation = True
            existing_memory.updated_at = datetime.utcnow()
        else:
            # Create new record
            new_memory = ValidationGroupingMemory(
                model_id=model.model_id,
                last_validation_request_id=validation_request.request_id,
                grouped_model_ids=json.dumps(other_model_ids),
                is_regular_validation=True,
                updated_at=datetime.utcnow()
            )
            db.add(new_memory)


def compute_suggested_regions(model_ids: List[int], db: Session) -> List[dict]:
    """Compute union of all regions from selected models (Phase 4).

    Returns a list of region dicts with region_id, code, name, and requires_regional_approval.
    This enables automatic region suggestion in the validation workflow UI.
    """
    if not model_ids:
        return []

    # Get all model-region links for selected models
    model_regions = db.query(ModelRegion).options(
        joinedload(ModelRegion.region)
    ).filter(
        ModelRegion.model_id.in_(model_ids)
    ).all()

    # Extract unique regions using a dict to deduplicate by region_id
    regions_dict = {}
    for mr in model_regions:
        if mr.region_id not in regions_dict:
            regions_dict[mr.region_id] = {
                "region_id": mr.region.region_id,
                "code": mr.region.code,
                "name": mr.region.name,
                "requires_regional_approval": mr.region.requires_regional_approval
            }

    return list(regions_dict.values())


def auto_assign_approvers(
    db: Session,
    validation_request: ValidationRequest,
    current_user: User
) -> None:
    """Auto-assign approvers based on validation scope, model ownership, and deployment regions (Phase 5).

    Business Rules:
    1. Collect all relevant regions from:
       - Model governance ownership (wholly_owned_region_id)
       - Model deployment regions (model_regions)
       - Validation request scope (regions)

    2. If ALL models are wholly-owned by the SAME region AND
       all deployment regions (if any) are ONLY that region AND
       validation scope (if any) is ONLY that region:
       - Only assign Regional Approvers for that region

    3. Otherwise (mixed ownership, multi-region deployment, or global scope):
       - Assign Global Approvers
       - ALSO assign Regional Approvers for all relevant regions that require approval

    Creates ValidationApproval records with approval_status="Pending" and is_required=True.
    """
    from app.models.user import UserRole, user_regions

    approvals_to_create = []
    assigned_approver_ids = set()  # Track to avoid duplicates

    # Collect all unique regions across governance, deployment, and validation scope
    all_region_ids = set()

    if validation_request.models and len(validation_request.models) > 0:
        # Collect governance regions (wholly_owned_region_id)
        governance_region_ids = set()
        for model in validation_request.models:
            if model.wholly_owned_region_id is not None:
                all_region_ids.add(model.wholly_owned_region_id)
                governance_region_ids.add(model.wholly_owned_region_id)

            # Collect deployment regions (model_regions)
            for model_region in model.model_regions:
                all_region_ids.add(model_region.region_id)

        # Collect validation request scope regions
        for region in validation_request.regions:
            all_region_ids.add(region.region_id)

        # Check if this is a single-region scenario
        # All models must be wholly-owned by the same region
        wholly_owned_region_id = None
        all_wholly_owned_by_same_region = False

        if len(governance_region_ids) == 1:
            wholly_owned_region_id = list(governance_region_ids)[0]
            # Check if ALL regions (deployment + validation scope) are only this region
            if all_region_ids == {wholly_owned_region_id}:
                all_wholly_owned_by_same_region = True

        # Apply business rules
        if all_wholly_owned_by_same_region and wholly_owned_region_id is not None:
            # Pure single-region scenario - only assign Regional Approvers
            regional_approvers = db.query(User).join(user_regions).filter(
                User.role == UserRole.REGIONAL_APPROVER,
                user_regions.c.region_id == wholly_owned_region_id
            ).all()

            region = db.query(Region).filter(
                Region.region_id == wholly_owned_region_id).first()
            region_code = region.code if region else f"Region {wholly_owned_region_id}"

            for approver in regional_approvers:
                if approver.user_id not in assigned_approver_ids:
                    approver_role = f"Regional Approver ({region_code})"
                    validate_approver_role_or_raise(db, approver_role)
                    approvals_to_create.append(ValidationApproval(
                        request_id=validation_request.request_id,
                        approver_id=approver.user_id,
                        approver_role=approver_role,
                        approval_type="Regional",
                        region_id=wholly_owned_region_id,
                        is_required=True,
                        approval_status="Pending",
                        represented_region_id=wholly_owned_region_id,  # Snapshot region context
                        created_at=datetime.utcnow()
                    ))
                    assigned_approver_ids.add(approver.user_id)
        else:
            # Multi-region or global scenario
            # Assign Global Approvers
            global_approvers = db.query(User).filter(
                User.role == UserRole.GLOBAL_APPROVER
            ).all()

            for approver in global_approvers:
                if approver.user_id not in assigned_approver_ids:
                    approver_role = "Global Approver"
                    validate_approver_role_or_raise(db, approver_role)
                    approvals_to_create.append(ValidationApproval(
                        request_id=validation_request.request_id,
                        approver_id=approver.user_id,
                        approver_role=approver_role,
                        approval_type="Global",
                        is_required=True,
                        approval_status="Pending",
                        represented_region_id=None,  # Global approver - no specific region
                        created_at=datetime.utcnow()
                    ))
                    assigned_approver_ids.add(approver.user_id)

            # Additionally, assign Regional Approvers for all relevant regions
            for region_id in all_region_ids:
                region = db.query(Region).filter(
                    Region.region_id == region_id).first()
                if region and region.requires_regional_approval:
                    regional_approvers = db.query(User).join(user_regions).filter(
                        User.role == UserRole.REGIONAL_APPROVER,
                        user_regions.c.region_id == region_id
                    ).all()

                    for approver in regional_approvers:
                        if approver.user_id not in assigned_approver_ids:
                            approver_role = f"Regional Approver ({region.code})"
                            validate_approver_role_or_raise(db, approver_role)
                            approvals_to_create.append(ValidationApproval(
                                request_id=validation_request.request_id,
                                approver_id=approver.user_id,
                                approver_role=approver_role,
                                approval_type="Regional",
                                region_id=region_id,
                                is_required=True,
                                approval_status="Pending",
                                represented_region_id=region_id,  # Snapshot region context
                                created_at=datetime.utcnow()
                            ))
                            assigned_approver_ids.add(approver.user_id)

    # Add all approvals to session
    for approval in approvals_to_create:
        db.add(approval)

    # Create audit log entry
    if approvals_to_create:
        approver_info = [
            {"approver_id": a.approver_id, "role": a.approver_role}
            for a in approvals_to_create
        ]
        audit_log = AuditLog(
            entity_type="ValidationRequest",
            entity_id=validation_request.request_id,
            action="AUTO_ASSIGN_APPROVERS",
            user_id=current_user.user_id,
            changes={
                "approvers_assigned": len(approvals_to_create),
                "approvers": approver_info,
                "assignment_type": "Automatic"
            },
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)


# ==================== REVALIDATION LIFECYCLE HELPERS ====================

def calculate_model_revalidation_status(model: Model, db: Session) -> Dict:
    """
    Calculate revalidation status for a model dynamically.
    No stored schedule - computed from last validation + policy.

    Returns dict with:
        - model_id, model_name, model_owner, risk_tier
        - status: "Never Validated" | "No Policy Configured" | "Upcoming" |
                  "Awaiting Submission" | "In Grace Period" | "Submission Overdue" |
                  "Validation In Progress" | "Validation Overdue" | "Revalidation Overdue (No Request)" |
                  "Should Create Request"
        - last_validation_date, next_submission_due, grace_period_end, next_validation_due
        - days_until_submission_due, days_until_validation_due
        - active_request_id, submission_received
    """

    # Find most recent APPROVED validation for this model
    last_validation = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.current_status.has(TaxonomyValue.code == "APPROVED")
    ).order_by(
        ValidationRequest.updated_at.desc()
    ).first()

    if not last_validation:
        return {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "model_owner": model.owner.full_name if model.owner else "Unknown",
            "risk_tier": model.risk_tier.label if model.risk_tier else None,
            "status": "Never Validated",
            "last_validation_date": None,
            "next_submission_due": None,
            "grace_period_end": None,
            "next_validation_due": None,
            "days_until_submission_due": None,
            "days_until_validation_due": None,
            "active_request_id": None,
            "submission_received": None
        }

    # Get validation policy for this model's risk tier
    policy = db.query(ValidationPolicy).filter(
        ValidationPolicy.risk_tier_id == model.risk_tier_id
    ).first()

    if not policy:
        return {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "model_owner": model.owner.full_name if model.owner else "Unknown",
            "risk_tier": model.risk_tier.label if model.risk_tier else None,
            "status": "No Policy Configured",
            "last_validation_date": last_validation.updated_at.date(),
            "next_submission_due": None,
            "grace_period_end": None,
            "next_validation_due": None,
            "days_until_submission_due": None,
            "days_until_validation_due": None,
            "active_request_id": None,
            "submission_received": None
        }

    # Calculate dates
    last_completed = last_validation.updated_at.date()
    submission_due = last_completed + relativedelta(months=policy.frequency_months)
    grace_period_end = submission_due + relativedelta(months=3)
    validation_due = grace_period_end + timedelta(days=policy.model_change_lead_time_days)

    # Check if active revalidation request exists
    active_request = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.validation_type.has(TaxonomyValue.code.in_(["COMPREHENSIVE", "ANNUAL"])),
        ValidationRequest.prior_validation_request_id == last_validation.request_id,
        ValidationRequest.current_status.has(TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"]))
    ).first()

    today = date.today()

    # Determine status
    if active_request:
        if not active_request.submission_received_date:
            if today > grace_period_end:
                status = "Submission Overdue"
            elif today > submission_due:
                status = "In Grace Period"
            else:
                status = "Awaiting Submission"
        else:
            if today > validation_due:
                status = "Validation Overdue"
            else:
                status = "Validation In Progress"
    else:
        # No active request
        if today > validation_due:
            status = "Revalidation Overdue (No Request)"
        elif today > grace_period_end:
            status = "Should Create Request"
        else:
            status = "Upcoming"

    return {
        "model_id": model.model_id,
        "model_name": model.model_name,
        "model_owner": model.owner.full_name if model.owner else "Unknown",
        "risk_tier": model.risk_tier.label if model.risk_tier else None,
        "status": status,
        "last_validation_date": last_completed,
        "next_submission_due": submission_due,
        "grace_period_end": grace_period_end,
        "next_validation_due": validation_due,
        "days_until_submission_due": (submission_due - today).days,
        "days_until_validation_due": (validation_due - today).days,
        "active_request_id": active_request.request_id if active_request else None,
        "submission_received": active_request.submission_received_date if active_request else None
    }


def get_models_needing_revalidation(
    db: Session,
    days_ahead: int = 90,
    include_overdue: bool = True
) -> List[Dict]:
    """
    Get all models that need revalidation (upcoming or overdue).
    Calculates dynamically - no stored schedule.

    Args:
        db: Database session
        days_ahead: Look ahead this many days for upcoming revalidations
        include_overdue: Include models with overdue revalidations

    Returns:
        List of revalidation status dicts sorted by submission due date
    """

    today = date.today()
    results = []

    # Get all active models with risk tiers (needed for policy lookup)
    models = db.query(Model).filter(
        Model.status == "Active",
        Model.risk_tier_id.isnot(None)
    ).all()

    for model in models:
        revalidation_status = calculate_model_revalidation_status(model, db)

        # Filter based on criteria
        if include_overdue and "Overdue" in revalidation_status["status"]:
            results.append(revalidation_status)
        elif revalidation_status["days_until_submission_due"] is not None:
            if revalidation_status["days_until_submission_due"] <= days_ahead:
                results.append(revalidation_status)

    # Sort by submission due date (None values go to end)
    results.sort(key=lambda x: x["next_submission_due"] if x["next_submission_due"] else date.max)

    return results


# ==================== VALIDATION REQUEST ENDPOINTS ====================

@router.get("/test/revalidation-status/{model_id}")
def test_revalidation_status(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    TEST ENDPOINT: Get revalidation status for a specific model.
    For testing Phase 2 helper functions.
    """
    model = db.query(Model).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    return calculate_model_revalidation_status(model, db)


@router.get("/test/models-needing-revalidation")
def test_models_needing_revalidation(
    days_ahead: int = Query(90, description="Look ahead this many days"),
    include_overdue: bool = Query(True, description="Include overdue models"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    TEST ENDPOINT: Get all models needing revalidation.
    For testing Phase 2 helper functions.
    """
    return get_models_needing_revalidation(db, days_ahead, include_overdue)


@router.post("/requests/check-warnings", response_model=ValidationRequestWarningsResponse)
def check_validation_request_warnings(
    request_data: ValidationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check for warnings about target completion date without creating a request.

    This endpoint validates the request data and returns warnings about:
    - Model change lead time violations
    - Implementation date conflicts
    - Revalidation overdue scenarios
    """
    # Run validation checks
    warnings = check_target_completion_date_warnings(db, request_data)

    # Determine if user can proceed (no ERROR-severity warnings)
    has_errors = any(w.severity == "ERROR" for w in warnings)

    return ValidationRequestWarningsResponse(
        has_warnings=len(warnings) > 0,
        can_proceed=not has_errors,
        warnings=warnings,
        request_data=request_data
    )


@router.post("/requests/", response_model=Union[ValidationRequestResponse, ValidationRequestWarningsResponse], status_code=status.HTTP_201_CREATED)
def create_validation_request(
    request_data: ValidationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new validation request.

    If check_warnings=True, returns warnings without creating the request.
    Otherwise, creates the request and returns the created object.
    """
    # Verify at least one model is specified
    if not request_data.model_ids or len(request_data.model_ids) == 0:
        raise HTTPException(
            status_code=400, detail="At least one model must be specified")

    # Verify all models exist (eagerly load model_regions for approver assignment)
    from sqlalchemy.orm import joinedload
    models = db.query(Model).options(
        joinedload(Model.model_regions)
    ).filter(Model.model_id.in_(request_data.model_ids)).all()
    if len(models) != len(request_data.model_ids):
        raise HTTPException(
            status_code=404, detail="One or more models not found")

    # If check_warnings flag is set, return warnings without creating
    if request_data.check_warnings:
        warnings = check_target_completion_date_warnings(db, request_data)
        has_errors = any(w.severity == "ERROR" for w in warnings)
        return ValidationRequestWarningsResponse(
            has_warnings=len(warnings) > 0,
            can_proceed=not has_errors,
            warnings=warnings,
            request_data=request_data
        )

    # Verify validation type exists
    validation_type = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == request_data.validation_type_id
    ).first()
    if not validation_type:
        raise HTTPException(
            status_code=404, detail="Validation type not found")

    # Verify priority exists
    priority = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == request_data.priority_id
    ).first()
    if not priority:
        raise HTTPException(status_code=404, detail="Priority not found")

    # Get initial status (INTAKE)
    intake_status = get_taxonomy_value_by_code(
        db, "Validation Request Status", "INTAKE")

    # Verify regions if provided
    regions = []
    if request_data.region_ids:
        from app.models import Region
        regions = db.query(Region).filter(
            Region.region_id.in_(request_data.region_ids)).all()
        if len(regions) != len(request_data.region_ids):
            raise HTTPException(
                status_code=404, detail="One or more regions not found")

    # Create the request
    validation_request = ValidationRequest(
        request_date=date.today(),
        requestor_id=current_user.user_id,
        validation_type_id=request_data.validation_type_id,
        priority_id=request_data.priority_id,
        target_completion_date=request_data.target_completion_date,
        trigger_reason=request_data.trigger_reason,
        current_status_id=intake_status.value_id,
        prior_validation_request_id=request_data.prior_validation_request_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(validation_request)
    db.flush()

    # Associate models with optional version tracking
    model_versions_dict = request_data.model_versions or {}
    for model in models:
        version_id = model_versions_dict.get(model.model_id)

        # Verify version exists and belongs to this model if specified
        if version_id:
            from app.models import ModelVersion
            version = db.query(ModelVersion).filter(
                ModelVersion.version_id == version_id,
                ModelVersion.model_id == model.model_id
            ).first()
            if not version:
                raise HTTPException(
                    status_code=400,
                    detail=f"Version {version_id} not found for model {model.model_name}"
                )

        # Create association with version tracking
        assoc = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model.model_id,
            version_id=version_id
        )
        db.add(assoc)

    # Associate regions using the many-to-many relationship
    if regions:
        validation_request.regions.extend(regions)

    # Flush to populate relationships before auto-assigning approvers
    db.flush()

    # Calculate and set submission_due_date for revalidation requests
    # This locks in the due date at request creation time based on current policy
    calculated_due_date = validation_request._calculate_submission_due_date()
    if calculated_due_date:
        validation_request.submission_due_date = calculated_due_date

    # Create initial status history entry
    create_status_history_entry(
        db, validation_request.request_id, None, intake_status.value_id, current_user.user_id
    )

    # Create audit log
    model_names = [m.model_name for m in models]
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=validation_request.request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "model_ids": request_data.model_ids,
            "model_names": model_names,
            "validation_type": validation_type.label,
            "priority": priority.label,
            "status": "Intake"
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    # Update grouping memory for multi-model regular validations
    update_grouping_memory(db, validation_request, models)

    # Auto-assign approvers based on validation scope (Phase 5)
    auto_assign_approvers(db, validation_request, current_user)

    db.commit()

    # Reload with relationships (including approvals with their approver)
    db.refresh(validation_request)
    validation_request_with_approvals = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.approvals).joinedload(
            ValidationApproval.approver)
    ).filter(ValidationRequest.request_id == validation_request.request_id).first()

    return validation_request_with_approvals


@router.get("/requests/", response_model=List[ValidationRequestListResponse])
def list_validation_requests(
    model_id: Optional[int] = None,
    status_id: Optional[int] = None,
    priority_id: Optional[int] = None,
    requestor_id: Optional[int] = None,
    region_id: Optional[int] = None,
    scope: Optional[str] = Query(
        None, description="Filter by scope: 'global' (region_id IS NULL) or 'regional' (region_id IS NOT NULL)"),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List validation requests with optional filters.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: See all validation requests
    - User: Only see validation requests for models they have access to
    """
    from app.models.validation import validation_request_models
    from app.core.rls import apply_validation_request_rls

    query = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.assignments).joinedload(
            ValidationAssignment.validator),
        joinedload(ValidationRequest.status_history)  # Eager-load for days_in_status calculation
    )

    # Apply Row-Level Security BEFORE other filters
    from app.core.rls import can_see_all_data
    rls_applied = not can_see_all_data(current_user)
    query = apply_validation_request_rls(query, current_user, db)

    # Filter by model_id
    # If RLS was applied, the join already exists, so just add the filter
    # Otherwise, we need to join the association table
    if model_id:
        if rls_applied:
            # RLS already joined ValidationRequestModelVersion, just add filter
            query = query.filter(ValidationRequestModelVersion.model_id == model_id)
        else:
            # Privileged user - need to join the association table
            query = query.join(validation_request_models).filter(
                validation_request_models.c.model_id == model_id)
    if status_id:
        query = query.filter(ValidationRequest.current_status_id == status_id)
    if priority_id:
        query = query.filter(ValidationRequest.priority_id == priority_id)
    if requestor_id:
        query = query.filter(ValidationRequest.requestor_id == requestor_id)
    if region_id:
        # Filter by requests that have this specific region
        from app.models.validation import validation_request_regions
        query = query.join(validation_request_regions).filter(
            validation_request_regions.c.region_id == region_id)
    if scope:
        from app.models.validation import validation_request_regions
        if scope.lower() == "global":
            # Global validations have no regions
            query = query.outerjoin(validation_request_regions).filter(
                validation_request_regions.c.request_id.is_(None))
        elif scope.lower() == "regional":
            # Regional validations have at least one region
            query = query.join(validation_request_regions)
        else:
            raise HTTPException(
                status_code=400, detail="Invalid scope. Must be 'global' or 'regional'")

    requests = query.order_by(desc(ValidationRequest.request_date)).offset(
        offset).limit(limit).all()

    # Transform to list response format
    result = []
    for req in requests:
        primary_validator = next(
            (a.validator.full_name for a in req.assignments if a.is_primary),
            None
        )
        result.append(ValidationRequestListResponse(
            request_id=req.request_id,
            model_ids=[m.model_id for m in req.models],
            model_names=[m.model_name for m in req.models],
            request_date=req.request_date,
            requestor_name=req.requestor.full_name,
            validation_type=req.validation_type.label,
            priority=req.priority.label,
            target_completion_date=req.target_completion_date,
            current_status=req.current_status.label,
            days_in_status=calculate_days_in_status(req),
            primary_validator=primary_validator,
            regions=req.regions if req.regions else [],
            created_at=req.created_at,
            updated_at=req.updated_at
        ))

    return result


@router.get("/requests/preview-regions")
def preview_suggested_regions(
    model_ids: str = Query(...,
                           description="Comma-separated list of model IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Preview suggested regions based on selected models (Phase 4).

    Returns the union of all regions associated with the selected models.
    This helps users understand which regional approvals may be required.
    """
    # Parse comma-separated model_ids
    try:
        model_id_list = [int(id.strip())
                         for id in model_ids.split(",") if id.strip()]
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid model_ids format. Use comma-separated integers.")

    if not model_id_list:
        return {"suggested_regions": []}

    # Compute suggested regions
    suggested_regions = compute_suggested_regions(model_id_list, db)

    return {
        "model_ids": model_id_list,
        "suggested_regions": suggested_regions
    }


@router.get("/requests/{request_id}", response_model=ValidationRequestDetailResponse)
def get_validation_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed validation request with all relationships.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can access any validation request
    - User: Can only access validation requests for models they have access to
    """
    from app.core.rls import can_access_validation_request

    # Check RLS access
    if not can_access_validation_request(request_id, current_user, db):
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models).joinedload(Model.model_regions),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.assignments).joinedload(
            ValidationAssignment.validator),
        joinedload(ValidationRequest.status_history).joinedload(
            ValidationStatusHistory.old_status),
        joinedload(ValidationRequest.status_history).joinedload(
            ValidationStatusHistory.new_status),
        joinedload(ValidationRequest.status_history).joinedload(
            ValidationStatusHistory.changed_by),
        joinedload(ValidationRequest.approvals).joinedload(
            ValidationApproval.approver),
        joinedload(ValidationRequest.outcome),
        joinedload(ValidationRequest.review_outcome).joinedload(
            ValidationReviewOutcome.reviewer)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    return validation_request


@router.patch("/requests/{request_id}", response_model=ValidationRequestResponse)
def update_validation_request(
    request_id: int,
    update_data: ValidationRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update validation request (only editable fields, not status)."""
    check_validator_or_admin(current_user)

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions)
    ).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    # Check if request is locked (in approval stage)
    status_code = validation_request.current_status.code if validation_request.current_status else None
    if status_code in ["PENDING_APPROVAL", "APPROVED"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot edit request in Pending Approval or Approved status"
        )

    # Track changes for audit log
    changes = {}
    update_dict = update_data.model_dump(exclude_unset=True)

    # Handle region_ids separately (many-to-many relationship)
    if 'region_ids' in update_dict:
        from app.models import Region
        new_region_ids = update_dict.pop('region_ids')
        old_region_ids = [r.region_id for r in validation_request.regions]

        if set(old_region_ids) != set(new_region_ids):
            # Update regions
            new_regions = db.query(Region).filter(Region.region_id.in_(
                new_region_ids)).all() if new_region_ids else []
            validation_request.regions = new_regions
            changes['region_ids'] = {
                "old": old_region_ids, "new": new_region_ids}

    for field, new_value in update_dict.items():
        old_value = getattr(validation_request, field)
        if old_value != new_value:
            setattr(validation_request, field, new_value)
            changes[field] = {"old": str(old_value), "new": str(new_value)}

    if changes:
        validation_request.updated_at = datetime.utcnow()

        audit_log = AuditLog(
            entity_type="ValidationRequest",
            entity_id=request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes,
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)

    db.commit()
    db.refresh(validation_request)
    return validation_request


@router.post("/requests/{request_id}/mark-submission", response_model=ValidationRequestResponse)
def mark_submission_received(
    request_id: int,
    submission_data: ValidationRequestMarkSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark submission as received and auto-transition from Planning to In Progress.
    This action starts the validation team's SLA timer.
    """
    check_validator_or_admin(current_user)

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions)
    ).filter(
        ValidationRequest.request_id == request_id
    ).first()

    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    # Check if submission already received
    if validation_request.submission_received_date:
        raise HTTPException(
            status_code=400,
            detail=f"Submission already marked as received on {validation_request.submission_received_date}"
        )

    # Validate submission date is not in the future
    if submission_data.submission_received_date > date.today():
        raise HTTPException(
            status_code=400,
            detail="Submission date cannot be in the future"
        )

    # Update submission_received_date
    old_date = validation_request.submission_received_date
    validation_request.submission_received_date = submission_data.submission_received_date

    # Auto-transition from Planning to In Progress
    current_status_code = validation_request.current_status.code if validation_request.current_status else None
    auto_transitioned = False

    if current_status_code == "PLANNING":
        # Get IN_PROGRESS status
        in_progress_status = get_taxonomy_value_by_code(
            db, "Validation Request Status", "IN_PROGRESS")

        if in_progress_status:
            old_status = validation_request.current_status
            validation_request.current_status_id = in_progress_status.value_id
            auto_transitioned = True

            # Create status history entry
            status_history = ValidationStatusHistory(
                request_id=request_id,
                old_status_id=old_status.value_id if old_status else None,
                new_status_id=in_progress_status.value_id,
                changed_by_id=current_user.user_id,
                change_reason=f"Auto-transitioned when submission received on {submission_data.submission_received_date}",
                changed_at=datetime.utcnow()
            )
            db.add(status_history)

    validation_request.updated_at = datetime.utcnow()

    # Create audit log
    changes = {
        "submission_received_date": {
            "old": str(old_date) if old_date else None,
            "new": str(submission_data.submission_received_date)
        }
    }

    if auto_transitioned:
        changes["status_auto_transition"] = {
            "from": "Planning",
            "to": "In Progress",
            "reason": "Submission received"
        }

    if submission_data.notes:
        changes["notes"] = submission_data.notes

    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="MARK_SUBMISSION_RECEIVED",
        user_id=current_user.user_id,
        changes=changes,
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    # Auto-update linked version statuses if we auto-transitioned to IN_PROGRESS
    if auto_transitioned:
        update_version_statuses_for_validation(
            db, validation_request, "IN_PROGRESS", current_user
        )

    db.commit()
    db.refresh(validation_request)
    return validation_request


@router.patch("/requests/{request_id}/status", response_model=ValidationRequestResponse)
def update_validation_request_status(
    request_id: int,
    status_update: ValidationRequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update validation request status with workflow validation."""
    check_validator_or_admin(current_user)

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.validation_plan)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    # Get new status
    new_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == status_update.new_status_id
    ).first()
    if not new_status:
        raise HTTPException(status_code=404, detail="New status not found")

    old_status = validation_request.current_status
    old_status_code = old_status.code if old_status else None
    new_status_code = new_status.code

    requires_plan, plan_region_codes = request_requires_validation_plan(
        db, validation_request)

    # Validate transition
    if not check_valid_status_transition(old_status_code, new_status_code):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{old_status_code}' to '{new_status_code}'"
        )

    # Additional business rules

    # BUSINESS RULE: Cannot move to or remain in active workflow statuses without a primary validator
    # Active workflow statuses that require a primary validator
    active_statuses_requiring_validator = ["PLANNING", "IN_PROGRESS", "REVIEW", "PENDING_APPROVAL"]

    if new_status_code in active_statuses_requiring_validator:
        # Check if there's a primary validator assigned
        primary_assignment = db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == request_id,
            ValidationAssignment.is_primary == True
        ).first()

        if not primary_assignment:
            stage_name = {
                "PLANNING": "Planning",
                "IN_PROGRESS": "In Progress",
                "REVIEW": "Review",
                "PENDING_APPROVAL": "Pending Approval"
            }.get(new_status_code, new_status_code)

            raise HTTPException(
                status_code=400,
                detail=f"Cannot move to {stage_name} stage without a primary validator assigned. Please assign a primary validator first."
            )

    if new_status_code == "REVIEW":
        # Must have at least one assigned validator
        if not validation_request.assignments:
            raise HTTPException(
                status_code=400, detail="Cannot move to Review without assigned validators")

        # Validate plan compliance (deviations must have rationale)
        is_valid, validation_errors = validate_plan_compliance(
            db,
            request_id,
            require_plan=requires_plan,
            required_region_codes=plan_region_codes
        )
        if not is_valid:
            error_message = "Validation plan compliance issues:\n" + "\n".join(f"• {err}" for err in validation_errors)
            raise HTTPException(
                status_code=400,
                detail=error_message
            )

    if new_status_code == "PENDING_APPROVAL":
        # Must have an outcome created
        if not validation_request.outcome:
            raise HTTPException(
                status_code=400, detail="Cannot move to Pending Approval without creating outcome")

        # Validate plan compliance (deviations must have rationale)
        is_valid, validation_errors = validate_plan_compliance(
            db,
            request_id,
            require_plan=requires_plan,
            required_region_codes=plan_region_codes
        )
        if not is_valid:
            error_message = "Validation plan compliance issues:\n" + "\n".join(f"• {err}" for err in validation_errors)
            raise HTTPException(
                status_code=400,
                detail=error_message
            )

        # If a reviewer is assigned, they must have signed off
        reviewer_assignment = db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == request_id,
            ValidationAssignment.is_reviewer == True
        ).first()
        if reviewer_assignment and not reviewer_assignment.reviewer_signed_off:
            raise HTTPException(
                status_code=400,
                detail="Reviewer must sign off before moving to Pending Approval"
            )

    # Update status
    old_status_id = validation_request.current_status_id
    validation_request.current_status_id = new_status.value_id
    validation_request.updated_at = datetime.utcnow()

    # Create status history
    create_status_history_entry(
        db, request_id, old_status_id, new_status.value_id,
        current_user.user_id, status_update.change_reason
    )

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="STATUS_CHANGE",
        user_id=current_user.user_id,
        changes={
            "old_status": old_status.label if old_status else None,
            "new_status": new_status.label,
            "reason": status_update.change_reason
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    # ===== VALIDATION PLAN LOCKING/UNLOCKING LOGIC =====
    # Lock plan when moving to Review or Pending Approval
    # Unlock plan when sending back from locked status to editable status
    if validation_request.validation_plan:
        plan = validation_request.validation_plan

        locked_statuses = ["REVIEW", "PENDING_APPROVAL", "APPROVED"]
        editable_statuses = ["INTAKE", "PLANNING", "IN_PROGRESS"]

        # LOCK: When moving TO Review/Pending Approval/Approved
        if new_status_code in locked_statuses and not plan.locked_at:
            active_config = db.query(ComponentDefinitionConfiguration).filter_by(is_active=True).first()

            if active_config:
                plan.config_id = active_config.config_id
                plan.locked_at = datetime.utcnow()
                plan.locked_by_user_id = current_user.user_id

                # Audit log for plan lock
                plan_lock_audit = AuditLog(
                    entity_type="ValidationPlan",
                    entity_id=plan.plan_id,
                    action="LOCK",
                    user_id=current_user.user_id,
                    changes={
                        "config_id": active_config.config_id,
                        "config_name": active_config.config_name,
                        "reason": f"Plan locked when validation moved to {new_status.label}",
                        "old_status": old_status.label if old_status else None,
                        "new_status": new_status.label
                    },
                    timestamp=datetime.utcnow()
                )
                db.add(plan_lock_audit)

        # UNLOCK: When moving FROM locked status TO editable status (sendback scenario)
        elif old_status_code in locked_statuses and new_status_code in editable_statuses and plan.locked_at:
            # Unlock the plan (config_id stays to preserve what it was locked to)
            plan.locked_at = None
            plan.locked_by_user_id = None

            # Audit log for plan unlock
            plan_unlock_audit = AuditLog(
                entity_type="ValidationPlan",
                entity_id=plan.plan_id,
                action="UNLOCK",
                user_id=current_user.user_id,
                changes={
                    "reason": f"Plan unlocked when validation sent back to {new_status.label}",
                    "previous_status": old_status.label if old_status else None,
                    "new_status": new_status.label,
                    "config_id_preserved": plan.config_id  # Still linked to original config
                },
                timestamp=datetime.utcnow()
            )
            db.add(plan_unlock_audit)

    # Auto-update linked model version statuses based on validation status
    update_version_statuses_for_validation(
        db, validation_request, new_status_code, current_user
    )

    db.commit()
    db.refresh(validation_request)
    return validation_request


@router.patch("/requests/{request_id}/decline", response_model=ValidationRequestResponse)
def decline_validation_request(
    request_id: int,
    decline_data: ValidationRequestDecline,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin-only: Decline a validation request by changing status to Cancelled."""
    # Admin-only access
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can decline validation requests"
        )

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.validation_plan)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    # Get CANCELLED status
    cancelled_status = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code == "CANCELLED"
    ).first()

    if not cancelled_status:
        raise HTTPException(
            status_code=500, detail="CANCELLED status not found in taxonomy")

    # Record old status for audit
    old_status = validation_request.current_status
    old_status_id = validation_request.current_status_id

    # Update validation request
    validation_request.current_status_id = cancelled_status.value_id
    validation_request.declined_by_id = current_user.user_id
    validation_request.decline_reason = decline_data.decline_reason
    validation_request.declined_at = datetime.utcnow()
    validation_request.updated_at = datetime.utcnow()

    # Create status history
    create_status_history_entry(
        db, request_id, old_status_id, cancelled_status.value_id,
        current_user.user_id, f"Declined: {decline_data.decline_reason}"
    )

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="DECLINED",
        user_id=current_user.user_id,
        changes={
            "old_status": old_status.label if old_status else None,
            "new_status": cancelled_status.label,
            "decline_reason": decline_data.decline_reason,
            "declined_by": current_user.full_name
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    # Auto-update linked model version statuses
    update_version_statuses_for_validation(
        db, validation_request, "CANCELLED", current_user
    )

    db.commit()
    db.refresh(validation_request)
    return validation_request


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_validation_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a validation request (Admin only)."""
    check_admin(current_user)

    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    # Create audit log before deletion
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"request_id": request_id},
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.delete(validation_request)
    db.commit()


# ==================== ASSIGNMENT ENDPOINTS ====================

@router.post("/requests/{request_id}/assignments", response_model=ValidationAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    request_id: int,
    assignment_data: ValidationAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a validator to a validation request."""
    check_validator_or_admin(current_user)

    # Verify request exists
    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    # Verify validator user exists
    validator = db.query(User).filter(
        User.user_id == assignment_data.validator_id).first()
    if not validator:
        raise HTTPException(status_code=404, detail="Validator user not found")

    # Check validator independence for all models
    model_ids = [m.model_id for m in validation_request.models]
    if not check_validator_independence(db, model_ids, assignment_data.validator_id):
        raise HTTPException(
            status_code=400,
            detail="Validator cannot be the model owner or developer of any of the models (independence requirement)"
        )

    # Require independence attestation
    if not assignment_data.independence_attestation:
        raise HTTPException(
            status_code=400,
            detail="Independence attestation is required to assign a validator"
        )

    # Check if already assigned
    existing = db.query(ValidationAssignment).filter(
        ValidationAssignment.request_id == request_id,
        ValidationAssignment.validator_id == assignment_data.validator_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Validator already assigned to this request")

    # If this is primary, demote existing primary
    if assignment_data.is_primary:
        db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == request_id,
            ValidationAssignment.is_primary == True
        ).update({"is_primary": False})

    # If this is reviewer, demote existing reviewer
    if assignment_data.is_reviewer:
        db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == request_id,
            ValidationAssignment.is_reviewer == True
        ).update({"is_reviewer": False})

    # Create assignment
    assignment = ValidationAssignment(
        request_id=request_id,
        validator_id=assignment_data.validator_id,
        is_primary=assignment_data.is_primary,
        is_reviewer=assignment_data.is_reviewer,
        assignment_date=date.today(),
        estimated_hours=assignment_data.estimated_hours,
        actual_hours=0.0,
        independence_attestation=assignment_data.independence_attestation,
        created_at=datetime.utcnow()
    )
    db.add(assignment)
    db.flush()

    # Create audit log for assignment
    roles = []
    if assignment_data.is_primary:
        roles.append("Primary")
    if assignment_data.is_reviewer:
        roles.append("Reviewer")
    role_str = " & ".join(roles) if roles else "Supporting"

    audit_log = AuditLog(
        entity_type="ValidationAssignment",
        entity_id=request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "assignment_id": assignment.assignment_id,
            "validator": validator.full_name,
            "role": role_str,
            "estimated_hours": assignment_data.estimated_hours
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    # Auto-transition from INTAKE to PLANNING when first validator is assigned
    if validation_request.current_status and validation_request.current_status.code == "INTAKE":
        # Get PLANNING status
        planning_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Validation Request Status",
            TaxonomyValue.code == "PLANNING"
        ).first()

        if planning_status:
            old_status_id = validation_request.current_status_id
            validation_request.current_status_id = planning_status.value_id
            validation_request.updated_at = datetime.utcnow()

            # Create status history entry
            create_status_history_entry(
                db,
                request_id,
                old_status_id,
                planning_status.value_id,
                current_user.user_id,
                f"Auto-transitioned to Planning when {validator.full_name} was assigned"
            )

            # Create audit log for status change
            status_audit = AuditLog(
                entity_type="ValidationRequest",
                entity_id=request_id,
                action="UPDATE",
                user_id=current_user.user_id,
                changes={
                    "field": "current_status",
                    "old_value": "INTAKE",
                    "new_value": "PLANNING",
                    "reason": "Auto-transitioned when validator assigned"
                },
                timestamp=datetime.utcnow()
            )
            db.add(status_audit)

    db.commit()
    db.refresh(assignment)

    return assignment


@router.get("/assignments/", response_model=List[ValidationAssignmentResponse])
def get_all_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all validator assignments (for dashboard filtering)."""
    check_validator_or_admin(current_user)

    assignments = db.query(ValidationAssignment).options(
        joinedload(ValidationAssignment.validator)
    ).all()

    return assignments


@router.patch("/assignments/{assignment_id}", response_model=ValidationAssignmentResponse)
def update_assignment(
    assignment_id: int,
    update_data: ValidationAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update validator assignment (hours, attestation, primary status)."""
    assignment = db.query(ValidationAssignment).filter(
        ValidationAssignment.assignment_id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check if current user is the primary validator on this request
    is_primary_validator = db.query(ValidationAssignment).filter(
        ValidationAssignment.request_id == assignment.request_id,
        ValidationAssignment.validator_id == current_user.user_id,
        ValidationAssignment.is_primary == True
    ).first() is not None

    # Allow update if: (1) updating own assignment, (2) admin, or (3) primary validator on this request
    if (current_user.user_id != assignment.validator_id and
        current_user.role != "Admin" and
            not is_primary_validator):
        raise HTTPException(
            status_code=403, detail="Only assigned validator or Admin can update assignment")

    update_dict = update_data.model_dump(exclude_unset=True)

    # If setting as primary, demote others
    if update_dict.get("is_primary"):
        db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == assignment.request_id,
            ValidationAssignment.assignment_id != assignment_id,
            ValidationAssignment.is_primary == True
        ).update({"is_primary": False})

    # If setting as reviewer, demote others
    if update_dict.get("is_reviewer"):
        db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == assignment.request_id,
            ValidationAssignment.assignment_id != assignment_id,
            ValidationAssignment.is_reviewer == True
        ).update({"is_reviewer": False})

    # Track changes for audit
    changes = {}
    for field, value in update_dict.items():
        old_value = getattr(assignment, field)
        if old_value != value:
            setattr(assignment, field, value)
            changes[field] = {"old": str(old_value), "new": str(value)}

    if changes:
        # Create audit log for assignment update
        audit_log = AuditLog(
            entity_type="ValidationAssignment",
            entity_id=assignment.request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes={
                "assignment_id": assignment_id,
                "validator": assignment.validator.full_name,
                **changes
            },
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)

    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    new_primary_id: Optional[int] = Query(
        None, description="New primary validator ID (required when removing primary with multiple remaining validators)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a validator assignment."""
    check_validator_or_admin(current_user)

    assignment = db.query(ValidationAssignment).options(
        joinedload(ValidationAssignment.validator)
    ).filter(
        ValidationAssignment.assignment_id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check how many validators will remain
    total_validators = db.query(ValidationAssignment).filter(
        ValidationAssignment.request_id == assignment.request_id
    ).count()

    if total_validators <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove the last validator. Assign another validator before removing this one."
        )

    # If removing primary validator, handle succession
    if assignment.is_primary:
        remaining_validators = db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == assignment.request_id,
            ValidationAssignment.assignment_id != assignment_id
        ).all()

        if len(remaining_validators) == 1:
            # Auto-promote the only remaining validator to primary
            remaining_validators[0].is_primary = True
            audit_log_promotion = AuditLog(
                entity_type="ValidationAssignment",
                entity_id=assignment.request_id,
                action="UPDATE",
                user_id=current_user.user_id,
                changes={
                    "assignment_id": remaining_validators[0].assignment_id,
                    "validator": remaining_validators[0].validator.full_name,
                    "is_primary": {"old": "False", "new": "True"},
                    "reason": "Auto-promoted when previous primary was removed"
                },
                timestamp=datetime.utcnow()
            )
            db.add(audit_log_promotion)
        elif len(remaining_validators) > 1:
            # Multiple validators remain - require explicit new primary selection
            if not new_primary_id:
                raise HTTPException(
                    status_code=400,
                    detail="Multiple validators remain. Please specify which validator should become the new primary."
                )

            # Find and promote the new primary
            new_primary = next(
                (v for v in remaining_validators if v.validator_id == new_primary_id), None)
            if not new_primary:
                raise HTTPException(
                    status_code=400,
                    detail="Selected new primary validator not found in remaining validators"
                )

            new_primary.is_primary = True
            audit_log_promotion = AuditLog(
                entity_type="ValidationAssignment",
                entity_id=assignment.request_id,
                action="UPDATE",
                user_id=current_user.user_id,
                changes={
                    "assignment_id": new_primary.assignment_id,
                    "validator": new_primary.validator.full_name,
                    "is_primary": {"old": "False", "new": "True"},
                    "reason": "Promoted to primary when previous primary was removed"
                },
                timestamp=datetime.utcnow()
            )
            db.add(audit_log_promotion)

    # Create audit log before deletion
    roles = []
    if assignment.is_primary:
        roles.append("Primary")
    if assignment.is_reviewer:
        roles.append("Reviewer")
    role_str = " & ".join(roles) if roles else "Supporting"

    audit_log = AuditLog(
        entity_type="ValidationAssignment",
        entity_id=assignment.request_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "assignment_id": assignment_id,
            "validator": assignment.validator.full_name,
            "role": role_str
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.delete(assignment)
    db.commit()


@router.post("/assignments/{assignment_id}/sign-off", response_model=ValidationAssignmentResponse)
def reviewer_sign_off(
    assignment_id: int,
    sign_off_data: ReviewerSignOffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reviewer signs off on validation work for quality assurance."""
    assignment = db.query(ValidationAssignment).options(
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.current_status)
    ).filter(
        ValidationAssignment.assignment_id == assignment_id
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Only the assigned reviewer can sign off
    if not assignment.is_reviewer:
        raise HTTPException(
            status_code=400, detail="This assignment is not a reviewer role")

    if current_user.user_id != assignment.validator_id:
        raise HTTPException(
            status_code=403, detail="Only the assigned reviewer can sign off")

    # Check if already signed off
    if assignment.reviewer_signed_off:
        raise HTTPException(
            status_code=400, detail="Reviewer has already signed off")

    # Verify the request has an outcome (reviewer should review the outcome before signing off)
    request = assignment.request
    if not request.outcome:
        raise HTTPException(
            status_code=400,
            detail="Cannot sign off before outcome is created"
        )

    # Perform sign-off
    assignment.reviewer_signed_off = True
    assignment.reviewer_signed_off_at = datetime.utcnow()
    assignment.reviewer_sign_off_comments = sign_off_data.comments

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationAssignment",
        entity_id=assignment.request_id,
        action="REVIEWER_SIGN_OFF",
        user_id=current_user.user_id,
        changes={
            "assignment_id": assignment_id,
            "reviewer": current_user.full_name,
            "comments": sign_off_data.comments
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/send-back", response_model=ValidationRequestResponse)
def reviewer_send_back(
    assignment_id: int,
    send_back_data: ReviewerSignOffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reviewer sends validation back to In Progress with comments for revisions."""
    assignment = db.query(ValidationAssignment).options(
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.current_status),
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.models),
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.requestor),
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.validation_type),
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.priority),
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.regions),
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.validation_plan)
    ).filter(
        ValidationAssignment.assignment_id == assignment_id
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Only the assigned reviewer can send back
    if not assignment.is_reviewer:
        raise HTTPException(
            status_code=400, detail="This assignment is not a reviewer role")

    if current_user.user_id != assignment.validator_id:
        raise HTTPException(
            status_code=403, detail="Only the assigned reviewer can send back")

    request = assignment.request

    # Verify request is in Review status
    current_status_code = request.current_status.code if request.current_status else None
    if current_status_code != "REVIEW":
        raise HTTPException(
            status_code=400,
            detail="Can only send back validations that are in Review status"
        )

    # Get In Progress status
    in_progress_status = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code == "IN_PROGRESS"
    ).first()

    if not in_progress_status:
        raise HTTPException(status_code=500, detail="In Progress status not found in taxonomy")

    # Update validation request status to In Progress
    old_status_id = request.current_status_id
    request.current_status_id = in_progress_status.value_id
    request.updated_at = datetime.utcnow()

    # Record status history with reviewer comments
    change_reason = f"Sent back by reviewer {current_user.full_name}"
    if send_back_data.comments:
        change_reason += f": {send_back_data.comments}"

    create_status_history_entry(
        db, request.request_id, old_status_id, in_progress_status.value_id,
        current_user.user_id, change_reason
    )

    # Reset reviewer sign-off if it was set
    if assignment.reviewer_signed_off:
        assignment.reviewer_signed_off = False
        assignment.reviewer_signed_off_at = None

    # Store send-back comments
    assignment.reviewer_sign_off_comments = send_back_data.comments

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request.request_id,
        action="REVIEWER_SEND_BACK",
        user_id=current_user.user_id,
        changes={
            "assignment_id": assignment_id,
            "reviewer": current_user.full_name,
            "comments": send_back_data.comments,
            "old_status": "Review",
            "new_status": "In Progress"
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(request)
    return request


# ==================== OUTCOME ENDPOINTS ====================

@router.post("/requests/{request_id}/outcome", response_model=ValidationOutcomeResponse, status_code=status.HTTP_201_CREATED)
def create_outcome(
    request_id: int,
    outcome_data: ValidationOutcomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create validation outcome (only after work is complete)."""
    check_validator_or_admin(current_user)

    # Verify request exists
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.outcome)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    # Check if outcome already exists
    if validation_request.outcome:
        raise HTTPException(
            status_code=400, detail="Outcome already exists for this request")

    # Verify status is In Progress or later (must have started work)
    status_code = validation_request.current_status.code if validation_request.current_status else None
    if status_code not in ["IN_PROGRESS", "REVIEW", "PENDING_APPROVAL", "APPROVED"]:
        raise HTTPException(
            status_code=400,
            detail="Outcome can only be created after work has begun (In Progress or later)"
        )

    # Verify overall rating exists
    rating = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == outcome_data.overall_rating_id
    ).first()
    if not rating:
        raise HTTPException(status_code=404, detail="Overall rating not found")

    # Create outcome
    outcome = ValidationOutcome(
        request_id=request_id,
        overall_rating_id=outcome_data.overall_rating_id,
        executive_summary=outcome_data.executive_summary,
        recommended_review_frequency=outcome_data.recommended_review_frequency,
        effective_date=outcome_data.effective_date,
        expiration_date=outcome_data.expiration_date,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(outcome)

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationOutcome",
        entity_id=request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "overall_rating": rating.label,
            "recommended_review_frequency": outcome_data.recommended_review_frequency
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(outcome)
    return outcome


@router.patch("/outcomes/{outcome_id}", response_model=ValidationOutcomeResponse)
def update_outcome(
    outcome_id: int,
    update_data: ValidationOutcomeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update validation outcome."""
    check_validator_or_admin(current_user)

    outcome = db.query(ValidationOutcome).filter(
        ValidationOutcome.outcome_id == outcome_id
    ).first()
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")

    # Check if request is in approved status (locked)
    request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == outcome.request_id
    ).first()
    if request and request.current_status and request.current_status.code == "APPROVED":
        raise HTTPException(
            status_code=400, detail="Cannot modify outcome of approved validation")

    update_dict = update_data.model_dump(exclude_unset=True)

    # Track changes for audit
    changes = {}
    for field, value in update_dict.items():
        old_value = getattr(outcome, field)
        if old_value != value:
            setattr(outcome, field, value)
            # For rating, fetch the label
            if field == 'overall_rating_id' and value:
                rating = db.query(TaxonomyValue).filter(
                    TaxonomyValue.value_id == value).first()
                changes['overall_rating'] = rating.label if rating else str(
                    value)
            else:
                changes[field] = value

    outcome.updated_at = datetime.utcnow()

    # Create audit log if changes were made
    if changes:
        audit_log = AuditLog(
            entity_type="ValidationOutcome",
            entity_id=outcome.request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes,
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)

    db.commit()
    db.refresh(outcome)
    return outcome


# ==================== REVIEW OUTCOME ENDPOINTS ====================

@router.post("/requests/{request_id}/review-outcome", response_model=ValidationReviewOutcomeResponse, status_code=status.HTTP_201_CREATED)
def create_review_outcome(
    request_id: int,
    review_data: ValidationReviewOutcomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create review outcome (only by assigned reviewer)."""
    check_validator_or_admin(current_user)

    # Verify request exists
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.review_outcome),
        joinedload(ValidationRequest.outcome),
        joinedload(ValidationRequest.assignments)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    # Check if review outcome already exists
    if validation_request.review_outcome:
        raise HTTPException(
            status_code=400, detail="Review outcome already exists for this request")

    # Verify status is REVIEW
    status_code = validation_request.current_status.code if validation_request.current_status else None
    if status_code != "REVIEW":
        raise HTTPException(
            status_code=400,
            detail="Review outcome can only be created when status is Review"
        )

    # Verify validation outcome exists
    if not validation_request.outcome:
        raise HTTPException(
            status_code=400, detail="Validation outcome must exist before creating review outcome")

    # Verify current user is assigned as reviewer
    is_reviewer = any(
        a.validator_id == current_user.user_id and a.is_reviewer for a in validation_request.assignments)
    if not is_reviewer:
        raise HTTPException(
            status_code=403, detail="Only the assigned reviewer can create review outcome")

    # Validate decision
    if review_data.decision not in ["AGREE", "SEND_BACK"]:
        raise HTTPException(
            status_code=400, detail="Decision must be 'AGREE' or 'SEND_BACK'")

    # Create review outcome
    review_outcome = ValidationReviewOutcome(
        request_id=request_id,
        reviewer_id=current_user.user_id,
        decision=review_data.decision,
        comments=review_data.comments,
        agrees_with_rating=review_data.agrees_with_rating,
        review_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(review_outcome)

    # Update status based on decision
    if review_data.decision == "AGREE":
        # Move to Pending Approval
        pending_approval_status = get_taxonomy_value_by_code(
            db, "Validation Request Status", "PENDING_APPROVAL")
        old_status_id = validation_request.current_status_id
        validation_request.current_status_id = pending_approval_status.value_id
        validation_request.updated_at = datetime.utcnow()

        # Create status history
        create_status_history_entry(
            db, request_id, old_status_id, pending_approval_status.value_id,
            current_user.user_id, f"Reviewer agreed with validation outcome"
        )
    else:  # SEND_BACK
        # Move back to In Progress
        in_progress_status = get_taxonomy_value_by_code(
            db, "Validation Request Status", "IN_PROGRESS")
        old_status_id = validation_request.current_status_id
        validation_request.current_status_id = in_progress_status.value_id
        validation_request.updated_at = datetime.utcnow()

        # Create status history
        create_status_history_entry(
            db, request_id, old_status_id, in_progress_status.value_id,
            current_user.user_id, f"Reviewer sent back for revision: {review_data.comments or 'No comments'}"
        )

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationReviewOutcome",
        entity_id=request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "decision": review_data.decision,
            "agrees_with_rating": review_data.agrees_with_rating,
            "comments": review_data.comments
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(review_outcome)
    return review_outcome


@router.patch("/review-outcomes/{review_outcome_id}", response_model=ValidationReviewOutcomeResponse)
def update_review_outcome(
    review_outcome_id: int,
    update_data: ValidationReviewOutcomeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update review outcome (only by the reviewer who created it)."""
    check_validator_or_admin(current_user)

    review_outcome = db.query(ValidationReviewOutcome).filter(
        ValidationReviewOutcome.review_outcome_id == review_outcome_id
    ).first()
    if not review_outcome:
        raise HTTPException(status_code=404, detail="Review outcome not found")

    # Verify current user is the reviewer who created it
    if review_outcome.reviewer_id != current_user.user_id:
        raise HTTPException(
            status_code=403, detail="Only the reviewer who created this outcome can update it")

    # Check if request is in approved status (locked)
    request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == review_outcome.request_id
    ).first()
    if request and request.current_status and request.current_status.code == "APPROVED":
        raise HTTPException(
            status_code=400, detail="Cannot modify review outcome of approved validation")

    update_dict = update_data.model_dump(exclude_unset=True)

    # Track changes for audit
    changes = {}
    for field, value in update_dict.items():
        old_value = getattr(review_outcome, field)
        if old_value != value:
            setattr(review_outcome, field, value)
            changes[field] = value

    review_outcome.updated_at = datetime.utcnow()

    # Create audit log if changes were made
    if changes:
        audit_log = AuditLog(
            entity_type="ValidationReviewOutcome",
            entity_id=review_outcome.request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes,
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)

    db.commit()
    db.refresh(review_outcome)
    return review_outcome


# ==================== APPROVAL ENDPOINTS ====================

@router.post("/requests/{request_id}/approvals", response_model=ValidationApprovalResponse, status_code=status.HTTP_201_CREATED)
def create_approval_requirement(
    request_id: int,
    approval_data: ValidationApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add an approval requirement to a validation request."""
    check_admin(current_user)

    # Verify request exists
    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    # Verify approver user exists
    approver = db.query(User).filter(
        User.user_id == approval_data.approver_id).first()
    if not approver:
        raise HTTPException(status_code=404, detail="Approver user not found")

    # Validate role against taxonomy and normalize region fields
    validate_approver_role_or_raise(db, approval_data.approver_role)
    approval_type, region_id, represented_region_id = normalize_region_fields_for_approval(
        approval_data.approval_type,
        approval_data.region_id,
        approval_data.represented_region_id
    )

    # Create approval record
    approval = ValidationApproval(
        request_id=request_id,
        approver_id=approval_data.approver_id,
        approver_role=approval_data.approver_role,
        is_required=approval_data.is_required,
        approval_type=approval_type,
        region_id=region_id,
        approval_status="Pending",
        represented_region_id=represented_region_id,
        created_at=datetime.utcnow()
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


@router.patch("/approvals/{approval_id}", response_model=ValidationApprovalResponse)
def submit_approval(
    approval_id: int,
    update_data: ValidationApprovalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit approval or rejection for a validation request."""
    from sqlalchemy.orm import joinedload
    approval = db.query(ValidationApproval).options(
        joinedload(ValidationApproval.approver)
    ).filter(
        ValidationApproval.approval_id == approval_id
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    # Only the designated approver or Admin can update approval
    if current_user.user_id != approval.approver_id and current_user.role != "Admin":
        raise HTTPException(
            status_code=403, detail="Only the designated approver or Admin can update this approval")

    approval.approval_status = update_data.approval_status
    approval.comments = update_data.comments

    if update_data.approval_status in ["Approved", "Rejected"]:
        approval.approved_at = datetime.utcnow()
    elif update_data.approval_status == "Pending":
        # Clear approved_at when withdrawing approval
        approval.approved_at = None

    # Create audit log with appropriate action type
    if update_data.approval_status == "Pending":
        action = "APPROVAL_WITHDRAWN"
    else:
        action = "APPROVAL_SUBMITTED"

    # Check if this is a proxy approval (admin approving on behalf)
    is_proxy_approval = current_user.role == "Admin" and current_user.user_id != approval.approver_id

    changes_dict = {
        "approval_id": approval_id,
        "status": update_data.approval_status,
        "approver_role": approval.approver_role
    }

    if is_proxy_approval:
        changes_dict["proxy_approval"] = True
        changes_dict["approved_by_admin"] = current_user.full_name
        changes_dict["on_behalf_of"] = approval.approver.full_name

    audit_log = AuditLog(
        entity_type="ValidationApproval",
        entity_id=approval.request_id,
        action=action,
        user_id=current_user.user_id,
        changes=changes_dict,
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    # Update validation request completion_date based on approval status
    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == approval.request_id
    ).first()

    if validation_request:
        # Recalculate completion_date based on all approvals
        latest_approval_date = db.query(func.max(ValidationApproval.approved_at)).filter(
            ValidationApproval.request_id == approval.request_id,
            ValidationApproval.approval_status == 'Approved'
        ).scalar()

        # Set completion_date to latest approval date, or None if no approvals
        validation_request.completion_date = latest_approval_date

    db.commit()
    db.refresh(approval)
    # Force load the approver relationship for the response schema
    _ = approval.approver
    return approval


@router.delete("/approvals/{approval_id}/unlink", response_model=ValidationApprovalResponse)
def unlink_regional_approval(
    approval_id: int,
    unlink_data: ValidationApprovalUnlink,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin-only: Unlink a regional approval to unblock a stalled validation."""
    # Admin-only access
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can unlink approvals"
        )

    approval = db.query(ValidationApproval).filter(
        ValidationApproval.approval_id == approval_id
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    # Update approval record
    approval.unlinked_by_id = current_user.user_id
    approval.unlink_reason = unlink_data.unlink_reason
    approval.unlinked_at = datetime.utcnow()
    approval.approval_status = "Removed"
    approval.is_required = False  # No longer required

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationApproval",
        entity_id=approval.request_id,
        action="APPROVAL_UNLINKED",
        user_id=current_user.user_id,
        changes={
            "approval_id": approval_id,
            "approver_role": approval.approver_role,
            "unlink_reason": unlink_data.unlink_reason,
            "unlinked_by": current_user.full_name
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(approval)
    return approval


# ==================== DASHBOARD / REPORTING ENDPOINTS ====================

@router.get("/dashboard/aging")
def get_aging_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validation requests aging report by status."""
    check_admin(current_user)

    # Get all non-terminal requests
    requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.status_history)  # For days_in_status calculation
    ).all()

    aging_data = []
    for req in requests:
        if req.current_status and req.current_status.code not in ["APPROVED", "CANCELLED"]:
            days_in_status = calculate_days_in_status(req)
            model_names = [
                m.model_name for m in req.models] if req.models else []
            aging_data.append({
                "request_id": req.request_id,
                "model_names": model_names,
                "current_status": req.current_status.label if req.current_status else "Unknown",
                "priority": req.priority.label if req.priority else "Unknown",
                "days_in_status": days_in_status,
                "target_completion_date": req.target_completion_date.isoformat() if req.target_completion_date else None,
                "is_overdue": req.target_completion_date < date.today() if req.target_completion_date else False
            })

    return sorted(aging_data, key=lambda x: x["days_in_status"], reverse=True)


@router.get("/dashboard/workload")
def get_workload_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validator workload report."""
    check_admin(current_user)

    # Get validators and their assignments
    validators = db.query(User).filter(
        User.role.in_(["Validator", "Admin"])).all()

    workload_data = []
    for validator in validators:
        active_assignments = db.query(ValidationAssignment).join(
            ValidationRequest
        ).join(
            TaxonomyValue,
            ValidationRequest.current_status_id == TaxonomyValue.value_id
        ).filter(
            ValidationAssignment.validator_id == validator.user_id,
            TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"])
        ).count()

        total_estimated_hours = db.query(ValidationAssignment).filter(
            ValidationAssignment.validator_id == validator.user_id
        ).with_entities(
            db.query(ValidationAssignment.estimated_hours).filter(
                ValidationAssignment.validator_id == validator.user_id
            ).as_scalar()
        )

        workload_data.append({
            "validator_id": validator.user_id,
            "validator_name": validator.full_name,
            "active_assignments": active_assignments,
            "role": validator.role
        })

    return sorted(workload_data, key=lambda x: x["active_assignments"], reverse=True)


@router.get("/validators/{validator_id}/assignments")
def get_validator_assignments(
    validator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all validation assignments for a specific validator."""
    # Verify validator exists
    validator = db.query(User).filter(User.user_id == validator_id).first()
    if not validator:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all assignments for this validator
    assignments = db.query(ValidationAssignment).options(
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.models),
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.current_status),
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.validation_type),
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.priority)
    ).filter(
        ValidationAssignment.validator_id == validator_id
    ).order_by(ValidationAssignment.created_at.desc()).all()

    result = []
    for assignment in assignments:
        req = assignment.request
        model_ids = [m.model_id for m in req.models] if req.models else []
        model_names = [m.model_name for m in req.models] if req.models else []
        result.append({
            "assignment_id": assignment.assignment_id,
            "request_id": req.request_id,
            "model_ids": model_ids,
            "model_names": model_names,
            "validation_type": req.validation_type.label if req.validation_type else "Unknown",
            "priority": req.priority.label if req.priority else "Unknown",
            "current_status": req.current_status.label if req.current_status else "Unknown",
            "is_primary": assignment.is_primary,
            "is_reviewer": assignment.is_reviewer,
            "assignment_date": assignment.assignment_date.isoformat() if assignment.assignment_date else None,
            "estimated_hours": assignment.estimated_hours,
            "actual_hours": assignment.actual_hours,
            "reviewer_signed_off": assignment.reviewer_signed_off,
            "target_completion_date": req.target_completion_date.isoformat() if req.target_completion_date else None,
            "created_at": assignment.created_at.isoformat() if assignment.created_at else None
        })

    return result


@router.get("/dashboard/sla-violations")
def get_sla_violations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get validation team SLA violations (Admin only).

    Shows validations where time from submission_received_date to now (or completion)
    exceeds the lead time specified in the validation policy for the model's risk tier.
    """
    check_admin(current_user)

    from app.models.validation import ValidationPolicy

    # Pre-load all validation policies (once, not in loop)
    policies = db.query(ValidationPolicy).all()
    policy_lookup = {p.risk_tier_id: p for p in policies}

    # Get all active (non-terminal) validation requests with submission received
    requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.priority)
    ).filter(
        ValidationRequest.submission_received_date.isnot(None),
        ValidationRequest.current_status.has(
            TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"])
        )
    ).all()

    violations = []
    now = datetime.utcnow()

    for req in requests:
        if not req.models:
            continue

        # Use first model's risk tier to determine policy
        model = req.models[0]
        if not model.risk_tier:
            continue

        # Lookup validation policy from pre-loaded dict
        policy = policy_lookup.get(model.risk_tier.value_id)

        if not policy:
            continue

        lead_time_days = policy.model_change_lead_time_days

        # Calculate days since submission
        days_since_submission = (now.date() - req.submission_received_date).days

        # Check if lead time has been exceeded
        if days_since_submission > lead_time_days:
            model_name = model.model_name
            days_overdue = days_since_submission - lead_time_days

            # Calculate severity based on how overdue
            if days_overdue > 30:
                severity = "critical"
            elif days_overdue > 14:
                severity = "high"
            else:
                severity = "medium"

            violations.append({
                "request_id": req.request_id,
                "model_name": model_name,
                "violation_type": "Validation Lead Time Exceeded",
                "sla_days": lead_time_days,
                "actual_days": days_since_submission,
                "days_overdue": days_overdue,
                "current_status": req.current_status.label if req.current_status else "Unknown",
                "priority": req.priority.label if req.priority else "Unknown",
                "severity": severity,
                "timestamp": req.submission_received_date.isoformat()
            })

    # Sort by days overdue (most overdue first)
    return sorted(violations, key=lambda x: x["days_overdue"], reverse=True)


@router.get("/dashboard/out-of-order")
def get_out_of_order_validations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validation requests where target completion date exceeds model change production date (Admin only)."""
    check_admin(current_user)

    from app.models.model_version import ModelVersion
    from collections import defaultdict

    # Pre-load all model versions with production dates (once, not in loop)
    all_versions = db.query(ModelVersion).filter(
        ModelVersion.validation_request_id.isnot(None),
        ModelVersion.production_date.isnot(None)
    ).all()

    # Group versions by validation_request_id for fast lookup
    versions_by_request = defaultdict(list)
    for version in all_versions:
        versions_by_request[version.validation_request_id].append(version)

    # Get all validation requests with linked model versions
    requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.priority)
    ).filter(
        ValidationRequest.current_status.has(
            TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"]))
    ).all()

    out_of_order = []

    for req in requests:
        model_names = [m.model_name for m in req.models] if req.models else []
        # Get model versions from pre-loaded dict
        versions = versions_by_request.get(req.request_id, [])

        for version in versions:
            # Check if target completion date is after production date
            target_date = req.target_completion_date
            prod_date = version.production_date

            if target_date > prod_date:
                days_gap = (target_date - prod_date).days
                severity = "critical" if days_gap > 30 else "high" if days_gap > 14 else "medium"

                out_of_order.append({
                    "request_id": req.request_id,
                    "model_names": model_names,
                    "version_number": version.version_number,
                    "validation_type": req.validation_type.label if req.validation_type else "Unknown",
                    "target_completion_date": target_date.isoformat(),
                    "production_date": prod_date.isoformat(),
                    "days_gap": days_gap,
                    "current_status": req.current_status.label if req.current_status else "Unknown",
                    "priority": req.priority.label if req.priority else "Unknown",
                    "severity": severity,
                    "is_interim": req.validation_type.code == "INTERIM" if req.validation_type else False
                })

    # Sort by days gap (worst first)
    return sorted(out_of_order, key=lambda x: x["days_gap"], reverse=True)


@router.get("/dashboard/pending-assignments")
def get_pending_validator_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validation requests in Intake status awaiting primary validator assignment (Admin only)."""
    check_admin(current_user)

    # Get INTAKE status
    intake_status = get_taxonomy_value_by_code(
        db, "Validation Request Status", "INTAKE")

    # Get all validation requests in INTAKE status
    requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models).joinedload(Model.model_regions),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.assignments).joinedload(
            ValidationAssignment.validator)
    ).filter(
        ValidationRequest.current_status_id == intake_status.value_id
    ).all()

    pending = []
    now = datetime.utcnow()

    for req in requests:
        # Check if there's a primary validator assigned
        primary_validator = next(
            (a for a in req.assignments if a.is_primary), None)

        # Only include if no primary validator assigned
        if not primary_validator:
            days_pending = (now - req.created_at).days

            # Determine severity based on how long it's been pending
            if days_pending > 7:
                severity = "critical"
            elif days_pending > 3:
                severity = "high"
            else:
                severity = "medium"

            model_ids = [m.model_id for m in req.models] if req.models else []
            model_names = [
                m.model_name for m in req.models] if req.models else []

            # Determine region display based on governance, deployment, and validation scope
            all_region_ids = set()
            governance_region_ids = set()

            if model_ids:
                models = db.query(Model).filter(
                    Model.model_id.in_(model_ids)).all()
                for model in models:
                    # Collect governance regions
                    if model.wholly_owned_region_id is not None:
                        all_region_ids.add(model.wholly_owned_region_id)
                        governance_region_ids.add(model.wholly_owned_region_id)
                    # Collect deployment regions
                    for model_region in model.model_regions:
                        all_region_ids.add(model_region.region_id)

            # Collect validation request scope regions
            for region in req.regions:
                all_region_ids.add(region.region_id)

            # Check if pure single-region scenario
            wholly_owned_region_id = None
            is_single_region = False

            if len(governance_region_ids) == 1:
                wholly_owned_region_id = list(governance_region_ids)[0]
                if all_region_ids == {wholly_owned_region_id}:
                    is_single_region = True

            # Display region(s)
            if is_single_region and wholly_owned_region_id is not None:
                # Pure single-region - only show that region
                region = db.query(Region).filter(
                    Region.region_id == wholly_owned_region_id).first()
                region_display = region.name if region else f"Region {wholly_owned_region_id}"
            elif all_region_ids:
                # Multi-region - show "Global + [Regions]"
                regions_list = db.query(Region).filter(
                    Region.region_id.in_(all_region_ids)).all()
                region_names = [r.name for r in regions_list]
                region_display = "Global + " + ", ".join(region_names)
            else:
                # No regional scope - just show "Global"
                region_display = "Global"

            pending.append({
                "request_id": req.request_id,
                "model_ids": model_ids,
                "model_names": model_names,
                "requestor_name": req.requestor.full_name if req.requestor else "Unknown",
                "validation_type": req.validation_type.label if req.validation_type else "Unknown",
                "priority": req.priority.label if req.priority else "Unknown",
                "region": region_display,
                "request_date": req.request_date.isoformat(),
                "target_completion_date": req.target_completion_date.isoformat() if req.target_completion_date else None,
                "days_pending": days_pending,
                "severity": severity
            })

    # Sort by days pending (longest pending first)
    return sorted(pending, key=lambda x: x["days_pending"], reverse=True)


# ==================== REVALIDATION LIFECYCLE ENDPOINTS ====================

@router.patch("/requests/{request_id}/submit-documentation")
def submit_documentation(
    request_id: int,
    submission_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark documentation as received for a revalidation request.
    Sets submission_received_date and creates audit log.

    Args:
        request_id: Validation request ID
        submission_date: Date documentation was received (defaults to today)
    """
    # Get validation request
    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()

    if not validation_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Check if this is a periodic revalidation
    if not validation_request.is_periodic_revalidation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only mark submission for periodic revalidations (COMPREHENSIVE or ANNUAL)"
        )

    # Check if submission already received
    if validation_request.submission_received_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submission already received on {validation_request.submission_received_date}"
        )

    # Set submission date (default to today)
    received_date = submission_date if submission_date else date.today()

    old_value = None
    validation_request.submission_received_date = received_date

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="SUBMIT_DOCUMENTATION",
        user_id=current_user.user_id,
        changes={
            "submission_received_date": received_date.isoformat(),
            "submission_status": validation_request.submission_status,
            "validation_team_sla_due_date": validation_request.validation_team_sla_due_date.isoformat() if validation_request.validation_team_sla_due_date else None
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    db.refresh(validation_request)

    return {
        "request_id": request_id,
        "submission_received_date": validation_request.submission_received_date,
        "submission_status": validation_request.submission_status,
        "validation_team_sla_due_date": validation_request.validation_team_sla_due_date,
        "days_until_team_sla_due": validation_request.days_until_team_sla_due,
        "message": "Documentation submission recorded successfully"
    }


@router.get("/dashboard/overdue-submissions")
def get_overdue_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get models with pending or overdue documentation submissions.
    Includes:
    1. Models past submission due date but still in grace period
    2. Models past grace period (fully overdue)
    Uses dynamic calculation from computed properties.
    Admin only.
    """
    check_admin(current_user)

    today = date.today()

    # Find active revalidation requests without submissions
    pending_requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model
        ).joinedload(Model.owner),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model
        ).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.validation_type)
    ).filter(
        ValidationRequest.validation_type.has(TaxonomyValue.code.in_(["COMPREHENSIVE", "ANNUAL"])),
        ValidationRequest.submission_received_date.is_(None),
        ValidationRequest.current_status.has(TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
    ).all()

    results = []
    for req in pending_requests:
        # Check if EITHER past submission due date OR past grace period
        is_past_due = req.submission_due_date and today > req.submission_due_date
        is_past_grace = req.submission_grace_period_end and today > req.submission_grace_period_end

        if is_past_due or is_past_grace:
            # Get model info from first model in request
            if req.model_versions_assoc and len(req.model_versions_assoc) > 0:
                model_assoc = req.model_versions_assoc[0]
                model = model_assoc.model

                # Calculate days overdue and urgency
                if is_past_grace:
                    days_overdue = (today - req.submission_grace_period_end).days
                    urgency = "overdue"  # Past grace period
                else:
                    days_overdue = (today - req.submission_due_date).days
                    urgency = "in_grace_period"  # Past due but in grace

                results.append({
                    "request_id": req.request_id,
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "model_owner": model.owner.full_name if model.owner else "Unknown",
                    "risk_tier": model.risk_tier.label if model.risk_tier else None,
                    "submission_due_date": req.submission_due_date,
                    "grace_period_end": req.submission_grace_period_end,
                    "days_overdue": days_overdue,
                    "urgency": urgency,
                    "validation_due_date": req.model_validation_due_date,
                    "submission_status": req.submission_status,
                    "current_status": req.current_status.label if req.current_status else "Unknown"
                })

    # Sort by urgency (overdue first) then by days overdue
    return sorted(results, key=lambda x: (0 if x["urgency"] == "overdue" else 1, -x["days_overdue"]))


@router.get("/dashboard/overdue-validations")
def get_overdue_validations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get models with overdue validations (past model_validation_due_date).
    This is SEPARATE from overdue submissions - no overlap.
    Uses dynamic calculation from computed properties.
    Admin only.
    """
    check_admin(current_user)

    today = date.today()

    # Find active revalidation requests
    active_requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model
        ).joinedload(Model.owner),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model
        ).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.validation_type)
    ).filter(
        ValidationRequest.validation_type.has(TaxonomyValue.code.in_(["COMPREHENSIVE", "ANNUAL"])),
        ValidationRequest.current_status.has(TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"]))
    ).all()

    results = []
    for req in active_requests:
        # Check ONLY if validation is overdue (past model_validation_due_date)
        # Submission overdue is handled separately by /dashboard/overdue-submissions
        if req.model_validation_due_date and today > req.model_validation_due_date:
            # Get model info from first model in request
            if req.model_versions_assoc and len(req.model_versions_assoc) > 0:
                model_assoc = req.model_versions_assoc[0]
                model = model_assoc.model

                days_overdue = (today - req.model_validation_due_date).days

                results.append({
                    "request_id": req.request_id,
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "model_owner": model.owner.full_name if model.owner else "Unknown",
                    "risk_tier": model.risk_tier.label if model.risk_tier else None,
                    "submission_due_date": req.submission_due_date,
                    "submission_received_date": req.submission_received_date,
                    "model_validation_due_date": req.model_validation_due_date,
                    "days_overdue": days_overdue,
                    "model_compliance_status": req.model_compliance_status,
                    "current_status": req.current_status.label if req.current_status else "Unknown"
                })

    # Sort by days overdue (most overdue first)
    return sorted(results, key=lambda x: x["days_overdue"], reverse=True)


@router.get("/dashboard/upcoming-revalidations")
def get_upcoming_revalidations(
    days_ahead: int = Query(90, description="Look ahead this many days for upcoming revalidations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get models with revalidations due in next N days.
    Uses dynamic calculation - no stored schedule table.
    Admin only.
    """
    check_admin(current_user)

    # Use helper function to calculate all revalidations
    upcoming = get_models_needing_revalidation(
        db=db,
        days_ahead=days_ahead,
        include_overdue=False  # Only upcoming, not overdue
    )

    return upcoming


@router.get("/my-pending-submissions")
def get_my_pending_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pending submission requests for models accessible by the current user.

    For Admin users: Shows all pending submissions (system-wide oversight)
    For non-Admin users: Shows revalidation requests for models where user is:
    - Owner
    - Developer
    - Delegate

    Only returns submissions that are overdue or due within the next 90 days.
    """
    from app.models.model_delegate import ModelDelegate

    today = date.today()
    ninety_days_out = today + timedelta(days=90)

    # Find revalidation requests for models accessible by current user
    # that are awaiting submission
    query = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).join(
        Model
    )

    # Admin users see all pending submissions; non-admin users see only their models
    if current_user.role != 'Admin':
        query = query.filter(
            or_(
                Model.owner_id == current_user.user_id,
                Model.developer_id == current_user.user_id,
                Model.delegates.any(
                    (ModelDelegate.user_id == current_user.user_id) &
                    (ModelDelegate.revoked_at == None)
                )
            )
        )

    # Apply common filters
    pending_requests = query.filter(
        ValidationRequest.validation_type.has(TaxonomyValue.code.in_(["COMPREHENSIVE", "ANNUAL"])),
        ValidationRequest.submission_received_date.is_(None),
        ValidationRequest.current_status.has(TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
    ).all()

    results = []
    for req in pending_requests:
        # Get model info from first model in request
        if req.model_versions_assoc and len(req.model_versions_assoc) > 0:
            model_assoc = req.model_versions_assoc[0]
            model = model_assoc.model

            # Determine urgency
            if req.submission_due_date:
                days_until_due = (req.submission_due_date - today).days
                if days_until_due < 0:
                    if req.submission_grace_period_end and today > req.submission_grace_period_end:
                        urgency = "overdue"
                    else:
                        urgency = "in_grace_period"
                elif days_until_due <= 30:
                    urgency = "due_soon"
                else:
                    urgency = "upcoming"
            else:
                urgency = "unknown"

            results.append({
                "request_id": req.request_id,
                "model_id": model.model_id,
                "model_name": model.model_name,
                "validation_type": req.validation_type.label if req.validation_type else "Unknown",
                "priority": req.priority.label if req.priority else "Medium",
                "request_date": req.request_date.isoformat() if req.request_date else str(req.created_at.date()),
                "submission_due_date": req.submission_due_date.isoformat() if req.submission_due_date else None,
                "grace_period_end": req.submission_grace_period_end.isoformat() if req.submission_grace_period_end else None,
                "model_validation_due_date": req.model_validation_due_date.isoformat() if req.model_validation_due_date else None,
                "days_until_submission_due": req.days_until_submission_due,
                "days_until_validation_due": req.days_until_model_validation_due,
                "submission_status": req.submission_status,
                "model_compliance_status": req.model_compliance_status,
                "urgency": urgency
            })

    # Filter to only show submissions that are overdue or due within 90 days
    filtered_results = []
    for result in results:
        if result["submission_due_date"]:
            due_date = date.fromisoformat(result["submission_due_date"])
            # Include if overdue or due within 90 days
            if due_date <= ninety_days_out:
                filtered_results.append(result)
        else:
            # Include submissions without a due date (can't determine if outside window)
            filtered_results.append(result)

    # Sort by urgency (overdue first, then by days until due)
    urgency_order = {"overdue": 0, "in_grace_period": 1, "due_soon": 2, "upcoming": 3, "unknown": 4}
    return sorted(filtered_results, key=lambda x: (urgency_order.get(x["urgency"], 4), x["days_until_submission_due"] or 999))


@router.get("/models/{model_id}/revalidation-status")
def get_model_revalidation_status(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get revalidation status for a specific model.
    Returns comprehensive revalidation timeline and status information.
    """
    # Get model
    model = db.query(Model).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    # Use helper function to calculate revalidation status
    return calculate_model_revalidation_status(model, db)


# ==================== VALIDATION PLAN ENDPOINTS ====================

@router.get("/component-definitions", response_model=List[ValidationComponentDefinitionResponse])
def list_validation_component_definitions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all validation component definitions (Figure 3 matrix).
    Returns the master list of validation components with expectations per risk tier.
    """
    components = db.query(ValidationComponentDefinition).filter(
        ValidationComponentDefinition.is_active == True
    ).order_by(ValidationComponentDefinition.sort_order).all()

    return components


@router.get("/component-definitions/{component_id}", response_model=ValidationComponentDefinitionResponse)
def get_validation_component_definition(
    component_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single validation component definition by ID."""
    component = db.query(ValidationComponentDefinition).filter(
        ValidationComponentDefinition.component_id == component_id
    ).first()

    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component definition {component_id} not found"
        )

    return component


@router.patch("/component-definitions/{component_id}", response_model=ValidationComponentDefinitionResponse)
def update_validation_component_definition(
    component_id: int,
    component_data: ValidationComponentDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a validation component definition.

    Admin only. Changes are not retroactive - existing plans are unaffected.
    To make changes effective for new plans, publish a new configuration version.
    """
    check_admin(current_user)

    component = db.query(ValidationComponentDefinition).filter(
        ValidationComponentDefinition.component_id == component_id
    ).first()

    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component definition {component_id} not found"
        )

    # Track changes for audit log
    changes = {}
    update_data = component_data.model_dump(exclude_unset=True)

    for field, new_value in update_data.items():
        old_value = getattr(component, field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}
            setattr(component, field, new_value)

    if changes:
        db.commit()
        db.refresh(component)

        # Audit log
        audit_log = AuditLog(
            entity_type="ValidationComponentDefinition",
            entity_id=component.component_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes,
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)
        db.commit()

    return component


def get_expectation_for_tier(component: ValidationComponentDefinition, risk_tier_code: str) -> str:
    """Helper to get expectation for a given risk tier."""
    tier_mapping = {
        "TIER_1": component.expectation_high,
        "TIER_2": component.expectation_medium,
        "TIER_3": component.expectation_low,
        "TIER_4": component.expectation_very_low,
        # Legacy fallbacks for backwards compatibility
        "HIGH": component.expectation_high,
        "MEDIUM": component.expectation_medium,
        "LOW": component.expectation_low,
        "VERY_LOW": component.expectation_very_low
    }
    return tier_mapping.get(risk_tier_code, "Required")


def calculate_is_deviation(default_expectation: str, planned_treatment: str) -> bool:
    """
    Calculate if a planned treatment is a deviation from the default expectation.

    Deviation cases:
    - Required -> NotPlanned or NotApplicable
    - NotExpected -> Planned
    - IfApplicable -> (no automatic deviation, requires judgment)
    """
    if default_expectation == "Required" and planned_treatment in ["NotPlanned", "NotApplicable"]:
        return True
    if default_expectation == "NotExpected" and planned_treatment == "Planned":
        return True
    return False


def recalculate_plan_expectations_for_model(
    db: Session,
    model_id: int,
    new_risk_tier_code: str
) -> int:
    """
    Recalculate validation plan expectations when a model's risk tier changes.

    This function:
    1. Finds all unlocked validation plans for the given model
    2. Recalculates default_expectation for each component based on new risk tier
    3. Recalculates is_deviation flag
    4. Updates the plans in the database

    Returns the number of plans updated.
    """
    # Find all unlocked validation plans for this model
    # A plan is unlocked if locked_at is NULL
    plans = db.query(ValidationPlan).join(
        ValidationRequest, ValidationPlan.request_id == ValidationRequest.request_id
    ).join(
        ValidationRequestModelVersion, ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequestModelVersion.model_id == model_id,
        ValidationPlan.locked_at == None  # Only unlocked plans
    ).options(
        joinedload(ValidationPlan.components).joinedload(ValidationPlanComponent.component_definition)
    ).all()

    if not plans:
        return 0

    plans_updated = 0

    # Map risk tier codes to expectation field names
    tier_to_field = {
        "HIGH": "expectation_high",
        "MEDIUM": "expectation_medium",
        "LOW": "expectation_low",
        "VERY_LOW": "expectation_very_low"
    }

    expectation_field = tier_to_field.get(new_risk_tier_code, "expectation_medium")

    for plan in plans:
        components_updated = False

        for component in plan.components:
            comp_def = component.component_definition

            # Get new default expectation based on new risk tier
            old_default_expectation = component.default_expectation
            new_default_expectation = getattr(comp_def, expectation_field, "NotExpected")

            if old_default_expectation != new_default_expectation:
                component.default_expectation = new_default_expectation

                # Recalculate is_deviation
                component.is_deviation = calculate_is_deviation(
                    new_default_expectation,
                    component.planned_treatment
                )

                components_updated = True

        if components_updated:
            plans_updated += 1

    if plans_updated > 0:
        db.commit()

    return plans_updated


def validate_plan_compliance(
    db: Session,
    request_id: int,
    require_plan: bool = False,
    required_region_codes: Optional[List[str]] = None
) -> tuple[bool, List[str]]:
    """
    Validate that a validation plan meets compliance requirements before submission.

    Checks:
    1. All components marked as deviation must have rationale
    2. If material_deviation_from_standard is true, must have overall_deviation_rationale
    3. (Optional) Plan existence required when configured per-region

    Returns: (is_valid, list_of_error_messages)
    """
    errors = []

    # Get the validation plan
    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components)
    ).filter(ValidationPlan.request_id == request_id).first()

    if not plan:
        if require_plan:
            regions_list = ", ".join(required_region_codes or [])
            if regions_list:
                errors.append(f"Validation plan is required for regions: {regions_list}")
            else:
                errors.append("Validation plan is required for this validation request")
        return len(errors) == 0, errors

    # Check if material deviation has rationale
    if plan.material_deviation_from_standard:
        if not plan.overall_deviation_rationale or not plan.overall_deviation_rationale.strip():
            errors.append(
                "Material deviation from standard is marked, but no overall deviation rationale provided"
            )

    # Check all component deviations have rationale
    for comp in plan.components:
        if comp.is_deviation:
            if not comp.rationale or not comp.rationale.strip():
                errors.append(
                    f"Component {comp.component_definition.component_code} ({comp.component_definition.component_title}) "
                    f"is marked as deviation but has no rationale"
                )

    return len(errors) == 0, errors


def get_request_region_ids(validation_request: ValidationRequest) -> List[int]:
    """Collect relevant region IDs from a validation request (scope + model governance/deployments)."""
    region_ids = set()

    for region in validation_request.regions or []:
        region_ids.add(region.region_id)

    for model in validation_request.models or []:
        if model.wholly_owned_region_id:
            region_ids.add(model.wholly_owned_region_id)
        for model_region in model.model_regions or []:
            region_ids.add(model_region.region_id)

    return list(region_ids)


def request_requires_validation_plan(db: Session, validation_request: ValidationRequest) -> tuple[bool, List[str]]:
    """
    Determine if a validation plan is mandatory for this request based on region settings.

    Returns (requires_plan, region_codes_requiring_plan)
    """
    region_ids = get_request_region_ids(validation_request)
    if not region_ids:
        return False, []

    regions = db.query(Region).filter(
        Region.region_id.in_(region_ids),
        Region.enforce_validation_plan == True
    ).all()

    if not regions:
        return False, []

    region_codes = [r.code or str(r.region_id) for r in regions]
    return True, region_codes


@router.post("/requests/{request_id}/plan", response_model=ValidationPlanResponse, status_code=status.HTTP_201_CREATED)
def create_validation_plan(
    request_id: int,
    plan_data: ValidationPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a validation plan for a validation request.

    The plan captures which validation components are planned or not planned,
    with rationale for deviations from bank standards.
    """
    check_validator_or_admin(current_user)

    # Get validation request
    request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(ValidationRequestModelVersion.model).joinedload(Model.risk_tier)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Check if plan already exists
    existing_plan = db.query(ValidationPlan).filter(ValidationPlan.request_id == request_id).first()
    if existing_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Validation plan already exists for this request. Use PATCH to update."
        )

    # Get model and risk tier
    if not request.model_versions_assoc or len(request.model_versions_assoc) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Validation request must have at least one model associated"
        )

    # Use most conservative (highest risk) tier among all models in the validation project
    # Risk tier hierarchy: TIER_1 (High) > TIER_2 (Medium) > TIER_3 (Low) > TIER_4 (Very Low)
    tier_hierarchy = {"TIER_1": 1, "TIER_2": 2, "TIER_3": 3, "TIER_4": 4}
    most_conservative_tier = "TIER_2"  # Default to medium
    highest_risk_level = 4  # Start with lowest risk

    for model_version_assoc in request.model_versions_assoc:
        model = model_version_assoc.model
        if model.risk_tier and model.risk_tier.code:
            tier_code = model.risk_tier.code
            risk_level = tier_hierarchy.get(tier_code, 2)
            if risk_level < highest_risk_level:  # Lower number = higher risk
                highest_risk_level = risk_level
                most_conservative_tier = tier_code

    risk_tier_code = most_conservative_tier
    # Get first model for response metadata (model name, etc.)
    first_model = request.model_versions_assoc[0].model

    # Validate material deviation rationale
    if plan_data.material_deviation_from_standard and not plan_data.overall_deviation_rationale:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="overall_deviation_rationale is required when material_deviation_from_standard is true"
        )

    # Create validation plan
    new_plan = ValidationPlan(
        request_id=request_id,
        overall_scope_summary=plan_data.overall_scope_summary,
        material_deviation_from_standard=plan_data.material_deviation_from_standard,
        overall_deviation_rationale=plan_data.overall_deviation_rationale
    )
    db.add(new_plan)
    db.flush()  # Get plan_id

    # Get all component definitions
    all_components = db.query(ValidationComponentDefinition).filter(
        ValidationComponentDefinition.is_active == True
    ).order_by(ValidationComponentDefinition.sort_order).all()

    # Create component entries
    # Priority: 1) explicit components, 2) template, 3) defaults
    if plan_data.components:
        # User provided specific components
        for comp_data in plan_data.components:
            # Get component definition
            comp_def = db.query(ValidationComponentDefinition).filter(
                ValidationComponentDefinition.component_id == comp_data.component_id
            ).first()

            if not comp_def:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Component {comp_data.component_id} not found"
                )

            # Get default expectation for this tier
            default_expectation = get_expectation_for_tier(comp_def, risk_tier_code)

            # Calculate deviation
            is_deviation = calculate_is_deviation(default_expectation, comp_data.planned_treatment)

            # Validate rationale if deviation
            if is_deviation and not comp_data.rationale:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Rationale is required for component {comp_def.component_code} because it deviates from the bank standard"
                )

            # Create plan component
            plan_comp = ValidationPlanComponent(
                plan_id=new_plan.plan_id,
                component_id=comp_data.component_id,
                default_expectation=default_expectation,
                planned_treatment=comp_data.planned_treatment,
                is_deviation=is_deviation,
                rationale=comp_data.rationale,
                additional_notes=comp_data.additional_notes
            )
            db.add(plan_comp)

    elif plan_data.template_plan_id:
        # Copy from template plan
        template_plan = db.query(ValidationPlan).options(
            joinedload(ValidationPlan.components).joinedload(ValidationPlanComponent.component_definition),
            joinedload(ValidationPlan.configuration)
        ).filter(ValidationPlan.plan_id == plan_data.template_plan_id).first()

        if not template_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template plan {plan_data.template_plan_id} not found"
            )

        # Copy high-level plan fields (if not already set by user)
        if not new_plan.overall_scope_summary and template_plan.overall_scope_summary:
            new_plan.overall_scope_summary = template_plan.overall_scope_summary
        if template_plan.material_deviation_from_standard:
            new_plan.material_deviation_from_standard = template_plan.material_deviation_from_standard
            if template_plan.overall_deviation_rationale:
                new_plan.overall_deviation_rationale = template_plan.overall_deviation_rationale

        # Copy components from template
        for template_comp in template_plan.components:
            # Get current expectation for this component (from ACTIVE config, not template's config)
            comp_def = template_comp.component_definition
            default_expectation = get_expectation_for_tier(comp_def, risk_tier_code)

            # Use template's planned_treatment and rationale
            planned_treatment = template_comp.planned_treatment
            rationale = template_comp.rationale

            # Recalculate is_deviation based on CURRENT expectation
            is_deviation = calculate_is_deviation(default_expectation, planned_treatment)

            plan_comp = ValidationPlanComponent(
                plan_id=new_plan.plan_id,
                component_id=template_comp.component_id,
                default_expectation=default_expectation,  # From ACTIVE config
                planned_treatment=planned_treatment,      # From template
                rationale=rationale,                      # From template
                is_deviation=is_deviation                 # Recalculated
            )
            db.add(plan_comp)

        # Audit log for template usage
        audit_log = AuditLog(
            entity_type="ValidationPlan",
            entity_id=new_plan.plan_id,
            action="CREATE_FROM_TEMPLATE",
            user_id=current_user.user_id,
            changes={
                "template_plan_id": plan_data.template_plan_id,
                "template_request_id": template_plan.request_id,
                "template_config_id": template_plan.config_id,
                "template_config_name": template_plan.configuration.config_name if template_plan.configuration else None
            },
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)

    else:
        # Auto-create all components with defaults
        for comp_def in all_components:
            default_expectation = get_expectation_for_tier(comp_def, risk_tier_code)

            # Default planned_treatment to match expectation
            if default_expectation == "Required":
                planned_treatment = "Planned"
            elif default_expectation == "NotExpected":
                planned_treatment = "NotPlanned"
            else:  # IfApplicable
                planned_treatment = "Planned"  # Default to planned, validator can change

            plan_comp = ValidationPlanComponent(
                plan_id=new_plan.plan_id,
                component_id=comp_def.component_id,
                default_expectation=default_expectation,
                planned_treatment=planned_treatment,
                is_deviation=False  # No deviation when using defaults
            )
            db.add(plan_comp)

    db.commit()
    db.refresh(new_plan)

    # Build response with derived fields
    response_data = ValidationPlanResponse.model_validate(new_plan)
    response_data.model_id = first_model.model_id
    response_data.model_name = first_model.model_name

    # Find the risk tier label for the most conservative tier used for the plan
    risk_tier_taxonomy = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == risk_tier_code
    ).first()
    response_data.risk_tier = risk_tier_taxonomy.label if risk_tier_taxonomy else "Unknown"

    # Map risk tier to validation approach
    tier_to_approach = {
        "TIER_1": "Comprehensive",
        "TIER_2": "Standard",
        "TIER_3": "Conceptual",
        "TIER_4": "Executive Summary",
        # Legacy fallbacks
        "HIGH": "Comprehensive",
        "MEDIUM": "Standard",
        "LOW": "Conceptual",
        "VERY_LOW": "Executive Summary"
    }
    response_data.validation_approach = tier_to_approach.get(risk_tier_code, "Standard")

    return response_data


@router.get("/requests/{request_id}/plan/template-suggestions", response_model=PlanTemplateSuggestionsResponse)
def get_plan_template_suggestions(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get suggestions for previous validation plans that could be used as templates.

    Returns plans from previous validations of the same Validation Type for the same models.
    Warns if template uses a different configuration version (requirements changed).
    """
    # Get current validation request
    current_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(ValidationRequestModelVersion.model)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not current_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Get active configuration for comparison
    active_config = db.query(ComponentDefinitionConfiguration).filter_by(is_active=True).first()
    active_config_id = active_config.config_id if active_config else None

    # Extract model IDs from current request
    current_model_ids = {assoc.model.model_id for assoc in current_request.model_versions_assoc if assoc.model}

    if not current_model_ids:
        return PlanTemplateSuggestionsResponse(has_suggestions=False, suggestions=[])

    # Find previous validations with same validation type and overlapping models
    # Must be APPROVED status and have a plan
    validation_type_id = current_request.validation_type.value_id if current_request.validation_type else None

    if not validation_type_id:
        return PlanTemplateSuggestionsResponse(has_suggestions=False, suggestions=[])

    # Query for potential template sources
    potential_templates = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.validation_plan).joinedload(ValidationPlan.components),
        joinedload(ValidationRequest.validation_plan).joinedload(ValidationPlan.configuration),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(ValidationRequestModelVersion.model),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.validation_type)
    ).filter(
        ValidationRequest.request_id != request_id,  # Not current request
        ValidationRequest.validation_type_id == validation_type_id,  # Same validation type
        ValidationRequest.current_status.has(code="APPROVED"),  # Only approved validations
        ValidationRequest.validation_plan != None  # Has a plan
    ).order_by(ValidationRequest.completion_date.desc()).limit(5).all()

    suggestions = []

    for template_request in potential_templates:
        # Check if models overlap
        template_model_ids = {assoc.model.model_id for assoc in template_request.model_versions_assoc if assoc.model}

        if not current_model_ids.intersection(template_model_ids):
            continue  # No overlapping models, skip

        plan = template_request.validation_plan

        # Count deviations
        deviations_count = sum(1 for comp in plan.components if comp.is_deviation)

        # Get primary validator name (first assigned validator)
        validator_name = None
        if template_request.assignments:
            primary = next((a for a in template_request.assignments if a.is_primary), None)
            if not primary and template_request.assignments:
                primary = template_request.assignments[0]
            if primary and primary.validator:
                validator_name = primary.validator.full_name

        # Check if config is different
        template_config_id = plan.config_id
        is_different_config = template_config_id != active_config_id if template_config_id and active_config_id else False

        config_name = plan.configuration.config_name if plan.configuration else None

        suggestion = PlanTemplateSuggestion(
            source_request_id=template_request.request_id,
            source_plan_id=plan.plan_id,
            validation_type=template_request.validation_type.label if template_request.validation_type else "Unknown",
            model_names=[assoc.model.model_name for assoc in template_request.model_versions_assoc if assoc.model],
            completion_date=template_request.completion_date.isoformat() if template_request.completion_date else None,
            validator_name=validator_name,
            component_count=len(plan.components),
            deviations_count=deviations_count,
            config_id=template_config_id,
            config_name=config_name,
            is_different_config=is_different_config
        )
        suggestions.append(suggestion)

    return PlanTemplateSuggestionsResponse(
        has_suggestions=len(suggestions) > 0,
        suggestions=suggestions
    )


@router.get("/requests/{request_id}/plan", response_model=ValidationPlanResponse)
def get_validation_plan(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the validation plan for a validation request.
    """
    # Get validation request
    request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(ValidationRequestModelVersion.model).joinedload(Model.risk_tier)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Get validation plan
    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components).joinedload(ValidationPlanComponent.component_definition)
    ).filter(ValidationPlan.request_id == request_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation plan not found for request {request_id}"
        )

    # Build response with derived fields
    model = request.model_versions_assoc[0].model if request.model_versions_assoc else None
    response_data = ValidationPlanResponse.model_validate(plan)

    if model:
        response_data.model_id = model.model_id
        response_data.model_name = model.model_name
        response_data.risk_tier = model.risk_tier.label if model.risk_tier else "Unknown"

        risk_tier_code = model.risk_tier.code if model.risk_tier else "MEDIUM"
        tier_to_approach = {
            "HIGH": "Comprehensive",
            "MEDIUM": "Standard",
            "LOW": "Conceptual",
            "VERY_LOW": "Executive Summary"
        }
        response_data.validation_approach = tier_to_approach.get(risk_tier_code, "Standard")

    return response_data


@router.get("/requests/{request_id}/plan/pdf")
def export_validation_plan_pdf(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export validation plan as a professional PDF document.
    """
    # Get validation request
    request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(ValidationRequestModelVersion.model).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.validation_type)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Get validation plan
    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components).joinedload(ValidationPlanComponent.component_definition)
    ).filter(ValidationPlan.request_id == request_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation plan not found for request {request_id}"
        )

    # Get model info
    model = request.model_versions_assoc[0].model if request.model_versions_assoc else None
    model_name = model.model_name if model else "Unknown Model"
    risk_tier = model.risk_tier.label if model and model.risk_tier else "Unknown"

    # Determine validation approach
    risk_tier_code = model.risk_tier.code if model and model.risk_tier else "MEDIUM"
    tier_to_approach = {
        "HIGH": "Comprehensive",
        "MEDIUM": "Standard",
        "LOW": "Conceptual",
        "VERY_LOW": "Executive Summary"
    }
    validation_approach = tier_to_approach.get(risk_tier_code, "Standard")

    validation_type = request.validation_type.label if request.validation_type else "Unknown"

    # Create PDF
    class ValidationPlanPDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, 'Model Validation Plan', 0, 1, 'C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    pdf = ValidationPlanPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header Information
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'Validation Request Information', 0, 1)
    pdf.ln(2)

    pdf.set_font('Arial', '', 10)
    info_data = [
        ('Request ID:', str(request_id)),
        ('Model Name:', model_name),
        ('Risk Tier:', risk_tier),
        ('Validation Type:', validation_type),
        ('Validation Approach:', validation_approach),
        ('Created:', plan.created_at.strftime('%Y-%m-%d') if plan.created_at else 'N/A'),
        ('Last Updated:', plan.updated_at.strftime('%Y-%m-%d') if plan.updated_at else 'N/A')
    ]

    for label, value in info_data:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(50, 6, label, 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, value, 0, 1)

    pdf.ln(5)

    # Overall Scope Summary
    if plan.overall_scope_summary:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Overall Scope Summary', 0, 1)
        pdf.ln(2)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 5, plan.overall_scope_summary or 'N/A')
        pdf.ln(3)

    # Material Deviation Information
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'Material Deviation from Standard', 0, 1)
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, 'Yes' if plan.material_deviation_from_standard else 'No', 0, 1)

    if plan.material_deviation_from_standard and plan.overall_deviation_rationale:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, 'Rationale:', 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 5, plan.overall_deviation_rationale)

    pdf.ln(5)

    # Validation Components by Section
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'Validation Components', 0, 1)
    pdf.ln(3)

    # Group components by section
    components_by_section = {}
    for comp in plan.components:
        section = comp.component_definition.section_number
        if section not in components_by_section:
            components_by_section[section] = {
                'title': comp.component_definition.section_title,
                'components': []
            }
        components_by_section[section]['components'].append(comp)

    # Render each section
    for section_num in sorted(components_by_section.keys()):
        section_data = components_by_section[section_num]

        # Section header
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, f"Section {section_num}: {section_data['title']}", 0, 1)
        pdf.ln(1)

        # Table header
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(30, 6, 'Code', 1, 0, 'C', True)
        pdf.cell(50, 6, 'Component', 1, 0, 'C', True)
        pdf.cell(30, 6, 'Expectation', 1, 0, 'C', True)
        pdf.cell(30, 6, 'Treatment', 1, 0, 'C', True)
        pdf.cell(50, 6, 'Deviation', 1, 1, 'C', True)

        # Components
        pdf.set_font('Arial', '', 8)
        for comp in section_data['components']:
            comp_def = comp.component_definition

            # Component code
            pdf.cell(30, 6, comp_def.component_code, 1, 0)

            # Component title (truncate if too long)
            title = comp_def.component_title[:30] + '...' if len(comp_def.component_title) > 30 else comp_def.component_title
            pdf.cell(50, 6, title, 1, 0)

            # Default expectation
            pdf.cell(30, 6, comp.default_expectation, 1, 0)

            # Planned treatment
            treatment_map = {
                'Planned': 'Planned',
                'NotPlanned': 'Not Planned',
                'NotApplicable': 'N/A'
            }
            treatment = treatment_map.get(comp.planned_treatment, comp.planned_treatment)
            pdf.cell(30, 6, treatment, 1, 0)

            # Deviation status
            deviation_text = 'Yes' if comp.is_deviation else 'No'
            if comp.is_deviation:
                pdf.set_fill_color(255, 240, 200)
                pdf.cell(50, 6, deviation_text, 1, 1, 'C', True)
            else:
                pdf.cell(50, 6, deviation_text, 1, 1, 'C')

            # Add rationale if present
            if comp.rationale and comp.rationale.strip():
                pdf.set_font('Arial', 'I', 7)
                pdf.set_x(40)
                rationale_text = f"Rationale: {comp.rationale[:100]}..." if len(comp.rationale) > 100 else f"Rationale: {comp.rationale}"
                pdf.multi_cell(150, 4, rationale_text)
                pdf.set_font('Arial', '', 8)

        pdf.ln(3)

    # Summary statistics
    total_components = len(plan.components)
    planned_components = sum(1 for c in plan.components if c.planned_treatment == 'Planned')
    deviations = sum(1 for c in plan.components if c.is_deviation)

    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'Summary Statistics', 0, 1)
    pdf.ln(2)

    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f'Total Components: {total_components}', 0, 1)
    pdf.cell(0, 6, f'Planned Components: {planned_components}', 0, 1)
    pdf.cell(0, 6, f'Total Deviations: {deviations}', 0, 1)

    if total_components > 0:
        deviation_rate = (deviations / total_components) * 100
        pdf.cell(0, 6, f'Deviation Rate: {deviation_rate:.1f}%', 0, 1)

    # Save PDF to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf.output(temp_file.name)
    temp_file.close()

    # Return as file response
    filename = f"validation_plan_request_{request_id}_{model_name.replace(' ', '_')}.pdf"

    return FileResponse(
        temp_file.name,
        media_type='application/pdf',
        filename=filename,
        background=lambda: os.unlink(temp_file.name)  # Clean up temp file after sending
    )


@router.patch("/requests/{request_id}/plan", response_model=ValidationPlanResponse)
def update_validation_plan(
    request_id: int,
    plan_updates: ValidationPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a validation plan.

    Allows updating:
    - Overall scope summary
    - Material deviation flag and rationale
    - Individual component planned treatments and rationales
    """
    check_validator_or_admin(current_user)

    # Get validation request
    request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(ValidationRequestModelVersion.model).joinedload(Model.risk_tier)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Get validation plan
    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components).joinedload(ValidationPlanComponent.component_definition)
    ).filter(ValidationPlan.request_id == request_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation plan not found for request {request_id}"
        )

    # Update plan header fields
    if plan_updates.overall_scope_summary is not None:
        plan.overall_scope_summary = plan_updates.overall_scope_summary

    if plan_updates.material_deviation_from_standard is not None:
        plan.material_deviation_from_standard = plan_updates.material_deviation_from_standard

        # Validate rationale if material deviation
        if plan.material_deviation_from_standard:
            if plan_updates.overall_deviation_rationale:
                plan.overall_deviation_rationale = plan_updates.overall_deviation_rationale
            elif not plan.overall_deviation_rationale:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="overall_deviation_rationale is required when material_deviation_from_standard is true"
                )
        else:
            plan.overall_deviation_rationale = plan_updates.overall_deviation_rationale
    elif plan_updates.overall_deviation_rationale is not None:
        plan.overall_deviation_rationale = plan_updates.overall_deviation_rationale

    # Update component entries
    if plan_updates.components:
        # Get model risk tier for deviation calculation
        model = request.model_versions_assoc[0].model if request.model_versions_assoc else None
        risk_tier_code = model.risk_tier.code if (model and model.risk_tier) else "MEDIUM"

        for comp_update in plan_updates.components:
            # Find existing component (match by component_id in update with our plan components)
            plan_comp = next(
                (pc for pc in plan.components if pc.component_id == comp_update.component_id),
                None
            )

            if not plan_comp:
                # Component doesn't exist in plan yet - skip or error
                continue

            # Update fields
            if comp_update.planned_treatment:
                plan_comp.planned_treatment = comp_update.planned_treatment

                # Recalculate deviation
                plan_comp.is_deviation = calculate_is_deviation(
                    plan_comp.default_expectation,
                    comp_update.planned_treatment
                )

                # Validate rationale if deviation
                if plan_comp.is_deviation:
                    if comp_update.rationale:
                        plan_comp.rationale = comp_update.rationale
                    elif not plan_comp.rationale:
                        comp_def = plan_comp.component_definition
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Rationale is required for component {comp_def.component_code} because it deviates from the bank standard"
                        )
                else:
                    plan_comp.rationale = comp_update.rationale
            elif comp_update.rationale is not None:
                plan_comp.rationale = comp_update.rationale

            if comp_update.additional_notes is not None:
                plan_comp.additional_notes = comp_update.additional_notes

    db.commit()
    db.refresh(plan)

    # Build response
    model = request.model_versions_assoc[0].model if request.model_versions_assoc else None
    response_data = ValidationPlanResponse.model_validate(plan)

    if model:
        response_data.model_id = model.model_id
        response_data.model_name = model.model_name
        response_data.risk_tier = model.risk_tier.label if model.risk_tier else "Unknown"

        risk_tier_code = model.risk_tier.code if model.risk_tier else "MEDIUM"
        tier_to_approach = {
            "HIGH": "Comprehensive",
            "MEDIUM": "Standard",
            "LOW": "Conceptual",
            "VERY_LOW": "Executive Summary"
        }
        response_data.validation_approach = tier_to_approach.get(risk_tier_code, "Standard")

    return response_data


@router.delete("/requests/{request_id}/plan", status_code=status.HTTP_204_NO_CONTENT)
def delete_validation_plan(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a validation plan.

    Business Rules:
    - Only Validators and Admins can delete plans
    - Plan must be unlocked (locked_at is NULL)
    - Once a plan is locked (in Review, Pending Approval, or Approved status), it cannot be deleted

    Use Case:
    - Validator realizes they need to start over before submitting for review
    - Plan was created with wrong template or configuration
    """
    check_validator_or_admin(current_user)

    # Get validation plan with request info
    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.request)
    ).filter(ValidationPlan.request_id == request_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation plan not found for request {request_id}"
        )

    # Check if plan is locked
    if plan.locked_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a locked validation plan. Locked plans have been submitted for review or approval and must be preserved for regulatory compliance."
        )

    # Store plan info for audit log before deletion
    plan_id = plan.plan_id
    component_count = len(plan.components)

    # Create audit log BEFORE deletion
    audit_log = AuditLog(
        entity_type="ValidationPlan",
        entity_id=plan_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "request_id": request_id,
            "component_count": component_count,
            "was_locked": False,
            "reason": "Validation plan deleted before lock-in"
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    # Delete plan (cascade will delete components)
    db.delete(plan)
    db.commit()

    return None


# ==================== CONFIGURATION MANAGEMENT ENDPOINTS ====================

@router.get("/configurations", response_model=List[ConfigurationResponse])
def list_configurations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all configuration versions.

    Configurations represent snapshots of validation requirements at different points in time.
    They enable grandfathering: old plans reference the config that was active when they were locked.
    """
    configs = db.query(ComponentDefinitionConfiguration).order_by(
        ComponentDefinitionConfiguration.effective_date.desc()
    ).all()

    return configs


@router.get("/configurations/{config_id}", response_model=ConfigurationDetailResponse)
def get_configuration_detail(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed configuration with all component snapshots.

    Shows the complete validation requirements matrix (Figure 3) as it existed
    at the time this configuration was published.
    """
    config = db.query(ComponentDefinitionConfiguration).options(
        joinedload(ComponentDefinitionConfiguration.config_items)
    ).filter(ComponentDefinitionConfiguration.config_id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found"
        )

    return config


@router.post("/configurations/publish", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
def publish_new_configuration(
    config_data: ConfigurationPublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Publish a new configuration version (Admin only).

    This creates a snapshot of the current component definitions and sets it as the active configuration.
    The previous active configuration is marked inactive but preserved for historical reference.

    Process:
    1. Deactivate the current active configuration
    2. Create new configuration header
    3. Snapshot all current component definitions
    4. Audit log the publication

    Future validation plans will use this new configuration's expectations.
    Existing locked plans remain linked to their original configuration (grandfathering).
    """
    check_admin(current_user)

    # Deactivate current active config
    current_active = db.query(ComponentDefinitionConfiguration).filter_by(is_active=True).first()
    if current_active:
        current_active.is_active = False

    # Create new configuration
    new_config = ComponentDefinitionConfiguration(
        config_name=config_data.config_name,
        description=config_data.description,
        effective_date=config_data.effective_date or date.today(),
        created_by_user_id=current_user.user_id,
        is_active=True
    )
    db.add(new_config)
    db.flush()  # Get config_id

    # Snapshot all component definitions
    components = db.query(ValidationComponentDefinition).filter_by(is_active=True).all()

    for component in components:
        config_item = ComponentDefinitionConfigItem(
            config_id=new_config.config_id,
            component_id=component.component_id,
            expectation_high=component.expectation_high,
            expectation_medium=component.expectation_medium,
            expectation_low=component.expectation_low,
            expectation_very_low=component.expectation_very_low,
            section_number=component.section_number,
            section_title=component.section_title,
            component_code=component.component_code,
            component_title=component.component_title,
            is_test_or_analysis=component.is_test_or_analysis,
            sort_order=component.sort_order,
            is_active=component.is_active
        )
        db.add(config_item)

    db.commit()
    db.refresh(new_config)

    # Audit log
    audit_log = AuditLog(
        entity_type="ComponentDefinitionConfiguration",
        entity_id=new_config.config_id,
        action="PUBLISH",
        user_id=current_user.user_id,
        changes={
            "config_name": config_data.config_name,
            "description": config_data.description,
            "effective_date": str(config_data.effective_date or date.today()),
            "component_count": len(components),
            "previous_active_config_id": current_active.config_id if current_active else None
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()

    return new_config


@router.get("/compliance-report/deviation-trends")
def get_deviation_trends_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate compliance report showing deviation trends across all validations.
    Includes counts of deviations by component, risk tier, and over time.
    """
    # Get all validation plans with components
    plans = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components).joinedload(ValidationPlanComponent.component_definition),
        joinedload(ValidationPlan.request)
        .joinedload(ValidationRequest.model_versions_assoc)
        .joinedload(ValidationRequestModelVersion.model)
        .joinedload(Model.risk_tier)
    ).all()

    # Calculate deviation statistics
    total_plans = len(plans)
    total_components = 0
    total_deviations = 0
    plans_with_deviations = 0

    deviation_by_component = {}  # component_code -> count
    deviation_by_risk_tier = {"High": 0, "Medium": 0, "Low": 0, "Very Low": 0}
    deviation_by_section = {}  # section_number -> count
    deviations_over_time = {}  # month -> count

    material_deviations_count = 0

    # Detailed deviation records
    deviation_records = []

    for plan in plans:
        has_deviation = False
        total_components += len(plan.components)

        # Track material deviations
        if plan.material_deviation_from_standard:
            material_deviations_count += 1

        for comp in plan.components:
            if comp.is_deviation:
                has_deviation = True
                total_deviations += 1

                # By component
                comp_code = comp.component_definition.component_code
                deviation_by_component[comp_code] = deviation_by_component.get(comp_code, 0) + 1

                # By section
                section = comp.component_definition.section_number
                deviation_by_section[section] = deviation_by_section.get(section, 0) + 1

                # By risk tier (from associated model)
                if plan.request and plan.request.model_versions_assoc:
                    model_version_assoc = plan.request.model_versions_assoc[0]
                    model = model_version_assoc.model if model_version_assoc else None
                    if model and model.risk_tier:
                        risk_tier = model.risk_tier.label
                        if risk_tier in ["Tier 1 (High)", "High"]:
                            deviation_by_risk_tier["High"] += 1
                        elif risk_tier in ["Tier 2 (Medium)", "Medium"]:
                            deviation_by_risk_tier["Medium"] += 1
                        elif risk_tier in ["Tier 3 (Low)", "Low"]:
                            deviation_by_risk_tier["Low"] += 1
                        else:
                            deviation_by_risk_tier["Very Low"] += 1

                # Over time (by month of plan creation)
                if plan.request and plan.request.created_at:
                    month_key = plan.request.created_at.strftime("%Y-%m")
                    deviations_over_time[month_key] = deviations_over_time.get(month_key, 0) + 1

                # Detailed record
                model_name = "Unknown"
                risk_tier = "Unknown"
                if plan.request and plan.request.model_versions_assoc:
                    model_version_assoc = plan.request.model_versions_assoc[0]
                    model = model_version_assoc.model if model_version_assoc else None
                    if model:
                        model_name = model.model_name
                        risk_tier = model.risk_tier.label if model.risk_tier else "Unknown"

                deviation_records.append({
                    "plan_id": plan.plan_id,
                    "request_id": plan.request_id,
                    "model_name": model_name,
                    "risk_tier": risk_tier,
                    "component_code": comp_code,
                    "component_title": comp.component_definition.component_title,
                    "section_number": comp.component_definition.section_number,
                    "section_title": comp.component_definition.section_title,
                    "rationale": comp.rationale,
                    "created_at": plan.request.created_at.isoformat() if plan.request and plan.request.created_at else None
                })

        if has_deviation:
            plans_with_deviations += 1

    # Sort component deviations by frequency
    top_deviation_components = sorted(
        [{"component_code": k, "count": v} for k, v in deviation_by_component.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:10]  # Top 10

    # Sort section deviations
    deviation_by_section_list = sorted(
        [{"section": k, "count": v} for k, v in deviation_by_section.items()],
        key=lambda x: x["count"],
        reverse=True
    )

    # Sort time series
    deviations_timeline = sorted(
        [{"month": k, "count": v} for k, v in deviations_over_time.items()],
        key=lambda x: x["month"]
    )

    # Calculate deviation rate
    deviation_rate = (total_deviations / total_components * 100) if total_components > 0 else 0
    plan_deviation_rate = (plans_with_deviations / total_plans * 100) if total_plans > 0 else 0

    return {
        "summary": {
            "total_validation_plans": total_plans,
            "total_components_reviewed": total_components,
            "total_deviations": total_deviations,
            "plans_with_deviations": plans_with_deviations,
            "plans_with_material_deviations": material_deviations_count,
            "deviation_rate_percentage": round(deviation_rate, 2),
            "plan_deviation_rate_percentage": round(plan_deviation_rate, 2)
        },
        "deviation_by_component": top_deviation_components,
        "deviation_by_risk_tier": deviation_by_risk_tier,
        "deviation_by_section": deviation_by_section_list,
        "deviations_timeline": deviations_timeline,
        "recent_deviations": sorted(deviation_records, key=lambda x: x["created_at"] or "", reverse=True)[:50]
    }

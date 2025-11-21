"""Validation workflow API endpoints."""
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Union, Dict
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    User, Model, TaxonomyValue, Taxonomy, AuditLog,
    ValidationRequest, ValidationRequestModelVersion, ValidationStatusHistory, ValidationAssignment,
    ValidationOutcome, ValidationReviewOutcome, ValidationApproval, ValidationGroupingMemory,
    ValidationPolicy, ModelRegion, Region
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
    ValidationStatusHistoryResponse
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


def calculate_days_in_status(db: Session, request: ValidationRequest) -> int:
    """Calculate how many days the request has been in current status."""
    latest_history = db.query(ValidationStatusHistory).filter(
        ValidationStatusHistory.request_id == request.request_id,
        ValidationStatusHistory.new_status_id == request.current_status_id
    ).order_by(desc(ValidationStatusHistory.changed_at)).first()

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
                    approvals_to_create.append(ValidationApproval(
                        request_id=validation_request.request_id,
                        approver_id=approver.user_id,
                        approver_role=f"Regional Approver ({region_code})",
                        is_required=True,
                        approval_status="Pending",
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
                    approvals_to_create.append(ValidationApproval(
                        request_id=validation_request.request_id,
                        approver_id=approver.user_id,
                        approver_role="Global Approver",
                        is_required=True,
                        approval_status="Pending",
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
                            approvals_to_create.append(ValidationApproval(
                                request_id=validation_request.request_id,
                                approver_id=approver.user_id,
                                approver_role=f"Regional Approver ({region.code})",
                                is_required=True,
                                approval_status="Pending",
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
            ValidationAssignment.validator)
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
            days_in_status=calculate_days_in_status(db, req),
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
        joinedload(ValidationRequest.models),
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
        joinedload(ValidationRequest.regions)
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

    # Validate transition
    if not check_valid_status_transition(old_status_code, new_status_code):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{old_status_code}' to '{new_status_code}'"
        )

    # Additional business rules
    if new_status_code == "REVIEW":
        # Must have at least one assigned validator
        if not validation_request.assignments:
            raise HTTPException(
                status_code=400, detail="Cannot move to Review without assigned validators")

    if new_status_code == "PENDING_APPROVAL":
        # Must have an outcome created
        if not validation_request.outcome:
            raise HTTPException(
                status_code=400, detail="Cannot move to Pending Approval without creating outcome")

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
        joinedload(ValidationRequest.regions)
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

    # Create approval record
    approval = ValidationApproval(
        request_id=request_id,
        approver_id=approval_data.approver_id,
        approver_role=approval_data.approver_role,
        is_required=approval_data.is_required,
        approval_status="Pending",
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
    approval = db.query(ValidationApproval).filter(
        ValidationApproval.approval_id == approval_id
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    # Only the designated approver can submit approval
    if current_user.user_id != approval.approver_id:
        raise HTTPException(
            status_code=403, detail="Only the designated approver can submit this approval")

    approval.approval_status = update_data.approval_status
    approval.comments = update_data.comments

    if update_data.approval_status in ["Approved", "Rejected"]:
        approval.approved_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationApproval",
        entity_id=approval.request_id,
        action="APPROVAL_SUBMITTED",
        user_id=current_user.user_id,
        changes={
            "approval_id": approval_id,
            "status": update_data.approval_status,
            "approver_role": approval.approver_role
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(approval)
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
        joinedload(ValidationRequest.priority)
    ).all()

    aging_data = []
    for req in requests:
        if req.current_status and req.current_status.code not in ["APPROVED", "CANCELLED"]:
            days_in_status = calculate_days_in_status(db, req)
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

        # Get validation policy for this risk tier
        policy = db.query(ValidationPolicy).filter(
            ValidationPolicy.risk_tier_id == model.risk_tier.value_id
        ).first()

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
        # Find model versions linked to this validation request
        versions = db.query(ModelVersion).filter(
            ModelVersion.validation_request_id == req.request_id,
            ModelVersion.production_date.isnot(None)
        ).all()

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
    pending_requests = db.query(ValidationRequest).filter(
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
    active_requests = db.query(ValidationRequest).filter(
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
    Shows revalidation requests awaiting documentation submission for models where user is:
    - Owner
    - Developer
    - Delegate
    """
    from app.models.model_delegate import ModelDelegate

    today = date.today()

    # Find revalidation requests for models accessible by current user
    # that are awaiting submission
    pending_requests = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).join(
        Model
    ).filter(
        or_(
            Model.owner_id == current_user.user_id,
            Model.developer_id == current_user.user_id,
            Model.delegates.any(
                (ModelDelegate.user_id == current_user.user_id) &
                (ModelDelegate.revoked_at == None)
            )
        ),
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

    # Sort by urgency (overdue first, then by days until due)
    urgency_order = {"overdue": 0, "in_grace_period": 1, "due_soon": 2, "upcoming": 3, "unknown": 4}
    return sorted(results, key=lambda x: (urgency_order.get(x["urgency"], 4), x["days_until_submission_due"] or 999))


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

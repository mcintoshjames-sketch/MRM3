"""Validation workflow API endpoints."""
from datetime import datetime, date, timedelta, timezone
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Union, Dict, Tuple, Set, Any
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import desc, or_, func, nullslast, select, text
from fpdf import FPDF
import tempfile
import os

from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.core.roles import is_admin, is_validator, is_global_approver, is_regional_approver, RoleCode
from app.core.rule_evaluation import get_required_approver_roles
from app.core.exception_detection import autoclose_type3_on_full_validation_approved
from app.core.validation_conflicts import (
    find_active_validation_conflicts,
    build_validation_conflict_message
)
from app.models.user import LocalStatus
from app.models import (
    User, Model, ModelVersion, TaxonomyValue, Taxonomy, AuditLog, Region, EntraUser, ApproverRole,
    ValidationRequest, ValidationRequestModelVersion, ValidationStatusHistory, ValidationAssignment,
    ValidationOutcome, ValidationReviewOutcome, ValidationApproval, ValidationGroupingMemory,
    ValidationPolicy, ValidationWorkflowSLA, ModelRegion, Region,
    ValidationComponentDefinition, ValidationPlan, ValidationPlanComponent,
    ComponentDefinitionConfiguration, ComponentDefinitionConfigItem,
    OverdueRevalidationComment
)
from app.models.recommendation import Recommendation
from app.models.attestation import AttestationRecord
from app.models.model_delegate import ModelDelegate
from app.api.due_date_override import (
    handle_override_on_approval,
    promote_next_cycle_override,
    void_override_on_cancellation
)
from app.schemas.validation import (
    ValidationRequestCreate, ValidationRequestUpdate, ValidationRequestStatusUpdate,
    ValidationRequestHold, ValidationRequestCancel, ValidationRequestResume,
    ValidationRequestDecline, ValidationRequestMarkSubmission, ValidationApprovalUnlink,
    ValidationWarning, ValidationRequestWarningsResponse,
    ValidationRequestModelUpdate, ValidationRequestModelUpdateResponse,
    ValidationRequestResponse, ValidationRequestDetailResponse, ValidationRequestListResponse,
    ValidationAssignmentCreate, ValidationAssignmentUpdate, ValidationAssignmentResponse,
    ReviewerSignOffRequest,
    ValidationOutcomeCreate, ValidationOutcomeUpdate, ValidationOutcomeResponse,
    ValidationReviewOutcomeCreate, ValidationReviewOutcomeUpdate, ValidationReviewOutcomeResponse,
    ValidationApprovalCreate, ValidationApprovalUpdate, ValidationApprovalResponse,
    ManualApprovalCreate, ManualApprovalResponse,
    ValidationStatusHistoryResponse,
    ValidationComponentDefinitionResponse, ValidationComponentDefinitionUpdate,
    ValidationPlanCreate, ValidationPlanUpdate, ValidationPlanResponse,
    PlanTemplateSuggestion, PlanTemplateSuggestionsResponse,
    ConfigurationResponse, ConfigurationDetailResponse, ConfigurationItemResponse, ConfigurationPublishRequest,
    OpenValidationSummary, OpenValidationsCheckResponse, ForceResetRequest, ForceResetResponse,
    RiskMismatchItem, RiskMismatchReportResponse,
    PreTransitionWarning, PreTransitionWarningsResponse
)
from app.schemas.user_lookup import AssignableValidatorResponse
from app.schemas.conditional_approval import (
    ConditionalApprovalsEvaluationResponse,
    ManualApprovalSummary,
    SubmitConditionalApprovalRequest,
    SubmitConditionalApprovalResponse,
    VoidApprovalRequirementRequest,
    VoidApprovalRequirementResponse
)
# Note: get_global_assessment_status is imported inside functions to avoid circular import

router = APIRouter()


# ==================== CONSTANTS ====================

# Validation types that require full component-level planning
FULL_PLAN_VALIDATION_TYPES = ["INITIAL", "COMPREHENSIVE"]

# Validation types that only require scope summary (no components)
SCOPE_ONLY_VALIDATION_TYPES = ["TARGETED", "INTERIM"]


# ==================== HELPER FUNCTIONS ====================

def check_validator_or_admin(user: User):
    """Check if user has Validator or Admin role."""
    if not (is_admin(user) or is_validator(user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Validators and Admins can perform this action"
        )


def check_admin(user: User):
    """Check if user has Admin role."""
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can perform this action"
        )


def create_audit_log(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    user_id: int,
    changes: Optional[dict] = None
):
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


def _is_user_active(db: Session, user: Optional[User]) -> bool:
    """Check if user is active based on local_status (synced from Entra)."""
    if not user:
        return False
    # Use local_status which is synced from Entra via the sync service
    return user.local_status == LocalStatus.ENABLED.value


# Staleness threshold for overdue comments (matches overdue_commentary.py)
COMMENT_STALENESS_DAYS = 45


def create_revision_snapshot(db: Session, validation_request: ValidationRequest) -> dict:
    """
    Create a snapshot of the current validation state for comparison when resubmitting
    from REVISION status. Used to determine if approvals should be reset.

    Returns a dict with:
    - overall_rating: Current scorecard overall rating (if any)
    - recommendation_ids: List of recommendation IDs linked to this validation
    - limitation_ids: List of limitation IDs linked to this validation
    - snapshot_at: Timestamp of snapshot creation
    """
    from app.models.recommendation import Recommendation
    from app.models.limitation import ModelLimitation

    # Get scorecard overall rating if exists
    overall_rating = None
    if validation_request.scorecard_result:
        overall_rating = validation_request.scorecard_result.overall_rating

    # Get recommendation IDs linked to this validation request
    recommendation_ids = [
        r.recommendation_id for r in db.query(Recommendation.recommendation_id).filter(
            Recommendation.validation_request_id == validation_request.request_id
        ).all()
    ]

    # Get limitation IDs linked to this validation request
    limitation_ids = [
        l.limitation_id for l in db.query(ModelLimitation.limitation_id).filter(
            ModelLimitation.validation_request_id == validation_request.request_id
        ).all()
    ]

    return {
        "snapshot_at": utc_now().isoformat(),
        "overall_rating": overall_rating,
        "recommendation_ids": sorted(recommendation_ids),
        "limitation_ids": sorted(limitation_ids)
    }

# Open/Active status codes (not closed)
CLOSED_STATUS_CODES = {"APPROVED", "CANCELLED"}


def get_open_validations_for_model(db: Session, model_id: int) -> List[ValidationRequest]:
    """
    Find all open (active, non-approved) validation requests for a model.

    Open status = NOT in APPROVED or CANCELLED status.
    Returns validation requests that could be affected by risk tier changes.
    """
    # Get closed status value_ids
    closed_statuses = db.query(TaxonomyValue.value_id).join(
        Taxonomy, TaxonomyValue.taxonomy_id == Taxonomy.taxonomy_id
    ).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code.in_(CLOSED_STATUS_CODES)
    ).subquery()

    # Find validation requests for this model that are not closed
    open_requests = db.query(ValidationRequest).join(
        ValidationRequestModelVersion,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequestModelVersion.model_id == model_id,
        ~ValidationRequest.current_status_id.in_(select(closed_statuses))
    ).all()

    return open_requests


def get_last_validation_completion_date(db: Session, model_id: int) -> Optional[datetime]:
    """
    Get the completion date of the most recent approved validation for a model.

    Returns None if no approved validation exists for the model.
    """
    # Get approved status
    approved_status = db.query(TaxonomyValue).join(
        Taxonomy, TaxonomyValue.taxonomy_id == Taxonomy.taxonomy_id
    ).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code == "APPROVED"
    ).first()

    if not approved_status:
        return None

    # Find the most recent approved validation for this model
    latest_approved = db.query(ValidationRequest).join(
        ValidationRequestModelVersion,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequestModelVersion.model_id == model_id,
        ValidationRequest.current_status_id == approved_status.value_id,
        ValidationRequest.completion_date.isnot(None)
    ).order_by(desc(ValidationRequest.completion_date)).first()

    if not latest_approved:
        return None

    return latest_approved.completion_date


def check_risk_assessment_for_workflow_progression(
    db: Session,
    models: List[Model],
    target_status_code: str
) -> Tuple[bool, List[str], List[str]]:
    """
    Check risk assessment status for models before allowing workflow progression.

    Checks both:
    1. Global risk assessment (required for all models)
    2. Regional risk assessments (required for deployed regions where requires_standalone_rating=True)

    Args:
        db: Database session
        models: List of models in the validation request
        target_status_code: Target status code (e.g., "REVIEW", "PENDING_APPROVAL")

    Returns:
        Tuple of:
        - can_proceed: bool - whether transition should be allowed
        - blocking_errors: List[str] - errors that block progression (no completed assessment)
        - warnings: List[str] - warnings for outdated assessments (user should review)
    """
    # Import here to avoid circular import
    from app.api.risk_assessment import get_global_assessment_status, get_regional_assessment_status

    blocking_errors = []
    warnings = []

    for model in models:
        # ========================================
        # 1. Check global assessment (required)
        # ========================================
        assessment_status = get_global_assessment_status(db, model.model_id)

        # Check if assessment exists and is complete
        if not assessment_status["has_assessment"]:
            blocking_errors.append(
                f"Model '{model.model_name}' (ID: {model.model_id}) has no global risk assessment. "
                f"A completed risk assessment is required before moving to {target_status_code.replace('_', ' ').title()}."
            )
            continue

        if not assessment_status["is_complete"]:
            blocking_errors.append(
                f"Model '{model.model_name}' (ID: {model.model_id}) has an incomplete global risk assessment. "
                f"Please complete the risk assessment before moving to {target_status_code.replace('_', ' ').title()}."
            )
            continue

        # Check if assessment is outdated (last modified before last validation completion)
        assessed_at = assessment_status["assessed_at"]
        if assessed_at:
            last_validation_date = get_last_validation_completion_date(db, model.model_id)
            if last_validation_date:
                # Normalize both datetimes to naive (strip timezone info) for comparison
                assessed_at_naive = assessed_at.replace(tzinfo=None) if assessed_at.tzinfo else assessed_at
                last_validation_naive = last_validation_date.replace(tzinfo=None) if last_validation_date.tzinfo else last_validation_date
                if assessed_at_naive < last_validation_naive:
                    warnings.append(
                        f"Model '{model.model_name}' (ID: {model.model_id}) has a global risk assessment "
                        f"that was last updated on {assessed_at.strftime('%Y-%m-%d')}, "
                        f"before the prior validation completed on {last_validation_date.strftime('%Y-%m-%d')}. "
                        f"Please review and update the risk assessment to ensure it reflects current model risk."
                    )

        # ========================================
        # 2. Check regional assessments (for deployed regions with requires_standalone_rating=True)
        # ========================================
        if hasattr(model, 'model_regions') and model.model_regions:
            for model_region in model.model_regions:
                region = model_region.region
                if region and region.requires_standalone_rating:
                    regional_status = get_regional_assessment_status(
                        db, model.model_id, region.region_id
                    )

                    if not regional_status["has_assessment"]:
                        blocking_errors.append(
                            f"Model '{model.model_name}' (ID: {model.model_id}) is deployed to region "
                            f"'{region.name}' which requires a standalone risk rating, but no regional "
                            f"risk assessment exists. Please complete a regional risk assessment for "
                            f"'{region.name}' before moving to {target_status_code.replace('_', ' ').title()}."
                        )
                    elif not regional_status["is_complete"]:
                        blocking_errors.append(
                            f"Model '{model.model_name}' (ID: {model.model_id}) has an incomplete "
                            f"regional risk assessment for '{region.name}'. Please complete the "
                            f"regional risk assessment before moving to {target_status_code.replace('_', ' ').title()}."
                        )
                    else:
                        # Check if regional assessment is outdated
                        regional_assessed_at = regional_status["assessed_at"]
                        if regional_assessed_at:
                            last_validation_date = get_last_validation_completion_date(db, model.model_id)
                            if last_validation_date:
                                regional_assessed_naive = regional_assessed_at.replace(tzinfo=None) if regional_assessed_at.tzinfo else regional_assessed_at
                                last_validation_naive = last_validation_date.replace(tzinfo=None) if last_validation_date.tzinfo else last_validation_date
                                if regional_assessed_naive < last_validation_naive:
                                    warnings.append(
                                        f"Model '{model.model_name}' (ID: {model.model_id}) has a regional "
                                        f"risk assessment for '{region.name}' that was last updated on "
                                        f"{regional_assessed_at.strftime('%Y-%m-%d')}, before the prior "
                                        f"validation completed on {last_validation_date.strftime('%Y-%m-%d')}. "
                                        f"Please review and update the regional risk assessment."
                                    )

    # Blocking errors prevent progression
    can_proceed = len(blocking_errors) == 0

    return can_proceed, blocking_errors, warnings


def reset_validation_plan_for_tier_change(
    db: Session,
    model_id: int,
    new_tier_id: int,
    user_id: int,
    force: bool = False
) -> dict:
    """
    Reset validation plan components and void approvals when a model's risk tier changes.

    This is called when a risk assessment finalizes a new tier for a model.

    Args:
        db: Database session
        model_id: Model whose risk tier changed
        new_tier_id: New risk tier taxonomy value ID
        user_id: User performing the change
        force: If True, proceed without checking for open validations first

    Returns:
        dict with:
        - reset_count: Number of validation requests affected
        - request_ids: List of affected request IDs
        - components_regenerated: Total components regenerated
        - approvals_voided: Total approvals voided
    """
    result = {
        "reset_count": 0,
        "request_ids": [],
        "components_regenerated": 0,
        "approvals_voided": 0
    }

    # Find open validation requests for this model
    open_requests = get_open_validations_for_model(db, model_id)

    if not open_requests:
        return result

    # Get the new risk tier code
    new_tier = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == new_tier_id).first()
    new_tier_code = new_tier.code if new_tier else "TIER_2"

    for request in open_requests:
        # Get the validation plan if it exists
        plan = db.query(ValidationPlan).filter(
            ValidationPlan.request_id == request.request_id
        ).first()

        if plan:
            # Delete existing plan components
            old_component_count = db.query(ValidationPlanComponent).filter(
                ValidationPlanComponent.plan_id == plan.plan_id
            ).count()

            db.query(ValidationPlanComponent).filter(
                ValidationPlanComponent.plan_id == plan.plan_id
            ).delete()

            # Regenerate components with new tier expectations
            all_components = db.query(ValidationComponentDefinition).filter(
                ValidationComponentDefinition.is_active == True
            ).order_by(ValidationComponentDefinition.sort_order).all()

            for comp_def in all_components:
                default_expectation = get_expectation_for_tier(comp_def, new_tier_code)

                # Default all to Planned (no deviations after reset)
                plan_comp = ValidationPlanComponent(
                    plan_id=plan.plan_id,
                    component_id=comp_def.component_id,
                    default_expectation=default_expectation,
                    planned_treatment="Planned",
                    is_deviation=False,
                    rationale=None,
                    additional_notes=None
                )
                db.add(plan_comp)
                result["components_regenerated"] += 1

            # Update plan metadata
            plan.updated_at = utc_now()
            plan.material_deviation_from_standard = False
            plan.overall_deviation_rationale = None

            # Create audit log for plan reset
            audit_log = AuditLog(
                entity_type="ValidationPlan",
                entity_id=plan.plan_id,
                action="RISK_TIER_RESET",
                user_id=user_id,
                changes={
                    "reason": "Model risk tier changed",
                    "model_id": model_id,
                    "new_risk_tier_id": new_tier_id,
                    "new_risk_tier_code": new_tier_code,
                    "old_component_count": old_component_count,
                    "new_component_count": len(all_components)
                },
                timestamp=utc_now()
            )
            db.add(audit_log)

        # Void all pending approvals for this request
        pending_approvals = db.query(ValidationApproval).filter(
            ValidationApproval.request_id == request.request_id,
            ValidationApproval.approval_status == "Pending",
            ValidationApproval.voided_at.is_(None)
        ).all()

        for approval in pending_approvals:
            approval.voided_by_id = user_id
            approval.void_reason = f"Voided due to model risk tier change to {new_tier_code}"
            approval.voided_at = utc_now()
            result["approvals_voided"] += 1

        # Create audit log for approvals voided
        if pending_approvals:
            approval_audit = AuditLog(
                entity_type="ValidationApproval",
                entity_id=request.request_id,
                action="BULK_VOID",
                user_id=user_id,
                changes={
                    "reason": "Model risk tier changed",
                    "model_id": model_id,
                    "new_risk_tier_code": new_tier_code,
                    "voided_approval_ids": [a.approval_id for a in pending_approvals]
                },
                timestamp=utc_now()
            )
            db.add(approval_audit)

        result["reset_count"] += 1
        result["request_ids"].append(request.request_id)

    return result


def get_commentary_status_for_request(
    db: Session,
    request_id: int,
    overdue_type: str
) -> dict:
    """
    Get commentary status for a validation request.

    Returns dict with:
    - comment_status: 'CURRENT' | 'STALE' | 'MISSING'
    - latest_comment: str | None
    - latest_comment_date: str | None
    - target_date_from_comment: date | None
    - needs_comment_update: bool
    """
    # Get current comment for this request
    current_comment = db.query(OverdueRevalidationComment).filter(
        OverdueRevalidationComment.validation_request_id == request_id,
        OverdueRevalidationComment.is_current == True
    ).first()

    if not current_comment:
        return {
            "comment_status": "MISSING",
            "latest_comment": None,
            "latest_comment_date": None,
            "target_date_from_comment": None,
            "stale_reason": None,
            "needs_comment_update": True
        }

    # Check staleness
    today = date.today()
    # Use timezone-aware datetime to match the database field
    now_utc = datetime.now(timezone.utc)
    # Make comparison timezone-aware
    created_at = current_comment.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    comment_age = (now_utc - created_at).days
    is_stale = False
    stale_reason = None

    if comment_age > COMMENT_STALENESS_DAYS:
        is_stale = True
        stale_reason = f"Comment is {comment_age} days old (exceeds {COMMENT_STALENESS_DAYS}-day freshness requirement)"
    elif current_comment.target_date < today:
        is_stale = True
        days_past = (today - current_comment.target_date).days
        stale_reason = f"Target date has passed ({days_past} days ago) - update required"

    return {
        "comment_status": "STALE" if is_stale else "CURRENT",
        "latest_comment": current_comment.reason_comment,
        "latest_comment_date": current_comment.created_at.isoformat() if current_comment.created_at else None,
        "target_date_from_comment": current_comment.target_date,
        "stale_reason": stale_reason,
        "needs_comment_update": is_stale
    }


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
    from app.models import Model, ValidationPolicy, ModelVersion
    from app.models.validation import validation_request_models
    from datetime import timedelta

    warnings = []
    target_date = request_data.target_completion_date
    model_versions_dict = request_data.model_versions or {}

    # NOTE: Lead time is now per-model from ValidationPolicy.model_change_lead_time_days

    # Load models with their versions
    models = db.query(Model).filter(
        Model.model_id.in_(request_data.model_ids)).all()

    for model in models:
        version_id = model_versions_dict.get(model.model_id)
        version = None

        if version_id:
            version = db.query(ModelVersion).filter(
                ModelVersion.version_id == version_id).first()

        # Check 1: Lead time violation
        # If validation completes before production but with insufficient lead time
        if version and version.production_date and target_date <= version.production_date:
            # Get policy for this model's risk tier
            if model.risk_tier_id:
                policy = db.query(ValidationPolicy).filter(
                    ValidationPolicy.risk_tier_id == model.risk_tier_id
                ).first()
                if policy and policy.model_change_lead_time_days:
                    days_before_production = (version.production_date - target_date).days
                    if days_before_production < policy.model_change_lead_time_days:
                        warnings.append(ValidationWarning(
                            warning_type="LEAD_TIME",
                            severity="WARNING",
                            model_id=model.model_id,
                            model_name=model.model_name,
                            version_number=version.version_number,
                            message=f"Target completion date ({target_date.isoformat()}) provides only {days_before_production} days lead time before implementation ({version.production_date.isoformat()}). Policy requires {policy.model_change_lead_time_days} days.",
                            details={
                                "implementation_date": version.production_date.isoformat(),
                                "target_completion_date": target_date.isoformat(),
                                "actual_lead_time_days": days_before_production,
                                "required_lead_time_days": policy.model_change_lead_time_days
                            }
                        ))

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


def check_change_validation_blockers(
    db: Session,
    validation_type_id: int,
    model_ids: List[int],
    model_versions: Optional[Dict[int, Optional[int]]]
) -> List[Dict]:
    """
    Check if CHANGE validation type requirements are met.

    For CHANGE validation requests, each model must be linked to a specific
    model version. If any model lacks a DRAFT version, the user must create
    one first via the model change submission flow.

    Args:
        db: Database session
        validation_type_id: The selected validation type ID
        model_ids: List of model IDs included in the validation request
        model_versions: Optional dict mapping model_id -> version_id

    Returns:
        List of blocker dicts if requirements not satisfied, empty list otherwise.
        Blockers are hard errors that prevent creation (cannot be overridden).
    """
    # Check if validation type is CHANGE
    change_type = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Validation Type",
        TaxonomyValue.code == "CHANGE"
    ).first()

    if not change_type or validation_type_id != change_type.value_id:
        return []  # Not a CHANGE validation, no blockers

    # Import ModelVersion locally (following existing pattern in this file)
    from app.models import ModelVersion

    blockers = []
    model_versions = model_versions or {}

    for model_id in model_ids:
        model = db.query(Model).filter(Model.model_id == model_id).first()
        if not model:
            continue  # Model validation happens elsewhere

        version_id = model_versions.get(model_id)

        # For CHANGE validations, version must be specified
        if version_id is None:
            # Check if model has any DRAFT versions available
            draft_versions = db.query(ModelVersion).filter(
                ModelVersion.model_id == model_id,
                ModelVersion.status == "DRAFT"
            ).all()

            if not draft_versions:
                blockers.append({
                    "type": "NO_DRAFT_VERSION",
                    "severity": "ERROR",
                    "model_id": model_id,
                    "model_name": model.model_name,
                    "message": f"Model '{model.model_name}' has no DRAFT version. "
                               f"Submit a model change first to create a version for validation."
                })
            else:
                blockers.append({
                    "type": "MISSING_VERSION_LINK",
                    "severity": "ERROR",
                    "model_id": model_id,
                    "model_name": model.model_name,
                    "message": f"Model '{model.model_name}' must be linked to a specific "
                               f"version for CHANGE validations.",
                    "available_versions": [
                        {"version_id": v.version_id, "version_number": v.version_number}
                        for v in draft_versions
                    ]
                })

    return blockers


def _validate_region_scope(
    models: List[Model],
    region_ids: List[int],
    regions: List["Region"]
) -> None:
    """Ensure selected region scope is valid for all models."""
    if not region_ids:
        return

    region_labels = {
        region.region_id: region.code or region.name or str(region.region_id)
        for region in regions
    }
    conflicts: List[str] = []

    for model in models:
        deployed_region_ids = {mr.region_id for mr in model.model_regions or []}
        missing_region_ids = [
            region_id for region_id in region_ids
            if region_id not in deployed_region_ids
        ]
        if missing_region_ids:
            missing_labels = ", ".join(
                region_labels.get(region_id, str(region_id))
                for region_id in missing_region_ids
            )
            conflicts.append(
                f"{model.model_name} (ID {model.model_id}): {missing_labels}"
            )

    if conflicts:
        raise HTTPException(
            status_code=400,
            detail=(
                "Selected region scope includes regions where one or more models "
                "are not deployed. Remove ineligible regions or models. Conflicts: "
                + "; ".join(conflicts)
            ),
        )


def find_prior_validation_for_models(
    db: Session,
    model_ids: List[int],
    validation_type_codes: Optional[List[str]] = None
) -> Optional[int]:
    """
    Find the most recent APPROVED validation request for any of the given models.

    Args:
        db: Database session
        model_ids: List of model IDs to search for
        validation_type_codes: Optional list of validation type codes to filter by
                              (e.g., ['INITIAL', 'COMPREHENSIVE'])

    Returns:
        The request_id of the most recent matching validation, or None if not found.
    """
    # Get the APPROVED status value
    approved_status = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code == "APPROVED"
    ).first()

    if not approved_status:
        return None

    # Build the query - find validation requests linked to these models
    query = db.query(ValidationRequest).join(
        ValidationRequestModelVersion,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequestModelVersion.model_id.in_(model_ids),
        ValidationRequest.current_status_id == approved_status.value_id
    )

    # Filter by validation type if specified
    if validation_type_codes:
        type_values = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Validation Type",
            TaxonomyValue.code.in_(validation_type_codes)
        ).all()
        type_ids = [tv.value_id for tv in type_values]
        if type_ids:
            query = query.filter(ValidationRequest.validation_type_id.in_(type_ids))
        else:
            return None

    # Order by completion_date (most recent first), fall back to updated_at
    # Use nullslast to push NULL completion_dates to the end
    prior_validation = query.order_by(
        nullslast(desc(ValidationRequest.completion_date)),
        desc(ValidationRequest.updated_at)
    ).first()

    return prior_validation.request_id if prior_validation else None


def find_models_with_prior_full_validation(
    db: Session,
    model_ids: List[int]
) -> List[Dict[str, Any]]:
    """Return models that already have an APPROVED full validation."""
    if not model_ids:
        return []

    approved_status = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code == "APPROVED"
    ).first()
    if not approved_status:
        return []

    full_type_values = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Validation Type",
        TaxonomyValue.code.in_(FULL_PLAN_VALIDATION_TYPES)
    ).all()
    if not full_type_values:
        return []

    full_type_ids = [value.value_id for value in full_type_values]

    rows = db.query(
        Model.model_id,
        Model.model_name
    ).join(
        ValidationRequestModelVersion,
        ValidationRequestModelVersion.model_id == Model.model_id
    ).join(
        ValidationRequest,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        Model.model_id.in_(model_ids),
        ValidationRequest.current_status_id == approved_status.value_id,
        ValidationRequest.validation_type_id.in_(full_type_ids)
    ).distinct().all()

    return [
        {"model_id": row.model_id, "model_name": row.model_name}
        for row in rows
    ]


def _validate_initial_validation_eligibility(
    db: Session,
    model_ids: List[int]
) -> None:
    """Block INITIAL validations when any model has a prior full validation."""
    prior_models = find_models_with_prior_full_validation(db, model_ids)
    if not prior_models:
        return

    conflicts = ", ".join(
        f"{model['model_name']} (ID {model['model_id']})"
        for model in prior_models
    )
    raise HTTPException(
        status_code=400,
        detail=(
            "Initial validations are only allowed for models without a prior full "
            "validation (Initial or Comprehensive). Conflicts: "
            f"{conflicts}."
        )
    )


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
        "PENDING_APPROVAL": ["APPROVED", "REVISION", "REVIEW", "IN_PROGRESS", "CANCELLED", "ON_HOLD"],
        "REVISION": ["PENDING_APPROVAL", "CANCELLED", "ON_HOLD"],  # Sent back for revisions
        "APPROVED": [],  # Terminal state
        "ON_HOLD": ["INTAKE", "PLANNING", "IN_PROGRESS", "REVIEW", "PENDING_APPROVAL", "REVISION", "CANCELLED"],
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
    change_reason: Optional[str] = None,
    additional_context: Optional[str] = None
):
    """Create a status history entry."""
    history = ValidationStatusHistory(
        request_id=request_id,
        old_status_id=old_status_id,
        new_status_id=new_status_id,
        changed_by_id=changed_by_id,
        change_reason=change_reason,
        additional_context=additional_context,
        changed_at=utc_now()
    )
    db.add(history)
    return history


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
        delta = utc_now() - latest_history.changed_at
        return delta.days
    else:
        # If no history, use creation date
        delta = utc_now() - request.created_at
        return delta.days


def update_grouping_memory(db: Session, validation_request: ValidationRequest, models: List[Model]):
    """Update validation grouping memory for multi-model regular validations.

    Only updates for regular validations (INITIAL, COMPREHENSIVE).
    Skips targeted validations (TARGETED, INTERIM).
    Only updates if 2 or more models are being validated together.
    """
    # Regular validation type codes that should update grouping memory
    REGULAR_VALIDATION_TYPES = ["INITIAL", "COMPREHENSIVE"]

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
            existing_memory.updated_at = utc_now()
        else:
            # Create new record
            new_memory = ValidationGroupingMemory(
                model_id=model.model_id,
                last_validation_request_id=validation_request.request_id,
                grouped_model_ids=json.dumps(other_model_ids),
                is_regular_validation=True,
                updated_at=utc_now()
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


def _get_request_models(validation_request: ValidationRequest) -> List[Model]:
    models = [assoc.model for assoc in validation_request.model_versions_assoc if assoc.model]
    if models:
        return models
    return list(validation_request.models or [])


def get_primary_model_from_models(models: List[Model]) -> Optional[Model]:
    """Primary model uses stable MIN(model_id)."""
    if not models:
        return None
    return min(models, key=lambda model: model.model_id)


def compute_required_approval_scope(
    validation_request: ValidationRequest
) -> Tuple[bool, Set[int]]:
    """
    Compute approval scope using the same region-selection logic as auto_assign_approvers.

    Returns (requires_global, required_region_ids).
    Global approvals are always required per business rule, but this flag is retained
    for future flexibility and for symmetry with regional scope calculations.
    """
    requires_global = True
    required_region_ids: Set[int] = set()

    models = _get_request_models(validation_request)
    if not models:
        return requires_global, required_region_ids

    # Collect governance regions (wholly_owned_region_id) - always required
    governance_region_ids = set()
    for model in models:
        if model.wholly_owned_region_id is not None:
            governance_region_ids.add(model.wholly_owned_region_id)

    # Collect all deployment regions (used as fallback for global scope)
    all_deployment_region_ids = set()
    for model in models:
        for model_region in model.model_regions:
            all_deployment_region_ids.add(model_region.region_id)

    # 1. Explicit scoped regions (user override)
    scoped_region_ids = set()
    for region in validation_request.regions:
        scoped_region_ids.add(region.region_id)

    # 2. Analyze linked model versions for scope
    has_global_version = False
    version_region_ids = set()

    for assoc in validation_request.model_versions_assoc:
        if assoc.version:
            if assoc.version.scope == "REGIONAL":
                for region in assoc.version.affected_regions:
                    version_region_ids.add(region.region_id)
            else:
                has_global_version = True

    # 3. Determine final approval regions using priority hierarchy
    if scoped_region_ids:
        required_region_ids = scoped_region_ids | version_region_ids
    elif has_global_version:
        required_region_ids = all_deployment_region_ids | governance_region_ids
    elif version_region_ids:
        required_region_ids = version_region_ids.copy()
    else:
        required_region_ids = all_deployment_region_ids.copy()

    # 4. Always include governance regions (for wholly-owned models)
    required_region_ids |= governance_region_ids

    return requires_global, required_region_ids


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
    from app.models.user import user_regions
    from app.core.roles import RoleCode

    approvals_to_create = []
    assigned_approver_ids = set()  # Track to avoid duplicates

    # Check for existing ACTIVE Global/Regional approvals to make this function idempotent
    # This is important when re-evaluating approvers at PENDING_APPROVAL transition
    # IMPORTANT: Ignore voided approvals - they've been invalidated and new ones should be created
    existing_approvals = db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation_request.request_id,
        ValidationApproval.approval_type.in_(["Global", "Regional"]),
        ValidationApproval.voided_by_id.is_(None)  # Only active approvals
    ).all()

    for existing in existing_approvals:
        if existing.approver_id:
            assigned_approver_ids.add(existing.approver_id)

    # Determine required regions using shared scope helper
    _, all_region_ids = compute_required_approval_scope(validation_request)

    if validation_request.models and len(validation_request.models) > 0:
        # Business Rule: Global Approvers are ALWAYS required for all validations
        # Regional Approvers are required for regions that have requires_regional_approval=True

        # 1. ALWAYS assign Global Approvers
        global_approvers = db.query(User).filter(
            User.role_code == RoleCode.GLOBAL_APPROVER.value
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
                    created_at=utc_now()
                ))
                assigned_approver_ids.add(approver.user_id)

        # 2. Assign Regional Approvers for all relevant regions that require approval
        for region_id in all_region_ids:
            region = db.query(Region).filter(
                Region.region_id == region_id).first()
            if region and region.requires_regional_approval:
                regional_approvers = db.query(User).join(user_regions).filter(
                    User.role_code == RoleCode.REGIONAL_APPROVER.value,
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
                            created_at=utc_now()
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
            timestamp=utc_now()
        )
        db.add(audit_log)


def evaluate_and_create_conditional_approvals(
    db: Session,
    validation_request: ValidationRequest,
    model: Model
):
    """
    Evaluate conditional approval rules and create ValidationApproval records
    for each required approver role.

    This function is called:
    1. When a validation request is created
    2. When a validation request moves to "Pending Approval" status (to handle null risk tiers)

    Args:
        db: Database session
        validation_request: The validation request being evaluated
        model: The primary model being validated (or first model if multi-model)
    """
    # Evaluate rules and get required approver roles
    evaluation_result = get_required_approver_roles(
        db, validation_request, model)

    # If no roles required, nothing to do
    if not evaluation_result["required_roles"]:
        return

    # For each required role, create or update ValidationApproval record
    for required_role in evaluation_result["required_roles"]:
        role_id = required_role["role_id"]
        existing_approval = required_role.get("approval_id")

        # If approval already exists (and not voided), skip
        if existing_approval:
            continue

        # Create new conditional approval requirement
        approval = ValidationApproval(
            request_id=validation_request.request_id,
            approver_role_id=role_id,
            approver_id=None,  # Will be set when Admin submits approval
            approver_role="Conditional",
            approval_type="Conditional",
            approval_status="Pending",
            is_required=True,
            comments=f"Additional approval required from {required_role['role_name']}",
            created_at=utc_now()
        )
        db.add(approval)


# ==================== MODEL UPDATE HELPERS ====================

def sync_approvals_for_scope_change(
    db: Session,
    validation_request: ValidationRequest,
    pre_scope: Tuple[bool, Set[int]],
    current_user: User
) -> Tuple[int, int]:
    """
    Sync Global/Regional approvals when approval scope changes.

    Returns (added_count, voided_count).
    """
    _pre_requires_global, _pre_region_ids = pre_scope
    post_requires_global, post_region_ids = compute_required_approval_scope(validation_request)

    active_approvals = db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation_request.request_id,
        ValidationApproval.approval_type.in_(["Global", "Regional"]),
        ValidationApproval.voided_at.is_(None)
    ).all()

    voided_count = 0
    for approval in active_approvals:
        if approval.approval_type == "Global" and not post_requires_global:
            approval.voided_by_id = current_user.user_id
            approval.void_reason = "Approval no longer required after model scope change"
            approval.voided_at = utc_now()
            voided_count += 1
        elif approval.approval_type == "Regional" and approval.region_id not in post_region_ids:
            approval.voided_by_id = current_user.user_id
            approval.void_reason = "Regional approval no longer required after model scope change"
            approval.voided_at = utc_now()
            voided_count += 1

    db.flush()

    before_active = db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation_request.request_id,
        ValidationApproval.approval_type.in_(["Global", "Regional"]),
        ValidationApproval.voided_at.is_(None)
    ).count()

    auto_assign_approvers(db, validation_request, current_user)

    after_active = db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation_request.request_id,
        ValidationApproval.approval_type.in_(["Global", "Regional"]),
        ValidationApproval.voided_at.is_(None)
    ).count()

    added_count = max(0, after_active - max(0, before_active - voided_count))
    return added_count, voided_count


def sync_conditional_approvals(
    db: Session,
    validation_request: ValidationRequest,
    current_user: User
) -> Tuple[int, int]:
    """
    Re-evaluate conditional approvals against the updated model set.

    Returns (added_count, voided_count).
    """
    from app.models import ApproverRole

    required_role_ids: Set[int] = set()
    for model in _get_request_models(validation_request):
        result = get_required_approver_roles(db, validation_request, model)
        required_role_ids.update(r["role_id"] for r in result.get("required_roles", []))

    existing = db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation_request.request_id,
        ValidationApproval.approval_type == "Conditional",
        ValidationApproval.voided_at.is_(None)
    ).all()

    existing_by_role = {a.approver_role_id: a for a in existing if a.approver_role_id}

    added_count = 0
    for role_id in required_role_ids:
        if role_id not in existing_by_role:
            role = db.query(ApproverRole).filter(ApproverRole.role_id == role_id).first()
            db.add(ValidationApproval(
                request_id=validation_request.request_id,
                approver_role_id=role_id,
                approver_role="Conditional",
                approval_type="Conditional",
                approval_status="Pending",
                is_required=True,
                comments=f"Additional approval required from {role.role_name}" if role else None,
                created_at=utc_now()
            ))
            added_count += 1

    voided_count = 0
    for approval in existing:
        if approval.approver_role_id not in required_role_ids and approval.approval_status == "Pending":
            approval.voided_by_id = current_user.user_id
            approval.void_reason = "Conditional approval no longer required after model change"
            approval.voided_at = utc_now()
            voided_count += 1

    return added_count, voided_count


def flag_plan_deviations_for_tier_change(
    db: Session,
    validation_request: ValidationRequest
) -> int:
    """
    Update plan components when the most conservative tier changes.

    Recalculates default_expectation and is_deviation while preserving planned_treatment.
    Returns count of components newly flagged as deviations.
    """
    if not validation_request.validation_plan:
        return 0

    validation_type_code = validation_request.validation_type.code if validation_request.validation_type else None
    if validation_type_code in SCOPE_ONLY_VALIDATION_TYPES:
        return 0

    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components).joinedload(
            ValidationPlanComponent.component_definition)
    ).filter(ValidationPlan.request_id == validation_request.request_id).first()
    if not plan:
        return 0

    tier_hierarchy = {"TIER_1": 1, "TIER_2": 2, "TIER_3": 3, "TIER_4": 4}
    most_conservative = "TIER_2"
    highest_risk = 4

    for model_assoc in validation_request.model_versions_assoc:
        model = model_assoc.model
        if model and model.risk_tier and model.risk_tier.code:
            tier_code = model.risk_tier.code
            risk_level = tier_hierarchy.get(tier_code, 2)
            if risk_level < highest_risk:
                highest_risk = risk_level
                most_conservative = tier_code

    flagged = 0
    for component in plan.components:
        comp_def = component.component_definition
        new_expectation = get_expectation_for_tier(comp_def, most_conservative)

        component.default_expectation = new_expectation
        new_is_deviation = calculate_is_deviation(
            new_expectation, component.planned_treatment
        )
        if new_is_deviation and not component.is_deviation:
            flagged += 1
        component.is_deviation = new_is_deviation

    return flagged


def log_model_change_audit(
    db: Session,
    validation_request: ValidationRequest,
    update_data: ValidationRequestModelUpdate,
    current_user: User,
    validators_unassigned: Optional[List[str]] = None,
    approvals_voided: Optional[int] = None,
    conditional_voided: Optional[int] = None
) -> None:
    """Create audit log entry for model add/remove operations."""
    changes = {
        "models_added": [entry.model_id for entry in (update_data.add_models or [])],
        "models_removed": list(update_data.remove_model_ids or []),
        "validators_unassigned": validators_unassigned or [],
        "approvals_voided": approvals_voided or 0,
        "conditional_approvals_voided": conditional_voided or 0
    }

    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=validation_request.request_id,
        action="UPDATE_MODELS",
        user_id=current_user.user_id,
        changes=changes,
        timestamp=utc_now()
    )
    db.add(audit_log)

# ==================== REVALIDATION LIFECYCLE HELPERS ====================


def _format_validation_summary(validation: Optional[ValidationRequest]) -> Optional[Dict]:
    """Format a validation request for the key dates summary."""
    if not validation:
        return None
    approval_date = (validation.completion_date.date() if validation.completion_date
                     else validation.updated_at.date())
    return {
        "request_id": validation.request_id,
        "approval_date": approval_date.isoformat(),
        "validation_type": validation.validation_type.label if validation.validation_type else "Unknown"
    }


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

    # Query INITIAL/COMPREHENSIVE validations for key dates summary
    # These are the "full" validations that reset the revalidation cycle
    full_validations = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.current_status.has(TaxonomyValue.code == "APPROVED"),
        ValidationRequest.validation_type.has(
            TaxonomyValue.code.in_(["INITIAL", "COMPREHENSIVE"])
        )
    ).order_by(
        ValidationRequest.completion_date.desc().nullslast(),
        ValidationRequest.updated_at.desc()
    ).limit(2).all()

    most_recent_full = full_validations[0] if len(full_validations) > 0 else None
    previous_full = full_validations[1] if len(full_validations) > 1 else None

    # Query INTERIM validation for fallback dates if no full validation
    interim_expiration = None
    if not most_recent_full:
        interim_validation = db.query(ValidationRequest).join(
            ValidationRequestModelVersion
        ).outerjoin(
            ValidationOutcome, ValidationRequest.request_id == ValidationOutcome.request_id
        ).filter(
            ValidationRequestModelVersion.model_id == model.model_id,
            ValidationRequest.current_status.has(TaxonomyValue.code == "APPROVED"),
            ValidationRequest.validation_type.has(TaxonomyValue.code == "INTERIM"),
            ValidationOutcome.expiration_date.isnot(None)
        ).order_by(
            ValidationOutcome.expiration_date.desc()
        ).first()

        if interim_validation and interim_validation.outcome:
            interim_expiration = interim_validation.outcome.expiration_date

    if not last_validation:
        # Check for INTERIM-derived dates
        today = date.today()
        interim_submission_due = None
        interim_validation_due = None

        if interim_expiration:
            # Get policy for lead_time calculation
            policy = db.query(ValidationPolicy).filter(
                ValidationPolicy.risk_tier_id == model.risk_tier_id
            ).first()
            if policy:
                interim_submission_due = interim_expiration - timedelta(days=policy.model_change_lead_time_days)
                interim_validation_due = interim_expiration

        return {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "model_owner": model.owner.full_name if model.owner else "Unknown",
            "risk_tier": model.risk_tier.label if model.risk_tier else None,
            "status": "Pending Full Validation" if interim_expiration else "Never Validated",
            "last_validation_date": None,
            "next_submission_due": interim_submission_due,
            "grace_period_end": None,
            "next_validation_due": interim_validation_due,
            "days_until_submission_due": (interim_submission_due - today).days if interim_submission_due else None,
            "days_until_validation_due": (interim_validation_due - today).days if interim_validation_due else None,
            "active_request_id": None,
            "submission_received": None,
            "interim_expiration": interim_expiration.isoformat() if interim_expiration else None,
            "most_recent_validation": _format_validation_summary(most_recent_full),
            "previous_validation": _format_validation_summary(previous_full)
        }

    # Get validation policy for this model's risk tier
    policy = db.query(ValidationPolicy).filter(
        ValidationPolicy.risk_tier_id == model.risk_tier_id
    ).first()

    if not policy:
        # Even without a policy, if we have interim_expiration, use it as the hard deadline
        today = date.today()
        # Use completion_date (approval date) for cycle calculation, fallback to updated_at
        approval_date = last_validation.completion_date.date() if last_validation.completion_date else last_validation.updated_at.date()
        return {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "model_owner": model.owner.full_name if model.owner else "Unknown",
            "risk_tier": model.risk_tier.label if model.risk_tier else None,
            "status": "No Policy Configured",
            "last_validation_date": approval_date,
            "next_submission_due": None,
            "grace_period_end": None,
            "next_validation_due": interim_expiration,  # Use interim expiration as deadline
            "days_until_submission_due": None,
            "days_until_validation_due": (interim_expiration - today).days if interim_expiration else None,
            "active_request_id": None,
            "submission_received": None,
            "interim_expiration": interim_expiration.isoformat() if interim_expiration else None,
            "most_recent_validation": _format_validation_summary(most_recent_full),
            "previous_validation": _format_validation_summary(previous_full)
        }

    # Calculate dates
    # Use completion_date (approval date) for cycle calculation, fallback to updated_at
    approval_date = last_validation.completion_date.date() if last_validation.completion_date else last_validation.updated_at.date()

    # If we have an INTERIM expiration but no full validation, use INTERIM dates instead
    if interim_expiration and not most_recent_full:
        # INTERIM expiration is the hard deadline
        lead_time_days = policy.model_change_lead_time_days
        submission_due = interim_expiration - timedelta(days=lead_time_days)
        grace_period_end = None  # No grace period for INTERIM - expiration is absolute
        validation_due = interim_expiration
        last_completed = approval_date
        active_request = None  # Don't look for COMPREHENSIVE request linked to INTERIM
    else:
        # Standard calculation from last full validation
        last_completed = approval_date
        submission_due = last_completed + \
            relativedelta(months=policy.frequency_months)
        grace_period_end = submission_due + relativedelta(months=policy.grace_period_months)

        # Check if active revalidation request exists
        active_request = db.query(ValidationRequest).join(
            ValidationRequestModelVersion
        ).filter(
            ValidationRequestModelVersion.model_id == model.model_id,
            ValidationRequest.validation_type.has(
                TaxonomyValue.code == "COMPREHENSIVE"),
            ValidationRequest.prior_validation_request_id == last_validation.request_id,
            ValidationRequest.current_status.has(
                TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"]))
        ).first()

        # Calculate validation_due:
        # Total lead time = completion_lead_time + workflow SLA periods (assignment + begin_work + approval)
        # - If active_request exists (potentially multi-model), use request's applicable_lead_time_days
        #   which is MAX across all models' policies (most conservative)
        # - If no active_request, use this model's policy (for calculating when request should be created)
        if active_request:
            completion_lead_time = active_request.applicable_lead_time_days
        else:
            completion_lead_time = policy.model_change_lead_time_days

        # Add workflow SLA periods (assignment, begin_work, approval)
        workflow_sla = db.query(ValidationWorkflowSLA).filter(
            ValidationWorkflowSLA.workflow_type == "Validation"
        ).first()
        sla_days = 0
        if workflow_sla:
            sla_days = (workflow_sla.assignment_days or 0) + \
                       (workflow_sla.begin_work_days or 0) + \
                       (workflow_sla.approval_days or 0)

        total_lead_time = completion_lead_time + sla_days
        validation_due = grace_period_end + timedelta(days=total_lead_time)

    today = date.today()

    # Determine status
    # For INTERIM (no full validation), grace_period_end is None - use different logic
    if interim_expiration and not most_recent_full:
        # INTERIM case: simpler status based on expiration
        if today > validation_due:
            status = "INTERIM Expired - Full Validation Required"
        elif today > submission_due:
            status = "Submission Overdue (INTERIM)"
        else:
            status = "Pending Full Validation"
    elif active_request:
        if not active_request.submission_received_date:
            if grace_period_end and today > grace_period_end:
                status = "Submission Overdue"
            elif submission_due and today > submission_due:
                status = "In Grace Period"
            else:
                status = "Awaiting Submission"
        else:
            if validation_due and today > validation_due:
                status = "Validation Overdue"
            else:
                status = "Validation In Progress"
    else:
        # No active request - standard revalidation lifecycle
        if validation_due and today > validation_due:
            status = "Revalidation Overdue (No Request)"
        elif grace_period_end and today > grace_period_end:
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
        "submission_received": active_request.submission_received_date if active_request else None,
        "interim_expiration": interim_expiration.isoformat() if interim_expiration else None,
        "most_recent_validation": _format_validation_summary(most_recent_full),
        "previous_validation": _format_validation_summary(previous_full)
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
            # Only include truly upcoming items (positive days) within the look-ahead window
            if 0 < revalidation_status["days_until_submission_due"] <= days_ahead:
                results.append(revalidation_status)

    # Sort by submission due date (None values go to end)
    results.sort(key=lambda x: x["next_submission_due"]
                 if x["next_submission_due"] else date.max)

    return results


# ==================== USER LOOKUP ENDPOINTS ====================

@router.get("/assignable-validators", response_model=List[AssignableValidatorResponse])
def get_assignable_validators(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List users eligible for validator assignments (Admin/Validator only)."""
    check_validator_or_admin(current_user)
    validators = db.query(User).options(
        joinedload(User.role_ref)
    ).filter(
        User.role_code.in_([RoleCode.ADMIN.value, RoleCode.VALIDATOR.value])
    ).order_by(User.full_name.asc()).all()
    return validators


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


VALIDATION_LOCK_NAMESPACE = 42


def _acquire_validation_locks(db: Session, model_ids: List[int]) -> None:
    """Acquire advisory locks for validation creation in a deterministic order."""
    bind = db.get_bind()
    if not bind or bind.dialect.name != "postgresql":
        return
    for model_id in sorted(model_ids):
        db.execute(
            text("SELECT pg_advisory_xact_lock(:namespace, :model_id)"),
            {"namespace": VALIDATION_LOCK_NAMESPACE, "model_id": model_id},
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

    Only Admins and Validators can create validation requests.
    """
    check_validator_or_admin(current_user)

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

    # Verify validation type exists
    validation_type = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == request_data.validation_type_id
    ).first()
    if not validation_type:
        raise HTTPException(
            status_code=404, detail="Validation type not found")

    if validation_type.code == "INITIAL":
        _validate_initial_validation_eligibility(db, request_data.model_ids)

    conflicts = find_active_validation_conflicts(
        db,
        request_data.model_ids,
        validation_type.code
    )
    if conflicts:
        raise HTTPException(
            status_code=400,
            detail=build_validation_conflict_message(conflicts, validation_type.code)
        )

    # Verify regions if provided
    regions = []
    if request_data.region_ids:
        from app.models import Region
        regions = db.query(Region).filter(
            Region.region_id.in_(request_data.region_ids)).all()
        if len(regions) != len(request_data.region_ids):
            raise HTTPException(
                status_code=404, detail="One or more regions not found")
        _validate_region_scope(models, request_data.region_ids, regions)

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

    # Check for warnings even when not explicitly requested
    # This enforces business rules about lead times and implementation dates
    warnings = check_target_completion_date_warnings(db, request_data)
    if warnings:
        has_errors = any(w.severity == "ERROR" for w in warnings)

        # If there are ERRORs, block creation regardless of force_create
        if has_errors:
            return ValidationRequestWarningsResponse(
                has_warnings=True,
                can_proceed=False,
                warnings=warnings,
                request_data=request_data
            )

        # If only WARNINGs exist and force_create is False, return warnings for user decision
        if not request_data.force_create:
            return ValidationRequestWarningsResponse(
                has_warnings=True,
                can_proceed=True,
                warnings=warnings,
                request_data=request_data
            )

        # If force_create is True and only warnings, proceed with creation

    # Check CHANGE validation type requirements (version linking)
    change_blockers = check_change_validation_blockers(
        db=db,
        validation_type_id=request_data.validation_type_id,
        model_ids=request_data.model_ids,
        model_versions=request_data.model_versions
    )
    if change_blockers:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Cannot create CHANGE validation without linking to model versions",
                "blockers": change_blockers
            }
        )

    # Acquire advisory locks to prevent concurrent conflicting requests
    _acquire_validation_locks(db, request_data.model_ids)

    # Re-check conflicts under lock to prevent races
    conflicts = find_active_validation_conflicts(
        db,
        request_data.model_ids,
        validation_type.code
    )
    if conflicts:
        raise HTTPException(
            status_code=400,
            detail=build_validation_conflict_message(conflicts, validation_type.code)
        )

    # Verify priority exists
    priority = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == request_data.priority_id
    ).first()
    if not priority:
        raise HTTPException(status_code=404, detail="Priority not found")

    # Get initial status (INTAKE)
    intake_status = get_taxonomy_value_by_code(
        db, "Validation Request Status", "INTAKE")

    # Auto-populate prior_validation_request_id if not provided
    # Links to the most recent APPROVED validation for these models
    prior_validation_id = request_data.prior_validation_request_id
    if not prior_validation_id:
        prior_validation_id = find_prior_validation_for_models(
            db, request_data.model_ids
        )

    # Auto-populate prior_full_validation_request_id
    # Links to the most recent APPROVED INITIAL or COMPREHENSIVE validation
    prior_full_validation_id = find_prior_validation_for_models(
        db, request_data.model_ids,
        validation_type_codes=['INITIAL', 'COMPREHENSIVE']
    )

    # Create the request
    validation_request = ValidationRequest(
        request_date=date.today(),
        requestor_id=current_user.user_id,
        validation_type_id=request_data.validation_type_id,
        priority_id=request_data.priority_id,
        target_completion_date=request_data.target_completion_date,
        trigger_reason=request_data.trigger_reason,
        external_project_id=request_data.external_project_id,
        current_status_id=intake_status.value_id,
        prior_validation_request_id=prior_validation_id,
        prior_full_validation_request_id=prior_full_validation_id,
        created_at=utc_now(),
        updated_at=utc_now()
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

    # ===== DUE DATE OVERRIDE: PROMOTE NEXT_CYCLE TO CURRENT_REQUEST =====
    # If there's an active NEXT_CYCLE override for any of these models,
    # promote it to CURRENT_REQUEST and link it to this new validation
    for model in models:
        promote_next_cycle_override(
            db, model.model_id, validation_request.request_id, current_user.user_id
        )

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
        timestamp=utc_now()
    )
    db.add(audit_log)

    # Update grouping memory for multi-model regular validations
    update_grouping_memory(db, validation_request, models)

    # Auto-assign approvers based on validation scope (Phase 5)
    auto_assign_approvers(db, validation_request, current_user)

    # Evaluate conditional approval rules and create approval requirements
    primary_model = get_primary_model_from_models(models)
    if primary_model:
        evaluate_and_create_conditional_approvals(
            db, validation_request, primary_model)

    # ===== UPDATE MODEL APPROVAL STATUS =====
    # When a validation request is created, models transition to VALIDATION_IN_PROGRESS
    from app.core.model_approval_status import update_model_approval_status_if_changed
    for model in models:
        update_model_approval_status_if_changed(
            model=model,
            db=db,
            trigger_type="VALIDATION_REQUEST_CREATED",
            trigger_entity_type="ValidationRequest",
            trigger_entity_id=validation_request.request_id,
            notes=f"Validation request created with status: Intake"
        )

    db.commit()

    # Reload with relationships (including approvals with their approver)
    db.refresh(validation_request)
    validation_request_with_approvals = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.approvals).joinedload(
            ValidationApproval.approver),
        joinedload(ValidationRequest.approvals).joinedload(
            ValidationApproval.assigned_approver),
        joinedload(ValidationRequest.approvals).joinedload(
            ValidationApproval.manually_added_by)
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
        # Eager-load for days_in_status calculation
        joinedload(ValidationRequest.status_history),
        # Eager-load model_versions_assoc for applicable_lead_time_days calculation
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model)
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
            query = query.filter(
                ValidationRequestModelVersion.model_id == model_id)
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

    # Fetch approval SLA days (for forecasted approval date)
    approval_days = None
    workflow_sla = db.query(ValidationWorkflowSLA).filter(
        ValidationWorkflowSLA.workflow_type == "Validation"
    ).first()
    if workflow_sla:
        approval_days = workflow_sla.approval_days

    # Fetch current overdue commentary for these requests
    request_ids = [req.request_id for req in requests]
    current_comments: dict[int, OverdueRevalidationComment] = {}
    if request_ids:
        comments = db.query(OverdueRevalidationComment).filter(
            OverdueRevalidationComment.validation_request_id.in_(request_ids),
            OverdueRevalidationComment.is_current == True
        ).all()
        current_comments = {comment.validation_request_id: comment for comment in comments}

    # Transform to list response format
    result = []
    for req in requests:
        primary_validator = next(
            (a.validator.full_name for a in req.assignments if a.is_primary),
            None
        )
        current_comment = current_comments.get(req.request_id)
        commentary_target_date = current_comment.target_date if current_comment else None
        if req.submission_received_date:
            current_forecast_date = commentary_target_date or req.target_completion_date
        else:
            current_forecast_date = (
                commentary_target_date + timedelta(days=req.applicable_lead_time_days)
                if commentary_target_date
                else req.target_completion_date
            )

        forecasted_approval_date = None
        if current_forecast_date and approval_days is not None:
            forecasted_approval_date = current_forecast_date + timedelta(days=approval_days)

        result.append(ValidationRequestListResponse(
            request_id=req.request_id,
            model_ids=[m.model_id for m in req.models],
            model_names=[m.model_name for m in req.models],
            request_date=req.request_date,
            requestor_name=req.requestor.full_name,
            validation_type=req.validation_type.label,
            priority=req.priority.label,
            target_completion_date=req.target_completion_date,
            current_forecast_date=current_forecast_date,
            forecasted_approval_date=forecasted_approval_date,
            external_project_id=req.external_project_id,
            current_status=req.current_status.label,
            days_in_status=calculate_days_in_status(req),
            primary_validator=primary_validator,
            regions=req.regions if req.regions else [],
            created_at=req.created_at,
            updated_at=req.updated_at,
            completion_date=req.completion_date,
            applicable_lead_time_days=req.applicable_lead_time_days,
            model_compliance_status=req.model_compliance_status
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
        joinedload(ValidationRequest.approvals).joinedload(
            ValidationApproval.assigned_approver),
        joinedload(ValidationRequest.approvals).joinedload(
            ValidationApproval.manually_added_by),
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
        joinedload(ValidationRequest.models).joinedload(Model.model_regions),
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

    if "validation_type_id" in update_dict:
        new_validation_type_id = update_dict["validation_type_id"]
        if new_validation_type_id != validation_request.validation_type_id:
            new_validation_type = db.query(TaxonomyValue).filter(
                TaxonomyValue.value_id == new_validation_type_id
            ).first()
            if not new_validation_type:
                raise HTTPException(
                    status_code=404, detail="Validation type not found"
                )
            if new_validation_type.code == "INITIAL":
                _validate_initial_validation_eligibility(
                    db,
                    [model.model_id for model in validation_request.models]
                )

    # Handle region_ids separately (many-to-many relationship)
    if 'region_ids' in update_dict:
        from app.models import Region
        new_region_ids = update_dict.pop('region_ids') or []
        old_region_ids = [r.region_id for r in validation_request.regions]

        if set(old_region_ids) != set(new_region_ids):
            # Update regions
            new_regions = db.query(Region).filter(Region.region_id.in_(
                new_region_ids)).all() if new_region_ids else []
            if new_region_ids and len(new_regions) != len(new_region_ids):
                raise HTTPException(
                    status_code=404, detail="One or more regions not found")
            if new_region_ids:
                _validate_region_scope(
                    validation_request.models,
                    new_region_ids,
                    new_regions
                )
            validation_request.regions = new_regions
            changes['region_ids'] = {
                "old": old_region_ids, "new": new_region_ids}

    for field, new_value in update_dict.items():
        old_value = getattr(validation_request, field)
        if old_value != new_value:
            setattr(validation_request, field, new_value)
            changes[field] = {"old": str(old_value), "new": str(new_value)}

    if changes:
        validation_request.updated_at = utc_now()

        audit_log = AuditLog(
            entity_type="ValidationRequest",
            entity_id=request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes,
            timestamp=utc_now()
        )
        db.add(audit_log)

    db.commit()
    db.refresh(validation_request)
    return validation_request


@router.patch("/requests/{request_id}/models", response_model=ValidationRequestModelUpdateResponse)
def update_request_models(
    request_id: int,
    update_data: ValidationRequestModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add or remove models from a validation request during INTAKE or PLANNING."""
    check_validator_or_admin(current_user)

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.assignments).joinedload(ValidationAssignment.validator),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.approver),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.assigned_approver),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.manually_added_by),
        joinedload(ValidationRequest.models).joinedload(Model.model_regions),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model).joinedload(Model.model_regions),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.version)
    ).filter(ValidationRequest.request_id == request_id).first()
    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    status_code = validation_request.current_status.code if validation_request.current_status else None
    if status_code not in ("INTAKE", "PLANNING"):
        raise HTTPException(
            status_code=400,
            detail="Model changes only allowed in Intake or Planning status"
        )

    validation_type_code = validation_request.validation_type.code if validation_request.validation_type else None

    add_entries = update_data.add_models or []
    remove_ids = set(update_data.remove_model_ids or [])

    if not add_entries and not remove_ids:
        lead_time = validation_request.applicable_lead_time_days
        return ValidationRequestModelUpdateResponse(
            success=True,
            models_added=[],
            models_removed=[],
            lead_time_changed=False,
            old_lead_time_days=lead_time,
            new_lead_time_days=lead_time,
            warnings=[],
            plan_deviations_flagged=0,
            approvals_added=0,
            approvals_voided=0,
            conditional_approvals_added=0,
            conditional_approvals_voided=0,
            validators_unassigned=[]
        )

    add_model_ids = [entry.model_id for entry in add_entries]
    if len(add_model_ids) != len(set(add_model_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate model_id entries in add_models"
        )

    overlap = set(add_model_ids) & remove_ids
    if overlap:
        raise HTTPException(
            status_code=400,
            detail="Model IDs cannot be both added and removed in the same update"
        )

    requested_ids = set(add_model_ids) | remove_ids
    models_by_id: Dict[int, Model] = {}
    if requested_ids:
        models = db.query(Model).options(
            joinedload(Model.model_regions)
        ).filter(
            Model.model_id.in_(requested_ids)
        ).all()
        if len(models) != len(requested_ids):
            raise HTTPException(
                status_code=404, detail="One or more models not found")
        models_by_id = {model.model_id: model for model in models}

    if add_entries and validation_request.regions:
        scoped_region_ids = [region.region_id for region in validation_request.regions]
        models_to_check = [models_by_id[entry.model_id] for entry in add_entries]
        _validate_region_scope(models_to_check, scoped_region_ids, validation_request.regions)

    existing_model_ids = {assoc.model_id for assoc in validation_request.model_versions_assoc}

    missing_remove = remove_ids - existing_model_ids
    if missing_remove:
        missing_id = sorted(missing_remove)[0]
        raise HTTPException(
            status_code=400,
            detail=f"Model {missing_id} is not associated with this request"
        )

    for model_id in add_model_ids:
        if model_id in existing_model_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Model {model_id} is already associated"
            )

    if add_model_ids:
        conflicts = find_active_validation_conflicts(
            db,
            add_model_ids,
            validation_type_code,
            exclude_request_id=request_id
        )
        if conflicts:
            raise HTTPException(
                status_code=400,
                detail=build_validation_conflict_message(conflicts, validation_type_code)
            )

    remaining_ids = (existing_model_ids - remove_ids) | set(add_model_ids)
    if not remaining_ids:
        raise HTTPException(
            status_code=400, detail="At least one model must remain")

    if validation_type_code == "INITIAL":
        _validate_initial_validation_eligibility(db, list(remaining_ids))

    is_change = validation_request.validation_type.code == "CHANGE" if validation_request.validation_type else False

    for entry in add_entries:
        if is_change and entry.version_id is None:
            raise HTTPException(
                status_code=400,
                detail=f"Model {entry.model_id}: CHANGE validations require a version_id"
            )
        if entry.version_id is not None:
            version = db.query(ModelVersion).filter(
                ModelVersion.version_id == entry.version_id
            ).first()
            if not version or version.model_id != entry.model_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Model {entry.model_id}: version_id does not belong to this model"
                )
            if is_change and version.status != "DRAFT":
                raise HTTPException(
                    status_code=400,
                    detail=f"Model {entry.model_id}: Only DRAFT versions can be added to CHANGE validations"
                )

    pre_scope = compute_required_approval_scope(validation_request)
    old_lead_time = validation_request.applicable_lead_time_days

    if remove_ids:
        db.query(ValidationRequestModelVersion).filter(
            ValidationRequestModelVersion.request_id == request_id,
            ValidationRequestModelVersion.model_id.in_(remove_ids)
        ).delete(synchronize_session=False)

    for entry in add_entries:
        db.add(ValidationRequestModelVersion(
            request_id=request_id,
            model_id=entry.model_id,
            version_id=entry.version_id
        ))

    db.flush()

    # Reload relationships after bulk delete/insert to avoid stale collections.
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.assignments).joinedload(ValidationAssignment.validator),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.approver),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.assigned_approver),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.manually_added_by),
        joinedload(ValidationRequest.models).joinedload(Model.model_regions),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model).joinedload(Model.model_regions),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.version)
    ).populate_existing().filter(ValidationRequest.request_id == request_id).first()
    if not validation_request:
        raise HTTPException(
            status_code=404, detail="Validation request not found")

    is_change = validation_request.validation_type.code == "CHANGE" if validation_request.validation_type else False
    if is_change and any(assoc.version_id is None for assoc in validation_request.model_versions_assoc):
        raise HTTPException(
            status_code=400,
            detail="CHANGE validations require versions for all models"
        )

    validators_unassigned: List[str] = []
    updated_model_ids = [
        assoc.model_id for assoc in validation_request.model_versions_assoc
    ]
    conflicting = [
        assignment for assignment in validation_request.assignments
        if not check_validator_independence(
            db, updated_model_ids, assignment.validator_id)
    ]

    if conflicting and not update_data.allow_unassign_conflicts:
        names = [assignment.validator.full_name for assignment in conflicting]
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Validator independence violation",
                "conflicting_validators": names,
                "action": "Set allow_unassign_conflicts=true to proceed and unassign"
            }
        )

    for assignment in conflicting:
        validators_unassigned.append(assignment.validator.full_name)
        db.delete(assignment)

    combined_versions = {
        assoc.model_id: assoc.version_id
        for assoc in validation_request.model_versions_assoc
    }
    warnings = check_target_completion_date_warnings(
        db,
        ValidationRequestCreate(
            model_ids=updated_model_ids,
            model_versions=combined_versions,
            validation_type_id=validation_request.validation_type_id,
            priority_id=validation_request.priority_id,
            target_completion_date=validation_request.target_completion_date,
            trigger_reason=validation_request.trigger_reason,
            region_ids=[region.region_id for region in validation_request.regions]
        )
    )
    if any(warning.severity == "ERROR" for warning in warnings):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Model changes violate target completion rules",
                "warnings": jsonable_encoder(warnings)
            }
        )

    deviations_flagged = flag_plan_deviations_for_tier_change(
        db, validation_request)
    approvals_added, approvals_voided = sync_approvals_for_scope_change(
        db, validation_request, pre_scope, current_user)
    conditional_added, conditional_voided = sync_conditional_approvals(
        db, validation_request, current_user)

    from app.core.model_approval_status import update_model_approval_status_if_changed

    for model_id in remove_ids:
        model = models_by_id.get(model_id)
        if model:
            update_model_approval_status_if_changed(
                model=model,
                db=db,
                trigger_type="VALIDATION_REQUEST_MODEL_REMOVED",
                trigger_entity_type="ValidationRequest",
                trigger_entity_id=request_id
            )

    for entry in add_entries:
        model = models_by_id.get(entry.model_id)
        if model:
            update_model_approval_status_if_changed(
                model=model,
                db=db,
                trigger_type="VALIDATION_REQUEST_MODEL_ADDED",
                trigger_entity_type="ValidationRequest",
                trigger_entity_id=request_id
            )

    models_for_grouping = [
        assoc.model for assoc in validation_request.model_versions_assoc if assoc.model
    ]
    update_grouping_memory(db, validation_request, models_for_grouping)

    validation_request.updated_at = utc_now()
    new_lead_time = validation_request.applicable_lead_time_days

    log_model_change_audit(
        db,
        validation_request,
        update_data,
        current_user,
        validators_unassigned=validators_unassigned,
        approvals_voided=approvals_voided,
        conditional_voided=conditional_voided
    )

    db.commit()

    return ValidationRequestModelUpdateResponse(
        success=True,
        models_added=[entry.model_id for entry in add_entries],
        models_removed=list(remove_ids),
        lead_time_changed=old_lead_time != new_lead_time,
        old_lead_time_days=old_lead_time,
        new_lead_time_days=new_lead_time,
        warnings=warnings,
        plan_deviations_flagged=deviations_flagged,
        approvals_added=approvals_added,
        approvals_voided=approvals_voided,
        conditional_approvals_added=conditional_added,
        conditional_approvals_voided=conditional_voided,
        validators_unassigned=validators_unassigned
    )


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

    # Update optional submission metadata fields
    if submission_data.confirmed_model_version_id is not None:
        validation_request.confirmed_model_version_id = submission_data.confirmed_model_version_id
        # Also update the ModelVersion to link back to this validation request
        from app.models.model_version import ModelVersion
        version = db.query(ModelVersion).filter(
            ModelVersion.version_id == submission_data.confirmed_model_version_id
        ).first()
        if version:
            version.validation_request_id = request_id
    if submission_data.model_documentation_version is not None:
        validation_request.model_documentation_version = submission_data.model_documentation_version
    if submission_data.model_submission_version is not None:
        validation_request.model_submission_version = submission_data.model_submission_version
    if submission_data.model_documentation_id is not None:
        validation_request.model_documentation_id = submission_data.model_documentation_id

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
                changed_at=utc_now()
            )
            db.add(status_history)

    validation_request.updated_at = utc_now()

    # Create audit log
    changes: dict[str, Any] = {
        "submission_received_date": {
            "old": str(old_date) if old_date else None,
            "new": str(submission_data.submission_received_date)
        }
    }

    # Include submission metadata fields in audit log if provided
    if submission_data.confirmed_model_version_id is not None:
        changes["confirmed_model_version_id"] = submission_data.confirmed_model_version_id
    if submission_data.model_documentation_version:
        changes["model_documentation_version"] = submission_data.model_documentation_version
    if submission_data.model_submission_version:
        changes["model_submission_version"] = submission_data.model_submission_version
    if submission_data.model_documentation_id:
        changes["model_documentation_id"] = submission_data.model_documentation_id

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
        timestamp=utc_now()
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


@router.get("/requests/{request_id}/pre-transition-warnings", response_model=PreTransitionWarningsResponse)
def get_pre_transition_warnings(
    request_id: int,
    target_status: str = Query(..., description="Target status to transition to (e.g., PENDING_APPROVAL)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pre-transition warnings for a validation request.

    Returns advisory warnings about conditions that should be reviewed before
    transitioning to the target status (e.g., open findings, pending recommendations,
    unaddressed attestations).

    Warning Types:
    - PENDING_RECOMMENDATIONS: Model has open recommendations not yet addressed
    - UNADDRESSED_ATTESTATIONS: Model owner has pending attestation items
    """
    # Get the validation request
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    warnings = []

    # Get models linked to this request
    model_ids = [link.model_id for link in validation_request.models]

    if not model_ids:
        # No models linked, no warnings to check
        return PreTransitionWarningsResponse(
            request_id=request_id,
            target_status=target_status,
            warnings=[],
            can_proceed=True
        )

    # Get model details for warnings
    models = db.query(Model).filter(Model.model_id.in_(model_ids)).all()
    model_map = {m.model_id: m for m in models}

    # Get CLOSED status for recommendations
    rec_closed_status = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Recommendation Status",
        TaxonomyValue.code == "CLOSED"
    ).first()
    closed_status_id = rec_closed_status.value_id if rec_closed_status else None

    for model_id in model_ids:
        model = model_map.get(model_id)
        if not model:
            continue

        model_name = model.model_name

        # 1. Check for PENDING_RECOMMENDATIONS (not CLOSED)
        # IMPORTANT: Exclude recommendations from the CURRENT validation being transitioned.
        # Only warn about recommendations from prior validations or monitoring cycles.
        rec_query = db.query(func.count(Recommendation.recommendation_id)).filter(
            Recommendation.model_id == model_id,
            # Exclude recommendations that belong to THIS validation request
            or_(
                Recommendation.validation_request_id.is_(None),  # From monitoring (no validation source)
                Recommendation.validation_request_id != request_id  # From a different validation
            )
        )
        if closed_status_id:
            rec_query = rec_query.filter(Recommendation.current_status_id != closed_status_id)

        pending_rec_count = rec_query.scalar()

        if pending_rec_count and pending_rec_count > 0:
            warnings.append(PreTransitionWarning(
                warning_type="PENDING_RECOMMENDATIONS",
                severity="WARNING",
                message=f"Model has {pending_rec_count} open recommendation(s) from prior validations or monitoring that should be addressed.",
                model_id=model_id,
                model_name=model_name,
                details={"recommendation_count": pending_rec_count}
            ))

        # 3. Check for UNADDRESSED_ATTESTATIONS (status="PENDING" for this model)
        pending_attest_count = db.query(func.count(AttestationRecord.attestation_id)).filter(
            AttestationRecord.model_id == model_id,
            AttestationRecord.status == "PENDING"
        ).scalar()

        if pending_attest_count and pending_attest_count > 0:
            warnings.append(PreTransitionWarning(
                warning_type="UNADDRESSED_ATTESTATIONS",
                severity="WARNING",
                message=f"Model has {pending_attest_count} pending attestation(s) that should be completed.",
                model_id=model_id,
                model_name=model_name,
                details={"attestation_count": pending_attest_count}
            ))

    # Determine can_proceed: True unless ERROR severity warnings exist
    # (Currently all warnings are WARNING severity, so can_proceed is True)
    has_error = any(w.severity == "ERROR" for w in warnings)
    can_proceed = not has_error

    return PreTransitionWarningsResponse(
        request_id=request_id,
        target_status=target_status,
        warnings=warnings,
        can_proceed=can_proceed
    )


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
        joinedload(ValidationRequest.validation_plan),
        joinedload(ValidationRequest.scorecard_result)  # Needed for REVISION resubmission comparison
    ).with_for_update(of=ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()

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
    # Special case: Allow IN_PROGRESS -> PENDING_APPROVAL if no reviewer assigned
    if old_status_code == "IN_PROGRESS" and new_status_code == "PENDING_APPROVAL":
        # Check if there's a reviewer assigned
        reviewer_assignment = db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == request_id,
            ValidationAssignment.is_reviewer == True
        ).first()

        # If no reviewer, allow the direct transition (skip REVIEW stage)
        if not reviewer_assignment:
            pass  # Allow this transition
        else:
            # Reviewer exists, must go through REVIEW first
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition from '{old_status_code}' to '{new_status_code}'. A reviewer is assigned, so work must go through REVIEW stage first."
            )
    elif not check_valid_status_transition(old_status_code, new_status_code):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{old_status_code}' to '{new_status_code}'"
        )

    # BUSINESS RULE: REVISION status can only be set via the send-back approval flow
    # Manual status changes to REVISION are blocked to ensure:
    # 1. Proper snapshot is captured for approval reset logic
    # 2. Comments are required explaining what needs revision
    # 3. Only Global/Regional approvers can initiate send-back
    if new_status_code == "REVISION":
        raise HTTPException(
            status_code=400,
            detail="Cannot manually set status to Revision. Use the 'Send Back' option in the approval workflow instead. This ensures proper tracking of revision requests and approval resets."
        )

    if old_status_code == "PENDING_APPROVAL" and new_status_code == "IN_PROGRESS":
        if not is_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only admins can send a validation back to In Progress from Pending Approval."
            )
        if not status_update.change_reason or not status_update.change_reason.strip():
            raise HTTPException(
                status_code=400,
                detail="A change reason is required when sending back to In Progress."
            )

    # Additional business rules

    # BUSINESS RULE: Cannot move to or remain in active workflow statuses without a primary validator
    # Active workflow statuses that require a primary validator
    active_statuses_requiring_validator = [
        "PLANNING", "IN_PROGRESS", "REVIEW", "PENDING_APPROVAL"]

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

        # Check risk assessment status for all models
        models = validation_request.models
        if models:
            can_proceed, blocking_errors, assessment_warnings = check_risk_assessment_for_workflow_progression(
                db, models, new_status_code
            )
            if not can_proceed:
                raise HTTPException(
                    status_code=400,
                    detail="Risk assessment requirements not met:\n" + "\n".join(f"• {err}" for err in blocking_errors)
                )
            # If there are warnings and user hasn't acknowledged them
            if assessment_warnings and not status_update.skip_assessment_warning:
                raise HTTPException(
                    status_code=409,  # Conflict - requires user confirmation
                    detail={
                        "warning_type": "outdated_risk_assessment",
                        "message": "Risk assessment review recommended",
                        "warnings": assessment_warnings,
                        "action": "Set skip_assessment_warning=true to proceed"
                    }
                )

        # Validate plan compliance (deviations must have rationale)
        # Pass validation type code so scope-only types skip component checks
        val_type_code = validation_request.validation_type.code if validation_request.validation_type else None
        is_valid, validation_errors = validate_plan_compliance(
            db,
            request_id,
            require_plan=requires_plan,
            required_region_codes=plan_region_codes,
            validation_type_code=val_type_code
        )
        if not is_valid:
            error_message = "Validation plan compliance issues:\n" + \
                "\n".join(f"• {err}" for err in validation_errors)
            raise HTTPException(
                status_code=400,
                detail=error_message
            )

    if new_status_code == "PENDING_APPROVAL":
        # Must have an outcome created
        if not validation_request.outcome:
            raise HTTPException(
                status_code=400, detail="Cannot move to Pending Approval without creating outcome")

        # Check risk assessment status for all models
        models = validation_request.models
        if models:
            can_proceed, blocking_errors, assessment_warnings = check_risk_assessment_for_workflow_progression(
                db, models, new_status_code
            )
            if not can_proceed:
                raise HTTPException(
                    status_code=400,
                    detail="Risk assessment requirements not met:\n" + "\n".join(f"• {err}" for err in blocking_errors)
                )
            # If there are warnings and user hasn't acknowledged them
            if assessment_warnings and not status_update.skip_assessment_warning:
                raise HTTPException(
                    status_code=409,  # Conflict - requires user confirmation
                    detail={
                        "warning_type": "outdated_risk_assessment",
                        "message": "Risk assessment review recommended",
                        "warnings": assessment_warnings,
                        "action": "Set skip_assessment_warning=true to proceed"
                    }
                )

        # Validate plan compliance (deviations must have rationale)
        # Pass validation type code so scope-only types skip component checks
        val_type_code = validation_request.validation_type.code if validation_request.validation_type else None
        is_valid, validation_errors = validate_plan_compliance(
            db,
            request_id,
            require_plan=requires_plan,
            required_region_codes=plan_region_codes,
            validation_type_code=val_type_code
        )
        if not is_valid:
            error_message = "Validation plan compliance issues:\n" + \
                "\n".join(f"• {err}" for err in validation_errors)
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

        # Re-evaluate conditional approval rules (handles null risk tiers at request creation)
        # Evaluate rules for ALL models in the validation request
        models = validation_request.models
        if models:
            for model in models:
                evaluate_and_create_conditional_approvals(
                    db, validation_request, model)

        # Re-evaluate standard approvers (Global/Regional) in case they weren't created at
        # request creation time (e.g., no approvers existed then, or regions weren't configured)
        # The function is idempotent - it won't create duplicates for existing approvals
        auto_assign_approvers(db, validation_request, current_user)

    admin_sendback_snapshot = None
    if old_status_code == "PENDING_APPROVAL" and new_status_code == "IN_PROGRESS":
        admin_sendback_snapshot = create_revision_snapshot(db, validation_request)
        admin_sendback_snapshot["context_type"] = "admin_in_progress_sendback"
        admin_sendback_snapshot["sent_back_to_in_progress_by_user_id"] = current_user.user_id

    # Update status
    old_status_id = validation_request.current_status_id
    validation_request.current_status_id = new_status.value_id
    validation_request.updated_at = utc_now()

    # Create status history
    status_history_entry = create_status_history_entry(
        db, request_id, old_status_id, new_status.value_id,
        current_user.user_id, status_update.change_reason,
        additional_context=json.dumps(admin_sendback_snapshot) if admin_sendback_snapshot else None
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
        timestamp=utc_now()
    )
    db.add(audit_log)

    # ===== SNAPSHOT RISK TIER ON APPROVAL =====
    # When validation is approved, capture the model's risk tier at that moment
    if new_status_code == "APPROVED":
        # Find the most conservative (highest) risk tier among associated models
        models = validation_request.models
        if models:
            # Risk tier hierarchy: TIER_1 (High) > TIER_2 (Medium) > TIER_3 (Low) > TIER_4 (Very Low)
            # Lower sort_order = higher risk
            best_tier_id = None
            best_sort_order = 999

            for model in models:
                if model.risk_tier_id and model.risk_tier:
                    if model.risk_tier.sort_order < best_sort_order:
                        best_sort_order = model.risk_tier.sort_order
                        best_tier_id = model.risk_tier_id

            if best_tier_id:
                validation_request.validated_risk_tier_id = best_tier_id

                # Audit log for risk tier snapshot
                tier_snapshot_audit = AuditLog(
                    entity_type="ValidationRequest",
                    entity_id=request_id,
                    action="RISK_TIER_SNAPSHOT",
                    user_id=current_user.user_id,
                    changes={
                        "validated_risk_tier_id": best_tier_id,
                        "model_count": len(models),
                        "reason": "Risk tier captured at validation approval"
                    },
                    timestamp=utc_now()
                )
                db.add(tier_snapshot_audit)

        # ===== DUE DATE OVERRIDE HANDLING ON APPROVAL =====
        # Handle override lifecycle: clear ONE_TIME or roll-forward PERMANENT
        # Must run BEFORE any new validation request is created
        handle_override_on_approval(db, validation_request, current_user.user_id)

    # ===== VALIDATION PLAN LOCKING/UNLOCKING LOGIC =====
    # Lock plan when moving to Review or Pending Approval
    # Unlock plan when sending back from locked status to editable status
    if validation_request.validation_plan:
        plan = validation_request.validation_plan

        locked_statuses = ["REVIEW", "PENDING_APPROVAL", "APPROVED"]
        editable_statuses = ["INTAKE", "PLANNING", "IN_PROGRESS"]

        # LOCK: When moving TO Review/Pending Approval/Approved
        if new_status_code in locked_statuses and not plan.locked_at:
            active_config = db.query(ComponentDefinitionConfiguration).filter_by(
                is_active=True).first()

            if active_config:
                plan.config_id = active_config.config_id
                plan.locked_at = utc_now()
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
                    timestamp=utc_now()
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
                timestamp=utc_now()
            )
            db.add(plan_unlock_audit)

    # ===== VOID CONDITIONAL APPROVALS WHEN SENDING BACK =====
    # When moving FROM PENDING_APPROVAL TO IN_PROGRESS, void all conditional approvals
    if old_status_code == "PENDING_APPROVAL" and new_status_code == "IN_PROGRESS":
        # Void all pending conditional approvals for this validation request
        conditional_approvals = db.query(ValidationApproval).filter(
            ValidationApproval.request_id == request_id,
            ValidationApproval.approval_type == "Conditional",
            ValidationApproval.approval_status == "Pending",
            ValidationApproval.voided_by_id.is_(None)
        ).all()

        for approval in conditional_approvals:
            approval.voided_by_id = current_user.user_id
            approval.void_reason = f"Validation sent back to In Progress from Pending Approval: {status_update.change_reason or 'No reason provided'}"
            approval.voided_at = utc_now()

            # Create audit log for each voided approval
            void_audit = AuditLog(
                entity_type="ValidationApproval",
                entity_id=approval.approval_id,
                action="VOID",
                user_id=current_user.user_id,
                changes={
                    "reason": approval.void_reason,
                    "approval_type": "Conditional",
                    "approver_role_id": approval.approver_role_id,
                    "request_id": request_id,
                    "status_change": f"{old_status.label} → {new_status.label}"
                },
                timestamp=utc_now()
            )
            db.add(void_audit)

        # Also clear model use_approval_date if any models were approved
        for model in validation_request.models:
            if model.use_approval_date:
                model.use_approval_date = None

                # Create audit log for model approval reversal
                model_audit = AuditLog(
                    entity_type="Model",
                    entity_id=model.model_id,
                    action="CONDITIONAL_APPROVAL_REVERTED",
                    user_id=current_user.user_id,
                    changes={
                        "reason": f"Validation sent back to In Progress: {status_update.change_reason or 'No reason provided'}",
                        "validation_request_id": request_id,
                        "status_change": f"{old_status.label} → {new_status.label}"
                    },
                    timestamp=utc_now()
                )
                db.add(model_audit)

        # Reset all traditional approvals (Global/Regional) unconditionally
        traditional_approvals = db.query(ValidationApproval).filter(
            ValidationApproval.request_id == request_id,
            ValidationApproval.approval_type.in_(["Global", "Regional"]),
            ValidationApproval.voided_by_id.is_(None)
        ).all()

        for approval in traditional_approvals:
            old_approval_status = approval.approval_status
            approval.approval_status = "Pending"
            approval.approved_at = None
            approval.comments = None

            reset_audit = AuditLog(
                entity_type="ValidationApproval",
                entity_id=approval.approval_id,
                action="RESET",
                user_id=current_user.user_id,
                changes={
                    "reason": (
                        "Admin sent validation back to In Progress "
                        f"(major rework required): {status_update.change_reason or 'No reason provided'}"
                    ),
                    "old_approval_status": old_approval_status,
                    "new_approval_status": "Pending",
                    "approval_type": approval.approval_type,
                    "request_id": request_id,
                    "reset_type": "unconditional"
                },
                timestamp=utc_now()
            )
            db.add(reset_audit)

    # ===== RESUBMISSION FROM REVISION - CONDITIONAL APPROVAL RESET =====
    # When resubmitting from REVISION to PENDING_APPROVAL, conditionally reset approvals
    if old_status_code == "REVISION" and new_status_code == "PENDING_APPROVAL":
        from app.models.recommendation import Recommendation
        from app.models.limitation import ModelLimitation

        # Find the most recent revision snapshot (entry into REVISION status)
        last_revision_entry = db.query(ValidationStatusHistory).filter(
            ValidationStatusHistory.request_id == request_id,
            ValidationStatusHistory.additional_context.isnot(None),
            ValidationStatusHistory.additional_context.contains(
                '"context_type": "revision_sendback"'
            )
        ).order_by(desc(ValidationStatusHistory.changed_at)).first()

        if last_revision_entry and last_revision_entry.additional_context:
            snapshot = json.loads(last_revision_entry.additional_context)

            # Get current state for comparison
            current_rating = None
            if validation_request.scorecard_result:
                current_rating = validation_request.scorecard_result.overall_rating

            current_rec_ids = set(
                r.recommendation_id for r in db.query(Recommendation.recommendation_id).filter(
                    Recommendation.validation_request_id == request_id
                ).all()
            )

            current_lim_ids = set(
                l.limitation_id for l in db.query(ModelLimitation.limitation_id).filter(
                    ModelLimitation.validation_request_id == request_id
                ).all()
            )

            # Compare to snapshot
            snapshot_rating = snapshot.get("overall_rating")
            snapshot_rec_ids = set(snapshot.get("recommendation_ids", []))
            snapshot_lim_ids = set(snapshot.get("limitation_ids", []))

            material_change = (
                current_rating != snapshot_rating or
                current_rec_ids != snapshot_rec_ids or
                current_lim_ids != snapshot_lim_ids
            )

            # Identify the approver who sent back (to always reset their approval)
            sent_back_approval_id = snapshot.get("sent_back_by_approval_id")

            # Reset approvals based on logic
            approvals = db.query(ValidationApproval).filter(
                ValidationApproval.request_id == request_id,
                ValidationApproval.voided_by_id.is_(None)  # Only active approvals
            ).all()

            reset_approvals = []
            for approval in approvals:
                should_reset = False

                # Always reset the sender's approval
                if approval.approval_id == sent_back_approval_id:
                    should_reset = True

                # Reset other "Approved" approvals only if material changes detected
                elif approval.approval_status == "Approved" and material_change:
                    should_reset = True

                # Reset "Sent Back" approvals (the sender, if not matched by ID)
                elif approval.approval_status == "Sent Back":
                    should_reset = True

                if should_reset:
                    old_approval_status = approval.approval_status
                    approval.approval_status = "Pending"
                    approval.approved_at = None
                    approval.comments = None
                    reset_approvals.append({
                        "approval_id": approval.approval_id,
                        "approval_type": approval.approval_type,
                        "approver_role": approval.approver_role,
                        "old_status": old_approval_status
                    })

            # Create audit log for resubmission
            resubmit_audit = AuditLog(
                entity_type="ValidationRequest",
                entity_id=request_id,
                action="RESUBMIT_FROM_REVISION",
                user_id=current_user.user_id,
                changes={
                    "material_change_detected": material_change,
                    "change_details": {
                        "rating_changed": current_rating != snapshot_rating,
                        "recommendations_changed": current_rec_ids != snapshot_rec_ids,
                        "limitations_changed": current_lim_ids != snapshot_lim_ids
                    },
                    "approvals_reset": reset_approvals,
                    "reason": status_update.change_reason
                },
                timestamp=utc_now()
            )
            db.add(resubmit_audit)

    # ===== RETURN FROM ADMIN IN_PROGRESS SENDBACK (AUDIT ONLY) =====
    if new_status_code == "PENDING_APPROVAL" and old_status_code in ("IN_PROGRESS", "REVIEW"):
        from app.models.recommendation import Recommendation
        from app.models.limitation import ModelLimitation

        last_sendback_entry = db.query(ValidationStatusHistory).filter(
            ValidationStatusHistory.request_id == request_id,
            ValidationStatusHistory.additional_context.isnot(None),
            ValidationStatusHistory.additional_context.contains(
                '"context_type": "admin_in_progress_sendback"'
            )
        ).order_by(desc(ValidationStatusHistory.changed_at)).first()

        if last_sendback_entry and last_sendback_entry.additional_context:
            snapshot = json.loads(last_sendback_entry.additional_context)

            current_rating = None
            if validation_request.scorecard_result:
                current_rating = validation_request.scorecard_result.overall_rating

            current_rec_ids = set(
                r.recommendation_id for r in db.query(Recommendation.recommendation_id).filter(
                    Recommendation.validation_request_id == request_id
                ).all()
            )

            current_lim_ids = set(
                l.limitation_id for l in db.query(ModelLimitation.limitation_id).filter(
                    ModelLimitation.validation_request_id == request_id
                ).all()
            )

            snapshot_rating = snapshot.get("overall_rating")
            snapshot_rec_ids = set(snapshot.get("recommendation_ids", []))
            snapshot_lim_ids = set(snapshot.get("limitation_ids", []))

            material_change = (
                current_rating != snapshot_rating or
                current_rec_ids != snapshot_rec_ids or
                current_lim_ids != snapshot_lim_ids
            )

            audit_log = AuditLog(
                entity_type="ValidationRequest",
                entity_id=request_id,
                action="RETURN_FROM_IN_PROGRESS_SENDBACK",
                user_id=current_user.user_id,
                changes={
                    "material_change_detected": material_change,
                    "change_details": {
                        "rating_changed": current_rating != snapshot_rating,
                        "recommendations_changed": current_rec_ids != snapshot_rec_ids,
                        "limitations_changed": current_lim_ids != snapshot_lim_ids
                    },
                    "note": "Approvals were reset when sent to In Progress; this audit is for transparency only.",
                    "reason": status_update.change_reason
                },
                timestamp=utc_now()
            )
            db.add(audit_log)

            if status_history_entry:
                status_history_entry.additional_context = json.dumps({
                    "context_type": "admin_in_progress_sendback_audit",
                    "material_change_detected": material_change,
                    "change_details": {
                        "rating_changed": current_rating != snapshot_rating,
                        "recommendations_changed": current_rec_ids != snapshot_rec_ids,
                        "limitations_changed": current_lim_ids != snapshot_lim_ids
                    }
                })

    # Auto-update linked model version statuses based on validation status
    update_version_statuses_for_validation(
        db, validation_request, new_status_code, current_user
    )

    # ===== UPDATE MODEL APPROVAL STATUS =====
    # Recalculate approval status for all models in this validation request
    # and record history if status changed
    from app.core.model_approval_status import update_model_approval_status_if_changed
    for model in validation_request.models:
        update_model_approval_status_if_changed(
            model=model,
            db=db,
            trigger_type="VALIDATION_STATUS_CHANGE",
            trigger_entity_type="ValidationRequest",
            trigger_entity_id=request_id,
            notes=f"Validation request status changed from {old_status_code or 'None'} to {new_status_code}"
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
    if not is_admin(current_user):
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
    validation_request.declined_at = utc_now()
    validation_request.updated_at = utc_now()

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
        timestamp=utc_now()
    )
    db.add(audit_log)

    # Auto-update linked model version statuses
    update_version_statuses_for_validation(
        db, validation_request, "CANCELLED", current_user
    )

    db.commit()
    db.refresh(validation_request)
    return validation_request


# ==================== HOLD / CANCEL / RESUME ENDPOINTS ====================


@router.post("/requests/{request_id}/hold", response_model=ValidationRequestResponse)
def put_request_on_hold(
    request_id: int,
    hold_data: ValidationRequestHold,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Put a validation request on hold with mandatory reason.

    - Pauses the validation workflow
    - Model version status reverts from IN_VALIDATION to DRAFT
    - Team SLA clock is paused (hold time excluded from calculations)
    - Compliance deadline remains unchanged
    """
    check_validator_or_admin(current_user)

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.new_status),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.old_status)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Check current status allows transition to ON_HOLD
    old_status = validation_request.current_status
    old_status_code = old_status.code if old_status else None

    if not check_valid_status_transition(old_status_code, "ON_HOLD"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot put request on hold from status '{old_status_code}'. Request may already be on hold, cancelled, or approved."
        )

    # Get ON_HOLD status
    on_hold_status = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code == "ON_HOLD"
    ).first()

    if not on_hold_status:
        raise HTTPException(status_code=500, detail="ON_HOLD status not found in taxonomy")

    # Update status
    old_status_id = validation_request.current_status_id
    validation_request.current_status_id = on_hold_status.value_id
    validation_request.updated_at = utc_now()

    # Create status history with mandatory reason
    create_status_history_entry(
        db, request_id, old_status_id, on_hold_status.value_id,
        current_user.user_id, hold_data.hold_reason
    )

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="PUT_ON_HOLD",
        user_id=current_user.user_id,
        changes={
            "old_status": old_status.label if old_status else None,
            "new_status": on_hold_status.label,
            "hold_reason": hold_data.hold_reason
        },
        timestamp=utc_now()
    )
    db.add(audit_log)

    # Auto-update linked model version statuses (IN_VALIDATION -> DRAFT)
    update_version_statuses_for_validation(
        db, validation_request, "ON_HOLD", current_user
    )

    db.commit()
    db.refresh(validation_request)
    return validation_request


@router.post("/requests/{request_id}/cancel", response_model=ValidationRequestResponse)
def cancel_validation_request(
    request_id: int,
    cancel_data: ValidationRequestCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a validation request with mandatory reason.

    - This is a terminal state - cannot be undone
    - Model version status reverts from IN_VALIDATION to DRAFT
    - Unlike 'decline', this can be used by validators (not just admins)
    """
    check_validator_or_admin(current_user)

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.new_status),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.old_status)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Check current status allows transition to CANCELLED
    old_status = validation_request.current_status
    old_status_code = old_status.code if old_status else None

    if not check_valid_status_transition(old_status_code, "CANCELLED"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel request from status '{old_status_code}'. Request may already be cancelled or approved."
        )

    # Get CANCELLED status
    cancelled_status = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code == "CANCELLED"
    ).first()

    if not cancelled_status:
        raise HTTPException(status_code=500, detail="CANCELLED status not found in taxonomy")

    # Update status
    old_status_id = validation_request.current_status_id
    validation_request.current_status_id = cancelled_status.value_id
    validation_request.updated_at = utc_now()

    # Create status history with mandatory reason
    create_status_history_entry(
        db, request_id, old_status_id, cancelled_status.value_id,
        current_user.user_id, cancel_data.cancel_reason
    )

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="CANCELLED",
        user_id=current_user.user_id,
        changes={
            "old_status": old_status.label if old_status else None,
            "new_status": cancelled_status.label,
            "cancel_reason": cancel_data.cancel_reason
        },
        timestamp=utc_now()
    )
    db.add(audit_log)

    # Auto-update linked model version statuses (IN_VALIDATION -> DRAFT)
    update_version_statuses_for_validation(
        db, validation_request, "CANCELLED", current_user
    )

    # ===== DUE DATE OVERRIDE: VOID ON CANCELLATION =====
    # If there's an active override linked to this cancelled request, void it
    void_override_on_cancellation(db, validation_request, current_user.user_id)

    db.commit()
    db.refresh(validation_request)
    return validation_request


@router.post("/requests/{request_id}/resume", response_model=ValidationRequestResponse)
def resume_from_hold(
    request_id: int,
    resume_data: ValidationRequestResume,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resume a validation request from hold.

    - Returns to the status the request was in before it was put on hold
    - Optionally specify a different target status via target_status_code
    """
    check_validator_or_admin(current_user)

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.regions),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.new_status),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.old_status)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Must be currently ON_HOLD
    if not validation_request.current_status or validation_request.current_status.code != "ON_HOLD":
        raise HTTPException(
            status_code=400,
            detail="Cannot resume - request is not currently on hold"
        )

    # Determine target status
    target_status_code = resume_data.target_status_code
    if not target_status_code:
        # Use previous_status_before_hold computed property
        target_status_code = validation_request.previous_status_before_hold
        if not target_status_code:
            raise HTTPException(
                status_code=400,
                detail="Cannot determine previous status. Please specify target_status_code."
            )

    # Validate the transition is allowed from ON_HOLD
    if not check_valid_status_transition("ON_HOLD", target_status_code):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume to status '{target_status_code}' from ON_HOLD"
        )

    # Get target status taxonomy value
    target_status = db.query(TaxonomyValue).join(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code == target_status_code
    ).first()

    if not target_status:
        raise HTTPException(status_code=404, detail=f"Status '{target_status_code}' not found in taxonomy")

    # Update status
    old_status = validation_request.current_status
    old_status_id = validation_request.current_status_id
    validation_request.current_status_id = target_status.value_id
    validation_request.updated_at = utc_now()

    # Create status history
    reason = resume_data.resume_notes or f"Resumed from hold to {target_status.label}"
    create_status_history_entry(
        db, request_id, old_status_id, target_status.value_id,
        current_user.user_id, reason
    )

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="RESUMED_FROM_HOLD",
        user_id=current_user.user_id,
        changes={
            "old_status": old_status.label if old_status else None,
            "new_status": target_status.label,
            "total_hold_days": validation_request.total_hold_days,
            "resume_notes": resume_data.resume_notes
        },
        timestamp=utc_now()
    )
    db.add(audit_log)

    # Auto-update linked model version statuses if resuming to active work
    if target_status_code in ["IN_PROGRESS", "REVIEW", "PENDING_APPROVAL"]:
        update_version_statuses_for_validation(
            db, validation_request, target_status_code, current_user
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
        timestamp=utc_now()
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
        created_at=utc_now()
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
        timestamp=utc_now()
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
            validation_request.updated_at = utc_now()

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
                timestamp=utc_now()
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
        not is_admin(current_user) and
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
            timestamp=utc_now()
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

    # Load the validation request with current status for auto-revert logic
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status)
    ).filter(ValidationRequest.request_id == assignment.request_id).first()

    # Check how many validators will remain
    total_validators = db.query(ValidationAssignment).filter(
        ValidationAssignment.request_id == assignment.request_id
    ).count()

    if total_validators <= 1:
        # Check if we're in PLANNING - if so, allow removal and revert to INTAKE
        if (validation_request and validation_request.current_status and
                validation_request.current_status.code == "PLANNING"):
            # Get INTAKE status
            intake_status = db.query(TaxonomyValue).join(Taxonomy).filter(
                Taxonomy.name == "Validation Request Status",
                TaxonomyValue.code == "INTAKE"
            ).first()

            if intake_status:
                old_status_id = validation_request.current_status_id
                validation_request.current_status_id = intake_status.value_id
                validation_request.updated_at = utc_now()

                # Create status history entry
                create_status_history_entry(
                    db,
                    assignment.request_id,
                    old_status_id,
                    intake_status.value_id,
                    current_user.user_id,
                    f"Auto-reverted to Intake when {assignment.validator.full_name} was removed (no validators remaining)"
                )

                # Create audit log for status change
                status_audit_log = AuditLog(
                    entity_type="ValidationRequest",
                    entity_id=assignment.request_id,
                    action="STATUS_CHANGE",
                    user_id=current_user.user_id,
                    changes={
                        "field": "current_status",
                        "old_value": "PLANNING",
                        "new_value": "INTAKE",
                        "reason": "Auto-reverted when last validator removed"
                    },
                    timestamp=utc_now()
                )
                db.add(status_audit_log)
        else:
            # For other active statuses, still block removal
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
                timestamp=utc_now()
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
                timestamp=utc_now()
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
        timestamp=utc_now()
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
    assignment.reviewer_signed_off_at = utc_now()
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
        timestamp=utc_now()
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
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.current_status),
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.models),
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.requestor),
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.validation_type),
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.priority),
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.regions),
        joinedload(ValidationAssignment.request).joinedload(
            ValidationRequest.validation_plan)
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
        raise HTTPException(
            status_code=500, detail="In Progress status not found in taxonomy")

    # Update validation request status to In Progress
    old_status_id = request.current_status_id
    request.current_status_id = in_progress_status.value_id
    request.updated_at = utc_now()

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
        timestamp=utc_now()
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
        joinedload(ValidationRequest.outcome),
        joinedload(ValidationRequest.validation_type)
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
            detail="Outcome can only be created after work has begun. Please 'Mark Submission Received' to move out of the Planning stage."
        )

    # INTERIM validations require expiration_date
    validation_type_code = validation_request.validation_type.code if validation_request.validation_type else None
    if validation_type_code == "INTERIM" and not outcome_data.expiration_date:
        raise HTTPException(
            status_code=400,
            detail="Expiration date is required for INTERIM validations. Interim approvals are time-limited and must have an expiration date."
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
        effective_date=outcome_data.effective_date,
        expiration_date=outcome_data.expiration_date,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(outcome)

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationOutcome",
        entity_id=request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "overall_rating": rating.label
        },
        timestamp=utc_now()
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
    request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.validation_type)
    ).filter(
        ValidationRequest.request_id == outcome.request_id
    ).first()
    if request and request.current_status and request.current_status.code == "APPROVED":
        raise HTTPException(
            status_code=400, detail="Cannot modify outcome of approved validation")

    update_dict = update_data.model_dump(exclude_unset=True)

    # INTERIM validations require expiration_date - check if update would remove it
    validation_type_code = request.validation_type.code if request and request.validation_type else None
    if validation_type_code == "INTERIM":
        # Check if update explicitly sets expiration_date to None
        if 'expiration_date' in update_dict and update_dict['expiration_date'] is None:
            raise HTTPException(
                status_code=400,
                detail="Expiration date cannot be removed for INTERIM validations. Interim approvals must have an expiration date."
            )

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

    outcome.updated_at = utc_now()

    # Create audit log if changes were made
    if changes:
        audit_log = AuditLog(
            entity_type="ValidationOutcome",
            entity_id=outcome.request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes,
            timestamp=utc_now()
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
        review_date=utc_now(),
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(review_outcome)

    # Update status based on decision
    if review_data.decision == "AGREE":
        # Move to Pending Approval
        pending_approval_status = get_taxonomy_value_by_code(
            db, "Validation Request Status", "PENDING_APPROVAL")
        old_status_id = validation_request.current_status_id
        validation_request.current_status_id = pending_approval_status.value_id
        validation_request.updated_at = utc_now()

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
        validation_request.updated_at = utc_now()

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
        timestamp=utc_now()
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

    review_outcome.updated_at = utc_now()

    # Create audit log if changes were made
    if changes:
        audit_log = AuditLog(
            entity_type="ValidationReviewOutcome",
            entity_id=review_outcome.request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes,
            timestamp=utc_now()
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
        created_at=utc_now()
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

    # Get the validation request to check its status
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.approver),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.assigned_approver),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.manually_added_by),
        joinedload(ValidationRequest.scorecard_result)
    ).filter(
        ValidationRequest.request_id == approval.request_id
    ).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Associated validation request not found")

    # BUSINESS RULE: Approvals can only be submitted when request is in PENDING_APPROVAL status
    current_status_code = validation_request.current_status.code if validation_request.current_status else None
    if current_status_code != "PENDING_APPROVAL":
        status_label = validation_request.current_status.label if validation_request.current_status else "Unknown"
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit approval when request is in '{status_label}' status. Approvals can only be submitted when the request is in 'Pending Approval' status."
        )

    # Only the designated approver or Admin can update approval
    if current_user.user_id != approval.approver_id and not is_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Only the designated approver or Admin can update this approval")

    # BUSINESS RULE: Voided approvals cannot be modified
    # Approvals may be voided due to model risk tier changes or other lifecycle events
    if approval.voided_at:
        raise HTTPException(
            status_code=400,
            detail="This approval has been voided and cannot be modified. New approvals will be created if needed."
        )

    approval.approval_status = update_data.approval_status
    approval.comments = update_data.comments

    if update_data.approval_status == "Approved":
        approval.approved_at = utc_now()
    elif update_data.approval_status == "Pending":
        # Clear approved_at when withdrawing approval
        approval.approved_at = None

        # If this is a conditional approval being withdrawn, also clear model use_approval_date
        if approval.approver_role_id:
            for model in validation_request.models:
                if model.use_approval_date:
                    # Clear the approval date since conditional approvals are no longer all complete
                    model.use_approval_date = None

                    # Create audit log for model approval reversal
                    model_audit = AuditLog(
                        entity_type="Model",
                        entity_id=model.model_id,
                        action="CONDITIONAL_APPROVAL_REVERTED",
                        user_id=current_user.user_id,
                        changes={
                            "reason": "Conditional approval withdrawn",
                            "validation_request_id": approval.request_id,
                            "approval_id": approval_id
                        },
                        timestamp=utc_now()
                    )
                    db.add(model_audit)

    elif update_data.approval_status == "Sent Back":
        # Handle send-back for revision - only Global and Regional approvers
        if approval.approval_type not in ["Global", "Regional"]:
            raise HTTPException(
                status_code=400,
                detail="Only Global and Regional approvers can send back for revision"
            )

        # Comments are mandatory for send-back
        if not update_data.comments or not update_data.comments.strip():
            raise HTTPException(
                status_code=400,
                detail="Comments are required when sending back for revision"
            )

        approval.approved_at = utc_now()  # Track when sent back

        # validation_request already loaded above with scorecard_result and current_status
        if validation_request:
            # Create snapshot of current state for comparison on resubmission
            snapshot = create_revision_snapshot(db, validation_request)
            snapshot["context_type"] = "revision_sendback"
            snapshot["sent_back_by_approval_id"] = approval.approval_id
            snapshot["sent_back_by_role"] = approval.approver_role

            # Transition validation request to REVISION status
            revision_status = db.query(TaxonomyValue).join(Taxonomy).filter(
                Taxonomy.name == "Validation Request Status",
                TaxonomyValue.code == "REVISION"
            ).first()

            if revision_status:
                old_status_id = validation_request.current_status_id

                # Update validation request status
                validation_request.current_status_id = revision_status.value_id

                # Create status history entry with snapshot in additional_context
                history = ValidationStatusHistory(
                    request_id=validation_request.request_id,
                    old_status_id=old_status_id,
                    new_status_id=revision_status.value_id,
                    changed_by_id=current_user.user_id,
                    change_reason=f"Sent back by {approval.approver_role}: {update_data.comments}",
                    additional_context=json.dumps(snapshot),
                    changed_at=utc_now()
                )
                db.add(history)

                # Create audit log for status transition
                status_audit = AuditLog(
                    entity_type="ValidationRequest",
                    entity_id=validation_request.request_id,
                    action="STATUS_SENT_BACK",
                    user_id=current_user.user_id,
                    changes={
                        "old_status": validation_request.current_status.code if validation_request.current_status else "PENDING_APPROVAL",
                        "new_status": "REVISION",
                        "sent_back_by_role": approval.approver_role,
                        "approval_id": approval_id,
                        "comments": update_data.comments
                    },
                    timestamp=utc_now()
                )
                db.add(status_audit)

    # Create audit log with appropriate action type
    if update_data.approval_status == "Pending":
        action = "APPROVAL_WITHDRAWN"
    elif update_data.approval_status == "Sent Back":
        action = "APPROVAL_SENT_BACK"
    else:
        action = "APPROVAL_SUBMITTED"

    # Check if this is a proxy approval (admin approving on behalf)
    is_proxy_approval = is_admin(current_user) and current_user.user_id != approval.approver_id

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
        timestamp=utc_now()
    )
    db.add(audit_log)

    # Update validation request completion_date based on approval status
    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == approval.request_id
    ).first()

    if validation_request:
        # Flush pending changes so the query below sees the updated approval status/date
        db.flush()

        # Recalculate completion_date based on all approvals
        latest_approval_date = db.query(func.max(ValidationApproval.approved_at)).filter(
            ValidationApproval.request_id == approval.request_id,
            ValidationApproval.approval_status == 'Approved'
        ).scalar()

        # Set completion_date to latest approval date, or None if no approvals
        validation_request.completion_date = latest_approval_date

        # Auto-transition to APPROVED if all required approvals are complete
        if update_data.approval_status == "Approved":
            # Check if current status is PENDING_APPROVAL
            current_status_code = validation_request.current_status.code if validation_request.current_status else None
            if current_status_code == "PENDING_APPROVAL":
                # Count required approvals and approved approvals
                all_required_approvals = db.query(ValidationApproval).filter(
                    ValidationApproval.request_id == approval.request_id,
                    ValidationApproval.is_required == True
                ).all()

                all_approved = all(a.approval_status == "Approved" for a in all_required_approvals)

                if all_approved and len(all_required_approvals) > 0:
                    # Get APPROVED status taxonomy value
                    approved_status = db.query(TaxonomyValue).join(Taxonomy).filter(
                        Taxonomy.name == "Validation Request Status",
                        TaxonomyValue.code == "APPROVED"
                    ).first()

                    if approved_status:
                        old_status_id = validation_request.current_status_id

                        # Update validation request status
                        validation_request.current_status_id = approved_status.value_id

                        # Create status history entry
                        create_status_history_entry(
                            db=db,
                            request_id=validation_request.request_id,
                            old_status_id=old_status_id,
                            new_status_id=approved_status.value_id,
                            changed_by_id=current_user.user_id,
                            change_reason="Auto-transitioned: All required approvals complete"
                        )

                        # Update linked model version statuses
                        update_version_statuses_for_validation(
                            db=db,
                            validation_request=validation_request,
                            new_validation_status="APPROVED",
                            current_user=current_user
                        )

                        # Create audit log for status transition
                        status_audit = AuditLog(
                            entity_type="ValidationRequest",
                            entity_id=validation_request.request_id,
                            action="STATUS_AUTO_TRANSITION",
                            user_id=current_user.user_id,
                            changes={
                                "old_status": "PENDING_APPROVAL",
                                "new_status": "APPROVED",
                                "reason": "All required approvals complete",
                                "final_approval_id": approval_id
                            },
                            timestamp=utc_now()
                        )
                        db.add(status_audit)

                        # Auto-close Type 3 exceptions for models in this validation
                        # (only for full validations, not interim)
                        autoclose_type3_on_full_validation_approved(db, validation_request)

    # ===== UPDATE MODEL APPROVAL STATUS =====
    # Recalculate approval status for all models in this validation request
    # and record history if status changed
    if validation_request:
        from app.core.model_approval_status import update_model_approval_status_if_changed
        for model in validation_request.models:
            update_model_approval_status_if_changed(
                model=model,
                db=db,
                trigger_type="APPROVAL_SUBMITTED",
                trigger_entity_type="ValidationApproval",
                trigger_entity_id=approval_id,
                notes=f"Approval submitted with status: {update_data.approval_status}"
            )

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
    if not is_admin(current_user):
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
    approval.unlinked_at = utc_now()
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
        timestamp=utc_now()
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
        # For days_in_status calculation
        joinedload(ValidationRequest.status_history)
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
        User.role_code.in_([RoleCode.VALIDATOR.value, RoleCode.ADMIN.value])
    ).all()

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
            ).scalar_subquery()
        )

        workload_data.append({
            "validator_id": validator.user_id,
            "validator_name": validator.full_name,
            "active_assignments": active_assignments,
            "role": validator.role_display
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

    IMPORTANT: Hold time is excluded from SLA calculations. Requests that have been
    on hold have their effective days reduced by the total hold duration.
    """
    check_admin(current_user)

    # Get all active (non-terminal) validation requests with submission received
    # NOTE: Lead time is now computed per-request via applicable_lead_time_days
    # which returns MAX across all models' risk tier policies
    # NOTE: status_history is needed to compute total_hold_days
    requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.new_status)
    ).filter(
        ValidationRequest.submission_received_date.isnot(None),
        ValidationRequest.current_status.has(
            TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"])
        )
    ).all()

    violations = []
    now = utc_now()

    for req in requests:
        if not req.models:
            continue

        # Use applicable_lead_time_days which computes MAX across all models' policies
        # This is the most conservative (longest) lead time for multi-model requests
        lead_time_days = req.applicable_lead_time_days

        # Calculate days since submission, EXCLUDING hold time
        # Team should not be penalized for periods when work was paused
        if not req.submission_received_date:
            continue
        raw_days_since_submission = (now.date() - req.submission_received_date).days
        effective_days_since_submission = raw_days_since_submission - req.total_hold_days

        # Check if lead time has been exceeded (using effective days)
        if effective_days_since_submission > lead_time_days:
            # For multi-model requests, show all model names
            model_names = [m.model_name for m in req.models]
            model_name = ", ".join(model_names) if len(model_names) > 1 else model_names[0]
            days_overdue = effective_days_since_submission - lead_time_days

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
                "actual_days": effective_days_since_submission,
                "raw_days": raw_days_since_submission,  # Total calendar days
                "hold_days": req.total_hold_days,  # Days excluded from SLA
                "days_overdue": days_overdue,
                "current_status": req.current_status.label if req.current_status else "Unknown",
                "priority": req.priority.label if req.priority else "Unknown",
                "severity": severity,
                "timestamp": f"{req.submission_received_date.isoformat()}T00:00:00"
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
    now = utc_now()

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
            detail="Can only mark submission for periodic revalidations (COMPREHENSIVE)"
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
        timestamp=utc_now()
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


@router.get("/my-overdue-items")
def get_my_overdue_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overdue SUBMISSION items for the current user's models.
    Returns only PRE_SUBMISSION overdue items where the current user
    is the model owner - i.e., models awaiting documentation submission.

    Note: VALIDATION_IN_PROGRESS overdue items are NOT returned here.
    Once the model owner submits documentation, the validation team
    is responsible for completing the validation and providing any
    overdue commentary via a separate validator endpoint.

    Available to all authenticated users.
    """
    today = date.today()
    results = []

    # Part 1: Find overdue SUBMISSIONS for user's models
    # Use SQLAlchemy 2.0-style query with unique() to prevent duplicate rows from joinedload
    pending_requests = db.execute(
        select(ValidationRequest).options(
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.owner),
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.risk_tier),
            joinedload(ValidationRequest.current_status),
            joinedload(ValidationRequest.validation_type)
        ).filter(
            ValidationRequest.validation_type.has(
                TaxonomyValue.code == "COMPREHENSIVE"),
            ValidationRequest.submission_received_date.is_(None),
            ValidationRequest.current_status.has(
                TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
        )
    ).scalars().unique().all()

    for req in pending_requests:
        # Check if past due or past grace
        is_past_due = req.submission_due_date and today > req.submission_due_date
        is_past_grace = req.submission_grace_period_end and today > req.submission_grace_period_end

        if is_past_due or is_past_grace:
            if req.model_versions_assoc and len(req.model_versions_assoc) > 0:
                model_assoc = req.model_versions_assoc[0]
                model = model_assoc.model

                # Only include if current user is the model owner
                if model.owner_id != current_user.user_id:
                    continue

                # Calculate days overdue and urgency
                if is_past_grace and req.submission_grace_period_end:
                    days_overdue = (today - req.submission_grace_period_end).days
                    urgency = "overdue"
                elif req.submission_due_date:
                    days_overdue = (today - req.submission_due_date).days
                    urgency = "in_grace_period"
                else:
                    continue

                # Get commentary status
                commentary = get_commentary_status_for_request(
                    db, req.request_id, "PRE_SUBMISSION"
                )

                results.append({
                    "overdue_type": "PRE_SUBMISSION",
                    "request_id": req.request_id,
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "risk_tier": model.risk_tier.label if model.risk_tier else None,
                    "due_date": req.submission_due_date,
                    "grace_period_end": req.submission_grace_period_end,
                    "days_overdue": days_overdue,
                    "urgency": urgency,
                    "current_status": req.current_status.label if req.current_status else "Unknown",
                    "comment_status": commentary["comment_status"],
                    "latest_comment": commentary["latest_comment"],
                    "latest_comment_date": commentary["latest_comment_date"],
                    "target_date": commentary["target_date_from_comment"],
                    "needs_comment_update": commentary["needs_comment_update"]
                })

    # Note: VALIDATION_IN_PROGRESS overdue items are NOT shown to model owners.
    # Once the model owner has submitted documentation, the validation team
    # (validators) are responsible for providing overdue commentary.
    # Validators see their overdue items via /my-validator-overdue-items endpoint.

    # Sort by urgency then days overdue
    return sorted(results, key=lambda x: (0 if x["urgency"] == "overdue" else 1, -x["days_overdue"]))


@router.get("/my-validator-overdue-items")
def get_my_validator_overdue_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overdue VALIDATION items for validations assigned to the current user.
    Returns only VALIDATION_IN_PROGRESS overdue items where the current user
    is an assigned validator - i.e., validations they're working on that are
    past their target completion date.

    Note: PRE_SUBMISSION overdue items are NOT returned here.
    Those are the responsibility of model owners/developers and
    are shown via the /my-overdue-items endpoint.

    Available to all authenticated users (primarily validators).
    """
    today = date.today()
    results = []

    # Find validations where:
    # 1. Current user is an assigned validator
    # 2. Documentation has been submitted (submission_received_date is set)
    # 3. Validation is past target completion date
    # 4. Validation is not yet approved/cancelled
    # Use SQLAlchemy 2.0-style query with unique() to prevent duplicate rows from joinedload
    assigned_requests = db.execute(
        select(ValidationRequest).options(
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.risk_tier),
            joinedload(ValidationRequest.current_status),
            joinedload(ValidationRequest.validation_type),
            joinedload(ValidationRequest.assignments).joinedload(ValidationAssignment.validator)
        ).filter(
            ValidationRequest.validation_type.has(
                TaxonomyValue.code == "COMPREHENSIVE"),
            ValidationRequest.submission_received_date.isnot(None),  # Submitted
            ValidationRequest.current_status.has(
                TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"]))
        )
    ).scalars().unique().all()

    for req in assigned_requests:
        # Check if current user is an assigned validator for this request
        is_assigned = any(
            assignment.validator_id == current_user.user_id
            for assignment in req.assignments
        )
        if not is_assigned:
            continue

        # Check if past validation due date
        if not (req.model_validation_due_date and today > req.model_validation_due_date):
            continue

        # Get model info
        if not req.model_versions_assoc:
            continue
        model_assoc = req.model_versions_assoc[0]
        model = model_assoc.model

        days_overdue = (today - req.model_validation_due_date).days

        # Get commentary status
        commentary = get_commentary_status_for_request(
            db, req.request_id, "VALIDATION_IN_PROGRESS"
        )

        results.append({
            "overdue_type": "VALIDATION_IN_PROGRESS",
            "request_id": req.request_id,
            "model_id": model.model_id,
            "model_name": model.model_name,
            "risk_tier": model.risk_tier.label if model.risk_tier else None,
            "due_date": req.model_validation_due_date,
            "grace_period_end": None,
            "days_overdue": days_overdue,
            "urgency": "overdue",
            "current_status": req.current_status.label if req.current_status else "Unknown",
            "comment_status": commentary["comment_status"],
            "latest_comment": commentary["latest_comment"],
            "latest_comment_date": commentary["latest_comment_date"],
            "target_date": commentary["target_date_from_comment"],
            "needs_comment_update": commentary["needs_comment_update"]
        })

    # Sort by days overdue (most urgent first)
    return sorted(results, key=lambda x: -x["days_overdue"])


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
    # Use SQLAlchemy 2.0-style query with unique() to prevent duplicate rows from joinedload
    pending_requests = db.execute(
        select(ValidationRequest).options(
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.owner),
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.risk_tier),
            joinedload(ValidationRequest.current_status),
            joinedload(ValidationRequest.validation_type)
        ).filter(
            ValidationRequest.validation_type.has(
                TaxonomyValue.code == "COMPREHENSIVE"),
            ValidationRequest.submission_received_date.is_(None),
            ValidationRequest.current_status.has(
                TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
        )
    ).scalars().unique().all()

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
                if is_past_grace and req.submission_grace_period_end:
                    days_overdue = (
                        today - req.submission_grace_period_end).days
                    urgency = "overdue"  # Past grace period
                elif req.submission_due_date:
                    days_overdue = (today - req.submission_due_date).days
                    urgency = "in_grace_period"  # Past due but in grace
                else:
                    continue

                # Get commentary status for pre-submission overdue
                commentary = get_commentary_status_for_request(
                    db, req.request_id, "PRE_SUBMISSION"
                )

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
                    "current_status": req.current_status.label if req.current_status else "Unknown",
                    # Commentary fields
                    "comment_status": commentary["comment_status"],
                    "latest_comment": commentary["latest_comment"],
                    "latest_comment_date": commentary["latest_comment_date"],
                    "target_submission_date": commentary["target_date_from_comment"].isoformat() if commentary["target_date_from_comment"] else None,
                    "needs_comment_update": commentary["needs_comment_update"]
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
    # Use SQLAlchemy 2.0-style query with unique() to prevent duplicate rows from joinedload
    active_requests = db.execute(
        select(ValidationRequest).options(
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.owner),
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.risk_tier),
            joinedload(ValidationRequest.current_status),
            joinedload(ValidationRequest.validation_type)
        ).filter(
            ValidationRequest.validation_type.has(
                TaxonomyValue.code == "COMPREHENSIVE"),
            ValidationRequest.current_status.has(
                TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"]))
        )
    ).scalars().unique().all()

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

                # Get commentary status for validation in progress overdue
                commentary = get_commentary_status_for_request(
                    db, req.request_id, "VALIDATION_IN_PROGRESS"
                )

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
                    "current_status": req.current_status.label if req.current_status else "Unknown",
                    # Commentary fields
                    "comment_status": commentary["comment_status"],
                    "latest_comment": commentary["latest_comment"],
                    "latest_comment_date": commentary["latest_comment_date"],
                    "target_completion_date": commentary["target_date_from_comment"].isoformat() if commentary["target_date_from_comment"] else None,
                    "needs_comment_update": commentary["needs_comment_update"]
                })

    # Sort by days overdue (most overdue first)
    return sorted(results, key=lambda x: x["days_overdue"], reverse=True)


@router.get("/dashboard/my-overdue-items")
def get_dashboard_my_overdue_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overdue items the current user is responsible for.

    Returns:
    - Pre-submission overdue items where user is model owner, developer, or delegate
    - In-progress validation overdue items where user is assigned validator

    Available to all users (filtered to their responsibilities).
    """
    today = date.today()
    results = []

    # PART 1: Pre-submission overdue (user is owner/developer/delegate)
    # Get models where user is owner or developer
    user_model_ids = db.query(Model.model_id).filter(
        or_(
            Model.owner_id == current_user.user_id,
            Model.developer_id == current_user.user_id
        )
    ).all()
    user_model_ids = [m[0] for m in user_model_ids]

    # Also get models where user is a delegate
    delegate_model_ids = db.query(ModelDelegate.model_id).filter(
        ModelDelegate.user_id == current_user.user_id,
        ModelDelegate.revoked_at.is_(None)
    ).all()
    delegate_model_ids = [m[0] for m in delegate_model_ids]

    # Combine all model IDs
    responsible_model_ids = list(set(user_model_ids + delegate_model_ids))

    if responsible_model_ids:
        # Find pre-submission overdue requests for these models
        pre_sub_requests = db.query(ValidationRequest).options(
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.owner),
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.risk_tier),
            joinedload(ValidationRequest.current_status)
        ).join(
            ValidationRequestModelVersion
        ).filter(
            ValidationRequestModelVersion.model_id.in_(responsible_model_ids),
            ValidationRequest.submission_received_date.is_(None),
            ValidationRequest.current_status.has(
                TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
        ).all()

        for req in pre_sub_requests:
            is_past_due = req.submission_due_date and today > req.submission_due_date
            is_past_grace = req.submission_grace_period_end and today > req.submission_grace_period_end

            if is_past_due or is_past_grace:
                if req.model_versions_assoc and len(req.model_versions_assoc) > 0:
                    model = req.model_versions_assoc[0].model

                    if is_past_grace and req.submission_grace_period_end:
                        days_overdue = (today - req.submission_grace_period_end).days
                    elif req.submission_due_date:
                        days_overdue = (today - req.submission_due_date).days
                    else:
                        continue

                    # Get commentary status
                    commentary = get_commentary_status_for_request(
                        db, req.request_id, "PRE_SUBMISSION"
                    )

                    # Determine user's role for this item
                    user_role = "delegate"
                    if model.owner_id == current_user.user_id:
                        user_role = "owner"
                    elif model.developer_id == current_user.user_id:
                        user_role = "developer"

                    results.append({
                        "overdue_type": "PRE_SUBMISSION",
                        "request_id": req.request_id,
                        "model_id": model.model_id,
                        "model_name": model.model_name,
                        "risk_tier": model.risk_tier.label if model.risk_tier else None,
                        "days_overdue": days_overdue,
                        "due_date": req.submission_due_date,
                        "user_role": user_role,
                        "current_status": req.current_status.label if req.current_status else "Unknown",
                        "comment_status": commentary["comment_status"],
                        "latest_comment": commentary["latest_comment"],
                        "latest_comment_date": commentary["latest_comment_date"],
                        "target_date": commentary["target_date_from_comment"].isoformat() if commentary["target_date_from_comment"] else None,
                        "needs_comment_update": commentary["needs_comment_update"]
                    })

    # PART 2: Validation in-progress overdue (user is assigned validator)
    validator_requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model
        ).joinedload(Model.owner),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model
        ).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.current_status)
    ).join(
        ValidationAssignment
    ).filter(
        ValidationAssignment.validator_id == current_user.user_id,
        ValidationRequest.current_status.has(
            TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"]))
    ).all()

    for req in validator_requests:
        if req.model_validation_due_date and today > req.model_validation_due_date:
            if req.model_versions_assoc and len(req.model_versions_assoc) > 0:
                model = req.model_versions_assoc[0].model

                days_overdue = (today - req.model_validation_due_date).days

                # Get commentary status
                commentary = get_commentary_status_for_request(
                    db, req.request_id, "VALIDATION_IN_PROGRESS"
                )

                results.append({
                    "overdue_type": "VALIDATION_IN_PROGRESS",
                    "request_id": req.request_id,
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "risk_tier": model.risk_tier.label if model.risk_tier else None,
                    "days_overdue": days_overdue,
                    "due_date": req.model_validation_due_date,
                    "user_role": "validator",
                    "current_status": req.current_status.label if req.current_status else "Unknown",
                    "comment_status": commentary["comment_status"],
                    "latest_comment": commentary["latest_comment"],
                    "latest_comment_date": commentary["latest_comment_date"],
                    "target_date": commentary["target_date_from_comment"].isoformat() if commentary["target_date_from_comment"] else None,
                    "needs_comment_update": commentary["needs_comment_update"]
                })

    # Sort by needs_comment_update first (items needing update at top), then by days_overdue
    return sorted(results, key=lambda x: (0 if x["needs_comment_update"] else 1, -x["days_overdue"]))


@router.get("/dashboard/upcoming-revalidations")
def get_upcoming_revalidations(
    days_ahead: int = Query(
        90, description="Look ahead this many days for upcoming revalidations"),
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
    if not is_admin(current_user):
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
        ValidationRequest.validation_type.has(
            TaxonomyValue.code == "COMPREHENSIVE"),
        ValidationRequest.submission_received_date.is_(None),
        ValidationRequest.current_status.has(
            TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
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
    urgency_order = {"overdue": 0, "in_grace_period": 1,
                     "due_soon": 2, "upcoming": 3, "unknown": 4}
    return sorted(filtered_results, key=lambda x: (urgency_order.get(x["urgency"], 4), x["days_until_submission_due"] or 999))


@router.get("/my-pending-approvals")
def get_my_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get validation requests pending approval by the current user.

    For Global Approvers: Returns validation requests where they have a pending Global approval
    For Regional Approvers: Returns validation requests where they have a pending Regional approval
    For Admins: Returns all validation requests with any pending approvals

    Only returns requests in PENDING_APPROVAL status.
    """
    from app.core.roles import is_admin, is_global_approver, is_regional_approver

    # Common joinedload options for all queries
    approval_options = [
        joinedload(ValidationApproval.request).joinedload(ValidationRequest.models),
        joinedload(ValidationApproval.request).joinedload(ValidationRequest.current_status),
        joinedload(ValidationApproval.request).joinedload(ValidationRequest.validation_type),
        joinedload(ValidationApproval.request).joinedload(ValidationRequest.priority),
        joinedload(ValidationApproval.request).joinedload(ValidationRequest.requestor),
        joinedload(ValidationApproval.request).joinedload(ValidationRequest.assignments).joinedload(ValidationAssignment.validator),
        joinedload(ValidationApproval.approver),
        joinedload(ValidationApproval.represented_region)
    ]

    # Query validation requests with pending approvals assigned to current user
    if is_admin(current_user):
        # Admin can see all pending approvals
        pending_approvals = db.query(ValidationApproval).options(
            *approval_options
        ).filter(
            ValidationApproval.approval_status == "Pending",
            ValidationApproval.voided_at.is_(None),
            ValidationApproval.approval_type.in_(["Global", "Regional"])  # Exclude conditional
        ).all()

    elif is_global_approver(current_user):
        # Global approvers see their assigned Global approvals
        pending_approvals = db.query(ValidationApproval).options(
            *approval_options
        ).filter(
            ValidationApproval.approver_id == current_user.user_id,
            ValidationApproval.approval_status == "Pending",
            ValidationApproval.voided_at.is_(None),
            ValidationApproval.approval_type == "Global"
        ).all()

    elif is_regional_approver(current_user):
        # Regional approvers see their assigned Regional approvals
        pending_approvals = db.query(ValidationApproval).options(
            *approval_options
        ).filter(
            ValidationApproval.approver_id == current_user.user_id,
            ValidationApproval.approval_status == "Pending",
            ValidationApproval.voided_at.is_(None),
            ValidationApproval.approval_type == "Regional"
        ).all()

    else:
        # Other roles don't have approval responsibilities
        pending_approvals = []

    # Build response with validation request details
    results = []
    seen_request_ids = set()

    for approval in pending_approvals:
        vr = approval.request
        if not vr or vr.request_id in seen_request_ids:
            continue

        # Only include requests that are in PENDING_APPROVAL status
        if vr.current_status and vr.current_status.code != "PENDING_APPROVAL":
            continue

        seen_request_ids.add(vr.request_id)

        # Get model names
        model_names = [m.model_name for m in vr.models] if vr.models else []

        # Calculate days in status
        days_in_status = None
        if vr.status_history:
            latest_history = max(vr.status_history, key=lambda h: h.changed_at, default=None)
            if latest_history:
                days_in_status = (date.today() - latest_history.changed_at.date()).days

        # Get requestor name
        requestor_name = vr.requestor.full_name if vr.requestor else None

        # Get primary validator
        primary_validator = None
        for assignment in vr.assignments or []:
            if assignment.is_primary and assignment.validator:
                primary_validator = assignment.validator.full_name
                break

        # Calculate days pending (how long has this approval been waiting)
        days_pending = (date.today() - approval.created_at.date()).days if approval.created_at else 0

        # Get represented region name
        represented_region = None
        if approval.represented_region:
            represented_region = approval.represented_region.name

        results.append({
            "approval_id": approval.approval_id,
            "request_id": vr.request_id,
            "model_ids": [m.model_id for m in vr.models] if vr.models else [],
            "model_names": model_names,
            "validation_type": vr.validation_type.label if vr.validation_type else None,
            "priority": vr.priority.label if vr.priority else None,
            "current_status": vr.current_status.label if vr.current_status else None,
            "requestor_name": requestor_name,
            "primary_validator": primary_validator,
            "target_completion_date": vr.target_completion_date.isoformat() if vr.target_completion_date else None,
            "approval_type": approval.approval_type,
            "approver_role": approval.approver_role,
            "is_required": approval.is_required,
            "represented_region": represented_region,
            "days_pending": days_pending,
            "request_date": vr.request_date.isoformat() if vr.request_date else None,
        })

    # Sort by days pending (longest first)
    return sorted(results, key=lambda x: (x["days_pending"] or 0), reverse=True)


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
            timestamp=utc_now()
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
        joinedload(ValidationPlan.components).joinedload(
            ValidationPlanComponent.component_definition)
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

    expectation_field = tier_to_field.get(
        new_risk_tier_code, "expectation_medium")

    for plan in plans:
        components_updated = False

        for component in plan.components:
            comp_def = component.component_definition

            # Get new default expectation based on new risk tier
            old_default_expectation = component.default_expectation
            new_default_expectation = getattr(
                comp_def, expectation_field, "NotExpected")

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
    required_region_codes: Optional[List[str]] = None,
    validation_type_code: Optional[str] = None
) -> tuple[bool, List[str]]:
    """
    Validate that a validation plan meets compliance requirements before submission.

    Checks:
    1. All components marked as deviation must have rationale
    2. If material_deviation_from_standard is true, must have overall_deviation_rationale
    3. (Optional) Plan existence required when configured per-region
    4. Component 9b (Monitoring Plan Review) validation - only for full plan types

    Note: For scope-only validation types (TARGETED, INTERIM), component-level checks
    are skipped since these types only have scope summaries, not component planning.

    Returns: (is_valid, list_of_error_messages)
    """
    errors = []

    # Get the validation plan with component definitions
    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components).joinedload(ValidationPlanComponent.component_definition)
    ).filter(ValidationPlan.request_id == request_id).first()

    if not plan:
        if require_plan:
            regions_list = ", ".join(required_region_codes or [])
            if regions_list:
                errors.append(
                    f"Validation plan is required for regions: {regions_list}")
            else:
                errors.append(
                    "Validation plan is required for this validation request")
        return len(errors) == 0, errors

    # Check if material deviation has rationale
    if plan.material_deviation_from_standard:
        if not plan.overall_deviation_rationale or not plan.overall_deviation_rationale.strip():
            errors.append(
                "Material deviation from standard is marked, but no overall deviation rationale provided"
            )

    # For scope-only validation types (TARGETED, INTERIM), skip component-level checks
    # These types only have scope summaries, not component-level planning
    is_scope_only = validation_type_code in SCOPE_ONLY_VALIDATION_TYPES

    if not is_scope_only:
        # Check all component deviations have rationale
        for comp in plan.components:
            if comp.is_deviation:
                if not comp.rationale or not comp.rationale.strip():
                    errors.append(
                        f"Component {comp.component_definition.component_code} ({comp.component_definition.component_title}) "
                        f"is marked as deviation but has no rationale"
                    )

    # ===== COMPONENT 9b VALIDATION (Performance Monitoring Plan Review) =====
    # Skip for scope-only validation types
    if is_scope_only:
        return len(errors) == 0, errors
    # Find component 9b in the plan
    comp_9b = next(
        (c for c in plan.components if c.component_definition.component_code == "9b"),
        None
    )

    if comp_9b:
        planned_treatment = comp_9b.planned_treatment
        expectation = comp_9b.default_expectation

        if planned_treatment == "Planned":
            # If marked as Planned, must have a valid monitoring_plan_version_id
            if not comp_9b.monitoring_plan_version_id:
                errors.append(
                    "Component 9b (Performance Monitoring Plan Review) is marked as 'Planned' but no "
                    "monitoring plan version is selected. Please select a version to review."
                )
            else:
                # Verify the version still exists and is valid
                from app.models.monitoring import MonitoringPlanVersion
                version = db.query(MonitoringPlanVersion).filter(
                    MonitoringPlanVersion.version_id == comp_9b.monitoring_plan_version_id
                ).first()
                if not version:
                    errors.append(
                        f"Component 9b (Performance Monitoring Plan Review): Selected monitoring plan "
                        f"version (ID: {comp_9b.monitoring_plan_version_id}) no longer exists."
                    )

        elif planned_treatment == "NotPlanned" and expectation == "Required":
            # If Required and marked NotPlanned, must have rationale
            if not comp_9b.rationale or not comp_9b.rationale.strip():
                errors.append(
                    "Component 9b (Performance Monitoring Plan Review) is 'Required' for this risk tier "
                    "but marked as 'Not Planned'. A rationale is required to justify this deviation."
                )

        # NotApplicable is allowed when no monitoring plan covers the model(s)
        # This is validated at form level, not blocking transition

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

    For scope-only validation types (TARGETED, INTERIM), only the overall_scope_summary
    is captured - no component-level planning is required.
    """
    check_validator_or_admin(current_user)

    # Get validation request with validation type
    request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.validation_type)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Determine if this is a scope-only plan based on validation type
    validation_type_code = request.validation_type.code if request.validation_type else None
    is_scope_only = validation_type_code in SCOPE_ONLY_VALIDATION_TYPES

    # Check if plan already exists
    existing_plan = db.query(ValidationPlan).filter(
        ValidationPlan.request_id == request_id).first()
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

    # For scope-only plans, force material deviation to false (no components to deviate from)
    # For full plans, validate material deviation rationale
    if is_scope_only:
        material_deviation = False
        deviation_rationale = None
    else:
        if plan_data.material_deviation_from_standard and not plan_data.overall_deviation_rationale:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="overall_deviation_rationale is required when material_deviation_from_standard is true"
            )
        material_deviation = plan_data.material_deviation_from_standard
        deviation_rationale = plan_data.overall_deviation_rationale

    # Create validation plan
    new_plan = ValidationPlan(
        request_id=request_id,
        overall_scope_summary=plan_data.overall_scope_summary,
        material_deviation_from_standard=material_deviation,
        overall_deviation_rationale=deviation_rationale
    )
    db.add(new_plan)
    db.flush()  # Get plan_id

    # For scope-only plans, skip component creation entirely
    if is_scope_only:
        db.commit()
        db.refresh(new_plan)

        # Build response for scope-only plan
        response_data = ValidationPlanResponse.model_validate(new_plan)
        response_data.is_scope_only = True
        response_data.validation_type_code = validation_type_code
        response_data.model_id = first_model.model_id
        response_data.model_name = first_model.model_name
        response_data.risk_tier = first_model.risk_tier.label if first_model.risk_tier else "Unknown"
        response_data.validation_approach = "Scope-Only"
        return response_data

    # Get all component definitions (for full plans only)
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
            default_expectation = get_expectation_for_tier(
                comp_def, risk_tier_code)

            # Calculate deviation
            is_deviation = calculate_is_deviation(
                default_expectation, comp_data.planned_treatment)

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
            joinedload(ValidationPlan.components).joinedload(
                ValidationPlanComponent.component_definition),
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
            default_expectation = get_expectation_for_tier(
                comp_def, risk_tier_code)

            # Use template's planned_treatment and rationale
            planned_treatment = template_comp.planned_treatment
            rationale = template_comp.rationale

            # Recalculate is_deviation based on CURRENT expectation
            is_deviation = calculate_is_deviation(
                default_expectation, planned_treatment)

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
            timestamp=utc_now()
        )
        db.add(audit_log)

    else:
        # Auto-create all components with defaults
        for comp_def in all_components:
            default_expectation = get_expectation_for_tier(
                comp_def, risk_tier_code)

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
    }
    response_data.validation_approach = tier_to_approach.get(
        risk_tier_code, "Standard")

    # Set scope-only indicator for full plans
    response_data.is_scope_only = False
    response_data.validation_type_code = validation_type_code

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
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not current_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Get active configuration for comparison
    active_config = db.query(ComponentDefinitionConfiguration).filter_by(
        is_active=True).first()
    active_config_id = active_config.config_id if active_config else None

    # Extract model IDs from current request
    current_model_ids = {
        assoc.model.model_id for assoc in current_request.model_versions_assoc if assoc.model}

    if not current_model_ids:
        return PlanTemplateSuggestionsResponse(has_suggestions=False, suggestions=[])

    # Find previous validations with same validation type and overlapping models
    # Must be APPROVED status and have a plan
    validation_type_id = current_request.validation_type.value_id if current_request.validation_type else None

    if not validation_type_id:
        return PlanTemplateSuggestionsResponse(has_suggestions=False, suggestions=[])

    # Query for potential template sources
    potential_templates = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.validation_plan).joinedload(
            ValidationPlan.components),
        joinedload(ValidationRequest.validation_plan).joinedload(
            ValidationPlan.configuration),
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.validation_type)
    ).filter(
        ValidationRequest.request_id != request_id,  # Not current request
        ValidationRequest.validation_type_id == validation_type_id,  # Same validation type
        ValidationRequest.current_status.has(
            code="APPROVED"),  # Only approved validations
        ValidationRequest.validation_plan != None  # Has a plan
    ).order_by(ValidationRequest.completion_date.desc()).limit(5).all()

    suggestions = []

    for template_request in potential_templates:
        # Check if models overlap
        template_model_ids = {
            assoc.model.model_id for assoc in template_request.model_versions_assoc if assoc.model}

        if not current_model_ids.intersection(template_model_ids):
            continue  # No overlapping models, skip

        plan = template_request.validation_plan
        if not plan:
            continue

        # Count deviations
        deviations_count = sum(
            1 for comp in plan.components if comp.is_deviation)

        # Get primary validator name (first assigned validator)
        validator_name = None
        if template_request.assignments:
            primary = next(
                (a for a in template_request.assignments if a.is_primary), None)
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
            model_names=[
                assoc.model.model_name for assoc in template_request.model_versions_assoc if assoc.model],
            completion_date=template_request.completion_date.isoformat(
            ) if template_request.completion_date else None,
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
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.validation_type)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Get validation plan
    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components).joinedload(
            ValidationPlanComponent.component_definition)
    ).filter(ValidationPlan.request_id == request_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation plan not found for request {request_id}"
        )

    # Determine if this is a scope-only plan based on validation type
    validation_type_code = request.validation_type.code if request.validation_type else None
    is_scope_only = validation_type_code in SCOPE_ONLY_VALIDATION_TYPES

    # Build response with derived fields
    model = request.model_versions_assoc[0].model if request.model_versions_assoc else None
    response_data = ValidationPlanResponse.model_validate(plan)

    # Set scope-only indicator
    response_data.is_scope_only = is_scope_only
    response_data.validation_type_code = validation_type_code

    if model:
        response_data.model_id = model.model_id
        response_data.model_name = model.model_name
        response_data.risk_tier = model.risk_tier.label if model.risk_tier else "Unknown"

        risk_tier_code = model.risk_tier.code if model.risk_tier else "TIER_2"
        tier_to_approach = {
            "TIER_1": "Comprehensive",
            "TIER_2": "Standard",
            "TIER_3": "Conceptual",
            "TIER_4": "Executive Summary",
        }
        response_data.validation_approach = tier_to_approach.get(
            risk_tier_code, "Standard")

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
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.validation_type)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Get validation plan
    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components).joinedload(
            ValidationPlanComponent.component_definition)
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
    risk_tier_code = model.risk_tier.code if model and model.risk_tier else "TIER_2"
    tier_to_approach = {
        "TIER_1": "Comprehensive",
        "TIER_2": "Standard",
        "TIER_3": "Conceptual",
        "TIER_4": "Executive Summary",
    }
    validation_approach = tier_to_approach.get(risk_tier_code, "Standard")

    validation_type = request.validation_type.label if request.validation_type else "Unknown"
    validation_type_code = request.validation_type.code if request.validation_type else None
    is_scope_only = validation_type_code in SCOPE_ONLY_VALIDATION_TYPES

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
        ('Created:', plan.created_at.strftime(
            '%Y-%m-%d') if plan.created_at else 'N/A'),
        ('Last Updated:', plan.updated_at.strftime(
            '%Y-%m-%d') if plan.updated_at else 'N/A')
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

    # For scope-only plans, add note and skip component-level details
    if is_scope_only:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Validation Plan Type', 0, 1)
        pdf.ln(2)
        pdf.set_font('Arial', 'I', 10)
        pdf.multi_cell(0, 5, f'This is a {validation_type} validation. Component-level planning is not required for this validation type. Only the Overall Scope Summary above defines the validation scope.')
        pdf.ln(5)
    else:
        # Material Deviation Information (full plans only)
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

        # Validation Components by Section (full plans only)
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
                title = comp_def.component_title[:30] + '...' if len(
                    comp_def.component_title) > 30 else comp_def.component_title
                pdf.cell(50, 6, title, 1, 0)

                # Default expectation
                pdf.cell(30, 6, comp.default_expectation, 1, 0)

                # Planned treatment
                treatment_map = {
                    'Planned': 'Planned',
                    'NotPlanned': 'Not Planned',
                    'NotApplicable': 'N/A'
                }
                treatment = treatment_map.get(
                    comp.planned_treatment,
                    comp.planned_treatment or "N/A"
                )
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
                    rationale_text = f"Rationale: {comp.rationale[:100]}..." if len(
                        comp.rationale) > 100 else f"Rationale: {comp.rationale}"
                    pdf.multi_cell(150, 4, rationale_text)
                    pdf.set_font('Arial', '', 8)

            pdf.ln(3)

        # Summary statistics (full plans only)
        total_components = len(plan.components)
        planned_components = sum(
            1 for c in plan.components if c.planned_treatment == 'Planned')
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
        # Clean up temp file after sending
        background=BackgroundTask(os.unlink, temp_file.name)
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
    - Material deviation flag and rationale (full plans only)
    - Individual component planned treatments and rationales (full plans only)

    For scope-only validation types (TARGETED, INTERIM), only overall_scope_summary
    can be updated.
    """
    check_validator_or_admin(current_user)

    # Get validation request with validation type
    request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model).joinedload(Model.risk_tier),
        joinedload(ValidationRequest.validation_type)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Determine if this is a scope-only plan based on validation type
    validation_type_code = request.validation_type.code if request.validation_type else None
    is_scope_only = validation_type_code in SCOPE_ONLY_VALIDATION_TYPES

    # Get validation plan
    plan = db.query(ValidationPlan).options(
        joinedload(ValidationPlan.components).joinedload(
            ValidationPlanComponent.component_definition)
    ).filter(ValidationPlan.request_id == request_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation plan not found for request {request_id}"
        )

    # Update plan header fields
    if plan_updates.overall_scope_summary is not None:
        plan.overall_scope_summary = plan_updates.overall_scope_summary

    # For scope-only plans, skip material deviation and component updates
    if is_scope_only:
        # Force material deviation to false for scope-only plans
        plan.material_deviation_from_standard = False
        plan.overall_deviation_rationale = None

        db.commit()
        db.refresh(plan)

        # Build response for scope-only plan
        model = request.model_versions_assoc[0].model if request.model_versions_assoc else None
        response_data = ValidationPlanResponse.model_validate(plan)
        response_data.is_scope_only = True
        response_data.validation_type_code = validation_type_code
        if model:
            response_data.model_id = model.model_id
            response_data.model_name = model.model_name
            response_data.risk_tier = model.risk_tier.label if model.risk_tier else "Unknown"
        response_data.validation_approach = "Scope-Only"
        return response_data

    # Full plan update logic below
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
        risk_tier_code = model.risk_tier.code if (
            model and model.risk_tier) else "MEDIUM"

        for comp_update in plan_updates.components:
            # Find existing component (match by component_id in update with our plan components)
            plan_comp = next(
                (pc for pc in plan.components if pc.component_id ==
                 comp_update.component_id),
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

            # Component 9b specific fields (Performance Monitoring Plan Review)
            if comp_update.monitoring_plan_version_id is not None:
                # Validate that the version exists
                from app.models.monitoring import MonitoringPlanVersion
                version = db.query(MonitoringPlanVersion).filter(
                    MonitoringPlanVersion.version_id == comp_update.monitoring_plan_version_id
                ).first()
                if not version:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Monitoring plan version {comp_update.monitoring_plan_version_id} not found"
                    )
                plan_comp.monitoring_plan_version_id = comp_update.monitoring_plan_version_id

            if comp_update.monitoring_review_notes is not None:
                plan_comp.monitoring_review_notes = comp_update.monitoring_review_notes

    db.commit()
    db.refresh(plan)

    # Build response
    model = request.model_versions_assoc[0].model if request.model_versions_assoc else None
    response_data = ValidationPlanResponse.model_validate(plan)

    if model:
        response_data.model_id = model.model_id
        response_data.model_name = model.model_name
        response_data.risk_tier = model.risk_tier.label if model.risk_tier else "Unknown"

        risk_tier_code = model.risk_tier.code if model.risk_tier else "TIER_2"
        tier_to_approach = {
            "TIER_1": "Comprehensive",
            "TIER_2": "Standard",
            "TIER_3": "Conceptual",
            "TIER_4": "Executive Summary",
        }
        response_data.validation_approach = tier_to_approach.get(
            risk_tier_code, "Standard")

    # Add scope-only indicator for full plans
    response_data.is_scope_only = False
    response_data.validation_type_code = validation_type_code

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
        timestamp=utc_now()
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
    current_active = db.query(ComponentDefinitionConfiguration).filter_by(
        is_active=True).first()
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
    components = db.query(ValidationComponentDefinition).filter_by(
        is_active=True).all()

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
        timestamp=utc_now()
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
        joinedload(ValidationPlan.components).joinedload(
            ValidationPlanComponent.component_definition),
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
                deviation_by_component[comp_code] = deviation_by_component.get(
                    comp_code, 0) + 1

                # By section
                section = comp.component_definition.section_number
                deviation_by_section[section] = deviation_by_section.get(
                    section, 0) + 1

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
                    deviations_over_time[month_key] = deviations_over_time.get(
                        month_key, 0) + 1

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
        [{"component_code": k, "count": v}
            for k, v in deviation_by_component.items()],
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
    deviation_rate = (total_deviations / total_components *
                      100) if total_components > 0 else 0
    plan_deviation_rate = (plans_with_deviations /
                           total_plans * 100) if total_plans > 0 else 0

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


# ==================== CONDITIONAL MODEL USE APPROVALS ====================

@router.get("/requests/{request_id}/additional-approvals", response_model=ConditionalApprovalsEvaluationResponse)
def get_conditional_approvals_evaluation(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get additional approval evaluation for a validation request.

    Returns:
        - required_roles: List of required approver roles with their approval status
        - rules_applied: List of rules that matched and why
        - explanation_summary: English summary of approval requirements
    """
    # Get validation request with models
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation request not found"
        )

    manual_approvals = db.query(ValidationApproval).filter(
        ValidationApproval.request_id == request_id,
        ValidationApproval.approval_type.in_(["Manual-Role", "Manual-User"])
    ).options(
        joinedload(ValidationApproval.approver_role_ref),
        joinedload(ValidationApproval.assigned_approver),
        joinedload(ValidationApproval.manually_added_by)
    ).all()

    manual_approvals_payload = [
        ManualApprovalSummary(
            approval_id=approval.approval_id,
            approval_type=approval.approval_type,
            approval_status=approval.approval_status,
            approver_role_id=approval.approver_role_id,
            approver_role_name=approval.approver_role_ref.role_name if approval.approver_role_ref else None,
            assigned_approver_id=approval.assigned_approver_id,
            assigned_approver_name=approval.assigned_approver.full_name if approval.assigned_approver else None,
            assigned_approver_active=_is_user_active(db, approval.assigned_approver) if approval.assigned_approver else None,
            manually_added_by_name=approval.manually_added_by.full_name if approval.manually_added_by else None,
            manual_add_reason=approval.manual_add_reason,
            manually_added_at=approval.manually_added_at,
            voided_at=approval.voided_at,
            void_reason=approval.void_reason
        )
        for approval in manual_approvals
    ]

    # Use first model as primary model for rule evaluation
    models = validation_request.models
    if not models:
        return ConditionalApprovalsEvaluationResponse(
            required_roles=[],
            rules_applied=[],
            explanation_summary="No models associated with this validation request",
            manual_approvals=manual_approvals_payload
        )

    primary_model = models[0]

    # Evaluate rules
    evaluation_result = get_required_approver_roles(
        db, validation_request, primary_model)

    return ConditionalApprovalsEvaluationResponse(
        required_roles=evaluation_result["required_roles"],
        rules_applied=evaluation_result["rules_applied"],
        explanation_summary=evaluation_result["explanation_summary"],
        manual_approvals=manual_approvals_payload
    )


@router.post("/requests/{request_id}/add-manual-approval", response_model=ManualApprovalResponse)
def add_manual_approval(
    request_id: int,
    data: ManualApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually add an additional approval requirement (Admin only).
    Can add either a role-based or individual user requirement.
    """
    check_admin(current_user)

    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation request not found"
        )

    if validation_request.current_status and validation_request.current_status.code in {"APPROVED", "CANCELLED"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add approvals to request in {validation_request.current_status.code} status"
        )

    approval_type = "Manual-Role"
    target_name = None

    if data.approver_role_id:
        approver_role = db.query(ApproverRole).filter(
            ApproverRole.role_id == data.approver_role_id,
            ApproverRole.is_active == True
        ).first()
        if not approver_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approver role not found or inactive"
            )

        existing = db.query(ValidationApproval).filter(
            ValidationApproval.request_id == request_id,
            ValidationApproval.approver_role_id == data.approver_role_id,
            ValidationApproval.voided_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval requirement for {approver_role.role_name} already exists"
            )

        approval = ValidationApproval(
            request_id=request_id,
            approver_role_id=data.approver_role_id,
            approver_id=None,
            approver_role="Manual",
            approval_type="Manual-Role",
            approval_status="Pending",
            is_required=True,
            manually_added_by_id=current_user.user_id,
            manual_add_reason=data.reason,
            manually_added_at=utc_now(),
            comments=f"Manually added by admin: {data.reason}"
        )
        target_name = approver_role.role_name
    else:
        assigned_user = db.query(User).filter(
            User.user_id == data.assigned_approver_id
        ).first()
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found"
            )

        existing = db.query(ValidationApproval).filter(
            ValidationApproval.request_id == request_id,
            ValidationApproval.assigned_approver_id == data.assigned_approver_id,
            ValidationApproval.voided_at.is_(None)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval requirement for {assigned_user.full_name} already exists"
            )

        approval = ValidationApproval(
            request_id=request_id,
            assigned_approver_id=data.assigned_approver_id,
            approver_id=None,
            approver_role="Manual",
            approval_type="Manual-User",
            approval_status="Pending",
            is_required=True,
            manually_added_by_id=current_user.user_id,
            manual_add_reason=data.reason,
            manually_added_at=utc_now(),
            comments=f"Manually assigned to {assigned_user.full_name}: {data.reason}"
        )
        approval_type = "Manual-User"
        target_name = assigned_user.full_name

    db.add(approval)
    db.flush()

    audit_log = AuditLog(
        entity_type="ValidationApproval",
        entity_id=request_id,
        action="MANUAL_APPROVAL_ADDED",
        user_id=current_user.user_id,
        changes={
            "approval_id": approval.approval_id,
            "approval_type": approval_type,
            "approver_role": approver_role.role_name if data.approver_role_id else None,
            "assigned_approver_name": assigned_user.full_name if data.assigned_approver_id else None,
            "status": "Pending",
            "reason": data.reason
        },
        timestamp=utc_now()
    )
    db.add(audit_log)
    db.commit()

    return ManualApprovalResponse(
        approval_id=approval.approval_id,
        approval_type=approval_type,
        approver_role_name=target_name if data.approver_role_id else None,
        assigned_approver_name=target_name if data.assigned_approver_id else None,
        reason=data.reason,
        added_by=current_user.full_name,
        added_at=approval.manually_added_at,
        message=f"Manual approval requirement added for {target_name}"
    )


@router.post("/approvals/{approval_id}/submit-additional", response_model=SubmitConditionalApprovalResponse)
def submit_conditional_approval(
    approval_id: int,
    approval_data: SubmitConditionalApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit additional approval (Admin or assigned approver).

    Any Admin can approve on behalf of any approver role by providing:
    - approver_role_id: The role being approved
    - approval_status: "Approved" or "Sent Back" (to reject entirely, cancel the workflow instead)
    - approval_evidence: Description of evidence (meeting minutes, email, etc.) [required for Admin proxy approvals]
    - comments: Optional additional comments
    """
    # Get the approval requirement
    approval = db.query(ValidationApproval).filter(
        ValidationApproval.approval_id == approval_id
    ).first()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval requirement not found"
        )

    is_admin_user = is_admin(current_user)
    is_assigned_user = (
        approval.assigned_approver_id is not None and
        approval.assigned_approver_id == current_user.user_id
    )

    if not is_admin_user and not is_assigned_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or the assigned approver can submit this approval"
        )

    approval_evidence = (approval_data.approval_evidence or "").strip()
    comments = (approval_data.comments or "").strip()
    if approval_data.approval_status == "Sent Back" and not comments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comments are required when sending back for revision"
        )
    if not is_assigned_user and not approval_evidence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin must provide approval_evidence when approving on behalf (e.g., meeting minutes, email confirmation)"
        )

    # Verify this is an additional/manual approval (has approver_role_id OR assigned_approver_id)
    is_additional_approval = (
        approval.approver_role_id is not None or
        approval.assigned_approver_id is not None
    )
    if not is_additional_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not an additional approval requirement"
        )

    # Verify the approver_role_id matches (if provided)
    if approval.approver_role_id is not None:
        if approval.approver_role_id != approval_data.approver_role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approver role ID does not match the approval requirement"
            )
    elif approval_data.approver_role_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is a user-assigned approval, approver_role_id should not be provided"
        )

    # Check if already approved or voided
    if approval.voided_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval requirement has been voided"
        )

    if approval.approval_status in ("Approved", "Sent Back"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This approval has already been {approval.approval_status.lower()}"
        )

    # Update approval
    approval.approval_status = approval_data.approval_status
    approval.approver_id = current_user.user_id  # Admin who submitted the approval
    approval.approved_at = utc_now()
    approval.approval_evidence = approval_evidence or None
    approval.comments = comments or None

    # Flush to ensure the update is visible in subsequent queries
    db.flush()

    # If this was the last pending additional approval and status is "Approved",
    # update model.use_approval_date
    if approval_data.approval_status == "Approved":
        from sqlalchemy.orm import joinedload
        validation_request = db.query(ValidationRequest).options(
            joinedload(ValidationRequest.models)
        ).with_for_update(of=ValidationRequest).filter(
            ValidationRequest.request_id == approval.request_id
        ).first()

        if validation_request:
            # Check if all additional approvals are now approved
            all_conditional_approvals = db.query(ValidationApproval).filter(
                ValidationApproval.request_id == approval.request_id,
                or_(
                    ValidationApproval.approver_role_id.isnot(None),
                    ValidationApproval.assigned_approver_id.isnot(None)
                ),
                ValidationApproval.voided_at.is_(None)
            ).all()

            all_approved = all(
                [a.approval_status == "Approved" for a in all_conditional_approvals])

            if all_approved:
                # Update use_approval_date for all models in this validation
                for model in validation_request.models:
                    model.use_approval_date = utc_now()

    approver_role_name = None
    assigned_approver_name = None
    if approval.approver_role_id is not None:
        role = db.query(ApproverRole).filter(
            ApproverRole.role_id == approval.approver_role_id
        ).first()
        approver_role_name = role.role_name if role else None
    if approval.assigned_approver_id is not None:
        assigned_user = db.query(User).filter(
            User.user_id == approval.assigned_approver_id
        ).first()
        assigned_approver_name = assigned_user.full_name if assigned_user else None
    target_label = approver_role_name or assigned_approver_name
    is_proxy_approval = is_admin_user and not is_assigned_user

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationApproval",
        entity_id=approval.request_id,
        action="CONDITIONAL_APPROVAL_SUBMIT",
        user_id=current_user.user_id,
        changes={
            "approval_id": approval_id,
            "approval_type": approval.approval_type,
            "approver_role": approver_role_name,
            "assigned_approver_name": assigned_approver_name,
            "approval_status": approval_data.approval_status,
            "status": approval_data.approval_status,
            "approval_evidence": approval_evidence or None,
            **(
                {
                    "proxy_approval": True,
                    "approved_by_admin": current_user.full_name,
                    "on_behalf_of": target_label or "Approver"
                }
                if is_proxy_approval
                else {}
            )
        },
        timestamp=utc_now()
    )
    db.add(audit_log)

    db.commit()

    return SubmitConditionalApprovalResponse(
        approval_id=approval_id,
        message=f"Additional approval {approval_data.approval_status.lower()} successfully"
    )


@router.post("/approvals/{approval_id}/void", response_model=VoidApprovalRequirementResponse)
def void_approval_requirement(
    approval_id: int,
    void_data: VoidApprovalRequirementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Void an additional approval requirement (Admin only).

    Allows Admin to cancel an approval requirement with justification.
    """
    # Check Admin permission
    check_admin(current_user)

    # Get the approval requirement
    approval = db.query(ValidationApproval).filter(
        ValidationApproval.approval_id == approval_id
    ).first()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval requirement not found"
        )

    # Verify this is an additional/manual approval (has approver_role_id OR assigned_approver_id)
    if approval.approver_role_id is None and approval.assigned_approver_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not an additional approval requirement"
        )

    # Check if already voided
    if approval.voided_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval requirement has already been voided"
        )

    # Void the approval
    approval.voided_by_id = current_user.user_id
    approval.void_reason = void_data.void_reason
    approval.voided_at = utc_now()

    # If model was previously approved, clear the use_approval_date
    # because additional approvals are no longer all complete
    from sqlalchemy.orm import joinedload
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models)
    ).with_for_update(of=ValidationRequest).filter(
        ValidationRequest.request_id == approval.request_id
    ).first()

    if validation_request:
        # Check if any models have use_approval_date set
        for model in validation_request.models:
            if model.use_approval_date:
                # Clear the approval date since approvals are no longer complete
                model.use_approval_date = None

                # Create audit log for model approval reversal
                model_audit = AuditLog(
                    entity_type="Model",
                    entity_id=model.model_id,
                    action="CONDITIONAL_APPROVAL_REVERTED",
                    user_id=current_user.user_id,
                    changes={
                        "reason": f"Additional approval voided: {void_data.void_reason}",
                        "validation_request_id": approval.request_id,
                        "voided_approval_id": approval_id
                    },
                    timestamp=utc_now()
                )
                db.add(model_audit)

    approver_role_name = None
    assigned_approver_name = None
    if approval.approver_role_id is not None:
        role = db.query(ApproverRole).filter(
            ApproverRole.role_id == approval.approver_role_id
        ).first()
        approver_role_name = role.role_name if role else None
    if approval.assigned_approver_id is not None:
        assigned_user = db.query(User).filter(
            User.user_id == approval.assigned_approver_id
        ).first()
        assigned_approver_name = assigned_user.full_name if assigned_user else None

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationApproval",
        entity_id=approval.request_id,
        action="CONDITIONAL_APPROVAL_VOID",
        user_id=current_user.user_id,
        changes={
            "approval_id": approval_id,
            "approval_type": approval.approval_type,
            "approver_role": approver_role_name,
            "assigned_approver_name": assigned_approver_name,
            "status": "Voided",
            "void_reason": void_data.void_reason
        },
        timestamp=utc_now()
    )
    db.add(audit_log)

    db.commit()

    return VoidApprovalRequirementResponse(
        approval_id=approval_id,
        message="Approval requirement voided successfully"
    )


@router.get("/dashboard/pending-additional-approvals")
def get_pending_conditional_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get validation requests with pending additional approval requirements.

    Returns list of validation requests that have:
    - At least one additional approval requirement (role-based or user-based)
    - At least one requirement with status = 'Pending' or null
    - Not voided

    Ordered by days pending (oldest first).
    Admin only.
    """
    check_admin(current_user)

    # Query validation approvals for conditional requirements that are pending
    pending_approvals = db.query(ValidationApproval).filter(
        or_(
            ValidationApproval.approver_role_id.isnot(None),
            ValidationApproval.assigned_approver_id.isnot(None)
        ),
        ValidationApproval.voided_at.is_(None),  # Not voided
        or_(
            ValidationApproval.approval_status == 'Pending',
            ValidationApproval.approval_status.is_(None)
        )
    ).options(
        joinedload(ValidationApproval.request).joinedload(
            ValidationRequest.model_versions_assoc).joinedload(ValidationRequestModelVersion.model),
        joinedload(ValidationApproval.request).joinedload(
            ValidationRequest.validation_type),
        joinedload(ValidationApproval.approver_role_ref),
        joinedload(ValidationApproval.assigned_approver)
    ).all()

    # Group by request_id to avoid duplicates
    requests_map = {}
    for approval in pending_approvals:
        req = approval.request
        req_id = req.request_id

        if req_id not in requests_map:
            # Get model info
            model_name = "Unknown Model"
            model_id = None
            if req.model_versions_assoc and len(req.model_versions_assoc) > 0:
                model = req.model_versions_assoc[0].model
                model_name = model.model_name
                model_id = model.model_id

            # Calculate days pending
            days_pending = (utc_now() - approval.created_at).days

            requests_map[req_id] = {
                "request_id": req_id,
                "model_id": model_id,
                "model_name": model_name,
                "validation_type": req.validation_type.label if req.validation_type else "Unknown",
                "pending_approvals": [],
                "days_pending": days_pending,
                "created_at": req.created_at.isoformat() if req.created_at else None
            }

        # Add this pending approval to the list
        requests_map[req_id]["pending_approvals"].append({
            "approval_id": approval.approval_id,
            "approval_type": approval.approval_type,
            "approver_role_id": approval.approver_role_id,
            "approver_role_name": approval.approver_role_ref.role_name if approval.approver_role_ref else None,
            "assigned_approver_id": approval.assigned_approver_id,
            "assigned_approver_name": approval.assigned_approver.full_name if approval.assigned_approver else None,
            "assigned_approver_active": _is_user_active(db, approval.assigned_approver) if approval.assigned_approver else None,
            "days_pending": (utc_now() - approval.created_at).days
        })

    # Sort by days pending (oldest first)
    results = sorted(requests_map.values(),
                     key=lambda x: x["days_pending"], reverse=True)

    return results


@router.get("/dashboard/my-pending-approvals")
def get_my_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get approvals where the current user is directly assigned (Manual-User type).
    Available to all authenticated users.
    """
    pending_approvals = db.query(ValidationApproval).filter(
        ValidationApproval.assigned_approver_id == current_user.user_id,
        ValidationApproval.voided_at.is_(None),
        or_(
            ValidationApproval.approval_status == 'Pending',
            ValidationApproval.approval_status.is_(None)
        )
    ).options(
        joinedload(ValidationApproval.request).joinedload(
            ValidationRequest.model_versions_assoc).joinedload(ValidationRequestModelVersion.model),
        joinedload(ValidationApproval.manually_added_by)
    ).all()

    results = []
    for approval in pending_approvals:
        req = approval.request
        model_name = "Unknown"
        if req.model_versions_assoc:
            model_name = req.model_versions_assoc[0].model.model_name

        results.append({
            "approval_id": approval.approval_id,
            "request_id": req.request_id,
            "model_name": model_name,
            "reason": approval.manual_add_reason,
            "added_by": approval.manually_added_by.full_name if approval.manually_added_by else "Unknown",
            "added_at": approval.manually_added_at.isoformat() if approval.manually_added_at else None,
            "days_pending": (utc_now() - approval.created_at).days
        })

    return {"pending_approvals": results, "count": len(results)}


@router.get("/dashboard/recent-approvals")
def get_recent_approvals(
    days_back: int = Query(
        30, description="Look back this many days for recent approvals"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recently approved models (models that received final approval).

    For non-Admin users: Returns models where they are owner, developer, or assigned validator.
    For Admin users: Returns all recently approved models.

    Looks for models where Model.use_approval_date was set in the last N days.
    """
    from app.models.model_delegate import ModelDelegate

    cutoff_date = utc_now() - timedelta(days=days_back)

    # Query models with recent use_approval_date
    query = db.query(Model).filter(
        Model.use_approval_date.isnot(None),
        Model.use_approval_date >= cutoff_date
    )

    # For non-Admin users, filter to their models
    if not (is_admin(current_user) or is_validator(current_user)):
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

    # For validators, show models from validations they performed
    if is_validator(current_user):
        # Find validation requests where this user was assigned as validator
        validator_request_ids = select(ValidationRequest.request_id).join(
            ValidationAssignment
        ).where(
            ValidationAssignment.validator_id == current_user.user_id
        ).scalar_subquery()

        # Get model IDs from those requests
        validator_model_ids = select(ValidationRequestModelVersion.model_id).where(
            ValidationRequestModelVersion.request_id.in_(validator_request_ids)
        ).scalar_subquery()

        # Add to query
        query = query.filter(Model.model_id.in_(validator_model_ids))

    models = query.options(
        joinedload(Model.owner),
        joinedload(Model.developer)
    ).order_by(desc(Model.use_approval_date)).limit(50).all()

    results = []
    for model in models:
        # Find the validation request that resulted in this approval
        validation_req = db.query(ValidationRequest).join(
            ValidationRequestModelVersion
        ).filter(
            ValidationRequestModelVersion.model_id == model.model_id
        ).order_by(desc(ValidationRequest.created_at)).first()

        results.append({
            "model_id": model.model_id,
            "model_name": model.model_name,
            "owner_name": model.owner.full_name if model.owner else "Unknown",
            "developer_name": model.developer.full_name if model.developer else None,
            "use_approval_date": model.use_approval_date.isoformat() if model.use_approval_date else None,
            "validation_request_id": validation_req.request_id if validation_req else None,
            "validation_type": validation_req.validation_type.label if validation_req and validation_req.validation_type else "Unknown",
            "days_ago": (utc_now() - model.use_approval_date).days if model.use_approval_date else None
        })

    return results


# ==================== RISK TIER CHANGE IMPACT ENDPOINTS ====================

@router.get("/risk-tier-impact/check/{model_id}", response_model=OpenValidationsCheckResponse)
def check_open_validations_for_risk_tier_change(
    model_id: int,
    proposed_tier_id: Optional[int] = Query(None, description="Proposed new risk tier ID (optional, for warning message)"),
    proposed_tier_code: Optional[str] = Query(None, description="Proposed new tier code (e.g., 'TIER_2') for change detection"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if a model has open validation requests that would be affected by a risk tier change.

    This endpoint should be called before changing a model's risk tier (via Risk Assessment
    finalization or Model Edit) to warn the user about potential impacts.

    Returns:
    - has_open_validations: Whether there are active validation requests AND tier is changing
    - open_validations: List of affected validation request summaries
    - warning_message: Human-readable warning if action needed
    - requires_confirmation: Whether user should confirm before proceeding
    """
    # Get model
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    # Get current tier info
    current_tier_label = None
    current_tier_code = None

    if model.risk_tier_id:
        current_tier = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == model.risk_tier_id).first()
        if current_tier:
            current_tier_label = current_tier.label
            current_tier_code = current_tier.code

    # Get proposed tier info
    proposed_tier_label = None
    effective_proposed_code = proposed_tier_code  # Use code directly if provided

    if proposed_tier_id:
        proposed_tier = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == proposed_tier_id).first()
        if proposed_tier:
            proposed_tier_label = proposed_tier.label
            if not effective_proposed_code:
                effective_proposed_code = proposed_tier.code

    # Check if tier is actually changing
    tier_is_changing = True
    if effective_proposed_code and current_tier_code:
        # Both tiers are known - compare them
        tier_is_changing = (effective_proposed_code != current_tier_code)
    elif effective_proposed_code is None and current_tier_code is None:
        # Both null - no change
        tier_is_changing = False

    # Find open validation requests only if tier is changing
    open_requests = []
    if tier_is_changing:
        open_requests = get_open_validations_for_model(db, model_id)

    # Build summaries
    validation_summaries = []
    for req in open_requests:
        # Get primary validator
        primary_assignment = next(
            (a for a in req.assignments if a.is_primary),
            None
        )

        # Count pending approvals
        pending_count = sum(
            1 for a in req.approvals
            if a.approval_status == "Pending" and a.voided_at is None
        )

        # Check if plan exists
        plan = db.query(ValidationPlan).filter(
            ValidationPlan.request_id == req.request_id
        ).first()

        validation_summaries.append(OpenValidationSummary(
            request_id=req.request_id,
            current_status=req.current_status.label if req.current_status else "Unknown",
            validation_type=req.validation_type.label if req.validation_type else "Unknown",
            has_plan=plan is not None,
            pending_approvals_count=pending_count,
            primary_validator=primary_assignment.validator.full_name if primary_assignment and primary_assignment.validator else None
        ))

    # Build warning message
    warning_message = None
    requires_confirmation = False

    if open_requests:
        requires_confirmation = True
        plan_count = sum(1 for v in validation_summaries if v.has_plan)

        # Count approvals that will actually be voided (only those at PENDING_APPROVAL stage)
        # For earlier stages, approvals will be re-evaluated when they reach that stage
        voided_approval_count = 0
        reevaluate_count = 0
        for req, summary in zip(open_requests, validation_summaries):
            status_code = req.current_status.code if req.current_status else ""
            if status_code == "PENDING_APPROVAL" and summary.pending_approvals_count > 0:
                voided_approval_count += summary.pending_approvals_count
            elif summary.pending_approvals_count > 0:
                # Earlier stages - approvals exist but haven't been formally solicited
                reevaluate_count += 1

        warning_parts = []
        if plan_count > 0:
            warning_parts.append(f"{plan_count} validation plan(s) will be reset")
        if voided_approval_count > 0:
            warning_parts.append(f"{voided_approval_count} pending approval(s) will be voided")
        if reevaluate_count > 0:
            warning_parts.append(f"approval requirements for {reevaluate_count} request(s) will be re-evaluated")

        tier_change_text = ""
        if proposed_tier_label and current_tier_label:
            tier_change_text = f" from '{current_tier_label}' to '{proposed_tier_label}'"

        warning_message = (
            f"Changing the Risk Tier{tier_change_text} will affect {len(open_requests)} "
            f"active validation request(s). "
            + " and ".join(warning_parts) + "."
            if warning_parts else
            f"Changing the Risk Tier{tier_change_text} will affect {len(open_requests)} "
            f"active validation request(s)."
        )

    return OpenValidationsCheckResponse(
        model_id=model_id,
        model_name=model.model_name,
        current_risk_tier=current_tier_label,
        proposed_risk_tier=proposed_tier_label,
        has_open_validations=len(open_requests) > 0,
        open_validation_count=len(open_requests),
        open_validations=validation_summaries,
        warning_message=warning_message,
        requires_confirmation=requires_confirmation
    )


@router.post("/risk-tier-impact/force-reset", response_model=ForceResetResponse)
def force_reset_validation_plans(
    request: ForceResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Force reset validation plans and void approvals after a model's risk tier changes.

    This should be called after confirming the user wants to proceed with a risk tier
    change that affects open validations.

    Requires Admin role and confirm_reset=True to proceed.

    Actions performed:
    1. Delete existing ValidationPlanComponents for affected requests
    2. Regenerate components based on new risk tier's expectations
    3. Void all pending ValidationApprovals for affected requests
    4. Create audit log entries for compliance tracking
    """
    check_admin(current_user)

    if not request.confirm_reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirm_reset must be True to proceed with force reset"
        )

    # Check model exists
    model = db.query(Model).filter(Model.model_id == request.model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {request.model_id} not found"
        )

    # Check new tier exists
    new_tier = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == request.new_risk_tier_id).first()
    if not new_tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk tier {request.new_risk_tier_id} not found"
        )

    # Perform reset
    result = reset_validation_plan_for_tier_change(
        db=db,
        model_id=request.model_id,
        new_tier_id=request.new_risk_tier_id,
        user_id=current_user.user_id,
        force=True
    )

    db.commit()

    # Build message
    if result["reset_count"] == 0:
        message = "No open validation requests found for this model."
    else:
        message = (
            f"Successfully reset {result['reset_count']} validation request(s). "
            f"Regenerated {result['components_regenerated']} plan component(s). "
            f"Voided {result['approvals_voided']} pending approval(s)."
        )

    return ForceResetResponse(
        success=True,
        reset_count=result["reset_count"],
        request_ids=result["request_ids"],
        components_regenerated=result["components_regenerated"],
        approvals_voided=result["approvals_voided"],
        message=message
    )


# ==================== RISK MISMATCH REPORT ENDPOINT ====================

@router.get("/reports/risk-mismatch", response_model=RiskMismatchReportResponse)
def get_risk_mismatch_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a report of models where the current risk tier doesn't match
    the risk tier at the time of their last approved validation.

    This helps identify models that may need revalidation due to risk tier changes
    that occurred after their last validation.

    Returns models where:
    - Model is Active (status = Active or similar)
    - Model has an approved validation request with validated_risk_tier_id set
    - Current risk_tier_id differs from validated_risk_tier_id

    Note: Models with NULL validated_risk_tier_id are excluded as we can't determine
    if there's a mismatch.
    """
    # Get approved status ID
    approved_status = db.query(TaxonomyValue).join(
        Taxonomy, TaxonomyValue.taxonomy_id == Taxonomy.taxonomy_id
    ).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code == "APPROVED"
    ).first()

    if not approved_status:
        return RiskMismatchReportResponse(
            total_models_checked=0,
            models_with_mismatch=0,
            items=[],
            generated_at=utc_now()
        )

    # Get active model status ID
    active_status = db.query(TaxonomyValue).join(
        Taxonomy, TaxonomyValue.taxonomy_id == Taxonomy.taxonomy_id
    ).filter(
        Taxonomy.name == "Model Status",
        TaxonomyValue.code == "ACTIVE"
    ).first()

    # Count active models without loading them all into memory
    total_checked_query = db.query(func.count(Model.model_id)).filter(
        Model.risk_tier_id.isnot(None)
    )
    if active_status:
        total_checked_query = total_checked_query.filter(
            Model.status_id == active_status.value_id
        )
    total_checked = total_checked_query.scalar() or 0

    # Find most recent approved validation per model (skip NULL risk tier snapshots)
    latest_approved_subq = db.query(
        ValidationRequestModelVersion.model_id.label("model_id"),
        ValidationRequest.request_id.label("request_id"),
        ValidationRequest.validated_risk_tier_id.label("validated_risk_tier_id"),
        ValidationRequest.completion_date.label("completion_date"),
        func.row_number().over(
            partition_by=ValidationRequestModelVersion.model_id,
            order_by=nullslast(desc(ValidationRequest.completion_date))
        ).label("rn"),
    ).join(
        ValidationRequest,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequest.current_status_id == approved_status.value_id,
        ValidationRequest.validated_risk_tier_id.isnot(None)
    ).subquery()

    current_tier = aliased(TaxonomyValue)
    validated_tier = aliased(TaxonomyValue)

    mismatch_query = db.query(
        Model,
        latest_approved_subq.c.request_id,
        latest_approved_subq.c.validated_risk_tier_id,
        latest_approved_subq.c.completion_date,
        current_tier,
        validated_tier,
    ).join(
        latest_approved_subq,
        latest_approved_subq.c.model_id == Model.model_id
    ).outerjoin(
        current_tier,
        current_tier.value_id == Model.risk_tier_id
    ).outerjoin(
        validated_tier,
        validated_tier.value_id == latest_approved_subq.c.validated_risk_tier_id
    ).filter(
        latest_approved_subq.c.rn == 1,
        Model.risk_tier_id.isnot(None),
        Model.risk_tier_id != latest_approved_subq.c.validated_risk_tier_id
    )
    if active_status:
        mismatch_query = mismatch_query.filter(
            Model.status_id == active_status.value_id
        )

    mismatch_items = []
    for model, request_id, validated_tier_id, completion_date, current_tier_value, validated_tier_value in mismatch_query.all():
        current_sort = current_tier_value.sort_order if current_tier_value else 99
        validated_sort = validated_tier_value.sort_order if validated_tier_value else 99

        if current_sort < validated_sort:
            direction = "INCREASED"  # Lower sort_order = higher risk
            requires_reval = True
        elif current_sort > validated_sort:
            direction = "DECREASED"
            requires_reval = False  # May not need revalidation for lower risk
        else:
            direction = "CHANGED"
            requires_reval = True

        mismatch_items.append(RiskMismatchItem(
            model_id=model.model_id,
            model_name=model.model_name,
            current_risk_tier_id=model.risk_tier_id,
            current_risk_tier_code=current_tier_value.code if current_tier_value else None,
            current_risk_tier_label=current_tier_value.label if current_tier_value else None,
            validated_risk_tier_id=validated_tier_id,
            validated_risk_tier_code=validated_tier_value.code if validated_tier_value else None,
            validated_risk_tier_label=validated_tier_value.label if validated_tier_value else None,
            last_validation_request_id=request_id,
            last_validation_date=completion_date.date() if completion_date else None,
            tier_change_direction=direction,
            requires_revalidation=requires_reval
        ))

    return RiskMismatchReportResponse(
        total_models_checked=total_checked,
        models_with_mismatch=len(mismatch_items),
        items=mismatch_items,
        generated_at=utc_now()
    )


# ===== EFFECTIVE CHALLENGE PDF EXPORT =====


@router.get("/requests/{request_id}/effective-challenge-report")
def export_effective_challenge_report(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate PDF documenting effective challenge process (send-backs and responses).

    This report captures the history of approver send-backs and validator responses,
    demonstrating the "effective challenge" process for audit and compliance purposes.
    """
    from fpdf import FPDF, XPos, YPos
    import io
    from fastapi.responses import StreamingResponse

    # Fetch validation request with relationships
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.models),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.outcome),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.approver),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.assigned_approver),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.manually_added_by)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Fetch status history ordered by date
    status_history = db.query(ValidationStatusHistory).options(
        joinedload(ValidationStatusHistory.old_status),
        joinedload(ValidationStatusHistory.new_status),
        joinedload(ValidationStatusHistory.changed_by)
    ).filter(
        ValidationStatusHistory.request_id == request_id
    ).order_by(ValidationStatusHistory.changed_at.asc()).all()

    # Find all REVISION entries (send-backs) and responses
    revision_entries = [h for h in status_history if h.new_status and h.new_status.code == "REVISION"]
    resubmit_entries = [h for h in status_history if h.old_status and h.old_status.code == "REVISION"]

    # Build rounds of challenge
    challenge_rounds = []
    for i, revision in enumerate(revision_entries):
        round_data = {
            "round_number": i + 1,
            "sent_back_at": revision.changed_at,
            "sent_back_by": revision.changed_by.full_name if revision.changed_by else "Unknown",
            "send_back_reason": revision.change_reason or "No reason provided",
            "snapshot": None,
            "response": None,
            "response_at": None,
            "responded_by": None
        }

        # Parse snapshot from additional_context
        if revision.additional_context:
            try:
                snapshot = json.loads(revision.additional_context)
                round_data["snapshot"] = snapshot
                round_data["approver_role"] = snapshot.get("sent_back_by_role", "Unknown")
            except json.JSONDecodeError:
                pass

        # Find corresponding resubmission (next REVISION -> PENDING_APPROVAL transition)
        for resubmit in resubmit_entries:
            if resubmit.changed_at > revision.changed_at:
                round_data["response"] = resubmit.change_reason or "Revisions completed"
                round_data["response_at"] = resubmit.changed_at
                round_data["responded_by"] = resubmit.changed_by.full_name if resubmit.changed_by else "Unknown"
                break

        challenge_rounds.append(round_data)

    # Generate PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 10, 'Effective Challenge Report', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(5)

    # Subtitle with request info
    pdf.set_font('Helvetica', 'I', 11)
    model_names = ", ".join([m.model_name for m in validation_request.models[:3]])
    if len(validation_request.models) > 3:
        model_names += f" (+{len(validation_request.models) - 3} more)"
    pdf.cell(0, 6, f'Validation Request #{request_id}: {model_names}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f'Generated: {utc_now().strftime("%Y-%m-%d %H:%M UTC")}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(10)

    # Summary section
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 8, 'Summary', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 10)
    pdf.ln(2)

    # Summary table
    pdf.set_fill_color(240, 240, 240)
    summary_items = [
        ("Validation Type", validation_request.validation_type.label if validation_request.validation_type else "N/A"),
        ("Current Status", validation_request.current_status.label if validation_request.current_status else "N/A"),
        ("Total Challenge Rounds", str(len(challenge_rounds))),
        ("Final Outcome", validation_request.outcome.overall_rating.label
         if validation_request.outcome and validation_request.outcome.overall_rating
         else "Pending")
    ]

    for label, value in summary_items:
        pdf.cell(60, 7, label + ":", border=1, fill=True)
        pdf.cell(0, 7, value, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(10)

    # Challenge rounds section
    if challenge_rounds:
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 8, 'Challenge Rounds', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)

        for round_data in challenge_rounds:
            # Round header
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_fill_color(66, 133, 244)  # Blue
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, f'Round {round_data["round_number"]}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)

            # Send-back details
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(255, 235, 205)  # Light orange
            pdf.cell(0, 7, 'SEND-BACK', new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)

            pdf.set_font('Helvetica', '', 10)
            pdf.cell(35, 6, 'Date:')
            pdf.cell(0, 6, round_data["sent_back_at"].strftime("%Y-%m-%d %H:%M UTC") if round_data["sent_back_at"] else "N/A", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.cell(35, 6, 'Approver:')
            pdf.cell(0, 6, f'{round_data["sent_back_by"]} ({round_data.get("approver_role", "Unknown")})', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.cell(35, 6, 'Feedback:')
            # Multi-line for long feedback
            pdf.multi_cell(0, 6, round_data["send_back_reason"])
            pdf.ln(3)

            # Response details (if any)
            if round_data["response"]:
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_fill_color(209, 250, 229)  # Light green
                pdf.cell(0, 7, 'RESPONSE', new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)

                pdf.set_font('Helvetica', '', 10)
                pdf.cell(35, 6, 'Date:')
                pdf.cell(0, 6, round_data["response_at"].strftime("%Y-%m-%d %H:%M UTC") if round_data["response_at"] else "N/A", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                pdf.cell(35, 6, 'Responder:')
                pdf.cell(0, 6, round_data["responded_by"] or "N/A", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                pdf.cell(35, 6, 'Response:')
                pdf.multi_cell(0, 6, round_data["response"])
            else:
                pdf.set_font('Helvetica', 'I', 10)
                pdf.set_text_color(128, 128, 128)
                pdf.cell(0, 6, 'Awaiting response...', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(0, 0, 0)

            pdf.ln(8)
    else:
        pdf.set_font('Helvetica', 'I', 11)
        pdf.cell(0, 10, 'No challenge rounds recorded for this validation request.', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Approval status section
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 8, 'Current Approval Status', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    approvals = [a for a in validation_request.approvals if a.voided_by_id is None]
    if approvals:
        # Table header
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(50, 7, 'Approver Role', border=1, fill=True)
        pdf.cell(30, 7, 'Type', border=1, fill=True)
        pdf.cell(30, 7, 'Status', border=1, fill=True)
        pdf.cell(0, 7, 'Comments', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)

        pdf.set_font('Helvetica', '', 9)
        for approval in approvals:
            pdf.cell(50, 7, approval.approver_role or "N/A", border=1)
            pdf.cell(30, 7, approval.approval_type or "N/A", border=1)
            pdf.cell(30, 7, approval.approval_status or "N/A", border=1)
            comments = (approval.comments or "")[:50]
            if len(approval.comments or "") > 50:
                comments += "..."
            pdf.cell(0, 7, comments, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(0, 7, 'No approvals configured.', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Footer
    pdf.ln(15)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 5, 'This report was auto-generated for compliance and audit purposes.', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.cell(0, 5, f'Request ID: {request_id} | User: {current_user.email}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # Output PDF
    pdf_bytes = bytes(pdf.output())

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="effective_challenge_VR{request_id}.pdf"'
        }
    )

"""Model Recommendations API endpoints.

Implements full lifecycle management of recommendations identified during validation,
including action plan tasks, rebuttals, evidence upload, and multi-stakeholder approvals.
"""
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_, exists

from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.core.rls import can_see_all_data, can_see_recommendation
from app.models import (
    User, Model, TaxonomyValue, Taxonomy, AuditLog, Region, ModelRegion,
    Recommendation, ActionPlanTask, RecommendationRebuttal,
    ClosureEvidence, RecommendationStatusHistory, RecommendationApproval,
    RecommendationPriorityConfig, ModelLimitation, ModelDelegate
)
from app.models.recommendation import RecommendationPriorityRegionalOverride, RecommendationTimeframeConfig
from app.schemas.recommendation import (
    RecommendationCreate, RecommendationUpdate, RecommendationResponse, RecommendationListResponse,
    ActionPlanTaskCreate, ActionPlanTaskUpdate, ActionPlanTaskResponse,
    ActionPlanSubmission, ActionPlanRevisionRequest,
    RebuttalCreate, RebuttalReviewRequest, RebuttalResponse, RebuttalReviewResponse, RebuttalSubmissionResponse,
    ClosureEvidenceCreate, ClosureEvidenceResponse,
    StatusHistoryResponse, ApprovalResponse, ApprovalRequest, ApprovalRejectRequest,
    PriorityConfigCreate, PriorityConfigUpdate, PriorityConfigResponse,
    RegionalOverrideCreate, RegionalOverrideUpdate, RegionalOverrideResponse,
    ClosureReviewRequest, DeclineAcknowledgementRequest,
    # Timeframe Config
    TimeframeConfigUpdate, TimeframeConfigResponse,
    TimeframeCalculationRequest, TimeframeCalculationResponse,
    # Dashboard & Reports
    MyTasksResponse, MyTaskItem, OpenRecommendationsSummary, StatusSummary, PrioritySummary,
    OverdueRecommendationsReport, OverdueRecommendation, ModelSummary
)
from app.schemas.taxonomy import TaxonomyValueResponse
from app.schemas.limitation import LimitationListResponse


# ==================== DATA CLASSES ====================

@dataclass
class TargetDateValidationResult:
    """Result of target date validation."""
    is_valid: bool
    is_enforced: bool
    max_target_date: Optional[date]
    reason_required: bool
    message: str


router = APIRouter(prefix="/recommendations")


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


def check_developer_or_admin(user: User, recommendation: Recommendation):
    """Check if user is the assigned developer or Admin."""
    if user.role != "Admin" and user.user_id != recommendation.assigned_to_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned developer or Admins can perform this action"
        )


def get_status_by_code(db: Session, code: str) -> TaxonomyValue:
    """Get recommendation status taxonomy value by code."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Recommendation Status").first()
    if not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recommendation Status taxonomy not found"
        )
    value = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.code == code
    ).first()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status code {code} not found"
        )
    return value


def get_task_status_by_code(db: Session, code: str) -> TaxonomyValue:
    """Get task status taxonomy value by code."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Action Plan Task Status").first()
    if not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Action Plan Task Status taxonomy not found"
        )
    value = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.code == code
    ).first()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task status code {code} not found"
        )
    return value


def generate_recommendation_code(db: Session) -> str:
    """Generate unique recommendation code like REC-2025-00001."""
    year = date.today().year
    # Get max sequence for this year
    prefix = f"REC-{year}-"
    max_rec = db.query(Recommendation).filter(
        Recommendation.recommendation_code.like(f"{prefix}%")
    ).order_by(desc(Recommendation.recommendation_code)).first()

    if max_rec:
        seq_part = max_rec.recommendation_code.split("-")[-1]
        try:
            next_seq = int(seq_part) + 1
        except ValueError:
            next_seq = 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:05d}"


def create_status_history(
    db: Session,
    recommendation: Recommendation,
    new_status: TaxonomyValue,
    user: User,
    reason: Optional[str] = None,
    additional_context: Optional[str] = None
):
    """Create a status history record."""
    old_status_id = recommendation.current_status_id
    history = RecommendationStatusHistory(
        recommendation_id=recommendation.recommendation_id,
        old_status_id=old_status_id,
        new_status_id=new_status.value_id,
        changed_by_id=user.user_id,
        change_reason=reason,
        additional_context=additional_context
    )
    db.add(history)
    recommendation.current_status_id = new_status.value_id


def create_audit_log(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    user: User,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None
):
    """Create an audit log entry."""
    # Combine old and new values into a single changes dict
    changes = {}
    if old_values:
        changes["old"] = old_values
    if new_values:
        changes["new"] = new_values

    audit = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user.user_id,
        changes=changes if changes else None
    )
    db.add(audit)


def is_terminal_status(code: str) -> bool:
    """Check if status is terminal (DROPPED or CLOSED)."""
    return code in ("REC_DROPPED", "REC_CLOSED")


def check_not_terminal(recommendation: Recommendation, db: Session):
    """Raise error if recommendation is in terminal state."""
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    if current_status and is_terminal_status(current_status.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot perform action on recommendation in terminal state: {current_status.label}"
        )


def get_max_days_for_recommendation(
    db: Session,
    priority_id: int,
    risk_tier_id: int,
    usage_frequency_id: int
) -> Optional[int]:
    """Look up the maximum days allowed for a priority/risk/frequency combination.

    Args:
        db: Database session
        priority_id: FK to Recommendation Priority taxonomy value
        risk_tier_id: FK to Model Risk Tier taxonomy value
        usage_frequency_id: FK to Model Usage Frequency taxonomy value

    Returns:
        max_days if a configuration exists for this combination, None otherwise
    """
    config = db.query(RecommendationTimeframeConfig).filter(
        RecommendationTimeframeConfig.priority_id == priority_id,
        RecommendationTimeframeConfig.risk_tier_id == risk_tier_id,
        RecommendationTimeframeConfig.usage_frequency_id == usage_frequency_id
    ).first()
    return config.max_days if config else None


def calculate_max_target_date(
    db: Session,
    priority_id: int,
    risk_tier_id: int,
    usage_frequency_id: int,
    creation_date: date
) -> Optional[date]:
    """Calculate the maximum allowed target date for a recommendation.

    Args:
        db: Database session
        priority_id: FK to Recommendation Priority taxonomy value
        risk_tier_id: FK to Model Risk Tier taxonomy value
        usage_frequency_id: FK to Model Usage Frequency taxonomy value
        creation_date: The date the recommendation was created

    Returns:
        The maximum allowed target date (creation_date + max_days),
        or None if no configuration exists for the combination.
        A max_days of 0 means immediate resolution (same day as creation).
    """
    max_days = get_max_days_for_recommendation(
        db, priority_id, risk_tier_id, usage_frequency_id
    )

    if max_days is None:
        return None

    return creation_date + timedelta(days=max_days)


def is_timeframe_enforced(db: Session, recommendation: Recommendation) -> bool:
    """Check if timeframe enforcement applies for this recommendation.

    Returns True if target dates must be within max allowed timeframe,
    False if timeframes are advisory only.

    Resolution logic with regional overrides:
    1. Get base config for the priority
    2. Get the model's deployed regions
    3. If model has regions, check for regional overrides
    4. Apply "most restrictive wins" logic:
       - If ANY override says True, return True (enforce)
       - If ALL overrides say False (explicit), return False (advisory)
       - NULL overrides are ignored (inherit from base)
       - If no overrides apply, use base config
    5. If no config exists, default to True (fail-safe: enforce by default)
    """
    # Get base config
    config = db.query(RecommendationPriorityConfig).filter(
        RecommendationPriorityConfig.priority_id == recommendation.priority_id
    ).first()

    # Default to True if no config exists (fail-safe: enforce by default)
    base_enforced = config.enforce_timeframes if config else True

    # Get model's deployed region IDs
    model_region_ids = db.query(ModelRegion.region_id).filter(
        ModelRegion.model_id == recommendation.model_id
    ).all()
    region_ids = [r[0] for r in model_region_ids]

    # If no regions, use base config only
    if not region_ids:
        return base_enforced

    # Get regional overrides for this priority + model's regions
    overrides = db.query(RecommendationPriorityRegionalOverride).filter(
        RecommendationPriorityRegionalOverride.priority_id == recommendation.priority_id,
        RecommendationPriorityRegionalOverride.region_id.in_(region_ids)
    ).all()

    # If no overrides, use base config
    if not overrides:
        return base_enforced

    # Apply "most restrictive wins" logic
    # First check if ANY override explicitly enforces timeframes
    for override in overrides:
        if override.enforce_timeframes is True:
            return True

    # Check if ALL overrides explicitly say no enforcement
    # (NULL values inherit from base, so don't count them)
    explicit_false_count = sum(1 for o in overrides if o.enforce_timeframes is False)
    if explicit_false_count == len(overrides):
        # All overrides explicitly say no enforcement
        return False

    # Some overrides are NULL (inherit) and none explicitly require enforcement
    # Fall back to base config
    return base_enforced


def _check_timeframe_enforced_for_model(
    db: Session,
    priority_id: int,
    model_id: int
) -> bool:
    """Check if timeframe enforcement applies for a given priority and model.

    This is a helper version of is_timeframe_enforced that doesn't require
    a Recommendation object. Used during validation before creating a recommendation.

    Returns True if target dates must be within max allowed timeframe,
    False if timeframes are advisory only.
    """
    # Get base config
    config = db.query(RecommendationPriorityConfig).filter(
        RecommendationPriorityConfig.priority_id == priority_id
    ).first()

    # Default to True if no config exists (fail-safe: enforce by default)
    base_enforced = config.enforce_timeframes if config else True

    # Get model's deployed region IDs
    model_region_ids = db.query(ModelRegion.region_id).filter(
        ModelRegion.model_id == model_id
    ).all()
    region_ids = [r[0] for r in model_region_ids]

    # If no regions, use base config only
    if not region_ids:
        return base_enforced

    # Get regional overrides for this priority + model's regions
    overrides = db.query(RecommendationPriorityRegionalOverride).filter(
        RecommendationPriorityRegionalOverride.priority_id == priority_id,
        RecommendationPriorityRegionalOverride.region_id.in_(region_ids)
    ).all()

    # If no overrides, use base config
    if not overrides:
        return base_enforced

    # Apply "most restrictive wins" logic
    for override in overrides:
        if override.enforce_timeframes is True:
            return True

    explicit_false_count = sum(1 for o in overrides if o.enforce_timeframes is False)
    if explicit_false_count == len(overrides):
        return False

    return base_enforced


def validate_target_date(
    db: Session,
    priority_id: int,
    model_id: int,
    proposed_target_date: date,
    creation_date: date
) -> TargetDateValidationResult:
    """Validate a proposed target date against timeframe configurations.

    Args:
        db: Database session
        priority_id: FK to Recommendation Priority taxonomy value
        model_id: FK to Model
        proposed_target_date: The target date being validated
        creation_date: The recommendation creation date

    Returns:
        TargetDateValidationResult with validation status, enforcement info,
        max date, reason requirement, and message.
    """
    # Check if target date is before creation date
    if proposed_target_date < creation_date:
        return TargetDateValidationResult(
            is_valid=False,
            is_enforced=True,  # This is always enforced
            max_target_date=None,
            reason_required=False,
            message="Target date cannot be before the creation date"
        )

    # Get model to retrieve risk_tier_id and usage_frequency_id
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return TargetDateValidationResult(
            is_valid=False,
            is_enforced=True,
            max_target_date=None,
            reason_required=False,
            message="Model not found"
        )

    # Get model's risk tier and usage frequency
    risk_tier_id = model.risk_tier_id
    usage_frequency_id = model.usage_frequency_id

    # Handle case where model doesn't have required fields
    if not risk_tier_id or not usage_frequency_id:
        return TargetDateValidationResult(
            is_valid=True,
            is_enforced=False,
            max_target_date=None,
            reason_required=False,
            message="Model does not have risk tier or usage frequency configured. No timeframe validation applied."
        )

    # Calculate max target date
    max_target = calculate_max_target_date(
        db, priority_id, risk_tier_id, usage_frequency_id, creation_date
    )

    # If no config exists, return valid with warning
    if max_target is None:
        return TargetDateValidationResult(
            is_valid=True,
            is_enforced=False,
            max_target_date=None,
            reason_required=False,
            message="No timeframe configuration exists for this priority/risk/frequency combination"
        )

    # Check if enforcement applies
    is_enforced = _check_timeframe_enforced_for_model(db, priority_id, model_id)

    # Calculate days from creation to max and to proposed
    # Check if proposed date exceeds max
    exceeds_max = proposed_target_date > max_target

    if is_enforced:
        # Strict enforcement mode
        if exceeds_max:
            return TargetDateValidationResult(
                is_valid=False,
                is_enforced=True,
                max_target_date=max_target,
                reason_required=False,
                message=f"Target date exceeds maximum allowed date of {max_target}. "
                        f"When timeframes are enforced, target date must be on or before the maximum."
            )
        else:
            # Within limits
            return TargetDateValidationResult(
                is_valid=True,
                is_enforced=True,
                max_target_date=max_target,
                reason_required=False,
                message="Target date is within the enforced maximum timeframe"
            )
    else:
        # Advisory mode (not enforced)
        if exceeds_max:
            return TargetDateValidationResult(
                is_valid=True,  # Valid because not enforced
                is_enforced=False,
                max_target_date=max_target,
                reason_required=True,  # But reason is required
                message=f"Target date exceeds the recommended maximum of {max_target}. "
                        f"Timeframe is advisory only. Explanation required for extended timeline."
            )
        else:
            # Within limits
            return TargetDateValidationResult(
                is_valid=True,
                is_enforced=False,
                max_target_date=max_target,
                reason_required=False,
                message="Target date is within the recommended timeframe"
            )


def check_requires_action_plan(db: Session, recommendation: Recommendation) -> bool:
    """Check if recommendation's priority requires an action plan.

    Returns True if action plan is required, False if it can be skipped.

    Resolution logic with regional overrides:
    1. Get base config for the priority
    2. Get the model's deployed regions
    3. If model has regions, check for regional overrides
    4. Apply "most restrictive wins" logic:
       - If ANY override says True, return True
       - If ALL overrides say False (explicit), return False
       - NULL overrides are ignored (inherit from base)
       - If no overrides apply, use base config
    """
    # Get base config
    config = db.query(RecommendationPriorityConfig).filter(
        RecommendationPriorityConfig.priority_id == recommendation.priority_id
    ).first()

    base_requires = config.requires_action_plan if config else True

    # Get model's deployed region IDs
    model_region_ids = db.query(ModelRegion.region_id).filter(
        ModelRegion.model_id == recommendation.model_id
    ).all()
    region_ids = [r[0] for r in model_region_ids]

    # If no regions, use base config only
    if not region_ids:
        return base_requires

    # Get regional overrides for this priority + model's regions
    overrides = db.query(RecommendationPriorityRegionalOverride).filter(
        RecommendationPriorityRegionalOverride.priority_id == recommendation.priority_id,
        RecommendationPriorityRegionalOverride.region_id.in_(region_ids)
    ).all()

    # If no overrides, use base config
    if not overrides:
        return base_requires

    # Apply "most restrictive wins" logic
    # First check if ANY override explicitly requires action plan
    for override in overrides:
        if override.requires_action_plan is True:
            return True

    # Check if ALL overrides explicitly say no action plan required
    # (NULL values inherit from base, so don't count them)
    explicit_false_count = sum(1 for o in overrides if o.requires_action_plan is False)
    if explicit_false_count == len(overrides):
        # All overrides explicitly say no action plan required
        return False

    # Some overrides are NULL (inherit) and none explicitly require it
    # Fall back to base config
    return base_requires


def create_final_approvals(
    db: Session,
    recommendation: Recommendation
):
    """Create Global and Regional approval requirements based on model deployment."""
    # Always create Global approval
    global_approval = RecommendationApproval(
        recommendation_id=recommendation.recommendation_id,
        approval_type="GLOBAL",
        region_id=None,
        is_required=True,
        approval_status="PENDING"
    )
    db.add(global_approval)

    # Create Regional approvals based on model regions
    model_regions = db.query(ModelRegion).filter(
        ModelRegion.model_id == recommendation.model_id
    ).all()

    for mr in model_regions:
        region = db.query(Region).filter(Region.region_id == mr.region_id).first()
        if region and region.requires_regional_approval:
            regional_approval = RecommendationApproval(
                recommendation_id=recommendation.recommendation_id,
                approval_type="REGIONAL",
                region_id=region.region_id,
                is_required=True,
                approval_status="PENDING"
            )
            db.add(regional_approval)


def check_all_approvals_complete(recommendation: Recommendation) -> bool:
    """Check if all required approvals are APPROVED or VOIDED (not PENDING or REJECTED)."""
    for approval in recommendation.approvals:
        if approval.is_required and approval.approval_status in ("PENDING", "REJECTED"):
            return False
    return True


# ==================== TIMEFRAME CONFIG ENDPOINTS ====================

@router.get("/timeframe-config/", response_model=List[TimeframeConfigResponse])
def list_timeframe_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all timeframe configurations."""
    configs = db.query(RecommendationTimeframeConfig).options(
        joinedload(RecommendationTimeframeConfig.priority),
        joinedload(RecommendationTimeframeConfig.risk_tier),
        joinedload(RecommendationTimeframeConfig.usage_frequency)
    ).all()
    return configs


@router.get("/timeframe-config/{config_id}", response_model=TimeframeConfigResponse)
def get_timeframe_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single timeframe configuration."""
    config = db.query(RecommendationTimeframeConfig).options(
        joinedload(RecommendationTimeframeConfig.priority),
        joinedload(RecommendationTimeframeConfig.risk_tier),
        joinedload(RecommendationTimeframeConfig.usage_frequency)
    ).filter(RecommendationTimeframeConfig.config_id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeframe config not found"
        )
    return config


@router.patch("/timeframe-config/{config_id}", response_model=TimeframeConfigResponse)
def update_timeframe_config(
    config_id: int,
    update_data: TimeframeConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update timeframe configuration (Admin only)."""
    check_admin(current_user)

    config = db.query(RecommendationTimeframeConfig).filter(
        RecommendationTimeframeConfig.config_id == config_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeframe config not found"
        )

    if update_data.max_days is not None:
        config.max_days = update_data.max_days
    if update_data.description is not None:
        config.description = update_data.description

    db.commit()
    db.refresh(config)

    # Load relationships for response
    db.refresh(config, ["priority", "risk_tier", "usage_frequency"])
    return config


@router.post("/timeframe-config/calculate", response_model=TimeframeCalculationResponse)
def calculate_timeframe(
    request: TimeframeCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate maximum target date for a model/priority combination."""
    model = db.query(Model).filter(Model.model_id == request.model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if not model.risk_tier_id or not model.usage_frequency_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model must have risk tier and usage frequency set"
        )

    today = date.today()
    max_target = calculate_max_target_date(
        db,
        priority_id=request.priority_id,
        risk_tier_id=model.risk_tier_id,
        usage_frequency_id=model.usage_frequency_id,
        creation_date=today
    )

    # Get taxonomy value codes for response
    priority = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == request.priority_id
    ).first()
    risk_tier = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == model.risk_tier_id
    ).first()
    usage_freq = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == model.usage_frequency_id
    ).first()

    # Get max days from config
    max_days = get_max_days_for_recommendation(
        db, request.priority_id, model.risk_tier_id, model.usage_frequency_id
    )

    # Check enforcement
    enforce = _check_timeframe_enforced_for_model(db, request.priority_id, request.model_id)

    return TimeframeCalculationResponse(
        priority_code=priority.code if priority else "UNKNOWN",
        risk_tier_code=risk_tier.code if risk_tier else "UNKNOWN",
        usage_frequency_code=usage_freq.code if usage_freq else "UNKNOWN",
        max_days=max_days if max_days is not None else 365,
        calculated_max_date=max_target if max_target else today + timedelta(days=365),
        enforce_timeframes=enforce,
        enforced_by_region=None  # Could enhance to return region name
    )


# ==================== PRIORITY CONFIG ENDPOINTS ====================

@router.get("/priority-config/", response_model=List[PriorityConfigResponse])
def list_priority_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all priority configurations."""
    configs = db.query(RecommendationPriorityConfig).options(
        joinedload(RecommendationPriorityConfig.priority)
    ).all()
    return configs


# ==================== REGIONAL OVERRIDE ENDPOINTS ====================
# NOTE: These must be defined BEFORE /priority-config/{priority_id} routes
# to avoid FastAPI matching "regional-overrides" as a priority_id.

@router.get("/priority-config/regional-overrides/", response_model=List[RegionalOverrideResponse])
def list_regional_overrides(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all regional priority overrides."""
    overrides = db.query(RecommendationPriorityRegionalOverride).options(
        joinedload(RecommendationPriorityRegionalOverride.priority),
        joinedload(RecommendationPriorityRegionalOverride.region)
    ).all()
    return overrides


@router.post("/priority-config/regional-overrides/", response_model=RegionalOverrideResponse, status_code=status.HTTP_201_CREATED)
def create_regional_override(
    override_data: RegionalOverrideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a regional priority override. Admin only."""
    check_admin(current_user)

    # Validate priority exists
    priority = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == override_data.priority_id
    ).first()
    if not priority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Priority not found"
        )

    # Validate region exists
    region = db.query(Region).filter(
        Region.region_id == override_data.region_id
    ).first()
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Region not found"
        )

    # Check for existing override (unique constraint)
    existing = db.query(RecommendationPriorityRegionalOverride).filter(
        RecommendationPriorityRegionalOverride.priority_id == override_data.priority_id,
        RecommendationPriorityRegionalOverride.region_id == override_data.region_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Regional override already exists for this priority and region"
        )

    override = RecommendationPriorityRegionalOverride(
        priority_id=override_data.priority_id,
        region_id=override_data.region_id,
        requires_action_plan=override_data.requires_action_plan,
        requires_final_approval=override_data.requires_final_approval,
        enforce_timeframes=override_data.enforce_timeframes,
        description=override_data.description
    )
    db.add(override)
    db.commit()
    db.refresh(override)

    # Load relationships for response
    db.refresh(override, ["priority", "region"])
    return override


@router.patch("/priority-config/regional-overrides/{override_id}", response_model=RegionalOverrideResponse)
def update_regional_override(
    override_id: int,
    override_update: RegionalOverrideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a regional priority override. Admin only."""
    check_admin(current_user)

    override = db.query(RecommendationPriorityRegionalOverride).filter(
        RecommendationPriorityRegionalOverride.override_id == override_id
    ).first()

    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regional override not found"
        )

    # Allow setting to None explicitly (to inherit from base)
    if override_update.requires_action_plan is not None or 'requires_action_plan' in override_update.model_dump(exclude_unset=True):
        override.requires_action_plan = override_update.requires_action_plan
    if override_update.requires_final_approval is not None or 'requires_final_approval' in override_update.model_dump(exclude_unset=True):
        override.requires_final_approval = override_update.requires_final_approval
    if override_update.enforce_timeframes is not None or 'enforce_timeframes' in override_update.model_dump(exclude_unset=True):
        override.enforce_timeframes = override_update.enforce_timeframes
    if override_update.description is not None:
        override.description = override_update.description

    db.commit()
    db.refresh(override, ["priority", "region"])
    return override


@router.delete("/priority-config/regional-overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_regional_override(
    override_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a regional priority override. Admin only."""
    check_admin(current_user)

    override = db.query(RecommendationPriorityRegionalOverride).filter(
        RecommendationPriorityRegionalOverride.override_id == override_id
    ).first()

    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regional override not found"
        )

    db.delete(override)
    db.commit()
    return None


# ==================== PRIORITY CONFIG DYNAMIC ROUTES ====================
# NOTE: These must be defined AFTER the static /regional-overrides/ routes

@router.patch("/priority-config/{priority_id}", response_model=PriorityConfigResponse)
def update_priority_config(
    priority_id: int,
    config_update: PriorityConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update priority configuration. Admin only."""
    check_admin(current_user)

    config = db.query(RecommendationPriorityConfig).filter(
        RecommendationPriorityConfig.priority_id == priority_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Priority configuration not found"
        )

    if config_update.requires_final_approval is not None:
        config.requires_final_approval = config_update.requires_final_approval
    if config_update.requires_action_plan is not None:
        config.requires_action_plan = config_update.requires_action_plan
    if config_update.enforce_timeframes is not None:
        config.enforce_timeframes = config_update.enforce_timeframes
    if config_update.description is not None:
        config.description = config_update.description

    db.commit()
    db.refresh(config)
    return config


@router.get("/priority-config/{priority_id}/regional-overrides/", response_model=List[RegionalOverrideResponse])
def list_regional_overrides_for_priority(
    priority_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List regional overrides for a specific priority."""
    overrides = db.query(RecommendationPriorityRegionalOverride).filter(
        RecommendationPriorityRegionalOverride.priority_id == priority_id
    ).options(
        joinedload(RecommendationPriorityRegionalOverride.priority),
        joinedload(RecommendationPriorityRegionalOverride.region)
    ).all()
    return overrides


# ==================== RECOMMENDATION CRUD ENDPOINTS ====================

@router.post("/", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
def create_recommendation(
    rec_data: RecommendationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new recommendation. Validator or Admin only."""
    check_validator_or_admin(current_user)

    # Validate model exists
    model = db.query(Model).filter(Model.model_id == rec_data.model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Validate priority
    priority = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == rec_data.priority_id
    ).first()
    if not priority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Priority not found"
        )

    # Validate category if provided
    if rec_data.category_id:
        category = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == rec_data.category_id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

    # Validate assigned user
    assigned_to = db.query(User).filter(User.user_id == rec_data.assigned_to_id).first()
    if not assigned_to:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user not found"
        )

    # Validate monitoring cycle if provided
    if rec_data.monitoring_cycle_id:
        from app.models.monitoring import MonitoringCycle
        cycle = db.query(MonitoringCycle).filter(
            MonitoringCycle.cycle_id == rec_data.monitoring_cycle_id
        ).first()
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitoring cycle not found"
            )

    # Validate target date against timeframe configuration
    creation_date = date.today()
    validation_result = validate_target_date(
        db,
        priority_id=rec_data.priority_id,
        model_id=rec_data.model_id,
        proposed_target_date=rec_data.original_target_date,
        creation_date=creation_date
    )

    if not validation_result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_result.message
        )

    # Get draft status
    draft_status = get_status_by_code(db, "REC_DRAFT")

    # Generate code
    rec_code = generate_recommendation_code(db)

    # Create recommendation
    recommendation = Recommendation(
        recommendation_code=rec_code,
        model_id=rec_data.model_id,
        validation_request_id=rec_data.validation_request_id,
        monitoring_cycle_id=rec_data.monitoring_cycle_id,
        title=rec_data.title,
        description=rec_data.description,
        root_cause_analysis=rec_data.root_cause_analysis,
        priority_id=rec_data.priority_id,
        category_id=rec_data.category_id,
        current_status_id=draft_status.value_id,
        created_by_id=current_user.user_id,
        assigned_to_id=rec_data.assigned_to_id,
        original_target_date=rec_data.original_target_date,
        current_target_date=rec_data.original_target_date,
        target_date_change_reason=rec_data.target_date_change_reason
    )
    db.add(recommendation)
    db.flush()

    # Create initial status history
    history = RecommendationStatusHistory(
        recommendation_id=recommendation.recommendation_id,
        old_status_id=None,
        new_status_id=draft_status.value_id,
        changed_by_id=current_user.user_id,
        change_reason="Recommendation created"
    )
    db.add(history)

    # Audit log
    create_audit_log(
        db, "Recommendation", recommendation.recommendation_id, "CREATE",
        current_user, None, {"title": rec_data.title, "code": rec_code}
    )

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.get("/", response_model=List[RecommendationListResponse])
def list_recommendations(
    model_id: Optional[int] = None,
    status_id: Optional[int] = None,
    priority_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List recommendations with optional filters.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: See all recommendations
    - User: Only see recommendations for models where they are owner, developer,
      shared owner, shared developer, or an active delegate
    """
    query = db.query(Recommendation).options(
        joinedload(Recommendation.model),
        joinedload(Recommendation.priority),
        joinedload(Recommendation.category),
        joinedload(Recommendation.current_status),
        joinedload(Recommendation.assigned_to)
    )

    # Apply Row-Level Security for basic users
    if not can_see_all_data(current_user):
        # Get DRAFT status to filter it out
        draft_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Recommendation Status",
            TaxonomyValue.code == "REC_DRAFT"
        ).first()

        # Subquery to check if user is an active delegate for the model
        is_active_delegate = exists().where(
            ModelDelegate.model_id == Model.model_id,
            ModelDelegate.user_id == current_user.user_id,
            ModelDelegate.revoked_at.is_(None)  # NULL means active
        )

        # Build the visibility filter:
        # 1. assigned_to user can see their non-DRAFT recommendations
        # 2. model owners/developers/delegates can see non-DRAFT recommendations
        query = query.outerjoin(Model, Recommendation.model_id == Model.model_id).filter(
            or_(
                # assigned_to user can see non-DRAFT recommendations
                Recommendation.assigned_to_id == current_user.user_id,
                # model access via ownership/developer/delegate
                Model.owner_id == current_user.user_id,
                Model.developer_id == current_user.user_id,
                Model.shared_owner_id == current_user.user_id,
                Model.shared_developer_id == current_user.user_id,
                is_active_delegate
            )
        )

        # DRAFT recommendations are hidden from non-validation team users
        # (validation team is still deciding if the recommendation is worthy)
        if draft_status:
            query = query.filter(Recommendation.current_status_id != draft_status.value_id)

    if model_id:
        query = query.filter(Recommendation.model_id == model_id)
    if status_id:
        query = query.filter(Recommendation.current_status_id == status_id)
    if priority_id:
        query = query.filter(Recommendation.priority_id == priority_id)
    if assigned_to_id:
        query = query.filter(Recommendation.assigned_to_id == assigned_to_id)

    recommendations = query.order_by(desc(Recommendation.created_at)).offset(offset).limit(limit).all()
    return recommendations


# ==================== DASHBOARD & REPORTS ENDPOINTS ====================
# NOTE: These must be defined BEFORE /{recommendation_id} to avoid route conflicts

# Terminal status codes
TERMINAL_STATUS_CODES = ("REC_DROPPED", "REC_CLOSED")


@router.get("/my-tasks", response_model=MyTasksResponse)
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's action items.

    Returns tasks where the user needs to take action:
    - Developer: recommendations assigned to them requiring response, acknowledgement, or rework
    - Validator: recommendations they created awaiting their review
    - Approver: recommendations awaiting their approval
    """
    today = date.today()
    tasks = []

    # Get all non-terminal status codes
    status_taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Recommendation Status").first()
    if not status_taxonomy:
        return MyTasksResponse(total_tasks=0, overdue_count=0, tasks=[])

    # 1. Developer tasks: recommendations assigned to current user needing action
    developer_action_statuses = ["REC_PENDING_RESPONSE", "REC_PENDING_ACKNOWLEDGEMENT",
                                  "REC_OPEN", "REC_REWORK_REQUIRED", "REC_PENDING_ACTION_PLAN"]

    developer_recs = db.query(Recommendation).options(
        joinedload(Recommendation.model),
        joinedload(Recommendation.priority),
        joinedload(Recommendation.current_status)
    ).join(
        TaxonomyValue, Recommendation.current_status_id == TaxonomyValue.value_id
    ).filter(
        Recommendation.assigned_to_id == current_user.user_id,
        TaxonomyValue.code.in_(developer_action_statuses)
    ).all()

    for rec in developer_recs:
        status_code = rec.current_status.code
        if status_code == "REC_PENDING_RESPONSE":
            action = "Submit rebuttal or action plan"
        elif status_code == "REC_PENDING_ACKNOWLEDGEMENT":
            action = "Acknowledge recommendation"
        elif status_code == "REC_OPEN":
            action = "Complete remediation and submit for closure"
        elif status_code == "REC_REWORK_REQUIRED":
            action = "Address feedback and resubmit for closure"
        elif status_code == "REC_PENDING_ACTION_PLAN":
            action = "Submit action plan"
        else:
            action = "Review and take action"

        days_until = (rec.current_target_date - today).days
        tasks.append(MyTaskItem(
            task_type="ACTION_REQUIRED",
            recommendation_id=rec.recommendation_id,
            recommendation_code=rec.recommendation_code,
            title=rec.title,
            model=ModelSummary.model_validate(rec.model, from_attributes=True),
            priority=TaxonomyValueResponse.model_validate(rec.priority, from_attributes=True),
            current_status=TaxonomyValueResponse.model_validate(rec.current_status, from_attributes=True),
            current_target_date=rec.current_target_date,
            action_description=action,
            days_until_due=days_until,
            is_overdue=days_until < 0
        ))

    # 2. Validator tasks: recommendations created by current user awaiting review
    validator_review_statuses = ["REC_IN_REBUTTAL", "REC_PENDING_VALIDATOR_REVIEW",
                                  "REC_PENDING_CLOSURE_REVIEW"]

    validator_recs = db.query(Recommendation).options(
        joinedload(Recommendation.model),
        joinedload(Recommendation.priority),
        joinedload(Recommendation.current_status)
    ).join(
        TaxonomyValue, Recommendation.current_status_id == TaxonomyValue.value_id
    ).filter(
        Recommendation.created_by_id == current_user.user_id,
        TaxonomyValue.code.in_(validator_review_statuses)
    ).all()

    for rec in validator_recs:
        status_code = rec.current_status.code
        if status_code == "REC_IN_REBUTTAL":
            action = "Review developer's rebuttal"
        elif status_code == "REC_PENDING_VALIDATOR_REVIEW":
            action = "Review submitted action plan"
        elif status_code == "REC_PENDING_CLOSURE_REVIEW":
            action = "Review closure submission"
        else:
            action = "Review pending"

        days_until = (rec.current_target_date - today).days
        tasks.append(MyTaskItem(
            task_type="REVIEW_PENDING",
            recommendation_id=rec.recommendation_id,
            recommendation_code=rec.recommendation_code,
            title=rec.title,
            model=ModelSummary.model_validate(rec.model, from_attributes=True),
            priority=TaxonomyValueResponse.model_validate(rec.priority, from_attributes=True),
            current_status=TaxonomyValueResponse.model_validate(rec.current_status, from_attributes=True),
            current_target_date=rec.current_target_date,
            action_description=action,
            days_until_due=days_until,
            is_overdue=days_until < 0
        ))

    # 3. Approver tasks: pending approvals for current user
    # Get user's regions for regional approvals
    user_region_ids = [r.region_id for r in current_user.regions]

    # Build approval query
    approval_query = db.query(RecommendationApproval).options(
        joinedload(RecommendationApproval.recommendation).joinedload(Recommendation.model),
        joinedload(RecommendationApproval.recommendation).joinedload(Recommendation.priority),
        joinedload(RecommendationApproval.recommendation).joinedload(Recommendation.current_status)
    ).filter(
        RecommendationApproval.approval_status == "PENDING",
        RecommendationApproval.is_required == True
    )

    # Filter based on user's role
    if current_user.role == "Admin":
        # Admin can see all pending approvals
        pending_approvals = approval_query.all()
    elif current_user.role == "Global Approver":
        # Global approvers see GLOBAL type approvals
        pending_approvals = approval_query.filter(
            RecommendationApproval.approval_type == "GLOBAL"
        ).all()
    elif current_user.role == "Regional Approver" and user_region_ids:
        # Regional approvers see REGIONAL approvals for their regions
        pending_approvals = approval_query.filter(
            RecommendationApproval.approval_type == "REGIONAL",
            RecommendationApproval.region_id.in_(user_region_ids)
        ).all()
    else:
        pending_approvals = []

    for approval in pending_approvals:
        rec = approval.recommendation
        if approval.approval_type == "GLOBAL":
            action = "Submit global approval"
        else:
            action = f"Submit regional approval"

        days_until = (rec.current_target_date - today).days
        tasks.append(MyTaskItem(
            task_type="APPROVAL_PENDING",
            recommendation_id=rec.recommendation_id,
            recommendation_code=rec.recommendation_code,
            title=rec.title,
            model=ModelSummary.model_validate(rec.model, from_attributes=True),
            priority=TaxonomyValueResponse.model_validate(rec.priority, from_attributes=True),
            current_status=TaxonomyValueResponse.model_validate(rec.current_status, from_attributes=True),
            current_target_date=rec.current_target_date,
            action_description=action,
            days_until_due=days_until,
            is_overdue=days_until < 0
        ))

    # Sort by overdue first, then by days_until_due
    tasks.sort(key=lambda t: (not t.is_overdue, t.days_until_due or 0))

    overdue_count = sum(1 for t in tasks if t.is_overdue)

    return MyTasksResponse(
        total_tasks=len(tasks),
        overdue_count=overdue_count,
        tasks=tasks
    )


@router.get("/dashboard/open", response_model=OpenRecommendationsSummary)
def get_open_recommendations_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary of all open (non-terminal) recommendations.

    Returns counts by status and priority.
    """
    # Get status taxonomy
    status_taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Recommendation Status").first()
    if not status_taxonomy:
        return OpenRecommendationsSummary(total_open=0, by_status=[], by_priority=[])

    # Get all non-terminal statuses
    non_terminal_statuses = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == status_taxonomy.taxonomy_id,
        ~TaxonomyValue.code.in_(TERMINAL_STATUS_CODES)
    ).all()
    non_terminal_status_ids = [s.value_id for s in non_terminal_statuses]

    # Count by status
    status_counts = db.query(
        TaxonomyValue.code,
        TaxonomyValue.label,
        func.count(Recommendation.recommendation_id).label("count")
    ).join(
        Recommendation, Recommendation.current_status_id == TaxonomyValue.value_id
    ).filter(
        TaxonomyValue.value_id.in_(non_terminal_status_ids)
    ).group_by(
        TaxonomyValue.code, TaxonomyValue.label
    ).all()

    by_status = [
        StatusSummary(status_code=s.code, status_label=s.label, count=s.count)
        for s in status_counts
    ]

    # Count by priority (only for non-terminal recommendations)
    priority_counts = db.query(
        TaxonomyValue.code,
        TaxonomyValue.label,
        func.count(Recommendation.recommendation_id).label("count")
    ).join(
        Recommendation, Recommendation.priority_id == TaxonomyValue.value_id
    ).filter(
        Recommendation.current_status_id.in_(non_terminal_status_ids)
    ).group_by(
        TaxonomyValue.code, TaxonomyValue.label
    ).all()

    by_priority = [
        PrioritySummary(priority_code=p.code, priority_label=p.label, count=p.count)
        for p in priority_counts
    ]

    total_open = sum(s.count for s in by_status)

    return OpenRecommendationsSummary(
        total_open=total_open,
        by_status=by_status,
        by_priority=by_priority
    )


@router.get("/dashboard/overdue", response_model=OverdueRecommendationsReport)
def get_overdue_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get report of overdue recommendations.

    Returns recommendations where current_target_date < today and not in terminal status.
    """
    today = date.today()

    # Get status taxonomy
    status_taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Recommendation Status").first()
    if not status_taxonomy:
        return OverdueRecommendationsReport(total_overdue=0, by_priority=[], recommendations=[])

    # Get non-terminal status IDs
    non_terminal_statuses = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == status_taxonomy.taxonomy_id,
        ~TaxonomyValue.code.in_(TERMINAL_STATUS_CODES)
    ).all()
    non_terminal_status_ids = [s.value_id for s in non_terminal_statuses]

    # Get overdue recommendations
    overdue_recs = db.query(Recommendation).options(
        joinedload(Recommendation.model),
        joinedload(Recommendation.priority),
        joinedload(Recommendation.current_status),
        joinedload(Recommendation.assigned_to)
    ).filter(
        Recommendation.current_status_id.in_(non_terminal_status_ids),
        Recommendation.current_target_date < today
    ).order_by(
        Recommendation.current_target_date.asc()
    ).all()

    recommendations = [
        OverdueRecommendation(
            recommendation_id=rec.recommendation_id,
            recommendation_code=rec.recommendation_code,
            title=rec.title,
            model=rec.model,
            priority=rec.priority,
            current_status=rec.current_status,
            assigned_to=rec.assigned_to,
            current_target_date=rec.current_target_date,
            days_overdue=(today - rec.current_target_date).days
        )
        for rec in overdue_recs
    ]

    # Count by priority
    priority_counts = {}
    for rec in overdue_recs:
        key = (rec.priority.code, rec.priority.label)
        priority_counts[key] = priority_counts.get(key, 0) + 1

    by_priority = [
        PrioritySummary(priority_code=code, priority_label=label, count=count)
        for (code, label), count in priority_counts.items()
    ]

    return OverdueRecommendationsReport(
        total_overdue=len(recommendations),
        by_priority=by_priority,
        recommendations=recommendations
    )


@router.get("/dashboard/by-model/{model_id}", response_model=List[RecommendationListResponse])
def get_recommendations_by_model(
    model_id: int,
    include_closed: bool = Query(False, description="Include closed/dropped recommendations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all recommendations for a specific model.

    Useful for model details page integration.
    """
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    query = db.query(Recommendation).options(
        joinedload(Recommendation.model),
        joinedload(Recommendation.priority),
        joinedload(Recommendation.category),
        joinedload(Recommendation.current_status),
        joinedload(Recommendation.assigned_to)
    ).filter(
        Recommendation.model_id == model_id
    )

    if not include_closed:
        # Get non-terminal status IDs
        status_taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Recommendation Status").first()
        if status_taxonomy:
            non_terminal_statuses = db.query(TaxonomyValue).filter(
                TaxonomyValue.taxonomy_id == status_taxonomy.taxonomy_id,
                ~TaxonomyValue.code.in_(TERMINAL_STATUS_CODES)
            ).all()
            non_terminal_status_ids = [s.value_id for s in non_terminal_statuses]
            query = query.filter(Recommendation.current_status_id.in_(non_terminal_status_ids))

    recommendations = query.order_by(desc(Recommendation.created_at)).all()

    return recommendations


# ==================== RECOMMENDATION DETAIL ENDPOINTS ====================

@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a recommendation by ID with all nested relationships.

    Row-Level Security:
    - Validation team (Admin, Validator, Global Approver, Regional Approver): See all
    - DRAFT recommendations are hidden from non-validation team users
    - Other status: user must have access to the associated model
    """
    recommendation = db.query(Recommendation).options(
        joinedload(Recommendation.model),
        joinedload(Recommendation.validation_request),
        joinedload(Recommendation.monitoring_cycle),
        joinedload(Recommendation.priority),
        joinedload(Recommendation.category),
        joinedload(Recommendation.current_status),
        joinedload(Recommendation.created_by),
        joinedload(Recommendation.assigned_to),
        joinedload(Recommendation.finalized_by),
        joinedload(Recommendation.acknowledged_by),
        joinedload(Recommendation.closed_by),
        joinedload(Recommendation.action_plan_tasks).joinedload(ActionPlanTask.owner),
        joinedload(Recommendation.action_plan_tasks).joinedload(ActionPlanTask.completion_status),
        joinedload(Recommendation.rebuttals).joinedload(RecommendationRebuttal.submitted_by),
        joinedload(Recommendation.rebuttals).joinedload(RecommendationRebuttal.reviewed_by),
        joinedload(Recommendation.closure_evidence).joinedload(ClosureEvidence.uploaded_by),
        joinedload(Recommendation.status_history).joinedload(RecommendationStatusHistory.old_status),
        joinedload(Recommendation.status_history).joinedload(RecommendationStatusHistory.new_status),
        joinedload(Recommendation.status_history).joinedload(RecommendationStatusHistory.changed_by),
        joinedload(Recommendation.approvals).joinedload(RecommendationApproval.approver),
        joinedload(Recommendation.approvals).joinedload(RecommendationApproval.region),
    ).filter(Recommendation.recommendation_id == recommendation_id).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    # Apply row-level security
    if not can_see_recommendation(current_user, recommendation, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    return recommendation


@router.get("/{recommendation_id}/limitations", response_model=List[LimitationListResponse])
def get_recommendation_limitations(
    recommendation_id: int,
    include_retired: bool = Query(False, description="Include retired limitations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all limitations linked to this recommendation.

    Returns limitations that have this recommendation set as their
    mitigation recommendation (i.e., limitation.recommendation_id = recommendation_id).
    """
    # Verify recommendation exists
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    query = db.query(ModelLimitation).options(
        joinedload(ModelLimitation.category),
        joinedload(ModelLimitation.model)
    ).filter(ModelLimitation.recommendation_id == recommendation_id)

    if not include_retired:
        query = query.filter(ModelLimitation.is_retired == False)

    limitations = query.order_by(ModelLimitation.created_at.desc()).all()
    return limitations


@router.patch("/{recommendation_id}", response_model=RecommendationResponse)
def update_recommendation(
    recommendation_id: int,
    rec_update: RecommendationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a recommendation.

    Editing permissions depend on status:
    - DRAFT, PENDING_RESPONSE, PENDING_VALIDATOR_REVIEW: All fields editable
    - PENDING_ACKNOWLEDGEMENT, OPEN, REC_REWORK_REQUIRED: Limited (assigned_to, target_date only)
    - PENDING_CLOSURE, PENDING_APPROVAL, CLOSED, WITHDRAWN: No updates allowed

    Only Validators and Admins can edit recommendations.
    """
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)
    check_validator_or_admin(current_user)

    # Check status and determine allowed fields
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()

    # Statuses that allow full editing
    full_edit_statuses = ["REC_DRAFT", "REC_PENDING_RESPONSE", "REC_PENDING_VALIDATOR_REVIEW"]

    # Statuses that allow limited editing (assigned_to, target_date only)
    limited_edit_statuses = ["REC_PENDING_ACKNOWLEDGEMENT", "REC_OPEN", "REC_REWORK_REQUIRED"]

    # Statuses that don't allow editing
    no_edit_statuses = ["REC_PENDING_CLOSURE", "REC_PENDING_APPROVAL", "REC_CLOSED", "REC_WITHDRAWN"]

    if current_status.code in no_edit_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit recommendations in {current_status.label} status"
        )

    if current_status.code in limited_edit_statuses:
        # Only allow assigned_to and current_target_date changes
        has_restricted_fields = any([
            rec_update.title is not None,
            rec_update.description is not None,
            rec_update.root_cause_analysis is not None,
            rec_update.priority_id is not None,
            rec_update.category_id is not None,
        ])
        if has_restricted_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"In {current_status.label} status, only assigned_to and current_target_date can be modified"
            )

    # Capture old values for audit log
    old_values = {}
    new_values = {}

    # Apply updates based on what's provided
    if rec_update.title is not None and rec_update.title != recommendation.title:
        old_values["title"] = recommendation.title
        new_values["title"] = rec_update.title
        recommendation.title = rec_update.title
    if rec_update.description is not None and rec_update.description != recommendation.description:
        old_values["description"] = recommendation.description
        new_values["description"] = rec_update.description
        recommendation.description = rec_update.description
    if rec_update.root_cause_analysis is not None and rec_update.root_cause_analysis != recommendation.root_cause_analysis:
        old_values["root_cause_analysis"] = recommendation.root_cause_analysis
        new_values["root_cause_analysis"] = rec_update.root_cause_analysis
        recommendation.root_cause_analysis = rec_update.root_cause_analysis
    if rec_update.priority_id is not None and rec_update.priority_id != recommendation.priority_id:
        # Validate priority exists
        priority = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == rec_update.priority_id
        ).first()
        if not priority:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid priority_id"
            )
        old_values["priority_id"] = recommendation.priority_id
        new_values["priority_id"] = rec_update.priority_id
        recommendation.priority_id = rec_update.priority_id
    if rec_update.category_id is not None and rec_update.category_id != recommendation.category_id:
        old_values["category_id"] = recommendation.category_id
        new_values["category_id"] = rec_update.category_id
        recommendation.category_id = rec_update.category_id
    if rec_update.assigned_to_id is not None and rec_update.assigned_to_id != recommendation.assigned_to_id:
        # Validate user exists
        assignee = db.query(User).filter(User.user_id == rec_update.assigned_to_id).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid assigned_to_id"
            )
        old_values["assigned_to_id"] = recommendation.assigned_to_id
        new_values["assigned_to_id"] = rec_update.assigned_to_id
        recommendation.assigned_to_id = rec_update.assigned_to_id
    if rec_update.current_target_date is not None:
        old_date = str(recommendation.current_target_date) if recommendation.current_target_date else None
        new_date = str(rec_update.current_target_date)
        if old_date != new_date:
            # Validate the new target date against timeframe configuration
            validation_result = validate_target_date(
                db,
                priority_id=recommendation.priority_id,
                model_id=recommendation.model_id,
                proposed_target_date=rec_update.current_target_date,
                creation_date=recommendation.original_target_date  # Use original date as creation date
            )

            if not validation_result.is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=validation_result.message
                )

            # Require reason when changing target date
            if not rec_update.target_date_change_reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A reason/explanation is required when changing the target date."
                )

            old_values["current_target_date"] = old_date
            new_values["current_target_date"] = new_date
            recommendation.current_target_date = rec_update.current_target_date
            recommendation.target_date_change_reason = rec_update.target_date_change_reason

    # Only create audit log if there were actual changes
    if new_values:
        create_audit_log(
            db=db,
            entity_type="Recommendation",
            entity_id=recommendation.recommendation_id,
            action="UPDATE",
            user=current_user,
            old_values=old_values,
            new_values=new_values
        )

    db.commit()
    db.refresh(recommendation)
    return recommendation


# ==================== WORKFLOW TRANSITION ENDPOINTS ====================

@router.post("/{recommendation_id}/submit", response_model=RecommendationResponse)
def submit_to_developer(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit recommendation to developer. DRAFT -> PENDING_RESPONSE."""
    check_validator_or_admin(current_user)

    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    if current_status.code != "REC_DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit from {current_status.label} status. Expected DRAFT."
        )

    # Transition to PENDING_RESPONSE
    new_status = get_status_by_code(db, "REC_PENDING_RESPONSE")
    create_status_history(db, recommendation, new_status, current_user, "Submitted to developer")

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post("/{recommendation_id}/rebuttal", response_model=RebuttalSubmissionResponse)
def submit_rebuttal(
    recommendation_id: int,
    rebuttal_data: RebuttalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a rebuttal. Developer only, from PENDING_RESPONSE status."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)

    # Check permission - developer or admin
    check_developer_or_admin(current_user, recommendation)

    # Block validator from submitting rebuttal (unless admin)
    if current_user.role == "Validator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Validators cannot submit rebuttals"
        )

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    if current_status.code != "REC_PENDING_RESPONSE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit rebuttal from {current_status.label} status. Expected PENDING_RESPONSE."
        )

    # Check for existing pending rebuttal
    existing_pending = db.query(RecommendationRebuttal).filter(
        RecommendationRebuttal.recommendation_id == recommendation_id,
        RecommendationRebuttal.is_current == True,
        RecommendationRebuttal.review_decision.is_(None)
    ).first()

    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rebuttal is already pending review"
        )

    # Check one-strike rule - any previous overridden rebuttal blocks new rebuttals
    overridden_rebuttal = db.query(RecommendationRebuttal).filter(
        RecommendationRebuttal.recommendation_id == recommendation_id,
        RecommendationRebuttal.review_decision == "OVERRIDE"
    ).first()

    if overridden_rebuttal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rebuttal already overridden. Must submit action plan instead."
        )

    # Mark any existing rebuttals as not current
    db.query(RecommendationRebuttal).filter(
        RecommendationRebuttal.recommendation_id == recommendation_id,
        RecommendationRebuttal.is_current == True
    ).update({"is_current": False})

    # Create rebuttal
    rebuttal = RecommendationRebuttal(
        recommendation_id=recommendation_id,
        submitted_by_id=current_user.user_id,
        rationale=rebuttal_data.rationale,
        supporting_evidence=rebuttal_data.supporting_evidence,
        is_current=True
    )
    db.add(rebuttal)
    db.flush()

    # Transition to IN_REBUTTAL
    new_status = get_status_by_code(db, "REC_IN_REBUTTAL")
    create_status_history(
        db, recommendation, new_status, current_user,
        "Rebuttal submitted",
        f'{{"rebuttal_id": {rebuttal.rebuttal_id}}}'
    )

    db.commit()
    db.refresh(rebuttal)
    db.refresh(recommendation)

    return RebuttalSubmissionResponse(
        rebuttal_id=rebuttal.rebuttal_id,
        recommendation=recommendation
    )


@router.post("/{recommendation_id}/rebuttal/{rebuttal_id}/review", response_model=RebuttalReviewResponse)
def review_rebuttal(
    recommendation_id: int,
    rebuttal_id: int,
    review_data: RebuttalReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Review a rebuttal. Validator or Admin only."""
    check_validator_or_admin(current_user)

    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    rebuttal = db.query(RecommendationRebuttal).filter(
        RecommendationRebuttal.rebuttal_id == rebuttal_id,
        RecommendationRebuttal.recommendation_id == recommendation_id
    ).first()

    if not rebuttal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rebuttal not found"
        )

    if rebuttal.review_decision is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rebuttal has already been reviewed"
        )

    decision = review_data.decision.upper()
    if decision not in ("ACCEPT", "OVERRIDE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be ACCEPT or OVERRIDE"
        )

    # Update rebuttal
    rebuttal.reviewed_by_id = current_user.user_id
    rebuttal.reviewed_at = utc_now()
    rebuttal.review_decision = decision
    rebuttal.review_comments = review_data.comments

    # Transition status based on decision
    if decision == "ACCEPT":
        new_status = get_status_by_code(db, "REC_DROPPED")
        reason = "Rebuttal accepted - issue dropped"
    else:  # OVERRIDE
        new_status = get_status_by_code(db, "REC_PENDING_ACTION_PLAN")
        reason = "Rebuttal overridden - action plan required"

    create_status_history(
        db, recommendation, new_status, current_user, reason,
        f'{{"rebuttal_id": {rebuttal_id}, "decision": "{decision}"}}'
    )

    db.commit()
    db.refresh(rebuttal)
    db.refresh(recommendation)

    return RebuttalReviewResponse(
        rebuttal_id=rebuttal.rebuttal_id,
        review_decision=rebuttal.review_decision,
        reviewed_by=rebuttal.reviewed_by,
        reviewed_at=rebuttal.reviewed_at,
        recommendation=recommendation
    )


@router.post("/{recommendation_id}/action-plan", response_model=RecommendationResponse)
def submit_action_plan(
    recommendation_id: int,
    action_plan: ActionPlanSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit an action plan with tasks. Developer only."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)
    check_developer_or_admin(current_user, recommendation)

    # Check current status allows action plan
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    allowed_statuses = ["REC_PENDING_RESPONSE", "REC_PENDING_ACTION_PLAN"]
    if current_status.code not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit action plan from {current_status.label} status"
        )

    # Get NOT_STARTED status for tasks
    not_started_status = get_task_status_by_code(db, "TASK_NOT_STARTED")

    # Clear existing tasks (in case of resubmission)
    db.query(ActionPlanTask).filter(
        ActionPlanTask.recommendation_id == recommendation_id
    ).delete()

    # Create tasks
    for idx, task_data in enumerate(action_plan.tasks, start=1):
        task = ActionPlanTask(
            recommendation_id=recommendation_id,
            task_order=idx,
            description=task_data.description,
            owner_id=task_data.owner_id,
            target_date=task_data.target_date,
            completion_status_id=not_started_status.value_id
        )
        db.add(task)

    # Transition to PENDING_VALIDATOR_REVIEW
    new_status = get_status_by_code(db, "REC_PENDING_VALIDATOR_REVIEW")
    create_status_history(
        db, recommendation, new_status, current_user,
        f"Action plan submitted with {len(action_plan.tasks)} tasks"
    )

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post("/{recommendation_id}/skip-action-plan", response_model=RecommendationResponse)
def skip_action_plan(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Skip action plan for low-priority recommendations.
    Only allowed for priorities with requires_action_plan=False (e.g., Consideration).

    Workflow: PENDING_RESPONSE -> PENDING_VALIDATOR_REVIEW (validator still finalizes)
    Then: validator finalizes -> PENDING_ACKNOWLEDGEMENT -> developer acknowledges -> OPEN
    """
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)
    check_developer_or_admin(current_user, recommendation)

    # Verify priority allows skipping action plan
    if check_requires_action_plan(db, recommendation):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This priority level requires an action plan. Use the standard workflow."
        )

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()

    if current_status.code != "REC_PENDING_RESPONSE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot skip action plan from {current_status.label} status. Expected Pending Response."
        )

    # Skip to PENDING_VALIDATOR_REVIEW (validator still needs to finalize)
    new_status = get_status_by_code(db, "REC_PENDING_VALIDATOR_REVIEW")
    create_status_history(
        db, recommendation, new_status, current_user,
        "Action plan skipped - not required for this priority level"
    )

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.get("/{recommendation_id}/can-skip-action-plan")
def can_skip_action_plan(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if a recommendation's priority allows skipping action plan.
    Returns information about whether the action plan can be skipped.
    """
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    requires_action_plan = check_requires_action_plan(db, recommendation)

    # Check if in correct status to skip
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()

    can_skip = (
        not requires_action_plan and
        current_status.code == "REC_PENDING_RESPONSE"
    )

    return {
        "recommendation_id": recommendation_id,
        "requires_action_plan": requires_action_plan,
        "current_status_code": current_status.code,
        "can_skip_action_plan": can_skip
    }


@router.post("/{recommendation_id}/action-plan/request-revisions", response_model=RecommendationResponse)
def request_action_plan_revisions(
    recommendation_id: int,
    revision_request: ActionPlanRevisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request revisions to action plan. Validator only."""
    check_validator_or_admin(current_user)

    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    if current_status.code != "REC_PENDING_VALIDATOR_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot request revisions from {current_status.label} status"
        )

    # Transition back to PENDING_RESPONSE
    new_status = get_status_by_code(db, "REC_PENDING_RESPONSE")
    create_status_history(
        db, recommendation, new_status, current_user,
        f"Action plan revisions requested: {revision_request.reason}"
    )

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post("/{recommendation_id}/finalize", response_model=RecommendationResponse)
def finalize_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Finalize recommendation. Validator only. PENDING_VALIDATOR_REVIEW -> PENDING_ACKNOWLEDGEMENT."""
    check_validator_or_admin(current_user)

    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    if current_status.code != "REC_PENDING_VALIDATOR_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finalize from {current_status.label} status"
        )

    recommendation.finalized_at = utc_now()
    recommendation.finalized_by_id = current_user.user_id

    # Transition to PENDING_ACKNOWLEDGEMENT
    new_status = get_status_by_code(db, "REC_PENDING_ACKNOWLEDGEMENT")
    create_status_history(db, recommendation, new_status, current_user, "Recommendation finalized")

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post("/{recommendation_id}/acknowledge", response_model=RecommendationResponse)
def acknowledge_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge recommendation. Developer only. PENDING_ACKNOWLEDGEMENT -> OPEN."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)
    check_developer_or_admin(current_user, recommendation)

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    if current_status.code != "REC_PENDING_ACKNOWLEDGEMENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot acknowledge from {current_status.label} status"
        )

    recommendation.acknowledged_at = utc_now()
    recommendation.acknowledged_by_id = current_user.user_id

    # Transition to OPEN
    new_status = get_status_by_code(db, "REC_OPEN")
    create_status_history(db, recommendation, new_status, current_user, "Recommendation acknowledged")

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post("/{recommendation_id}/decline-acknowledgement", response_model=RecommendationResponse)
def decline_acknowledgement(
    recommendation_id: int,
    decline_data: DeclineAcknowledgementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Decline acknowledgement. Developer only. PENDING_ACKNOWLEDGEMENT -> PENDING_VALIDATOR_REVIEW."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)
    check_developer_or_admin(current_user, recommendation)

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    if current_status.code != "REC_PENDING_ACKNOWLEDGEMENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot decline from {current_status.label} status"
        )

    # Transition back to PENDING_VALIDATOR_REVIEW
    new_status = get_status_by_code(db, "REC_PENDING_VALIDATOR_REVIEW")
    create_status_history(
        db, recommendation, new_status, current_user,
        f"Acknowledgement declined: {decline_data.reason}"
    )

    db.commit()
    db.refresh(recommendation)
    return recommendation


# ==================== TASK ENDPOINTS ====================

@router.patch("/{recommendation_id}/tasks/{task_id}", response_model=ActionPlanTaskResponse)
def update_task(
    recommendation_id: int,
    task_id: int,
    task_update: ActionPlanTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a task status or details. Task owner, assigned developer, or Admin."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    task = db.query(ActionPlanTask).filter(
        ActionPlanTask.task_id == task_id,
        ActionPlanTask.recommendation_id == recommendation_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check permission - task owner, assigned developer, or admin
    if (current_user.role != "Admin" and
        current_user.user_id != task.owner_id and
        current_user.user_id != recommendation.assigned_to_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only task owner, assigned developer, or Admin can update task"
        )

    # Apply updates
    if task_update.description is not None:
        task.description = task_update.description
    if task_update.owner_id is not None:
        task.owner_id = task_update.owner_id
    if task_update.target_date is not None:
        task.target_date = task_update.target_date
    if task_update.completion_notes is not None:
        task.completion_notes = task_update.completion_notes

    # Handle status change
    if task_update.completion_status_id is not None:
        # Check if transitioning to COMPLETED
        new_status = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == task_update.completion_status_id
        ).first()
        if new_status and new_status.code == "TASK_COMPLETED":
            task.completed_date = date.today()
        task.completion_status_id = task_update.completion_status_id

    db.commit()
    db.refresh(task)
    return task


# ==================== EVIDENCE ENDPOINTS ====================

@router.post("/{recommendation_id}/evidence", response_model=ClosureEvidenceResponse, status_code=status.HTTP_201_CREATED)
def upload_evidence(
    recommendation_id: int,
    evidence_data: ClosureEvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload closure evidence. Developer only, when status is OPEN or REWORK_REQUIRED."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)
    check_developer_or_admin(current_user, recommendation)

    # Check status allows evidence upload
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    allowed_statuses = ["REC_OPEN", "REC_REWORK_REQUIRED"]
    if current_status.code not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot upload evidence in {current_status.label} status"
        )

    evidence = ClosureEvidence(
        recommendation_id=recommendation_id,
        file_name=evidence_data.file_name,
        file_path=evidence_data.file_path,
        file_type=evidence_data.file_type,
        file_size_bytes=evidence_data.file_size_bytes,
        description=evidence_data.description,
        uploaded_by_id=current_user.user_id
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


# ==================== CLOSURE WORKFLOW ENDPOINTS ====================

@router.post("/{recommendation_id}/submit-closure", response_model=RecommendationResponse)
def submit_for_closure(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit recommendation for closure. Developer only. OPEN -> PENDING_CLOSURE_REVIEW."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)
    check_developer_or_admin(current_user, recommendation)

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    allowed_statuses = ["REC_OPEN", "REC_REWORK_REQUIRED"]
    if current_status.code not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit for closure from {current_status.label} status"
        )

    # Check all tasks are completed
    incomplete_tasks = db.query(ActionPlanTask).join(TaxonomyValue).filter(
        ActionPlanTask.recommendation_id == recommendation_id,
        TaxonomyValue.code != "TASK_COMPLETED"
    ).count()

    if incomplete_tasks > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{incomplete_tasks} task(s) are not completed. Complete all tasks before submitting for closure."
        )

    # Check evidence is provided
    evidence_count = db.query(ClosureEvidence).filter(
        ClosureEvidence.recommendation_id == recommendation_id
    ).count()

    if evidence_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one piece of closure evidence is required"
        )

    # Transition to PENDING_CLOSURE_REVIEW
    new_status = get_status_by_code(db, "REC_PENDING_CLOSURE_REVIEW")
    create_status_history(db, recommendation, new_status, current_user, "Submitted for closure review")

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post("/{recommendation_id}/closure-review", response_model=RecommendationResponse)
def review_closure(
    recommendation_id: int,
    review_data: ClosureReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Review closure submission. Validator only."""
    check_validator_or_admin(current_user)

    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    check_not_terminal(recommendation, db)

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()
    if current_status.code != "REC_PENDING_CLOSURE_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review closure from {current_status.label} status"
        )

    decision = review_data.decision.upper()
    if decision not in ("APPROVE", "RETURN"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be APPROVE or RETURN"
        )

    if decision == "RETURN":
        # Transition to REWORK_REQUIRED
        new_status = get_status_by_code(db, "REC_REWORK_REQUIRED")
        create_status_history(
            db, recommendation, new_status, current_user,
            f"Closure returned for rework: {review_data.comments}"
        )
    else:  # APPROVE
        # Check if final approval is required based on priority
        priority_config = db.query(RecommendationPriorityConfig).filter(
            RecommendationPriorityConfig.priority_id == recommendation.priority_id
        ).first()

        if priority_config and priority_config.requires_final_approval:
            # Create approvals and transition to PENDING_FINAL_APPROVAL
            create_final_approvals(db, recommendation)
            new_status = get_status_by_code(db, "REC_PENDING_FINAL_APPROVAL")
            recommendation.closure_summary = review_data.closure_summary
            create_status_history(
                db, recommendation, new_status, current_user,
                "Closure approved by validator - awaiting final approvals"
            )
        else:
            # Low priority - close directly
            new_status = get_status_by_code(db, "REC_CLOSED")
            recommendation.closed_at = utc_now()
            recommendation.closed_by_id = current_user.user_id
            recommendation.closure_summary = review_data.closure_summary
            create_status_history(
                db, recommendation, new_status, current_user,
                "Recommendation closed"
            )

    db.commit()
    db.refresh(recommendation)
    return recommendation


# ==================== APPROVAL ENDPOINTS ====================

@router.get("/{recommendation_id}/approvals", response_model=List[ApprovalResponse])
def list_approvals(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all approvals for a recommendation."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    approvals = db.query(RecommendationApproval).options(
        joinedload(RecommendationApproval.approver),
        joinedload(RecommendationApproval.region),
        joinedload(RecommendationApproval.represented_region),
        joinedload(RecommendationApproval.voided_by)
    ).filter(
        RecommendationApproval.recommendation_id == recommendation_id
    ).all()

    return approvals


def check_approval_authorization(user: User, approval: RecommendationApproval):
    """
    Verify user has authorization to submit an approval.
    - Admin can approve anything
    - Global Approver can approve GLOBAL approvals
    - Regional Approver can approve REGIONAL approvals for their assigned regions
    """
    # Admin can approve anything
    if user.role == "Admin":
        return

    if approval.approval_type == "GLOBAL":
        if user.role != "Global Approver":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Global Approvers or Admins can approve Global approvals"
            )
    elif approval.approval_type == "REGIONAL":
        if user.role != "Regional Approver":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Regional Approvers or Admins can approve Regional approvals"
            )
        # Check user is assigned to this specific region
        user_region_ids = [r.region_id for r in user.regions]
        if approval.region_id not in user_region_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to approve for this region"
            )


@router.post("/{recommendation_id}/approvals/{approval_id}/approve", response_model=ApprovalResponse)
def approve_recommendation(
    recommendation_id: int,
    approval_id: int,
    approval_data: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a recommendation. Global Approver, Regional Approver, or Admin."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    approval = db.query(RecommendationApproval).options(
        joinedload(RecommendationApproval.region)
    ).filter(
        RecommendationApproval.approval_id == approval_id,
        RecommendationApproval.recommendation_id == recommendation_id
    ).first()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found"
        )

    if approval.approval_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval is already {approval.approval_status}"
        )

    # Verify authorization
    check_approval_authorization(current_user, approval)

    # Update approval
    approval.approver_id = current_user.user_id
    approval.approved_at = utc_now()
    approval.approval_status = "APPROVED"
    approval.comments = approval_data.comments
    approval.approval_evidence = approval_data.approval_evidence

    # Track which region the approver represents (for audit trail)
    if approval.approval_type == "REGIONAL":
        approval.represented_region_id = approval.region_id

    # Check if all approvals are now complete
    db.flush()
    if check_all_approvals_complete(recommendation):
        # Transition to CLOSED
        new_status = get_status_by_code(db, "REC_CLOSED")
        recommendation.closed_at = utc_now()
        recommendation.closed_by_id = current_user.user_id
        create_status_history(
            db, recommendation, new_status, current_user,
            "All approvals complete - recommendation closed"
        )

    db.commit()
    db.refresh(approval)
    return approval


@router.post("/{recommendation_id}/approvals/{approval_id}/reject", response_model=ApprovalResponse)
def reject_recommendation_approval(
    recommendation_id: int,
    approval_id: int,
    reject_data: ApprovalRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject an approval. Returns recommendation to REWORK_REQUIRED status."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    approval = db.query(RecommendationApproval).options(
        joinedload(RecommendationApproval.region)
    ).filter(
        RecommendationApproval.approval_id == approval_id,
        RecommendationApproval.recommendation_id == recommendation_id
    ).first()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found"
        )

    if approval.approval_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval is already {approval.approval_status}"
        )

    # Verify authorization
    check_approval_authorization(current_user, approval)

    # Rejection reason is required
    if not reject_data.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required"
        )

    # Update approval
    approval.approver_id = current_user.user_id
    approval.approved_at = utc_now()
    approval.approval_status = "REJECTED"
    approval.comments = reject_data.rejection_reason

    # Track which region the approver represents
    if approval.approval_type == "REGIONAL":
        approval.represented_region_id = approval.region_id

    # Transition recommendation back to REWORK_REQUIRED
    new_status = get_status_by_code(db, "REC_REWORK_REQUIRED")
    create_status_history(
        db, recommendation, new_status, current_user,
        f"Approval rejected: {reject_data.rejection_reason}"
    )

    # Reset all pending approvals back to PENDING for re-approval after rework
    db.query(RecommendationApproval).filter(
        RecommendationApproval.recommendation_id == recommendation_id,
        RecommendationApproval.approval_status == "APPROVED"
    ).update({"approval_status": "PENDING", "approver_id": None, "approved_at": None})

    db.commit()
    db.refresh(approval)
    return approval


@router.post("/{recommendation_id}/approvals/{approval_id}/void", response_model=ApprovalResponse)
def void_approval_requirement(
    recommendation_id: int,
    approval_id: int,
    void_data: ApprovalRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Void an approval requirement. Admin only."""
    check_admin(current_user)

    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    approval = db.query(RecommendationApproval).filter(
        RecommendationApproval.approval_id == approval_id,
        RecommendationApproval.recommendation_id == recommendation_id
    ).first()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found"
        )

    if approval.approval_status not in ("PENDING", "REJECTED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot void approval that is already {approval.approval_status}"
        )

    # Void reason is required
    if not void_data.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Void reason is required"
        )

    # Update approval
    approval.approval_status = "VOIDED"
    approval.voided_by_id = current_user.user_id
    approval.voided_at = utc_now()
    approval.void_reason = void_data.rejection_reason

    # Check if all approvals are now complete (voided counts as complete)
    db.flush()
    if check_all_approvals_complete(recommendation):
        # Transition to CLOSED
        new_status = get_status_by_code(db, "REC_CLOSED")
        recommendation.closed_at = utc_now()
        recommendation.closed_by_id = current_user.user_id
        create_status_history(
            db, recommendation, new_status, current_user,
            "All approvals complete (with voided) - recommendation closed"
        )

    db.commit()
    db.refresh(approval)
    return approval

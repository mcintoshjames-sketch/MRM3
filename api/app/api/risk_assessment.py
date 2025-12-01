"""API endpoints for Model Risk Assessment."""
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.time import utc_now
from app.core.risk_calculation import (
    calculate_qualitative_score,
    lookup_inherent_risk,
    map_to_tier_code,
    RATING_SCORES
)
from app.models.user import User
from app.models.model import Model
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.audit_log import AuditLog
from app.models.risk_assessment import (
    ModelRiskAssessment,
    QualitativeRiskFactor,
    QualitativeFactorAssessment,
)
from app.schemas.risk_assessment import (
    RiskAssessmentCreate,
    RiskAssessmentUpdate,
    RiskAssessmentResponse,
    RiskAssessmentHistoryItem,
    QualitativeFactorResponse,
    RegionBrief,
    UserBrief,
    TaxonomyValueBrief,
)
from app.models.region import Region
from app.api.validation_workflow import reset_validation_plan_for_tier_change

router = APIRouter()


def create_audit_log(
    db: Session, entity_type: str, entity_id: int,
    action: str, user_id: int, changes: dict = None
):
    """Create an audit log entry for risk assessment changes."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def require_admin_or_validator(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an Admin or Validator."""
    if current_user.role not in ("Admin", "Validator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Validator role required"
        )
    return current_user


def get_model_or_404(db: Session, model_id: int) -> Model:
    """Get model by ID or raise 404."""
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


def get_assessment_or_404(
    db: Session, model_id: int, assessment_id: int
) -> ModelRiskAssessment:
    """Get assessment by ID, ensuring it belongs to the model."""
    assessment = (
        db.query(ModelRiskAssessment)
        .options(
            joinedload(ModelRiskAssessment.region),
            joinedload(ModelRiskAssessment.assessed_by),
            joinedload(ModelRiskAssessment.final_tier),
            joinedload(ModelRiskAssessment.factor_assessments)
            .joinedload(QualitativeFactorAssessment.factor),
        )
        .filter(
            ModelRiskAssessment.assessment_id == assessment_id,
            ModelRiskAssessment.model_id == model_id,
        )
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


def get_tier_value(db: Session, tier_code: str) -> Optional[TaxonomyValue]:
    """Get the taxonomy value for a tier code (TIER_1, TIER_2, etc.)."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.name == "Model Risk Tier").first()
    if not taxonomy:
        return None
    return (
        db.query(TaxonomyValue)
        .filter(
            TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
            TaxonomyValue.code == tier_code,
        )
        .first()
    )


def build_assessment_response(
    assessment: ModelRiskAssessment,
    db: Session,
) -> RiskAssessmentResponse:
    """Build the full response schema from an assessment."""
    # Build factor responses
    factor_responses = []
    for fa in assessment.factor_assessments:
        factor_responses.append(
            QualitativeFactorResponse(
                factor_assessment_id=fa.factor_assessment_id,
                factor_id=fa.factor_id,
                factor_code=fa.factor.code if fa.factor else "",
                factor_name=fa.factor.name if fa.factor else "",
                rating=fa.rating,
                comment=fa.comment,
                weight=float(fa.weight_at_assessment),
                score=float(fa.score) if fa.score else None,
            )
        )

    # Calculate effective values
    eff_quantitative = assessment.quantitative_override or assessment.quantitative_rating
    eff_qualitative = assessment.qualitative_override or assessment.qualitative_calculated_level

    derived = None
    if eff_quantitative and eff_qualitative:
        derived = lookup_inherent_risk(eff_quantitative, eff_qualitative)

    eff_final = assessment.derived_risk_tier_override or derived

    # Determine completeness
    has_quantitative = assessment.quantitative_rating is not None
    has_all_factors = len(factor_responses) > 0 and all(
        f.rating is not None for f in factor_responses
    )
    is_complete = has_quantitative and has_all_factors

    return RiskAssessmentResponse(
        assessment_id=assessment.assessment_id,
        model_id=assessment.model_id,
        region=RegionBrief.model_validate(assessment.region) if assessment.region else None,
        qualitative_factors=factor_responses,
        qualitative_calculated_score=(
            float(assessment.qualitative_calculated_score)
            if assessment.qualitative_calculated_score
            else None
        ),
        qualitative_calculated_level=assessment.qualitative_calculated_level,
        qualitative_override=assessment.qualitative_override,
        qualitative_override_comment=assessment.qualitative_override_comment,
        qualitative_effective_level=eff_qualitative,
        quantitative_rating=assessment.quantitative_rating,
        quantitative_comment=assessment.quantitative_comment,
        quantitative_override=assessment.quantitative_override,
        quantitative_override_comment=assessment.quantitative_override_comment,
        quantitative_effective_rating=eff_quantitative,
        derived_risk_tier=derived,
        derived_risk_tier_override=assessment.derived_risk_tier_override,
        derived_risk_tier_override_comment=assessment.derived_risk_tier_override_comment,
        derived_risk_tier_effective=eff_final,
        final_tier=(
            TaxonomyValueBrief.model_validate(assessment.final_tier)
            if assessment.final_tier
            else None
        ),
        assessed_by=(
            UserBrief.model_validate(assessment.assessed_by)
            if assessment.assessed_by
            else None
        ),
        assessed_at=assessment.assessed_at,
        is_complete=is_complete,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
    )


def sync_model_tier(
    db: Session, model: Model, assessment: ModelRiskAssessment, tier_code: Optional[str],
    user_id: Optional[int] = None
) -> None:
    """Sync model's risk_tier_id with the global assessment's final tier.

    If the tier is changing and there are open validation requests,
    this will reset their validation plan components and void approvals.
    """
    # Only sync for global assessments (region_id is None)
    if assessment.region_id is not None:
        return

    # Track old tier for change detection
    old_tier_id = model.risk_tier_id

    if tier_code:
        tier_value = get_tier_value(db, tier_code)
        if tier_value:
            new_tier_id = tier_value.value_id
            model.risk_tier_id = new_tier_id
            assessment.final_tier_id = new_tier_id

            # Force reset validation plans if tier actually changed
            if old_tier_id != new_tier_id and user_id:
                reset_validation_plan_for_tier_change(
                    db=db,
                    model_id=model.model_id,
                    new_tier_id=new_tier_id,
                    user_id=user_id,
                    force=True  # Auto-apply the reset
                )
    else:
        model.risk_tier_id = None
        assessment.final_tier_id = None

        # Force reset if tier changed to None
        if old_tier_id is not None and user_id:
            reset_validation_plan_for_tier_change(
                db=db,
                model_id=model.model_id,
                new_tier_id=None,
                user_id=user_id,
                force=True
            )


# ============================================================================
# Endpoints
# ============================================================================

@router.get(
    "/models/{model_id}/risk-assessments/",
    response_model=List[RiskAssessmentResponse],
)
def list_assessments(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[RiskAssessmentResponse]:
    """List all risk assessments for a model."""
    # Verify model exists
    get_model_or_404(db, model_id)

    assessments = (
        db.query(ModelRiskAssessment)
        .options(
            joinedload(ModelRiskAssessment.region),
            joinedload(ModelRiskAssessment.assessed_by),
            joinedload(ModelRiskAssessment.final_tier),
            joinedload(ModelRiskAssessment.factor_assessments)
            .joinedload(QualitativeFactorAssessment.factor),
        )
        .filter(ModelRiskAssessment.model_id == model_id)
        .all()
    )

    return [build_assessment_response(a, db) for a in assessments]


@router.get(
    "/models/{model_id}/risk-assessments/history",
    response_model=List[RiskAssessmentHistoryItem],
)
def get_assessment_history(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[RiskAssessmentHistoryItem]:
    """Get risk assessment change history for a model."""
    # Verify model exists
    get_model_or_404(db, model_id)

    # Get all assessment IDs for this model (including deleted ones from audit logs)
    assessment_ids = (
        db.query(ModelRiskAssessment.assessment_id)
        .filter(ModelRiskAssessment.model_id == model_id)
        .all()
    )
    assessment_ids = [a[0] for a in assessment_ids]

    # Also find assessment IDs from audit logs (for deleted assessments)
    audit_logs_with_model = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "ModelRiskAssessment",
        )
        .all()
    )

    # Filter logs that belong to this model
    relevant_logs = []
    for log in audit_logs_with_model:
        if log.entity_id in assessment_ids:
            relevant_logs.append(log)
        elif log.changes and isinstance(log.changes, dict):
            # Check if this log's changes dict has model_id matching
            if log.changes.get("model_id") == model_id:
                relevant_logs.append(log)
            elif log.changes.get("old", {}).get("model_id") == model_id:
                relevant_logs.append(log)
            elif log.changes.get("new", {}).get("model_id") == model_id:
                relevant_logs.append(log)

    # Build history items
    history_items = []
    for log in relevant_logs:
        # Get user name
        user_name = None
        if log.user_id:
            user = db.query(User).filter(User.user_id == log.user_id).first()
            if user:
                user_name = user.full_name

        # Extract region info
        region_id = None
        region_name = None
        if log.changes and isinstance(log.changes, dict):
            region_id = log.changes.get("region_id")
            if region_id is None and "old" in log.changes:
                region_id = log.changes.get("old", {}).get("region_id")
            if region_id is None and "new" in log.changes:
                region_id = log.changes.get("new", {}).get("region_id")

        if region_id:
            region = db.query(Region).filter(Region.region_id == region_id).first()
            if region:
                region_name = region.name

        # Extract tier changes
        old_tier = None
        new_tier = None
        old_quantitative = None
        new_quantitative = None
        old_qualitative = None
        new_qualitative = None

        if log.changes and isinstance(log.changes, dict):
            if log.action == "CREATE":
                new_quantitative = log.changes.get("quantitative_rating")
                new_qualitative = log.changes.get("qualitative_override")
                new_tier = log.changes.get("derived_risk_tier_override")
            elif log.action == "UPDATE":
                old_data = log.changes.get("old", {})
                new_data = log.changes.get("new", {})
                old_quantitative = old_data.get("quantitative_rating")
                new_quantitative = new_data.get("quantitative_rating")
                old_qualitative = old_data.get("qualitative_override") or old_data.get("qualitative_calculated_level")
                new_qualitative = new_data.get("qualitative_override") or new_data.get("qualitative_calculated_level")
                old_tier = old_data.get("derived_risk_tier_override") or old_data.get("derived_risk_tier")
                new_tier = new_data.get("derived_risk_tier_override") or new_data.get("derived_risk_tier")
            elif log.action == "DELETE":
                old_tier = log.changes.get("derived_risk_tier_override")

        # Build summary
        changes_summary = _build_changes_summary(
            log.action, region_name,
            old_tier, new_tier,
            old_quantitative, new_quantitative,
            old_qualitative, new_qualitative
        )

        history_items.append(
            RiskAssessmentHistoryItem(
                log_id=log.log_id,
                action=log.action,
                timestamp=log.timestamp,
                user_id=log.user_id,
                user_name=user_name,
                region_id=region_id,
                region_name=region_name,
                old_tier=old_tier,
                new_tier=new_tier,
                old_quantitative=old_quantitative,
                new_quantitative=new_quantitative,
                old_qualitative=old_qualitative,
                new_qualitative=new_qualitative,
                changes_summary=changes_summary,
            )
        )

    # Sort by timestamp descending (most recent first)
    history_items.sort(key=lambda x: x.timestamp, reverse=True)
    return history_items


def _build_changes_summary(
    action: str,
    region_name: Optional[str],
    old_tier: Optional[str],
    new_tier: Optional[str],
    old_quantitative: Optional[str],
    new_quantitative: Optional[str],
    old_qualitative: Optional[str],
    new_qualitative: Optional[str],
) -> str:
    """Build a human-readable summary of assessment changes."""
    scope = f"({region_name})" if region_name else "(Global)"

    if action == "CREATE":
        parts = [f"Created {scope} assessment"]
        if new_quantitative:
            parts.append(f"Quantitative: {new_quantitative}")
        if new_tier:
            parts.append(f"Tier: {new_tier}")
        return ". ".join(parts)

    elif action == "DELETE":
        return f"Deleted {scope} assessment"

    elif action == "UPDATE":
        changes = []
        if old_quantitative != new_quantitative:
            changes.append(f"Quantitative: {old_quantitative or 'None'} → {new_quantitative or 'None'}")
        if old_qualitative != new_qualitative:
            changes.append(f"Qualitative: {old_qualitative or 'None'} → {new_qualitative or 'None'}")
        if old_tier != new_tier:
            changes.append(f"Tier: {old_tier or 'None'} → {new_tier or 'None'}")

        if changes:
            return f"Updated {scope}: " + ", ".join(changes)
        return f"Updated {scope} assessment"

    return f"{action} {scope} assessment"


@router.get(
    "/models/{model_id}/risk-assessments/{assessment_id}",
    response_model=RiskAssessmentResponse,
)
def get_assessment(
    model_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskAssessmentResponse:
    """Get a specific risk assessment."""
    assessment = get_assessment_or_404(db, model_id, assessment_id)
    return build_assessment_response(assessment, db)


@router.post(
    "/models/{model_id}/risk-assessments/",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    model_id: int,
    data: RiskAssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator),
) -> RiskAssessmentResponse:
    """Create a new risk assessment for a model."""
    model = get_model_or_404(db, model_id)

    # Check for duplicate (same model + region)
    existing = (
        db.query(ModelRiskAssessment)
        .filter(
            ModelRiskAssessment.model_id == model_id,
            ModelRiskAssessment.region_id == data.region_id,
        )
        .first()
    )
    if existing:
        scope = "global" if data.region_id is None else "regional"
        raise HTTPException(
            status_code=409,
            detail=f"A {scope} assessment already exists for this model",
        )

    # Create assessment
    assessment = ModelRiskAssessment(
        model_id=model_id,
        region_id=data.region_id,
        quantitative_rating=data.quantitative_rating,
        quantitative_comment=data.quantitative_comment,
        quantitative_override=data.quantitative_override,
        quantitative_override_comment=data.quantitative_override_comment,
        qualitative_override=data.qualitative_override,
        qualitative_override_comment=data.qualitative_override_comment,
        derived_risk_tier_override=data.derived_risk_tier_override,
        derived_risk_tier_override_comment=data.derived_risk_tier_override_comment,
        assessed_by_id=current_user.user_id,
        assessed_at=utc_now(),
    )
    db.add(assessment)
    db.flush()  # Get assessment_id

    # Create audit log for assessment creation
    create_audit_log(
        db=db,
        entity_type="ModelRiskAssessment",
        entity_id=assessment.assessment_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "model_id": model_id,
            "region_id": data.region_id,
            "quantitative_rating": data.quantitative_rating,
            "quantitative_override": data.quantitative_override,
            "quantitative_override_comment": data.quantitative_override_comment,
            "qualitative_override": data.qualitative_override,
            "qualitative_override_comment": data.qualitative_override_comment,
            "derived_risk_tier_override": data.derived_risk_tier_override,
            "derived_risk_tier_override_comment": data.derived_risk_tier_override_comment,
        }
    )

    # Get active factors for weight snapshots
    active_factors = (
        db.query(QualitativeRiskFactor)
        .filter(QualitativeRiskFactor.is_active == True)
        .all()
    )
    factor_weights = {f.factor_id: f.weight for f in active_factors}

    # Create factor assessments
    factor_assessments = []
    for fr in data.factor_ratings:
        weight = factor_weights.get(fr.factor_id, Decimal("0"))
        score = None
        if fr.rating:
            points = RATING_SCORES.get(fr.rating, 0)
            score = weight * points

        fa = QualitativeFactorAssessment(
            assessment_id=assessment.assessment_id,
            factor_id=fr.factor_id,
            rating=fr.rating,
            comment=fr.comment,
            weight_at_assessment=weight,
            score=score,
        )
        db.add(fa)
        factor_assessments.append(fa)

    # Calculate qualitative score
    if factor_assessments:
        score, level = calculate_qualitative_score(factor_assessments)
        assessment.qualitative_calculated_score = score
        assessment.qualitative_calculated_level = level

    # Calculate derived tier
    eff_quantitative = assessment.quantitative_override or assessment.quantitative_rating
    eff_qualitative = assessment.qualitative_override or assessment.qualitative_calculated_level

    derived = None
    if eff_quantitative and eff_qualitative:
        derived = lookup_inherent_risk(eff_quantitative, eff_qualitative)
    assessment.derived_risk_tier = derived

    # Get final tier
    eff_final = assessment.derived_risk_tier_override or derived
    tier_code = map_to_tier_code(eff_final)

    # Sync model tier (for global assessments) - includes force reset if tier changed
    sync_model_tier(db, model, assessment, tier_code, user_id=current_user.user_id)

    db.commit()

    # Reload with relationships
    assessment = get_assessment_or_404(db, model_id, assessment.assessment_id)
    return build_assessment_response(assessment, db)


@router.put(
    "/models/{model_id}/risk-assessments/{assessment_id}",
    response_model=RiskAssessmentResponse,
)
def update_assessment(
    model_id: int,
    assessment_id: int,
    data: RiskAssessmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator),
) -> RiskAssessmentResponse:
    """Update an existing risk assessment."""
    model = get_model_or_404(db, model_id)
    assessment = get_assessment_or_404(db, model_id, assessment_id)

    # Capture old values for audit log
    old_values = {
        "quantitative_rating": assessment.quantitative_rating,
        "quantitative_override": assessment.quantitative_override,
        "qualitative_override": assessment.qualitative_override,
        "derived_risk_tier_override": assessment.derived_risk_tier_override,
        "derived_risk_tier": assessment.derived_risk_tier,
    }

    # Update fields
    assessment.quantitative_rating = data.quantitative_rating
    assessment.quantitative_comment = data.quantitative_comment
    assessment.quantitative_override = data.quantitative_override
    assessment.quantitative_override_comment = data.quantitative_override_comment
    assessment.qualitative_override = data.qualitative_override
    assessment.qualitative_override_comment = data.qualitative_override_comment
    assessment.derived_risk_tier_override = data.derived_risk_tier_override
    assessment.derived_risk_tier_override_comment = data.derived_risk_tier_override_comment
    assessment.assessed_by_id = current_user.user_id
    assessment.assessed_at = utc_now()
    assessment.updated_at = utc_now()

    # Get active factors for weight snapshots
    active_factors = (
        db.query(QualitativeRiskFactor)
        .filter(QualitativeRiskFactor.is_active == True)
        .all()
    )
    factor_weights = {f.factor_id: f.weight for f in active_factors}

    # Delete existing factor assessments and recreate
    db.query(QualitativeFactorAssessment).filter(
        QualitativeFactorAssessment.assessment_id == assessment_id
    ).delete()

    # Create new factor assessments
    factor_assessments = []
    for fr in data.factor_ratings:
        weight = factor_weights.get(fr.factor_id, Decimal("0"))
        score = None
        if fr.rating:
            points = RATING_SCORES.get(fr.rating, 0)
            score = weight * points

        fa = QualitativeFactorAssessment(
            assessment_id=assessment.assessment_id,
            factor_id=fr.factor_id,
            rating=fr.rating,
            comment=fr.comment,
            weight_at_assessment=weight,
            score=score,
        )
        db.add(fa)
        factor_assessments.append(fa)

    # Calculate qualitative score
    if factor_assessments:
        score, level = calculate_qualitative_score(factor_assessments)
        assessment.qualitative_calculated_score = score
        assessment.qualitative_calculated_level = level
    else:
        assessment.qualitative_calculated_score = None
        assessment.qualitative_calculated_level = None

    # Calculate derived tier
    eff_quantitative = assessment.quantitative_override or assessment.quantitative_rating
    eff_qualitative = assessment.qualitative_override or assessment.qualitative_calculated_level

    derived = None
    if eff_quantitative and eff_qualitative:
        derived = lookup_inherent_risk(eff_quantitative, eff_qualitative)
    assessment.derived_risk_tier = derived

    # Get final tier
    eff_final = assessment.derived_risk_tier_override or derived
    tier_code = map_to_tier_code(eff_final)

    # Sync model tier (for global assessments) - includes force reset if tier changed
    sync_model_tier(db, model, assessment, tier_code, user_id=current_user.user_id)

    # Create audit log for update
    new_values = {
        "quantitative_rating": data.quantitative_rating,
        "quantitative_override": data.quantitative_override,
        "qualitative_override": data.qualitative_override,
        "derived_risk_tier_override": data.derived_risk_tier_override,
        "derived_risk_tier": derived,
    }
    create_audit_log(
        db=db,
        entity_type="ModelRiskAssessment",
        entity_id=assessment_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={
            "old": old_values,
            "new": new_values,
        }
    )

    db.commit()

    # Reload with relationships
    assessment = get_assessment_or_404(db, model_id, assessment.assessment_id)
    return build_assessment_response(assessment, db)


@router.delete(
    "/models/{model_id}/risk-assessments/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assessment(
    model_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator),
) -> None:
    """Delete a risk assessment."""
    model = get_model_or_404(db, model_id)
    assessment = get_assessment_or_404(db, model_id, assessment_id)

    # Clear model tier if this was the global assessment
    if assessment.region_id is None:
        model.risk_tier_id = None

    # Create audit log for delete
    create_audit_log(
        db=db,
        entity_type="ModelRiskAssessment",
        entity_id=assessment_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "model_id": model_id,
            "region_id": assessment.region_id,
        }
    )

    db.delete(assessment)
    db.commit()

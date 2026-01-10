"""Model Overlays API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin, is_validator
from app.core.rls import can_access_model
from app.core.team_utils import get_models_team_map
from app.core.time import utc_now
from app.core.monitoring_scope import get_cycle_scope_model_ids
from app.models import (
    User, Model, Region, Team, TaxonomyValue,
    ModelOverlay, ModelLimitation, MonitoringResult, MonitoringCycle, MonitoringPlan,
    Recommendation, ModelStatus
)
from app.schemas.model_overlay import (
    ModelOverlayCreate, ModelOverlayUpdate, ModelOverlayRetire,
    ModelOverlayResponse, ModelOverlayListResponse,
    ModelOverlayReportItem, ModelOverlaysReportResponse
)


router = APIRouter()


def require_admin_or_validator(current_user: User = Depends(get_current_user)) -> User:
    """Require Admin or Validator role for the current user."""
    if not (is_admin(current_user) or is_validator(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Validator role required"
        )
    return current_user


def _get_model_or_404(db: Session, model_id: int, user: User) -> Model:
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model or not can_access_model(model_id, user, db):
        raise HTTPException(status_code=404, detail="Model not found")
    return model


def _get_overlay_with_relations(db: Session, overlay_id: int) -> ModelOverlay:
    overlay = db.query(ModelOverlay).options(
        joinedload(ModelOverlay.model),
        joinedload(ModelOverlay.region),
        joinedload(ModelOverlay.trigger_monitoring_result),
        joinedload(ModelOverlay.trigger_monitoring_cycle),
        joinedload(ModelOverlay.related_recommendation),
        joinedload(ModelOverlay.related_limitation),
        joinedload(ModelOverlay.created_by),
        joinedload(ModelOverlay.retired_by),
    ).filter(ModelOverlay.overlay_id == overlay_id).first()
    if not overlay:
        raise HTTPException(status_code=404, detail="Overlay not found")
    return overlay


def _log_audit(
    db: Session,
    entity_id: int,
    action: str,
    user_id: int,
    old_values: dict | None = None,
    new_values: dict | None = None
):
    changes = {}
    if old_values is not None:
        changes["old"] = old_values
    if new_values is not None:
        changes["new"] = new_values
    from app.models.audit_log import AuditLog
    db.add(AuditLog(
        entity_type="ModelOverlay",
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes if changes else None
    ))


def _validate_region(db: Session, region_id: int) -> None:
    region = db.query(Region).filter(Region.region_id == region_id).first()
    if not region:
        raise HTTPException(status_code=400, detail="Invalid region_id")


def _validate_monitoring_result(db: Session, model_id: int, result_id: int) -> MonitoringResult:
    result = db.query(MonitoringResult).options(
        joinedload(MonitoringResult.cycle)
        .joinedload(MonitoringCycle.plan)
        .joinedload(MonitoringPlan.models)
    ).filter(MonitoringResult.result_id == result_id).first()
    if not result:
        raise HTTPException(status_code=400, detail="Invalid trigger_monitoring_result_id")

    if result.model_id is not None:
        if result.model_id != model_id:
            raise HTTPException(status_code=400, detail="Monitoring result does not belong to this model")
        return result

    scope_model_ids = get_cycle_scope_model_ids(db, result.cycle) if result.cycle else set()
    if len(scope_model_ids) == 1 and model_id in scope_model_ids:
        return result

    raise HTTPException(status_code=400, detail="Monitoring result does not belong to this model")


def _validate_monitoring_cycle(db: Session, model_id: int, cycle_id: int) -> MonitoringCycle:
    cycle = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.plan).joinedload(MonitoringPlan.models)
    ).filter(MonitoringCycle.cycle_id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=400, detail="Invalid trigger_monitoring_cycle_id")

    scope_model_ids = get_cycle_scope_model_ids(db, cycle)
    if model_id not in scope_model_ids:
        raise HTTPException(status_code=400, detail="Monitoring cycle does not include this model")
    return cycle


def _validate_limitation(db: Session, model_id: int, limitation_id: int) -> ModelLimitation:
    limitation = db.query(ModelLimitation).filter(
        ModelLimitation.limitation_id == limitation_id
    ).first()
    if not limitation:
        raise HTTPException(status_code=400, detail="Invalid related_limitation_id")
    if limitation.model_id != model_id:
        raise HTTPException(status_code=400, detail="Related limitation does not belong to this model")
    return limitation


def _validate_recommendation(db: Session, model_id: int, recommendation_id: int) -> Recommendation:
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()
    if not recommendation:
        raise HTTPException(status_code=400, detail="Invalid related_recommendation_id")
    if recommendation.model_id != model_id:
        raise HTTPException(status_code=400, detail="Related recommendation does not belong to this model")
    return recommendation


@router.get(
    "/models/{model_id}/overlays",
    response_model=List[ModelOverlayListResponse],
    summary="List overlays for a model"
)
def list_model_overlays(
    model_id: int,
    include_retired: bool = Query(False, description="Include retired overlays"),
    overlay_kind: Optional[str] = Query(None, description="Filter by overlay kind"),
    region_id: Optional[int] = Query(None, description="Filter by region"),
    is_underperformance_related: Optional[bool] = Query(None, description="Filter by underperformance flag"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _get_model_or_404(db, model_id, current_user)

    query = db.query(ModelOverlay).options(
        joinedload(ModelOverlay.region)
    ).filter(ModelOverlay.model_id == model_id)

    if not include_retired:
        query = query.filter(ModelOverlay.is_retired == False)

    if overlay_kind:
        query = query.filter(ModelOverlay.overlay_kind == overlay_kind)

    if region_id:
        query = query.filter(ModelOverlay.region_id == region_id)

    if is_underperformance_related is not None:
        query = query.filter(ModelOverlay.is_underperformance_related == is_underperformance_related)

    overlays = query.order_by(ModelOverlay.created_at.desc()).all()
    return overlays


@router.post(
    "/models/{model_id}/overlays",
    response_model=ModelOverlayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an overlay for a model"
)
def create_model_overlay(
    model_id: int,
    payload: ModelOverlayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator)
):
    _get_model_or_404(db, model_id, current_user)

    if payload.region_id:
        _validate_region(db, payload.region_id)
    if payload.trigger_monitoring_result_id:
        _validate_monitoring_result(db, model_id, payload.trigger_monitoring_result_id)
    if payload.trigger_monitoring_cycle_id:
        _validate_monitoring_cycle(db, model_id, payload.trigger_monitoring_cycle_id)
    if payload.related_limitation_id:
        _validate_limitation(db, model_id, payload.related_limitation_id)
    if payload.related_recommendation_id:
        _validate_recommendation(db, model_id, payload.related_recommendation_id)

    overlay = ModelOverlay(
        model_id=model_id,
        overlay_kind=payload.overlay_kind,
        is_underperformance_related=payload.is_underperformance_related,
        description=payload.description,
        rationale=payload.rationale,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        region_id=payload.region_id,
        trigger_monitoring_result_id=payload.trigger_monitoring_result_id,
        trigger_monitoring_cycle_id=payload.trigger_monitoring_cycle_id,
        related_recommendation_id=payload.related_recommendation_id,
        related_limitation_id=payload.related_limitation_id,
        evidence_description=payload.evidence_description,
        is_retired=False,
        created_by_id=current_user.user_id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(overlay)
    db.flush()

    _log_audit(
        db,
        entity_id=overlay.overlay_id,
        action="CREATE",
        user_id=current_user.user_id,
        new_values={
            "model_id": model_id,
            "overlay_kind": payload.overlay_kind,
            "is_underperformance_related": payload.is_underperformance_related,
            "effective_from": str(payload.effective_from),
            "effective_to": str(payload.effective_to) if payload.effective_to else None,
        }
    )

    db.commit()
    return _get_overlay_with_relations(db, overlay.overlay_id)


@router.get(
    "/overlays/{overlay_id}",
    response_model=ModelOverlayResponse,
    summary="Get overlay details"
)
def get_model_overlay(
    overlay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    overlay = _get_overlay_with_relations(db, overlay_id)
    if not can_access_model(overlay.model_id, current_user, db):
        raise HTTPException(status_code=404, detail="Overlay not found")
    return overlay


@router.patch(
    "/overlays/{overlay_id}",
    response_model=ModelOverlayResponse,
    summary="Update overlay evidence/link fields"
)
def update_model_overlay(
    overlay_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator)
):
    overlay = db.query(ModelOverlay).filter(
        ModelOverlay.overlay_id == overlay_id
    ).first()
    if not overlay:
        raise HTTPException(status_code=404, detail="Overlay not found")

    if overlay.is_retired:
        raise HTTPException(status_code=400, detail="Cannot update a retired overlay")

    allowed_fields = {
        "evidence_description",
        "trigger_monitoring_result_id",
        "trigger_monitoring_cycle_id",
        "related_recommendation_id",
        "related_limitation_id",
    }
    invalid_fields = set(payload.keys()) - allowed_fields
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail="Immutable fields cannot be updated. Retire the overlay and create a new one."
        )

    data = ModelOverlayUpdate(**payload)
    old_values: dict = {}
    new_values: dict = {}

    if "evidence_description" in payload:
        old_values["evidence_description"] = overlay.evidence_description
        overlay.evidence_description = data.evidence_description
        new_values["evidence_description"] = data.evidence_description

    if "trigger_monitoring_result_id" in payload:
        if data.trigger_monitoring_result_id is not None:
            _validate_monitoring_result(db, overlay.model_id, data.trigger_monitoring_result_id)
        old_values["trigger_monitoring_result_id"] = overlay.trigger_monitoring_result_id
        overlay.trigger_monitoring_result_id = data.trigger_monitoring_result_id
        new_values["trigger_monitoring_result_id"] = data.trigger_monitoring_result_id

    if "trigger_monitoring_cycle_id" in payload:
        if data.trigger_monitoring_cycle_id is not None:
            _validate_monitoring_cycle(db, overlay.model_id, data.trigger_monitoring_cycle_id)
        old_values["trigger_monitoring_cycle_id"] = overlay.trigger_monitoring_cycle_id
        overlay.trigger_monitoring_cycle_id = data.trigger_monitoring_cycle_id
        new_values["trigger_monitoring_cycle_id"] = data.trigger_monitoring_cycle_id

    if "related_recommendation_id" in payload:
        if data.related_recommendation_id is not None:
            _validate_recommendation(db, overlay.model_id, data.related_recommendation_id)
        old_values["related_recommendation_id"] = overlay.related_recommendation_id
        overlay.related_recommendation_id = data.related_recommendation_id
        new_values["related_recommendation_id"] = data.related_recommendation_id

    if "related_limitation_id" in payload:
        if data.related_limitation_id is not None:
            _validate_limitation(db, overlay.model_id, data.related_limitation_id)
        old_values["related_limitation_id"] = overlay.related_limitation_id
        overlay.related_limitation_id = data.related_limitation_id
        new_values["related_limitation_id"] = data.related_limitation_id

    overlay.updated_at = utc_now()

    if new_values:
        _log_audit(
            db,
            entity_id=overlay.overlay_id,
            action="UPDATE",
            user_id=current_user.user_id,
            old_values=old_values,
            new_values=new_values
        )

    db.commit()
    return _get_overlay_with_relations(db, overlay.overlay_id)


@router.post(
    "/overlays/{overlay_id}/retire",
    response_model=ModelOverlayResponse,
    summary="Retire an overlay"
)
def retire_model_overlay(
    overlay_id: int,
    payload: ModelOverlayRetire,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_validator)
):
    overlay = db.query(ModelOverlay).filter(
        ModelOverlay.overlay_id == overlay_id
    ).first()
    if not overlay:
        raise HTTPException(status_code=404, detail="Overlay not found")

    if overlay.is_retired:
        raise HTTPException(status_code=400, detail="Overlay is already retired")

    overlay.is_retired = True
    overlay.retirement_date = utc_now()
    overlay.retirement_reason = payload.retirement_reason
    overlay.retired_by_id = current_user.user_id
    overlay.updated_at = utc_now()

    _log_audit(
        db,
        entity_id=overlay.overlay_id,
        action="RETIRE",
        user_id=current_user.user_id,
        new_values={"retirement_reason": payload.retirement_reason}
    )

    db.commit()
    return _get_overlay_with_relations(db, overlay.overlay_id)


@router.get(
    "/reports/model-overlays",
    response_model=ModelOverlaysReportResponse,
    summary="Model overlays report"
)
def get_model_overlays_report(
    region_id: Optional[int] = Query(None, description="Filter by overlay region"),
    team_id: Optional[int] = Query(None, description="Filter by team ID (0 = Unassigned)"),
    risk_tier: Optional[str] = Query(None, description="Filter by risk tier code or value ID"),
    overlay_kind: Optional[str] = Query(None, description="Filter by overlay kind"),
    include_pending_decommission: bool = Query(False, description="Include Pending Decommission models"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = utc_now().date()
    statuses = [ModelStatus.ACTIVE.value]
    if include_pending_decommission:
        statuses.append(ModelStatus.PENDING_DECOMMISSION.value)

    query = db.query(ModelOverlay).options(
        joinedload(ModelOverlay.model).joinedload(Model.risk_tier),
        joinedload(ModelOverlay.region),
    ).join(Model, ModelOverlay.model_id == Model.model_id).filter(
        ModelOverlay.is_underperformance_related == True,
        ModelOverlay.is_retired == False,
        ModelOverlay.effective_from <= today,
        or_(ModelOverlay.effective_to == None, ModelOverlay.effective_to >= today),
        Model.status.in_(statuses)
    )

    if overlay_kind:
        query = query.filter(ModelOverlay.overlay_kind == overlay_kind)

    if region_id:
        region = db.query(Region).filter(Region.region_id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")
        query = query.filter(ModelOverlay.region_id == region_id)

    if risk_tier:
        if risk_tier.isdigit():
            query = query.filter(Model.risk_tier_id == int(risk_tier))
        else:
            query = query.join(
                TaxonomyValue, Model.risk_tier_id == TaxonomyValue.value_id
            ).filter(TaxonomyValue.code == risk_tier)

    overlays = query.order_by(Model.model_name, ModelOverlay.effective_from.desc()).all()

    team_map = get_models_team_map(db, list({o.model_id for o in overlays}))
    team_filter_name: Optional[str] = None
    if team_id is not None:
        if team_id == 0:
            overlays = [o for o in overlays if team_map.get(o.model_id) is None]
            team_filter_name = "Unassigned"
        else:
            overlays = [
                o for o in overlays
                if (team_entry := team_map.get(o.model_id))
                and team_entry.get("team_id") == team_id
            ]
            team = db.query(Team).filter(Team.team_id == team_id).first()
            team_filter_name = team.name if team else f"Team {team_id}"

    items = []
    for overlay in overlays:
        risk_tier_label = overlay.model.risk_tier.label if overlay.model and overlay.model.risk_tier else None
        risk_tier_code = overlay.model.risk_tier.code if overlay.model and overlay.model.risk_tier else None
        team_entry = team_map.get(overlay.model_id)
        items.append(ModelOverlayReportItem(
            overlay_id=overlay.overlay_id,
            model_id=overlay.model_id,
            model_name=overlay.model.model_name if overlay.model else "Unknown",
            model_status=overlay.model.status if overlay.model else "Unknown",
            risk_tier=risk_tier_label,
            risk_tier_code=risk_tier_code,
            team_name=team_entry.get("name") if team_entry else None,
            overlay_kind=overlay.overlay_kind,
            is_underperformance_related=overlay.is_underperformance_related,
            description=overlay.description,
            rationale=overlay.rationale,
            effective_from=overlay.effective_from,
            effective_to=overlay.effective_to,
            region_name=overlay.region.name if overlay.region else None,
            region_code=overlay.region.code if overlay.region else None,
            evidence_description=overlay.evidence_description,
            trigger_monitoring_result_id=overlay.trigger_monitoring_result_id,
            trigger_monitoring_cycle_id=overlay.trigger_monitoring_cycle_id,
            related_recommendation_id=overlay.related_recommendation_id,
            related_limitation_id=overlay.related_limitation_id,
            has_monitoring_traceability=bool(
                overlay.trigger_monitoring_result_id or overlay.trigger_monitoring_cycle_id
            ),
            created_at=overlay.created_at,
        ))

    filters_applied = {
        "region_id": region_id,
        "team_id": team_id,
        "team_name": team_filter_name,
        "risk_tier": risk_tier,
        "overlay_kind": overlay_kind,
        "include_pending_decommission": include_pending_decommission,
    }

    return ModelOverlaysReportResponse(
        filters_applied=filters_applied,
        total_count=len(items),
        items=items
    )

"""Audit logs routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse

# Import models for entity label lookups
from app.models.model import Model
from app.models.vendor import Vendor
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.region import Region
from app.models.validation import (
    ValidationRequest, ValidationPolicy, ValidationPlan,
    ValidationAssignment, ValidationOutcome, ValidationApproval,
    ValidationReviewOutcome, ValidationComponentDefinition
)
from app.models.monitoring import (
    MonitoringTeam, MonitoringPlan, MonitoringPlanMetric,
    MonitoringCycle, MonitoringResult, MonitoringCycleApproval,
    MonitoringPlanVersion
)
from app.models.recommendation import Recommendation
from app.models.attestation import (
    AttestationCycle, AttestationRecord, AttestationEvidence,
    AttestationSchedulingRule, AttestationQuestionConfig
)
from app.models.model_version import ModelVersion
from app.models.decommissioning import DecommissioningRequest
from app.models.model_hierarchy import ModelHierarchy
from app.models.model_feed_dependency import ModelFeedDependency
from app.models.lob import LOBUnit
from app.models.irp import IRP
from app.models.limitation import ModelLimitation
from app.models.model_overlay import ModelOverlay
from app.models.risk_assessment import QualitativeRiskFactor, QualitativeFactorGuidance
from app.models.scorecard import ScorecardSection, ScorecardCriterion, ScorecardConfigVersion
from app.models.model_change_taxonomy import ModelChangeType
from app.models.model_type_taxonomy import ModelType
from app.models.methodology import MethodologyCategory, Methodology
from app.models.model_delegate import ModelDelegate
from app.models.residual_risk_map import ResidualRiskMapConfig
from app.models.model_exception import ModelException


class EntityOption(BaseModel):
    """Entity option for dropdown selection."""
    entity_id: int
    label: str

router = APIRouter()


@router.get("/", response_model=List[AuditLogResponse])
def list_audit_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g., Model, Vendor)"),
    entity_id: Optional[int] = Query(None, description="Filter by specific entity ID"),
    action: Optional[str] = Query(None, description="Filter by action (CREATE, UPDATE, DELETE)"),
    user_id: Optional[int] = Query(None, description="Filter by user who made the change"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List audit logs with optional filters."""
    query = db.query(AuditLog).options(joinedload(AuditLog.user))

    # Apply filters
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)

    # Order by most recent first, then apply pagination
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return logs


@router.get("/entity-types", response_model=List[str])
def get_entity_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all unique entity types from audit logs."""
    result = db.query(AuditLog.entity_type).distinct().all()
    return [r[0] for r in result]


@router.get("/actions", response_model=List[str])
def get_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all unique actions from audit logs."""
    result = db.query(AuditLog.action).distinct().all()
    return [r[0] for r in result]


# Mapping of entity_type to (model_class, primary_key_field, label_field_or_callable)
# For complex labels, we use a callable that takes the entity and returns a string
def _get_entity_config():
    """Return configuration for entity type -> model mapping."""
    return {
        "Model": (Model, "model_id", lambda e: e.model_name),
        "Vendor": (Vendor, "vendor_id", lambda e: e.vendor_name),
        "User": (User, "user_id", lambda e: e.full_name or e.email),
        "Taxonomy": (Taxonomy, "taxonomy_id", lambda e: e.name),
        "TaxonomyValue": (TaxonomyValue, "value_id", lambda e: f"{e.label} ({e.code})"),
        "Region": (Region, "region_id", lambda e: e.region_name),
        "ValidationRequest": (ValidationRequest, "request_id", lambda e: f"VR-{e.request_id}"),
        "ValidationPolicy": (ValidationPolicy, "policy_id", lambda e: f"Policy {e.policy_id}"),
        "ValidationPlan": (ValidationPlan, "plan_id", lambda e: f"Plan {e.plan_id}"),
        "ValidationAssignment": (ValidationAssignment, "assignment_id", lambda e: f"Assignment {e.assignment_id}"),
        "ValidationOutcome": (ValidationOutcome, "outcome_id", lambda e: f"Outcome {e.outcome_id}"),
        "ValidationApproval": (ValidationApproval, "approval_id", lambda e: f"Approval {e.approval_id}"),
        "ValidationReviewOutcome": (ValidationReviewOutcome, "review_outcome_id", lambda e: f"Review {e.review_outcome_id}"),
        "ValidationComponentDefinition": (ValidationComponentDefinition, "component_id", lambda e: e.component_name),
        "MonitoringTeam": (MonitoringTeam, "team_id", lambda e: e.team_name),
        "MonitoringPlan": (MonitoringPlan, "plan_id", lambda e: e.plan_name),
        "MonitoringPlanMetric": (MonitoringPlanMetric, "metric_id", lambda e: e.metric_name),
        "MonitoringPlanVersion": (MonitoringPlanVersion, "version_id", lambda e: f"Version {e.version_id}"),
        "MonitoringCycle": (MonitoringCycle, "cycle_id", lambda e: f"Cycle {e.cycle_id}"),
        "MonitoringResult": (MonitoringResult, "result_id", lambda e: f"Result {e.result_id}"),
        "MonitoringCycleApproval": (MonitoringCycleApproval, "approval_id", lambda e: f"Approval {e.approval_id}"),
        "Recommendation": (Recommendation, "recommendation_id", lambda e: e.recommendation_number or f"Rec {e.recommendation_id}"),
        "AttestationCycle": (AttestationCycle, "cycle_id", lambda e: e.cycle_name),
        "AttestationRecord": (AttestationRecord, "record_id", lambda e: f"Record {e.record_id}"),
        "AttestationEvidence": (AttestationEvidence, "evidence_id", lambda e: f"Evidence {e.evidence_id}"),
        "AttestationSchedulingRule": (AttestationSchedulingRule, "rule_id", lambda e: f"Rule {e.rule_id}"),
        "AttestationQuestion": (AttestationQuestionConfig, "question_id", lambda e: e.question_text[:50] if e.question_text else f"Q{e.question_id}"),
        "ModelVersion": (ModelVersion, "version_id", lambda e: e.version_name or f"v{e.version_number}"),
        "DecommissioningRequest": (DecommissioningRequest, "request_id", lambda e: f"Decom {e.request_id}"),
        "ModelHierarchy": (ModelHierarchy, "hierarchy_id", lambda e: f"Hierarchy {e.hierarchy_id}"),
        "ModelFeedDependency": (ModelFeedDependency, "dependency_id", lambda e: f"Dependency {e.dependency_id}"),
        "LOBUnit": (LOBUnit, "lob_id", lambda e: e.lob_name),
        "IRP": (IRP, "irp_id", lambda e: e.irp_name),
        "ModelLimitation": (ModelLimitation, "limitation_id", lambda e: e.title or f"Limitation {e.limitation_id}"),
        "QualitativeRiskFactor": (QualitativeRiskFactor, "factor_id", lambda e: e.factor_name),
        "QualitativeFactorGuidance": (QualitativeFactorGuidance, "guidance_id", lambda e: f"Guidance {e.guidance_id}"),
        "ScorecardSection": (ScorecardSection, "section_id", lambda e: e.section_name),
        "ScorecardCriterion": (ScorecardCriterion, "criterion_id", lambda e: e.criterion_name),
        "ScorecardConfigVersion": (ScorecardConfigVersion, "version_id", lambda e: e.version_name),
        "ModelChangeType": (ModelChangeType, "type_id", lambda e: e.type_name),
        "ModelType": (ModelType, "type_id", lambda e: e.type_name),
        "MethodologyCategory": (MethodologyCategory, "category_id", lambda e: e.category_name),
        "Methodology": (Methodology, "methodology_id", lambda e: e.methodology_name),
        "ModelDelegate": (ModelDelegate, "delegation_id", lambda e: f"Delegation {e.delegation_id}"),
        "ResidualRiskMapConfig": (ResidualRiskMapConfig, "config_id", lambda e: f"Config {e.config_id}"),
        "ModelException": (ModelException, "exception_id", lambda e: e.title or f"Exception {e.exception_id}"),
        "ModelOverlay": (ModelOverlay, "overlay_id", lambda e: (e.description[:50] + "...") if e.description and len(e.description) > 50 else (e.description or f"Overlay {e.overlay_id}")),
    }


@router.get("/entities", response_model=List[EntityOption])
def get_entities_by_type(
    entity_type: str = Query(..., description="Entity type to get entities for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get unique entities (ID + label) for a given entity type from audit logs.

    This endpoint returns all entities of a specific type that have audit log entries,
    allowing users to filter audit logs by selecting an entity from a dropdown
    instead of typing an ID.
    """
    # Get unique entity IDs for this type from audit logs
    entity_ids = db.query(AuditLog.entity_id).filter(
        AuditLog.entity_type == entity_type
    ).distinct().all()
    entity_ids = [r[0] for r in entity_ids]

    if not entity_ids:
        return []

    # Get entity config
    config = _get_entity_config()

    if entity_type not in config:
        # Fallback: return IDs only as labels
        return [EntityOption(entity_id=eid, label=f"{entity_type} #{eid}") for eid in sorted(entity_ids)]

    model_class, pk_field, label_fn = config[entity_type]

    # Query the actual entities to get their labels
    pk_column = getattr(model_class, pk_field)
    entities = db.query(model_class).filter(pk_column.in_(entity_ids)).all()

    # Build result with labels
    result = []
    found_ids = set()

    for entity in entities:
        entity_id = getattr(entity, pk_field)
        found_ids.add(entity_id)
        try:
            label = label_fn(entity)
        except Exception:
            label = f"{entity_type} #{entity_id}"
        result.append(EntityOption(entity_id=entity_id, label=label))

    # Add any IDs that weren't found in the current table (deleted entities)
    for eid in entity_ids:
        if eid not in found_ids:
            result.append(EntityOption(entity_id=eid, label=f"{entity_type} #{eid} (deleted)"))

    # Sort by label
    result.sort(key=lambda x: x.label.lower())

    return result

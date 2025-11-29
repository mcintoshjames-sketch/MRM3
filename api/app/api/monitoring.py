"""Monitoring Plans and Teams routes."""
from typing import List, Optional
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.model import Model
from app.models.kpm import Kpm
from app.models.audit_log import AuditLog
from app.models.region import Region
from app.models.taxonomy import TaxonomyValue
from app.models.monitoring import (
    MonitoringTeam,
    MonitoringPlan,
    MonitoringPlanMetric,
    MonitoringPlanVersion,
    MonitoringPlanMetricSnapshot,
    MonitoringPlanModelSnapshot,
    MonitoringFrequency,
    monitoring_team_members,
    monitoring_plan_models,
)
from app.schemas.monitoring import (
    MonitoringTeamCreate,
    MonitoringTeamUpdate,
    MonitoringTeamResponse,
    MonitoringTeamListResponse,
    MonitoringPlanCreate,
    MonitoringPlanUpdate,
    MonitoringPlanResponse,
    MonitoringPlanListResponse,
    MonitoringPlanMetricCreate,
    MonitoringPlanMetricUpdate,
    MonitoringPlanMetricResponse,
    # Version schemas
    PublishVersionRequest,
    MonitoringPlanVersionResponse,
    MonitoringPlanVersionDetailResponse,
    MonitoringPlanVersionListResponse,
    MetricSnapshotResponse,
    ActiveCyclesWarning,
    # Component 9b lookup
    ModelMonitoringPlanResponse,
    # Phase 7: Reporting & Trends
    MetricTrendPoint,
    MetricTrendResponse,
    PerformanceSummary,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for monitoring changes."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def check_plan_edit_permission(db: Session, plan_id: int, current_user: User) -> MonitoringPlan:
    """Check if user can edit a monitoring plan.

    Returns the plan if user has permission, raises HTTPException otherwise.

    Permission is granted if:
    - User is an Admin, OR
    - User is a member of the monitoring team assigned to the plan
    """
    plan = db.query(MonitoringPlan).options(
        joinedload(MonitoringPlan.team).joinedload(MonitoringTeam.members)
    ).filter(MonitoringPlan.plan_id == plan_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

    # Admins always have permission
    if current_user.role == UserRole.ADMIN:
        return plan

    # Check if user is a member of the plan's monitoring team
    if plan.team:
        member_ids = [m.user_id for m in plan.team.members]
        if current_user.user_id in member_ids:
            return plan

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You must be an Admin or a member of the assigned monitoring team to edit this plan"
    )


def validate_metric_thresholds(
    yellow_min: Optional[float],
    yellow_max: Optional[float],
    red_min: Optional[float],
    red_max: Optional[float]
) -> None:
    """Validate that metric thresholds are logically consistent.

    Rules:
    - If both yellow_max and red_max are set, red_max must be > yellow_max
      (otherwise the yellow_max threshold becomes unreachable)
    - If both yellow_min and red_min are set, red_min must be < yellow_min
      (otherwise the yellow_min threshold becomes unreachable)

    Raises HTTPException with 400 status if validation fails.
    """
    if yellow_max is not None and red_max is not None:
        if red_max <= yellow_max:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid threshold configuration: red_max ({red_max}) must be greater than yellow_max ({yellow_max}). "
                       f"Otherwise yellow_max threshold becomes unreachable."
            )

    if yellow_min is not None and red_min is not None:
        if red_min >= yellow_min:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid threshold configuration: red_min ({red_min}) must be less than yellow_min ({yellow_min}). "
                       f"Otherwise yellow_min threshold becomes unreachable."
            )


def calculate_next_submission_date(frequency: MonitoringFrequency, from_date: date = None) -> date:
    """Calculate the next submission due date based on frequency."""
    if from_date is None:
        from_date = date.today()

    if frequency == MonitoringFrequency.MONTHLY:
        return from_date + relativedelta(months=1)
    elif frequency == MonitoringFrequency.QUARTERLY:
        return from_date + relativedelta(months=3)
    elif frequency == MonitoringFrequency.SEMI_ANNUAL:
        return from_date + relativedelta(months=6)
    elif frequency == MonitoringFrequency.ANNUAL:
        return from_date + relativedelta(years=1)
    else:
        return from_date + relativedelta(months=3)  # Default to quarterly


def calculate_report_due_date(submission_date: date, lead_days: int) -> date:
    """Calculate the report due date from submission date and lead days."""
    return submission_date + timedelta(days=lead_days)


# ============================================================================
# MONITORING TEAMS ENDPOINTS
# ============================================================================

@router.get("/monitoring/teams", response_model=List[MonitoringTeamListResponse])
def list_monitoring_teams(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all monitoring teams with member and plan counts."""
    query = db.query(MonitoringTeam)

    if not include_inactive:
        query = query.filter(MonitoringTeam.is_active == True)

    teams = query.order_by(MonitoringTeam.name).all()

    result = []
    for team in teams:
        result.append({
            "team_id": team.team_id,
            "name": team.name,
            "description": team.description,
            "is_active": team.is_active,
            "member_count": len(team.members),
            "plan_count": len([p for p in team.plans if p.is_active])
        })

    return result


@router.get("/monitoring/teams/{team_id}", response_model=MonitoringTeamResponse)
def get_monitoring_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific monitoring team with members."""
    team = db.query(MonitoringTeam).options(
        joinedload(MonitoringTeam.members)
    ).filter(MonitoringTeam.team_id == team_id).first()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    return team


@router.post("/monitoring/teams", response_model=MonitoringTeamResponse, status_code=status.HTTP_201_CREATED)
def create_monitoring_team(
    team_data: MonitoringTeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new monitoring team (Admin only)."""
    # Check for duplicate name
    existing = db.query(MonitoringTeam).filter(
        MonitoringTeam.name == team_data.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team with name '{team_data.name}' already exists"
        )

    # Create team
    team = MonitoringTeam(
        name=team_data.name,
        description=team_data.description,
        is_active=team_data.is_active
    )

    db.add(team)
    db.flush()

    # Add members
    if team_data.member_ids:
        members = db.query(User).filter(
            User.user_id.in_(team_data.member_ids)).all()
        team.members = members

    # Audit log
    create_audit_log(
        db=db,
        entity_type="MonitoringTeam",
        entity_id=team.team_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "name": team.name,
            "member_ids": team_data.member_ids or []
        }
    )

    db.commit()
    db.refresh(team)

    return team


@router.patch("/monitoring/teams/{team_id}", response_model=MonitoringTeamResponse)
def update_monitoring_team(
    team_id: int,
    update_data: MonitoringTeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a monitoring team (Admin only)."""
    team = db.query(MonitoringTeam).options(
        joinedload(MonitoringTeam.members)
    ).filter(MonitoringTeam.team_id == team_id).first()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Track changes for audit log
    changes = {}
    old_member_ids = [m.user_id for m in team.members]

    # Update fields
    if update_data.name is not None:
        # Check for duplicate name
        existing = db.query(MonitoringTeam).filter(
            MonitoringTeam.name == update_data.name,
            MonitoringTeam.team_id != team_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team with name '{update_data.name}' already exists"
            )
        if team.name != update_data.name:
            changes["name"] = {"old": team.name, "new": update_data.name}
        team.name = update_data.name

    if update_data.description is not None:
        if team.description != update_data.description:
            changes["description"] = {
                "old": team.description, "new": update_data.description}
        team.description = update_data.description

    if update_data.is_active is not None:
        if team.is_active != update_data.is_active:
            changes["is_active"] = {
                "old": team.is_active, "new": update_data.is_active}
        team.is_active = update_data.is_active

    if update_data.member_ids is not None:
        members = db.query(User).filter(
            User.user_id.in_(update_data.member_ids)).all()
        team.members = members
        if set(old_member_ids) != set(update_data.member_ids):
            changes["member_ids"] = {
                "old": old_member_ids, "new": update_data.member_ids}

    # Audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="MonitoringTeam",
            entity_id=team_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(team)

    return team


@router.delete("/monitoring/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitoring_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a monitoring team (Admin only)."""
    team = db.query(MonitoringTeam).filter(
        MonitoringTeam.team_id == team_id
    ).first()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Check if team has active plans
    active_plans = [p for p in team.plans if p.is_active]
    if active_plans:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete team with {len(active_plans)} active plans. Deactivate plans first."
        )

    # Audit log before deletion
    create_audit_log(
        db=db,
        entity_type="MonitoringTeam",
        entity_id=team_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"name": team.name}
    )

    db.delete(team)
    db.commit()

    return None


# ============================================================================
# MONITORING PLANS ENDPOINTS
# ============================================================================

@router.get("/monitoring/plans", response_model=List[MonitoringPlanListResponse])
def list_monitoring_plans(
    include_inactive: bool = False,
    model_id: Optional[int] = None,
    team_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all monitoring plans with summary info."""
    query = db.query(MonitoringPlan).options(
        joinedload(MonitoringPlan.team),
        joinedload(MonitoringPlan.data_provider),
        joinedload(MonitoringPlan.models),
        joinedload(MonitoringPlan.metrics),
        joinedload(MonitoringPlan.versions)
    )

    if not include_inactive:
        query = query.filter(MonitoringPlan.is_active == True)

    if team_id:
        query = query.filter(MonitoringPlan.monitoring_team_id == team_id)

    plans = query.order_by(MonitoringPlan.name).all()

    # Filter by model if specified
    if model_id:
        plans = [p for p in plans if any(
            m.model_id == model_id for m in p.models)]

    result = []
    for plan in plans:
        # Find active version
        active_version = next((v for v in plan.versions if v.is_active), None)
        result.append({
            "plan_id": plan.plan_id,
            "name": plan.name,
            "description": plan.description,
            "frequency": plan.frequency,
            "is_active": plan.is_active,
            "next_submission_due_date": plan.next_submission_due_date,
            "next_report_due_date": plan.next_report_due_date,
            "team_name": plan.team.name if plan.team else None,
            "data_provider_name": plan.data_provider.full_name if plan.data_provider else None,
            "model_count": len(plan.models),
            "metric_count": len([m for m in plan.metrics if m.is_active]),
            "version_count": len(plan.versions),
            "active_version_number": active_version.version_number if active_version else None
        })

    return result


@router.get("/monitoring/plans/{plan_id}", response_model=MonitoringPlanResponse)
def get_monitoring_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific monitoring plan with full details."""
    plan = db.query(MonitoringPlan).options(
        joinedload(MonitoringPlan.team).joinedload(MonitoringTeam.members),
        joinedload(MonitoringPlan.data_provider),
        joinedload(MonitoringPlan.models),
        joinedload(MonitoringPlan.metrics).joinedload(
            MonitoringPlanMetric.kpm).joinedload(Kpm.category)
    ).filter(MonitoringPlan.plan_id == plan_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

    # Query for active version
    active_version = db.query(MonitoringPlanVersion).filter(
        MonitoringPlanVersion.plan_id == plan_id,
        MonitoringPlanVersion.is_active == True
    ).first()

    # Build response with proper nested structure
    return {
        "plan_id": plan.plan_id,
        "name": plan.name,
        "description": plan.description,
        "frequency": plan.frequency,
        "monitoring_team_id": plan.monitoring_team_id,
        "data_provider_user_id": plan.data_provider_user_id,
        "reporting_lead_days": plan.reporting_lead_days,
        "next_submission_due_date": plan.next_submission_due_date,
        "next_report_due_date": plan.next_report_due_date,
        "is_active": plan.is_active,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
        "team": {
            "team_id": plan.team.team_id,
            "name": plan.team.name,
            "description": plan.team.description,
            "is_active": plan.team.is_active,
            "member_count": len(plan.team.members),
            "plan_count": len([p for p in plan.team.plans if p.is_active]),
            "members": [
                {
                    "user_id": m.user_id,
                    "email": m.email,
                    "full_name": m.full_name
                }
                for m in plan.team.members
            ]
        } if plan.team else None,
        # User permission indicators for frontend
        "user_permissions": {
            "is_admin": current_user.role == UserRole.ADMIN,
            "is_team_member": plan.team and current_user.user_id in [m.user_id for m in plan.team.members] if plan.team else False,
            "is_data_provider": plan.data_provider and plan.data_provider.user_id == current_user.user_id if plan.data_provider else False,
            "can_start_cycle": current_user.role == UserRole.ADMIN or (plan.team and current_user.user_id in [m.user_id for m in plan.team.members]),
            "can_submit_cycle": True,  # Anyone with view access can submit results
            "can_request_approval": current_user.role == UserRole.ADMIN or (plan.team and current_user.user_id in [m.user_id for m in plan.team.members]),
            "can_cancel_cycle": current_user.role == UserRole.ADMIN or (plan.team and current_user.user_id in [m.user_id for m in plan.team.members]),
        },
        "data_provider": {
            "user_id": plan.data_provider.user_id,
            "email": plan.data_provider.email,
            "full_name": plan.data_provider.full_name
        } if plan.data_provider else None,
        "models": [
            {"model_id": m.model_id, "model_name": m.model_name}
            for m in plan.models
        ],
        "metrics": [
            {
                "metric_id": metric.metric_id,
                "plan_id": metric.plan_id,
                "kpm_id": metric.kpm_id,
                "yellow_min": metric.yellow_min,
                "yellow_max": metric.yellow_max,
                "red_min": metric.red_min,
                "red_max": metric.red_max,
                "qualitative_guidance": metric.qualitative_guidance,
                "sort_order": metric.sort_order,
                "is_active": metric.is_active,
                "kpm": {
                    "kpm_id": metric.kpm.kpm_id,
                    "name": metric.kpm.name,
                    "category_id": metric.kpm.category_id,
                    "category_name": metric.kpm.category.name if metric.kpm.category else None,
                    "evaluation_type": metric.kpm.evaluation_type
                }
            }
            for metric in plan.metrics
        ],
        "active_version_number": active_version.version_number if active_version else None
    }


@router.post("/monitoring/plans", response_model=MonitoringPlanResponse, status_code=status.HTTP_201_CREATED)
def create_monitoring_plan(
    plan_data: MonitoringPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new monitoring plan (Admin only)."""
    # Validate team exists if specified
    if plan_data.monitoring_team_id:
        team = db.query(MonitoringTeam).filter(
            MonitoringTeam.team_id == plan_data.monitoring_team_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

    # Validate data provider exists if specified
    if plan_data.data_provider_user_id:
        user = db.query(User).filter(
            User.user_id == plan_data.data_provider_user_id
        ).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data provider user not found"
            )

    # Calculate due dates
    submission_date = plan_data.next_submission_due_date or calculate_next_submission_date(
        MonitoringFrequency(plan_data.frequency)
    )
    report_date = calculate_report_due_date(
        submission_date, plan_data.reporting_lead_days)

    # Create plan
    plan = MonitoringPlan(
        name=plan_data.name,
        description=plan_data.description,
        frequency=plan_data.frequency,
        monitoring_team_id=plan_data.monitoring_team_id,
        data_provider_user_id=plan_data.data_provider_user_id,
        reporting_lead_days=plan_data.reporting_lead_days,
        next_submission_due_date=submission_date,
        next_report_due_date=report_date,
        is_active=plan_data.is_active
    )

    db.add(plan)
    db.flush()

    # Add models (scope)
    if plan_data.model_ids:
        models = db.query(Model).filter(
            Model.model_id.in_(plan_data.model_ids)).all()
        plan.models = models

    # Add metrics
    for metric_data in plan_data.metrics:
        # Validate KPM exists
        kpm = db.query(Kpm).filter(Kpm.kpm_id == metric_data.kpm_id).first()
        if not kpm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"KPM with ID {metric_data.kpm_id} not found"
            )

        metric = MonitoringPlanMetric(
            plan_id=plan.plan_id,
            kpm_id=metric_data.kpm_id,
            yellow_min=metric_data.yellow_min,
            yellow_max=metric_data.yellow_max,
            red_min=metric_data.red_min,
            red_max=metric_data.red_max,
            qualitative_guidance=metric_data.qualitative_guidance,
            sort_order=metric_data.sort_order,
            is_active=metric_data.is_active
        )
        db.add(metric)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="MonitoringPlan",
        entity_id=plan.plan_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "name": plan.name,
            "frequency": plan.frequency,
            "model_ids": plan_data.model_ids or [],
            "metric_count": len(plan_data.metrics)
        }
    )

    db.commit()

    # Return full plan
    return get_monitoring_plan(plan.plan_id, db, current_user)


@router.patch("/monitoring/plans/{plan_id}", response_model=MonitoringPlanResponse)
def update_monitoring_plan(
    plan_id: int,
    update_data: MonitoringPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a monitoring plan (Admin or team member)."""
    # Check permission - raises 403 if not authorized
    check_plan_edit_permission(db, plan_id, current_user)

    # Reload plan with models for update operations
    plan = db.query(MonitoringPlan).options(
        joinedload(MonitoringPlan.models)
    ).filter(
        MonitoringPlan.plan_id == plan_id
    ).first()

    recalculate_dates = False

    # Track changes for audit log
    changes = {}
    old_model_ids = [m.model_id for m in plan.models]

    # Update fields
    if update_data.name is not None:
        if plan.name != update_data.name:
            changes["name"] = {"old": plan.name, "new": update_data.name}
        plan.name = update_data.name

    if update_data.description is not None:
        if plan.description != update_data.description:
            changes["description"] = {
                "old": plan.description, "new": update_data.description}
        plan.description = update_data.description

    if update_data.frequency is not None:
        if plan.frequency != update_data.frequency:
            changes["frequency"] = {
                "old": plan.frequency, "new": update_data.frequency}
        plan.frequency = update_data.frequency
        recalculate_dates = True

    if update_data.monitoring_team_id is not None:
        if update_data.monitoring_team_id != 0:
            team = db.query(MonitoringTeam).filter(
                MonitoringTeam.team_id == update_data.monitoring_team_id
            ).first()
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found"
                )
        new_team_id = update_data.monitoring_team_id if update_data.monitoring_team_id != 0 else None
        if plan.monitoring_team_id != new_team_id:
            changes["monitoring_team_id"] = {
                "old": plan.monitoring_team_id, "new": new_team_id}
        plan.monitoring_team_id = new_team_id

    if update_data.data_provider_user_id is not None:
        if update_data.data_provider_user_id != 0:
            user = db.query(User).filter(
                User.user_id == update_data.data_provider_user_id
            ).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Data provider user not found"
                )
        new_provider_id = update_data.data_provider_user_id if update_data.data_provider_user_id != 0 else None
        if plan.data_provider_user_id != new_provider_id:
            changes["data_provider_user_id"] = {
                "old": plan.data_provider_user_id, "new": new_provider_id}
        plan.data_provider_user_id = new_provider_id

    if update_data.reporting_lead_days is not None:
        if plan.reporting_lead_days != update_data.reporting_lead_days:
            changes["reporting_lead_days"] = {
                "old": plan.reporting_lead_days, "new": update_data.reporting_lead_days}
        plan.reporting_lead_days = update_data.reporting_lead_days
        recalculate_dates = True

    if update_data.next_submission_due_date is not None:
        old_date = str(
            plan.next_submission_due_date) if plan.next_submission_due_date else None
        new_date = str(update_data.next_submission_due_date)
        if old_date != new_date:
            changes["next_submission_due_date"] = {
                "old": old_date, "new": new_date}
        plan.next_submission_due_date = update_data.next_submission_due_date
        plan.next_report_due_date = calculate_report_due_date(
            update_data.next_submission_due_date, plan.reporting_lead_days
        )
        recalculate_dates = False  # Dates manually set

    if update_data.is_active is not None:
        if plan.is_active != update_data.is_active:
            changes["is_active"] = {
                "old": plan.is_active, "new": update_data.is_active}
        plan.is_active = update_data.is_active

    if update_data.model_ids is not None:
        models = db.query(Model).filter(
            Model.model_id.in_(update_data.model_ids)).all()
        plan.models = models
        if set(old_model_ids) != set(update_data.model_ids):
            changes["model_ids"] = {
                "old": old_model_ids, "new": update_data.model_ids}

    # Recalculate dates if frequency or lead days changed
    if recalculate_dates and plan.next_submission_due_date:
        plan.next_report_due_date = calculate_report_due_date(
            plan.next_submission_due_date, plan.reporting_lead_days
        )

    # Audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="MonitoringPlan",
            entity_id=plan_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()

    # Return full plan
    return get_monitoring_plan(plan_id, db, current_user)


@router.delete("/monitoring/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitoring_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a monitoring plan (Admin or team member)."""
    # Check permission - raises 403 if not authorized
    plan = check_plan_edit_permission(db, plan_id, current_user)

    # Audit log before deletion
    create_audit_log(
        db=db,
        entity_type="MonitoringPlan",
        entity_id=plan_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"name": plan.name}
    )

    db.delete(plan)
    db.commit()

    return None


# ============================================================================
# MODEL → MONITORING PLANS LOOKUP (Component 9b)
# ============================================================================

@router.get("/models/{model_id}/monitoring-plans", response_model=List[ModelMonitoringPlanResponse])
def get_model_monitoring_plans(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get monitoring plans covering this model.
    Used for component 9b version selection in validation workflow.

    Returns plans that include this model, along with their versions and latest cycle info.
    """
    # Import MonitoringCycle locally to avoid circular imports
    from app.models.monitoring import MonitoringCycle, MonitoringCycleStatus

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Find monitoring plans that include this model
    plans = db.query(MonitoringPlan).options(
        joinedload(MonitoringPlan.versions).joinedload(
            MonitoringPlanVersion.published_by),
        joinedload(MonitoringPlan.versions).joinedload(
            MonitoringPlanVersion.metric_snapshots),
    ).filter(
        MonitoringPlan.models.any(Model.model_id == model_id),
        MonitoringPlan.is_active == True
    ).all()

    result = []
    for plan in plans:
        # Find active version
        active_version = None
        all_versions = []

        for v in sorted(plan.versions, key=lambda x: x.version_number, reverse=True):
            version_data = {
                "version_id": v.version_id,
                "plan_id": v.plan_id,
                "version_number": v.version_number,
                "version_name": v.version_name,
                "description": v.description,
                "effective_date": v.effective_date,
                "published_by": {
                    "user_id": v.published_by.user_id,
                    "email": v.published_by.email,
                    "full_name": v.published_by.full_name
                } if v.published_by else None,
                "published_at": v.published_at,
                "is_active": v.is_active,
                "metrics_count": len(v.metric_snapshots),
                "cycles_count": len(v.cycles) if hasattr(v, 'cycles') else 0
            }
            all_versions.append(version_data)
            if v.is_active:
                active_version = version_data

        # Get latest approved cycle for this plan
        latest_cycle = db.query(MonitoringCycle).filter(
            MonitoringCycle.plan_id == plan.plan_id,
            MonitoringCycle.status == MonitoringCycleStatus.APPROVED.value
        ).order_by(MonitoringCycle.period_end_date.desc()).first()

        # Build outcome summary from latest cycle results
        latest_cycle_outcome_summary = None
        if latest_cycle:
            # Import MonitoringResult locally
            from app.models.monitoring import MonitoringResult
            results = db.query(MonitoringResult).filter(
                MonitoringResult.cycle_id == latest_cycle.cycle_id
            ).all()

            if results:
                green_count = sum(
                    1 for r in results if r.calculated_outcome == "GREEN")
                yellow_count = sum(
                    1 for r in results if r.calculated_outcome == "YELLOW")
                red_count = sum(
                    1 for r in results if r.calculated_outcome == "RED")
                latest_cycle_outcome_summary = f"{green_count} Green, {yellow_count} Yellow, {red_count} Red"

        result.append({
            "plan_id": plan.plan_id,
            "plan_name": plan.name,
            "frequency": plan.frequency,
            "active_version": active_version,
            "all_versions": all_versions,
            "latest_cycle_status": latest_cycle.status if latest_cycle else None,
            "latest_cycle_outcome_summary": latest_cycle_outcome_summary
        })

    return result


# ============================================================================
# MONITORING PLAN VERSION ENDPOINTS
# ============================================================================

@router.get("/monitoring/plans/{plan_id}/versions", response_model=List[MonitoringPlanVersionListResponse])
def list_plan_versions(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all versions for a monitoring plan."""
    # Verify plan exists
    plan = db.query(MonitoringPlan).filter(
        MonitoringPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

    versions = db.query(MonitoringPlanVersion).options(
        joinedload(MonitoringPlanVersion.published_by),
        joinedload(MonitoringPlanVersion.metric_snapshots),
        joinedload(MonitoringPlanVersion.model_snapshots),
        joinedload(MonitoringPlanVersion.cycles)
    ).filter(
        MonitoringPlanVersion.plan_id == plan_id
    ).order_by(MonitoringPlanVersion.version_number.desc()).all()

    result = []
    for v in versions:
        result.append({
            "version_id": v.version_id,
            "version_number": v.version_number,
            "version_name": v.version_name,
            "effective_date": v.effective_date,
            "published_by_name": v.published_by.full_name if v.published_by else None,
            "published_at": v.published_at,
            "is_active": v.is_active,
            "metrics_count": len(v.metric_snapshots),
            "models_count": len(v.model_snapshots),
            "cycles_count": len(v.cycles)
        })

    return result


@router.get("/monitoring/plans/{plan_id}/versions/{version_id}", response_model=MonitoringPlanVersionDetailResponse)
def get_plan_version(
    plan_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific version with its metric and model snapshots."""
    version = db.query(MonitoringPlanVersion).options(
        joinedload(MonitoringPlanVersion.published_by),
        joinedload(MonitoringPlanVersion.metric_snapshots),
        joinedload(MonitoringPlanVersion.model_snapshots),
        joinedload(MonitoringPlanVersion.cycles)
    ).filter(
        MonitoringPlanVersion.version_id == version_id,
        MonitoringPlanVersion.plan_id == plan_id
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    return {
        "version_id": version.version_id,
        "plan_id": version.plan_id,
        "version_number": version.version_number,
        "version_name": version.version_name,
        "description": version.description,
        "effective_date": version.effective_date,
        "published_by": {
            "user_id": version.published_by.user_id,
            "email": version.published_by.email,
            "full_name": version.published_by.full_name
        } if version.published_by else None,
        "published_at": version.published_at,
        "is_active": version.is_active,
        "metrics_count": len(version.metric_snapshots),
        "models_count": len(version.model_snapshots),
        "cycles_count": len(version.cycles),
        "metric_snapshots": [
            {
                "snapshot_id": s.snapshot_id,
                # FK to MonitoringPlanMetric for result submission
                "original_metric_id": s.original_metric_id,
                "kpm_id": s.kpm_id,
                "kpm_name": s.kpm_name,
                "kpm_category_name": s.kpm_category_name,
                "evaluation_type": s.evaluation_type,
                "yellow_min": s.yellow_min,
                "yellow_max": s.yellow_max,
                "red_min": s.red_min,
                "red_max": s.red_max,
                "qualitative_guidance": s.qualitative_guidance,
                "sort_order": s.sort_order
            }
            for s in sorted(version.metric_snapshots, key=lambda x: x.sort_order)
        ],
        "model_snapshots": [
            {
                "snapshot_id": m.snapshot_id,
                "model_id": m.model_id,
                "model_name": m.model_name
            }
            for m in version.model_snapshots
        ]
    }


@router.post("/monitoring/plans/{plan_id}/versions/publish", response_model=MonitoringPlanVersionResponse, status_code=status.HTTP_201_CREATED)
def publish_plan_version(
    plan_id: int,
    payload: PublishVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Publish a new version of the monitoring plan (Admin or Team Member).

    Snapshots all current active metrics with their thresholds.
    """
    # Check plan edit permission (Admin or Team Member)
    plan = check_plan_edit_permission(db, plan_id, current_user)

    # Reload with metrics and models
    plan = db.query(MonitoringPlan).options(
        joinedload(MonitoringPlan.metrics).joinedload(
            MonitoringPlanMetric.kpm),
        joinedload(MonitoringPlan.models)
    ).filter(MonitoringPlan.plan_id == plan_id).first()

    # Get next version number
    max_version = db.query(func.max(MonitoringPlanVersion.version_number)).filter(
        MonitoringPlanVersion.plan_id == plan_id
    ).scalar() or 0

    new_version_number = max_version + 1

    # Deactivate previous active version
    db.query(MonitoringPlanVersion).filter(
        MonitoringPlanVersion.plan_id == plan_id,
        MonitoringPlanVersion.is_active == True
    ).update({"is_active": False})

    # Create new version
    effective_date = payload.effective_date or date.today()
    new_version = MonitoringPlanVersion(
        plan_id=plan_id,
        version_number=new_version_number,
        version_name=payload.version_name or f"Version {new_version_number}",
        description=payload.description,
        effective_date=effective_date,
        published_by_user_id=current_user.user_id,
        is_active=True
    )
    db.add(new_version)
    db.flush()

    # Snapshot all active metrics
    active_metrics = [m for m in plan.metrics if m.is_active]

    for metric in active_metrics:
        # Get category name from KPM
        kpm = metric.kpm
        category_name = None
        if kpm.category_id:
            from app.models.kpm import KpmCategory
            category = db.query(KpmCategory).filter(
                KpmCategory.category_id == kpm.category_id).first()
            category_name = category.name if category else None

        snapshot = MonitoringPlanMetricSnapshot(
            version_id=new_version.version_id,
            original_metric_id=metric.metric_id,
            kpm_id=metric.kpm_id,
            yellow_min=metric.yellow_min,
            yellow_max=metric.yellow_max,
            red_min=metric.red_min,
            red_max=metric.red_max,
            qualitative_guidance=metric.qualitative_guidance,
            sort_order=metric.sort_order,
            is_active=metric.is_active,
            kpm_name=kpm.name,
            kpm_category_name=category_name,
            evaluation_type=kpm.evaluation_type or "Quantitative"
        )
        db.add(snapshot)

    # Snapshot all models in scope
    for model in plan.models:
        model_snapshot = MonitoringPlanModelSnapshot(
            version_id=new_version.version_id,
            model_id=model.model_id,
            model_name=model.model_name
        )
        db.add(model_snapshot)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="MonitoringPlanVersion",
        entity_id=new_version.version_id,
        action="PUBLISH",
        user_id=current_user.user_id,
        changes={
            "plan_id": plan_id,
            "plan_name": plan.name,
            "version_number": new_version_number,
            "version_name": new_version.version_name,
            "metrics_count": len(active_metrics),
            "models_count": len(plan.models)
        }
    )

    db.commit()
    db.refresh(new_version)

    return {
        "version_id": new_version.version_id,
        "plan_id": new_version.plan_id,
        "version_number": new_version.version_number,
        "version_name": new_version.version_name,
        "description": new_version.description,
        "effective_date": new_version.effective_date,
        "published_by": {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "full_name": current_user.full_name
        },
        "published_at": new_version.published_at,
        "is_active": new_version.is_active,
        "metrics_count": len(active_metrics),
        "models_count": len(plan.models),
        "cycles_count": 0
    }


@router.get("/monitoring/plans/{plan_id}/versions/{version_id}/export")
def export_version_metrics(
    plan_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export version metrics as CSV for manual comparison."""
    from fastapi.responses import StreamingResponse
    import csv
    import io

    version = db.query(MonitoringPlanVersion).options(
        joinedload(MonitoringPlanVersion.metric_snapshots),
        joinedload(MonitoringPlanVersion.plan)
    ).filter(
        MonitoringPlanVersion.version_id == version_id,
        MonitoringPlanVersion.plan_id == plan_id
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "KPM ID", "KPM Name", "Category", "Evaluation Type",
        "Yellow Min", "Yellow Max", "Red Min", "Red Max",
        "Qualitative Guidance", "Sort Order"
    ])

    # Data rows
    for s in sorted(version.metric_snapshots, key=lambda x: x.sort_order):
        writer.writerow([
            s.kpm_id,
            s.kpm_name,
            s.kpm_category_name or "",
            s.evaluation_type,
            s.yellow_min if s.yellow_min is not None else "",
            s.yellow_max if s.yellow_max is not None else "",
            s.red_min if s.red_min is not None else "",
            s.red_max if s.red_max is not None else "",
            s.qualitative_guidance or "",
            s.sort_order
        ])

    output.seek(0)

    # Generate filename
    plan_name = version.plan.name.replace(" ", "_")[:30]
    filename = f"{plan_name}_v{version.version_number}_{version.effective_date}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/monitoring/plans/{plan_id}/active-cycles-warning", response_model=ActiveCyclesWarning)
def check_active_cycles_warning(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if there are active cycles that would not be affected by metric changes.

    Returns warning info if there are cycles locked to previous versions.
    """
    from app.models.monitoring import MonitoringCycle, MonitoringCycleStatus

    # Verify plan exists
    plan = db.query(MonitoringPlan).filter(
        MonitoringPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

    active_statuses = [
        MonitoringCycleStatus.DATA_COLLECTION.value,
        MonitoringCycleStatus.UNDER_REVIEW.value,
        MonitoringCycleStatus.PENDING_APPROVAL.value
    ]

    active_cycles = db.query(MonitoringCycle).filter(
        MonitoringCycle.plan_id == plan_id,
        MonitoringCycle.status.in_(active_statuses),
        MonitoringCycle.plan_version_id.isnot(None)
    ).count()

    if active_cycles > 0:
        return {
            "warning": True,
            "message": f"There are {active_cycles} active cycle(s) locked to previous versions. "
            f"Changes will only affect new cycles after a new version is published.",
            "active_cycle_count": active_cycles
        }

    return {
        "warning": False,
        "message": "",
        "active_cycle_count": 0
    }


# ============================================================================
# MONITORING PLAN METRICS ENDPOINTS
# ============================================================================

@router.post("/monitoring/plans/{plan_id}/metrics", response_model=MonitoringPlanMetricResponse, status_code=status.HTTP_201_CREATED)
def add_plan_metric(
    plan_id: int,
    metric_data: MonitoringPlanMetricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a metric to a monitoring plan (Admin or team member)."""
    # Check permission - raises 403 if not authorized
    plan = check_plan_edit_permission(db, plan_id, current_user)

    # Validate KPM exists
    kpm = db.query(Kpm).filter(Kpm.kpm_id == metric_data.kpm_id).first()
    if not kpm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KPM not found"
        )

    # Check if metric already exists in plan
    existing = db.query(MonitoringPlanMetric).filter(
        MonitoringPlanMetric.plan_id == plan_id,
        MonitoringPlanMetric.kpm_id == metric_data.kpm_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This KPM is already in the plan"
        )

    # Validate threshold consistency
    validate_metric_thresholds(
        yellow_min=metric_data.yellow_min,
        yellow_max=metric_data.yellow_max,
        red_min=metric_data.red_min,
        red_max=metric_data.red_max
    )

    metric = MonitoringPlanMetric(
        plan_id=plan_id,
        kpm_id=metric_data.kpm_id,
        yellow_min=metric_data.yellow_min,
        yellow_max=metric_data.yellow_max,
        red_min=metric_data.red_min,
        red_max=metric_data.red_max,
        qualitative_guidance=metric_data.qualitative_guidance,
        sort_order=metric_data.sort_order,
        is_active=metric_data.is_active
    )

    db.add(metric)
    db.flush()

    # Audit log
    create_audit_log(
        db=db,
        entity_type="MonitoringPlanMetric",
        entity_id=metric.metric_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "plan_id": plan_id,
            "plan_name": plan.name,
            "kpm_id": kpm.kpm_id,
            "kpm_name": kpm.name
        }
    )

    db.commit()
    db.refresh(metric)

    # Load KPM relationship
    metric = db.query(MonitoringPlanMetric).options(
        joinedload(MonitoringPlanMetric.kpm)
    ).filter(MonitoringPlanMetric.metric_id == metric.metric_id).first()

    return {
        "metric_id": metric.metric_id,
        "plan_id": metric.plan_id,
        "kpm_id": metric.kpm_id,
        "yellow_min": metric.yellow_min,
        "yellow_max": metric.yellow_max,
        "red_min": metric.red_min,
        "red_max": metric.red_max,
        "qualitative_guidance": metric.qualitative_guidance,
        "sort_order": metric.sort_order,
        "is_active": metric.is_active,
        "kpm": {
            "kpm_id": metric.kpm.kpm_id,
            "name": metric.kpm.name,
            "category_id": metric.kpm.category_id,
            "evaluation_type": metric.kpm.evaluation_type
        }
    }


@router.patch("/monitoring/plans/{plan_id}/metrics/{metric_id}", response_model=MonitoringPlanMetricResponse)
def update_plan_metric(
    plan_id: int,
    metric_id: int,
    update_data: MonitoringPlanMetricUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a metric in a monitoring plan (Admin or team member)."""
    # Check permission - raises 403 if not authorized
    check_plan_edit_permission(db, plan_id, current_user)

    metric = db.query(MonitoringPlanMetric).options(
        joinedload(MonitoringPlanMetric.kpm),
        joinedload(MonitoringPlanMetric.plan)
    ).filter(
        MonitoringPlanMetric.metric_id == metric_id,
        MonitoringPlanMetric.plan_id == plan_id
    ).first()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found in this plan"
        )

    # Track changes for audit log
    changes = {}

    # Update fields
    if update_data.kpm_id is not None:
        kpm = db.query(Kpm).filter(Kpm.kpm_id == update_data.kpm_id).first()
        if not kpm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="KPM not found"
            )
        if metric.kpm_id != update_data.kpm_id:
            changes["kpm_id"] = {
                "old": metric.kpm_id, "new": update_data.kpm_id}
        metric.kpm_id = update_data.kpm_id

    if update_data.yellow_min is not None:
        if metric.yellow_min != update_data.yellow_min:
            changes["yellow_min"] = {
                "old": metric.yellow_min, "new": update_data.yellow_min}
        metric.yellow_min = update_data.yellow_min

    if update_data.yellow_max is not None:
        if metric.yellow_max != update_data.yellow_max:
            changes["yellow_max"] = {
                "old": metric.yellow_max, "new": update_data.yellow_max}
        metric.yellow_max = update_data.yellow_max

    if update_data.red_min is not None:
        if metric.red_min != update_data.red_min:
            changes["red_min"] = {
                "old": metric.red_min, "new": update_data.red_min}
        metric.red_min = update_data.red_min

    if update_data.red_max is not None:
        if metric.red_max != update_data.red_max:
            changes["red_max"] = {
                "old": metric.red_max, "new": update_data.red_max}
        metric.red_max = update_data.red_max

    if update_data.qualitative_guidance is not None:
        if metric.qualitative_guidance != update_data.qualitative_guidance:
            changes["qualitative_guidance"] = {
                "old": metric.qualitative_guidance, "new": update_data.qualitative_guidance}
        metric.qualitative_guidance = update_data.qualitative_guidance

    if update_data.sort_order is not None:
        if metric.sort_order != update_data.sort_order:
            changes["sort_order"] = {
                "old": metric.sort_order, "new": update_data.sort_order}
        metric.sort_order = update_data.sort_order

    if update_data.is_active is not None:
        if metric.is_active != update_data.is_active:
            changes["is_active"] = {
                "old": metric.is_active, "new": update_data.is_active}
        metric.is_active = update_data.is_active

    # Validate threshold consistency with final values
    validate_metric_thresholds(
        yellow_min=metric.yellow_min,
        yellow_max=metric.yellow_max,
        red_min=metric.red_min,
        red_max=metric.red_max
    )

    # Audit log if changes were made
    if changes:
        changes["plan_name"] = metric.plan.name
        changes["kpm_name"] = metric.kpm.name
        create_audit_log(
            db=db,
            entity_type="MonitoringPlanMetric",
            entity_id=metric_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(metric)

    return {
        "metric_id": metric.metric_id,
        "plan_id": metric.plan_id,
        "kpm_id": metric.kpm_id,
        "yellow_min": metric.yellow_min,
        "yellow_max": metric.yellow_max,
        "red_min": metric.red_min,
        "red_max": metric.red_max,
        "qualitative_guidance": metric.qualitative_guidance,
        "sort_order": metric.sort_order,
        "is_active": metric.is_active,
        "kpm": {
            "kpm_id": metric.kpm.kpm_id,
            "name": metric.kpm.name,
            "category_id": metric.kpm.category_id,
            "evaluation_type": metric.kpm.evaluation_type
        }
    }


@router.delete("/monitoring/plans/{plan_id}/metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_metric(
    plan_id: int,
    metric_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a metric from a monitoring plan (Admin or team member)."""
    # Check permission - raises 403 if not authorized
    check_plan_edit_permission(db, plan_id, current_user)

    metric = db.query(MonitoringPlanMetric).options(
        joinedload(MonitoringPlanMetric.kpm),
        joinedload(MonitoringPlanMetric.plan)
    ).filter(
        MonitoringPlanMetric.metric_id == metric_id,
        MonitoringPlanMetric.plan_id == plan_id
    ).first()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found in this plan"
        )

    # Audit log before deletion
    create_audit_log(
        db=db,
        entity_type="MonitoringPlanMetric",
        entity_id=metric_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "plan_id": plan_id,
            "plan_name": metric.plan.name,
            "kpm_id": metric.kpm_id,
            "kpm_name": metric.kpm.name
        }
    )

    db.delete(metric)
    db.commit()

    return None


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.post("/monitoring/plans/{plan_id}/advance-cycle", response_model=MonitoringPlanResponse)
def advance_plan_cycle(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Advance a plan to the next monitoring cycle (Admin or team member).

    This recalculates the next submission and report due dates based on frequency.
    """
    # Check permission - raises 403 if not authorized
    plan = check_plan_edit_permission(db, plan_id, current_user)

    # Store old dates for audit log
    old_submission_date = str(
        plan.next_submission_due_date) if plan.next_submission_due_date else None
    old_report_date = str(
        plan.next_report_due_date) if plan.next_report_due_date else None

    # Calculate next dates from current submission date
    base_date = plan.next_submission_due_date or date.today()
    new_submission_date = calculate_next_submission_date(
        MonitoringFrequency(plan.frequency), base_date
    )
    new_report_date = calculate_report_due_date(
        new_submission_date, plan.reporting_lead_days
    )

    plan.next_submission_due_date = new_submission_date
    plan.next_report_due_date = new_report_date

    # Audit log for cycle advance
    create_audit_log(
        db=db,
        entity_type="MonitoringPlan",
        entity_id=plan_id,
        action="ADVANCE_CYCLE",
        user_id=current_user.user_id,
        changes={
            "plan_name": plan.name,
            "next_submission_due_date": {"old": old_submission_date, "new": str(new_submission_date)},
            "next_report_due_date": {"old": old_report_date, "new": str(new_report_date)}
        }
    )

    db.commit()

    return get_monitoring_plan(plan_id, db, current_user)


# ============================================================================
# MONITORING CYCLES ENDPOINTS
# ============================================================================


# ============================================================================
# MY MONITORING TASKS ENDPOINT
# ============================================================================

@router.get("/monitoring/my-tasks", response_model=List[MyMonitoringTaskResponse])
def get_my_monitoring_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get monitoring tasks for the current user.

    Returns cycles where the current user has a role/responsibility:
    - data_provider: User is the plan's data provider (needs to submit results)
    - team_member: User is on the monitoring team (risk function - review/approve)
    - assignee: User is specifically assigned to the cycle

    Only returns active cycles (not APPROVED or CANCELLED).
    """
    today = date.today()
    tasks = []

    # Get active statuses (cycles that need action)
    active_statuses = [
        MonitoringCycleStatus.PENDING.value,
        MonitoringCycleStatus.DATA_COLLECTION.value,
        MonitoringCycleStatus.UNDER_REVIEW.value,
        MonitoringCycleStatus.PENDING_APPROVAL.value,
    ]

    # Query 1: Cycles where user is the data provider for the plan
    data_provider_cycles = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.plan)
    ).join(
        MonitoringPlan, MonitoringCycle.plan_id == MonitoringPlan.plan_id
    ).filter(
        MonitoringPlan.data_provider_user_id == current_user.user_id,
        MonitoringCycle.status.in_(active_statuses)
    ).all()

    for cycle in data_provider_cycles:
        action = _get_data_provider_action(cycle.status)
        is_overdue = cycle.submission_due_date < today
        days_until_due = (cycle.submission_due_date -
                          today).days if not is_overdue else None

        # Count results
        result_count = db.query(func.count(MonitoringResult.result_id)).filter(
            MonitoringResult.cycle_id == cycle.cycle_id
        ).scalar() or 0

        tasks.append({
            "cycle_id": cycle.cycle_id,
            "plan_id": cycle.plan_id,
            "plan_name": cycle.plan.name,
            "period_start_date": cycle.period_start_date,
            "period_end_date": cycle.period_end_date,
            "submission_due_date": cycle.submission_due_date,
            "report_due_date": cycle.report_due_date,
            "status": cycle.status,
            "user_role": "data_provider",
            "action_needed": action,
            "result_count": result_count,
            "pending_approval_count": 0,
            "is_overdue": is_overdue,
            "days_until_due": days_until_due,
        })

    # Query 2: Cycles where user is assigned_to
    assigned_cycles = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.plan)
    ).filter(
        MonitoringCycle.assigned_to_user_id == current_user.user_id,
        MonitoringCycle.status.in_(active_statuses)
    ).all()

    # Track cycle_ids we've already added to avoid duplicates
    added_cycle_ids = {t["cycle_id"] for t in tasks}

    for cycle in assigned_cycles:
        if cycle.cycle_id in added_cycle_ids:
            continue

        action = _get_assignee_action(cycle.status)
        is_overdue = cycle.submission_due_date < today
        days_until_due = (cycle.submission_due_date -
                          today).days if not is_overdue else None

        result_count = db.query(func.count(MonitoringResult.result_id)).filter(
            MonitoringResult.cycle_id == cycle.cycle_id
        ).scalar() or 0

        tasks.append({
            "cycle_id": cycle.cycle_id,
            "plan_id": cycle.plan_id,
            "plan_name": cycle.plan.name,
            "period_start_date": cycle.period_start_date,
            "period_end_date": cycle.period_end_date,
            "submission_due_date": cycle.submission_due_date,
            "report_due_date": cycle.report_due_date,
            "status": cycle.status,
            "user_role": "assignee",
            "action_needed": action,
            "result_count": result_count,
            "pending_approval_count": 0,
            "is_overdue": is_overdue,
            "days_until_due": days_until_due,
        })
        added_cycle_ids.add(cycle.cycle_id)

    # Query 3: Cycles where user is a monitoring team member (risk function)
    # These users review and approve results
    team_member_plans = db.query(MonitoringPlan.plan_id).join(
        MonitoringTeam, MonitoringPlan.monitoring_team_id == MonitoringTeam.team_id
    ).join(
        monitoring_team_members,
        MonitoringTeam.team_id == monitoring_team_members.c.team_id
    ).filter(
        monitoring_team_members.c.user_id == current_user.user_id
    ).all()

    team_plan_ids = [p[0] for p in team_member_plans]

    if team_plan_ids:
        team_cycles = db.query(MonitoringCycle).options(
            joinedload(MonitoringCycle.plan)
        ).filter(
            MonitoringCycle.plan_id.in_(team_plan_ids),
            MonitoringCycle.status.in_(active_statuses)
        ).all()

        for cycle in team_cycles:
            if cycle.cycle_id in added_cycle_ids:
                continue

            action = _get_team_member_action(cycle.status)
            # Team members care about report due date
            is_overdue = cycle.report_due_date < today
            days_until_due = (cycle.report_due_date -
                              today).days if not is_overdue else None

            result_count = db.query(func.count(MonitoringResult.result_id)).filter(
                MonitoringResult.cycle_id == cycle.cycle_id
            ).scalar() or 0

            pending_approval_count = db.query(func.count(MonitoringCycleApproval.approval_id)).filter(
                MonitoringCycleApproval.cycle_id == cycle.cycle_id,
                MonitoringCycleApproval.approval_status == "Pending"
            ).scalar() or 0

            tasks.append({
                "cycle_id": cycle.cycle_id,
                "plan_id": cycle.plan_id,
                "plan_name": cycle.plan.name,
                "period_start_date": cycle.period_start_date,
                "period_end_date": cycle.period_end_date,
                "submission_due_date": cycle.submission_due_date,
                "report_due_date": cycle.report_due_date,
                "status": cycle.status,
                "user_role": "team_member",
                "action_needed": action,
                "result_count": result_count,
                "pending_approval_count": pending_approval_count,
                "is_overdue": is_overdue,
                "days_until_due": days_until_due,
            })
            added_cycle_ids.add(cycle.cycle_id)

    # Sort by due date (most urgent first)
    tasks.sort(key=lambda t: (not t["is_overdue"], t["submission_due_date"]))

    return tasks


def _get_data_provider_action(status: str) -> str:
    """Get action needed for data provider based on cycle status."""
    if status == MonitoringCycleStatus.PENDING.value:
        return "Waiting for cycle to start"
    elif status == MonitoringCycleStatus.DATA_COLLECTION.value:
        return "Submit Results"
    elif status == MonitoringCycleStatus.UNDER_REVIEW.value:
        return "Results submitted - Under Review"
    elif status == MonitoringCycleStatus.PENDING_APPROVAL.value:
        return "Pending Approval"
    return "No action required"


def _get_assignee_action(status: str) -> str:
    """Get action needed for assignee based on cycle status."""
    if status == MonitoringCycleStatus.PENDING.value:
        return "Start Cycle"
    elif status == MonitoringCycleStatus.DATA_COLLECTION.value:
        return "Submit Results"
    elif status == MonitoringCycleStatus.UNDER_REVIEW.value:
        return "Review Results"
    elif status == MonitoringCycleStatus.PENDING_APPROVAL.value:
        return "Pending Approval"
    return "No action required"


def _get_team_member_action(status: str) -> str:
    """Get action needed for team member (risk function) based on cycle status."""
    if status == MonitoringCycleStatus.PENDING.value:
        return "Awaiting Data Collection"
    elif status == MonitoringCycleStatus.DATA_COLLECTION.value:
        return "Awaiting Results"
    elif status == MonitoringCycleStatus.UNDER_REVIEW.value:
        return "Review Results"
    elif status == MonitoringCycleStatus.PENDING_APPROVAL.value:
        return "Approve Results"
    return "No action required"


# ============================================================================
# ADMIN MONITORING OVERVIEW ENDPOINT
# ============================================================================

@router.get("/monitoring/admin-overview", response_model=AdminMonitoringOverviewResponse)
def get_admin_monitoring_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get monitoring program overview for admin governance.

    Provides a comprehensive view of all monitoring activity:
    - Summary counts: overdue, pending approval, in progress, recently completed
    - Priority-sorted cycle list with urgency indicators

    Only accessible by Admin users.
    """
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    fourteen_days_from_now = today + timedelta(days=14)

    # Query all cycles with their related data
    cycles = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.plan).joinedload(MonitoringPlan.team),
        joinedload(MonitoringCycle.plan).joinedload(
            MonitoringPlan.data_provider),
    ).all()

    # Calculate summary counts
    overdue_count = 0
    pending_approval_count = 0
    in_progress_count = 0
    completed_last_30_days = 0

    for cycle in cycles:
        if cycle.status == MonitoringCycleStatus.APPROVED.value:
            if cycle.completed_at and cycle.completed_at.date() >= thirty_days_ago:
                completed_last_30_days += 1
        elif cycle.status == MonitoringCycleStatus.CANCELLED.value:
            pass  # Don't count cancelled
        elif cycle.status == MonitoringCycleStatus.PENDING_APPROVAL.value:
            pending_approval_count += 1
            if cycle.report_due_date < today:
                overdue_count += 1
        elif cycle.status in [
            MonitoringCycleStatus.DATA_COLLECTION.value,
            MonitoringCycleStatus.UNDER_REVIEW.value
        ]:
            in_progress_count += 1
            # Check if overdue based on relevant due date
            due_date = cycle.submission_due_date if cycle.status == MonitoringCycleStatus.DATA_COLLECTION.value else cycle.report_due_date
            if due_date < today:
                overdue_count += 1
        elif cycle.status == MonitoringCycleStatus.PENDING.value:
            # PENDING cycles don't contribute to overdue yet
            pass

    # Build cycle summaries for active cycles (exclude APPROVED and CANCELLED)
    active_statuses = [
        MonitoringCycleStatus.PENDING.value,
        MonitoringCycleStatus.DATA_COLLECTION.value,
        MonitoringCycleStatus.UNDER_REVIEW.value,
        MonitoringCycleStatus.PENDING_APPROVAL.value,
    ]

    cycle_summaries = []
    for cycle in cycles:
        if cycle.status not in active_statuses:
            continue

        # Determine due date based on status
        if cycle.status in [MonitoringCycleStatus.PENDING.value, MonitoringCycleStatus.DATA_COLLECTION.value]:
            due_date = cycle.submission_due_date
        else:
            due_date = cycle.report_due_date

        # Calculate days overdue (positive = overdue, negative = days remaining)
        days_overdue = (today - due_date).days

        # Determine priority
        if days_overdue > 0:
            priority = "overdue"
        elif cycle.status == MonitoringCycleStatus.PENDING_APPROVAL.value:
            priority = "pending_approval"
        elif days_overdue >= -14:  # Within 14 days
            priority = "approaching"
        else:
            priority = "normal"

        # Generate period label (e.g., "Q3 2025" or "Sep 2025")
        period_label = _generate_period_label(
            cycle.period_start_date, cycle.period_end_date)

        # Get team and data provider names
        team_name = cycle.plan.team.name if cycle.plan.team else None
        data_provider_name = cycle.plan.data_provider.full_name if cycle.plan.data_provider else None

        # Get approval progress for PENDING_APPROVAL cycles
        approval_progress = None
        if cycle.status == MonitoringCycleStatus.PENDING_APPROVAL.value:
            total_approvals = db.query(func.count(MonitoringCycleApproval.approval_id)).filter(
                MonitoringCycleApproval.cycle_id == cycle.cycle_id,
                MonitoringCycleApproval.is_required == True
            ).scalar() or 0

            completed_approvals = db.query(func.count(MonitoringCycleApproval.approval_id)).filter(
                MonitoringCycleApproval.cycle_id == cycle.cycle_id,
                MonitoringCycleApproval.is_required == True,
                MonitoringCycleApproval.approval_status == "Approved"
            ).scalar() or 0

            if total_approvals > 0:
                approval_progress = f"{completed_approvals}/{total_approvals}"

        # Get result counts
        result_count = db.query(func.count(MonitoringResult.result_id)).filter(
            MonitoringResult.cycle_id == cycle.cycle_id
        ).scalar() or 0

        green_count = db.query(func.count(MonitoringResult.result_id)).filter(
            MonitoringResult.cycle_id == cycle.cycle_id,
            MonitoringResult.calculated_outcome == "GREEN"
        ).scalar() or 0

        yellow_count = db.query(func.count(MonitoringResult.result_id)).filter(
            MonitoringResult.cycle_id == cycle.cycle_id,
            MonitoringResult.calculated_outcome == "YELLOW"
        ).scalar() or 0

        red_count = db.query(func.count(MonitoringResult.result_id)).filter(
            MonitoringResult.cycle_id == cycle.cycle_id,
            MonitoringResult.calculated_outcome == "RED"
        ).scalar() or 0

        cycle_summaries.append(AdminMonitoringCycleSummary(
            cycle_id=cycle.cycle_id,
            plan_id=cycle.plan_id,
            plan_name=cycle.plan.name,
            period_label=period_label,
            period_start_date=cycle.period_start_date,
            period_end_date=cycle.period_end_date,
            due_date=due_date,
            status=cycle.status,
            days_overdue=days_overdue,
            priority=priority,
            team_name=team_name,
            data_provider_name=data_provider_name,
            approval_progress=approval_progress,
            report_url=cycle.report_url,
            result_count=result_count,
            green_count=green_count,
            yellow_count=yellow_count,
            red_count=red_count,
        ))

    # Sort by priority: overdue first (most overdue), then pending_approval, then approaching, then normal
    priority_order = {"overdue": 0, "pending_approval": 1,
                      "approaching": 2, "normal": 3}
    cycle_summaries.sort(key=lambda c: (
        priority_order.get(c.priority, 3), -c.days_overdue))

    return AdminMonitoringOverviewResponse(
        summary=AdminMonitoringOverviewSummary(
            overdue_count=overdue_count,
            pending_approval_count=pending_approval_count,
            in_progress_count=in_progress_count,
            completed_last_30_days=completed_last_30_days,
        ),
        cycles=cycle_summaries,
    )


def _generate_period_label(start_date: date, end_date: date) -> str:
    """Generate a human-readable period label (e.g., 'Q3 2025' or 'Sep 2025')."""
    # Check if it's a quarter (3-month period starting in Jan, Apr, Jul, Oct)
    if start_date.day == 1 and start_date.month in [1, 4, 7, 10]:
        # Calculate expected quarter end
        quarter_month = start_date.month + 2
        quarter_year = start_date.year
        if quarter_month > 12:
            quarter_month -= 12
            quarter_year += 1

        # Check if end_date matches quarter end
        from calendar import monthrange
        expected_end = date(
            quarter_year if quarter_month <= 12 else quarter_year + 1,
            quarter_month,
            monthrange(quarter_year, quarter_month)[1]
        )

        if end_date == expected_end:
            quarter = (start_date.month - 1) // 3 + 1
            return f"Q{quarter} {start_date.year}"

    # Check if it's a single month
    if start_date.day == 1:
        from calendar import monthrange
        last_day = monthrange(start_date.year, start_date.month)[1]
        if end_date == date(start_date.year, start_date.month, last_day):
            return start_date.strftime("%b %Y")

    # Check if it's semi-annual (6 months)
    months_diff = (end_date.year - start_date.year) * \
        12 + end_date.month - start_date.month
    if months_diff >= 5 and months_diff <= 6:
        if start_date.month <= 6:
            return f"H1 {start_date.year}"
        else:
            return f"H2 {start_date.year}"

    # Default: show date range
    return f"{start_date.strftime('%Y-%m')} - {end_date.strftime('%Y-%m')}"


def calculate_period_dates(frequency: MonitoringFrequency, from_date: date = None) -> tuple:
    """Calculate period start and end dates based on frequency."""
    if from_date is None:
        from_date = date.today()

    # Start from beginning of current period
    if frequency == MonitoringFrequency.MONTHLY:
        period_start = from_date.replace(day=1)
        period_end = (period_start + relativedelta(months=1)) - \
            timedelta(days=1)
    elif frequency == MonitoringFrequency.QUARTERLY:
        quarter_month = ((from_date.month - 1) // 3) * 3 + 1
        period_start = from_date.replace(month=quarter_month, day=1)
        period_end = (period_start + relativedelta(months=3)) - \
            timedelta(days=1)
    elif frequency == MonitoringFrequency.SEMI_ANNUAL:
        half_month = 1 if from_date.month <= 6 else 7
        period_start = from_date.replace(month=half_month, day=1)
        period_end = (period_start + relativedelta(months=6)) - \
            timedelta(days=1)
    elif frequency == MonitoringFrequency.ANNUAL:
        period_start = from_date.replace(month=1, day=1)
        period_end = from_date.replace(month=12, day=31)
    else:
        # Default to quarterly
        quarter_month = ((from_date.month - 1) // 3) * 3 + 1
        period_start = from_date.replace(month=quarter_month, day=1)
        period_end = (period_start + relativedelta(months=3)) - \
            timedelta(days=1)

    return period_start, period_end


def calculate_outcome(value: float, metric: MonitoringPlanMetric) -> str:
    """Calculate outcome (GREEN, YELLOW, RED) based on thresholds."""
    if value is None:
        return "N/A"

    # Check red thresholds first (highest severity)
    if metric.red_min is not None and value < metric.red_min:
        return "RED"
    if metric.red_max is not None and value > metric.red_max:
        return "RED"

    # Check yellow thresholds
    if metric.yellow_min is not None and value < metric.yellow_min:
        return "YELLOW"
    if metric.yellow_max is not None and value > metric.yellow_max:
        return "YELLOW"

    # If passed all threshold checks, it's green
    return "GREEN"


def check_cycle_edit_permission(db: Session, cycle_id: int, current_user: User) -> MonitoringCycle:
    """Check if user can edit a monitoring cycle (enter/update results).

    Returns the cycle if user has permission, raises HTTPException otherwise.

    Permission is granted if:
    - User is an Admin, OR
    - User is a member of the monitoring team assigned to the plan, OR
    - User is the data provider for the plan, OR
    - User is assigned to this specific cycle
    """
    cycle = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.plan).joinedload(
            MonitoringPlan.team).joinedload(MonitoringTeam.members)
    ).filter(MonitoringCycle.cycle_id == cycle_id).first()

    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cycle not found"
        )

    # Admins always have permission
    if current_user.role == UserRole.ADMIN:
        return cycle

    # Check if user is assigned to this cycle
    if cycle.assigned_to_user_id == current_user.user_id:
        return cycle

    # Check if user is the data provider for the plan
    if cycle.plan and cycle.plan.data_provider_user_id == current_user.user_id:
        return cycle

    # Check if user is a member of the plan's monitoring team
    if cycle.plan and cycle.plan.team:
        member_ids = [m.user_id for m in cycle.plan.team.members]
        if current_user.user_id in member_ids:
            return cycle

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You must be an Admin, team member, data provider, or cycle assignee to edit this cycle"
    )


def check_team_member_or_admin(db: Session, cycle_id: int, current_user: User) -> MonitoringCycle:
    """Check if user is Admin or monitoring team member (risk function).

    Used for workflow actions that should only be performed by the risk function:
    - Start cycle (PENDING → DATA_COLLECTION)
    - Request approval (UNDER_REVIEW → PENDING_APPROVAL)
    - Cancel cycle

    Data providers and assignees who are not team members cannot perform these actions.
    """
    cycle = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.plan).joinedload(
            MonitoringPlan.team).joinedload(MonitoringTeam.members)
    ).filter(MonitoringCycle.cycle_id == cycle_id).first()

    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cycle not found"
        )

    # Admins always have permission
    if current_user.role == UserRole.ADMIN:
        return cycle

    # Check if user is a member of the plan's monitoring team (risk function)
    if cycle.plan and cycle.plan.team:
        member_ids = [m.user_id for m in cycle.plan.team.members]
        if current_user.user_id in member_ids:
            return cycle

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only Admin or monitoring team members can perform this workflow action"
    )


def validate_results_completeness(db: Session, cycle: MonitoringCycle) -> None:
    """Validate results before submission.

    Rules:
    - Cycle must have a locked version
    - At least one result must be entered
    - For metrics without a value (null numeric_value and null outcome_value_id),
      a narrative/comment is required explaining why the metric was not measured

    Raises HTTPException if validation fails.
    """
    # Get the version's metric snapshots (what metrics were active when cycle started)
    if not cycle.plan_version_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit: Cycle has no locked version. Start the cycle first."
        )

    # Get metric snapshots for this version
    metric_snapshots = db.query(MonitoringPlanMetricSnapshot).filter(
        MonitoringPlanMetricSnapshot.version_id == cycle.plan_version_id
    ).all()

    if not metric_snapshots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit: No metrics defined in the plan version."
        )

    # Get existing results for this cycle
    existing_results = db.query(MonitoringResult).filter(
        MonitoringResult.cycle_id == cycle.cycle_id
    ).all()

    # Must have at least one result
    if not existing_results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit: No results have been entered. Enter at least one metric result before submitting."
        )

    # Build map of results by metric_id for easy lookup
    results_by_metric = {r.plan_metric_id: r for r in existing_results}

    # Check which metrics are missing entirely or have no value without explanation
    metrics_missing_entirely = []
    metrics_missing_explanation = []

    for snapshot in metric_snapshots:
        if not snapshot.original_metric_id:
            continue

        result = results_by_metric.get(snapshot.original_metric_id)

        if not result:
            # Metric has no result record at all
            metrics_missing_entirely.append(snapshot.kpm_name)
        elif result.numeric_value is None and result.outcome_value_id is None:
            # Result exists but has no value - must have narrative
            if not result.narrative or not result.narrative.strip():
                metrics_missing_explanation.append(snapshot.kpm_name)

    # Report issues
    issues = []
    if metrics_missing_entirely:
        issues.append(
            f"Missing results for: {', '.join(metrics_missing_entirely)}")
    if metrics_missing_explanation:
        issues.append(
            f"Missing explanation for N/A values: {', '.join(metrics_missing_explanation)}")

    if issues:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit: {'; '.join(issues)}. Either enter a value or provide a narrative explaining why the metric was not measured."
        )


@router.post("/monitoring/plans/{plan_id}/cycles", response_model=MonitoringCycleResponse, status_code=status.HTTP_201_CREATED)
def create_monitoring_cycle(
    plan_id: int,
    cycle_data: MonitoringCycleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new monitoring cycle for a plan (Admin or team member)."""
    # Check plan edit permission
    plan = check_plan_edit_permission(db, plan_id, current_user)

    # Calculate period dates if not provided
    if cycle_data.period_start_date and cycle_data.period_end_date:
        period_start = cycle_data.period_start_date
        period_end = cycle_data.period_end_date
    else:
        # Find the last cycle to determine next period
        last_cycle = db.query(MonitoringCycle).filter(
            MonitoringCycle.plan_id == plan_id
        ).order_by(MonitoringCycle.period_end_date.desc()).first()

        if last_cycle:
            # Next period starts after last period ended
            base_date = last_cycle.period_end_date + timedelta(days=1)
        else:
            # First cycle - use plan's current dates or today
            base_date = plan.next_submission_due_date or date.today()

        period_start, period_end = calculate_period_dates(
            MonitoringFrequency(plan.frequency), base_date
        )

    # Calculate due dates
    # Default: 15 days after period end
    submission_due = period_end + timedelta(days=15)
    report_due = calculate_report_due_date(
        submission_due, plan.reporting_lead_days)

    # Use plan's data provider if no specific assignment
    assigned_to = cycle_data.assigned_to_user_id or plan.data_provider_user_id

    cycle = MonitoringCycle(
        plan_id=plan_id,
        period_start_date=period_start,
        period_end_date=period_end,
        submission_due_date=submission_due,
        report_due_date=report_due,
        status=MonitoringCycleStatus.PENDING.value,
        assigned_to_user_id=assigned_to,
        notes=cycle_data.notes
    )

    db.add(cycle)
    db.flush()

    # Audit log
    create_audit_log(
        db=db,
        entity_type="MonitoringCycle",
        entity_id=cycle.cycle_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "plan_id": plan_id,
            "plan_name": plan.name,
            "period": f"{period_start} to {period_end}",
            "status": cycle.status
        }
    )

    db.commit()

    return get_monitoring_cycle(cycle.cycle_id, db, current_user)


@router.get("/monitoring/plans/{plan_id}/cycles", response_model=list[MonitoringCycleListResponse])
def list_plan_cycles(
    plan_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all cycles for a monitoring plan."""
    # Verify plan exists
    plan = db.query(MonitoringPlan).filter(
        MonitoringPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    query = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.assigned_to),
        joinedload(MonitoringCycle.results),
        joinedload(MonitoringCycle.approvals),
        joinedload(MonitoringCycle.plan_version)
    ).filter(MonitoringCycle.plan_id == plan_id)

    if status_filter:
        query = query.filter(MonitoringCycle.status == status_filter)

    cycles = query.order_by(MonitoringCycle.period_end_date.desc()).all()

    result = []
    today = date.today()
    for cycle in cycles:
        # Count outcomes
        green_count = sum(
            1 for r in cycle.results if r.calculated_outcome == "GREEN")
        yellow_count = sum(
            1 for r in cycle.results if r.calculated_outcome == "YELLOW")
        red_count = sum(
            1 for r in cycle.results if r.calculated_outcome == "RED")

        # Count approvals (only required, non-voided ones)
        required_approvals = [
            a for a in cycle.approvals if a.is_required and not a.voided_at]
        approval_count = len(required_approvals)
        pending_approval_count = sum(
            1 for a in required_approvals if a.approval_status == "Pending")

        # Calculate overdue status (only non-completed cycles can be overdue)
        status_value = cycle.status.value if hasattr(
            cycle.status, 'value') else cycle.status
        if status_value in ("APPROVED", "CANCELLED"):
            is_overdue = False
            days_overdue = 0
        else:
            days_overdue = (today - cycle.report_due_date).days
            is_overdue = days_overdue > 0

        result.append({
            "cycle_id": cycle.cycle_id,
            "plan_id": cycle.plan_id,
            "period_start_date": cycle.period_start_date,
            "period_end_date": cycle.period_end_date,
            "status": cycle.status,
            "submission_due_date": cycle.submission_due_date,
            "report_due_date": cycle.report_due_date,
            "assigned_to_name": cycle.assigned_to.full_name if cycle.assigned_to else None,
            # Version info
            "plan_version_id": cycle.plan_version_id,
            "version_number": cycle.plan_version.version_number if cycle.plan_version else None,
            "version_name": cycle.plan_version.version_name if cycle.plan_version else None,
            "result_count": len(cycle.results),
            "green_count": green_count,
            "yellow_count": yellow_count,
            "red_count": red_count,
            "approval_count": approval_count,
            "pending_approval_count": pending_approval_count,
            "is_overdue": is_overdue,
            "days_overdue": days_overdue
        })

    return result


@router.get("/monitoring/cycles/{cycle_id}", response_model=MonitoringCycleResponse)
def get_monitoring_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific monitoring cycle with full details."""
    cycle = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.assigned_to),
        joinedload(MonitoringCycle.submitted_by),
        joinedload(MonitoringCycle.completed_by),
        joinedload(MonitoringCycle.results),
        joinedload(MonitoringCycle.approvals),
        joinedload(MonitoringCycle.plan_version),
        joinedload(MonitoringCycle.version_locked_by)
    ).filter(MonitoringCycle.cycle_id == cycle_id).first()

    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    # Count pending approvals
    pending_approvals = sum(
        1 for a in cycle.approvals
        if a.approval_status == "Pending" and a.is_required and not a.voided_at
    )

    # Build version info if locked
    plan_version_info = None
    if cycle.plan_version:
        plan_version_info = {
            "version_id": cycle.plan_version.version_id,
            "version_number": cycle.plan_version.version_number,
            "version_name": cycle.plan_version.version_name
        }

    version_locked_by_info = None
    if cycle.version_locked_by:
        version_locked_by_info = {
            "user_id": cycle.version_locked_by.user_id,
            "email": cycle.version_locked_by.email,
            "full_name": cycle.version_locked_by.full_name
        }

    return {
        "cycle_id": cycle.cycle_id,
        "plan_id": cycle.plan_id,
        "period_start_date": cycle.period_start_date,
        "period_end_date": cycle.period_end_date,
        "submission_due_date": cycle.submission_due_date,
        "report_due_date": cycle.report_due_date,
        "status": cycle.status,
        "assigned_to": {
            "user_id": cycle.assigned_to.user_id,
            "email": cycle.assigned_to.email,
            "full_name": cycle.assigned_to.full_name
        } if cycle.assigned_to else None,
        "submitted_at": cycle.submitted_at,
        "submitted_by": {
            "user_id": cycle.submitted_by.user_id,
            "email": cycle.submitted_by.email,
            "full_name": cycle.submitted_by.full_name
        } if cycle.submitted_by else None,
        "completed_at": cycle.completed_at,
        "completed_by": {
            "user_id": cycle.completed_by.user_id,
            "email": cycle.completed_by.email,
            "full_name": cycle.completed_by.full_name
        } if cycle.completed_by else None,
        "notes": cycle.notes,
        # Version tracking fields
        "plan_version_id": cycle.plan_version_id,
        "plan_version": plan_version_info,
        "version_locked_at": cycle.version_locked_at,
        "version_locked_by": version_locked_by_info,
        "created_at": cycle.created_at,
        "updated_at": cycle.updated_at,
        "result_count": len(cycle.results),
        "approval_count": len([a for a in cycle.approvals if a.is_required and not a.voided_at]),
        "pending_approval_count": pending_approvals
    }


@router.patch("/monitoring/cycles/{cycle_id}", response_model=MonitoringCycleResponse)
def update_monitoring_cycle(
    cycle_id: int,
    update_data: MonitoringCycleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a monitoring cycle (Admin, team member, or assigned user)."""
    cycle = check_cycle_edit_permission(db, cycle_id, current_user)

    # Cannot edit completed cycles
    if cycle.status == MonitoringCycleStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit an approved cycle"
        )

    changes = {}

    if update_data.assigned_to_user_id is not None:
        if update_data.assigned_to_user_id != 0:
            user = db.query(User).filter(
                User.user_id == update_data.assigned_to_user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        new_id = update_data.assigned_to_user_id if update_data.assigned_to_user_id != 0 else None
        if cycle.assigned_to_user_id != new_id:
            changes["assigned_to_user_id"] = {
                "old": cycle.assigned_to_user_id, "new": new_id}
        cycle.assigned_to_user_id = new_id

    if update_data.notes is not None:
        if cycle.notes != update_data.notes:
            changes["notes"] = {"old": cycle.notes, "new": update_data.notes}
        cycle.notes = update_data.notes

    if changes:
        create_audit_log(
            db=db,
            entity_type="MonitoringCycle",
            entity_id=cycle_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    return get_monitoring_cycle(cycle_id, db, current_user)


@router.delete("/monitoring/cycles/{cycle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitoring_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a monitoring cycle (only if PENDING or CANCELLED with no results)."""
    cycle = check_cycle_edit_permission(db, cycle_id, current_user)

    # Can only delete PENDING or CANCELLED cycles
    if cycle.status not in [MonitoringCycleStatus.PENDING.value, MonitoringCycleStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete PENDING or CANCELLED cycles"
        )

    # Cannot delete if has results
    if cycle.results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete cycle with existing results"
        )

    create_audit_log(
        db=db,
        entity_type="MonitoringCycle",
        entity_id=cycle_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"plan_id": cycle.plan_id,
                 "period": f"{cycle.period_start_date} to {cycle.period_end_date}"}
    )

    db.delete(cycle)
    db.commit()
    return None


# ============================================================================
# MONITORING RESULTS ENDPOINTS
# ============================================================================

@router.post("/monitoring/cycles/{cycle_id}/results", response_model=MonitoringResultResponse, status_code=status.HTTP_201_CREATED)
def create_monitoring_result(
    cycle_id: int,
    result_data: MonitoringResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enter a result for a metric in a cycle."""
    cycle = check_cycle_edit_permission(db, cycle_id, current_user)

    # Can only add results when cycle is in DATA_COLLECTION or UNDER_REVIEW
    if cycle.status not in [MonitoringCycleStatus.DATA_COLLECTION.value, MonitoringCycleStatus.UNDER_REVIEW.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add results when cycle is in {cycle.status} status"
        )

    # Validate plan_metric belongs to this cycle's plan
    metric = db.query(MonitoringPlanMetric).options(
        joinedload(MonitoringPlanMetric.kpm)
    ).filter(
        MonitoringPlanMetric.metric_id == result_data.plan_metric_id,
        MonitoringPlanMetric.plan_id == cycle.plan_id
    ).first()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metric does not belong to this plan"
        )

    # Check for existing result with exact same combination
    existing = db.query(MonitoringResult).filter(
        MonitoringResult.cycle_id == cycle_id,
        MonitoringResult.plan_metric_id == result_data.plan_metric_id,
        MonitoringResult.model_id == result_data.model_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result already exists for this metric/model combination"
        )

    # Exclusive mode: Cannot mix plan-level and model-specific results for the same metric
    # If submitting plan-level (model_id=null), check no model-specific results exist
    # If submitting model-specific, check no plan-level result exists
    if result_data.model_id is None:
        # Trying to create plan-level result - check for any model-specific results
        model_specific_exists = db.query(MonitoringResult).filter(
            MonitoringResult.cycle_id == cycle_id,
            MonitoringResult.plan_metric_id == result_data.plan_metric_id,
            MonitoringResult.model_id.isnot(None)
        ).first()
        if model_specific_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create plan-level result: model-specific results already exist for this metric. Delete existing model-specific results first or continue with model-specific entry."
            )
    else:
        # Trying to create model-specific result - check for plan-level result
        plan_level_exists = db.query(MonitoringResult).filter(
            MonitoringResult.cycle_id == cycle_id,
            MonitoringResult.plan_metric_id == result_data.plan_metric_id,
            MonitoringResult.model_id.is_(None)
        ).first()
        if plan_level_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create model-specific result: a plan-level result already exists for this metric. Delete the plan-level result first or continue with plan-level entry."
            )

    # Calculate outcome for quantitative metrics
    calculated_outcome = None
    if metric.kpm.evaluation_type == "Quantitative" and result_data.numeric_value is not None:
        calculated_outcome = calculate_outcome(
            result_data.numeric_value, metric)
    elif result_data.outcome_value_id:
        # For qualitative/outcome-only, use the selected outcome
        outcome_value = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == result_data.outcome_value_id
        ).first()
        if outcome_value:
            calculated_outcome = outcome_value.code

    # Validate narrative for qualitative metrics
    if metric.kpm.evaluation_type == "Qualitative" and not result_data.narrative:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Narrative is required for qualitative metrics"
        )

    result = MonitoringResult(
        cycle_id=cycle_id,
        plan_metric_id=result_data.plan_metric_id,
        model_id=result_data.model_id,
        numeric_value=result_data.numeric_value,
        outcome_value_id=result_data.outcome_value_id,
        calculated_outcome=calculated_outcome,
        narrative=result_data.narrative,
        supporting_data=result_data.supporting_data,
        entered_by_user_id=current_user.user_id
    )

    db.add(result)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="MonitoringResult",
        entity_id=result.result_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "cycle_id": cycle_id,
            "metric_name": metric.kpm.name,
            "calculated_outcome": calculated_outcome
        }
    )

    db.commit()
    db.refresh(result)

    # Load relationships
    result = db.query(MonitoringResult).options(
        joinedload(MonitoringResult.model),
        joinedload(MonitoringResult.outcome_value),
        joinedload(MonitoringResult.entered_by),
        joinedload(MonitoringResult.plan_metric).joinedload(
            MonitoringPlanMetric.kpm)
    ).filter(MonitoringResult.result_id == result.result_id).first()

    return _build_result_response(result)


def _build_result_response(result: MonitoringResult) -> dict:
    """Build result response dict."""
    return {
        "result_id": result.result_id,
        "cycle_id": result.cycle_id,
        "plan_metric_id": result.plan_metric_id,
        "model": {
            "model_id": result.model.model_id,
            "model_name": result.model.model_name
        } if result.model else None,
        "numeric_value": result.numeric_value,
        "outcome_value": {
            "value_id": result.outcome_value.value_id,
            "code": result.outcome_value.code,
            "label": result.outcome_value.label
        } if result.outcome_value else None,
        "calculated_outcome": result.calculated_outcome,
        "narrative": result.narrative,
        "supporting_data": result.supporting_data,
        "entered_by": {
            "user_id": result.entered_by.user_id,
            "email": result.entered_by.email,
            "full_name": result.entered_by.full_name
        },
        "entered_at": result.entered_at,
        "updated_at": result.updated_at,
        "metric": {
            "metric_id": result.plan_metric.metric_id,
            "plan_id": result.plan_metric.plan_id,
            "kpm_id": result.plan_metric.kpm_id,
            "yellow_min": result.plan_metric.yellow_min,
            "yellow_max": result.plan_metric.yellow_max,
            "red_min": result.plan_metric.red_min,
            "red_max": result.plan_metric.red_max,
            "qualitative_guidance": result.plan_metric.qualitative_guidance,
            "sort_order": result.plan_metric.sort_order,
            "is_active": result.plan_metric.is_active,
            "kpm": {
                "kpm_id": result.plan_metric.kpm.kpm_id,
                "name": result.plan_metric.kpm.name,
                "category_id": result.plan_metric.kpm.category_id,
                "evaluation_type": result.plan_metric.kpm.evaluation_type
            }
        } if result.plan_metric else None
    }


@router.get("/monitoring/cycles/{cycle_id}/results", response_model=list[MonitoringResultListResponse])
def list_cycle_results(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all results for a cycle."""
    cycle = db.query(MonitoringCycle).filter(
        MonitoringCycle.cycle_id == cycle_id).first()
    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    results = db.query(MonitoringResult).options(
        joinedload(MonitoringResult.model),
        joinedload(MonitoringResult.entered_by),
        joinedload(MonitoringResult.plan_metric).joinedload(
            MonitoringPlanMetric.kpm)
    ).filter(MonitoringResult.cycle_id == cycle_id).all()

    return [
        {
            "result_id": r.result_id,
            "cycle_id": r.cycle_id,
            "plan_metric_id": r.plan_metric_id,
            "model_id": r.model_id,
            "model_name": r.model.model_name if r.model else None,
            "metric_name": r.plan_metric.kpm.name if r.plan_metric and r.plan_metric.kpm else "Unknown",
            "numeric_value": r.numeric_value,
            "calculated_outcome": r.calculated_outcome,
            "entered_by_name": r.entered_by.full_name,
            "entered_at": r.entered_at
        }
        for r in results
    ]


@router.patch("/monitoring/results/{result_id}", response_model=MonitoringResultResponse)
def update_monitoring_result(
    result_id: int,
    update_data: MonitoringResultUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a monitoring result."""
    result = db.query(MonitoringResult).options(
        joinedload(MonitoringResult.cycle),
        joinedload(MonitoringResult.plan_metric).joinedload(
            MonitoringPlanMetric.kpm)
    ).filter(MonitoringResult.result_id == result_id).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    # Check cycle edit permission
    check_cycle_edit_permission(db, result.cycle_id, current_user)

    # Can only update when cycle is in DATA_COLLECTION or UNDER_REVIEW
    if result.cycle.status not in [MonitoringCycleStatus.DATA_COLLECTION.value, MonitoringCycleStatus.UNDER_REVIEW.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update results when cycle is in {result.cycle.status} status"
        )

    changes = {}

    # Use model_fields_set to check which fields were explicitly provided (including null)
    provided_fields = update_data.model_fields_set

    if "numeric_value" in provided_fields:
        if result.numeric_value != update_data.numeric_value:
            changes["numeric_value"] = {
                "old": result.numeric_value, "new": update_data.numeric_value}
        result.numeric_value = update_data.numeric_value
        # Recalculate outcome (or clear if value is now null)
        if result.plan_metric.kpm.evaluation_type == "Quantitative":
            if update_data.numeric_value is not None:
                result.calculated_outcome = calculate_outcome(
                    update_data.numeric_value, result.plan_metric)
            else:
                result.calculated_outcome = None

    if "outcome_value_id" in provided_fields:
        if result.outcome_value_id != update_data.outcome_value_id:
            changes["outcome_value_id"] = {
                "old": result.outcome_value_id, "new": update_data.outcome_value_id}
        result.outcome_value_id = update_data.outcome_value_id
        # Update calculated outcome from taxonomy value (or clear if null)
        if update_data.outcome_value_id is not None:
            outcome_value = db.query(TaxonomyValue).filter(
                TaxonomyValue.value_id == update_data.outcome_value_id
            ).first()
            if outcome_value:
                result.calculated_outcome = outcome_value.code
        else:
            result.calculated_outcome = None

    if "narrative" in provided_fields:
        if result.narrative != update_data.narrative:
            changes["narrative"] = {"old": result.narrative[:100] if result.narrative else None,
                                    "new": update_data.narrative[:100] if update_data.narrative else None}
        result.narrative = update_data.narrative

    if "supporting_data" in provided_fields:
        result.supporting_data = update_data.supporting_data

    if changes:
        create_audit_log(
            db=db,
            entity_type="MonitoringResult",
            entity_id=result_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()

    # Reload with relationships
    result = db.query(MonitoringResult).options(
        joinedload(MonitoringResult.model),
        joinedload(MonitoringResult.outcome_value),
        joinedload(MonitoringResult.entered_by),
        joinedload(MonitoringResult.plan_metric).joinedload(
            MonitoringPlanMetric.kpm)
    ).filter(MonitoringResult.result_id == result_id).first()

    return _build_result_response(result)


@router.delete("/monitoring/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitoring_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a monitoring result."""
    result = db.query(MonitoringResult).options(
        joinedload(MonitoringResult.cycle),
        joinedload(MonitoringResult.plan_metric).joinedload(
            MonitoringPlanMetric.kpm)
    ).filter(MonitoringResult.result_id == result_id).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    # Check cycle edit permission
    check_cycle_edit_permission(db, result.cycle_id, current_user)

    # Can only delete when cycle is in DATA_COLLECTION or UNDER_REVIEW
    if result.cycle.status not in [MonitoringCycleStatus.DATA_COLLECTION.value, MonitoringCycleStatus.UNDER_REVIEW.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete results when cycle is in {result.cycle.status} status"
        )

    create_audit_log(
        db=db,
        entity_type="MonitoringResult",
        entity_id=result_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "cycle_id": result.cycle_id,
            "metric_name": result.plan_metric.kpm.name if result.plan_metric and result.plan_metric.kpm else "Unknown"
        }
    )

    db.delete(result)
    db.commit()
    return None


# ============================================================================
# WORKFLOW ENDPOINTS
# ============================================================================

@router.post("/monitoring/cycles/{cycle_id}/start", response_model=MonitoringCycleResponse)
def start_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Move cycle from PENDING to DATA_COLLECTION.

    When starting a cycle, it is locked to the current active version of the plan.
    This ensures that metrics/thresholds used for this cycle remain consistent
    even if the plan is updated later.

    Only Admin or monitoring team members (risk function) can start a cycle.
    Data providers cannot start cycles - they can only submit results.
    """
    cycle = check_team_member_or_admin(db, cycle_id, current_user)

    if cycle.status != MonitoringCycleStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only start a cycle in PENDING status (current: {cycle.status})"
        )

    # Get active version for this plan (required for version locking)
    # Use SELECT FOR UPDATE to prevent race condition with concurrent version publishing
    active_version = db.query(MonitoringPlanVersion).filter(
        MonitoringPlanVersion.plan_id == cycle.plan_id,
        MonitoringPlanVersion.is_active == True
    ).with_for_update(skip_locked=False).first()

    if not active_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start cycle: No published version exists for this plan. Please publish a version first."
        )

    # Lock cycle to active version
    cycle.plan_version_id = active_version.version_id
    cycle.version_locked_at = datetime.utcnow()
    cycle.version_locked_by_user_id = current_user.user_id
    cycle.status = MonitoringCycleStatus.DATA_COLLECTION.value

    create_audit_log(
        db=db,
        entity_type="MonitoringCycle",
        entity_id=cycle_id,
        action="STATUS_CHANGE",
        user_id=current_user.user_id,
        changes={
            "status": {"old": "PENDING", "new": "DATA_COLLECTION"},
            "version_locked": {
                "version_id": active_version.version_id,
                "version_number": active_version.version_number
            }
        }
    )

    db.commit()
    return get_monitoring_cycle(cycle_id, db, current_user)


@router.post("/monitoring/cycles/{cycle_id}/submit", response_model=MonitoringCycleResponse)
def submit_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Move cycle from DATA_COLLECTION to UNDER_REVIEW.

    Data providers, assignees, team members, and Admins can submit.
    Before submitting, validates that results are complete:
    - At least one result must be entered
    - Metrics without values must have a narrative explaining why
    """
    cycle = check_cycle_edit_permission(db, cycle_id, current_user)

    if cycle.status != MonitoringCycleStatus.DATA_COLLECTION.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only submit a cycle in DATA_COLLECTION status (current: {cycle.status})"
        )

    # Validate results completeness before submission
    validate_results_completeness(db, cycle)

    cycle.status = MonitoringCycleStatus.UNDER_REVIEW.value
    cycle.submitted_at = datetime.utcnow()
    cycle.submitted_by_user_id = current_user.user_id

    create_audit_log(
        db=db,
        entity_type="MonitoringCycle",
        entity_id=cycle_id,
        action="STATUS_CHANGE",
        user_id=current_user.user_id,
        changes={"status": {"old": "DATA_COLLECTION", "new": "UNDER_REVIEW"}}
    )

    db.commit()
    return get_monitoring_cycle(cycle_id, db, current_user)


@router.post("/monitoring/cycles/{cycle_id}/cancel", response_model=MonitoringCycleResponse)
def cancel_cycle(
    cycle_id: int,
    cancel_data: CycleCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a cycle (with reason).

    Only Admin or monitoring team members (risk function) can cancel a cycle.
    Data providers cannot cancel cycles.
    """
    cycle = check_team_member_or_admin(db, cycle_id, current_user)

    if cycle.status == MonitoringCycleStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel an approved cycle"
        )

    old_status = cycle.status
    cycle.status = MonitoringCycleStatus.CANCELLED.value
    cycle.notes = f"[CANCELLED] {cancel_data.cancel_reason}" + \
        (f"\n\n{cycle.notes}" if cycle.notes else "")

    create_audit_log(
        db=db,
        entity_type="MonitoringCycle",
        entity_id=cycle_id,
        action="STATUS_CHANGE",
        user_id=current_user.user_id,
        changes={
            "status": {"old": old_status, "new": "CANCELLED"},
            "cancel_reason": cancel_data.cancel_reason
        }
    )

    db.commit()
    return get_monitoring_cycle(cycle_id, db, current_user)


# ============================================================================
# APPROVAL WORKFLOW ENDPOINTS
# ============================================================================

def _can_user_approve_approval(
    approval: MonitoringCycleApproval,
    current_user: User,
    team_member_ids: List[int],
    user_region_ids: List[int]
) -> bool:
    """Check if the current user can approve this specific approval.

    - Approval must be pending and not voided
    - For Global: Admin OR user with 'Global Approver' role
    - For Regional: Admin OR user with 'Regional Approver' role AND authorized for the region
    """
    # Can't approve if already approved or voided
    if approval.approval_status != "Pending":
        return False
    if approval.voided_at:
        return False

    # Admin can always approve (on behalf of the appropriate role with evidence)
    if current_user.role == UserRole.ADMIN:
        return True

    if approval.approval_type == "Global":
        # User must have Global Approver role
        return current_user.role == UserRole.GLOBAL_APPROVER
    elif approval.approval_type == "Regional":
        # User must have Regional Approver role AND be authorized for this region
        if current_user.role != UserRole.REGIONAL_APPROVER:
            return False
        return approval.region_id in user_region_ids

    return False


def _build_approval_response(approval: MonitoringCycleApproval, can_approve: bool = False) -> dict:
    """Build approval response dict."""
    # Determine if this was a proxy approval (Admin approving on behalf)
    is_proxy_approval = (
        approval.approval_evidence is not None and
        approval.approver is not None and
        approval.approver.role == UserRole.ADMIN
    )

    return {
        "approval_id": approval.approval_id,
        "cycle_id": approval.cycle_id,
        "approval_type": approval.approval_type,
        "region": {
            "region_id": approval.region.region_id,
            "region_name": approval.region.name,
            "region_code": approval.region.code
        } if approval.region else None,
        "approver": {
            "user_id": approval.approver.user_id,
            "email": approval.approver.email,
            "full_name": approval.approver.full_name
        } if approval.approver else None,
        "represented_region": {
            "region_id": approval.represented_region.region_id,
            "region_name": approval.represented_region.name,
            "region_code": approval.represented_region.code
        } if approval.represented_region else None,
        "is_required": approval.is_required,
        "approval_status": approval.approval_status,
        "comments": approval.comments,
        "approved_at": approval.approved_at,
        "approval_evidence": approval.approval_evidence,
        "is_proxy_approval": is_proxy_approval,
        "voided_by": {
            "user_id": approval.voided_by.user_id,
            "email": approval.voided_by.email,
            "full_name": approval.voided_by.full_name
        } if approval.voided_by else None,
        "void_reason": approval.void_reason,
        "voided_at": approval.voided_at,
        "created_at": approval.created_at,
        "can_approve": can_approve
    }


@router.post("/monitoring/cycles/{cycle_id}/request-approval", response_model=MonitoringCycleResponse)
def request_cycle_approval(
    cycle_id: int,
    request_data: CycleRequestApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Move cycle from UNDER_REVIEW to PENDING_APPROVAL and create approval requirements.

    Auto-generates approval requirements based on:
    - Global approval (always required)
    - Regional approvals based on regions of models in the plan scope

    Requires a report_url to the final monitoring report document that approvers will review.

    Only Admin or monitoring team members (risk function) can request approval.
    Data providers cannot advance to approval stage.
    """
    cycle = check_team_member_or_admin(db, cycle_id, current_user)

    if cycle.status != MonitoringCycleStatus.UNDER_REVIEW.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only request approval for a cycle in UNDER_REVIEW status (current: {cycle.status})"
        )

    # Get the plan with models to determine regions
    plan = db.query(MonitoringPlan).options(
        joinedload(MonitoringPlan.models)
    ).filter(MonitoringPlan.plan_id == cycle.plan_id).first()

    # Collect unique regions from models in the plan scope that require regional approval
    regions_needing_approval = set()
    for model in plan.models:
        # Get model's regions through model_regions table
        from app.models.model_region import ModelRegion
        model_regions = db.query(ModelRegion).filter(
            ModelRegion.model_id == model.model_id
        ).all()

        for mr in model_regions:
            region = db.query(Region).filter(
                Region.region_id == mr.region_id).first()
            if region and region.requires_regional_approval:
                regions_needing_approval.add(region.region_id)

    # Check if Global approval already exists (shouldn't but handle gracefully)
    existing_global = db.query(MonitoringCycleApproval).filter(
        MonitoringCycleApproval.cycle_id == cycle_id,
        MonitoringCycleApproval.approval_type == "Global"
    ).first()

    if not existing_global:
        # Create Global approval requirement
        global_approval = MonitoringCycleApproval(
            cycle_id=cycle_id,
            approval_type="Global",
            is_required=True,
            approval_status="Pending"
        )
        db.add(global_approval)

    # Create Regional approval requirements
    for region_id in regions_needing_approval:
        existing_regional = db.query(MonitoringCycleApproval).filter(
            MonitoringCycleApproval.cycle_id == cycle_id,
            MonitoringCycleApproval.approval_type == "Regional",
            MonitoringCycleApproval.region_id == region_id
        ).first()

        if not existing_regional:
            regional_approval = MonitoringCycleApproval(
                cycle_id=cycle_id,
                approval_type="Regional",
                region_id=region_id,
                is_required=True,
                approval_status="Pending"
            )
            db.add(regional_approval)

    # Reset any Rejected approvals to Pending for re-review
    rejected_approvals = db.query(MonitoringCycleApproval).filter(
        MonitoringCycleApproval.cycle_id == cycle_id,
        MonitoringCycleApproval.approval_status == "Rejected"
    ).all()

    for approval in rejected_approvals:
        approval.approval_status = "Pending"
        approval.approver_id = None
        approval.approved_at = None
        approval.comments = None

    # Update cycle status and store report URL
    cycle.status = MonitoringCycleStatus.PENDING_APPROVAL.value
    cycle.report_url = request_data.report_url

    create_audit_log(
        db=db,
        entity_type="MonitoringCycle",
        entity_id=cycle_id,
        action="STATUS_CHANGE",
        user_id=current_user.user_id,
        changes={
            "status": {"old": "UNDER_REVIEW", "new": "PENDING_APPROVAL"},
            "report_url": request_data.report_url,
            "regional_approvals_created": list(regions_needing_approval)
        }
    )

    db.commit()
    return get_monitoring_cycle(cycle_id, db, current_user)


@router.get("/monitoring/cycles/{cycle_id}/approvals", response_model=List[MonitoringCycleApprovalResponse])
def list_cycle_approvals(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all approval requirements for a cycle with can_approve permissions."""
    cycle = db.query(MonitoringCycle).filter(
        MonitoringCycle.cycle_id == cycle_id).first()
    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    approvals = db.query(MonitoringCycleApproval).options(
        joinedload(MonitoringCycleApproval.approver),
        joinedload(MonitoringCycleApproval.region),
        joinedload(MonitoringCycleApproval.represented_region),
        joinedload(MonitoringCycleApproval.voided_by)
    ).filter(
        MonitoringCycleApproval.cycle_id == cycle_id
    ).order_by(
        MonitoringCycleApproval.approval_type,
        MonitoringCycleApproval.region_id
    ).all()

    # Only calculate can_approve if cycle is in PENDING_APPROVAL status
    if cycle.status != MonitoringCycleStatus.PENDING_APPROVAL.value:
        return [_build_approval_response(a, can_approve=False) for a in approvals]

    # Get team member IDs for Global approval permission check
    plan = db.query(MonitoringPlan).options(
        joinedload(MonitoringPlan.team).joinedload(MonitoringTeam.members)
    ).filter(MonitoringPlan.plan_id == cycle.plan_id).first()

    team_member_ids = []
    if plan and plan.team:
        team_member_ids = [m.user_id for m in plan.team.members]

    # Get current user's region IDs for Regional approval permission check
    user_region_ids = [r.region_id for r in current_user.regions]

    # Build responses with can_approve calculated for each approval
    return [
        _build_approval_response(
            a,
            can_approve=_can_user_approve_approval(
                a, current_user, team_member_ids, user_region_ids)
        )
        for a in approvals
    ]


def _check_and_complete_cycle(db: Session, cycle: MonitoringCycle, current_user: User):
    """Check if all required approvals are complete and auto-transition to APPROVED."""
    # Get all required approvals that aren't voided
    required_approvals = db.query(MonitoringCycleApproval).filter(
        MonitoringCycleApproval.cycle_id == cycle.cycle_id,
        MonitoringCycleApproval.is_required == True,
        MonitoringCycleApproval.voided_at == None
    ).all()

    # Check if all are approved
    all_approved = all(a.approval_status ==
                       "Approved" for a in required_approvals)

    if all_approved and required_approvals:
        cycle.status = MonitoringCycleStatus.APPROVED.value
        cycle.completed_at = datetime.utcnow()
        cycle.completed_by_user_id = current_user.user_id

        create_audit_log(
            db=db,
            entity_type="MonitoringCycle",
            entity_id=cycle.cycle_id,
            action="STATUS_CHANGE",
            user_id=current_user.user_id,
            changes={
                "status": {"old": "PENDING_APPROVAL", "new": "APPROVED"},
                "reason": "All required approvals completed"
            }
        )


@router.post("/monitoring/cycles/{cycle_id}/approvals/{approval_id}/approve", response_model=MonitoringCycleApprovalResponse)
def approve_cycle(
    cycle_id: int,
    approval_id: int,
    approval_data: ApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a monitoring cycle approval requirement.

    For Global approvals: User must have 'Global Approver' role OR be Admin.
    For Regional approvals: User must have 'Regional Approver' role AND be
        authorized for that region, OR be Admin.

    Admin users can approve on behalf of the appropriate role by providing
    approval_evidence (description of meeting minutes, email confirmation, etc.).
    """
    approval = db.query(MonitoringCycleApproval).options(
        joinedload(MonitoringCycleApproval.cycle),
        joinedload(MonitoringCycleApproval.region)
    ).filter(
        MonitoringCycleApproval.approval_id == approval_id,
        MonitoringCycleApproval.cycle_id == cycle_id
    ).first()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")

    if approval.cycle.status != MonitoringCycleStatus.PENDING_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve when cycle is in PENDING_APPROVAL status"
        )

    if approval.approval_status == "Approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval has already been granted"
        )

    if approval.voided_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval requirement has been voided"
        )

    # Check permission to approve
    represented_region_id = None
    is_proxy_approval = False

    if approval.approval_type == "Global":
        # User must have Global Approver role OR be Admin
        if current_user.role == UserRole.ADMIN:
            # Admin approving on behalf - require evidence
            if not approval_data.approval_evidence:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Admin must provide approval_evidence when approving on behalf (e.g., meeting minutes, email confirmation)"
                )
            is_proxy_approval = True
        elif current_user.role == UserRole.GLOBAL_APPROVER:
            # Global Approver has direct authority
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with 'Global Approver' role or Admin can approve Global approvals"
            )

    elif approval.approval_type == "Regional":
        # User must have Regional Approver role AND be authorized for this region, OR be Admin
        if current_user.role == UserRole.ADMIN:
            # Admin approving on behalf - require evidence
            if not approval_data.approval_evidence:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Admin must provide approval_evidence when approving on behalf (e.g., meeting minutes, email confirmation)"
                )
            is_proxy_approval = True
        elif current_user.role == UserRole.REGIONAL_APPROVER:
            # Check if user is authorized for this region
            user_region_ids = [r.region_id for r in current_user.regions]
            if approval.region_id not in user_region_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You are not authorized for region {approval.region.name if approval.region else approval.region_id}"
                )
            represented_region_id = approval.region_id
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with 'Regional Approver' role (with authorized regions) or Admin can approve Regional approvals"
            )

    # Record the approval
    approval.approver_id = current_user.user_id
    approval.approval_status = "Approved"
    approval.comments = approval_data.comments
    approval.approved_at = datetime.utcnow()
    approval.represented_region_id = represented_region_id
    approval.approval_evidence = approval_data.approval_evidence if is_proxy_approval else None

    # Build audit log changes
    audit_changes = {
        "cycle_id": cycle_id,
        "approval_type": approval.approval_type,
        "region": approval.region.name if approval.region else None,
        "comments": approval_data.comments
    }
    if is_proxy_approval:
        audit_changes["proxy_approval"] = True
        audit_changes["approval_evidence"] = approval_data.approval_evidence

    create_audit_log(
        db=db,
        entity_type="MonitoringCycleApproval",
        entity_id=approval_id,
        action="APPROVE",
        user_id=current_user.user_id,
        changes=audit_changes
    )

    # Check if all approvals complete
    _check_and_complete_cycle(db, approval.cycle, current_user)

    db.commit()

    # Reload with relationships
    approval = db.query(MonitoringCycleApproval).options(
        joinedload(MonitoringCycleApproval.approver),
        joinedload(MonitoringCycleApproval.region),
        joinedload(MonitoringCycleApproval.represented_region),
        joinedload(MonitoringCycleApproval.voided_by)
    ).filter(MonitoringCycleApproval.approval_id == approval_id).first()

    return _build_approval_response(approval)


@router.post("/monitoring/cycles/{cycle_id}/approvals/{approval_id}/reject", response_model=MonitoringCycleApprovalResponse)
def reject_cycle_approval(
    cycle_id: int,
    approval_id: int,
    reject_data: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a monitoring cycle approval and return cycle to UNDER_REVIEW.

    Rejection requires a comment explaining the reason.
    """
    approval = db.query(MonitoringCycleApproval).options(
        joinedload(MonitoringCycleApproval.cycle),
        joinedload(MonitoringCycleApproval.region)
    ).filter(
        MonitoringCycleApproval.approval_id == approval_id,
        MonitoringCycleApproval.cycle_id == cycle_id
    ).first()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")

    if approval.cycle.status != MonitoringCycleStatus.PENDING_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only reject when cycle is in PENDING_APPROVAL status"
        )

    if approval.voided_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval requirement has been voided"
        )

    # Check permission (same as approve)
    if approval.approval_type == "Global":
        if current_user.role != UserRole.ADMIN:
            plan = db.query(MonitoringPlan).options(
                joinedload(MonitoringPlan.team).joinedload(
                    MonitoringTeam.members)
            ).filter(MonitoringPlan.plan_id == approval.cycle.plan_id).first()

            if not plan or not plan.team:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Admin or team members can reject Global approvals"
                )

            member_ids = [m.user_id for m in plan.team.members]
            if current_user.user_id not in member_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Admin or team members can reject Global approvals"
                )

    elif approval.approval_type == "Regional":
        if current_user.role != UserRole.ADMIN:
            user_region_ids = [r.region_id for r in current_user.regions]
            if approval.region_id not in user_region_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You are not an approver for region {approval.region.name if approval.region else approval.region_id}"
                )

    # Record the rejection
    approval.approver_id = current_user.user_id
    approval.approval_status = "Rejected"
    approval.comments = reject_data.comments
    approval.approved_at = datetime.utcnow()

    # Return cycle to UNDER_REVIEW for corrections
    old_status = approval.cycle.status
    approval.cycle.status = MonitoringCycleStatus.UNDER_REVIEW.value

    # Reset all approvals to Pending for re-review
    all_approvals = db.query(MonitoringCycleApproval).filter(
        MonitoringCycleApproval.cycle_id == cycle_id,
        MonitoringCycleApproval.voided_at == None
    ).all()

    for a in all_approvals:
        if a.approval_id != approval_id:  # Don't reset the one being rejected
            a.approval_status = "Pending"
            a.approver_id = None
            a.approved_at = None
            a.comments = None

    create_audit_log(
        db=db,
        entity_type="MonitoringCycleApproval",
        entity_id=approval_id,
        action="REJECT",
        user_id=current_user.user_id,
        changes={
            "cycle_id": cycle_id,
            "approval_type": approval.approval_type,
            "region": approval.region.name if approval.region else None,
            "comments": reject_data.comments,
            "cycle_status_change": {"old": old_status, "new": "UNDER_REVIEW"}
        }
    )

    db.commit()

    # Reload with relationships
    approval = db.query(MonitoringCycleApproval).options(
        joinedload(MonitoringCycleApproval.approver),
        joinedload(MonitoringCycleApproval.region),
        joinedload(MonitoringCycleApproval.represented_region),
        joinedload(MonitoringCycleApproval.voided_by)
    ).filter(MonitoringCycleApproval.approval_id == approval_id).first()

    return _build_approval_response(approval)


@router.post("/monitoring/cycles/{cycle_id}/approvals/{approval_id}/void", response_model=MonitoringCycleApprovalResponse)
def void_cycle_approval(
    cycle_id: int,
    approval_id: int,
    void_data: VoidApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Void an approval requirement (Admin only).

    Voiding removes the requirement without completing it.
    Used when a regional approval is no longer applicable.
    """
    approval = db.query(MonitoringCycleApproval).options(
        joinedload(MonitoringCycleApproval.cycle),
        joinedload(MonitoringCycleApproval.region)
    ).filter(
        MonitoringCycleApproval.approval_id == approval_id,
        MonitoringCycleApproval.cycle_id == cycle_id
    ).first()

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")

    if approval.voided_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval has already been voided"
        )

    if approval.approval_status == "Approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot void an approval that has already been granted"
        )

    # Void the approval
    approval.voided_by_id = current_user.user_id
    approval.void_reason = void_data.void_reason
    approval.voided_at = datetime.utcnow()
    approval.approval_status = "Voided"

    create_audit_log(
        db=db,
        entity_type="MonitoringCycleApproval",
        entity_id=approval_id,
        action="VOID",
        user_id=current_user.user_id,
        changes={
            "cycle_id": cycle_id,
            "approval_type": approval.approval_type,
            "region": approval.region.name if approval.region else None,
            "void_reason": void_data.void_reason
        }
    )

    # Check if all remaining approvals are complete
    _check_and_complete_cycle(db, approval.cycle, current_user)

    db.commit()

    # Reload with relationships
    approval = db.query(MonitoringCycleApproval).options(
        joinedload(MonitoringCycleApproval.approver),
        joinedload(MonitoringCycleApproval.region),
        joinedload(MonitoringCycleApproval.represented_region),
        joinedload(MonitoringCycleApproval.voided_by)
    ).filter(MonitoringCycleApproval.approval_id == approval_id).first()

    return _build_approval_response(approval)


# ============================================================================
# PHASE 7: REPORTING & TRENDS
# ============================================================================

@router.get("/monitoring/metrics/{plan_metric_id}/trend", response_model=MetricTrendResponse)
def get_metric_trend(
    plan_metric_id: int,
    model_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get time series trend data for a specific metric.

    Returns results across completed cycles for trend analysis.
    Optionally filter by model for multi-model plans.
    """
    # Get the metric with KPM info
    metric = db.query(MonitoringPlanMetric).options(
        joinedload(MonitoringPlanMetric.kpm).joinedload(Kpm.category)
    ).filter(MonitoringPlanMetric.metric_id == plan_metric_id).first()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Metric not found")

    # Build query for results
    query = db.query(MonitoringResult).join(
        MonitoringCycle
    ).filter(
        MonitoringResult.plan_metric_id == plan_metric_id,
        MonitoringCycle.status.in_([MonitoringCycleStatus.APPROVED.value,
                                   MonitoringCycleStatus.PENDING_APPROVAL.value, MonitoringCycleStatus.UNDER_REVIEW.value])
    )

    if model_id:
        query = query.filter(MonitoringResult.model_id == model_id)

    if start_date:
        query = query.filter(MonitoringCycle.period_end_date >= start_date)

    if end_date:
        query = query.filter(MonitoringCycle.period_end_date <= end_date)

    results = query.options(
        joinedload(MonitoringResult.cycle),
        joinedload(MonitoringResult.model)
    ).order_by(MonitoringCycle.period_end_date.asc()).all()

    # Build trend data points
    data_points = []
    for result in results:
        data_points.append(MetricTrendPoint(
            cycle_id=result.cycle_id,
            period_end_date=result.cycle.period_end_date,
            numeric_value=result.numeric_value,
            calculated_outcome=result.calculated_outcome,
            model_id=result.model_id,
            model_name=result.model.model_name if result.model else None
        ))

    return MetricTrendResponse(
        plan_metric_id=plan_metric_id,
        metric_name=f"{metric.kpm.category.name}: {metric.kpm.name}" if metric.kpm.category else metric.kpm.name,
        kpm_name=metric.kpm.name,
        evaluation_type=metric.kpm.evaluation_type or "Quantitative",
        yellow_min=metric.yellow_min,
        yellow_max=metric.yellow_max,
        red_min=metric.red_min,
        red_max=metric.red_max,
        data_points=data_points
    )


@router.get("/monitoring/plans/{plan_id}/performance-summary", response_model=PerformanceSummary)
def get_performance_summary(
    plan_id: int,
    cycles: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get aggregate performance summary across recent cycles.

    Provides outcome distribution (GREEN/YELLOW/RED) for the last N cycles.
    """
    # Verify plan exists
    plan = db.query(MonitoringPlan).filter(
        MonitoringPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    # Get recent completed/in-review cycles
    recent_cycles = db.query(MonitoringCycle).filter(
        MonitoringCycle.plan_id == plan_id,
        MonitoringCycle.status.in_([MonitoringCycleStatus.APPROVED.value,
                                   MonitoringCycleStatus.PENDING_APPROVAL.value, MonitoringCycleStatus.UNDER_REVIEW.value])
    ).order_by(MonitoringCycle.period_end_date.desc()).limit(cycles).all()

    if not recent_cycles:
        return PerformanceSummary(
            total_results=0,
            green_count=0,
            yellow_count=0,
            red_count=0,
            na_count=0,
            by_metric=[]
        )

    cycle_ids = [c.cycle_id for c in recent_cycles]

    # Get all results for these cycles
    results = db.query(MonitoringResult).filter(
        MonitoringResult.cycle_id.in_(cycle_ids)
    ).all()

    # Count outcomes
    total = len(results)
    green_count = sum(1 for r in results if r.calculated_outcome == "GREEN")
    yellow_count = sum(1 for r in results if r.calculated_outcome == "YELLOW")
    red_count = sum(1 for r in results if r.calculated_outcome == "RED")
    na_count = sum(1 for r in results if r.calculated_outcome ==
                   "N/A" or r.calculated_outcome is None)

    # Group by metric for breakdown
    metric_outcomes = {}
    for result in results:
        metric_id = result.plan_metric_id
        if metric_id not in metric_outcomes:
            metric_outcomes[metric_id] = {
                "green": 0, "yellow": 0, "red": 0, "na": 0}

        if result.calculated_outcome == "GREEN":
            metric_outcomes[metric_id]["green"] += 1
        elif result.calculated_outcome == "YELLOW":
            metric_outcomes[metric_id]["yellow"] += 1
        elif result.calculated_outcome == "RED":
            metric_outcomes[metric_id]["red"] += 1
        else:
            metric_outcomes[metric_id]["na"] += 1

    # Get metric names
    metrics = db.query(MonitoringPlanMetric).options(
        joinedload(MonitoringPlanMetric.kpm)
    ).filter(
        MonitoringPlanMetric.metric_id.in_(metric_outcomes.keys())
    ).all()

    metric_name_map = {m.metric_id: m.kpm.name for m in metrics}

    by_metric = []
    for metric_id, counts in metric_outcomes.items():
        by_metric.append({
            "metric_id": metric_id,
            "metric_name": metric_name_map.get(metric_id, f"Metric {metric_id}"),
            "green_count": counts["green"],
            "yellow_count": counts["yellow"],
            "red_count": counts["red"],
            "na_count": counts["na"],
            "total": sum(counts.values())
        })

    return PerformanceSummary(
        total_results=total,
        green_count=green_count,
        yellow_count=yellow_count,
        red_count=red_count,
        na_count=na_count,
        by_metric=by_metric
    )


@router.get("/monitoring/plans/{plan_id}/cycles/{cycle_id}/export")
def export_cycle_results(
    plan_id: int,
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export cycle results to CSV format.

    Returns CSV with all metric results for the cycle.
    """
    from fastapi.responses import Response
    import csv
    import io

    # Verify cycle belongs to plan
    cycle = db.query(MonitoringCycle).filter(
        MonitoringCycle.cycle_id == cycle_id,
        MonitoringCycle.plan_id == plan_id
    ).first()

    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    # Get all results with metric and model info
    results = db.query(MonitoringResult).options(
        joinedload(MonitoringResult.model),
        joinedload(MonitoringResult.entered_by),
        joinedload(MonitoringResult.plan_metric).joinedload(
            MonitoringPlanMetric.kpm).joinedload(Kpm.category)
    ).filter(
        MonitoringResult.cycle_id == cycle_id
    ).order_by(MonitoringResult.plan_metric_id).all()

    # Get plan name for filename
    plan = db.query(MonitoringPlan).filter(
        MonitoringPlan.plan_id == plan_id).first()

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Category",
        "Metric",
        "Model",
        "Numeric Value",
        "Outcome",
        "Narrative",
        "Entered By",
        "Entered At"
    ])

    # Data rows
    for result in results:
        metric = result.plan_metric
        writer.writerow([
            metric.kpm.category.name if metric and metric.kpm and metric.kpm.category else "",
            metric.kpm.name if metric and metric.kpm else f"Metric {result.plan_metric_id}",
            result.model.model_name if result.model else "All Models",
            result.numeric_value if result.numeric_value is not None else "",
            result.calculated_outcome or "N/A",
            result.narrative or "",
            result.entered_by.full_name if result.entered_by else "",
            result.entered_at.strftime(
                "%Y-%m-%d %H:%M") if result.entered_at else ""
        ])

    csv_content = output.getvalue()

    # Generate filename
    period = f"{cycle.period_start_date.strftime('%Y%m%d')}-{cycle.period_end_date.strftime('%Y%m%d')}"
    filename = f"{plan.name.replace(' ', '_')}_Cycle_{period}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

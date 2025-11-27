"""Monitoring Plans and Teams routes."""
from typing import List, Optional
from datetime import date, timedelta
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
from app.models.monitoring import (
    MonitoringTeam,
    MonitoringPlan,
    MonitoringPlanMetric,
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
        members = db.query(User).filter(User.user_id.in_(team_data.member_ids)).all()
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
            changes["description"] = {"old": team.description, "new": update_data.description}
        team.description = update_data.description

    if update_data.is_active is not None:
        if team.is_active != update_data.is_active:
            changes["is_active"] = {"old": team.is_active, "new": update_data.is_active}
        team.is_active = update_data.is_active

    if update_data.member_ids is not None:
        members = db.query(User).filter(User.user_id.in_(update_data.member_ids)).all()
        team.members = members
        if set(old_member_ids) != set(update_data.member_ids):
            changes["member_ids"] = {"old": old_member_ids, "new": update_data.member_ids}

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
        joinedload(MonitoringPlan.metrics)
    )

    if not include_inactive:
        query = query.filter(MonitoringPlan.is_active == True)

    if team_id:
        query = query.filter(MonitoringPlan.monitoring_team_id == team_id)

    plans = query.order_by(MonitoringPlan.name).all()

    # Filter by model if specified
    if model_id:
        plans = [p for p in plans if any(m.model_id == model_id for m in p.models)]

    result = []
    for plan in plans:
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
            "metric_count": len([m for m in plan.metrics if m.is_active])
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
        joinedload(MonitoringPlan.metrics).joinedload(MonitoringPlanMetric.kpm)
    ).filter(MonitoringPlan.plan_id == plan_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

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
            "plan_count": len([p for p in plan.team.plans if p.is_active])
        } if plan.team else None,
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
                    "evaluation_type": metric.kpm.evaluation_type
                }
            }
            for metric in plan.metrics
        ]
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
    report_date = calculate_report_due_date(submission_date, plan_data.reporting_lead_days)

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
        models = db.query(Model).filter(Model.model_id.in_(plan_data.model_ids)).all()
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
            changes["description"] = {"old": plan.description, "new": update_data.description}
        plan.description = update_data.description

    if update_data.frequency is not None:
        if plan.frequency != update_data.frequency:
            changes["frequency"] = {"old": plan.frequency, "new": update_data.frequency}
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
            changes["monitoring_team_id"] = {"old": plan.monitoring_team_id, "new": new_team_id}
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
            changes["data_provider_user_id"] = {"old": plan.data_provider_user_id, "new": new_provider_id}
        plan.data_provider_user_id = new_provider_id

    if update_data.reporting_lead_days is not None:
        if plan.reporting_lead_days != update_data.reporting_lead_days:
            changes["reporting_lead_days"] = {"old": plan.reporting_lead_days, "new": update_data.reporting_lead_days}
        plan.reporting_lead_days = update_data.reporting_lead_days
        recalculate_dates = True

    if update_data.next_submission_due_date is not None:
        old_date = str(plan.next_submission_due_date) if plan.next_submission_due_date else None
        new_date = str(update_data.next_submission_due_date)
        if old_date != new_date:
            changes["next_submission_due_date"] = {"old": old_date, "new": new_date}
        plan.next_submission_due_date = update_data.next_submission_due_date
        plan.next_report_due_date = calculate_report_due_date(
            update_data.next_submission_due_date, plan.reporting_lead_days
        )
        recalculate_dates = False  # Dates manually set

    if update_data.is_active is not None:
        if plan.is_active != update_data.is_active:
            changes["is_active"] = {"old": plan.is_active, "new": update_data.is_active}
        plan.is_active = update_data.is_active

    if update_data.model_ids is not None:
        models = db.query(Model).filter(Model.model_id.in_(update_data.model_ids)).all()
        plan.models = models
        if set(old_model_ids) != set(update_data.model_ids):
            changes["model_ids"] = {"old": old_model_ids, "new": update_data.model_ids}

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
            changes["kpm_id"] = {"old": metric.kpm_id, "new": update_data.kpm_id}
        metric.kpm_id = update_data.kpm_id

    if update_data.yellow_min is not None:
        if metric.yellow_min != update_data.yellow_min:
            changes["yellow_min"] = {"old": metric.yellow_min, "new": update_data.yellow_min}
        metric.yellow_min = update_data.yellow_min

    if update_data.yellow_max is not None:
        if metric.yellow_max != update_data.yellow_max:
            changes["yellow_max"] = {"old": metric.yellow_max, "new": update_data.yellow_max}
        metric.yellow_max = update_data.yellow_max

    if update_data.red_min is not None:
        if metric.red_min != update_data.red_min:
            changes["red_min"] = {"old": metric.red_min, "new": update_data.red_min}
        metric.red_min = update_data.red_min

    if update_data.red_max is not None:
        if metric.red_max != update_data.red_max:
            changes["red_max"] = {"old": metric.red_max, "new": update_data.red_max}
        metric.red_max = update_data.red_max

    if update_data.qualitative_guidance is not None:
        if metric.qualitative_guidance != update_data.qualitative_guidance:
            changes["qualitative_guidance"] = {"old": metric.qualitative_guidance, "new": update_data.qualitative_guidance}
        metric.qualitative_guidance = update_data.qualitative_guidance

    if update_data.sort_order is not None:
        if metric.sort_order != update_data.sort_order:
            changes["sort_order"] = {"old": metric.sort_order, "new": update_data.sort_order}
        metric.sort_order = update_data.sort_order

    if update_data.is_active is not None:
        if metric.is_active != update_data.is_active:
            changes["is_active"] = {"old": metric.is_active, "new": update_data.is_active}
        metric.is_active = update_data.is_active

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
    old_submission_date = str(plan.next_submission_due_date) if plan.next_submission_due_date else None
    old_report_date = str(plan.next_report_due_date) if plan.next_report_due_date else None

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

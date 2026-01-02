"""Team management API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.core.team_utils import build_lob_team_map, get_all_lob_ids_for_team, get_models_team_map
from app.models.team import Team
from app.models.audit_log import AuditLog
from app.models.lob import LOBUnit
from app.models.model import Model
from app.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate, TeamRead, TeamWithLOBs, LOBUnitBasic
from app.schemas.model import ModelListResponse
from app.api.lob_units import build_tree, get_full_path

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamLOBAssignment(BaseModel):
    lob_id: int


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for team changes."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def _require_admin(user: User) -> None:
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


@router.get("/", response_model=List[TeamRead])
def list_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    teams = db.query(Team).order_by(Team.name).all()

    lob_counts = dict(
        db.query(LOBUnit.team_id, func.count(LOBUnit.lob_id))
        .filter(LOBUnit.team_id.isnot(None))
        .group_by(LOBUnit.team_id)
        .all()
    )

    lob_team_map = build_lob_team_map(db)
    model_owner_lobs = db.query(Model.model_id, User.lob_id).join(
        User, Model.owner_id == User.user_id
    ).all()

    model_counts: dict = {}
    for _, lob_id in model_owner_lobs:
        team_id = lob_team_map.get(lob_id)
        if team_id:
            model_counts[team_id] = model_counts.get(team_id, 0) + 1

    results = []
    for team in teams:
        team_data = TeamRead.model_validate(team).model_dump()
        team_data["lob_count"] = lob_counts.get(team.team_id, 0)
        team_data["model_count"] = model_counts.get(team.team_id, 0)
        results.append(team_data)

    return results


@router.post("/", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(
    team_data: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_admin(current_user)

    existing = db.query(Team).filter(func.lower(Team.name) == team_data.name.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team with this name already exists")

    team = Team(**team_data.model_dump())
    db.add(team)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="Team",
        entity_id=team.team_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "name": team.name,
            "description": team.description,
            "is_active": team.is_active
        }
    )

    db.commit()
    db.refresh(team)

    response = TeamRead.model_validate(team).model_dump()
    response["lob_count"] = 0
    response["model_count"] = 0
    return response


@router.get("/{team_id}", response_model=TeamWithLOBs)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    direct_lobs = db.query(LOBUnit).filter(LOBUnit.team_id == team_id).order_by(
        LOBUnit.level, LOBUnit.name
    ).all()

    lob_units = []
    for lob in direct_lobs:
        lob_units.append(LOBUnitBasic(
            lob_id=lob.lob_id,
            name=lob.name,
            org_unit=lob.org_unit,
            level=lob.level,
            parent_id=lob.parent_id,
            full_path=get_full_path(db, lob),
            is_active=lob.is_active,
        ))

    lob_ids = get_all_lob_ids_for_team(db, team_id)
    model_count = 0
    if lob_ids:
        model_count = db.query(func.count(Model.model_id)).join(
            User, Model.owner_id == User.user_id
        ).filter(User.lob_id.in_(lob_ids)).scalar() or 0

    response = TeamRead.model_validate(team).model_dump()
    response["lob_count"] = len(direct_lobs)
    response["model_count"] = model_count
    response["lob_units"] = [lob.model_dump() for lob in lob_units]
    return response


@router.patch("/{team_id}", response_model=TeamRead)
def update_team(
    team_id: int,
    team_data: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_admin(current_user)

    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    update_data = team_data.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"].lower() != team.name.lower():
        existing = db.query(Team).filter(
            func.lower(Team.name) == update_data["name"].lower(),
            Team.team_id != team_id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team with this name already exists")

    changes = {}
    for field, value in update_data.items():
        old_value = getattr(team, field)
        if old_value != value:
            changes[field] = {"old": old_value, "new": value}
        setattr(team, field, value)

    if changes:
        create_audit_log(
            db=db,
            entity_type="Team",
            entity_id=team.team_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(team)

    response = TeamRead.model_validate(team).model_dump()
    response["lob_count"] = db.query(func.count(LOBUnit.lob_id)).filter(
        LOBUnit.team_id == team_id
    ).scalar() or 0
    response["model_count"] = db.query(Model.model_id).join(
        User, Model.owner_id == User.user_id
    ).filter(User.lob_id.in_(get_all_lob_ids_for_team(db, team_id))).count()
    return response


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_admin(current_user)

    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    if not team.is_active:
        return None

    team.is_active = False
    db.add(team)
    create_audit_log(
        db=db,
        entity_type="Team",
        entity_id=team.team_id,
        action="DEACTIVATE",
        user_id=current_user.user_id,
        changes={"is_active": {"old": True, "new": False}}
    )
    db.commit()
    return None


@router.post("/{team_id}/lobs", response_model=LOBUnitBasic)
def assign_lob_to_team(
    team_id: int,
    assignment: TeamLOBAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_admin(current_user)

    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    lob = db.query(LOBUnit).filter(LOBUnit.lob_id == assignment.lob_id).first()
    if not lob:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LOB unit not found")

    previous_team_id = lob.team_id
    previous_team_name = None
    if previous_team_id and previous_team_id != team_id:
        previous_team = db.query(Team).filter(Team.team_id == previous_team_id).first()
        previous_team_name = previous_team.name if previous_team else None

    lob.team_id = team_id
    db.add(lob)

    if previous_team_id != team_id:
        action = "ASSIGN_LOB" if previous_team_id is None else "REASSIGN_LOB"
        create_audit_log(
            db=db,
            entity_type="Team",
            entity_id=team_id,
            action=action,
            user_id=current_user.user_id,
            changes={
                "lob_id": lob.lob_id,
                "lob_name": lob.name,
                "previous_team_id": previous_team_id,
                "previous_team_name": previous_team_name,
                "new_team_id": team_id,
                "new_team_name": team.name
            }
        )

    db.commit()
    db.refresh(lob)

    return LOBUnitBasic(
        lob_id=lob.lob_id,
        name=lob.name,
        org_unit=lob.org_unit,
        level=lob.level,
        parent_id=lob.parent_id,
        full_path=get_full_path(db, lob),
        is_active=lob.is_active,
    )


@router.delete("/{team_id}/lobs/{lob_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_lob_from_team(
    team_id: int,
    lob_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_admin(current_user)

    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    lob = db.query(LOBUnit).filter(LOBUnit.lob_id == lob_id).first()
    if not lob:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LOB unit not found")

    if lob.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LOB is not assigned to this team")

    previous_team_id = lob.team_id
    lob.team_id = None
    db.add(lob)

    create_audit_log(
        db=db,
        entity_type="Team",
        entity_id=team_id,
        action="REMOVE_LOB",
        user_id=current_user.user_id,
        changes={
            "lob_id": lob.lob_id,
            "lob_name": lob.name,
            "previous_team_id": previous_team_id,
            "previous_team_name": team.name
        }
    )

    db.commit()
    return None


@router.get("/{team_id}/models", response_model=List[ModelListResponse])
def get_team_models(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    lob_ids = get_all_lob_ids_for_team(db, team_id)
    if not lob_ids:
        return []

    from app.api.models import _build_model_list_response
    from app.models.lob import LOBUnit as LOBUnitModel
    from app.models.methodology import Methodology
    from app.models.model_region import ModelRegion
    from app.models.irp import IRP

    models = db.query(Model).options(
        joinedload(Model.owner).joinedload(User.lob).joinedload(LOBUnitModel.parent).joinedload(LOBUnitModel.parent).joinedload(LOBUnitModel.parent),
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
        selectinload(Model.users).joinedload(User.lob),
        selectinload(Model.regulatory_categories),
        selectinload(Model.model_regions).joinedload(ModelRegion.region),
        selectinload(Model.versions),
        selectinload(Model.irps).joinedload(IRP.contact_user)
    ).join(User, Model.owner_id == User.user_id).filter(
        User.lob_id.in_(lob_ids)
    ).all()

    results = [_build_model_list_response(m, False, db) for m in models]
    team_map = get_models_team_map(db, [m.model_id for m in models])
    for item in results:
        item["team"] = team_map.get(item["model_id"])

    return results


@router.get("/{team_id}/lob-tree")
def get_team_lob_tree(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    lob_ids = get_all_lob_ids_for_team(db, team_id)
    if not lob_ids:
        return []

    lobs = db.query(LOBUnit).filter(LOBUnit.lob_id.in_(lob_ids)).all()
    return build_tree(db, lobs, include_inactive=True)

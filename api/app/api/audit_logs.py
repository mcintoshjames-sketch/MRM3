"""Audit logs routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse

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

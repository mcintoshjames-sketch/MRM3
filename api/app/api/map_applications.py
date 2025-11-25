"""MAP Applications API - Search Managed Application Portfolio."""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.map_application import MapApplication
from app.schemas.map_application import MapApplicationResponse, MapApplicationListResponse

router = APIRouter(prefix="/map", tags=["MAP Applications"])


@router.get("/applications", response_model=List[MapApplicationListResponse])
def list_applications(
    search: Optional[str] = Query(None, description="Search by name, code, or description"),
    department: Optional[str] = Query(None, description="Filter by department"),
    status: Optional[str] = Query(None, description="Filter by status (Active, Decommissioned, In Development)"),
    criticality_tier: Optional[str] = Query(None, description="Filter by criticality tier"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search and list applications from the Managed Application Portfolio (MAP).

    This is a read-only endpoint simulating integration with the organization's
    application inventory system.
    """
    query = db.query(MapApplication)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                MapApplication.application_name.ilike(search_term),
                MapApplication.application_code.ilike(search_term),
                MapApplication.description.ilike(search_term),
                MapApplication.owner_name.ilike(search_term)
            )
        )

    # Apply filters
    if department:
        query = query.filter(MapApplication.department == department)
    if status:
        query = query.filter(MapApplication.status == status)
    if criticality_tier:
        query = query.filter(MapApplication.criticality_tier == criticality_tier)

    # Order by name and apply pagination
    query = query.order_by(MapApplication.application_name)
    applications = query.offset(skip).limit(limit).all()

    return applications


@router.get("/applications/{application_id}", response_model=MapApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single application from MAP by ID."""
    application = db.query(MapApplication).filter(
        MapApplication.application_id == application_id
    ).first()

    if not application:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found"
        )

    return application


@router.get("/departments", response_model=List[str])
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of unique departments from MAP applications."""
    departments = db.query(MapApplication.department).distinct().filter(
        MapApplication.department.isnot(None)
    ).order_by(MapApplication.department).all()

    return [d[0] for d in departments]

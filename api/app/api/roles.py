"""Role catalog routes."""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.role import Role
from app.schemas.role import RoleResponse

router = APIRouter()


@router.get("/roles", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """List all active roles for UI consumption."""
    roles = db.query(Role).order_by(Role.display_name.asc()).all()
    return [
        RoleResponse(
            role_id=role.role_id,
            role_code=role.code,
            display_name=role.display_name,
            is_system=role.is_system,
            is_active=role.is_active
        )
        for role in roles
    ]

"""API endpoints for approver roles management."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User, ApproverRole, RuleRequiredApprover
from app.schemas.conditional_approval import (
    ApproverRoleCreate,
    ApproverRoleUpdate,
    ApproverRoleResponse,
    ApproverRoleListResponse
)

router = APIRouter(prefix="/approver-roles", tags=["Approver Roles"])


@router.get("/", response_model=List[ApproverRoleListResponse])
def list_approver_roles(
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all approver roles.

    Query Parameters:
    - is_active: Filter by active status (optional)

    Returns list with count of rules using each role.
    """
    query = db.query(ApproverRole)

    if is_active is not None:
        query = query.filter(ApproverRole.is_active == is_active)

    roles = query.order_by(ApproverRole.role_name).all()

    # Count rules for each role
    result = []
    for role in roles:
        rules_count = db.query(func.count(RuleRequiredApprover.id)).filter(
            RuleRequiredApprover.approver_role_id == role.role_id
        ).scalar()

        result.append(ApproverRoleListResponse(
            role_id=role.role_id,
            role_name=role.role_name,
            description=role.description,
            is_active=role.is_active,
            rules_count=rules_count
        ))

    return result


@router.get("/{role_id}", response_model=ApproverRoleResponse)
def get_approver_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get approver role details by ID."""
    role = db.query(ApproverRole).filter(ApproverRole.role_id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approver role with ID {role_id} not found"
        )

    return role


@router.post("/", response_model=ApproverRoleResponse, status_code=status.HTTP_201_CREATED)
def create_approver_role(
    role_data: ApproverRoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new approver role (Admin only).

    Required fields:
    - role_name: Unique name for the role
    - description: Optional description
    - is_active: Default true
    """
    # Check Admin permission
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can create approver roles"
        )

    # Check for duplicate name
    existing = db.query(ApproverRole).filter(
        ApproverRole.role_name == role_data.role_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approver role with name '{role_data.role_name}' already exists"
        )

    # Create new role
    new_role = ApproverRole(
        role_name=role_data.role_name,
        description=role_data.description,
        is_active=role_data.is_active
    )

    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    return new_role


@router.patch("/{role_id}", response_model=ApproverRoleResponse)
def update_approver_role(
    role_id: int,
    role_data: ApproverRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update approver role (Admin only).

    Allows updating:
    - role_name
    - description
    - is_active (to deactivate roles)
    """
    # Check Admin permission
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can update approver roles"
        )

    # Find role
    role = db.query(ApproverRole).filter(ApproverRole.role_id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approver role with ID {role_id} not found"
        )

    # Update fields
    if role_data.role_name is not None:
        # Check for duplicate name (excluding current role)
        existing = db.query(ApproverRole).filter(
            ApproverRole.role_name == role_data.role_name,
            ApproverRole.role_id != role_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approver role with name '{role_data.role_name}' already exists"
            )
        role.role_name = role_data.role_name

    if role_data.description is not None:
        role.description = role_data.description

    if role_data.is_active is not None:
        role.is_active = role_data.is_active

    db.commit()
    db.refresh(role)

    return role


@router.delete("/{role_id}", status_code=status.HTTP_200_OK)
def delete_approver_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete approver role by setting is_active=false (Admin only).

    Note: Cannot delete roles that are currently used in active rules.
    """
    # Check Admin permission
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can delete approver roles"
        )

    # Find role
    role = db.query(ApproverRole).filter(ApproverRole.role_id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approver role with ID {role_id} not found"
        )

    # Check if used in any active rules
    active_rules_count = db.query(func.count(RuleRequiredApprover.id)).join(
        RuleRequiredApprover.rule
    ).filter(
        RuleRequiredApprover.approver_role_id == role_id,
        RuleRequiredApprover.rule.has(is_active=True)
    ).scalar()

    if active_rules_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role: it is used in {active_rules_count} active rule(s). Deactivate the rules first or deactivate this role instead of deleting it."
        )

    # Soft delete (set is_active=false)
    role.is_active = False
    db.commit()

    return {"message": f"Approver role '{role.role_name}' deactivated successfully"}

"""Validation policies API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.validation import ValidationPolicy
from app.schemas.validation import ValidationPolicyResponse, ValidationPolicyCreate, ValidationPolicyUpdate
from datetime import datetime

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/", response_model=List[ValidationPolicyResponse])
def list_validation_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all validation policies."""
    policies = db.query(ValidationPolicy)\
        .options(joinedload(ValidationPolicy.risk_tier))\
        .all()
    return policies


@router.post("/", response_model=ValidationPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_validation_policy(
    policy_data: ValidationPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new validation policy (Admin only)."""
    # Check if policy already exists for this risk tier
    existing = db.query(ValidationPolicy)\
        .filter(ValidationPolicy.risk_tier_id == policy_data.risk_tier_id)\
        .first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation policy already exists for this risk tier"
        )

    policy = ValidationPolicy(
        risk_tier_id=policy_data.risk_tier_id,
        frequency_months=policy_data.frequency_months,
        model_change_lead_time_days=policy_data.model_change_lead_time_days,
        description=policy_data.description,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return policy


@router.patch("/{policy_id}", response_model=ValidationPolicyResponse)
def update_validation_policy(
    policy_id: int,
    policy_data: ValidationPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update a validation policy (Admin only)."""
    policy = db.query(ValidationPolicy)\
        .options(joinedload(ValidationPolicy.risk_tier))\
        .filter(ValidationPolicy.policy_id == policy_id)\
        .first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation policy not found"
        )

    # Update fields
    if policy_data.frequency_months is not None:
        policy.frequency_months = policy_data.frequency_months
    if policy_data.model_change_lead_time_days is not None:
        policy.model_change_lead_time_days = policy_data.model_change_lead_time_days
    if policy_data.description is not None:
        policy.description = policy_data.description

    policy.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(policy)

    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_validation_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a validation policy (Admin only)."""
    policy = db.query(ValidationPolicy)\
        .filter(ValidationPolicy.policy_id == policy_id)\
        .first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation policy not found"
        )

    db.delete(policy)
    db.commit()

    return None

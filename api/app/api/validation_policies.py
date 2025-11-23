"""Validation policies API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.validation import ValidationPolicy
from app.models.audit_log import AuditLog
from app.schemas.validation import ValidationPolicyResponse, ValidationPolicyCreate, ValidationPolicyUpdate
from datetime import datetime

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for validation policy changes."""
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
    db.flush()  # Get policy_id before creating audit log

    # Create audit log for new policy
    create_audit_log(
        db=db,
        entity_type="ValidationPolicy",
        entity_id=policy.policy_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "risk_tier_id": policy_data.risk_tier_id,
            "frequency_months": policy_data.frequency_months,
            "model_change_lead_time_days": policy_data.model_change_lead_time_days,
            "description": policy_data.description
        }
    )

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

    # Track changes for audit log
    changes = {}

    if policy_data.frequency_months is not None and policy_data.frequency_months != policy.frequency_months:
        # CRITICAL: Frequency changes affect revalidation schedules and compliance timelines
        changes["frequency_months"] = {
            "old": policy.frequency_months,
            "new": policy_data.frequency_months
        }
        policy.frequency_months = policy_data.frequency_months

    if policy_data.model_change_lead_time_days is not None and policy_data.model_change_lead_time_days != policy.model_change_lead_time_days:
        # CRITICAL: Lead time changes affect when changes must be submitted for validation
        changes["model_change_lead_time_days"] = {
            "old": policy.model_change_lead_time_days,
            "new": policy_data.model_change_lead_time_days
        }
        policy.model_change_lead_time_days = policy_data.model_change_lead_time_days

    if policy_data.description is not None and policy_data.description != policy.description:
        changes["description"] = {
            "old": policy.description,
            "new": policy_data.description
        }
        policy.description = policy_data.description

    policy.updated_at = datetime.utcnow()

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="ValidationPolicy",
            entity_id=policy_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

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

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="ValidationPolicy",
        entity_id=policy_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "risk_tier_id": policy.risk_tier_id,
            "frequency_months": policy.frequency_months,
            "model_change_lead_time_days": policy.model_change_lead_time_days
        }
    )

    db.delete(policy)
    db.commit()

    return None

"""MRSA Review Policy routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.models.user import User
from app.models.mrsa_review_policy import MRSAReviewPolicy, MRSAReviewException
from app.models.model import Model
from app.models.taxonomy import TaxonomyValue
from app.models.audit_log import AuditLog
from app.schemas.mrsa_review_policy import (
    MRSAReviewPolicyCreate,
    MRSAReviewPolicyUpdate,
    MRSAReviewPolicyResponse,
    MRSAReviewExceptionCreate,
    MRSAReviewExceptionUpdate,
    MRSAReviewExceptionResponse,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for MRSA review policy operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def require_admin(current_user: User):
    """Require admin role for MRSA review policy operations."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this operation"
        )


# ============================================================================
# MRSA Review Policy Endpoints
# ============================================================================

@router.get("/mrsa-review-policies/", response_model=List[MRSAReviewPolicyResponse])
def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all MRSA review policies."""
    policies = db.query(MRSAReviewPolicy).options(
        joinedload(MRSAReviewPolicy.mrsa_risk_level)
    ).all()
    return policies


@router.get("/mrsa-review-policies/{policy_id}", response_model=MRSAReviewPolicyResponse)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific MRSA review policy."""
    policy = db.query(MRSAReviewPolicy).options(
        joinedload(MRSAReviewPolicy.mrsa_risk_level)
    ).filter(MRSAReviewPolicy.policy_id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MRSA review policy not found"
        )

    return policy


@router.post("/mrsa-review-policies/", response_model=MRSAReviewPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy_data: MRSAReviewPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new MRSA review policy (Admin only)."""
    require_admin(current_user)

    # Validate that mrsa_risk_level_id exists
    risk_level = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == policy_data.mrsa_risk_level_id
    ).first()
    if not risk_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MRSA risk level ID"
        )

    # Check for duplicate policy for this risk level
    existing = db.query(MRSAReviewPolicy).filter(
        MRSAReviewPolicy.mrsa_risk_level_id == policy_data.mrsa_risk_level_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A policy already exists for this MRSA risk level"
        )

    # Validate numeric fields
    if policy_data.frequency_months <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Frequency months must be greater than 0"
        )
    if policy_data.initial_review_months <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial review months must be greater than 0"
        )
    if policy_data.warning_days < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warning days must be 0 or greater"
        )

    policy = MRSAReviewPolicy(**policy_data.model_dump())
    db.add(policy)
    db.flush()  # Get policy_id before creating audit log

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="MRSAReviewPolicy",
        entity_id=policy.policy_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "mrsa_risk_level_id": policy_data.mrsa_risk_level_id,
            "frequency_months": policy_data.frequency_months,
            "initial_review_months": policy_data.initial_review_months,
            "warning_days": policy_data.warning_days,
            "is_active": policy_data.is_active
        }
    )

    db.commit()
    db.refresh(policy)

    # Reload with relationship
    policy = db.query(MRSAReviewPolicy).options(
        joinedload(MRSAReviewPolicy.mrsa_risk_level)
    ).filter(MRSAReviewPolicy.policy_id == policy.policy_id).first()

    return policy


@router.patch("/mrsa-review-policies/{policy_id}", response_model=MRSAReviewPolicyResponse)
def update_policy(
    policy_id: int,
    policy_data: MRSAReviewPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an MRSA review policy (Admin only)."""
    require_admin(current_user)

    policy = db.query(MRSAReviewPolicy).filter(
        MRSAReviewPolicy.policy_id == policy_id
    ).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MRSA review policy not found"
        )

    update_data = policy_data.model_dump(exclude_unset=True)

    # Validate mrsa_risk_level_id if being updated
    if "mrsa_risk_level_id" in update_data:
        risk_level = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == update_data["mrsa_risk_level_id"]
        ).first()
        if not risk_level:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MRSA risk level ID"
            )

        # Check for duplicate policy for this risk level (excluding current policy)
        existing = db.query(MRSAReviewPolicy).filter(
            MRSAReviewPolicy.mrsa_risk_level_id == update_data["mrsa_risk_level_id"],
            MRSAReviewPolicy.policy_id != policy_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A policy already exists for this MRSA risk level"
            )

    # Validate numeric fields
    if "frequency_months" in update_data and update_data["frequency_months"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Frequency months must be greater than 0"
        )
    if "initial_review_months" in update_data and update_data["initial_review_months"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial review months must be greater than 0"
        )
    if "warning_days" in update_data and update_data["warning_days"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warning days must be 0 or greater"
        )

    # Track changes for audit log
    changes = {}
    for field, value in update_data.items():
        old_value = getattr(policy, field, None)
        if old_value != value:
            changes[field] = {
                "old": old_value,
                "new": value
            }
        setattr(policy, field, value)

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="MRSAReviewPolicy",
            entity_id=policy_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(policy)

    # Reload with relationship
    policy = db.query(MRSAReviewPolicy).options(
        joinedload(MRSAReviewPolicy.mrsa_risk_level)
    ).filter(MRSAReviewPolicy.policy_id == policy.policy_id).first()

    return policy


@router.delete("/mrsa-review-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an MRSA review policy (Admin only)."""
    require_admin(current_user)

    policy = db.query(MRSAReviewPolicy).filter(
        MRSAReviewPolicy.policy_id == policy_id
    ).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MRSA review policy not found"
        )

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="MRSAReviewPolicy",
        entity_id=policy_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "mrsa_risk_level_id": policy.mrsa_risk_level_id,
            "frequency_months": policy.frequency_months,
            "initial_review_months": policy.initial_review_months
        }
    )

    db.delete(policy)
    db.commit()
    return None


# ============================================================================
# MRSA Review Exception Endpoints
# ============================================================================

@router.get("/mrsa-review-exceptions/", response_model=List[MRSAReviewExceptionResponse])
def list_exceptions(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all MRSA review exceptions."""
    query = db.query(MRSAReviewException).options(
        joinedload(MRSAReviewException.mrsa),
        joinedload(MRSAReviewException.approved_by)
    )

    if active_only:
        query = query.filter(MRSAReviewException.is_active == True)

    exceptions = query.all()
    return exceptions


@router.get("/mrsa-review-exceptions/{mrsa_id}", response_model=Optional[MRSAReviewExceptionResponse])
def get_exception_for_mrsa(
    mrsa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active exception for a specific MRSA."""
    exception = db.query(MRSAReviewException).options(
        joinedload(MRSAReviewException.mrsa),
        joinedload(MRSAReviewException.approved_by)
    ).filter(
        MRSAReviewException.mrsa_id == mrsa_id,
        MRSAReviewException.is_active == True
    ).first()

    return exception


@router.post("/mrsa-review-exceptions/", response_model=MRSAReviewExceptionResponse, status_code=status.HTTP_201_CREATED)
def create_exception(
    exception_data: MRSAReviewExceptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new MRSA review exception (Admin only)."""
    require_admin(current_user)

    # Validate that mrsa_id exists
    mrsa = db.query(Model).filter(Model.model_id == exception_data.mrsa_id).first()
    if not mrsa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MRSA not found"
        )

    # Check if there's already an active exception for this MRSA
    existing = db.query(MRSAReviewException).filter(
        MRSAReviewException.mrsa_id == exception_data.mrsa_id,
        MRSAReviewException.is_active == True
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active exception already exists for this MRSA. Please revoke the existing exception first."
        )

    exception = MRSAReviewException(
        mrsa_id=exception_data.mrsa_id,
        override_due_date=exception_data.override_due_date,
        reason=exception_data.reason,
        approved_by_id=current_user.user_id
    )
    db.add(exception)
    db.flush()  # Get exception_id before creating audit log

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="MRSAReviewException",
        entity_id=exception.exception_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "mrsa_id": exception_data.mrsa_id,
            "mrsa_name": mrsa.model_name,
            "override_due_date": exception_data.override_due_date.isoformat(),
            "reason": exception_data.reason
        }
    )

    db.commit()
    db.refresh(exception)

    # Reload with relationships
    exception = db.query(MRSAReviewException).options(
        joinedload(MRSAReviewException.mrsa),
        joinedload(MRSAReviewException.approved_by)
    ).filter(MRSAReviewException.exception_id == exception.exception_id).first()

    return exception


@router.patch("/mrsa-review-exceptions/{exception_id}", response_model=MRSAReviewExceptionResponse)
def update_exception(
    exception_id: int,
    exception_data: MRSAReviewExceptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update/revoke an MRSA review exception (Admin only)."""
    require_admin(current_user)

    exception = db.query(MRSAReviewException).options(
        joinedload(MRSAReviewException.mrsa)
    ).filter(MRSAReviewException.exception_id == exception_id).first()

    if not exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MRSA review exception not found"
        )

    update_data = exception_data.model_dump(exclude_unset=True)

    # Track changes for audit log
    changes = {}
    for field, value in update_data.items():
        old_value = getattr(exception, field, None)
        if old_value != value:
            # Convert date to string for audit log
            if field in ("override_due_date",):
                changes[field] = {
                    "old": old_value.isoformat() if old_value else None,
                    "new": value.isoformat() if value else None
                }
            else:
                changes[field] = {
                    "old": old_value,
                    "new": value
                }
        setattr(exception, field, value)

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="MRSAReviewException",
            entity_id=exception_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(exception)

    # Reload with relationships
    exception = db.query(MRSAReviewException).options(
        joinedload(MRSAReviewException.mrsa),
        joinedload(MRSAReviewException.approved_by)
    ).filter(MRSAReviewException.exception_id == exception.exception_id).first()

    return exception

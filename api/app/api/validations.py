"""Validations routes."""
from typing import List, Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.model import Model
from app.models.validation import Validation, ValidationPolicy
from app.models.taxonomy import TaxonomyValue
from app.models.audit_log import AuditLog
from app.schemas.validation import (
    ValidationCreate,
    ValidationUpdate,
    ValidationResponse,
    ValidationListResponse,
    ValidationPolicyCreate,
    ValidationPolicyUpdate,
    ValidationPolicyResponse,
)

router = APIRouter()


def check_validator_or_admin(user: User):
    """Check if user has Validator or Admin role."""
    if user.role not in [UserRole.VALIDATOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Validators or Admins can perform this action"
        )


def check_admin(user: User):
    """Check if user has Admin role."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can perform this action"
        )


@router.get("/", response_model=List[ValidationListResponse])
def list_validations(
    model_id: Optional[int] = Query(None),
    outcome_id: Optional[int] = Query(None),
    validator_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List validations with optional filters."""
    query = db.query(Validation).options(
        joinedload(Validation.model),
        joinedload(Validation.validator),
        joinedload(Validation.validation_type),
        joinedload(Validation.outcome),
        joinedload(Validation.scope)
    )

    if model_id is not None:
        query = query.filter(Validation.model_id == model_id)
    if outcome_id is not None:
        query = query.filter(Validation.outcome_id == outcome_id)
    if validator_id is not None:
        query = query.filter(Validation.validator_id == validator_id)
    if from_date is not None:
        query = query.filter(Validation.validation_date >= from_date)
    if to_date is not None:
        query = query.filter(Validation.validation_date <= to_date)

    validations = query.order_by(Validation.validation_date.desc()).offset(offset).limit(limit).all()

    # Transform to list response
    result = []
    for v in validations:
        result.append(ValidationListResponse(
            validation_id=v.validation_id,
            model_id=v.model_id,
            model_name=v.model.model_name,
            validation_date=v.validation_date,
            validator_name=v.validator.full_name,
            validation_type=v.validation_type.label,
            outcome=v.outcome.label,
            scope=v.scope.label,
            created_at=v.created_at
        ))

    return result


@router.post("/", response_model=ValidationResponse, status_code=status.HTTP_201_CREATED)
def create_validation(
    validation_data: ValidationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new validation record. Only Validators or Admins can create."""
    check_validator_or_admin(current_user)

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == validation_data.model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify validator user exists
    validator = db.query(User).filter(User.user_id == validation_data.validator_id).first()
    if not validator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validator user not found"
        )

    # Verify taxonomy values exist
    validation_type = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == validation_data.validation_type_id).first()
    if not validation_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation type not found")

    outcome = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == validation_data.outcome_id).first()
    if not outcome:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outcome not found")

    scope = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == validation_data.scope_id).first()
    if not scope:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found")

    validation = Validation(**validation_data.model_dump())
    db.add(validation)
    db.flush()

    # Create audit log
    audit_log = AuditLog(
        entity_type="Validation",
        entity_id=validation.validation_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "model_id": validation.model_id,
            "model_name": model.model_name,
            "validation_date": str(validation.validation_date),
            "outcome": outcome.label
        }
    )
    db.add(audit_log)
    db.commit()

    # Reload with relationships
    validation = db.query(Validation).options(
        joinedload(Validation.model),
        joinedload(Validation.validator),
        joinedload(Validation.validation_type),
        joinedload(Validation.outcome),
        joinedload(Validation.scope)
    ).filter(Validation.validation_id == validation.validation_id).first()

    return validation


@router.get("/{validation_id}", response_model=ValidationResponse)
def get_validation(
    validation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific validation."""
    validation = db.query(Validation).options(
        joinedload(Validation.model),
        joinedload(Validation.validator),
        joinedload(Validation.validation_type),
        joinedload(Validation.outcome),
        joinedload(Validation.scope)
    ).filter(Validation.validation_id == validation_id).first()

    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation not found"
        )

    return validation


@router.patch("/{validation_id}", response_model=ValidationResponse)
def update_validation(
    validation_id: int,
    validation_data: ValidationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a validation record. Only Validators or Admins can update."""
    check_validator_or_admin(current_user)

    validation = db.query(Validation).filter(Validation.validation_id == validation_id).first()
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation not found"
        )

    update_data = validation_data.model_dump(exclude_unset=True)
    old_values = {}
    new_values = {}

    for field, value in update_data.items():
        old_value = getattr(validation, field)
        if old_value != value:
            old_values[field] = str(old_value) if old_value is not None else None
            new_values[field] = str(value) if value is not None else None
            setattr(validation, field, value)

    if old_values:
        # Create audit log
        changes = {field: {"old": old_values[field], "new": new_values[field]} for field in old_values}
        audit_log = AuditLog(
            entity_type="Validation",
            entity_id=validation.validation_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )
        db.add(audit_log)

    db.commit()

    # Reload with relationships
    validation = db.query(Validation).options(
        joinedload(Validation.model),
        joinedload(Validation.validator),
        joinedload(Validation.validation_type),
        joinedload(Validation.outcome),
        joinedload(Validation.scope)
    ).filter(Validation.validation_id == validation_id).first()

    return validation


@router.delete("/{validation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_validation(
    validation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a validation record. Only Admins can delete."""
    check_admin(current_user)

    validation = db.query(Validation).options(
        joinedload(Validation.model)
    ).filter(Validation.validation_id == validation_id).first()

    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation not found"
        )

    # Create audit log before deletion
    audit_log = AuditLog(
        entity_type="Validation",
        entity_id=validation.validation_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "model_name": validation.model.model_name,
            "validation_date": str(validation.validation_date)
        }
    )
    db.add(audit_log)

    db.delete(validation)
    db.commit()


# Validation Policy Routes
@router.get("/policies/", response_model=List[ValidationPolicyResponse])
def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all validation policies."""
    policies = db.query(ValidationPolicy).options(
        joinedload(ValidationPolicy.risk_tier)
    ).all()
    return policies


@router.post("/policies/", response_model=ValidationPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy_data: ValidationPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new validation policy. Only Admins can create."""
    check_admin(current_user)

    # Verify risk tier exists
    risk_tier = db.query(TaxonomyValue).filter(TaxonomyValue.value_id == policy_data.risk_tier_id).first()
    if not risk_tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk tier not found"
        )

    # Check for duplicate
    existing = db.query(ValidationPolicy).filter(ValidationPolicy.risk_tier_id == policy_data.risk_tier_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy for this risk tier already exists"
        )

    policy = ValidationPolicy(**policy_data.model_dump())
    db.add(policy)
    db.commit()

    policy = db.query(ValidationPolicy).options(
        joinedload(ValidationPolicy.risk_tier)
    ).filter(ValidationPolicy.policy_id == policy.policy_id).first()

    return policy


@router.patch("/policies/{policy_id}", response_model=ValidationPolicyResponse)
def update_policy(
    policy_id: int,
    policy_data: ValidationPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a validation policy. Only Admins can update."""
    check_admin(current_user)

    policy = db.query(ValidationPolicy).filter(ValidationPolicy.policy_id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )

    update_data = policy_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)

    db.commit()

    policy = db.query(ValidationPolicy).options(
        joinedload(ValidationPolicy.risk_tier)
    ).filter(ValidationPolicy.policy_id == policy_id).first()

    return policy


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a validation policy. Only Admins can delete."""
    check_admin(current_user)

    policy = db.query(ValidationPolicy).filter(ValidationPolicy.policy_id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )

    db.delete(policy)
    db.commit()


# Dashboard helper endpoints
@router.get("/dashboard/overdue", response_model=List[dict])
def get_overdue_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get models that are overdue for validation based on policy."""
    check_admin(current_user)

    # Get all policies
    policies = {p.risk_tier_id: p.frequency_months for p in db.query(ValidationPolicy).all()}

    if not policies:
        return []

    # Get all active models with their risk tiers and last validations
    models = db.query(Model).options(
        joinedload(Model.risk_tier),
        joinedload(Model.owner)
    ).filter(Model.status == "Active").all()

    overdue = []
    today = date.today()

    for model in models:
        if not model.risk_tier_id or model.risk_tier_id not in policies:
            continue

        # Get last validation
        last_validation = db.query(Validation).filter(
            Validation.model_id == model.model_id
        ).order_by(Validation.validation_date.desc()).first()

        frequency_months = policies[model.risk_tier_id]

        if not last_validation:
            # Never validated
            overdue.append({
                "model_id": model.model_id,
                "model_name": model.model_name,
                "risk_tier": model.risk_tier.label if model.risk_tier else None,
                "owner_name": model.owner.full_name,
                "last_validation_date": None,
                "next_due_date": None,
                "days_overdue": None,
                "status": "Never Validated"
            })
        else:
            next_due = last_validation.validation_date + timedelta(days=frequency_months * 30)
            if next_due < today:
                days_overdue = (today - next_due).days
                overdue.append({
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "risk_tier": model.risk_tier.label if model.risk_tier else None,
                    "owner_name": model.owner.full_name,
                    "last_validation_date": str(last_validation.validation_date),
                    "next_due_date": str(next_due),
                    "days_overdue": days_overdue,
                    "status": "Overdue"
                })

    return overdue


@router.get("/dashboard/pass-with-findings", response_model=List[dict])
def get_pass_with_findings_no_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validations with 'Pass with Findings' outcome (placeholder for future Issue Management)."""
    check_admin(current_user)

    # Get the Pass with Findings outcome value_id
    pass_with_findings = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == "PASS_WITH_FINDINGS"
    ).first()

    if not pass_with_findings:
        return []

    validations = db.query(Validation).options(
        joinedload(Validation.model),
        joinedload(Validation.validator)
    ).filter(
        Validation.outcome_id == pass_with_findings.value_id
    ).order_by(Validation.validation_date.desc()).all()

    result = []
    for v in validations:
        # TODO: When Issue Management is added, check if there are recommendations linked
        result.append({
            "validation_id": v.validation_id,
            "model_id": v.model_id,
            "model_name": v.model.model_name,
            "validation_date": str(v.validation_date),
            "validator_name": v.validator.full_name,
            "findings_summary": v.findings_summary,
            "has_recommendations": False  # Placeholder for future Issue Management
        })

    return result

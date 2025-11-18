"""Validation workflow API endpoints."""
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    User, Model, TaxonomyValue, Taxonomy, AuditLog,
    ValidationRequest, ValidationStatusHistory, ValidationAssignment,
    ValidationOutcome, ValidationApproval
)
from app.schemas.validation import (
    ValidationRequestCreate, ValidationRequestUpdate, ValidationRequestStatusUpdate,
    ValidationRequestResponse, ValidationRequestDetailResponse, ValidationRequestListResponse,
    ValidationAssignmentCreate, ValidationAssignmentUpdate, ValidationAssignmentResponse,
    ReviewerSignOffRequest,
    ValidationOutcomeCreate, ValidationOutcomeUpdate, ValidationOutcomeResponse,
    ValidationApprovalCreate, ValidationApprovalUpdate, ValidationApprovalResponse,
    ValidationStatusHistoryResponse
)

router = APIRouter()


# ==================== HELPER FUNCTIONS ====================

def check_validator_or_admin(user: User):
    """Check if user has Validator or Admin role."""
    if user.role not in ("Validator", "Admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Validators and Admins can perform this action"
        )


def check_admin(user: User):
    """Check if user has Admin role."""
    if user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can perform this action"
        )


def get_taxonomy_value_by_code(db: Session, taxonomy_name: str, code: str) -> TaxonomyValue:
    """Get taxonomy value by taxonomy name and code."""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.name == taxonomy_name).first()
    if not taxonomy:
        raise HTTPException(status_code=404, detail=f"Taxonomy '{taxonomy_name}' not found")

    value = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.code == code
    ).first()
    if not value:
        raise HTTPException(status_code=404, detail=f"Taxonomy value '{code}' not found in '{taxonomy_name}'")
    return value


def check_valid_status_transition(old_status_code: Optional[str], new_status_code: str) -> bool:
    """Validate status transition according to workflow rules."""
    # Define valid transitions
    valid_transitions = {
        None: ["INTAKE"],  # Initial creation
        "INTAKE": ["PLANNING", "CANCELLED", "ON_HOLD"],
        "PLANNING": ["IN_PROGRESS", "CANCELLED", "ON_HOLD"],
        "IN_PROGRESS": ["REVIEW", "CANCELLED", "ON_HOLD"],
        "REVIEW": ["PENDING_APPROVAL", "IN_PROGRESS", "CANCELLED", "ON_HOLD"],
        "PENDING_APPROVAL": ["APPROVED", "REVIEW", "CANCELLED", "ON_HOLD"],
        "APPROVED": [],  # Terminal state
        "ON_HOLD": ["INTAKE", "PLANNING", "IN_PROGRESS", "REVIEW", "PENDING_APPROVAL", "CANCELLED"],
        "CANCELLED": [],  # Terminal state
    }

    allowed = valid_transitions.get(old_status_code, [])
    return new_status_code in allowed


def create_status_history_entry(
    db: Session,
    request_id: int,
    old_status_id: Optional[int],
    new_status_id: int,
    changed_by_id: int,
    change_reason: Optional[str] = None
):
    """Create a status history entry."""
    history = ValidationStatusHistory(
        request_id=request_id,
        old_status_id=old_status_id,
        new_status_id=new_status_id,
        changed_by_id=changed_by_id,
        change_reason=change_reason,
        changed_at=datetime.utcnow()
    )
    db.add(history)


def check_validator_independence(db: Session, model_id: int, validator_id: int) -> bool:
    """Check if validator is independent from model (not owner or developer)."""
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return False

    # Validator cannot be model owner or developer
    if model.owner_id == validator_id:
        return False
    if model.developer_id == validator_id:
        return False

    return True


def calculate_days_in_status(db: Session, request: ValidationRequest) -> int:
    """Calculate how many days the request has been in current status."""
    latest_history = db.query(ValidationStatusHistory).filter(
        ValidationStatusHistory.request_id == request.request_id,
        ValidationStatusHistory.new_status_id == request.current_status_id
    ).order_by(desc(ValidationStatusHistory.changed_at)).first()

    if latest_history:
        delta = datetime.utcnow() - latest_history.changed_at
        return delta.days
    else:
        # If no history, use creation date
        delta = datetime.utcnow() - request.created_at
        return delta.days


# ==================== VALIDATION REQUEST ENDPOINTS ====================

@router.post("/requests/", response_model=ValidationRequestResponse, status_code=status.HTTP_201_CREATED)
def create_validation_request(
    request_data: ValidationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new validation request."""
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == request_data.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Verify validation type exists
    validation_type = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == request_data.validation_type_id
    ).first()
    if not validation_type:
        raise HTTPException(status_code=404, detail="Validation type not found")

    # Verify priority exists
    priority = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == request_data.priority_id
    ).first()
    if not priority:
        raise HTTPException(status_code=404, detail="Priority not found")

    # Get initial status (INTAKE)
    intake_status = get_taxonomy_value_by_code(db, "Validation Request Status", "INTAKE")

    # Create the request
    validation_request = ValidationRequest(
        model_id=request_data.model_id,
        request_date=date.today(),
        requestor_id=current_user.user_id,
        validation_type_id=request_data.validation_type_id,
        priority_id=request_data.priority_id,
        target_completion_date=request_data.target_completion_date,
        trigger_reason=request_data.trigger_reason,
        business_justification=request_data.business_justification,
        current_status_id=intake_status.value_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(validation_request)
    db.flush()

    # Create initial status history entry
    create_status_history_entry(
        db, validation_request.request_id, None, intake_status.value_id, current_user.user_id
    )

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=validation_request.request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "model_id": model.model_id,
            "model_name": model.model_name,
            "validation_type": validation_type.label,
            "priority": priority.label,
            "status": "Intake"
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()

    # Reload with relationships
    db.refresh(validation_request)
    return validation_request


@router.get("/requests/", response_model=List[ValidationRequestListResponse])
def list_validation_requests(
    model_id: Optional[int] = None,
    status_id: Optional[int] = None,
    priority_id: Optional[int] = None,
    requestor_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List validation requests with optional filters."""
    query = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.assignments).joinedload(ValidationAssignment.validator)
    )

    if model_id:
        query = query.filter(ValidationRequest.model_id == model_id)
    if status_id:
        query = query.filter(ValidationRequest.current_status_id == status_id)
    if priority_id:
        query = query.filter(ValidationRequest.priority_id == priority_id)
    if requestor_id:
        query = query.filter(ValidationRequest.requestor_id == requestor_id)

    requests = query.order_by(desc(ValidationRequest.request_date)).offset(offset).limit(limit).all()

    # Transform to list response format
    result = []
    for req in requests:
        primary_validator = next(
            (a.validator.full_name for a in req.assignments if a.is_primary),
            None
        )
        result.append(ValidationRequestListResponse(
            request_id=req.request_id,
            model_id=req.model_id,
            model_name=req.model.model_name,
            request_date=req.request_date,
            requestor_name=req.requestor.full_name,
            validation_type=req.validation_type.label,
            priority=req.priority.label,
            target_completion_date=req.target_completion_date,
            current_status=req.current_status.label,
            days_in_status=calculate_days_in_status(db, req),
            primary_validator=primary_validator,
            created_at=req.created_at
        ))

    return result


@router.get("/requests/{request_id}", response_model=ValidationRequestDetailResponse)
def get_validation_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed validation request with all relationships."""
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model),
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.validation_type),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.assignments).joinedload(ValidationAssignment.validator),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.old_status),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.new_status),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.changed_by),
        joinedload(ValidationRequest.approvals).joinedload(ValidationApproval.approver),
        joinedload(ValidationRequest.outcome)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    return validation_request


@router.patch("/requests/{request_id}", response_model=ValidationRequestResponse)
def update_validation_request(
    request_id: int,
    update_data: ValidationRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update validation request (only editable fields, not status)."""
    check_validator_or_admin(current_user)

    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Check if request is locked (in approval stage)
    status_code = validation_request.current_status.code if validation_request.current_status else None
    if status_code in ["PENDING_APPROVAL", "APPROVED"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot edit request in Pending Approval or Approved status"
        )

    # Track changes for audit log
    changes = {}
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, new_value in update_dict.items():
        old_value = getattr(validation_request, field)
        if old_value != new_value:
            setattr(validation_request, field, new_value)
            changes[field] = {"old": str(old_value), "new": str(new_value)}

    if changes:
        validation_request.updated_at = datetime.utcnow()

        audit_log = AuditLog(
            entity_type="ValidationRequest",
            entity_id=request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes,
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)

    db.commit()
    db.refresh(validation_request)
    return validation_request


@router.patch("/requests/{request_id}/status", response_model=ValidationRequestResponse)
def update_validation_request_status(
    request_id: int,
    status_update: ValidationRequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update validation request status with workflow validation."""
    check_validator_or_admin(current_user)

    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Get new status
    new_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == status_update.new_status_id
    ).first()
    if not new_status:
        raise HTTPException(status_code=404, detail="New status not found")

    old_status = validation_request.current_status
    old_status_code = old_status.code if old_status else None
    new_status_code = new_status.code

    # Validate transition
    if not check_valid_status_transition(old_status_code, new_status_code):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{old_status_code}' to '{new_status_code}'"
        )

    # Additional business rules
    if new_status_code == "REVIEW":
        # Must have at least one assigned validator
        if not validation_request.assignments:
            raise HTTPException(status_code=400, detail="Cannot move to Review without assigned validators")

    if new_status_code == "PENDING_APPROVAL":
        # Must have an outcome created
        if not validation_request.outcome:
            raise HTTPException(status_code=400, detail="Cannot move to Pending Approval without creating outcome")

        # If a reviewer is assigned, they must have signed off
        reviewer_assignment = db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == request_id,
            ValidationAssignment.is_reviewer == True
        ).first()
        if reviewer_assignment and not reviewer_assignment.reviewer_signed_off:
            raise HTTPException(
                status_code=400,
                detail="Reviewer must sign off before moving to Pending Approval"
            )

    # Update status
    old_status_id = validation_request.current_status_id
    validation_request.current_status_id = new_status.value_id
    validation_request.updated_at = datetime.utcnow()

    # Create status history
    create_status_history_entry(
        db, request_id, old_status_id, new_status.value_id,
        current_user.user_id, status_update.change_reason
    )

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="STATUS_CHANGE",
        user_id=current_user.user_id,
        changes={
            "old_status": old_status.label if old_status else None,
            "new_status": new_status.label,
            "reason": status_update.change_reason
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(validation_request)
    return validation_request


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_validation_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a validation request (Admin only)."""
    check_admin(current_user)

    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Create audit log before deletion
    audit_log = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"request_id": request_id},
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.delete(validation_request)
    db.commit()


# ==================== ASSIGNMENT ENDPOINTS ====================

@router.post("/requests/{request_id}/assignments", response_model=ValidationAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    request_id: int,
    assignment_data: ValidationAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a validator to a validation request."""
    check_validator_or_admin(current_user)

    # Verify request exists
    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Verify validator user exists
    validator = db.query(User).filter(User.user_id == assignment_data.validator_id).first()
    if not validator:
        raise HTTPException(status_code=404, detail="Validator user not found")

    # Check validator independence
    if not check_validator_independence(db, validation_request.model_id, assignment_data.validator_id):
        raise HTTPException(
            status_code=400,
            detail="Validator cannot be the model owner or developer (independence requirement)"
        )

    # Require independence attestation
    if not assignment_data.independence_attestation:
        raise HTTPException(
            status_code=400,
            detail="Independence attestation is required to assign a validator"
        )

    # Check if already assigned
    existing = db.query(ValidationAssignment).filter(
        ValidationAssignment.request_id == request_id,
        ValidationAssignment.validator_id == assignment_data.validator_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Validator already assigned to this request")

    # If this is primary, demote existing primary
    if assignment_data.is_primary:
        db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == request_id,
            ValidationAssignment.is_primary == True
        ).update({"is_primary": False})

    # If this is reviewer, demote existing reviewer
    if assignment_data.is_reviewer:
        db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == request_id,
            ValidationAssignment.is_reviewer == True
        ).update({"is_reviewer": False})

    # Create assignment
    assignment = ValidationAssignment(
        request_id=request_id,
        validator_id=assignment_data.validator_id,
        is_primary=assignment_data.is_primary,
        is_reviewer=assignment_data.is_reviewer,
        assignment_date=date.today(),
        estimated_hours=assignment_data.estimated_hours,
        actual_hours=0.0,
        independence_attestation=assignment_data.independence_attestation,
        created_at=datetime.utcnow()
    )
    db.add(assignment)
    db.flush()

    # Create audit log for assignment
    roles = []
    if assignment_data.is_primary:
        roles.append("Primary")
    if assignment_data.is_reviewer:
        roles.append("Reviewer")
    role_str = " & ".join(roles) if roles else "Supporting"

    audit_log = AuditLog(
        entity_type="ValidationAssignment",
        entity_id=request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "assignment_id": assignment.assignment_id,
            "validator": validator.full_name,
            "role": role_str,
            "estimated_hours": assignment_data.estimated_hours
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(assignment)

    return assignment


@router.patch("/assignments/{assignment_id}", response_model=ValidationAssignmentResponse)
def update_assignment(
    assignment_id: int,
    update_data: ValidationAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update validator assignment (hours, attestation, primary status)."""
    assignment = db.query(ValidationAssignment).filter(
        ValidationAssignment.assignment_id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Only assigned validator or admin can update
    if current_user.user_id != assignment.validator_id and current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only assigned validator or Admin can update assignment")

    update_dict = update_data.model_dump(exclude_unset=True)

    # If setting as primary, demote others
    if update_dict.get("is_primary"):
        db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == assignment.request_id,
            ValidationAssignment.assignment_id != assignment_id,
            ValidationAssignment.is_primary == True
        ).update({"is_primary": False})

    # If setting as reviewer, demote others
    if update_dict.get("is_reviewer"):
        db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == assignment.request_id,
            ValidationAssignment.assignment_id != assignment_id,
            ValidationAssignment.is_reviewer == True
        ).update({"is_reviewer": False})

    # Track changes for audit
    changes = {}
    for field, value in update_dict.items():
        old_value = getattr(assignment, field)
        if old_value != value:
            setattr(assignment, field, value)
            changes[field] = {"old": str(old_value), "new": str(value)}

    if changes:
        # Create audit log for assignment update
        audit_log = AuditLog(
            entity_type="ValidationAssignment",
            entity_id=assignment.request_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes={
                "assignment_id": assignment_id,
                "validator": assignment.validator.full_name,
                **changes
            },
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)

    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    new_primary_id: Optional[int] = Query(None, description="New primary validator ID (required when removing primary with multiple remaining validators)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a validator assignment."""
    check_validator_or_admin(current_user)

    assignment = db.query(ValidationAssignment).options(
        joinedload(ValidationAssignment.validator)
    ).filter(
        ValidationAssignment.assignment_id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check how many validators will remain
    total_validators = db.query(ValidationAssignment).filter(
        ValidationAssignment.request_id == assignment.request_id
    ).count()

    if total_validators <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove the last validator. Assign another validator before removing this one."
        )

    # If removing primary validator, handle succession
    if assignment.is_primary:
        remaining_validators = db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == assignment.request_id,
            ValidationAssignment.assignment_id != assignment_id
        ).all()

        if len(remaining_validators) == 1:
            # Auto-promote the only remaining validator to primary
            remaining_validators[0].is_primary = True
            audit_log_promotion = AuditLog(
                entity_type="ValidationAssignment",
                entity_id=assignment.request_id,
                action="UPDATE",
                user_id=current_user.user_id,
                changes={
                    "assignment_id": remaining_validators[0].assignment_id,
                    "validator": remaining_validators[0].validator.full_name,
                    "is_primary": {"old": "False", "new": "True"},
                    "reason": "Auto-promoted when previous primary was removed"
                },
                timestamp=datetime.utcnow()
            )
            db.add(audit_log_promotion)
        elif len(remaining_validators) > 1:
            # Multiple validators remain - require explicit new primary selection
            if not new_primary_id:
                raise HTTPException(
                    status_code=400,
                    detail="Multiple validators remain. Please specify which validator should become the new primary."
                )

            # Find and promote the new primary
            new_primary = next((v for v in remaining_validators if v.validator_id == new_primary_id), None)
            if not new_primary:
                raise HTTPException(
                    status_code=400,
                    detail="Selected new primary validator not found in remaining validators"
                )

            new_primary.is_primary = True
            audit_log_promotion = AuditLog(
                entity_type="ValidationAssignment",
                entity_id=assignment.request_id,
                action="UPDATE",
                user_id=current_user.user_id,
                changes={
                    "assignment_id": new_primary.assignment_id,
                    "validator": new_primary.validator.full_name,
                    "is_primary": {"old": "False", "new": "True"},
                    "reason": "Promoted to primary when previous primary was removed"
                },
                timestamp=datetime.utcnow()
            )
            db.add(audit_log_promotion)

    # Create audit log before deletion
    roles = []
    if assignment.is_primary:
        roles.append("Primary")
    if assignment.is_reviewer:
        roles.append("Reviewer")
    role_str = " & ".join(roles) if roles else "Supporting"

    audit_log = AuditLog(
        entity_type="ValidationAssignment",
        entity_id=assignment.request_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "assignment_id": assignment_id,
            "validator": assignment.validator.full_name,
            "role": role_str
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.delete(assignment)
    db.commit()


@router.post("/assignments/{assignment_id}/sign-off", response_model=ValidationAssignmentResponse)
def reviewer_sign_off(
    assignment_id: int,
    sign_off_data: ReviewerSignOffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reviewer signs off on validation work for quality assurance."""
    assignment = db.query(ValidationAssignment).options(
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.current_status)
    ).filter(
        ValidationAssignment.assignment_id == assignment_id
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Only the assigned reviewer can sign off
    if not assignment.is_reviewer:
        raise HTTPException(status_code=400, detail="This assignment is not a reviewer role")

    if current_user.user_id != assignment.validator_id:
        raise HTTPException(status_code=403, detail="Only the assigned reviewer can sign off")

    # Check if already signed off
    if assignment.reviewer_signed_off:
        raise HTTPException(status_code=400, detail="Reviewer has already signed off")

    # Verify the request has an outcome (reviewer should review the outcome before signing off)
    request = assignment.request
    if not request.outcome:
        raise HTTPException(
            status_code=400,
            detail="Cannot sign off before outcome is created"
        )

    # Perform sign-off
    assignment.reviewer_signed_off = True
    assignment.reviewer_signed_off_at = datetime.utcnow()
    assignment.reviewer_sign_off_comments = sign_off_data.comments

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationAssignment",
        entity_id=assignment.request_id,
        action="REVIEWER_SIGN_OFF",
        user_id=current_user.user_id,
        changes={
            "assignment_id": assignment_id,
            "reviewer": current_user.full_name,
            "comments": sign_off_data.comments
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(assignment)
    return assignment


# ==================== OUTCOME ENDPOINTS ====================

@router.post("/requests/{request_id}/outcome", response_model=ValidationOutcomeResponse, status_code=status.HTTP_201_CREATED)
def create_outcome(
    request_id: int,
    outcome_data: ValidationOutcomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create validation outcome (only after work is complete)."""
    check_validator_or_admin(current_user)

    # Verify request exists
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.outcome)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Check if outcome already exists
    if validation_request.outcome:
        raise HTTPException(status_code=400, detail="Outcome already exists for this request")

    # Verify status is Review or later (not Intake/Planning/In Progress)
    status_code = validation_request.current_status.code if validation_request.current_status else None
    if status_code not in ["REVIEW", "PENDING_APPROVAL", "APPROVED"]:
        raise HTTPException(
            status_code=400,
            detail="Outcome can only be created when status is Review or later"
        )

    # Verify overall rating exists
    rating = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == outcome_data.overall_rating_id
    ).first()
    if not rating:
        raise HTTPException(status_code=404, detail="Overall rating not found")

    # Create outcome
    outcome = ValidationOutcome(
        request_id=request_id,
        overall_rating_id=outcome_data.overall_rating_id,
        executive_summary=outcome_data.executive_summary,
        recommended_review_frequency=outcome_data.recommended_review_frequency,
        effective_date=outcome_data.effective_date,
        expiration_date=outcome_data.expiration_date,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(outcome)

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationOutcome",
        entity_id=request_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "overall_rating": rating.label,
            "recommended_review_frequency": outcome_data.recommended_review_frequency
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(outcome)
    return outcome


@router.patch("/outcomes/{outcome_id}", response_model=ValidationOutcomeResponse)
def update_outcome(
    outcome_id: int,
    update_data: ValidationOutcomeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update validation outcome."""
    check_validator_or_admin(current_user)

    outcome = db.query(ValidationOutcome).filter(
        ValidationOutcome.outcome_id == outcome_id
    ).first()
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")

    # Check if request is in approved status (locked)
    request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == outcome.request_id
    ).first()
    if request and request.current_status and request.current_status.code == "APPROVED":
        raise HTTPException(status_code=400, detail="Cannot modify outcome of approved validation")

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(outcome, field, value)

    outcome.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(outcome)
    return outcome


# ==================== APPROVAL ENDPOINTS ====================

@router.post("/requests/{request_id}/approvals", response_model=ValidationApprovalResponse, status_code=status.HTTP_201_CREATED)
def create_approval_requirement(
    request_id: int,
    approval_data: ValidationApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add an approval requirement to a validation request."""
    check_admin(current_user)

    # Verify request exists
    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()
    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    # Verify approver user exists
    approver = db.query(User).filter(User.user_id == approval_data.approver_id).first()
    if not approver:
        raise HTTPException(status_code=404, detail="Approver user not found")

    # Create approval record
    approval = ValidationApproval(
        request_id=request_id,
        approver_id=approval_data.approver_id,
        approver_role=approval_data.approver_role,
        is_required=approval_data.is_required,
        approval_status="Pending",
        created_at=datetime.utcnow()
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


@router.patch("/approvals/{approval_id}", response_model=ValidationApprovalResponse)
def submit_approval(
    approval_id: int,
    update_data: ValidationApprovalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit approval or rejection for a validation request."""
    approval = db.query(ValidationApproval).filter(
        ValidationApproval.approval_id == approval_id
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    # Only the designated approver can submit approval
    if current_user.user_id != approval.approver_id:
        raise HTTPException(status_code=403, detail="Only the designated approver can submit this approval")

    approval.approval_status = update_data.approval_status
    approval.comments = update_data.comments

    if update_data.approval_status in ["Approved", "Rejected"]:
        approval.approved_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        entity_type="ValidationApproval",
        entity_id=approval.request_id,
        action="APPROVAL_SUBMITTED",
        user_id=current_user.user_id,
        changes={
            "approval_id": approval_id,
            "status": update_data.approval_status,
            "approver_role": approval.approver_role
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

    db.commit()
    db.refresh(approval)
    return approval


# ==================== DASHBOARD / REPORTING ENDPOINTS ====================

@router.get("/dashboard/aging")
def get_aging_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validation requests aging report by status."""
    check_admin(current_user)

    # Get all non-terminal requests
    requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.model),
        joinedload(ValidationRequest.priority)
    ).all()

    aging_data = []
    for req in requests:
        if req.current_status and req.current_status.code not in ["APPROVED", "CANCELLED"]:
            days_in_status = calculate_days_in_status(db, req)
            aging_data.append({
                "request_id": req.request_id,
                "model_name": req.model.model_name if req.model else "Unknown",
                "current_status": req.current_status.label if req.current_status else "Unknown",
                "priority": req.priority.label if req.priority else "Unknown",
                "days_in_status": days_in_status,
                "target_completion_date": req.target_completion_date.isoformat() if req.target_completion_date else None,
                "is_overdue": req.target_completion_date < date.today() if req.target_completion_date else False
            })

    return sorted(aging_data, key=lambda x: x["days_in_status"], reverse=True)


@router.get("/dashboard/workload")
def get_workload_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validator workload report."""
    check_admin(current_user)

    # Get validators and their assignments
    validators = db.query(User).filter(User.role.in_(["Validator", "Admin"])).all()

    workload_data = []
    for validator in validators:
        active_assignments = db.query(ValidationAssignment).join(
            ValidationRequest
        ).join(
            TaxonomyValue,
            ValidationRequest.current_status_id == TaxonomyValue.value_id
        ).filter(
            ValidationAssignment.validator_id == validator.user_id,
            TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"])
        ).count()

        total_estimated_hours = db.query(ValidationAssignment).filter(
            ValidationAssignment.validator_id == validator.user_id
        ).with_entities(
            db.query(ValidationAssignment.estimated_hours).filter(
                ValidationAssignment.validator_id == validator.user_id
            ).as_scalar()
        )

        workload_data.append({
            "validator_id": validator.user_id,
            "validator_name": validator.full_name,
            "active_assignments": active_assignments,
            "role": validator.role
        })

    return sorted(workload_data, key=lambda x: x["active_assignments"], reverse=True)


@router.get("/validators/{validator_id}/assignments")
def get_validator_assignments(
    validator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all validation assignments for a specific validator."""
    # Verify validator exists
    validator = db.query(User).filter(User.user_id == validator_id).first()
    if not validator:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all assignments for this validator
    assignments = db.query(ValidationAssignment).options(
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.model),
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.current_status),
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.validation_type),
        joinedload(ValidationAssignment.request).joinedload(ValidationRequest.priority)
    ).filter(
        ValidationAssignment.validator_id == validator_id
    ).order_by(ValidationAssignment.created_at.desc()).all()

    result = []
    for assignment in assignments:
        req = assignment.request
        result.append({
            "assignment_id": assignment.assignment_id,
            "request_id": req.request_id,
            "model_id": req.model_id,
            "model_name": req.model.model_name if req.model else "Unknown",
            "validation_type": req.validation_type.label if req.validation_type else "Unknown",
            "priority": req.priority.label if req.priority else "Unknown",
            "current_status": req.current_status.label if req.current_status else "Unknown",
            "is_primary": assignment.is_primary,
            "is_reviewer": assignment.is_reviewer,
            "assignment_date": assignment.assignment_date.isoformat() if assignment.assignment_date else None,
            "estimated_hours": assignment.estimated_hours,
            "actual_hours": assignment.actual_hours,
            "reviewer_signed_off": assignment.reviewer_signed_off,
            "target_completion_date": req.target_completion_date.isoformat() if req.target_completion_date else None,
            "created_at": assignment.created_at.isoformat() if assignment.created_at else None
        })

    return result


@router.get("/dashboard/sla-violations")
def get_sla_violations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all SLA violations for validation requests (Admin only)."""
    check_admin(current_user)

    # Get SLA configuration
    from app.models.validation import ValidationWorkflowSLA
    sla_config = db.query(ValidationWorkflowSLA).filter(
        ValidationWorkflowSLA.workflow_type == "Validation"
    ).first()

    if not sla_config:
        return []

    # Get all non-terminal validation requests
    requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model),
        joinedload(ValidationRequest.current_status),
        joinedload(ValidationRequest.priority),
        joinedload(ValidationRequest.assignments).joinedload(ValidationAssignment.validator),
        joinedload(ValidationRequest.status_history).joinedload(ValidationStatusHistory.new_status)
    ).all()

    violations = []
    now = datetime.utcnow()

    for req in requests:
        if not req.current_status or req.current_status.code in ["APPROVED", "CANCELLED"]:
            continue

        # Check Assignment SLA (from request_date to first assignment)
        if req.current_status.code in ["INTAKE", "PLANNING"]:
            days_since_request = (now - req.created_at).days
            if days_since_request > sla_config.assignment_days:
                primary_assignment = next((a for a in req.assignments if a.is_primary), None)
                if not primary_assignment:
                    violations.append({
                        "request_id": req.request_id,
                        "model_name": req.model.model_name if req.model else "Unknown",
                        "violation_type": "Assignment Overdue",
                        "sla_days": sla_config.assignment_days,
                        "actual_days": days_since_request,
                        "days_overdue": days_since_request - sla_config.assignment_days,
                        "current_status": req.current_status.label,
                        "priority": req.priority.label if req.priority else "Unknown",
                        "severity": "high" if (days_since_request - sla_config.assignment_days) > 5 else "medium",
                        "timestamp": req.created_at.isoformat()
                    })

        # Check Begin Work SLA (from assignment to IN_PROGRESS)
        primary_assignment = next((a for a in req.assignments if a.is_primary), None)
        if primary_assignment and req.current_status.code == "PLANNING":
            days_since_assignment = (now.date() - primary_assignment.assignment_date).days
            if days_since_assignment > sla_config.begin_work_days:
                violations.append({
                    "request_id": req.request_id,
                    "model_name": req.model.model_name if req.model else "Unknown",
                    "violation_type": "Begin Work Overdue",
                    "sla_days": sla_config.begin_work_days,
                    "actual_days": days_since_assignment,
                    "days_overdue": days_since_assignment - sla_config.begin_work_days,
                    "current_status": req.current_status.label,
                    "priority": req.priority.label if req.priority else "Unknown",
                    "severity": "high" if (days_since_assignment - sla_config.begin_work_days) > 3 else "medium",
                    "timestamp": primary_assignment.assignment_date.isoformat()
                })

        # Check Complete Work SLA (from assignment to REVIEW/PENDING_APPROVAL)
        if primary_assignment and req.current_status.code == "IN_PROGRESS":
            days_since_assignment = (now.date() - primary_assignment.assignment_date).days
            if days_since_assignment > sla_config.complete_work_days:
                violations.append({
                    "request_id": req.request_id,
                    "model_name": req.model.model_name if req.model else "Unknown",
                    "violation_type": "Work Completion Overdue",
                    "sla_days": sla_config.complete_work_days,
                    "actual_days": days_since_assignment,
                    "days_overdue": days_since_assignment - sla_config.complete_work_days,
                    "current_status": req.current_status.label,
                    "priority": req.priority.label if req.priority else "Unknown",
                    "severity": "critical" if (days_since_assignment - sla_config.complete_work_days) > 10 else "high",
                    "timestamp": primary_assignment.assignment_date.isoformat()
                })

        # Check Approval SLA (from PENDING_APPROVAL status to APPROVED)
        if req.current_status.code == "PENDING_APPROVAL":
            # Find when it moved to PENDING_APPROVAL
            approval_history = next(
                (h for h in sorted(req.status_history, key=lambda x: x.changed_at, reverse=True)
                 if h.new_status.code == "PENDING_APPROVAL"),
                None
            )
            if approval_history:
                days_in_approval = (now - approval_history.changed_at).days
                if days_in_approval > sla_config.approval_days:
                    violations.append({
                        "request_id": req.request_id,
                        "model_name": req.model.model_name if req.model else "Unknown",
                        "violation_type": "Approval Overdue",
                        "sla_days": sla_config.approval_days,
                        "actual_days": days_in_approval,
                        "days_overdue": days_in_approval - sla_config.approval_days,
                        "current_status": req.current_status.label,
                        "priority": req.priority.label if req.priority else "Unknown",
                        "severity": "critical" if (days_in_approval - sla_config.approval_days) > 5 else "high",
                        "timestamp": approval_history.changed_at.isoformat()
                    })

    # Sort by days overdue (most overdue first)
    return sorted(violations, key=lambda x: x["days_overdue"], reverse=True)

"""Model delegates routes."""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.model_delegate import ModelDelegate
from app.models.audit_log import AuditLog
from app.schemas.model_delegate import (
    ModelDelegateCreate,
    ModelDelegateUpdate,
    ModelDelegateResponse,
    BatchDelegateRequest,
    BatchDelegateResponse,
    ModelDelegateDetail,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def check_model_owner(model: Model, user: User) -> bool:
    """Check if user is the model owner or admin."""
    if user.role == "Admin":
        return True
    if model.owner_id == user.user_id:
        return True
    return False


@router.post("/models/{model_id}/delegates", response_model=ModelDelegateResponse, status_code=status.HTTP_201_CREATED)
def create_delegate(
    model_id: int,
    delegate_data: ModelDelegateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new model delegation (owner or admin only)."""
    # Get model
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Only owner or admin can create delegations
    if not check_model_owner(model, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner or administrators can create delegations"
        )

    # Check if user exists
    delegate_user = db.query(User).filter(User.user_id == delegate_data.user_id).first()
    if not delegate_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user is already owner or developer (no need to delegate)
    if delegate_data.user_id == model.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delegate to model owner (already has full permissions)"
        )
    if delegate_data.user_id == model.developer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delegate to model developer (already has permissions)"
        )

    # Check if delegation already exists (including revoked ones)
    existing = db.query(ModelDelegate).filter(
        ModelDelegate.model_id == model_id,
        ModelDelegate.user_id == delegate_data.user_id
    ).first()

    if existing:
        if existing.revoked_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active delegation already exists for this user"
            )
        else:
            # Revoked delegation exists - update it instead
            existing.can_submit_changes = delegate_data.can_submit_changes
            existing.can_manage_regional = delegate_data.can_manage_regional
            existing.delegated_by_id = current_user.user_id
            existing.delegated_at = utc_now()
            existing.revoked_at = None
            existing.revoked_by_id = None

            create_audit_log(
                db=db,
                entity_type="ModelDelegate",
                entity_id=existing.delegate_id,
                action="RESTORE",
                user_id=current_user.user_id,
                changes={
                    "user_id": delegate_data.user_id,
                    "can_submit_changes": delegate_data.can_submit_changes,
                    "can_manage_regional": delegate_data.can_manage_regional
                }
            )

            db.commit()
            db.refresh(existing)
            return existing

    # Create new delegation
    new_delegate = ModelDelegate(
        model_id=model_id,
        user_id=delegate_data.user_id,
        can_submit_changes=delegate_data.can_submit_changes,
        can_manage_regional=delegate_data.can_manage_regional,
        delegated_by_id=current_user.user_id,
        delegated_at=utc_now()
    )

    db.add(new_delegate)
    db.commit()
    db.refresh(new_delegate)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="ModelDelegate",
        entity_id=new_delegate.delegate_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "user_id": delegate_data.user_id,
            "can_submit_changes": delegate_data.can_submit_changes,
            "can_manage_regional": delegate_data.can_manage_regional
        }
    )
    db.commit()

    return new_delegate


@router.get("/models/{model_id}/delegates", response_model=List[ModelDelegateResponse])
def list_delegates(
    model_id: int,
    include_revoked: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all delegations for a model (active by default)."""
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Build query
    query = db.query(ModelDelegate).filter(ModelDelegate.model_id == model_id)

    if not include_revoked:
        query = query.filter(ModelDelegate.revoked_at.is_(None))

    delegates = query.order_by(ModelDelegate.delegated_at.desc()).all()

    # Populate user names
    for delegate in delegates:
        delegate.user_name = delegate.user.full_name if delegate.user else None
        delegate.user_email = delegate.user.email if delegate.user else None
        delegate.delegated_by_name = delegate.delegated_by.full_name if delegate.delegated_by else None
        if delegate.revoked_by_id:
            delegate.revoked_by_name = delegate.revoked_by.full_name if delegate.revoked_by else None

    return delegates


@router.patch("/delegates/{delegate_id}", response_model=ModelDelegateResponse)
def update_delegate(
    delegate_id: int,
    delegate_update: ModelDelegateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update delegation permissions (owner or admin only)."""
    delegate = db.query(ModelDelegate).filter(ModelDelegate.delegate_id == delegate_id).first()
    if not delegate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delegation not found"
        )

    # Get model to check ownership
    model = db.query(Model).filter(Model.model_id == delegate.model_id).first()
    if not check_model_owner(model, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner or administrators can update delegations"
        )

    # Cannot update revoked delegations
    if delegate.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update revoked delegation"
        )

    # Update fields
    changes = {}
    if delegate_update.can_submit_changes is not None:
        old_value = delegate.can_submit_changes
        delegate.can_submit_changes = delegate_update.can_submit_changes
        changes["can_submit_changes"] = {"old": old_value, "new": delegate_update.can_submit_changes}

    if delegate_update.can_manage_regional is not None:
        old_value = delegate.can_manage_regional
        delegate.can_manage_regional = delegate_update.can_manage_regional
        changes["can_manage_regional"] = {"old": old_value, "new": delegate_update.can_manage_regional}

    if changes:
        create_audit_log(
            db=db,
            entity_type="ModelDelegate",
            entity_id=delegate.delegate_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(delegate)

    return delegate


@router.patch("/delegates/{delegate_id}/revoke", response_model=ModelDelegateResponse)
def revoke_delegate(
    delegate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke a delegation (owner or admin only, maintains audit trail)."""
    delegate = db.query(ModelDelegate).filter(ModelDelegate.delegate_id == delegate_id).first()
    if not delegate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delegation not found"
        )

    # Get model to check ownership
    model = db.query(Model).filter(Model.model_id == delegate.model_id).first()
    if not check_model_owner(model, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner or administrators can revoke delegations"
        )

    # Already revoked
    if delegate.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delegation already revoked"
        )

    # Revoke delegation
    delegate.revoked_at = utc_now()
    delegate.revoked_by_id = current_user.user_id

    create_audit_log(
        db=db,
        entity_type="ModelDelegate",
        entity_id=delegate.delegate_id,
        action="REVOKE",
        user_id=current_user.user_id,
        changes={"revoked_at": str(delegate.revoked_at)}
    )

    db.commit()
    db.refresh(delegate)

    return delegate


@router.delete("/delegates/{delegate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delegate(
    delegate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a delegation permanently (admin only, use revoke instead for audit trail)."""
    # Only admins can permanently delete
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can permanently delete delegations. Use revoke instead."
        )

    delegate = db.query(ModelDelegate).filter(ModelDelegate.delegate_id == delegate_id).first()
    if not delegate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delegation not found"
        )

    create_audit_log(
        db=db,
        entity_type="ModelDelegate",
        entity_id=delegate.delegate_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"user_id": delegate.user_id, "model_id": delegate.model_id}
    )

    db.delete(delegate)
    db.commit()

    return None


@router.post("/delegates/batch", response_model=BatchDelegateResponse)
def batch_add_delegates(
    batch_request: BatchDelegateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add or update a delegate for all models owned or developed by a specific user.
    Admin only operation.
    """
    # Only admins can perform batch operations
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform batch delegate operations"
        )

    # Verify target user exists
    target_user = db.query(User).filter(User.user_id == batch_request.target_user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found"
        )

    # Verify delegate user exists
    delegate_user = db.query(User).filter(User.user_id == batch_request.delegate_user_id).first()
    if not delegate_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delegate user not found"
        )

    # Cannot delegate to the same user
    if batch_request.target_user_id == batch_request.delegate_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delegate to the same user"
        )

    # Find all models for the target user
    query = db.query(Model)
    if batch_request.role == "owner":
        query = query.filter(Model.owner_id == batch_request.target_user_id)
    else:  # developer
        query = query.filter(Model.developer_id == batch_request.target_user_id)

    models = query.all()

    if not models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No models found where user is {batch_request.role}"
        )

    delegations_created = 0
    delegations_updated = 0
    delegations_revoked = 0
    model_details = []

    for model in models:
        # Skip if delegate user is already owner or developer of this model
        if batch_request.delegate_user_id == model.owner_id or batch_request.delegate_user_id == model.developer_id:
            continue

        action = None

        # If replace_existing is True, revoke all other active delegates for this model
        if batch_request.replace_existing:
            other_delegates = db.query(ModelDelegate).filter(
                ModelDelegate.model_id == model.model_id,
                ModelDelegate.user_id != batch_request.delegate_user_id,
                ModelDelegate.revoked_at.is_(None)
            ).all()

            for other_delegate in other_delegates:
                other_delegate.revoked_at = utc_now()
                other_delegate.revoked_by_id = current_user.user_id
                delegations_revoked += 1

        # Check if delegation already exists
        existing = db.query(ModelDelegate).filter(
            ModelDelegate.model_id == model.model_id,
            ModelDelegate.user_id == batch_request.delegate_user_id
        ).first()

        if existing:
            if existing.revoked_at is None:
                # Update existing active delegation
                existing.can_submit_changes = batch_request.can_submit_changes
                existing.can_manage_regional = batch_request.can_manage_regional
                delegations_updated += 1
                action = "replaced" if batch_request.replace_existing else "updated"
            else:
                # Restore revoked delegation
                existing.can_submit_changes = batch_request.can_submit_changes
                existing.can_manage_regional = batch_request.can_manage_regional
                existing.delegated_by_id = current_user.user_id
                existing.delegated_at = utc_now()
                existing.revoked_at = None
                existing.revoked_by_id = None
                delegations_created += 1
                action = "replaced" if batch_request.replace_existing else "created"
        else:
            # Create new delegation
            new_delegate = ModelDelegate(
                model_id=model.model_id,
                user_id=batch_request.delegate_user_id,
                can_submit_changes=batch_request.can_submit_changes,
                can_manage_regional=batch_request.can_manage_regional,
                delegated_by_id=current_user.user_id,
                delegated_at=utc_now()
            )
            db.add(new_delegate)
            delegations_created += 1
            action = "replaced" if batch_request.replace_existing else "created"

        model_details.append(ModelDelegateDetail(
            model_id=model.model_id,
            model_name=model.name,
            action=action
        ))

        # Audit log
        create_audit_log(
            db=db,
            entity_type="ModelDelegate",
            entity_id=model.model_id,
            action="BATCH_DELEGATE_REPLACE" if batch_request.replace_existing else "BATCH_DELEGATE",
            user_id=current_user.user_id,
            changes={
                "target_user_id": batch_request.target_user_id,
                "role": batch_request.role,
                "delegate_user_id": batch_request.delegate_user_id,
                "can_submit_changes": batch_request.can_submit_changes,
                "can_manage_regional": batch_request.can_manage_regional,
                "replace_existing": batch_request.replace_existing,
                "delegations_revoked": delegations_revoked if batch_request.replace_existing else 0
            }
        )

    db.commit()

    return BatchDelegateResponse(
        models_affected=len(model_details),
        model_details=model_details,
        delegations_created=delegations_created,
        delegations_updated=delegations_updated,
        delegations_revoked=delegations_revoked
    )

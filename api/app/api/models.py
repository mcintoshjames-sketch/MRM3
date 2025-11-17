"""Models routes."""
import csv
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.vendor import Vendor
from app.models.audit_log import AuditLog
from app.models.taxonomy import TaxonomyValue
from app.schemas.model import ModelCreate, ModelUpdate, ModelDetailResponse

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
    # Note: commit happens with the main transaction


@router.get("/", response_model=List[ModelDetailResponse])
def list_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all models with details."""
    models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories)
    ).all()
    return models


@router.post("/", response_model=ModelDetailResponse, status_code=status.HTTP_201_CREATED)
def create_model(
    model_data: ModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new model."""
    # Validate vendor requirement for third-party models
    if model_data.development_type == "Third-Party" and not model_data.vendor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor is required for third-party models"
        )

    # Validate vendor exists if provided
    if model_data.vendor_id:
        vendor = db.query(Vendor).filter(Vendor.vendor_id == model_data.vendor_id).first()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

    # Validate owner exists
    owner = db.query(User).filter(User.user_id == model_data.owner_id).first()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner user not found"
        )

    # Validate developer exists if provided
    if model_data.developer_id:
        developer = db.query(User).filter(User.user_id == model_data.developer_id).first()
        if not developer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer user not found"
            )

    # Extract user_ids and regulatory_category_ids before creating model
    user_ids = model_data.user_ids or []
    regulatory_category_ids = model_data.regulatory_category_ids or []
    model_dict = model_data.model_dump(exclude={'user_ids', 'regulatory_category_ids'})

    model = Model(**model_dict)

    # Add model users
    if user_ids:
        users = db.query(User).filter(User.user_id.in_(user_ids)).all()
        if len(users) != len(user_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more model users not found"
            )
        model.users = users

    # Add regulatory categories
    if regulatory_category_ids:
        categories = db.query(TaxonomyValue).filter(TaxonomyValue.value_id.in_(regulatory_category_ids)).all()
        if len(categories) != len(regulatory_category_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more regulatory categories not found"
            )
        model.regulatory_categories = categories

    db.add(model)
    db.commit()
    db.refresh(model)

    # Audit log for model creation
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model.model_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"model_name": model.model_name, "status": model.status, "development_type": model.development_type}
    )
    db.commit()

    # Reload with relationships
    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories)
    ).filter(Model.model_id == model.model_id).first()

    return model


@router.get("/{model_id}", response_model=ModelDetailResponse)
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific model with details."""
    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories)
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    return model


@router.patch("/{model_id}", response_model=ModelDetailResponse)
def update_model(
    model_id: int,
    model_data: ModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a model."""
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Authorization: only model owner or admin can update
    if model.owner_id != current_user.user_id and current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner or administrator can update this model"
        )

    update_data = model_data.model_dump(exclude_unset=True)

    # Handle development_type and vendor_id together
    new_dev_type = update_data.get('development_type', model.development_type)
    new_vendor_id = update_data.get('vendor_id', model.vendor_id)

    if new_dev_type == "Third-Party" and new_vendor_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor is required for third-party models"
        )

    # Validate vendor exists if provided
    if 'vendor_id' in update_data and update_data['vendor_id'] is not None:
        vendor = db.query(Vendor).filter(Vendor.vendor_id == update_data['vendor_id']).first()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

    # Validate owner exists if provided
    if 'owner_id' in update_data:
        owner = db.query(User).filter(User.user_id == update_data['owner_id']).first()
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Owner user not found"
            )

    # Validate developer exists if provided
    if 'developer_id' in update_data and update_data['developer_id'] is not None:
        developer = db.query(User).filter(User.user_id == update_data['developer_id']).first()
        if not developer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer user not found"
            )

    # Handle user_ids separately
    user_ids_changed = False
    if 'user_ids' in update_data:
        user_ids = update_data.pop('user_ids')
        if user_ids is not None:
            users = db.query(User).filter(User.user_id.in_(user_ids)).all()
            if len(users) != len(user_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more model users not found"
                )
            model.users = users
            user_ids_changed = True

    # Handle regulatory_category_ids separately
    regulatory_categories_changed = False
    if 'regulatory_category_ids' in update_data:
        category_ids = update_data.pop('regulatory_category_ids')
        if category_ids is not None:
            categories = db.query(TaxonomyValue).filter(TaxonomyValue.value_id.in_(category_ids)).all()
            if len(categories) != len(category_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more regulatory categories not found"
                )
            model.regulatory_categories = categories
            regulatory_categories_changed = True

    # Track changes for audit log
    changes_made = {}
    for field, value in update_data.items():
        old_value = getattr(model, field, None)
        if old_value != value:
            changes_made[field] = {"old": old_value, "new": value}
        setattr(model, field, value)

    if user_ids_changed:
        changes_made["user_ids"] = "modified"

    if regulatory_categories_changed:
        changes_made["regulatory_category_ids"] = "modified"

    # Audit log for model update
    if changes_made:
        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=model_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes_made
        )

    db.commit()
    db.refresh(model)

    # Reload with relationships
    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories)
    ).filter(Model.model_id == model.model_id).first()

    return model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a model."""
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Authorization: only model owner or admin can delete
    if model.owner_id != current_user.user_id and current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner or administrator can delete this model"
        )

    # Audit log for model deletion (before delete)
    model_name = model.model_name
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"model_name": model_name}
    )

    db.delete(model)
    db.commit()
    return None


@router.get("/export/csv")
def export_models_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export all models to CSV."""
    models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.users),
        joinedload(Model.regulatory_categories)
    ).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Model ID",
        "Model Name",
        "Description",
        "Development Type",
        "Model Type",
        "Status",
        "Owner",
        "Owner Email",
        "Developer",
        "Developer Email",
        "Vendor",
        "Risk Tier",
        "Validation Type",
        "Regulatory Categories",
        "Model Users",
        "Created At",
        "Updated At"
    ])

    # Write data rows
    for model in models:
        # Format model users as comma-separated list
        model_users_str = ", ".join([u.full_name for u in model.users]) if model.users else ""
        # Format regulatory categories as comma-separated list
        reg_categories_str = ", ".join([c.label for c in model.regulatory_categories]) if model.regulatory_categories else ""

        writer.writerow([
            model.model_id,
            model.model_name,
            model.description or "",
            model.development_type,
            model.model_type.label if model.model_type else "",
            model.status,
            model.owner.full_name if model.owner else "",
            model.owner.email if model.owner else "",
            model.developer.full_name if model.developer else "",
            model.developer.email if model.developer else "",
            model.vendor.name if model.vendor else "",
            model.risk_tier.label if model.risk_tier else "",
            model.validation_type.label if model.validation_type else "",
            reg_categories_str,
            model_users_str,
            model.created_at.isoformat() if model.created_at else "",
            model.updated_at.isoformat() if model.updated_at else ""
        ])

    # Reset stream position
    output.seek(0)

    # Return as streaming response
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=models_export.csv"
        }
    )

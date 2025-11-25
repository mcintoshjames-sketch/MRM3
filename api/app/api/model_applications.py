"""Model-Application Relationships API."""
from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rls import can_access_model, can_modify_model
from app.models.user import User
from app.models.model import Model
from app.models.map_application import MapApplication
from app.models.model_application import ModelApplication
from app.models.taxonomy import TaxonomyValue
from app.schemas.model_application import (
    ModelApplicationCreate,
    ModelApplicationUpdate,
    ModelApplicationResponse
)

router = APIRouter(prefix="/models/{model_id}/applications", tags=["Model Applications"])


@router.get("", response_model=List[ModelApplicationResponse])
def list_model_applications(
    model_id: int,
    include_inactive: bool = Query(False, description="Include relationships with end_date set"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all applications linked to a model.

    By default, only active relationships (end_date IS NULL) are returned.
    Set include_inactive=true to see all relationships including ended ones.
    """
    # Check model exists and user has access
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found"
        )

    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this model"
        )

    # Query relationships with eager loading
    query = db.query(ModelApplication).options(
        joinedload(ModelApplication.application),
        joinedload(ModelApplication.relationship_type),
        joinedload(ModelApplication.created_by_user)
    ).filter(ModelApplication.model_id == model_id)

    if not include_inactive:
        query = query.filter(ModelApplication.end_date.is_(None))

    query = query.order_by(ModelApplication.created_at.desc())
    relationships = query.all()

    return relationships


@router.post("", response_model=ModelApplicationResponse, status_code=status.HTTP_201_CREATED)
def add_model_application(
    model_id: int,
    data: ModelApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Link an application to a model.

    Requires permission to modify the model (Admin, Validator, or model owner/developer).
    """
    # Check model exists and user can modify it
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found"
        )

    # Check permission - Admin, Validator, or model owner/developer can add applications
    if current_user.role not in ['Admin', 'Validator']:
        if not can_modify_model(model_id, current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this model"
            )

    # Verify application exists
    application = db.query(MapApplication).filter(
        MapApplication.application_id == data.application_id
    ).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {data.application_id} not found in MAP"
        )

    # Verify relationship type is valid
    relationship_type = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == data.relationship_type_id
    ).first()
    if not relationship_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid relationship type ID: {data.relationship_type_id}"
        )

    # Check for existing active relationship
    existing = db.query(ModelApplication).filter(
        ModelApplication.model_id == model_id,
        ModelApplication.application_id == data.application_id,
        ModelApplication.end_date.is_(None)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An active relationship already exists between this model and application"
        )

    # Create the relationship
    relationship = ModelApplication(
        model_id=model_id,
        application_id=data.application_id,
        relationship_type_id=data.relationship_type_id,
        description=data.description,
        effective_date=data.effective_date or date.today(),
        created_by_user_id=current_user.user_id
    )
    db.add(relationship)
    db.commit()
    db.refresh(relationship)

    # Reload with relationships for response
    relationship = db.query(ModelApplication).options(
        joinedload(ModelApplication.application),
        joinedload(ModelApplication.relationship_type),
        joinedload(ModelApplication.created_by_user)
    ).filter(
        ModelApplication.model_id == model_id,
        ModelApplication.application_id == data.application_id
    ).first()

    return relationship


@router.patch("/{application_id}", response_model=ModelApplicationResponse)
def update_model_application(
    model_id: int,
    application_id: int,
    data: ModelApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a model-application relationship.

    Requires permission to modify the model (Admin, Validator, or model owner/developer).
    """
    # Check model exists and user can modify it
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found"
        )

    # Check permission
    if current_user.role not in ['Admin', 'Validator']:
        if not can_modify_model(model_id, current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this model"
            )

    # Find the relationship
    relationship = db.query(ModelApplication).filter(
        ModelApplication.model_id == model_id,
        ModelApplication.application_id == application_id
    ).first()
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No relationship found between model {model_id} and application {application_id}"
        )

    # Update fields
    if data.relationship_type_id is not None:
        # Verify relationship type is valid
        relationship_type = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == data.relationship_type_id
        ).first()
        if not relationship_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid relationship type ID: {data.relationship_type_id}"
            )
        relationship.relationship_type_id = data.relationship_type_id

    if data.description is not None:
        relationship.description = data.description

    if data.end_date is not None:
        if relationship.effective_date and data.end_date < relationship.effective_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date cannot be before effective date"
            )
        relationship.end_date = data.end_date

    db.commit()
    db.refresh(relationship)

    # Reload with relationships for response
    relationship = db.query(ModelApplication).options(
        joinedload(ModelApplication.application),
        joinedload(ModelApplication.relationship_type),
        joinedload(ModelApplication.created_by_user)
    ).filter(
        ModelApplication.model_id == model_id,
        ModelApplication.application_id == application_id
    ).first()

    return relationship


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_model_application(
    model_id: int,
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove (soft delete) a model-application relationship.

    Sets the end_date to today rather than deleting the record,
    preserving historical data for audit purposes.

    Requires permission to modify the model (Admin, Validator, or model owner/developer).
    """
    # Check model exists and user can modify it
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found"
        )

    # Check permission
    if current_user.role not in ['Admin', 'Validator']:
        if not can_modify_model(model_id, current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this model"
            )

    # Find the relationship
    relationship = db.query(ModelApplication).filter(
        ModelApplication.model_id == model_id,
        ModelApplication.application_id == application_id,
        ModelApplication.end_date.is_(None)  # Only can remove active relationships
    ).first()
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active relationship found between model {model_id} and application {application_id}"
        )

    # Soft delete by setting end_date
    relationship.end_date = date.today()
    db.commit()

    return None

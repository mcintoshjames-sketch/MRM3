"""Model hierarchy routes - parent-child relationships."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.model_hierarchy import ModelHierarchy
from app.models.taxonomy import TaxonomyValue
from app.models.audit_log import AuditLog
from app.schemas.model_relationships import (
    ModelHierarchyCreate,
    ModelHierarchyUpdate,
    ModelHierarchyResponse,
    ModelHierarchySummary,
    ModelInfo,
    RelationTypeInfo,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for model hierarchy changes."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def check_admin(user: User):
    """Check if user is admin."""
    if user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for hierarchy management"
        )


@router.get("/models/{model_id}/hierarchy/children", response_model=List[ModelHierarchySummary])
def list_children(
    model_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all child (sub) models of a given model.

    - **include_inactive**: If true, include relationships that have ended
    """
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Query child relationships
    query = db.query(ModelHierarchy).options(
        joinedload(ModelHierarchy.child_model),
        joinedload(ModelHierarchy.relation_type)
    ).filter(ModelHierarchy.parent_model_id == model_id)

    # Filter by active status if requested
    if not include_inactive:
        query = query.filter(
            (ModelHierarchy.end_date == None) | (
                ModelHierarchy.end_date >= func.current_date())
        )

    relationships = query.all()

    # Build response
    result = []
    for rel in relationships:
        result.append(ModelHierarchySummary(
            id=rel.id,
            model_id=rel.child_model.model_id,
            model_name=rel.child_model.model_name,
            relation_type=rel.relation_type.label if rel.relation_type else "Unknown",
            relation_type_id=rel.relation_type_id,
            effective_date=rel.effective_date,
            end_date=rel.end_date,
            notes=rel.notes
        ))

    return result


@router.get("/models/{model_id}/hierarchy/parents", response_model=List[ModelHierarchySummary])
def list_parents(
    model_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all parent models of a given model.

    - **include_inactive**: If true, include relationships that have ended
    """
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Query parent relationships
    query = db.query(ModelHierarchy).options(
        joinedload(ModelHierarchy.parent_model),
        joinedload(ModelHierarchy.relation_type)
    ).filter(ModelHierarchy.child_model_id == model_id)

    # Filter by active status if requested
    if not include_inactive:
        query = query.filter(
            (ModelHierarchy.end_date == None) | (
                ModelHierarchy.end_date >= func.current_date())
        )

    relationships = query.all()

    # Build response
    result = []
    for rel in relationships:
        result.append(ModelHierarchySummary(
            id=rel.id,
            model_id=rel.parent_model.model_id,
            model_name=rel.parent_model.model_name,
            relation_type=rel.relation_type.label if rel.relation_type else "Unknown",
            relation_type_id=rel.relation_type_id,
            effective_date=rel.effective_date,
            end_date=rel.end_date,
            notes=rel.notes
        ))

    return result


@router.post("/models/{model_id}/hierarchy", response_model=ModelHierarchyResponse, status_code=status.HTTP_201_CREATED)
def create_hierarchy(
    model_id: int,
    hierarchy_data: ModelHierarchyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new parent-child hierarchy relationship (Admin only).

    The model_id in the URL is the parent model.
    """
    check_admin(current_user)

    # Verify parent model exists
    parent_model = db.query(Model).filter(Model.model_id == model_id).first()
    if not parent_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent model not found"
        )

    # Verify child model exists
    child_model = db.query(Model).filter(
        Model.model_id == hierarchy_data.child_model_id).first()
    if not child_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child model not found"
        )

    # Prevent self-reference (database constraint will also catch this)
    if model_id == hierarchy_data.child_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model cannot be its own child (self-reference not allowed)"
        )

    # Check if child already has a parent (enforce single parent rule)
    existing_parent = db.query(ModelHierarchy).filter(
        ModelHierarchy.child_model_id == hierarchy_data.child_model_id,
        (ModelHierarchy.end_date == None) | (
            ModelHierarchy.end_date >= func.current_date())
    ).first()

    if existing_parent:
        existing_parent_model = db.query(Model).filter(
            Model.model_id == existing_parent.parent_model_id
        ).first()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{child_model.model_name}' already has a parent model ('{existing_parent_model.model_name}'). A model can only have one parent for clear ownership and governance. Use dependencies to model data flow relationships."
        )

    # Verify relation type exists
    relation_type = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == hierarchy_data.relation_type_id
    ).first()
    if not relation_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relation type not found"
        )

    # Validate date range
    if hierarchy_data.end_date and hierarchy_data.effective_date:
        if hierarchy_data.end_date < hierarchy_data.effective_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after or equal to effective date"
            )

    # Check for existing relationship
    existing = db.query(ModelHierarchy).filter(
        ModelHierarchy.parent_model_id == model_id,
        ModelHierarchy.child_model_id == hierarchy_data.child_model_id,
        ModelHierarchy.relation_type_id == hierarchy_data.relation_type_id,
        ModelHierarchy.effective_date == hierarchy_data.effective_date
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This hierarchy relationship already exists"
        )

    # Create hierarchy relationship
    hierarchy = ModelHierarchy(
        parent_model_id=model_id,
        child_model_id=hierarchy_data.child_model_id,
        relation_type_id=hierarchy_data.relation_type_id,
        effective_date=hierarchy_data.effective_date,
        end_date=hierarchy_data.end_date,
        notes=hierarchy_data.notes
    )
    db.add(hierarchy)
    db.flush()  # Get hierarchy ID before audit log

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="ModelHierarchy",
        entity_id=hierarchy.id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "parent_model_id": model_id,
            "parent_model_name": parent_model.model_name,
            "child_model_id": hierarchy_data.child_model_id,
            "child_model_name": child_model.model_name,
            "relation_type": relation_type.label,
            "effective_date": str(hierarchy_data.effective_date) if hierarchy_data.effective_date else None,
            "end_date": str(hierarchy_data.end_date) if hierarchy_data.end_date else None
        }
    )

    db.commit()
    db.refresh(hierarchy)

    # Build response with nested objects
    return ModelHierarchyResponse(
        id=hierarchy.id,
        parent_model_id=hierarchy.parent_model_id,
        child_model_id=hierarchy.child_model_id,
        relation_type_id=hierarchy.relation_type_id,
        effective_date=hierarchy.effective_date,
        end_date=hierarchy.end_date,
        notes=hierarchy.notes,
        parent_model=ModelInfo(
            model_id=parent_model.model_id, model_name=parent_model.model_name),
        child_model=ModelInfo(model_id=child_model.model_id,
                              model_name=child_model.model_name),
        relation_type=RelationTypeInfo(
            value_id=relation_type.value_id,
            code=relation_type.code,
            label=relation_type.label
        )
    )


@router.patch("/hierarchy/{hierarchy_id}", response_model=ModelHierarchyResponse)
def update_hierarchy(
    hierarchy_id: int,
    hierarchy_data: ModelHierarchyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a model hierarchy relationship (Admin only)."""
    check_admin(current_user)

    # Get existing hierarchy
    hierarchy = db.query(ModelHierarchy).options(
        joinedload(ModelHierarchy.parent_model),
        joinedload(ModelHierarchy.child_model),
        joinedload(ModelHierarchy.relation_type)
    ).filter(ModelHierarchy.id == hierarchy_id).first()

    if not hierarchy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hierarchy relationship not found"
        )

    # Track changes for audit log
    changes = {}
    update_data = hierarchy_data.model_dump(exclude_unset=True)

    # Validate relation type if being updated
    if "relation_type_id" in update_data:
        relation_type = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == update_data["relation_type_id"]
        ).first()
        if not relation_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relation type not found"
            )

    # Validate date range
    new_effective = update_data.get("effective_date", hierarchy.effective_date)
    new_end = update_data.get("end_date", hierarchy.end_date)
    if new_end and new_effective and new_end < new_effective:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after or equal to effective date"
        )

    # Track changes
    for field, value in update_data.items():
        old_value = getattr(hierarchy, field, None)
        if old_value != value:
            changes[field] = {
                "old": str(old_value) if old_value else None,
                "new": str(value) if value else None
            }
            setattr(hierarchy, field, value)

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="ModelHierarchy",
            entity_id=hierarchy_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(hierarchy)

    # Build response
    return ModelHierarchyResponse(
        id=hierarchy.id,
        parent_model_id=hierarchy.parent_model_id,
        child_model_id=hierarchy.child_model_id,
        relation_type_id=hierarchy.relation_type_id,
        effective_date=hierarchy.effective_date,
        end_date=hierarchy.end_date,
        notes=hierarchy.notes,
        parent_model=ModelInfo(
            model_id=hierarchy.parent_model.model_id,
            model_name=hierarchy.parent_model.model_name
        ),
        child_model=ModelInfo(
            model_id=hierarchy.child_model.model_id,
            model_name=hierarchy.child_model.model_name
        ),
        relation_type=RelationTypeInfo(
            value_id=hierarchy.relation_type.value_id,
            code=hierarchy.relation_type.code,
            label=hierarchy.relation_type.label
        )
    )


@router.delete("/hierarchy/{hierarchy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hierarchy(
    hierarchy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a model hierarchy relationship (Admin only)."""
    check_admin(current_user)

    # Get existing hierarchy
    hierarchy = db.query(ModelHierarchy).options(
        joinedload(ModelHierarchy.parent_model),
        joinedload(ModelHierarchy.child_model),
        joinedload(ModelHierarchy.relation_type)
    ).filter(ModelHierarchy.id == hierarchy_id).first()

    if not hierarchy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hierarchy relationship not found"
        )

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="ModelHierarchy",
        entity_id=hierarchy_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "parent_model_id": hierarchy.parent_model_id,
            "parent_model_name": hierarchy.parent_model.model_name,
            "child_model_id": hierarchy.child_model_id,
            "child_model_name": hierarchy.child_model.model_name,
            "relation_type": hierarchy.relation_type.label if hierarchy.relation_type else None
        }
    )

    db.delete(hierarchy)
    db.commit()

    return None

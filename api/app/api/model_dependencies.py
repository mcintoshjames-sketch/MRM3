"""Model dependency routes - feeder-consumer data flow relationships with cycle detection."""
from typing import List, Set
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.model_feed_dependency import ModelFeedDependency
from app.models.taxonomy import TaxonomyValue
from app.models.audit_log import AuditLog
from app.schemas.model_relationships import (
    ModelFeedDependencyCreate,
    ModelFeedDependencyUpdate,
    ModelFeedDependencyResponse,
    ModelDependencySummary,
    ModelInfo,
    DependencyTypeInfo,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for model dependency changes."""
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
            detail="Admin access required for dependency management"
        )


def detect_cycle(
    db: Session,
    feeder_model_id: int,
    consumer_model_id: int,
    exclude_dependency_id: int = None
) -> tuple[bool, List[int]]:
    """
    Detect if adding this dependency would create a cycle in the dependency graph.

    Returns: (has_cycle: bool, cycle_path: List[int])
    If has_cycle is True, cycle_path contains the model IDs in the cycle.

    Algorithm: DFS from consumer_model_id to see if we can reach feeder_model_id.
    If we can, adding feeder->consumer would create a cycle.
    """
    # Build adjacency list from existing dependencies (excluding the one being updated)
    query = db.query(ModelFeedDependency).filter(
        ModelFeedDependency.is_active == True)
    if exclude_dependency_id:
        query = query.filter(ModelFeedDependency.id != exclude_dependency_id)

    dependencies = query.all()

    # Build graph: node -> list of nodes it feeds into
    graph = {}
    for dep in dependencies:
        if dep.feeder_model_id not in graph:
            graph[dep.feeder_model_id] = []
        graph[dep.feeder_model_id].append(dep.consumer_model_id)

    # DFS to check if consumer_model_id can reach feeder_model_id
    def dfs(current: int, target: int, visited: Set[int], path: List[int]) -> tuple[bool, List[int]]:
        if current == target:
            return True, path + [current]

        visited.add(current)
        path.append(current)

        if current in graph:
            for neighbor in graph[current]:
                if neighbor not in visited:
                    found, found_path = dfs(neighbor, target, visited, path[:])
                    if found:
                        return True, found_path

        return False, []

    # Check if adding this edge creates a cycle
    # We're adding feeder -> consumer
    # So check if consumer can already reach feeder
    has_cycle, cycle_path = dfs(consumer_model_id, feeder_model_id, set(), [])

    if has_cycle:
        # Complete the cycle by adding the new edge
        cycle_path.append(consumer_model_id)

    return has_cycle, cycle_path


@router.get("/models/{model_id}/dependencies/inbound", response_model=List[ModelDependencySummary])
def list_inbound_dependencies(
    model_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all inbound dependencies (feeders) for a model.

    Returns models that feed data TO this model.
    """
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Query inbound dependencies (where this model is the consumer)
    query = db.query(ModelFeedDependency).options(
        joinedload(ModelFeedDependency.feeder_model),
        joinedload(ModelFeedDependency.dependency_type)
    ).filter(ModelFeedDependency.consumer_model_id == model_id)

    # Filter by active status if requested
    if not include_inactive:
        query = query.filter(ModelFeedDependency.is_active == True)
        query = query.filter(
            (ModelFeedDependency.end_date == None) | (
                ModelFeedDependency.end_date >= func.current_date())
        )

    dependencies = query.all()

    # Build response
    result = []
    for dep in dependencies:
        result.append(ModelDependencySummary(
            id=dep.id,
            model_id=dep.feeder_model.model_id,
            model_name=dep.feeder_model.model_name,
            dependency_type=dep.dependency_type.label if dep.dependency_type else "Unknown",
            dependency_type_id=dep.dependency_type_id,
            description=dep.description,
            is_active=dep.is_active,
            effective_date=dep.effective_date,
            end_date=dep.end_date
        ))

    return result


@router.get("/models/{model_id}/dependencies/outbound", response_model=List[ModelDependencySummary])
def list_outbound_dependencies(
    model_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all outbound dependencies (consumers) for a model.

    Returns models that receive data FROM this model.
    """
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Query outbound dependencies (where this model is the feeder)
    query = db.query(ModelFeedDependency).options(
        joinedload(ModelFeedDependency.consumer_model),
        joinedload(ModelFeedDependency.dependency_type)
    ).filter(ModelFeedDependency.feeder_model_id == model_id)

    # Filter by active status if requested
    if not include_inactive:
        query = query.filter(ModelFeedDependency.is_active == True)
        query = query.filter(
            (ModelFeedDependency.end_date == None) | (
                ModelFeedDependency.end_date >= func.current_date())
        )

    dependencies = query.all()

    # Build response
    result = []
    for dep in dependencies:
        result.append(ModelDependencySummary(
            id=dep.id,
            model_id=dep.consumer_model.model_id,
            model_name=dep.consumer_model.model_name,
            dependency_type=dep.dependency_type.label if dep.dependency_type else "Unknown",
            dependency_type_id=dep.dependency_type_id,
            description=dep.description,
            is_active=dep.is_active,
            effective_date=dep.effective_date,
            end_date=dep.end_date
        ))

    return result


@router.post("/models/{model_id}/dependencies", response_model=ModelFeedDependencyResponse, status_code=status.HTTP_201_CREATED)
def create_dependency(
    model_id: int,
    dependency_data: ModelFeedDependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new model dependency (Admin only).

    The model_id in the URL is the feeder model.
    Validates that the new dependency does not create a cycle.
    """
    check_admin(current_user)

    # Verify feeder model exists
    feeder_model = db.query(Model).filter(Model.model_id == model_id).first()
    if not feeder_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeder model not found"
        )

    # Verify consumer model exists
    consumer_model = db.query(Model).filter(
        Model.model_id == dependency_data.consumer_model_id).first()
    if not consumer_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consumer model not found"
        )

    # Prevent self-reference (database constraint will also catch this)
    if model_id == dependency_data.consumer_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model cannot depend on itself (self-reference not allowed)"
        )

    # Verify dependency type exists
    dependency_type = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == dependency_data.dependency_type_id
    ).first()
    if not dependency_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency type not found"
        )

    # Validate date range
    if dependency_data.end_date and dependency_data.effective_date:
        if dependency_data.end_date < dependency_data.effective_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after or equal to effective date"
            )

    # CRITICAL: Check for cycles in dependency graph
    has_cycle, cycle_path = detect_cycle(
        db, model_id, dependency_data.consumer_model_id)
    if has_cycle:
        # Get model names for the cycle path
        cycle_models = db.query(Model).filter(
            Model.model_id.in_(cycle_path)).all()
        model_map = {m.model_id: m.model_name for m in cycle_models}
        cycle_names = [model_map.get(
            mid, f"Model {mid}") for mid in cycle_path]

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "dependency_cycle_detected",
                "message": "Adding this dependency would create a cycle in the dependency graph",
                "cycle_path": cycle_path,
                "cycle_names": cycle_names,
                "cycle_description": " → ".join(cycle_names)
            }
        )

    # Check for existing dependency
    existing = db.query(ModelFeedDependency).filter(
        ModelFeedDependency.feeder_model_id == model_id,
        ModelFeedDependency.consumer_model_id == dependency_data.consumer_model_id,
        ModelFeedDependency.dependency_type_id == dependency_data.dependency_type_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dependency relationship already exists"
        )

    # Create dependency relationship
    dependency = ModelFeedDependency(
        feeder_model_id=model_id,
        consumer_model_id=dependency_data.consumer_model_id,
        dependency_type_id=dependency_data.dependency_type_id,
        description=dependency_data.description,
        effective_date=dependency_data.effective_date,
        end_date=dependency_data.end_date,
        is_active=dependency_data.is_active
    )
    db.add(dependency)
    db.flush()  # Get dependency ID before audit log

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="ModelFeedDependency",
        entity_id=dependency.id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "feeder_model_id": model_id,
            "feeder_model_name": feeder_model.model_name,
            "consumer_model_id": dependency_data.consumer_model_id,
            "consumer_model_name": consumer_model.model_name,
            "dependency_type": dependency_type.label,
            "description": dependency_data.description,
            "is_active": dependency_data.is_active
        }
    )

    db.commit()
    db.refresh(dependency)

    # Build response with nested objects
    return ModelFeedDependencyResponse(
        id=dependency.id,
        feeder_model_id=dependency.feeder_model_id,
        consumer_model_id=dependency.consumer_model_id,
        dependency_type_id=dependency.dependency_type_id,
        description=dependency.description,
        effective_date=dependency.effective_date,
        end_date=dependency.end_date,
        is_active=dependency.is_active,
        feeder_model=ModelInfo(
            model_id=feeder_model.model_id, model_name=feeder_model.model_name),
        consumer_model=ModelInfo(
            model_id=consumer_model.model_id, model_name=consumer_model.model_name),
        dependency_type=DependencyTypeInfo(
            value_id=dependency_type.value_id,
            code=dependency_type.code,
            label=dependency_type.label
        )
    )


@router.patch("/dependencies/{dependency_id}", response_model=ModelFeedDependencyResponse)
def update_dependency(
    dependency_id: int,
    dependency_data: ModelFeedDependencyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a model dependency (Admin only)."""
    check_admin(current_user)

    # Get existing dependency
    dependency = db.query(ModelFeedDependency).options(
        joinedload(ModelFeedDependency.feeder_model),
        joinedload(ModelFeedDependency.consumer_model),
        joinedload(ModelFeedDependency.dependency_type)
    ).filter(ModelFeedDependency.id == dependency_id).first()

    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency relationship not found"
        )

    # Track changes for audit log
    changes = {}
    update_data = dependency_data.model_dump(exclude_unset=True)

    # Validate dependency type if being updated
    if "dependency_type_id" in update_data:
        dep_type = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == update_data["dependency_type_id"]
        ).first()
        if not dep_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dependency type not found"
            )

    # Validate date range
    new_effective = update_data.get(
        "effective_date", dependency.effective_date)
    new_end = update_data.get("end_date", dependency.end_date)
    if new_end and new_effective and new_end < new_effective:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after or equal to effective date"
        )

    # Track changes
    for field, value in update_data.items():
        old_value = getattr(dependency, field, None)
        if old_value != value:
            changes[field] = {
                "old": str(old_value) if old_value else None,
                "new": str(value) if value else None
            }
            setattr(dependency, field, value)

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="ModelFeedDependency",
            entity_id=dependency_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(dependency)

    # Build response
    return ModelFeedDependencyResponse(
        id=dependency.id,
        feeder_model_id=dependency.feeder_model_id,
        consumer_model_id=dependency.consumer_model_id,
        dependency_type_id=dependency.dependency_type_id,
        description=dependency.description,
        effective_date=dependency.effective_date,
        end_date=dependency.end_date,
        is_active=dependency.is_active,
        feeder_model=ModelInfo(
            model_id=dependency.feeder_model.model_id,
            model_name=dependency.feeder_model.model_name
        ),
        consumer_model=ModelInfo(
            model_id=dependency.consumer_model.model_id,
            model_name=dependency.consumer_model.model_name
        ),
        dependency_type=DependencyTypeInfo(
            value_id=dependency.dependency_type.value_id,
            code=dependency.dependency_type.code,
            label=dependency.dependency_type.label
        )
    )


@router.delete("/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependency(
    dependency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a model dependency (Admin only)."""
    check_admin(current_user)

    # Get existing dependency
    dependency = db.query(ModelFeedDependency).options(
        joinedload(ModelFeedDependency.feeder_model),
        joinedload(ModelFeedDependency.consumer_model),
        joinedload(ModelFeedDependency.dependency_type)
    ).filter(ModelFeedDependency.id == dependency_id).first()

    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency relationship not found"
        )

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="ModelFeedDependency",
        entity_id=dependency_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "feeder_model_id": dependency.feeder_model_id,
            "feeder_model_name": dependency.feeder_model.model_name,
            "consumer_model_id": dependency.consumer_model_id,
            "consumer_model_name": dependency.consumer_model.model_name,
            "dependency_type": dependency.dependency_type.label if dependency.dependency_type else None
        }
    )

    db.delete(dependency)
    db.commit()

    return None

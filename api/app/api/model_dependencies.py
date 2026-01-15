"""Model dependency routes - feeder-consumer data flow relationships with cycle detection."""
from typing import List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.models.user import User
from app.models.model import Model
from app.models.model_feed_dependency import ModelFeedDependency
from app.models.model_application import ModelApplication
from app.models.model_hierarchy import ModelHierarchy
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
import io
import math
from fastapi.responses import StreamingResponse
from fpdf import FPDF

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict | None = None):
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
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for dependency management"
        )


# --- Hierarchy bulk loading helpers for lineage ---

def _collect_all_model_ids_from_lineage(lineage_data: dict) -> Set[int]:
    """Recursively collect all model_ids from the lineage tree."""
    ids: Set[int] = set()

    def collect_from_node(node: dict):
        if node.get("node_type") == "model" and "model_id" in node:
            ids.add(node["model_id"])
        # Recurse into upstream/downstream
        for upstream in node.get("upstream", []):
            collect_from_node(upstream)
        for downstream in node.get("downstream", []):
            collect_from_node(downstream)

    # Center model
    if "model" in lineage_data:
        collect_from_node(lineage_data["model"])

    # Upstream tree
    for node in lineage_data.get("upstream", []):
        collect_from_node(node)

    # Downstream tree
    for node in lineage_data.get("downstream", []):
        collect_from_node(node)

    return ids


def _bulk_load_hierarchy(
    db: Session,
    model_ids: Set[int],
    include_inactive: bool = False
) -> dict[int, dict]:
    """
    Bulk fetch all hierarchy relationships for given model IDs.

    Returns: {model_id: {"parent": {...} or None, "children": [...]}}
    """
    if not model_ids:
        return {}

    # Initialize result with empty hierarchy for all models
    result: dict[int, dict] = {mid: {"parent": None, "children": []} for mid in model_ids}

    # Build query for all hierarchy relationships involving these models
    query = db.query(ModelHierarchy).options(
        joinedload(ModelHierarchy.parent_model),
        joinedload(ModelHierarchy.child_model),
        joinedload(ModelHierarchy.relation_type)
    ).filter(
        (ModelHierarchy.parent_model_id.in_(model_ids)) |
        (ModelHierarchy.child_model_id.in_(model_ids))
    )

    if not include_inactive:
        query = query.filter(
            (ModelHierarchy.end_date == None) |
            (ModelHierarchy.end_date >= func.current_date())
        )

    # Order by ID for deterministic parent selection in case of legacy data with multiple parents
    query = query.order_by(ModelHierarchy.id.asc())

    relationships = query.all()

    # Build the hierarchy map
    for rel in relationships:
        relation_label = rel.relation_type.label if rel.relation_type else "Sub-Model"

        # If this model is a child, set its parent
        if rel.child_model_id in model_ids:
            # Only set parent if not already set (single-parent rule, take first)
            if result[rel.child_model_id]["parent"] is None:
                result[rel.child_model_id]["parent"] = {
                    "model_id": rel.parent_model.model_id,
                    "model_name": rel.parent_model.model_name,
                    "relation_type": relation_label
                }

        # If this model is a parent, add to its children
        if rel.parent_model_id in model_ids:
            result[rel.parent_model_id]["children"].append({
                "model_id": rel.child_model.model_id,
                "model_name": rel.child_model.model_name,
                "relation_type": relation_label
            })

    return result


def _attach_hierarchy_to_nodes(lineage_data: dict, hierarchy_map: dict[int, dict]):
    """Recursively attach hierarchy data to all model nodes in the lineage tree."""

    def attach_to_node(node: dict):
        if node.get("node_type") == "model" and "model_id" in node:
            model_id = node["model_id"]
            if model_id in hierarchy_map:
                node["hierarchy"] = hierarchy_map[model_id]
        # Recurse into upstream/downstream
        for upstream in node.get("upstream", []):
            attach_to_node(upstream)
        for downstream in node.get("downstream", []):
            attach_to_node(downstream)

    # Center model
    if "model" in lineage_data:
        attach_to_node(lineage_data["model"])

    # Upstream tree
    for node in lineage_data.get("upstream", []):
        attach_to_node(node)

    # Downstream tree
    for node in lineage_data.get("downstream", []):
        attach_to_node(node)


def detect_cycle(
    db: Session,
    feeder_model_id: int,
    consumer_model_id: int,
    exclude_dependency_id: Optional[int] = None
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


@router.get("/models/{model_id}/dependencies/lineage", response_model=dict)
def get_dependency_lineage(
    model_id: int,
    direction: str = "both",  # "upstream", "downstream", or "both"
    max_depth: int = 10,
    include_inactive: bool = False,
    include_hierarchy: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trace the dependency lineage (data flow chain) for a model.

    Returns upstream feeders, downstream consumers, or both in a structured format
    showing the complete data flow chain. Useful for impact analysis and lineage visualization.

    Parameters:
    - direction: "upstream" (feeders), "downstream" (consumers), or "both"
    - max_depth: Maximum depth to traverse (default 10, prevents infinite loops)
    - include_inactive: Include inactive dependencies
    - include_hierarchy: Include parent/sub-model hierarchy for each model node

    Returns a dictionary with:
    - model: The center model info (with optional hierarchy)
    - upstream: List of upstream dependencies (models that feed this model)
    - downstream: List of downstream dependencies (models that consume from this model)
    """
    # Verify model exists
    model = db.query(Model).options(joinedload(Model.owner)).filter(
        Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    application_cache: dict[int, tuple[list[dict], list[dict]]] = {}

    def load_application_nodes(target_model_id: int) -> tuple[list[dict], list[dict]]:
        """Load upstream/downstream application nodes for a model, excluding UNKNOWN."""
        if target_model_id in application_cache:
            return application_cache[target_model_id]

        query = db.query(ModelApplication).options(
            joinedload(ModelApplication.application),
            joinedload(ModelApplication.relationship_type),
        ).filter(ModelApplication.model_id == target_model_id)

        if not include_inactive:
            query = query.filter(ModelApplication.end_date.is_(None))

        relationships = query.all()

        upstream_apps: list[dict] = []
        downstream_apps: list[dict] = []
        for rel in relationships:
            direction = (rel.relationship_direction or "UNKNOWN").upper()
            if direction not in ["UPSTREAM", "DOWNSTREAM"]:
                continue

            app = rel.application
            app_node = {
                "node_type": "application",
                "application_id": app.application_id,
                "application_code": app.application_code,
                "application_name": app.application_name,
                "owner_name": app.owner_name,
                "relationship_type": rel.relationship_type.label if rel.relationship_type else "Unknown",
                "relationship_direction": direction,
                "description": rel.description,
            }

            if direction == "UPSTREAM":
                upstream_apps.append(app_node)
            else:
                downstream_apps.append(app_node)

        application_cache[target_model_id] = (upstream_apps, downstream_apps)
        return application_cache[target_model_id]

    def trace_upstream(
        consumer_id: int,
        depth: int = 0,
        visited: Optional[Set[int]] = None
    ) -> List[dict]:
        """Recursively trace upstream feeders."""
        if visited is None:
            visited = set()

        if depth >= max_depth or consumer_id in visited:
            return []

        visited.add(consumer_id)

        # Query feeder dependencies
        query = db.query(ModelFeedDependency).options(
            joinedload(ModelFeedDependency.feeder_model).joinedload(
                Model.owner),
            joinedload(ModelFeedDependency.dependency_type)
        ).filter(ModelFeedDependency.consumer_model_id == consumer_id)

        if not include_inactive:
            query = query.filter(ModelFeedDependency.is_active == True)
            query = query.filter(
                (ModelFeedDependency.end_date == None) | (
                    ModelFeedDependency.end_date >= func.current_date())
            )

        dependencies = query.all()

        result = []
        for dep in dependencies:
            upstream_apps, downstream_apps = load_application_nodes(dep.feeder_model.model_id)
            feeder_dict = {
                "node_type": "model",
                "model_id": dep.feeder_model.model_id,
                "model_name": dep.feeder_model.model_name,
                "owner_name": dep.feeder_model.owner.full_name if dep.feeder_model.owner else "Unknown",
                "dependency_type": dep.dependency_type.label if dep.dependency_type else "Unknown",
                "description": dep.description,
                "depth": depth + 1,
                "upstream_applications": upstream_apps,
                "downstream_applications": downstream_apps,
                "upstream": trace_upstream(dep.feeder_model.model_id, depth + 1, visited)
            }
            result.append(feeder_dict)

        return result

    def trace_downstream(
        feeder_id: int,
        depth: int = 0,
        visited: Optional[Set[int]] = None
    ) -> List[dict]:
        """Recursively trace downstream consumers."""
        if visited is None:
            visited = set()

        if depth >= max_depth or feeder_id in visited:
            return []

        visited.add(feeder_id)

        # Query consumer dependencies
        query = db.query(ModelFeedDependency).options(
            joinedload(ModelFeedDependency.consumer_model).joinedload(
                Model.owner),
            joinedload(ModelFeedDependency.dependency_type)
        ).filter(ModelFeedDependency.feeder_model_id == feeder_id)

        if not include_inactive:
            query = query.filter(ModelFeedDependency.is_active == True)
            query = query.filter(
                (ModelFeedDependency.end_date == None) | (
                    ModelFeedDependency.end_date >= func.current_date())
            )

        dependencies = query.all()

        result = []
        for dep in dependencies:
            upstream_apps, downstream_apps = load_application_nodes(dep.consumer_model.model_id)
            consumer_dict = {
                "node_type": "model",
                "model_id": dep.consumer_model.model_id,
                "model_name": dep.consumer_model.model_name,
                "owner_name": dep.consumer_model.owner.full_name if dep.consumer_model.owner else "Unknown",
                "dependency_type": dep.dependency_type.label if dep.dependency_type else "Unknown",
                "description": dep.description,
                "depth": depth + 1,
                "upstream_applications": upstream_apps,
                "downstream_applications": downstream_apps,
                "downstream": trace_downstream(dep.consumer_model.model_id, depth + 1, visited)
            }
            result.append(consumer_dict)

        return result

    # Build response
    root_upstream_apps, root_downstream_apps = load_application_nodes(model.model_id)
    response: dict[str, object] = {
        "model": {
            "node_type": "model",
            "model_id": model.model_id,
            "model_name": model.model_name,
            "owner_name": model.owner.full_name if model.owner else "Unknown",
            "upstream_applications": root_upstream_apps,
            "downstream_applications": root_downstream_apps,
        }
    }

    if direction in ["upstream", "both"]:
        response["upstream"] = trace_upstream(model_id)

    if direction in ["downstream", "both"]:
        response["downstream"] = trace_downstream(model_id)

    # Attach hierarchy data if requested (bulk fetch for performance)
    if include_hierarchy:
        all_model_ids = _collect_all_model_ids_from_lineage(response)
        hierarchy_map = _bulk_load_hierarchy(db, all_model_ids, include_inactive)
        _attach_hierarchy_to_nodes(response, hierarchy_map)

    return response


class LineagePDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'End-to-End Model Lineage Paths', border=False,
                  align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

    # Hierarchy constants
    HIER_BOX_W = 40  # Smaller boxes for hierarchy nodes
    HIER_BOX_H = 15
    HIER_GAP = 8     # Gap between main node and hierarchy
    MAX_VISIBLE_CHILDREN = 3  # Truncate if more

    # Box dimensions (for reference in metrics calculation)
    BOX_W = 50
    BOX_H = 25
    GAP = 10

    # Colors
    COLORS = {
        'center': {'fill': (235, 248, 255), 'border': (66, 153, 225)},
        'upstream': {'fill': (240, 253, 244), 'border': (74, 222, 128)},
        'downstream': {'fill': (250, 245, 255), 'border': (192, 132, 252)},
        'application': {'fill': (255, 251, 235), 'border': (245, 158, 11)},
        'hierarchy': {'fill': (236, 254, 255), 'border': (34, 211, 238)},
    }

    def _calculate_row_metrics(self, path: list) -> dict:
        """Calculate consistent row height based on max hierarchy requirements."""
        extra_top = 0
        extra_bottom = 0

        for node in path:
            hier = node.get('hierarchy', {})
            if hier and hier.get('parent'):
                extra_top = max(extra_top, self.HIER_BOX_H + self.HIER_GAP)
            if hier and hier.get('children'):
                extra_bottom = max(extra_bottom, self.HIER_BOX_H + self.HIER_GAP)

        return {
            "extra_top": extra_top,
            "extra_bottom": extra_bottom,
            "row_height": extra_top + self.BOX_H + extra_bottom + self.GAP + 10
        }

    def _draw_dashed_line(self, x1: float, y1: float, x2: float, y2: float, dash_len: float = 2, gap_len: float = 1):
        """Draw a dashed line between two points."""
        length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length == 0:
            return

        # Unit direction vector
        ux = (x2 - x1) / length
        uy = (y2 - y1) / length

        cx, cy = x1, y1
        drawing = True
        traveled = 0

        while traveled < length:
            if drawing:
                step = min(dash_len, length - traveled)
                ex = cx + ux * step
                ey = cy + uy * step
                self.line(cx, cy, ex, ey)
                cx, cy = ex, ey
                traveled += step
            else:
                step = min(gap_len, length - traveled)
                cx += ux * step
                cy += uy * step
                traveled += step
            drawing = not drawing

    def _draw_hierarchy_node(self, x: float, y: float, node_info: dict, is_parent: bool = True):
        """Draw a smaller hierarchy node (parent or child)."""
        colors = self.COLORS['hierarchy']
        self.set_fill_color(*colors['fill'])
        self.set_draw_color(*colors['border'])
        self.set_line_width(0.3)

        self.rect(x, y, self.HIER_BOX_W, self.HIER_BOX_H, style='FD')

        # Model name (truncated)
        self.set_xy(x + 1, y + 2)
        self.set_font("helvetica", 'B', 7)
        self.set_text_color(0, 0, 0)
        name = node_info.get('model_name', 'Unknown')
        if len(name) > 18:
            name = name[:15] + '...'
        self.cell(self.HIER_BOX_W - 2, 4, name, align='C')

        # Relation type
        self.set_xy(x + 1, y + 7)
        self.set_font("helvetica", '', 6)
        self.set_text_color(80, 80, 80)
        rel_type = node_info.get('relation_type', 'Sub-Model')
        prefix = "Parent" if is_parent else "Child"
        self.cell(self.HIER_BOX_W - 2, 3, f"[{prefix}: {rel_type}]", align='C')

        # Model ID
        self.set_xy(x + 1, y + 11)
        self.set_font("helvetica", '', 5)
        model_id = node_info.get('model_id', '?')
        self.cell(self.HIER_BOX_W - 2, 3, f"ID: {model_id}", align='C')

    def _draw_hierarchy_for_node(self, node_x: float, node_y: float, box_w: float, box_h: float, hierarchy_info: dict):
        """Draw parent above and children below a main node."""
        node_center_x = node_x + box_w / 2

        # Draw parent above
        parent = hierarchy_info.get('parent')
        if parent:
            parent_x = node_center_x - self.HIER_BOX_W / 2
            parent_y = node_y - self.HIER_GAP - self.HIER_BOX_H

            self._draw_hierarchy_node(parent_x, parent_y, parent, is_parent=True)

            # Draw dashed line from parent bottom to node top
            self.set_draw_color(*self.COLORS['hierarchy']['border'])
            self.set_line_width(0.2)
            self._draw_dashed_line(
                node_center_x, parent_y + self.HIER_BOX_H,
                node_center_x, node_y
            )

        # Draw children below (max 3 visible)
        children = hierarchy_info.get('children', [])[:self.MAX_VISIBLE_CHILDREN]
        if children:
            total_width = len(children) * self.HIER_BOX_W + (len(children) - 1) * 5
            start_x = node_center_x - total_width / 2
            child_y = node_y + box_h + self.HIER_GAP

            for i, child in enumerate(children):
                child_x = start_x + i * (self.HIER_BOX_W + 5)
                self._draw_hierarchy_node(child_x, child_y, child, is_parent=False)

                # Draw dashed line from node bottom to child top
                child_center_x = child_x + self.HIER_BOX_W / 2
                self.set_draw_color(*self.COLORS['hierarchy']['border'])
                self.set_line_width(0.2)
                self._draw_dashed_line(
                    node_center_x, node_y + box_h,
                    child_center_x, child_y
                )

            # Indicate more children if truncated
            all_children = hierarchy_info.get('children', [])
            if len(all_children) > self.MAX_VISIBLE_CHILDREN:
                more_count = len(all_children) - self.MAX_VISIBLE_CHILDREN
                self.set_xy(start_x + total_width + 3, child_y + self.HIER_BOX_H / 2 - 2)
                self.set_font("helvetica", 'I', 6)
                self.set_text_color(100, 100, 100)
                self.cell(20, 4, f"+{more_count} more")

    def draw_legend(self):
        """Draw legend explaining visual elements."""
        legend_x = self.w - 75  # Right side of page
        legend_y = 20  # Below header

        # Background box for legend
        self.set_fill_color(250, 250, 250)
        self.set_draw_color(200, 200, 200)
        self.rect(legend_x - 2, legend_y - 2, 72, 58, 'FD')

        self.set_font("helvetica", 'B', 9)
        self.set_text_color(0, 0, 0)
        self.set_xy(legend_x, legend_y)
        self.cell(68, 5, "Legend", align='L')

        y = legend_y + 7
        items = [
            ("Center Model", self.COLORS['center']),
            ("Upstream (Feeder)", self.COLORS['upstream']),
            ("Downstream (Consumer)", self.COLORS['downstream']),
            ("Application", self.COLORS['application']),
            ("Parent/Sub-Model", self.COLORS['hierarchy']),
        ]

        for label, colors in items:
            self.set_fill_color(*colors['fill'])
            self.set_draw_color(*colors['border'])
            self.rect(legend_x, y, 8, 4, 'FD')
            self.set_xy(legend_x + 10, y)
            self.set_font("helvetica", '', 7)
            self.set_text_color(0, 0, 0)
            self.cell(55, 4, label)
            y += 6

        # Line styles section
        y += 2
        self.set_font("helvetica", '', 7)
        self.set_text_color(0, 0, 0)

        # Solid line (data flow)
        self.set_draw_color(100, 100, 100)
        self.set_line_width(0.3)
        self.line(legend_x, y + 2, legend_x + 15, y + 2)
        self.set_xy(legend_x + 17, y)
        self.cell(50, 4, "Data Flow (solid)")

        y += 6
        # Dashed line (hierarchy)
        self.set_draw_color(*self.COLORS['hierarchy']['border'])
        self.set_line_width(0.2)
        self._draw_dashed_line(legend_x, y + 2, legend_x + 15, y + 2)
        self.set_xy(legend_x + 17, y)
        self.cell(50, 4, "Hierarchy (dashed)")

    def draw_path(self, path, path_idx, include_hierarchy: bool = False):
        self.set_font("helvetica", 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, f"Path #{path_idx}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        # Settings
        box_w = 50
        box_h = 25  # Increased height for extra info
        gap = 10
        margin = self.l_margin
        page_w = self.w - 2 * margin

        # Pre-calculate layout metrics for consistent row heights when hierarchy is included
        if include_hierarchy:
            metrics = self._calculate_row_metrics(path)
            extra_top = metrics["extra_top"]
            extra_bottom = metrics["extra_bottom"]
            row_height = metrics["row_height"]
        else:
            extra_top = 0
            extra_bottom = 0
            row_height = box_h + gap + 10

        x = margin
        y = self.get_y() + extra_top  # Leave space for parent boxes at top

        max_x = margin + page_w - box_w

        for i, node in enumerate(path):
            # Check if we need to wrap to next line
            if x > max_x:
                x = margin
                y += row_height  # Use consistent row height

            # Check page break - account for hierarchy space
            needed_height = box_h + extra_bottom
            if y + needed_height > self.h - 20:
                self.add_page()
                y = self.get_y() + extra_top  # Leave room for parent boxes

            node_type = node.get("node_type", "model")
            is_application = node_type == "application"
            is_center = node.get('is_center', False)

            # Determine node color from COLORS constant for consistency
            if is_center:
                colors = self.COLORS['center']
                self.set_line_width(0.5)
            elif is_application:
                colors = self.COLORS['application']
                self.set_line_width(0.3)
            elif i < len(path) and not node.get('is_center') and any(n.get('is_center') for n in path[i+1:]):
                # Upstream (before center)
                colors = self.COLORS['upstream']
                self.set_line_width(0.3)
            else:
                # Downstream (after center)
                colors = self.COLORS['downstream']
                self.set_line_width(0.3)

            self.set_fill_color(*colors['fill'])
            self.set_draw_color(*colors['border'])

            # Draw Box
            self.rect(x, y, box_w, box_h, style='FD')

            # Text
            self.set_xy(x + 1, y + 2)
            self.set_font("helvetica", 'B', 8)
            self.set_text_color(0, 0, 0)

            # Truncate name
            name = node.get("model_name") or node.get("application_name") or "Unknown"
            if len(name) > 25:
                name = name[:22] + "..."
            self.cell(box_w - 2, 5, name, align='C')

            # Type
            self.set_xy(x + 1, y + 8)
            self.set_font("helvetica", '', 7)
            self.set_text_color(80, 80, 80)
            dep_type = node.get("dependency_type") or node.get("relationship_type") or "Center"
            self.cell(box_w - 2, 4, f"[{dep_type}]", align='C')

            # ID & Owner
            self.set_xy(x + 1, y + 13)
            self.set_font("helvetica", '', 6)
            if is_application:
                app_code = node.get("application_code") or node.get("application_id") or "-"
                self.cell(box_w - 2, 3, f"App: {app_code}", align='C')
            else:
                self.cell(box_w - 2, 3, f"ID: {node['model_id']}", align='C')

            self.set_xy(x + 1, y + 17)
            owner = node.get('owner_name', 'Unknown')
            if len(owner) > 25:
                owner = owner[:22] + "..."
            self.cell(box_w - 2, 3, f"Owner: {owner}", align='C')

            # Draw hierarchy immediately after drawing main node (while we have coordinates)
            if include_hierarchy and node.get('hierarchy'):
                self._draw_hierarchy_for_node(x, y, box_w, box_h, node['hierarchy'])

            # Draw Arrow to next node
            if i < len(path) - 1:
                # If next node wraps, don't draw right arrow
                if x + box_w + gap <= max_x:
                    mid_y = y + box_h / 2
                    self.set_draw_color(100, 100, 100)
                    self.set_line_width(0.3)  # Standardize arrow thickness
                    self.line(x + box_w, mid_y, x + box_w + gap, mid_y)
                    # Arrow head
                    self.line(x + box_w + gap - 2, mid_y - 2, x + box_w + gap, mid_y)
                    self.line(x + box_w + gap - 2, mid_y + 2, x + box_w + gap, mid_y)

            x += box_w + gap

        self.set_y(y + box_h + extra_bottom + 15)
        if self.get_y() > self.h - 30:
            self.add_page()


def _collect_upstream_paths_for_node(node: dict) -> list[list[dict]]:
    """Collect all upstream paths ending at this node.

    Returns paths where each path ends with `node`.
    """
    paths: list[list[dict]] = []
    upstream_nodes = node.get("upstream", [])

    for upstream in upstream_nodes:
        for path in _collect_upstream_paths_for_node(upstream):
            # path already ends with 'upstream', so append current 'node' to continue the chain
            paths.append(path + [node])

    for app in node.get("upstream_applications", []):
        paths.append([app, node])

    if not paths:
        paths.append([node])

    return paths


def _collect_upstream_paths(nodes: list[dict]) -> list[list[dict]]:
    if not nodes:
        return [[]]

    paths: list[list[dict]] = []
    for node in nodes:
        paths.extend(_collect_upstream_paths_for_node(node))

    return paths


def _collect_downstream_paths_for_node(node: dict) -> list[list[dict]]:
    """Collect all downstream paths starting at this node.

    Returns paths where each path starts with `node`.
    """
    paths: list[list[dict]] = []
    downstream_nodes = node.get("downstream", [])

    for downstream in downstream_nodes:
        for path in _collect_downstream_paths_for_node(downstream):
            # path already starts with 'downstream', so prepend current 'node' to continue the chain
            paths.append([node] + path)

    for app in node.get("downstream_applications", []):
        paths.append([node, app])

    if not paths:
        paths.append([node])

    return paths


def _collect_downstream_paths(nodes: list[dict]) -> list[list[dict]]:
    if not nodes:
        return [[]]

    paths: list[list[dict]] = []
    for node in nodes:
        paths.extend(_collect_downstream_paths_for_node(node))

    return paths


def build_lineage_paths(lineage_data: dict) -> list[list[dict]]:
    """Build full lineage paths with application leaf nodes."""
    center_node = lineage_data["model"].copy()
    center_node.setdefault("node_type", "model")
    center_node["is_center"] = True
    center_node.setdefault("dependency_type", "Center")

    upstream_paths = _collect_upstream_paths(lineage_data.get("upstream", []))
    downstream_paths = _collect_downstream_paths(lineage_data.get("downstream", []))

    full_paths: list[list[dict]] = []
    for u_path in upstream_paths:
        for d_path in downstream_paths:
            full_paths.append(u_path + [center_node] + d_path)

    return full_paths


@router.get("/models/{model_id}/dependencies/lineage/pdf")
def export_lineage_pdf(
    model_id: int,
    direction: str = "both",
    max_depth: int = 10,
    include_inactive: bool = False,
    include_hierarchy: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a PDF report of the dependency lineage as end-to-end paths.

    Parameters:
    - include_hierarchy: Include parent/sub-model hierarchy in the diagram (default False)
    """
    # Fetch lineage data
    lineage_data = get_dependency_lineage(
        model_id=model_id,
        direction=direction,
        max_depth=max_depth,
        include_inactive=include_inactive,
        include_hierarchy=include_hierarchy,
        db=db,
        current_user=current_user
    )

    full_paths = build_lineage_paths(lineage_data)

    # Create PDF in Landscape
    pdf = LineagePDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()

    # Draw legend if hierarchy is included
    if include_hierarchy:
        pdf.draw_legend()

    # Draw paths
    for idx, path in enumerate(full_paths, 1):
        pdf.draw_path(path, idx, include_hierarchy=include_hierarchy)

    # Output
    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)

    filename = f"lineage_chain_{model_id}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

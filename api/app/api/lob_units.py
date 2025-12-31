"""LOB (Line of Business) unit API routes."""
import csv
import io
import re
from types import SimpleNamespace
from typing import List, Dict, Optional, Tuple, Union
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.models.user import User
from app.models.lob import LOBUnit
from app.models.audit_log import AuditLog
from app.schemas.lob import (
    LOBUnitCreate,
    LOBUnitUpdate,
    LOBUnitResponse,
    LOBUnitTreeNode,
    LOBUnitWithAncestors,
    LOBImportResult,
    LOBImportPreview,
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for LOB operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def get_full_path(db: Session, lob: LOBUnit) -> str:
    """Build full path string from root to this node."""
    path_parts = []
    current = lob
    while current:
        path_parts.insert(0, current.name)
        if current.parent_id:
            current = db.query(LOBUnit).filter(LOBUnit.lob_id == current.parent_id).first()
        else:
            current = None
    return " > ".join(path_parts)


def get_ancestors(db: Session, lob: LOBUnit) -> List[LOBUnit]:
    """Get all ancestors from root to parent (excluding self)."""
    ancestors = []
    current_id = lob.parent_id
    while current_id:
        parent = db.query(LOBUnit).filter(LOBUnit.lob_id == current_id).first()
        if parent:
            ancestors.insert(0, parent)
            current_id = parent.parent_id
        else:
            break
    return ancestors


def get_user_count(db: Session, lob_id: int) -> int:
    """Get count of users assigned to this LOB unit."""
    return db.query(func.count(User.user_id)).filter(User.lob_id == lob_id).scalar() or 0


def lob_to_response(db: Session, lob: LOBUnit) -> dict:
    """Convert LOB model to response dict with computed fields."""
    return {
        "lob_id": lob.lob_id,
        "parent_id": lob.parent_id,
        "code": lob.code,
        "name": lob.name,
        "org_unit": lob.org_unit,
        "level": lob.level,
        "sort_order": lob.sort_order,
        "is_active": lob.is_active,
        "description": lob.description,
        "full_path": get_full_path(db, lob),
        "user_count": get_user_count(db, lob.lob_id),
        # Metadata fields (typically on leaf nodes)
        "contact_name": lob.contact_name,
        "org_description": lob.org_description,
        "legal_entity_id": lob.legal_entity_id,
        "legal_entity_name": lob.legal_entity_name,
        "short_name": lob.short_name,
        "status_code": lob.status_code,
        "tier": lob.tier,
        "created_at": lob.created_at,
        "updated_at": lob.updated_at,
    }


def build_tree(db: Session, lobs: List[LOBUnit], include_inactive: bool = False) -> List[LOBUnitTreeNode]:
    """Build hierarchical tree structure from flat list of LOB units."""
    # Filter by active status if needed
    if not include_inactive:
        lobs = [l for l in lobs if l.is_active]

    # Create lookup by ID
    lob_dict: Dict[int, dict] = {}
    for lob in lobs:
        lob_dict[lob.lob_id] = {
            "lob_id": lob.lob_id,
            "parent_id": lob.parent_id,
            "code": lob.code,
            "name": lob.name,
            "org_unit": lob.org_unit,
            "level": lob.level,
            "sort_order": lob.sort_order,
            "is_active": lob.is_active,
            "full_path": get_full_path(db, lob),
            "user_count": get_user_count(db, lob.lob_id),
            "description": lob.description,
            # Metadata fields (typically on leaf nodes)
            "contact_name": lob.contact_name,
            "org_description": lob.org_description,
            "legal_entity_id": lob.legal_entity_id,
            "legal_entity_name": lob.legal_entity_name,
            "short_name": lob.short_name,
            "status_code": lob.status_code,
            "tier": lob.tier,
            "children": []
        }

    # Build parent-child relationships
    roots = []
    for lob_id, lob_data in lob_dict.items():
        parent_id = lob_data["parent_id"]
        if parent_id is None:
            roots.append(lob_data)
        elif parent_id in lob_dict:
            lob_dict[parent_id]["children"].append(lob_data)

    # Sort children by sort_order, then name
    def sort_children(node: dict):
        node["children"].sort(key=lambda x: (x["sort_order"], x["name"]))
        for child in node["children"]:
            sort_children(child)

    for root in roots:
        sort_children(root)

    # Sort roots
    roots.sort(key=lambda x: (x["sort_order"], x["name"]))

    return roots


def check_admin(current_user: User):
    """Verify user is admin."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this action"
        )


# Enterprise CSV column mapping
# Note: For LOB1-5, we use Lob*Description for names (clean values) instead of LOB* columns
# (which have inconsistent formatting like "63186 (63186)" instead of proper names)
ENTERPRISE_COLUMNS = {
    'levels': [
        {'name': 'SBU', 'code': 'SBUCode', 'org_unit': None, 'description': None},
        {'name': 'Lob1Description', 'code': None, 'org_unit': 'Lob1Code', 'description': None},
        {'name': 'Lob2Description', 'code': None, 'org_unit': 'Lob2Code', 'description': None},
        {'name': 'Lob3Description', 'code': None, 'org_unit': 'Lob3Code', 'description': None},
        {'name': 'Lob4Description', 'code': None, 'org_unit': 'Lob4Code', 'description': None},
        {'name': 'Lob5Description', 'code': None, 'org_unit': 'Lob5Code', 'description': None},
    ],
    'leaf_org_unit': 'OrgUnit',
    'metadata': {
        'contact_name': 'OrgUnitContactName',
        'org_description': 'OrgUnitDescription',
        'legal_entity_id': 'OrgUnitLegalEntityId',
        'legal_entity_name': 'OrgUnitLegalEntityName',
        'short_name': 'OrgUnitShortName',
        'status_code': 'OrgUnitStatusCode',
        'tier': 'OrgUnitTier',
    }
}


def sanitize_code(raw_code: str) -> str:
    """Sanitize code by removing special characters, keeping alphanumeric + underscore."""
    if not raw_code:
        return ""
    sanitized = re.sub(r'[^A-Za-z0-9_]', '', raw_code)
    return sanitized.upper()[:50]  # Max 50 chars


def derive_synthetic_org_unit(name: str, existing_org_units: set, synthetic_counter: list) -> str:
    """Generate synthetic org_unit with S prefix for SBU level.

    Format: S0001, S0002, etc. Guarantees no collision with numeric org_units.
    Uses a counter (passed as list for mutability) to ensure uniqueness.
    """
    while True:
        synthetic_counter[0] += 1
        candidate = f"S{synthetic_counter[0]:04d}"
        if candidate not in existing_org_units:
            return candidate
        if synthetic_counter[0] >= 9999:
            raise ValueError("Exceeded maximum synthetic org_unit count (9999)")


def can_deactivate(db: Session, lob_id: int) -> Tuple[bool, str]:
    """Check if LOB unit can be deactivated."""
    # Check for active children
    active_children = db.query(LOBUnit).filter(
        LOBUnit.parent_id == lob_id,
        LOBUnit.is_active == True
    ).count()
    if active_children > 0:
        return False, f"Cannot deactivate: {active_children} active child LOB unit(s) exist"

    # Check for assigned users
    assigned_users = db.query(User).filter(User.lob_id == lob_id).count()
    if assigned_users > 0:
        return False, f"Cannot deactivate: {assigned_users} user(s) are assigned to this LOB"

    return True, ""


@router.get("/", response_model=List[LOBUnitResponse])
def list_lob_units(
    include_inactive: bool = Query(False, description="Include inactive LOB units"),
    org_unit: Optional[str] = Query(None, description="Filter by exact org_unit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all LOB units (flat list with parent info)."""
    query = db.query(LOBUnit)
    if not include_inactive:
        query = query.filter(LOBUnit.is_active == True)
    if org_unit:
        query = query.filter(LOBUnit.org_unit == org_unit)

    lobs = query.order_by(LOBUnit.level, LOBUnit.sort_order, LOBUnit.name).all()
    return [lob_to_response(db, lob) for lob in lobs]


@router.get("/tree", response_model=List[LOBUnitTreeNode])
def get_lob_tree(
    include_inactive: bool = Query(False, description="Include inactive LOB units"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get hierarchical tree structure of LOB units."""
    lobs = db.query(LOBUnit).all()
    return build_tree(db, lobs, include_inactive)


@router.get("/export-csv")
def export_lob_csv(
    include_inactive: bool = Query(False, description="Include inactive LOB units"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export LOB hierarchy as flat denormalized CSV (admin only).

    Each row represents a leaf path through the hierarchy.
    """
    check_admin(current_user)

    query = db.query(LOBUnit)
    if not include_inactive:
        query = query.filter(LOBUnit.is_active == True)

    lobs = query.order_by(LOBUnit.level, LOBUnit.sort_order, LOBUnit.name).all()

    # Find max depth
    max_level = max((lob.level for lob in lobs), default=1)

    # Build id to lob map
    lob_map = {lob.lob_id: lob for lob in lobs}

    # Find leaf nodes (nodes with no children)
    parent_ids = {lob.parent_id for lob in lobs if lob.parent_id}
    leaf_lobs = [lob for lob in lobs if lob.lob_id not in parent_ids]

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    header = ["SBU"] + [f"LOB{i}" for i in range(1, max_level)]
    writer.writerow(header)

    # Write rows
    for leaf in leaf_lobs:
        # Build path from leaf to root
        path = []
        current = leaf
        while current:
            path.insert(0, f"{current.name} ({current.code})")
            if current.parent_id and current.parent_id in lob_map:
                current = lob_map[current.parent_id]
            else:
                current = None

        # Pad to max_level columns
        while len(path) < max_level:
            path.append("")

        writer.writerow(path)

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=lob_hierarchy_export.csv"
        }
    )


@router.get("/{lob_id}", response_model=LOBUnitWithAncestors)
def get_lob_unit(
    lob_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single LOB unit with ancestor chain."""
    lob = db.query(LOBUnit).filter(LOBUnit.lob_id == lob_id).first()
    if not lob:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LOB unit not found"
        )

    ancestors = get_ancestors(db, lob)
    response = lob_to_response(db, lob)
    response["ancestors"] = [lob_to_response(db, a) for a in ancestors]
    return response


@router.post("/", response_model=LOBUnitResponse, status_code=status.HTTP_201_CREATED)
def create_lob_unit(
    lob_data: LOBUnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new LOB unit (admin only)."""
    check_admin(current_user)

    # Determine level based on parent
    level = 1
    if lob_data.parent_id:
        parent = db.query(LOBUnit).filter(LOBUnit.lob_id == lob_data.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent LOB unit not found"
            )
        if not parent.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create child under inactive parent"
            )
        level = parent.level + 1

    # Check for duplicate code under same parent
    existing = db.query(LOBUnit).filter(
        LOBUnit.parent_id == lob_data.parent_id,
        LOBUnit.code == lob_data.code.upper()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LOB unit with code '{lob_data.code}' already exists under this parent"
        )

    # Check for duplicate org_unit (globally unique)
    existing_org_unit = db.query(LOBUnit).filter(LOBUnit.org_unit == lob_data.org_unit).first()
    if existing_org_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LOB unit with org_unit '{lob_data.org_unit}' already exists"
        )

    lob = LOBUnit(
        parent_id=lob_data.parent_id,
        code=lob_data.code.upper(),
        name=lob_data.name,
        org_unit=lob_data.org_unit,
        level=level,
        sort_order=lob_data.sort_order,
        description=lob_data.description,
        contact_name=lob_data.contact_name,
        org_description=lob_data.org_description,
        legal_entity_id=lob_data.legal_entity_id,
        legal_entity_name=lob_data.legal_entity_name,
        short_name=lob_data.short_name,
        status_code=lob_data.status_code,
        tier=lob_data.tier,
        is_active=True
    )
    db.add(lob)
    db.flush()

    create_audit_log(
        db=db,
        entity_type="LOBUnit",
        entity_id=lob.lob_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "code": lob.code,
            "name": lob.name,
            "org_unit": lob.org_unit,
            "parent_id": lob.parent_id,
            "level": lob.level
        }
    )

    db.commit()
    db.refresh(lob)
    return lob_to_response(db, lob)


@router.patch("/{lob_id}", response_model=LOBUnitResponse)
def update_lob_unit(
    lob_id: int,
    lob_data: LOBUnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update LOB unit (admin only)."""
    check_admin(current_user)

    lob = db.query(LOBUnit).filter(LOBUnit.lob_id == lob_id).first()
    if not lob:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LOB unit not found"
        )

    update_data = lob_data.model_dump(exclude_unset=True)
    changes = {}

    # Handle deactivation check
    if "is_active" in update_data and update_data["is_active"] is False and lob.is_active:
        allowed, reason = can_deactivate(db, lob_id)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=reason
            )

    # Check for code uniqueness if being changed
    if "code" in update_data and update_data["code"] != lob.code:
        existing = db.query(LOBUnit).filter(
            LOBUnit.parent_id == lob.parent_id,
            LOBUnit.code == update_data["code"],
            LOBUnit.lob_id != lob_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LOB unit with code '{update_data['code']}' already exists under this parent"
            )

    # Check for org_unit uniqueness if being changed
    if "org_unit" in update_data and update_data["org_unit"] != lob.org_unit:
        existing = db.query(LOBUnit).filter(
            LOBUnit.org_unit == update_data["org_unit"],
            LOBUnit.lob_id != lob_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LOB unit with org_unit '{update_data['org_unit']}' already exists"
            )

    # Track changes
    for field, value in update_data.items():
        old_value = getattr(lob, field)
        if old_value != value:
            changes[field] = {"old": old_value, "new": value}
        setattr(lob, field, value)

    if changes:
        create_audit_log(
            db=db,
            entity_type="LOBUnit",
            entity_id=lob_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(lob)
    return lob_to_response(db, lob)


@router.delete("/{lob_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lob_unit(
    lob_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete (deactivate) LOB unit (admin only).

    This endpoint deactivates the LOB unit rather than hard deleting it.
    Deactivation is blocked if:
    - Active child LOB units exist
    - Users are assigned to this LOB unit
    """
    check_admin(current_user)

    lob = db.query(LOBUnit).filter(LOBUnit.lob_id == lob_id).first()
    if not lob:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LOB unit not found"
        )

    if not lob.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LOB unit is already inactive"
        )

    allowed, reason = can_deactivate(db, lob_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason
        )

    lob.is_active = False

    create_audit_log(
        db=db,
        entity_type="LOBUnit",
        entity_id=lob_id,
        action="DEACTIVATE",
        user_id=current_user.user_id,
        changes={
            "code": lob.code,
            "name": lob.name,
            "is_active": {"old": True, "new": False}
        }
    )

    db.commit()
    return None


def is_enterprise_format(headers: List[str]) -> bool:
    """Detect if CSV is in enterprise format based on columns."""
    headers_upper = [h.upper() for h in headers]
    enterprise_indicators = ['LOB1CODE', 'ORGUNIT', 'SBUCODE']
    return any(ind in headers_upper for ind in enterprise_indicators)


@router.post("/import-csv", response_model=Union[LOBImportPreview, LOBImportResult])
async def import_lob_csv(
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="Preview changes without committing"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Import LOB hierarchy from CSV file (admin only).

    Supports two formats:
    1. Enterprise format: SBU, SBUCode, LOB1, Lob1Code, Lob1Description, ..., OrgUnit, OrgUnitContactName, etc.
    2. Legacy format: SBU, LOB1, LOB2, LOB3, etc.

    When dry_run=True, returns LOBImportPreview with detailed breakdown.
    When dry_run=False, returns LOBImportResult with counts.
    """
    check_admin(current_user)

    # Read and parse CSV
    content = await file.read()
    try:
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        text_content = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text_content))
    headers = reader.fieldnames or []

    # Build lookup for existing LOB units
    existing_lobs = db.query(LOBUnit).all()
    existing_org_units = {lob.org_unit for lob in existing_lobs}
    lob_by_id = {lob.lob_id: lob for lob in existing_lobs}

    # Build existing_by_path, path_to_id, and existing_by_org_unit
    existing_by_path: Dict[Tuple[str, str], LOBUnit] = {}
    existing_by_org_unit: Dict[str, LOBUnit] = {}
    path_to_id: Dict[str, int] = {}

    for lob in existing_lobs:
        path_parts = []
        current = lob
        while current:
            path_parts.insert(0, current.code)
            current = lob_by_id.get(current.parent_id) if current.parent_id else None
        full_path = "/".join(path_parts)
        parent_path = "/".join(path_parts[:-1]) if len(path_parts) > 1 else ""
        existing_by_path[(parent_path, lob.code)] = lob
        existing_by_org_unit[lob.org_unit] = lob
        path_to_id[full_path] = lob.lob_id

    # Counter for synthetic org_units (starts at max existing S#### + 1)
    # Note: S9999 is reserved for the placeholder LOB, so we exclude it from max calculation
    max_synthetic = 0
    for org_unit in existing_org_units:
        if org_unit and org_unit.upper().startswith('S') and org_unit[1:].isdigit():
            num = int(org_unit[1:])
            # Skip S9999 (reserved placeholder) to avoid overflow to S10000
            if num < 9999:
                max_synthetic = max(max_synthetic, num)
    synthetic_counter = [max_synthetic]

    errors = []
    to_create = []
    to_update = []
    to_skip = []
    row_num = 1

    if is_enterprise_format(headers):
        # Enterprise format processing
        detected_columns = [h for h in headers if h.upper() in ['SBU', 'SBUCODE'] or
                           re.match(r'^LOB\d+$', h.upper()) or
                           re.match(r'^LOB\d+CODE$', h.upper()) or
                           h.upper() == 'ORGUNIT']

        # Build header mapping (case-insensitive)
        header_map = {h.upper(): h for h in headers}

        # Track processed nodes by org_unit to avoid duplicates
        processed_org_units: Dict[str, dict] = {}

        for row in reader:
            row_num += 1
            parent_path = ""
            parent_code = None
            deepest_level = -1
            leaf_node_key = None

            for level_idx, level_config in enumerate(ENTERPRISE_COLUMNS['levels']):
                level = level_idx  # 0-indexed for compatibility with existing data

                # Get name column (case-insensitive lookup)
                name_col = header_map.get(level_config['name'].upper())
                if not name_col:
                    continue
                name = row.get(name_col, '').strip()
                if not name:
                    break

                deepest_level = level

                # Get code - for SBU use SBUCode column, for LOB* derive from name
                if level_config['code']:
                    code_col = header_map.get(level_config['code'].upper())
                    raw_code = row.get(code_col, '').strip() if code_col else ''
                    code = sanitize_code(raw_code) if raw_code else sanitize_code(name)
                else:
                    code = sanitize_code(name)

                if not code:
                    errors.append(f"Row {row_num}: Could not derive code for '{name}'")
                    break

                # Get org_unit - LOB1-5 use Lob*Code, SBU gets synthetic
                org_unit = None
                if level_config['org_unit']:
                    org_unit_col = header_map.get(level_config['org_unit'].upper())
                    org_unit = row.get(org_unit_col, '').strip() if org_unit_col else ''

                # Get description
                description = None
                if level_config['description']:
                    desc_col = header_map.get(level_config['description'].upper())
                    description = row.get(desc_col, '').strip() if desc_col else None
                    if description == '':
                        description = None

                # Check if node exists by (parent_path, code)
                key = (parent_path, code)
                existing = existing_by_path.get(key)

                # If not found by path, also check by org_unit for denormalized CSV handling
                # This handles cases where the same LOB appears on multiple rows with different path derivation
                # or where LOB3/4/5 all have the same org_unit (meaning they're the same node)
                if not existing and org_unit and org_unit in existing_org_units:
                    existing = existing_by_org_unit.get(org_unit)
                    if existing:
                        # Found by org_unit - add to path lookup for this session
                        existing_by_path[key] = existing
                        # Also update path_to_id so leaf nodes can find their parent via this path
                        full_path = f"{parent_path}/{code}" if parent_path else code
                        path_to_id[full_path] = existing.lob_id

                if existing:
                    # Node exists - check for updates
                    updates_needed = {}
                    if existing.name != name:
                        updates_needed['name'] = name
                    if description and existing.description != description:
                        updates_needed['description'] = description
                    if org_unit and existing.org_unit != org_unit and org_unit not in existing_org_units:
                        updates_needed['org_unit'] = org_unit

                    if updates_needed:
                        node_info = {"code": code, "name": name, "org_unit": existing.org_unit, "level": level, "updates": updates_needed}
                        if node_info not in to_update:
                            to_update.append(node_info)
                        if not dry_run:
                            for field, value in updates_needed.items():
                                setattr(existing, field, value)
                    else:
                        node_info = {"code": code, "name": name, "org_unit": existing.org_unit, "level": level}
                        if node_info not in to_skip:
                            to_skip.append(node_info)

                    leaf_node_key = key
                else:
                    # New node - determine org_unit
                    # Only generate synthetic for SBU level (level_config['org_unit'] is None)
                    # LOB1-5 should always use the org_unit from CSV Lob*Code columns
                    if level_config['org_unit'] is None:
                        # SBU level - always generate synthetic since no org_unit column exists
                        org_unit = derive_synthetic_org_unit(name, existing_org_units, synthetic_counter)
                    elif not org_unit:
                        # LOB1-5 with missing org_unit (shouldn't happen with proper CSV) - generate synthetic as fallback
                        org_unit = derive_synthetic_org_unit(name, existing_org_units, synthetic_counter)
                    # else: LOB1-5 with org_unit from CSV - use it as-is

                    existing_org_units.add(org_unit)

                    parent_id = path_to_id.get(parent_path) if parent_path else None

                    node_info = {"code": code, "name": name, "org_unit": org_unit, "level": level, "parent_code": parent_code}
                    to_create.append(node_info)

                    full_path = f"{parent_path}/{code}" if parent_path else code

                    if not dry_run:
                        new_lob = LOBUnit(
                            parent_id=parent_id,
                            code=code,
                            name=name,
                            org_unit=org_unit,
                            level=level,
                            description=description,
                            sort_order=0,
                            is_active=True
                        )
                        db.add(new_lob)
                        db.flush()
                        path_to_id[full_path] = new_lob.lob_id
                        existing_by_path[key] = new_lob
                        existing_by_org_unit[org_unit] = new_lob
                    else:
                        # For dry_run, create a placeholder to track this node for subsequent rows
                        # Use a SimpleNamespace as a lightweight object with the same attributes
                        placeholder = SimpleNamespace(
                            lob_id=-(len(to_create)),  # Negative ID to indicate not-yet-created
                            code=code,
                            name=name,
                            org_unit=org_unit,
                            level=level,
                            description=description
                        )
                        path_to_id[full_path] = placeholder.lob_id
                        existing_by_path[key] = placeholder
                        existing_by_org_unit[org_unit] = placeholder

                    leaf_node_key = key

                # Update parent tracking for next level
                parent_path = f"{parent_path}/{code}" if parent_path else code
                parent_code = code

            # Create actual leaf node from OrgUnit column (as child of deepest LOB level)
            # Each row's OrgUnit represents a unique leaf node (e.g., 90111, 90448)
            # which is a child of LOB5 (e.g., US CORP BANKING with Lob5Code=63186)
            leaf_org_unit_col = header_map.get('ORGUNIT')
            leaf_desc_col = header_map.get('ORGUNITDESCRIPTION')

            if leaf_org_unit_col:
                leaf_org_unit = row.get(leaf_org_unit_col, '').strip()
                leaf_name = row.get(leaf_desc_col, '').strip() if leaf_desc_col else ''

                # Only create leaf if OrgUnit is different from the deepest LOB's org_unit
                # (to handle "stump" rows where OrgUnit == Lob5Code)
                deepest_lob = existing_by_path.get(leaf_node_key) if leaf_node_key else None
                deepest_org_unit = deepest_lob.org_unit if deepest_lob else None

                if leaf_org_unit and leaf_org_unit != deepest_org_unit:
                    # Check if this leaf node already exists
                    leaf_code = sanitize_code(leaf_name) if leaf_name else sanitize_code(leaf_org_unit)
                    leaf_key = (parent_path, leaf_code)

                    existing_leaf = existing_by_org_unit.get(leaf_org_unit)

                    if existing_leaf:
                        # Leaf exists - apply metadata updates
                        node_info = {"code": leaf_code, "name": leaf_name or leaf_org_unit, "org_unit": leaf_org_unit, "level": deepest_level + 1}
                        if node_info not in to_skip:
                            to_skip.append(node_info)

                        if not dry_run:
                            # Apply metadata fields to existing leaf
                            for field, csv_col in ENTERPRISE_COLUMNS['metadata'].items():
                                col = header_map.get(csv_col.upper())
                                if col:
                                    value = row.get(col, '').strip()
                                    if value:
                                        setattr(existing_leaf, field, value)
                    elif leaf_org_unit not in existing_org_units:
                        # Create new leaf node
                        leaf_level = deepest_level + 1
                        leaf_parent_id = path_to_id.get(parent_path) if parent_path else None

                        node_info = {
                            "code": leaf_code,
                            "name": leaf_name or leaf_org_unit,
                            "org_unit": leaf_org_unit,
                            "level": leaf_level,
                            "parent_code": parent_code
                        }
                        to_create.append(node_info)
                        existing_org_units.add(leaf_org_unit)

                        if not dry_run:
                            new_leaf = LOBUnit(
                                parent_id=leaf_parent_id,
                                code=leaf_code,
                                name=leaf_name or leaf_org_unit,
                                org_unit=leaf_org_unit,
                                level=leaf_level,
                                sort_order=0,
                                is_active=True
                            )
                            # Apply metadata fields
                            for field, csv_col in ENTERPRISE_COLUMNS['metadata'].items():
                                col = header_map.get(csv_col.upper())
                                if col:
                                    value = row.get(col, '').strip()
                                    if value:
                                        setattr(new_leaf, field, value)

                            db.add(new_leaf)
                            db.flush()
                            existing_by_org_unit[leaf_org_unit] = new_leaf
                        else:
                            # For dry_run, track the leaf
                            placeholder = SimpleNamespace(
                                lob_id=-(len(to_create)),
                                code=leaf_code,
                                name=leaf_name or leaf_org_unit,
                                org_unit=leaf_org_unit,
                                level=leaf_level
                            )
                            existing_by_org_unit[leaf_org_unit] = placeholder

    else:
        # Legacy format processing
        hierarchy_cols = []
        for h in headers:
            h_upper = h.upper().strip()
            if h_upper == 'SBU' or re.match(r'^LOB\d+$', h_upper):
                hierarchy_cols.append(h)

        if not hierarchy_cols:
            if dry_run:
                return LOBImportPreview(
                    to_create=[], to_update=[], to_skip=[],
                    errors=["No hierarchy columns found. Expected: SBU, LOB1, LOB2, etc."],
                    detected_columns=[], max_depth=0
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hierarchy columns found. Expected: SBU, LOB1, LOB2, etc."
            )

        # Sort columns
        def col_sort_key(col):
            upper = col.upper().strip()
            if upper == 'SBU':
                return 0
            match = re.match(r'^LOB(\d+)$', upper)
            return int(match.group(1)) if match else 999

        hierarchy_cols.sort(key=col_sort_key)
        detected_columns = hierarchy_cols

        nodes_to_process: Dict[Tuple[str, str], dict] = {}

        for row in reader:
            row_num += 1
            parent_path = ""
            parent_code = None

            for level_idx, col in enumerate(hierarchy_cols):
                level = level_idx
                value = row.get(col, '').strip()
                if not value:
                    break

                # Parse code and name
                match = re.match(r'^(.+?)\s*\(([^)]+)\)$', value)
                if match:
                    name = match.group(1).strip()
                    code = match.group(2).strip().upper()
                else:
                    code = sanitize_code(value)
                    name = value

                if not re.match(r'^[A-Za-z0-9_]+$', code):
                    errors.append(f"Row {row_num}: Invalid code '{code}'")
                    continue

                key = (parent_path, code)
                if key not in nodes_to_process:
                    nodes_to_process[key] = {
                        "code": code, "name": name, "parent_code": parent_code,
                        "parent_path": parent_path, "level": level
                    }

                parent_path = f"{parent_path}/{code}" if parent_path else code
                parent_code = code

        # Process nodes level by level
        sorted_nodes = sorted(nodes_to_process.values(), key=lambda x: x["level"])

        for node in sorted_nodes:
            code = node["code"]
            name = node["name"]
            parent_path = node["parent_path"]
            level = node["level"]

            parent_id = path_to_id.get(parent_path) if parent_path else None
            existing = existing_by_path.get((parent_path, code))

            if existing:
                if existing.name != name:
                    to_update.append({"code": code, "name": name, "org_unit": existing.org_unit, "level": level})
                    if not dry_run:
                        existing.name = name
                else:
                    to_skip.append({"code": code, "name": name, "org_unit": existing.org_unit, "level": level})
            else:
                org_unit = derive_synthetic_org_unit(name, existing_org_units, synthetic_counter)
                existing_org_units.add(org_unit)
                to_create.append({"code": code, "name": name, "org_unit": org_unit, "level": level, "parent_code": node["parent_code"]})

                if not dry_run:
                    new_lob = LOBUnit(
                        parent_id=parent_id, code=code, name=name, org_unit=org_unit,
                        level=level, sort_order=0, is_active=True
                    )
                    db.add(new_lob)
                    db.flush()
                    full_path = f"{parent_path}/{code}" if parent_path else code
                    path_to_id[full_path] = new_lob.lob_id
                    existing_by_path[(parent_path, code)] = new_lob

    if dry_run:
        return LOBImportPreview(
            to_create=to_create, to_update=to_update, to_skip=to_skip,
            errors=errors, detected_columns=detected_columns if 'detected_columns' in dir() else [],
            max_depth=len(detected_columns) if 'detected_columns' in dir() else 0
        )

    if errors and not dry_run:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": errors}
        )

    create_audit_log(
        db=db, entity_type="LOBUnit", entity_id=0, action="IMPORT",
        user_id=current_user.user_id,
        changes={
            "file_name": file.filename,
            "created_count": len(to_create), "updated_count": len(to_update), "skipped_count": len(to_skip)
        }
    )
    db.commit()

    return LOBImportResult(
        created_count=len(to_create), updated_count=len(to_update),
        skipped_count=len(to_skip), errors=errors
    )


@router.get("/{lob_id}/users", response_model=List[dict])
def get_lob_users(
    lob_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users assigned to this LOB unit."""
    lob = db.query(LOBUnit).filter(LOBUnit.lob_id == lob_id).first()
    if not lob:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LOB unit not found"
        )

    users = db.query(User).filter(User.lob_id == lob_id).all()
    return [
        {
            "user_id": u.user_id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role_display
        }
        for u in users
    ]

"""Authentication routes."""
import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.deps import get_current_user
from app.models.user import User
from app.models.role import Role
from app.models.model import Model
from app.models.entra_user import EntraUser
from app.models.region import Region
from app.models.lob import LOBUnit
from app.models.audit_log import AuditLog
from app.core.roles import RoleCode, resolve_role_code, get_user_role_code, build_capabilities, get_role_display
from app.schemas.user import LoginRequest, Token, UserResponse, UserCreate, UserUpdate, LOBUnitBrief
from app.schemas.entra_user import EntraUserResponse, EntraUserProvisionRequest
from app.schemas.model import ModelDetailResponse

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for user management operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def get_lob_full_path(db: Session, lob: LOBUnit) -> str:
    """Build full path string from root to this LOB node."""
    path_parts = []
    current = lob
    while current:
        path_parts.insert(0, current.name)
        if current.parent_id:
            current = db.query(LOBUnit).filter(LOBUnit.lob_id == current.parent_id).first()
        else:
            current = None
    return " > ".join(path_parts)


def get_user_with_lob(db: Session, user: User) -> dict:
    """Convert user to response dict with LOB info."""
    role_code = get_user_role_code(user)
    user_dict = {
        "user_id": user.user_id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role_display or get_role_display(role_code),
        "role_code": role_code,
        "capabilities": build_capabilities(role_code),
        "high_fluctuation_flag": user.high_fluctuation_flag,
        "regions": user.regions,
        "lob_id": user.lob_id,
        "lob": None
    }
    if user.lob_id and user.lob:
        user_dict["lob"] = LOBUnitBrief(
            lob_id=user.lob.lob_id,
            code=user.lob.code,
            name=user.lob.name,
            level=user.lob.level,
            full_path=get_lob_full_path(db, user.lob)
        )
    return user_dict


def resolve_role_for_write(db: Session, role_code: str | None, role_display: str | None) -> Role:
    resolved_code = resolve_role_code(role_code, role_display)
    if not resolved_code:
        resolved_code = RoleCode.USER.value
    role = db.query(Role).filter(Role.code == resolved_code, Role.is_active == True).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive role"
        )
    return role


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint."""
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user."""
    # Reload with LOB relationship to compute full_path
    user = db.query(User).options(
        joinedload(User.regions),
        joinedload(User.lob),
        joinedload(User.role_ref)
    ).filter(User.user_id == current_user.user_id).first()
    return get_user_with_lob(db, user)


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users."""
    users = db.query(User).options(
        joinedload(User.regions),
        joinedload(User.lob),
        joinedload(User.role_ref)
    ).all()
    return [get_user_with_lob(db, u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific user by ID."""
    user = db.query(User).options(
        joinedload(User.regions),
        joinedload(User.lob),
        joinedload(User.role_ref)
    ).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return get_user_with_lob(db, user)


@router.get("/users/{user_id}/models", response_model=List[ModelDetailResponse])
def get_user_models(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all models where user is owner or developer."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories)
    ).filter(
        or_(
            Model.owner_id == user_id,
            Model.developer_id == user_id
        )
    ).all()

    return models


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user (admin only in production)."""
    # Check if user exists
    existing_user = db.query(User).filter(
        User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate LOB (required for all users)
    lob = db.query(LOBUnit).filter(
        LOBUnit.lob_id == user_data.lob_id,
        LOBUnit.is_active == True
    ).first()
    if not lob:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive LOB unit"
        )

    # Resolve role (role_code preferred, role display fallback)
    role = resolve_role_for_write(db, user_data.role_code, user_data.role)

    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=get_password_hash(user_data.password),
        role_id=role.role_id,
        lob_id=user_data.lob_id
    )

    # Handle region associations for Regional Approvers
    if user_data.region_ids:
        regions = db.query(Region).filter(Region.region_id.in_(user_data.region_ids)).all()
        user.regions.extend(regions)

    db.add(user)
    db.flush()  # Get user_id before creating audit log

    # Create audit log for new user
    # Note: For user creation, the new user is logged as performing their own creation
    create_audit_log(
        db=db,
        entity_type="User",
        entity_id=user.user_id,
        action="CREATE",
        user_id=user.user_id,  # Self-registration
        changes={
            "email": user_data.email,
            "full_name": user_data.full_name,
            "role": role.display_name,
            "region_ids": user_data.region_ids or [],
            "lob_id": user_data.lob_id
        }
    )

    db.commit()
    db.refresh(user)

    return get_user_with_lob(db, user)


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a user."""
    user = db.query(User).options(
        joinedload(User.regions),
        joinedload(User.lob)
    ).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    update_data = user_data.model_dump(exclude_unset=True)
    role_code = update_data.pop("role_code", None)

    # Check for email uniqueness if email is being updated
    if 'email' in update_data and update_data['email'] != user.email:
        existing = db.query(User).filter(User.email == update_data['email']).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Validate LOB if being updated
    if 'lob_id' in update_data and update_data['lob_id'] is not None:
        lob = db.query(LOBUnit).filter(
            LOBUnit.lob_id == update_data['lob_id'],
            LOBUnit.is_active == True
        ).first()
        if not lob:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or inactive LOB unit"
            )

    # Track changes for audit log
    changes = {}

    # Hash password if provided (but don't log the actual password)
    if 'password' in update_data:
        update_data['password_hash'] = get_password_hash(update_data.pop('password'))
        changes["password"] = "changed"  # Don't log actual password values

    # Handle region associations for Regional Approvers
    region_ids_changed = False
    if 'region_ids' in update_data:
        region_ids = update_data.pop('region_ids')
        old_region_ids = [r.region_id for r in user.regions]

        # Clear existing regions
        user.regions.clear()
        # Add new regions
        if region_ids:
            regions = db.query(Region).filter(Region.region_id.in_(region_ids)).all()
            user.regions.extend(regions)

        if set(old_region_ids) != set(region_ids or []):
            changes["region_ids"] = {
                "old": old_region_ids,
                "new": region_ids or []
            }
            region_ids_changed = True

    # Handle role updates (role_code preferred, role display fallback)
    if role_code is not None or "role" in update_data:
        role = resolve_role_for_write(db, role_code, update_data.get("role"))
        if user.role_display != role.display_name:
            changes["role"] = {
                "old": user.role_display,
                "new": role.display_name
            }
        user.role_id = role.role_id
        update_data.pop("role", None)

    # Track other field changes
    for field, value in update_data.items():
        old_value = getattr(user, field, None)
        if old_value != value:
            if field == "email":
                changes["email"] = {
                    "old": old_value,
                    "new": value
                }
            elif field == "full_name":
                changes["full_name"] = {
                    "old": old_value,
                    "new": value
                }
            elif field == "lob_id":
                changes["lob_id"] = {
                    "old": old_value,
                    "new": value
                }
        setattr(user, field, value)

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="User",
            entity_id=user_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(user)
    return get_user_with_lob(db, user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a user."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user.user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Create audit log before deletion
    create_audit_log(
        db=db,
        entity_type="User",
        entity_id=user_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role_display
        }
    )

    db.delete(user)
    db.commit()
    return None


@router.get("/entra/users", response_model=List[EntraUserResponse])
def search_entra_directory(
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search Microsoft Entra directory for users.

    This simulates querying Microsoft Graph API. In production, this would
    call the actual Microsoft Graph endpoint.
    """
    query = db.query(EntraUser).filter(EntraUser.account_enabled == True)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (EntraUser.display_name.ilike(search_term)) |
            (EntraUser.mail.ilike(search_term)) |
            (EntraUser.user_principal_name.ilike(search_term)) |
            (EntraUser.department.ilike(search_term)) |
            (EntraUser.job_title.ilike(search_term))
        )

    return query.all()


@router.post("/entra/provision", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def provision_entra_user(
    provision_data: EntraUserProvisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Provision an Entra user as an application user.

    This creates an application user from the Entra directory entry,
    simulating SSO integration. The user will be created with a placeholder
    password since they would authenticate via Entra ID in production.
    """
    # Check if current user is admin
    if get_user_role_code(current_user) != RoleCode.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can provision users from directory"
        )

    # Find the Entra user
    entra_user = db.query(EntraUser).filter(
        EntraUser.entra_id == provision_data.entra_id
    ).first()

    if not entra_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entra user not found in directory"
        )

    if not entra_user.account_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot provision disabled Entra account"
        )

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == entra_user.mail).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists in application"
        )

    # Validate region_ids for Regional Approvers
    requested_role_code = resolve_role_code(provision_data.role_code, provision_data.role)
    if requested_role_code == RoleCode.REGIONAL_APPROVER.value:
        if not provision_data.region_ids or len(provision_data.region_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Regional Approvers must have at least one region assigned"
            )

    # Validate LOB (required for all users)
    lob = db.query(LOBUnit).filter(
        LOBUnit.lob_id == provision_data.lob_id,
        LOBUnit.is_active == True
    ).first()
    if not lob:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive LOB unit"
        )

    role = resolve_role_for_write(db, provision_data.role_code, provision_data.role)

    # Create application user from Entra data
    # In production, password would not be used as auth goes through Entra ID
    user = User(
        email=entra_user.mail,
        full_name=entra_user.display_name,
        password_hash=get_password_hash("entra_sso_placeholder"),  # Placeholder for SSO
        role_id=role.role_id,
        lob_id=provision_data.lob_id
    )
    db.add(user)
    db.flush()  # Flush to get user_id before attaching regions

    # Attach regions for Regional Approvers
    if role.code == RoleCode.REGIONAL_APPROVER.value and provision_data.region_ids:
        from app.models.region import Region
        regions = db.query(Region).filter(Region.region_id.in_(provision_data.region_ids)).all()
        if len(regions) != len(provision_data.region_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more invalid region IDs provided"
            )
        user.regions = regions

    # Create audit log for Entra user provisioning
    create_audit_log(
        db=db,
        entity_type="User",
        entity_id=user.user_id,
        action="PROVISION",
        user_id=current_user.user_id,  # Admin who performed the provisioning
        changes={
            "email": entra_user.mail,
            "full_name": entra_user.display_name,
            "role": role.display_name,
            "entra_id": provision_data.entra_id,
            "provisioned_from": "Microsoft Entra ID",
            "region_ids": provision_data.region_ids or []
        }
    )

    db.commit()
    db.refresh(user)

    return get_user_with_lob(db, user)


@router.get("/users/export/csv")
def export_users_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export all users to CSV."""
    users = db.query(User).options(joinedload(User.lob)).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "User ID",
        "Email",
        "Full Name",
        "Role",
        "LOB Code",
        "LOB Name",
        "LOB Path"
    ])

    # Write data rows
    for user in users:
        lob_code = user.lob.code if user.lob else ""
        lob_name = user.lob.name if user.lob else ""
        lob_path = get_lob_full_path(db, user.lob) if user.lob else ""
        role_display = user.role_display or get_role_display(get_user_role_code(user))
        writer.writerow([
            user.user_id,
            user.email,
            user.full_name,
            role_display,
            lob_code,
            lob_name,
            lob_path
        ])

    # Reset stream position
    output.seek(0)

    # Return as streaming response
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=users_export.csv"
        }
    )

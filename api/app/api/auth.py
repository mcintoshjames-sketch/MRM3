"""Authentication routes."""
import csv
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.deps import get_current_user
from app.models.user import User
from app.models.entra_user import EntraUser
from app.schemas.user import LoginRequest, Token, UserResponse, UserCreate, UserUpdate
from app.schemas.entra_user import EntraUserResponse, EntraUserProvisionRequest

router = APIRouter()


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
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user."""
    return current_user


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users."""
    users = db.query(User).all()
    return users


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

    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a user."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    update_data = user_data.model_dump(exclude_unset=True)

    # Check for email uniqueness if email is being updated
    if 'email' in update_data and update_data['email'] != user.email:
        existing = db.query(User).filter(User.email == update_data['email']).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Hash password if provided
    if 'password' in update_data:
        update_data['password_hash'] = get_password_hash(update_data.pop('password'))

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


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
    if current_user.role != "Admin":
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

    # Create application user from Entra data
    # In production, password would not be used as auth goes through Entra ID
    user = User(
        email=entra_user.mail,
        full_name=entra_user.display_name,
        password_hash=get_password_hash("entra_sso_placeholder"),  # Placeholder for SSO
        role=provision_data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.get("/users/export/csv")
def export_users_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export all users to CSV."""
    users = db.query(User).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "User ID",
        "Email",
        "Full Name",
        "Role"
    ])

    # Write data rows
    for user in users:
        writer.writerow([
            user.user_id,
            user.email,
            user.full_name,
            user.role
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

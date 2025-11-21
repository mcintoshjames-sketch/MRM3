"""
Provision Emily Davis from Entra directory as a User (model owner).
"""

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.entra_user import EntraUser
from app.models.user import User
from app.core.security import get_password_hash

def provision_emily_davis():
    db = SessionLocal()

    try:
        # Check if Emily Davis already exists
        existing_user = db.query(User).filter(User.email == "emily.davis@contoso.com").first()
        if existing_user:
            print("Emily Davis already exists as a user.")
            print(f"  User ID: {existing_user.user_id}")
            print(f"  Email: {existing_user.email}")
            print(f"  Role: {existing_user.role}")
            return

        # Get Emily from Entra directory
        emily = db.query(EntraUser).filter(EntraUser.mail == "emily.davis@contoso.com").first()

        if not emily:
            print("ERROR: Emily Davis not found in Entra directory!")
            return

        # Create user with "User" role (typical for model owners)
        user = User(
            email=emily.mail,
            full_name=emily.display_name,
            password_hash=get_password_hash("emily123"),  # Password: emily123
            role="User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        print("✓ Emily Davis provisioned successfully!")
        print(f"  User ID: {user.user_id}")
        print(f"  Email: {user.email}")
        print(f"  Full Name: {user.full_name}")
        print(f"  Role: {user.role}")
        print(f"  Password: emily123")
        print(f"  Job Title: {emily.job_title}")
        print(f"  Department: {emily.department}")

    except Exception as e:
        db.rollback()
        print(f"✗ Error provisioning Emily Davis: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    provision_emily_davis()

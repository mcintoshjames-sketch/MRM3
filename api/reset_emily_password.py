"""
Reset Emily Davis's password to emily123.
"""

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def reset_emily_password():
    db = SessionLocal()

    try:
        # Find Emily Davis
        emily = db.query(User).filter(User.email == "emily.davis@contoso.com").first()

        if not emily:
            print("ERROR: Emily Davis not found in users table!")
            return

        # Reset password
        emily.password_hash = get_password_hash("emily123")
        db.commit()

        print("✓ Password reset successfully!")
        print(f"  User ID: {emily.user_id}")
        print(f"  Email: {emily.email}")
        print(f"  Full Name: {emily.full_name}")
        print(f"  Role: {emily.role}")
        print(f"  New Password: emily123")

    except Exception as e:
        db.rollback()
        print(f"✗ Error resetting password: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    reset_emily_password()

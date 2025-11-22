"""
Test the actual API endpoint via HTTP request simulation
"""
import sys
from datetime import datetime, timedelta
from jose import jwt

# JWT settings from app.core.config
SECRET_KEY = "dev-secret-key-change-in-production-min-32-chars"  # From docker-compose.yml
ALGORITHM = "HS256"

# Create a test token for admin@example.com
def create_access_token(email: str, expires_delta: timedelta = None):
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode = {"sub": email, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Create token
token = create_access_token("admin@example.com")
print(f"Test Token: {token}")
print("\nYou can now test the API with curl:")
print(f'\ncurl -H "Authorization: Bearer {token}" "http://localhost:8001/validation-workflow/requests/?model_id=45"')

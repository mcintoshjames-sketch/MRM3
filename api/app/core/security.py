"""Security utilities for authentication and authorization."""
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from app.core.config import settings
from app.core.time import utc_now


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password."""
    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )
    return hashed.decode("utf-8")


def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    if settings.JWT_ISSUER:
        to_encode["iss"] = settings.JWT_ISSUER
    if settings.JWT_AUDIENCE:
        to_encode["aud"] = settings.JWT_AUDIENCE
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    """Decode JWT token."""
    try:
        options = {
            "verify_aud": bool(settings.JWT_AUDIENCE),
            "verify_iss": bool(settings.JWT_ISSUER),
        }
        decode_kwargs = {
            "token": token,
            "key": settings.SECRET_KEY,
            "algorithms": [settings.ALGORITHM],
            "options": options,
        }
        if settings.JWT_AUDIENCE:
            decode_kwargs["audience"] = settings.JWT_AUDIENCE
        if settings.JWT_ISSUER:
            decode_kwargs["issuer"] = settings.JWT_ISSUER
        payload = jwt.decode(**decode_kwargs)
        return payload
    except JWTError:
        return None

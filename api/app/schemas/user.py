"""User schemas."""
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from app.schemas.region import Region


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str
    role: str = "User"
    region_ids: List[int] = []  # For Regional Approvers


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    password: str | None = None
    region_ids: Optional[List[int]] = None  # For Regional Approvers


class UserResponse(UserBase):
    user_id: int
    role: str
    regions: List[Region] = []  # Authorized regions for Regional Approvers

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

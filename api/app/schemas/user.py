"""User schemas."""
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List, Optional
from app.schemas.region import Region


class LOBUnitBrief(BaseModel):
    """Brief LOB unit info for embedding in user responses."""
    lob_id: int
    code: str
    name: str
    level: int
    full_path: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str
    role: str | None = "User"
    role_code: str | None = None
    region_ids: List[int] = []  # For Regional Approvers
    lob_id: int  # User's LOB assignment (required)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    role_code: str | None = None
    password: str | None = None
    region_ids: Optional[List[int]] = None  # For Regional Approvers
    high_fluctuation_flag: bool | None = None  # For quarterly attestation triggering
    lob_id: Optional[int] = None  # User's LOB assignment


class UserSelfUpdate(BaseModel):
    full_name: str | None = None
    password: str | None = None
    current_password: str | None = None


class UserResponse(UserBase):
    user_id: int
    role: str
    role_code: str | None = None
    capabilities: dict | None = None
    regions: List[Region] = []  # Authorized regions for Regional Approvers
    high_fluctuation_flag: bool = False  # For quarterly attestation triggering
    lob_id: int  # User's LOB assignment (required)
    lob: Optional[LOBUnitBrief] = None  # Nested LOB info with full path

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

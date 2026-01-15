"""Entra user schemas."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class EntraUserResponse(BaseModel):
    """Response schema for Entra directory user."""
    object_id: str
    user_principal_name: str
    display_name: str
    given_name: str | None = None
    surname: str | None = None
    mail: EmailStr
    job_title: str | None = None
    department: str | None = None
    office_location: str | None = None
    mobile_phone: str | None = None
    account_enabled: bool
    in_recycle_bin: bool
    deleted_datetime: datetime | None = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class EntraUserProvisionRequest(BaseModel):
    """Request to provision an Entra user as an application user."""
    entra_id: str  # This is the object_id from the frontend
    role: str | None = "User"
    role_code: str | None = None
    region_ids: list[int] = []
    lob_id: int  # Required: User's LOB assignment


class EntraUserCreate(BaseModel):
    """Request schema for creating a mock Entra directory user."""
    user_principal_name: str
    display_name: str
    given_name: str | None = None
    surname: str | None = None
    mail: EmailStr
    job_title: str | None = None
    department: str | None = None
    office_location: str | None = None
    mobile_phone: str | None = None
    account_enabled: bool = True


class EntraUserUpdate(BaseModel):
    """Request schema for updating a mock Entra directory user."""
    user_principal_name: str | None = None
    display_name: str | None = None
    given_name: str | None = None
    surname: str | None = None
    mail: EmailStr | None = None
    job_title: str | None = None
    department: str | None = None
    office_location: str | None = None
    mobile_phone: str | None = None
    account_enabled: bool | None = None
    in_recycle_bin: bool | None = None
    deleted_datetime: datetime | None = None

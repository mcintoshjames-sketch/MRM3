"""Entra user schemas."""
from pydantic import BaseModel, ConfigDict, EmailStr


class EntraUserResponse(BaseModel):
    """Response schema for Entra directory user."""
    entra_id: str
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

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class EntraUserProvisionRequest(BaseModel):
    """Request to provision an Entra user as an application user."""
    entra_id: str
    role: str | None = "User"
    role_code: str | None = None
    region_ids: list[int] = []
    lob_id: int  # Required: User's LOB assignment

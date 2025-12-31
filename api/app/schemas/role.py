"""Role schemas."""
from pydantic import BaseModel


class RoleResponse(BaseModel):
    role_id: int
    role_code: str
    display_name: str
    is_system: bool
    is_active: bool

    class Config:
        from_attributes = True

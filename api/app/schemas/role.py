"""Role schemas."""
from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    role_id: int
    role_code: str
    display_name: str
    is_system: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

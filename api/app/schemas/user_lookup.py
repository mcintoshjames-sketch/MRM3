"""Minimal user lookup response schemas."""
from pydantic import BaseModel, ConfigDict


class AssignableValidatorResponse(BaseModel):
    """Minimal user info for validator assignment dropdowns."""
    user_id: int
    full_name: str
    email: str
    role_code: str | None = None
    role_display: str | None = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelAssigneeResponse(BaseModel):
    """Minimal user info for model-scoped assignee lists."""
    user_id: int
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

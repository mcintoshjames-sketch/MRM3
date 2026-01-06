"""Model delegate schemas."""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field


class ModelDelegateBase(BaseModel):
    """Base model delegate schema."""
    can_submit_changes: bool = Field(False, description="Can submit model changes (create versions)")
    can_manage_regional: bool = Field(False, description="Can manage regional configurations")
    can_attest: bool = Field(False, description="Can submit attestations on behalf of model owner")


class ModelDelegateCreate(ModelDelegateBase):
    """Schema for creating a new model delegation."""
    user_id: int = Field(..., description="User to grant delegation to")


class ModelDelegateUpdate(BaseModel):
    """Schema for updating a model delegation (primarily for revoking)."""
    can_submit_changes: Optional[bool] = None
    can_manage_regional: Optional[bool] = None
    can_attest: Optional[bool] = None


class ModelDelegateResponse(ModelDelegateBase):
    """Full model delegate response with relationships."""
    delegate_id: int
    model_id: int
    user_id: int
    delegated_by_id: int
    delegated_at: datetime
    revoked_at: Optional[datetime] = None
    revoked_by_id: Optional[int] = None

    # Nested objects (optional, can be populated by API)
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    delegated_by_name: Optional[str] = None
    revoked_by_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class BatchDelegateRequest(BaseModel):
    """Schema for batch delegate operations."""
    target_user_id: int = Field(..., description="User ID of the model owner or developer")
    role: Literal["owner", "developer"] = Field(..., description="Whether to target models owned or developed by the user")
    delegate_user_id: int = Field(..., description="User to grant delegation to")
    can_submit_changes: bool = Field(True, description="Can submit model changes (create versions)")
    can_manage_regional: bool = Field(True, description="Can manage regional configurations")
    can_attest: bool = Field(False, description="Can submit attestations on behalf of model owner")
    replace_existing: bool = Field(False, description="If true, revoke all other delegates for each model")


class ModelDelegateDetail(BaseModel):
    """Details of a model affected by batch operation."""
    model_id: int
    model_name: str
    action: Literal["created", "updated", "replaced"]


    model_config = ConfigDict(protected_namespaces=())
class BatchDelegateResponse(BaseModel):
    """Response for batch delegate operations."""
    models_affected: int = Field(..., description="Number of models where delegation was added/updated")
    model_details: List[ModelDelegateDetail] = Field(..., description="Details of affected models")
    delegations_created: int = Field(..., description="Number of new delegations created")
    delegations_updated: int = Field(..., description="Number of existing delegations updated")
    delegations_revoked: int = Field(0, description="Number of delegations revoked (when replacing)")
    model_config = ConfigDict(protected_namespaces=())

"""Model version schemas."""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ChangeType(str, Enum):
    """Model change type."""
    MINOR = "MINOR"  # Does not require validation
    MAJOR = "MAJOR"  # Requires validation


class VersionStatus(str, Enum):
    """Model version status."""
    DRAFT = "DRAFT"
    IN_VALIDATION = "IN_VALIDATION"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class ModelVersionBase(BaseModel):
    """Base model version schema."""
    change_type: ChangeType = Field(..., description="MINOR (no validation required) or MAJOR (requires validation) - legacy field")
    change_type_id: Optional[int] = Field(None, description="Reference to model_change_types taxonomy (preferred)")
    change_description: str = Field(..., description="Description of changes in this version")
    production_date: Optional[date] = Field(None, description="Date deployed to production")


class ModelVersionCreate(ModelVersionBase):
    """Schema for creating a new model version."""
    version_number: Optional[str] = Field(None, max_length=50, description="Version number (auto-generated if not provided)")
    # If not provided, will be auto-generated based on change_type


class ModelVersionUpdate(BaseModel):
    """Schema for updating a model version."""
    version_number: Optional[str] = Field(None, max_length=50)
    change_type: Optional[ChangeType] = None
    change_description: Optional[str] = None
    production_date: Optional[date] = None
    status: Optional[VersionStatus] = None
    validation_request_id: Optional[int] = None


class ModelVersionResponse(ModelVersionBase):
    """Full model version response with relationships."""
    version_id: int
    model_id: int
    version_number: str
    status: VersionStatus
    created_by_id: int
    created_at: datetime
    validation_request_id: Optional[int] = None
    change_type_id: Optional[int] = None

    # Nested objects (optional, can be added later)
    created_by_name: Optional[str] = None
    change_type_name: Optional[str] = None  # L2 change type name (e.g., "New Model Development")
    change_category_name: Optional[str] = None  # L1 category name (e.g., "New Model")

    # Validation request info (populated when auto-created)
    validation_request_created: Optional[bool] = None
    validation_type: Optional[str] = None  # "TARGETED" or "INTERIM"
    validation_warning: Optional[str] = None  # Warning message if interim or out of order

    class Config:
        from_attributes = True

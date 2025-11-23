"""Model version schemas."""
from datetime import datetime, date
from typing import Optional, List
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


class VersionScope(str, Enum):
    """Model version scope."""
    GLOBAL = "GLOBAL"  # Change affects all regions
    REGIONAL = "REGIONAL"  # Change affects specific regions only


class ModelVersionBase(BaseModel):
    """Base model version schema."""
    change_type: ChangeType = Field(..., description="MINOR (no validation required) or MAJOR (requires validation) - legacy field")
    change_type_id: Optional[int] = Field(None, description="Reference to model_change_types taxonomy (preferred)")
    change_description: str = Field(..., description="Description of changes in this version")

    # Regional scope
    scope: VersionScope = Field(default=VersionScope.GLOBAL, description="GLOBAL (all regions) or REGIONAL (specific regions)")
    affected_region_ids: Optional[List[int]] = Field(None, description="List of region IDs affected (required if scope=REGIONAL)")

    # Production dates
    planned_production_date: Optional[date] = Field(None, description="Planned/target production date")
    actual_production_date: Optional[date] = Field(None, description="Actual date deployed to production")
    production_date: Optional[date] = Field(None, description="Legacy field - maps to planned_production_date")


class ModelVersionCreate(ModelVersionBase):
    """Schema for creating a new model version."""
    version_number: Optional[str] = Field(None, max_length=50, description="Version number (auto-generated if not provided)")
    # If not provided, will be auto-generated based on change_type


class ModelVersionUpdate(BaseModel):
    """Schema for updating a model version."""
    version_number: Optional[str] = Field(None, max_length=50)
    change_type: Optional[ChangeType] = None
    change_description: Optional[str] = None
    scope: Optional[VersionScope] = None
    affected_region_ids: Optional[List[int]] = None
    planned_production_date: Optional[date] = None
    actual_production_date: Optional[date] = None
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

    # Regional scope (inherited from Base but including for clarity)
    scope: VersionScope
    affected_region_ids: Optional[List[int]] = None

    # Point-in-time compliance snapshot
    change_requires_mv_approval: Optional[bool] = Field(
        None,
        description="Point-in-time snapshot: Did this change require MV approval at submission time?"
    )

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

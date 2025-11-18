"""Regional Model Implementation schemas."""
from datetime import datetime, date
from pydantic import BaseModel, Field
from typing import Optional


class RegionalModelImplementationBase(BaseModel):
    """Base RMI schema."""
    local_identifier: Optional[str] = Field(None, max_length=100, description="Region-specific identifier")
    status: str = Field("ACTIVE", max_length=50, description="Implementation status")
    effective_date: Optional[date] = Field(None, description="Date when implementation became active")
    decommission_date: Optional[date] = Field(None, description="Date when implementation was decommissioned")
    notes: Optional[str] = Field(None, description="Additional notes about this implementation")


class RegionalModelImplementationCreate(RegionalModelImplementationBase):
    """Schema for creating a regional implementation."""
    model_id: int = Field(..., description="Global model ID")
    region_id: int = Field(..., description="Region ID")
    shared_model_owner_id: Optional[int] = Field(None, description="Regional owner if different from global")


class RegionalModelImplementationUpdate(BaseModel):
    """Schema for updating a regional implementation."""
    shared_model_owner_id: Optional[int] = None
    local_identifier: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=50)
    effective_date: Optional[date] = None
    decommission_date: Optional[date] = None
    notes: Optional[str] = None


class RegionalModelImplementationResponse(RegionalModelImplementationBase):
    """Regional implementation response schema."""
    regional_model_impl_id: int
    model_id: int
    region_id: int
    shared_model_owner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RegionalModelImplementationDetailResponse(RegionalModelImplementationResponse):
    """Regional implementation with nested details."""
    # These will be populated from relationships
    # model: ModelResponse  # Could include if needed
    # region: Region
    # shared_model_owner: Optional[UserResponse]
    pass

    class Config:
        from_attributes = True

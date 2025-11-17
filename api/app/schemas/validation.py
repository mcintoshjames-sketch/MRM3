"""Validation and ValidationPolicy schemas."""
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional
from app.schemas.user import UserResponse
from app.schemas.taxonomy import TaxonomyValueResponse


class ValidationPolicyBase(BaseModel):
    """Base schema for validation policy."""
    risk_tier_id: int
    frequency_months: int = 12
    description: Optional[str] = None


class ValidationPolicyCreate(ValidationPolicyBase):
    """Schema for creating a validation policy."""
    pass


class ValidationPolicyUpdate(BaseModel):
    """Schema for updating a validation policy."""
    frequency_months: Optional[int] = None
    description: Optional[str] = None


class ValidationPolicyResponse(ValidationPolicyBase):
    """Response schema for validation policy."""
    policy_id: int
    risk_tier: TaxonomyValueResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ValidationBase(BaseModel):
    """Base schema for validation."""
    model_id: int
    validation_date: date
    validator_id: int
    validation_type_id: int
    outcome_id: int
    scope_id: int
    findings_summary: Optional[str] = None
    report_reference: Optional[str] = None


class ValidationCreate(ValidationBase):
    """Schema for creating a validation."""
    pass


class ValidationUpdate(BaseModel):
    """Schema for updating a validation."""
    validation_date: Optional[date] = None
    validator_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    outcome_id: Optional[int] = None
    scope_id: Optional[int] = None
    findings_summary: Optional[str] = None
    report_reference: Optional[str] = None


class ModelSummary(BaseModel):
    """Minimal model info for validation response."""
    model_id: int
    model_name: str
    status: str

    class Config:
        from_attributes = True


class ValidationResponse(ValidationBase):
    """Response schema for validation."""
    validation_id: int
    model: ModelSummary
    validator: UserResponse
    validation_type: TaxonomyValueResponse
    outcome: TaxonomyValueResponse
    scope: TaxonomyValueResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ValidationListResponse(BaseModel):
    """Response schema for validation list."""
    validation_id: int
    model_id: int
    model_name: str
    validation_date: date
    validator_name: str
    validation_type: str
    outcome: str
    scope: str
    created_at: datetime

    class Config:
        from_attributes = True

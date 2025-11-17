"""Model schemas."""
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
from app.schemas.user import UserResponse
from app.schemas.vendor import VendorResponse
from app.schemas.taxonomy import TaxonomyValueResponse


class ModelBase(BaseModel):
    model_name: str
    description: Optional[str] = None
    development_type: str = "In-House"
    status: str = "In Development"


class ModelCreate(ModelBase):
    owner_id: int
    developer_id: Optional[int] = None
    vendor_id: Optional[int] = None
    risk_tier_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    user_ids: Optional[List[int]] = None

    @field_validator('vendor_id')
    @classmethod
    def validate_vendor_required_for_third_party(cls, v, info):
        if info.data.get('development_type') == 'Third-Party' and v is None:
            raise ValueError('Vendor is required for third-party models')
        return v


class ModelUpdate(BaseModel):
    model_name: Optional[str] = None
    description: Optional[str] = None
    development_type: Optional[str] = None
    owner_id: Optional[int] = None
    developer_id: Optional[int] = None
    vendor_id: Optional[int] = None
    risk_tier_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    status: Optional[str] = None
    user_ids: Optional[List[int]] = None


class ModelResponse(ModelBase):
    model_id: int
    owner_id: int
    developer_id: Optional[int] = None
    vendor_id: Optional[int] = None
    risk_tier_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelDetailResponse(ModelResponse):
    """Model response with nested user and vendor details."""
    owner: UserResponse
    developer: Optional[UserResponse] = None
    vendor: Optional[VendorResponse] = None
    risk_tier: Optional[TaxonomyValueResponse] = None
    validation_type: Optional[TaxonomyValueResponse] = None
    users: List[UserResponse] = []

    class Config:
        from_attributes = True

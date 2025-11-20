"""Model schemas."""
from pydantic import BaseModel, field_validator, field_serializer
from datetime import datetime, date
from typing import Optional, List, Any
from app.schemas.user import UserResponse
from app.schemas.vendor import VendorResponse
from app.schemas.taxonomy import TaxonomyValueResponse
from app.schemas.region import Region


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
    model_type_id: Optional[int] = None
    ownership_type_id: Optional[int] = None
    wholly_owned_region_id: Optional[int] = None
    user_ids: Optional[List[int]] = None
    regulatory_category_ids: Optional[List[int]] = None
    initial_implementation_date: Optional[date] = None

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
    model_type_id: Optional[int] = None
    ownership_type_id: Optional[int] = None
    wholly_owned_region_id: Optional[int] = None
    status: Optional[str] = None
    user_ids: Optional[List[int]] = None
    regulatory_category_ids: Optional[List[int]] = None


class ModelResponse(ModelBase):
    model_id: int
    owner_id: int
    developer_id: Optional[int] = None
    vendor_id: Optional[int] = None
    risk_tier_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    model_type_id: Optional[int] = None
    ownership_type_id: Optional[int] = None
    wholly_owned_region_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelRegionListItem(BaseModel):
    """Simplified model-region info for list views."""
    region_id: int
    region_code: str
    region_name: str

    class Config:
        from_attributes = True


class ModelDetailResponse(ModelResponse):
    """Model response with nested user and vendor details."""
    owner: UserResponse
    developer: Optional[UserResponse] = None
    vendor: Optional[VendorResponse] = None
    risk_tier: Optional[TaxonomyValueResponse] = None
    validation_type: Optional[TaxonomyValueResponse] = None
    model_type: Optional[TaxonomyValueResponse] = None
    ownership_type: Optional[TaxonomyValueResponse] = None
    wholly_owned_region: Optional[Region] = None
    users: List[UserResponse] = []
    regulatory_categories: List[TaxonomyValueResponse] = []
    regions: List[ModelRegionListItem] = []

    class Config:
        from_attributes = True


class ValidationGroupingSuggestion(BaseModel):
    """Suggested models based on previous validation groupings."""
    suggested_model_ids: List[int]
    suggested_models: List[ModelDetailResponse]
    last_validation_request_id: Optional[int] = None
    last_grouped_at: Optional[datetime] = None

    class Config:
        from_attributes = True

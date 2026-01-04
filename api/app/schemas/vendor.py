"""Vendor schemas."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class VendorBase(BaseModel):
    name: str
    contact_info: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact_info: Optional[str] = None


class VendorResponse(VendorBase):
    vendor_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

"""Bulk update schemas for models."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Literal


class BulkUpdateFieldsRequest(BaseModel):
    """
    Request schema for bulk updating model fields.

    For all optional fields:
    - If the field is NOT in the request body: field is not changed
    - If the field is in the request body with a value: field is set to that value
    - If the field is in the request body as null: field is cleared (where allowed)

    Use model_dump(exclude_unset=True) on the backend to distinguish.
    """

    model_ids: List[int] = Field(..., min_length=1, description="Model IDs to update")

    # People pickers (single-select, replace mode)
    owner_id: Optional[int] = None
    developer_id: Optional[int] = None
    shared_owner_id: Optional[int] = None
    shared_developer_id: Optional[int] = None
    monitoring_manager_id: Optional[int] = None

    # Text field (replace mode)
    products_covered: Optional[str] = None

    # Multi-select fields with mode
    user_ids: Optional[List[int]] = None
    user_ids_mode: Literal["add", "replace"] = "add"

    regulatory_category_ids: Optional[List[int]] = None
    regulatory_category_ids_mode: Literal["add", "replace"] = "add"

    model_config = ConfigDict(protected_namespaces=())


class BulkUpdateResultItem(BaseModel):
    """Result for a single model in bulk update."""

    model_id: int
    model_name: Optional[str] = None
    success: bool
    error: Optional[str] = None


class BulkUpdateFieldsResponse(BaseModel):
    """Response schema for bulk field update."""

    total_requested: int
    total_modified: int
    total_skipped: int
    total_failed: int
    results: List[BulkUpdateResultItem]

    model_config = ConfigDict(protected_namespaces=())

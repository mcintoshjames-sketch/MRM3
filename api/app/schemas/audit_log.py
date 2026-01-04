"""Audit log schemas."""
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse


class AuditLogResponse(BaseModel):
    log_id: int
    entity_type: str
    entity_id: int
    action: str
    user_id: int
    changes: Optional[Dict[str, Any]] = None
    timestamp: datetime
    user: UserResponse

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

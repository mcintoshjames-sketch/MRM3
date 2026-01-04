"""Model Submission Comment schemas."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.schemas.user import UserResponse


class ModelSubmissionCommentBase(BaseModel):
    comment_text: str
    action_taken: Optional[str] = None


class ModelSubmissionCommentCreate(ModelSubmissionCommentBase):
    pass


class ModelSubmissionCommentResponse(ModelSubmissionCommentBase):
    comment_id: int
    model_id: int
    user_id: int
    user: UserResponse
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

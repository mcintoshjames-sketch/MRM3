from pydantic import BaseModel
from typing import Optional


class SubmissionAction(BaseModel):
    comment: Optional[str] = None


class SubmissionFeedback(BaseModel):
    comment: str


class SubmissionCommentCreate(BaseModel):
    comment_text: str

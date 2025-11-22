from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


@router.post("/query")
def execute_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Execute a raw SQL query.
    WARNING: This is a dangerous endpoint. Ensure only trusted users can access it.
    """
    # Basic safety check - allow SELECT, WITH (for CTEs), EXPLAIN, SHOW, VALUES, TABLE
    allowed_keywords = ["SELECT", "WITH", "EXPLAIN", "SHOW", "VALUES", "TABLE"]
    cleaned_query = request.query.strip().upper()

    # Handle queries wrapped in parentheses like (SELECT ...)
    while cleaned_query.startswith('('):
        cleaned_query = cleaned_query[1:].strip()

    if not any(cleaned_query.startswith(keyword) for keyword in allowed_keywords):
        raise HTTPException(
            status_code=400,
            detail="Only read-only queries (SELECT, WITH, EXPLAIN, SHOW, VALUES, TABLE) are allowed."
        )

    try:
        result = db.execute(text(request.query))
        # Convert result to list of dicts
        rows = result.fetchall()
        if not rows:
            return []

        # Get column names
        keys = result.keys()
        return [dict(zip(keys, row)) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

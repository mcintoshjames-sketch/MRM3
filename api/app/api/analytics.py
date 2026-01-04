"""Ad-hoc analytics endpoints (raw read-only SQL execution)."""
from typing import Any, List, Dict
import hashlib
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db, SessionLocal
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter()

ALLOWED_READONLY_KEYWORDS = ["SELECT", "WITH", "EXPLAIN", "SHOW", "VALUES", "TABLE"]
MAX_RESULT_ROWS = 1000
STATEMENT_TIMEOUT = "5s"


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
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Basic safety check - allow SELECT, WITH (for CTEs), EXPLAIN, SHOW, VALUES, TABLE
    cleaned_query = request.query.strip().upper()

    # Handle queries wrapped in parentheses like (SELECT ...)
    while cleaned_query.startswith('('):
        cleaned_query = cleaned_query[1:].strip()

    if not any(cleaned_query.startswith(keyword) for keyword in ALLOWED_READONLY_KEYWORDS):
        raise HTTPException(
            status_code=400,
            detail="Only read-only queries (SELECT, WITH, EXPLAIN, SHOW, VALUES, TABLE) are allowed."
        )

    start_time = time.monotonic()
    query_hash = hashlib.sha256(request.query.encode("utf-8")).hexdigest()
    outcome = "success"
    error_detail = None
    rows = []
    keys = []
    row_count = 0

    try:
        with SessionLocal() as analytics_db:
            try:
                analytics_db.execute(text("SET TRANSACTION READ ONLY"))
                analytics_db.execute(
                    text("SET LOCAL statement_timeout = :timeout"),
                    {"timeout": STATEMENT_TIMEOUT},
                )
                result = analytics_db.execute(text(request.query))
                keys = result.keys()
                rows = result.fetchmany(MAX_RESULT_ROWS + 1)
                row_count = len(rows)
                if row_count > MAX_RESULT_ROWS:
                    outcome = "too_large"
                    error_detail = f"Result too large; limit to {MAX_RESULT_ROWS} rows."
            finally:
                analytics_db.rollback()
    except Exception as exc:
        outcome = "error"
        error_detail = str(exc)

    duration_ms = int((time.monotonic() - start_time) * 1000)
    audit_log = AuditLog(
        entity_type="AnalyticsQuery",
        entity_id=0,
        action="EXECUTE",
        user_id=current_user.user_id,
        changes={
            "query_sha256": query_hash,
            "query_length": len(request.query),
            "duration_ms": duration_ms,
            "outcome": outcome,
            "row_count": row_count,
            "max_rows": MAX_RESULT_ROWS,
            "error": error_detail[:200] if error_detail else None,
        },
    )
    try:
        db.add(audit_log)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Audit logging failed") from exc

    if error_detail:
        raise HTTPException(status_code=400, detail=error_detail)

    if not rows:
        return []

    return [dict(zip(keys, row)) for row in rows]

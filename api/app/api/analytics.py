"""Ad-hoc analytics endpoints (raw read-only SQL execution)."""
from typing import Any, List, Dict
import hashlib
import logging
import os
import re
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
import sqlparse
from sqlparse.sql import Function
from sqlparse.tokens import Comment, DML, Keyword, Newline, Punctuation, Whitespace, DDL, Name

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_READONLY_KEYWORDS = {"SELECT", "WITH",
                             "EXPLAIN", "SHOW", "VALUES", "TABLE"}
DISALLOWED_KEYWORDS = {
    "COPY",
    "SET",
    "CALL",
    "DO",
    "VACUUM",
    "ALTER",
    "CREATE",
    "DROP",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
}
MAX_RESULT_ROWS = 1000
MAX_QUERY_LENGTH = 20000
STATEMENT_TIMEOUT = "5s"
LOCK_TIMEOUT = os.getenv("ANALYTICS_LOCK_TIMEOUT", "2s")
IDLE_IN_TRANSACTION_TIMEOUT = os.getenv("ANALYTICS_IDLE_IN_TRANSACTION_TIMEOUT", "30s")
ANALYTICS_DB_ROLE = os.getenv("ANALYTICS_DB_ROLE")
ANALYTICS_SEARCH_PATH = os.getenv("ANALYTICS_SEARCH_PATH")
BLOCKED_FUNCTIONS = {
    "pg_sleep",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "pg_read_file",
    "pg_write_file",
}
BLOCKED_FUNCTION_PREFIXES = ("lo_", "dblink")
WARNED_MISSING_ANALYTICS_ROLE = False
WARNED_MISSING_ANALYTICS_SEARCH_PATH = False


class QueryRequest(BaseModel):
    query: str


def _first_statement_keyword(statement: sqlparse.sql.Statement) -> str:
    for token in statement.flatten():
        if token.is_whitespace or token.ttype in (Whitespace, Newline):
            continue
        if token.ttype in (Comment.Single, Comment.Multiline):
            continue
        if token.ttype in (Keyword, DML):
            return token.value.upper()
    return ""


def _has_select_dml_only(statement: sqlparse.sql.Statement) -> bool:
    found_select = False
    for token in statement.flatten():
        if token.ttype is DML:
            if token.value.upper() == "SELECT":
                found_select = True
            else:
                return False
    return found_select


def _walk_tokens(token):
    yield token
    if hasattr(token, "tokens"):
        for child in token.tokens:
            yield from _walk_tokens(child)


def _iter_functions(statement: sqlparse.sql.Statement) -> List[str]:
    functions = []
    for token in _walk_tokens(statement):
        if isinstance(token, Function):
            name = token.get_name()
            if name:
                functions.append(name)
    return functions


def _contains_keyword(statement: sqlparse.sql.Statement, keywords: set[str]) -> bool:
    for token in statement.flatten():
        if token.ttype in (Keyword, DML, DDL) and token.value.upper() in keywords:
            return True
    return False


def _contains_explain_options(statement: sqlparse.sql.Statement) -> bool:
    for token in statement.flatten():
        if token.ttype in (Keyword, Name) and token.value.upper() in {"ANALYZE", "BUFFERS"}:
            return True
    return False


def _should_wrap_with_limit(statement: sqlparse.sql.Statement) -> bool:
    if _contains_keyword(statement, {"FOR", "UPDATE"}):
        return False
    statement_type = statement.get_type().upper()
    if statement_type in {"SELECT", "VALUES", "TABLE", "WITH"}:
        return True
    first_keyword = _first_statement_keyword(statement)
    return first_keyword in {"WITH", "RECURSIVE"}


def _is_production_env() -> bool:
    return settings.ENVIRONMENT.strip().lower() in {"production", "prod"}


def _ensure_analytics_config() -> None:
    global WARNED_MISSING_ANALYTICS_ROLE, WARNED_MISSING_ANALYTICS_SEARCH_PATH

    if not ANALYTICS_DB_ROLE:
        if _is_production_env():
            raise HTTPException(status_code=500, detail="Analytics role is not configured.")
        if not WARNED_MISSING_ANALYTICS_ROLE:
            logger.warning("ANALYTICS_DB_ROLE is not configured; analytics will run as the app user.")
            WARNED_MISSING_ANALYTICS_ROLE = True

    if not ANALYTICS_SEARCH_PATH:
        if _is_production_env():
            logger.error("ANALYTICS_SEARCH_PATH is not configured in production.")
        elif not WARNED_MISSING_ANALYTICS_SEARCH_PATH:
            logger.warning("ANALYTICS_SEARCH_PATH is not configured; schema isolation is not enforced.")
            WARNED_MISSING_ANALYTICS_SEARCH_PATH = True


def _validate_role_name(value: str, label: str) -> str:
    if not re.match(r"^[A-Za-z0-9_]+$", value):
        raise HTTPException(status_code=500, detail=f"Invalid {label} configuration.")
    return value


def _validate_search_path(value: str) -> str:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        raise HTTPException(status_code=500, detail="Invalid analytics search_path configuration.")
    for part in parts:
        _validate_role_name(part, "analytics search_path")
    return ", ".join(parts)


def _audit_query(
    db: Session,
    user_id: int,
    query_hash: str,
    query_length: int,
    duration_ms: int,
    outcome: str,
    row_count: int,
    error_detail: str | None,
) -> None:
    audit_log = AuditLog(
        entity_type="AnalyticsQuery",
        entity_id=0,
        action="EXECUTE",
        user_id=user_id,
        changes={
            "query_sha256": query_hash,
            "query_length": query_length,
            "duration_ms": duration_ms,
            "outcome": outcome,
            "row_count": row_count,
            "max_rows": MAX_RESULT_ROWS,
            "error": error_detail[:200] if error_detail else None,
        },
    )
    db.add(audit_log)
    db.commit()


def _validate_query(query: str) -> sqlparse.sql.Statement:
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Query too long. Max length is {MAX_QUERY_LENGTH} characters.",
        )

    parsed = [stmt for stmt in sqlparse.parse(
        query) if stmt and stmt.value.strip()]
    if len(parsed) != 1:
        raise HTTPException(
            status_code=400, detail="Only single-statement queries are allowed.")

    statement = parsed[0]
    for token in statement.flatten():
        if token.ttype is Punctuation and token.value == ";":
            raise HTTPException(
                status_code=400, detail="Semicolons are not allowed.")

        if token.ttype in (Keyword, DML, DDL):
            keyword = token.value.upper()
            if keyword in DISALLOWED_KEYWORDS:
                raise HTTPException(
                    status_code=400, detail="Only read-only queries are allowed.")

            if token.ttype is DML and keyword != "SELECT":
                raise HTTPException(
                    status_code=400, detail="Only read-only queries are allowed.")

            if token.ttype is DDL:
                raise HTTPException(
                    status_code=400, detail="Only read-only queries are allowed.")

    for name in _iter_functions(statement):
        lowered = name.lower()
        if lowered in BLOCKED_FUNCTIONS or lowered.startswith(BLOCKED_FUNCTION_PREFIXES):
            raise HTTPException(status_code=400, detail="Only read-only queries are allowed.")

    first_keyword = _first_statement_keyword(statement)
    if first_keyword == "EXPLAIN":
        if _contains_explain_options(statement):
            raise HTTPException(status_code=400, detail="Only read-only queries are allowed.")
        return statement

    statement_type = statement.get_type().upper()
    if statement_type in ALLOWED_READONLY_KEYWORDS and statement_type != "WITH":
        return statement

    if first_keyword in ALLOWED_READONLY_KEYWORDS and first_keyword != "WITH":
        return statement

    if statement_type == "WITH" or first_keyword in {"WITH", "RECURSIVE"}:
        if _has_select_dml_only(statement):
            return statement

    raise HTTPException(
        status_code=400,
        detail="Only read-only queries (SELECT, WITH, EXPLAIN, SHOW, VALUES, TABLE) are allowed.",
    )


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

    start_time = time.monotonic()
    query_hash = hashlib.sha256(request.query.encode("utf-8")).hexdigest()
    try:
        _ensure_analytics_config()
        statement = _validate_query(request.query)
    except HTTPException as exc:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        try:
            _audit_query(
                db=db,
                user_id=current_user.user_id,
                query_hash=query_hash,
                query_length=len(request.query),
                duration_ms=duration_ms,
                outcome="blocked",
                row_count=0,
                error_detail=str(exc.detail),
            )
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Audit logging failed") from exc
        raise

    outcome = "success"
    error_detail = None
    rows = []
    keys = []
    row_count = 0
    safe_query = request.query
    safe_params: Dict[str, Any] = {}

    try:
        with SessionLocal() as analytics_db:
            try:
                if ANALYTICS_DB_ROLE:
                    role = _validate_role_name(ANALYTICS_DB_ROLE, "analytics role")
                    analytics_db.execute(text(f'SET LOCAL ROLE "{role}"'))
                if ANALYTICS_SEARCH_PATH:
                    search_path = _validate_search_path(ANALYTICS_SEARCH_PATH)
                    quoted_parts = ", ".join(f'"{p.strip()}"' for p in search_path.split(","))
                    analytics_db.execute(text(f"SET LOCAL search_path = {quoted_parts}"))
                analytics_db.execute(text("SET TRANSACTION READ ONLY"))
                analytics_db.execute(
                    text("SET LOCAL statement_timeout = :timeout"),
                    {"timeout": STATEMENT_TIMEOUT},
                )
                analytics_db.execute(
                    text("SET LOCAL lock_timeout = :timeout"),
                    {"timeout": LOCK_TIMEOUT},
                )
                analytics_db.execute(
                    text("SET LOCAL idle_in_transaction_session_timeout = :timeout"),
                    {"timeout": IDLE_IN_TRANSACTION_TIMEOUT},
                )
                if _should_wrap_with_limit(statement):
                    safe_query = f"SELECT * FROM ({safe_query}) AS limited LIMIT :max_rows"
                    safe_params["max_rows"] = MAX_RESULT_ROWS
                result = analytics_db.execute(text(safe_query), safe_params)
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
        logger.error("Analytics query failed for user %s: %s", current_user.user_id, exc)
        error_detail = str(exc)

    duration_ms = int((time.monotonic() - start_time) * 1000)
    try:
        _audit_query(
            db=db,
            user_id=current_user.user_id,
            query_hash=query_hash,
            query_length=len(request.query),
            duration_ms=duration_ms,
            outcome=outcome,
            row_count=row_count,
            error_detail=error_detail,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Audit logging failed") from exc

    if error_detail:
        raise HTTPException(status_code=400, detail=error_detail)

    if not rows:
        return []

    return [dict(zip(keys, row)) for row in rows]

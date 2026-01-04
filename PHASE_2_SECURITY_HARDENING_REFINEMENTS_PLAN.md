# Phase 2 — Security Hardening (Refinements)

This plan addresses SEC-01, SEC-03, and SEC-04 from `PHASE_2_RISK_REGISTER.md`.

## Scope

**In scope**
- `SEC-01` (Critical): Stricter analytics parsing (single-statement + stronger validation)
- `SEC-03` (High): Self-service user update endpoint
- `SEC-04` (High): Remove hardcoded default secrets; add `.env.example`

**Out of scope**
- New analytics product features or saved-query UI
- Full secrets manager integration (tracked as P2)

## Assumptions

- API router prefix for auth is `/auth`.
- Analytics endpoint remains admin-only and read-only.
- Existing audit logging must continue to capture security-sensitive mutations.

---

## SEC-03 — Add Self-Service User Update

**Goal:** Allow users to update safe fields (password, full name) without reopening admin-only user management.

### Engineering Steps
1. **Define a narrow schema**
   - Add `UserSelfUpdate` (e.g., `full_name`, `password`, **required** `current_password` when changing password) in `api/app/schemas/user.py`.
   - Exclude `email`, `role`, `region_ids`, and `lob_id`.
2. **Add endpoint**
   - Implement `PATCH /auth/users/me` (or `PATCH /auth/me` if you want symmetry with `GET /auth/me`).
   - Load the current user from DB with necessary relationships.
3. **Apply update rules**
   - If `password` is provided, require `current_password` and verify via `verify_password` (prevents token theft from silently changing password).
   - Update `full_name` and/or `password_hash` only.
   - Do not allow email, role, regions, or LOB changes in this endpoint.
4. **Audit logging**
   - Log changes (e.g., `full_name`, `password` changed) with `entity_type="User"`, `action="UPDATE_SELF"`, and `user_id=current_user.user_id`.
5. **Response shape**
   - Return `UserResponse` with fresh data (`get_user_with_lob` for consistency).

### Acceptance Criteria
- Non-admin can update **only** their own full name and password.
- Role/region/LOB/email changes remain admin-only.
- Audit log records self-service updates without storing password values.

### Tests
- Unit/integration: update full name only.
- Unit/integration: update password with and without `current_password`.
- Negative: attempts to update `role`, `region_ids`, `lob_id`, or `email` are ignored or rejected.

---

## SEC-01 — Stricter Analytics Parsing (Single-Statement)

**Goal:** Enforce single-statement execution and reduce SQL injection bypass risk on the admin analytics endpoint.

### Engineering Steps
1. **Add a SQL parser dependency**
   - Use `sqlparse` (lightweight, sufficient for statement/token validation).
   - **Required:** Add `sqlparse` to `api/requirements.txt`.
2. **Single-statement validation**
   - Parse the query into statements.
   - Reject if the parser finds more than one statement.
   - Reject if any semicolon token appears (even if single-statement), to satisfy the explicit “block `;`” requirement.
3. **Stricter statement-type checks**
   - Confirm the statement type is in the allowed read-only set (`SELECT`, `WITH`, `EXPLAIN`, `SHOW`, `VALUES`, `TABLE`).
   - Reject any utility commands (e.g., `COPY`, `SET`, `CALL`, `DO`, `VACUUM`), even if they appear in a single statement.
4. **Query size and shape limits**
   - Add `MAX_QUERY_LENGTH` (e.g., 10–20k chars).
   - Optionally cap number of columns returned to reduce large payloads.
5. **Keep existing guards**
   - Preserve `SET TRANSACTION READ ONLY`, `statement_timeout`, and row cap logic.
   - Keep audit log with query hash and execution metadata.

### Implementation Notes (sqlparse)

**Suggested validation snippet (illustrative):**
```python
import sqlparse
from sqlparse.tokens import Punctuation

parsed = sqlparse.parse(raw_query)
if len(parsed) != 1:
    raise HTTPException(status_code=400, detail="Only single-statement queries are allowed.")

stmt = parsed[0]
for token in stmt.flatten():
    if token.ttype is Punctuation and token.value == ";":
        raise HTTPException(status_code=400, detail="Semicolons are not allowed.")

statement_type = stmt.get_type().upper()
if statement_type not in {"SELECT", "WITH", "EXPLAIN", "SHOW", "VALUES", "TABLE"}:
    raise HTTPException(status_code=400, detail="Only read-only queries are allowed.")
```

### Dependency Update Checklist

- Add `sqlparse` to `api/requirements.txt`.
- Rebuild the API image/container to include the new dependency.
- Verify `pip freeze` (or container build logs) shows `sqlparse` installed.

### Acceptance Criteria
- Any query containing `;` is rejected.
- Only a single read-only statement is accepted.
- Endpoint remains admin-only and read-only at DB/session level.
- Audit log records outcome and query hash for all attempts.

### Tests
- Valid single-statement SELECT passes.
- Queries with `;` fail (including `SELECT 1;`).
- Multi-statement input fails.
- Disallowed statement types fail (`COPY`, `SET`, `INSERT`, etc.).

---

## SEC-04 — Secrets Management Cleanup

**Goal:** Remove hardcoded default secrets and require explicit configuration via environment variables.

### Engineering Steps
1. **Remove defaults from `Settings`**
   - Remove default values for `SECRET_KEY` and `DATABASE_URL` to force Pydantic validation errors when missing.
   - Ensure `ENVIRONMENT` defaults to `development` only if it is not a secret.
2. **Add `.env.example`**
   - Provide non-secret placeholders and short guidance for local dev.
   - Include all required keys (DB URL, JWT issuer/audience, etc.).
3. **Update deployment artifacts**
   - Ensure Docker/compose and CI set required env vars.
   - Document how to source secrets from secret managers (P1 doc update).
4. **Startup validation**
   - Keep production fail-fast checks (already present).
   - Confirm errors are clear when required env vars are missing.

### Acceptance Criteria
- No hardcoded secrets in code.
- App fails fast in production if required env vars are missing.
- `.env.example` enables local development with explicit values.

### Tests
- Boot with missing `SECRET_KEY`/`DATABASE_URL` in production → startup fails.
- Boot in development with `.env` populated → startup succeeds.

---

## Implementation Order

1. SEC-01 — stricter analytics parsing (blocks injection vectors)
2. SEC-03 — self-service user update endpoint
3. SEC-04 — secrets cleanup and `.env.example`

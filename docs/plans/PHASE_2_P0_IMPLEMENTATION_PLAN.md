# Phase 2 — P0 Remediation Implementation Plan

This document turns the **P0** items in `PHASE_2_RISK_REGISTER.md` into an executable implementation plan (engineering + deployment), suitable for audit/approval.

## Scope

**In scope (P0 defined in register):**
- `SEC-01`, `SEC-02`, `SEC-03`, `SEC-04`, `PERF-04`, `REL-01`, `REL-03`

**Not in scope (no P0 currently defined in register):**
- `DATA-01`, `PERF-01`, `PERF-02`, `PERF-03`, `REL-02` (treat as P1 decision items; see “No-P0 Items”)

## Assumptions (explicit)

- Production DB is **PostgreSQL**.
- “Production” is controlled by `ENVIRONMENT=production` in `api/app/core/config.py`.
- Requests are served behind an ingress/reverse proxy where **request body size limits** can be enforced (or equivalent platform settings).
- `AuditLog` is the authoritative audit mechanism for security-relevant actions in production.

## Audit Review Response (findings confirmed + plan adjustments)

- **SEC-04 (localhost DB access)**: Confirmed. Remove any hard block on `localhost/127.0.0.1` in production; those are valid in sidecar/proxy/service-mesh patterns. Use “known default” and “known dev credential” checks instead; emit warnings for localhost rather than failing startup.
- **SEC-01 (connection/session leak)**: Confirmed. Any separate analytics DB session/connection must be created with a context manager or `try...finally` ensuring `rollback()` (on error) and `close()` always happen.
- **SEC-02 (orphaned regions)**: Confirmed. Self-registration must ignore (or reject) `region_ids` so USER-role accounts cannot persist region associations.
- **REL-01 (atomic transaction + privileges)**: Confirmed. Ensure the DB role used by the API can write business tables and `audit_logs` in the same transaction.
- **PERF-04 (upload limits vs ingress)**: Confirmed. Ensure ingress limits are configured intentionally relative to app limits; otherwise the proxy may emit a generic 413 before the app can return a structured JSON error.

## P0 Evaluation (what’s good / what must be clarified)

- **SEC-01**: Correct direction (admin-gate + timeouts + caps + audit), but “DB/session read-only” must be implemented in a way that cannot accidentally commit writes from the analytics query.
- **SEC-02**: Correctly removes privilege escalation via `role_code`; still allows uncontrolled account creation (spam) unless route is gated at perimeter or rate-limited (P1).
- **SEC-03**: Admin-only gating is safe; may be operationally restrictive if validators/approvers need user lookup for assignments—confirm expected UX. If needed, add a *separate* “minimal directory lookup” endpoint later (P1).
- **SEC-04**: Adds the right fail-fast checks; do **not** treat localhost DB access as inherently unsafe in production (sidecar/proxy patterns exist). Prefer checking for **known defaults** / **known dev credentials** and emit warnings (not failures) for localhost usage.
- **PERF-04**: Conditional P0 is reasonable; even trusted-role DoS is still a real availability risk. Recommend implementing conservative limits regardless of role breadth if endpoints are internet-exposed.
- **REL-01**: Straightforward; ensure the audit log write is in the same transaction as the imported results.
- **REL-03**: Straightforward; use response background cleanup consistent with existing PDF endpoints.

## Execution Order (recommended)

1) `SEC-02` + `SEC-03` (stop privilege escalation / account takeover vectors)
2) `SEC-01` (reduce blast radius of raw SQL execution)
3) `SEC-04` (prevent unsafe prod deployments)
4) `PERF-04` (prevent oversized upload DoS)
5) `REL-01` + `REL-03` (audit correctness + disk leak prevention)

## Implementation Plan by Risk

### SEC-02 — Force self-registration role to USER

**Target behavior (P0):** `/auth/register` creates only `USER` accounts regardless of supplied `role`/`role_code`.

**Engineering steps**
1. Update `api/app/api/auth.py` `register` to ignore client-supplied role and resolve the role server-side as `RoleCode.USER`.
2. **Required (data integrity):** Ignore (or reject with 400) any `region_ids` provided during self-registration so USER-role accounts cannot persist region associations.
3. Add a regression test (or extend an existing auth test) ensuring a payload with `role_code=ADMIN` still results in a `USER` role and persists **no regions**.

**Operational steps**
- If `/auth/register` is not required in production, additionally block at ingress (route deny) to reduce account-spam risk (still compatible with the P0 register plan).

**Acceptance checks**
- A non-admin can register, but the created user’s `role_code` is always `USER`.
- No payload can create `ADMIN`, `VALIDATOR`, `GLOBAL_APPROVER`, or `REGIONAL_APPROVER` via self-registration.
- A self-registered USER has **no region associations** even if `region_ids` are sent in the request.

**Rollback**
- Revert the server-side override (and re-open only if protected by an explicit admin workflow).

---

### SEC-03 — Gate user management endpoints behind ADMIN

**Target behavior (P0):** Only `ADMIN` can call `GET /auth/users`, `GET /auth/users/{id}`, `PATCH /auth/users/{id}`, `DELETE /auth/users/{id}`.

**Engineering steps**
1. Add an explicit admin guard at the top of each endpoint in `api/app/api/auth.py`:
   - `list_users`
   - `get_user`
   - `update_user`
   - `delete_user`
2. Ensure the guard is a shared helper (local function or dependency) to keep behavior consistent.

**Operational consideration (confirm before merge)**
- If validators need to search/select users (e.g., assignment flows), do **not** weaken these endpoints. Instead, plan a separate P1 “directory lookup” endpoint that returns minimal fields and has tight role gating.

**Acceptance checks**
- Non-admin receives 403 for all four endpoints.
- Admin retains existing behavior.

**Rollback**
- Revert gating changes (not recommended without replacing with a safer alternative).

---

### SEC-01 — Harden ad-hoc analytics SQL endpoint

**Target behavior (P0):**
- Only `ADMIN` can execute.
- Queries are bounded (timeout + result size).
- Execution is auditable.
- Writes are prevented at the transaction level (not by string parsing alone).

**Key implementation warning (must address):**
`get_current_user` already executes DB queries using the injected `db` session before `execute_query()` runs. That means `SET TRANSACTION READ ONLY` cannot reliably be applied to *that same transaction* after auth queries have run.

**Engineering steps**
1. **Admin gate** `POST /analytics/query` in `api/app/api/analytics.py`.
2. Execute the analytics query using a **separate, dedicated DB session/connection** created inside the endpoint, and **guarantee closure** via a context manager (`with ...`) or `try...finally`:
   - Start a fresh transaction for the analytics session.
   - Set transaction mode to **READ ONLY** as the first statement (e.g., `SET TRANSACTION READ ONLY`).
   - Set `statement_timeout` for the analytics session/transaction (e.g., `SET LOCAL statement_timeout = '5s'`).
   - Execute the query and always `ROLLBACK`/`CLOSE` the analytics session (no commit required).
3. **Bound response size**:
   - Replace `fetchall()` with a capped fetch (`fetchmany(max_rows + 1)`), then:
     - If exceeded, return a 400 with an explicit message (“Result too large; add LIMIT”) rather than silently truncating.
   - Cap returned columns if needed (optional for P0; cap rows is the primary safety control).
4. **Audit logging**:
   - Record an `AuditLog` entry (using the normal request session) including:
     - `user_id` (actor)
     - `query_sha256` (hash of the raw query)
     - `query_length`
     - `duration_ms`
     - outcome (`success`/`error`/`timeout`/`too_large`)
   - Do **not** persist full raw SQL by default; store hash + length to avoid sensitive query contents in the audit DB.
5. Keep the existing “read-only prefix allowlist” as an additional guardrail, but treat it as secondary to the read-only transaction + timeout.

**Operational steps**
- Decide initial values (P0 defaults):
  - `statement_timeout`: 5–10 seconds
  - `max_rows`: 1,000 (or lower)
- Add configuration knobs via env/settings if this must be tunable without code changes.

**Acceptance checks**
- Non-admin receives 403.
- Attempted `INSERT/UPDATE/DELETE` fails even if allowed keywords are bypassed (enforced by transaction read-only).
- Expensive queries are terminated by timeout.
- Over-large result sets are rejected with a clear error.
- Every execution attempt produces an auditable record (success/failure) without committing any query-side writes.
- Repeated executions do not leak DB connections (connection pool utilization remains stable).

**Rollback**
- Disable the endpoint route in production (feature flag / router include conditional) until a safer alternative exists.

---

### SEC-04 — Fail-fast production configuration checks

**Target behavior (P0):** App refuses to start in production if it detects default or unsafe config.

**Engineering steps**
1. Update `api/app/core/config.py` `validate_production_settings()` to add:
   - `DATABASE_URL` checks:
     - Fail if `DATABASE_URL` equals the known dev default.
     - Fail if it contains known dev credentials (e.g., `mrm_user:mrm_pass`), unless an explicit override is approved.
     - **Do not fail** if host is `localhost`/`127.0.0.1` (valid sidecar/proxy patterns); instead emit a **warning** recommending confirmation of the deployment pattern.
2. Keep existing checks (min secret length, issuer/audience required, UAT tools break-glass).
3. Add a documented “break-glass override” mechanism only if required (e.g., allow dev defaults in prod only with explicit ticket env var). Prefer *not* supporting this for DB credentials.

**Operational steps**
- Update deployment documentation/runbooks to list required env vars and their constraints.
- Validate in CI/CD by running a minimal startup check with `ENVIRONMENT=production` in a pre-deploy stage.

**Acceptance checks**
- Starting with `ENVIRONMENT=production` and default `SECRET_KEY` fails.
- Starting with `ENVIRONMENT=production` and default `DATABASE_URL` fails.
- Starting with valid prod secrets/config succeeds.
- If `DATABASE_URL` uses `localhost`/`127.0.0.1` with non-default credentials, startup succeeds and emits a clear warning (sidecar/proxy expected).

**Rollback**
- Temporarily relax only the new DB URL checks if they block legitimate prod patterns (retain SECRET_KEY/JWT checks).

---

### PERF-04 — Enforce upload size limits for CSV imports

**Target behavior (P0):** Oversized uploads are rejected early with 413, preventing memory/CPU pressure.

**Endpoints in scope**
- `api/app/api/monitoring.py` `import_cycle_results_csv`
- `api/app/api/lob_units.py` `import_lob_csv`

**Operational steps (preferred first line of defense)**
1. Configure ingress/reverse proxy max request size. For consistent UX, set proxy limits **slightly above** the app-enforced limits so the app can return a structured JSON 413 for “near-limit” uploads (very large uploads may still be rejected at the proxy with a generic 413).
2. If using a managed gateway (Azure), apply equivalent request size limits at that layer.

**Engineering steps**
1. Define per-endpoint max sizes (P0 defaults):
   - Monitoring results CSV: 5 MB
   - LOB import CSV: 10 MB (adjust based on expected enterprise file sizes)
2. In each endpoint, enforce the limit before parsing:
   - Read in chunks up to the limit; if exceeded, raise `HTTPException(status_code=413, ...)`.
   - Avoid holding multiple copies of the file contents in memory.

**Acceptance checks**
- Uploads above limit return 413 without attempting full parse.
- Normal-sized uploads behave as before.
- Ingress/proxy limits are configured intentionally relative to app limits (so “near-limit” uploads reach the app and get a structured JSON 413 where desired).

**Rollback**
- Increase limits if false positives occur, while preserving an upper bound.

---

### REL-01 — Persist monitoring CSV import audit logs

**Target behavior (P0):** Successful monitoring CSV imports always create a persisted audit log entry.

**Engineering steps**
1. In `api/app/api/monitoring.py` `import_cycle_results_csv`, ensure the audit log is written **before** the commit that finalizes the import results, or ensure there is a second commit that is safe and cannot commit untrusted writes.
2. Prefer a single atomic transaction:
   - Import changes
   - Audit log insert
   - One `commit()`
3. Confirm the production DB role used by the API can write both the monitoring tables and `audit_logs` in the same transaction (no cross-DB writes, no restricted grants that would break the commit).
4. Add a regression test that imports with `dry_run=false` and asserts an audit log entry exists.

**Acceptance checks**
- After a successful import, the audit log record exists with correct created/updated/skipped counts.
- If import fails, neither results nor audit log are persisted (atomicity).

**Rollback**
- Revert to previous behavior (not recommended; compliance risk).

---

### REL-03 — Prevent PDF temp file leak in risk assessment export

**Target behavior (P0):** Risk assessment PDF generation does not leak temp files.

**Engineering steps**
1. In `api/app/api/risk_assessment.py` where the PDF is written with `NamedTemporaryFile(delete=False)`:
   - Attach a `BackgroundTask` to delete the file after response is sent (pattern already used in `api/app/api/validation_workflow.py`).
2. Add a basic test or manual verification:
   - Generate PDF, confirm file is removed after response completes.

**Acceptance checks**
- No persistent PDF files accumulate in the temp directory under repeated downloads.

**Rollback**
- Switch to in-memory streaming if filesystem cleanup is unreliable in the target deployment.

## No-P0 Items (decision log)

The following risks currently have **no P0** in `PHASE_2_RISK_REGISTER.md`. Confirm that deferring to P1 is acceptable, given severity:
- `DATA-01` (High): If exploitation window is a concern, consider an interim P0 guardrail (e.g., per-model advisory lock around creation) even before full DB-level enforcement.
- `PERF-01` (High): If KPI report is on a user-facing dashboard in production, consider a P0 cache TTL to prevent timeouts.
- `PERF-02`, `PERF-03` (Medium), `REL-02` (Medium): P1-only is typically acceptable unless current prod load is already near limits.

## Validation Plan (P0)

**Automated**
- Run backend tests relevant to auth, analytics, monitoring import, and PDF export.
- Add/extend targeted tests where noted above (SEC-02, REL-01).

**Manual**
- Attempt privileged operations as non-admin (expect 403) for SEC-01/02/03.
- Start app with `ENVIRONMENT=production` + bad env vars (expect startup failure) for SEC-04.
- Upload oversized CSVs to both endpoints (expect 413) for PERF-04.
- Download risk assessment PDFs repeatedly and observe temp dir stability for REL-03.

## Rollout & Rollback (P0)

- Roll out behind a short-lived release branch/hotfix track (P0).
- Prefer feature flags for high-risk surfaces (`/analytics/query`, `/auth/register`).
- Rollback strategy per item is defined above; highest-confidence rollback is to **disable the risky endpoint** while preserving auth hardening.

# Phase 3 Plan: Risk Register Closeout (Validation + Evidence)

## Objective
Convert all “Implemented; Pending Test” items in `PHASE_2_RISK_REGISTER.md` into “Verified” by running repeatable, automated validations (concurrency, performance, reliability) and producing audit-ready evidence. Minimize production risk and avoid false positives.

## Scope (From Closeout Report)
- **Validate remaining risks**: DATA-01, PERF-01..04, REL-01..03
- **Security regression suite**: SEC-01, SEC-02, SEC-03 (plus SEC-04 positive + negative validation)
- **Operational hygiene**: remove temporary prod admin accounts created for verification (after sign-off)
- **Docs**: keep `ARCHITECTURE.md` accurate as changes land; update final closeout artifacts

## Guiding Principles
- Prefer **automation** (tests/scripts) over manual runbooks.
- Use **staging or staging-equivalent** isolated DBs for destructive/edge-case validations.
- Make tests **repeatable and idempotent** (create fixtures; clean up; no persistent test data in prod).
- Measure performance using **query-count + latency** (not just wall clock).

## Environment & Baseline Assumptions
- **Staging definition**: either (a) a deployed staging environment with prod-like config, or (b) a staging-equivalent local Docker Compose stack with prod-like env vars and an isolated Postgres database. If no staging exists, use (b) and label evidence accordingly.
- **Benchmark dataset sizes (initial targets)**:
  - KPI report: 10k models (with representative validations/recommendations/monitoring rows).
  - Regional compliance report: 10k report rows.
  - Attestation cycles list: 2k cycles with realistic record counts.
- **Performance baselines (initial targets; adjust only with explicit sign-off)**:
  - KPI report: query count ≤ 12; p95 ≤ 2.5s uncached, ≤ 300ms cached.
  - Regional compliance: query count ≤ 4; p95 ≤ 1.5s at 10k rows.
  - Attestation cycles: query count ≤ 4; p95 ≤ 1.0s at 2k cycles; memory delta ≤ 100MB.
  - CSV imports: monitoring (5MB max) and LOB (10MB max) keep RSS delta ≤ 75MB; oversized files fail with 413 within 1MB past the limit.

---

## Workstreams

### 1) Security Regression Suite (SEC-01..04)
**Goal**
Prove critical security fixes remain effective and are safe to close out.

**Plan**
1. **SEC-01 (Analytics hardening)**: run automated regression tests to assert:
   - non-admin gets 403
   - read-only role switching (`current_user = analytics_readonly`)
   - single-statement enforcement
   - DDL and dangerous functions blocked (e.g., `DROP`, `pg_sleep`)
   - EXPLAIN ANALYZE rejected while EXPLAIN (non-ANALYZE) is allowed
   - audit log entries created on allow/deny paths
2. **SEC-02 (Registration)**: attempt self-register with `role_code=ADMIN` and `region_ids`; assert server forces `USER` and regions are empty.
3. **SEC-03 (User mgmt)**: assert non-admin gets 403 for list/get/update/delete; verify `/auth/users/me` allows safe fields only and requires `current_password` for password changes.
4. **SEC-04 (Positive + Negative)**:
   - **Positive**: app starts with valid prod config; `/health` and `/ready` return 200.
   - **Negative**: startup fails with missing/weak `SECRET_KEY` or localhost/dev `DATABASE_URL` (staging/CI only).

**Exit criteria**
- All four SEC items pass automated regression checks in CI or staging-equivalent environment.
- Evidence captures both positive and negative config validation for SEC-04.

---

### 2) Test Harness & Environments (Foundation)
**Deliverables**
- A Postgres-backed integration test path (local + CI) for concurrency/DB-lock assertions (SQLite cannot validate advisory locks or transaction semantics).
- A small “bench harness” for reports that records:
  - DB query counts (via SQLAlchemy event hooks)
  - p50/p95 latency
  - peak memory where feasible (process RSS sampling)

**Plan**
1. Add a `TEST_DATABASE_URL`-driven pytest marker (e.g., `@pytest.mark.postgres`) and skip if unset.
2. Add a lightweight benchmark runner (Python script) that can:
   - seed/generate a large synthetic dataset in an isolated DB
   - call report endpoints with stable parameters
   - print machine-readable output (JSON) for evidence

**Exit criteria**
- CI can run both unit tests (SQLite) and opt-in Postgres integration tests.
- Bench harness can be executed locally and in staging-equivalent.

---

### 3) DATA-01 (Concurrency): Prevent Duplicate Validation Requests
**Goal**
Prove advisory-lock serialization prevents overlapping active validations for the same model set under parallel requests.

**Plan**
1. Create a Postgres integration test that:
   - spins up N parallel requests to the validation request creation endpoint for the *same* `model_id`(s)
   - asserts exactly one request is created (others receive deterministic “conflict/duplicate” response)
   - verifies no deadlocks by requiring model IDs are locked in sorted order
2. Add a follow-up test for multi-model requests (sorted lock acquisition).

**Exit criteria**
- Repeated parallel runs never produce >1 active validation for identical model sets.
- No deadlocks observed under stress (e.g., 100 iterations).

---

### 4) PERF-01..04 (Performance & Scaling)

#### PERF-01: KPI Report
**Goal**
Demonstrate KPI report is no longer N+1 and remains correct relative to legacy business rules.

**Plan**
1. Correctness check: compare new batch/SQL results vs legacy Python logic on a small dataset (golden cases: “INTERIM Expired”, “Submission Overdue”, boundary dates).
2. Scaling check: run KPI for datasets of increasing size (e.g., 1k / 5k / 20k models) and record:
   - query count (should be O(1) relative to model count)
   - p95 latency
   - cache hit behavior across repeated calls (TTL respected)

**Exit criteria**
- Query count ≤ 12; p95 ≤ 2.5s uncached and ≤ 300ms cached at 10k models.
- Business-rule parity confirmed for edge cases.

#### PERF-02: Regional Compliance Report
**Goal**
Prove per-row approval lookups were eliminated (no N+1).

**Plan**
1. Add query-count assertion test (single report call; assert query count does not scale with rows).
2. Benchmark runtime on larger dataset; record query plan if needed.

**Exit criteria**
- Query count ≤ 4; p95 ≤ 1.5s at 10k rows; runtime scales with result size, not row-wise lookups.

#### PERF-03: Attestation Cycles List
**Goal**
Prove counts are computed in SQL and cycles list is paginated to prevent memory spikes.

**Plan**
1. Test that the endpoint returns paginated responses and does not materialize per-cycle records.
2. Benchmark with large attestation history; record memory and query count.

**Exit criteria**
- Query count ≤ 4; p95 ≤ 1.0s at 2k cycles; memory delta ≤ 100MB; pagination enforced.

#### PERF-04: CSV Imports (Streaming)
**Goal**
Prove CSV imports stream row-by-row, enforce upload limits during read, and do not OOM.

**Plan**
1. Add tests that:
   - feed a streamed file-like object and assert it is not fully read into memory
   - exceed the configured size limit mid-stream and assert the request fails safely
2. Soak test in staging with a “large but allowed” file and measure memory.

**Exit criteria**
- Monitoring import (≤ 5MB) and LOB import (≤ 10MB) keep RSS delta ≤ 75MB.
- Oversized inputs fail with 413 within 1MB past the configured limit.

---

### 5) REL-01..03 (Reliability)

#### REL-01: Monitoring CSV Import Audit Log
**Plan**
1. Add integration test calling the import endpoint with `dry_run=false`.
2. Assert exactly one audit log row is persisted for the import and includes expected metadata (actor + counts).

**Exit criteria**
- Import success always produces a persisted audit log in the same unit of work.

#### REL-02: Bulk Deployment Confirmation Savepoints
**Plan**
1. Create a test fixture with multiple deployment tasks where one update is guaranteed to fail.
2. Assert:
   - successful items commit
   - failure is reported
   - failed item changes are rolled back (no partial persistence)
   - session remains usable and subsequent operations succeed

**Exit criteria**
- Partial success works; failed item is fully rolled back; one failure doesn’t poison the batch/session.

#### REL-03: Risk Assessment PDF Temp Cleanup
**Plan**
1. Add a test that downloads PDFs repeatedly and confirms temp artifacts are cleaned (via mocking `os.unlink` or inspecting temp directory usage in a controlled environment).
2. Add a simple disk-usage guard in staging checks (optional).

**Exit criteria**
- No unbounded temp-file growth under repeated PDF generation.

---

## Closeout & Governance
1. Update `PHASE_2_RISK_REGISTER.md` statuses to “Verified” only when evidence is captured.
2. Append benchmark/test artifacts to an evidence bundle (e.g., `docs/` or a dedicated report file) with timestamps and commands.
3. Remove temporary admin accounts created for verification (and associated audit logs if required by FK policy) after sign-off.
4. Re-run an `ARCHITECTURE.md` reconciliation pass after any additional changes land; keep deployment and security guarantees accurate.

## Definition of Done (Phase 3)
- All risks in `PHASE_2_RISK_REGISTER.md` are either **Verified (Prod/Staging/CI)** with evidence, or explicitly deferred with owner + date.
- `PHASE_2_RISK_REGISTER_CLOSEOUT_REPORT.md` updated to reflect final verification outcomes.
- Temporary verification access removed (accounts/credentials rotated).

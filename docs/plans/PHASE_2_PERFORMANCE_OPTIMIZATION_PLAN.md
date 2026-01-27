# Phase 2 — Performance Optimization (N+1 & Scaling)

This plan addresses PERF-01 through PERF-04 from `PHASE_2_RISK_REGISTER.md`.

## Scope

**In scope**
- `PERF-01` (High): KPI report performance
- `PERF-02` (Medium): Regional compliance report
- `PERF-03` (Medium): Attestation cycles list
- `PERF-04` (Medium): CSV import streaming

**Out of scope**
- Non-performance items and any P0 security/reliability fixes

## Assumptions

- Production DB is PostgreSQL.
- Performance improvements should preserve existing API response shapes.
- P0 upload size limits are already in place (from `PHASE_2_P0_IMPLEMENTATION_PLAN.md`).

## PERF-01 — Optimize KPI Report

**Goal:** Prevent KPI timeouts as inventory size grows by eliminating per-model query loops.

**Approach:** Introduce short-lived caching and replace per-model queries with batch queries.

### Engineering Steps
1. **Short-lived caching (fast relief)**
   - Cache KPI results by `(region_id, team_id)` with a short TTL (e.g., 5–15 minutes).
   - Invalidate cache on model/validation state changes if possible; otherwise rely on TTL.
2. **Batch-load validation status (structural fix)**
   - Replace per-model calls to `calculate_model_revalidation_status()` with set-based SQL queries:
     - Most recent approved validation per model
     - Policy lead times by risk tier
     - Derived “overdue” / “on time” counts
   - Batch-join to approval status rather than re-calling status functions per model.
   - **Parity check:** Ensure the SQL logic exactly matches current business rules (e.g., INTERIM vs full validation handling, grace periods, “Should Create Request,” “INTERIM Expired”).
3. **Reduce repeated DB access**
   - Pre-fetch common lookup tables once (e.g., taxonomies, tiers).
   - Avoid multiple DB hits for the same model data.

### Acceptance Criteria
- KPI endpoint uses O(1) DB queries relative to model count.
- Response time meets agreed SLO at projected inventory size.
- Cached responses are returned within the TTL window without correctness regressions.

### Tests
- Add a performance test (or benchmark script) to compare query counts before/after.
- Add a unit test for caching key correctness `(region_id, team_id)`.
- Add golden test cases comparing SQL-derived status outputs to `calculate_model_revalidation_status()` for edge-case scenarios.

### Rollback
- Disable caching and revert to prior logic if result correctness is affected.

---

## PERF-02 — Optimize Regional Compliance Report

**Goal:** Reduce DB load by eliminating per-row approval lookups.

**Approach:** Bulk-fetch approvals in one query or join approvals in the base query.

### Engineering Steps
1. **Bulk-fetch approvals**
   - Collect `(request_id, region_id)` pairs from the base query.
   - Fetch all matching approvals in one query.
   - Build an in-memory map keyed by `(request_id, region_id)`.
2. **Swap per-row lookup**
   - Replace the per-row `db.execute(approval_query)` with lookup from the map.
3. **Index support**
   - Ensure an index on `(request_id, region_id, approval_type)` for approvals.

### Acceptance Criteria
- Regional compliance report uses a constant number of DB queries.
- Total report generation time scales primarily with result size, not row-by-row lookups.

### Tests
- Add a test that asserts one approval query for a multi-row report.
- Add a regression test to confirm approval data correctness per region.

### Rollback
- Revert to prior per-row lookup if approval accuracy is compromised.

---

## PERF-03 — Optimize Attestation Cycles List

**Goal:** Prevent memory spikes and N+1 queries when listing cycles.

**Approach:** Use SQL aggregation and pagination.

### Engineering Steps
1. **Replace Python aggregation**
   - Use `GROUP BY cycle_id` with `COUNT(*)` and `SUM(CASE...)` for status counts.
2. **Paginate cycles**
   - Add `limit`/`offset` to cycles query (or cursor-based pagination).
   - Default to recent cycles only if UI permits.
3. **Index support**
   - Ensure index on `attestation_records(cycle_id, status)` to support aggregation.

### Acceptance Criteria
- Listing cycles does not materialize all records in Python.
- Response time and memory usage remain stable as history grows.

### Tests
- Add a test that lists cycles and verifies aggregated counts match source records.
- Add pagination tests.

### Rollback
- Revert pagination changes if UI workflows are disrupted.

---

## PERF-04 — Stream-Parse CSV Imports

**Goal:** Support larger files with constant memory usage.

**Approach:** Process CSVs row-by-row instead of loading the entire file into memory.

### Engineering Steps
1. **Streaming read**
   - Use `UploadFile.file` as a file-like stream; wrap with `io.TextIOWrapper` and `csv.DictReader`.
2. **Row-by-row processing**
   - Parse and validate each row incrementally.
   - Track counts without storing all rows in memory.
3. **Enforce size limit during streaming**
   - Wrap the underlying stream in a “limited” reader that counts bytes read and raises once `MAX_BYTES` is exceeded.
   - If `Content-Length` is available, use it as a pre-check, but still enforce a **fail-during-read** cap in the stream wrapper.
4. **Batch commits (optional)**
   - Commit in batches (e.g., every 500 rows) to balance memory and transaction size.
5. **Preserve existing P0 size limits**
   - Keep max-size enforcement; streaming ensures constant memory for near-limit files.

### Acceptance Criteria
- CSV imports run with constant memory usage (no full file read).
- Large but allowed files complete successfully without OOM.
- Oversized streams are rejected during read once the limit is exceeded.

### Tests
- Add a CSV import test with a large in-memory stream to validate streaming logic.
- Verify behavior with malformed rows still matches prior error handling.

### Rollback
- Revert to current in-memory parsing if streaming introduces regression in import behavior.

## Implementation Order

1. PERF-01 (High) — KPI report batch-loading + caching
2. PERF-02 (Medium) — regional compliance report bulk approvals
3. PERF-03 (Medium) — attestation cycles aggregation + pagination
4. PERF-04 (Medium) — streaming CSV imports

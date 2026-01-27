# Phase 2 — High-Priority Functional Fixes (Concurrency & Reliability)

This plan covers the next high-priority functional fixes after P0: DATA-01 (Concurrency) and REL-02 (Bulk Reliability).

## Scope

**In scope**
- `DATA-01` (High): Prevent duplicate validation requests under concurrency
- `REL-02` (Medium): Robust bulk deployment confirmation with partial success

**Out of scope**
- All other P1/P2 items listed in `PHASE_2_RISK_REGISTER.md`

## Assumptions

- Production DB is PostgreSQL.
- Validation request creation happens in `api/app/api/validation_workflow.py`.
- Bulk deployment confirmation is implemented in `api/app/api/version_deployment_tasks.py`.

## Plan A — DATA-01: Prevent Duplicate Validation Requests

**Goal:** Parallel requests cannot create overlapping active validations for the same model(s).

**Approach:** Use database-level advisory locks around the conflict check + insert to ensure serialization by model, namespaced to avoid cross-feature collisions.

### Engineering Steps
1. **Lock selection**
   - Use two-argument PostgreSQL advisory locks to avoid global lock collisions:
     - `VALIDATION_LOCK_NAMESPACE = 42` (arbitrary constant)
     - `SELECT pg_advisory_xact_lock(:namespace, :model_id)`
   - Acquire locks in **sorted model_id order** to avoid deadlocks on multi-model requests.
2. **Wrap creation flow**
   - In `create_validation_request`, acquire locks **before** conflict checks.
   - Keep conflict check + insert inside the same transaction.
3. **Release**
   - Advisory locks are released automatically at transaction end; ensure errors roll back the transaction.
4. **Edge cases**
   - Ensure the lock covers both targeted and non-targeted validation conflict rules.
   - Confirm multi-model requests lock all model_ids involved.

### Acceptance Criteria
- Two concurrent requests for the same model(s) cannot both create active non-targeted validations.
- Multi-model requests remain atomic (either all models validated together or none).
- No deadlocks under high concurrency (locks acquired in deterministic order).

### Tests
- Add a concurrency test that spawns parallel request creation for the same model and asserts exactly one succeeds.
- Add a multi-model test verifying locks are acquired in sorted order.

### Rollback
- Remove advisory locking and revert to previous behavior (not recommended unless lock contention is unacceptable).

## Plan B — REL-02: Robust Bulk Deployment Confirmation

**Goal:** One failure in bulk confirmation does not break the session or rollback other successful updates.

**Approach:** Wrap each task update in a **savepoint** (`begin_nested()`) with per-task rollback on failure.

### Engineering Steps
1. **Per-task savepoint**
   - In `bulk_confirm_deployments`, wrap each task update in `with db.begin_nested():`.
   - `flush()` inside each savepoint to surface errors early.
2. **Error handling**
   - On exception, rollback to the savepoint and record failure details.
   - Continue processing remaining tasks.
3. **Commit**
   - Commit once at the end for all successful tasks.
   - Ensure audit logs for successful tasks are persisted in the same transaction.

### Acceptance Criteria
- One failing task does not invalidate the SQLAlchemy session.
- Successful tasks are committed; failed tasks are not partially applied.
- Response counts accurately reflect DB state.

### Tests
- Add a bulk test where one task fails (e.g., invalid status transition) and verify others succeed.
- Add a test for repeated bulk calls to ensure session remains healthy.

### Rollback
- Revert to previous bulk behavior if savepoints introduce unacceptable overhead.

## Implementation Order

1. DATA-01 (High) — concurrency lock in validation request creation
2. REL-02 (Medium) — savepoints in bulk confirmation loop

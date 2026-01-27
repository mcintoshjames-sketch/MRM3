# Monitoring Plan Transfer & Immutability Test Plan

This verification plan defines the test procedures required to confirm the safe implementation of the Monitoring Plan Transfer logic and the Immutable Cycle Scope primitives. It specifically addresses the risks of history loss, race conditions, and permission regressions.

**Target Implementation Plan:** `MONITORING_MODEL_PLAN_TRANSFER_PLAN.md`

---

## 1. Database Integrity & Ledger Constraints
*Objective: Verify that the database schema enforces the "One Plan at a Time" invariant and that the ledger is the source of truth.*

| Test ID | Test Scenario | Expected Outcome |
|:---:|:---|:---|
| **DB-01** | **Enforce One Active Plan**<br>Attempt to insert a second `monitoring_plan_memberships` row for Model `M` where `effective_to IS NULL` while one already exists. | **DB Error**: Constraint violation (Unique Partial Index on `model_id where effective_to is null`). |
| **DB-02** | **Effective Date Validity**<br>Attempt to insert a membership row where `effective_to < effective_from`. | **DB Error**: Check constraint violation. |
| **DB-03** | **Sync Consistency**<br>Use `MonitoringMembershipService` to add Model `M` to Plan `P`. | `monitoring_plan_models` (projection) MUST contain `(P, M)`. `monitoring_plan_memberships` MUST have active row for `(P, M)`. |
| **DB-04** | **Sync Cleanup**<br>Use `MonitoringMembershipService` to remove Model `M` from Plan `P`. | `monitoring_plan_models` MUST NOT contain `(P, M)`. Membership row MUST have `effective_to` populated. |

---

## 2. Transfer Operation Logic (API / Service)
*Objective: Verify the transfer state machine and boundary rules.*

| Test ID | Test Scenario | Expected Outcome |
|:---:|:---|:---|
| **TR-01** | **Standard Transfer**<br>Transfer Model `M` from Plan `A` → Plan `B`. | 1. Plan `A` membership closed (`effective_to` = now).<br>2. Plan `B` membership created (`effective_from` = now).<br>3. `monitoring_plan_models` updated (M removed from A, added to B).<br>4. Audit log entry created. |
| **TR-02** | **Blocked Transfer (Active Cycle)**<br>Plan `A` has a cycle in `DATA_COLLECTION`, `UNDER_REVIEW`, `PENDING_APPROVAL`, or `ON_HOLD`. Attempt to transfer Model `M` out of Plan `A`. | **400 Bad Request**. Transfer rejected. Error message cites active cycle. |
| **TR-03** | **Allowed Transfer (Pending Cycle)**<br>Plan `A` has a cycle in `PENDING` status. Attempt transfer. | **Success**. Transfer proceeds. (Pending cycles have not locked scope yet). |
| **TR-04** | **Allowed Transfer (Closed Cycle)**<br>Plan `A` has cycles in `APPROVED` or `CANCELLED`. Attempt transfer. | **Success**. Transfer proceeds. |
| **TR-05** | **Idempotency/No-op**<br>Attempt to transfer Model `M` to Plan `A` (its current plan). | **Success/No-op**. No new ledger rows created, or graceful handle. |
| **TR-06** | **Unmonitored Transfer**<br>Attempt to transfer Model `M` which has NO active plan. | **Success** (behaving like an "Add to Plan"). |
| **TR-07** | **Authorization Enforcement**<br>Non-admin user (e.g., `test_user`) attempts to transfer Model `M`. | **403 Forbidden**. Only admins can execute transfers. |

---

## 3. Cycle Scope Immutability ("History Persistence")
*Objective: Crucial check. Verify that historical monitoring data remains attached to the model despite plan changes.*

| Test ID | Test Scenario | Expected Outcome |
|:---:|:---|:---|
| **HIST-01** | **Scope Materialization**<br>Start a cycle (transition `PENDING` → `DATA_COLLECTION`). | Verify `monitoring_cycle_model_scopes` is populated with all currently active members of the plan at that exact timestamp. |
| **HIST-02** | **History Survival (The "Transfer" Test)**<br>1. Model `M` in Plan `A`.<br>2. Start Cycle `C1` (Plan `A`).<br>3. **Transfer** Model `M` to Plan `B`.<br>4. Fetch details for Cycle `C1`. | Cycle `C1` MUST still list Model `M` as in-scope.<br>Results for Model `M` in Cycle `C1` must still be accessible. |
| **HIST-03** | **New Cycle Respects Transfer**<br>After step 3 above, Start Cycle `C2` (Plan `A`). | Cycle `C2` MUST NOT include Model `M`. |
| **HIST-04** | **Destination Plan Scope**<br>Start Cycle `C3` (Plan `B`). | Cycle `C3` MUST include Model `M`. |
| **HIST-05** | **Legacy Fallback: Version Snapshots**<br>Create cycle `C_old` with `plan_version_id` set but NO `monitoring_cycle_model_scopes` rows. Fetch scope. | Scope resolved from `monitoring_plan_model_snapshots` for that version. |
| **HIST-06** | **Legacy Fallback: Results Inference**<br>Create cycle `C_legacy` with results but NO scope rows and NO `plan_version_id`. Fetch scope. | Scope inferred from distinct `monitoring_results.model_id` for that cycle. |
| **HIST-07** | **Legacy Fallback: Current Membership**<br>Create cycle `C_empty` with NO scope, NO version, NO results. Fetch scope. | Scope falls back to current active memberships (last resort). |

---

## 4. Regression: Impacted Dependencies
*Objective: Verify that downstream consumers use the new "Scope" logic instead of "Current Membership".*

| Test ID | Code Path / Feature | Test Procedure | Pass Criteria |
|:---:|:---|:---|:---|
| **REG-01** | **Dashboard / News Feed** | 1. Create `MonitoringResult` for Model `M` in Cycle `C1` (Plan `A`) with `alert_triggered=true` or `narrative` populated.<br>2. Ensure result is visible in `GET /news-feed` before transfer.<br>3. Transfer `M` to Plan `B`.<br>4. Re-query `GET /news-feed`. | The alert/result for `C1` must still appear in the feed. (Failure mode: It disappears because query joined current `plan_models`). |
| **REG-02** | **Model Activity Timeline** | 1. Complete Cycle `C1` (Plan `A`) with Model `M` in scope (status `APPROVED`).<br>2. Create audit log entry for cycle completion (or rely on existing status change logs).<br>3. Transfer `M` to Plan `B`.<br>4. Query Model `M` activity timeline (check endpoint response or audit logs). | Cycle `C1` completion event must be visible in timeline. |
| **REG-03** | **KPI Reporting** | 1. Start and complete Cycle `C1` with Model `M` in Plan `A` during "Last Month" date range.<br>2. Run KPI report for "Last Month" (snapshot count of monitored models).<br>3. Transfer `M` to Plan `B` today.<br>4. Rerun KPI report for the same "Last Month" period. | Numbers must match. Historical count of "Monitored Models" in previous month should rely on historical scope/cycles, not current membership. |
| **REG-04** | **Overlay Validation** | 1. Create a finding/exception entity and link it to Cycle `C1` / Model `M` (via validation endpoint or direct DB setup).<br>2. Validate linkage succeeds (e.g., `GET /model-overlays` returns the finding for the cycle).<br>3. Transfer `M` to Plan `B`.<br>4. Re-validate linkage (re-query the same endpoint). | Validation passes. The system recognizes `M` was part of `C1` scope and the finding remains linked. |

---

## 5. Permissions & RLS (Access Control)
*Objective: Ensure users don't lose access to their own model's history.*

| Test ID | Test Scenario | Expected Outcome |
|:---:|:---|:---|
| **PERM-01** | **Cross-Plan History Access**<br>User `U` has access to Model `M`, but **not** Plan `A` or Plan `B` generally.<br>Model `M` was in Plan `A` during Cycle `C1`.<br>Model `M` is now in Plan `B`. | User `U` CAN view Cycle `C1` details.<br>*Logic:* Access is granted because `M` (accessible) is in `scope(C1)`. |
| **PERM-02** | **Negative Access**<br>User `U` has NO access to Model `Y`. Model `Y` was in Cycle `C1`. | User `U` CANNOT see data specific to Model `Y` in Cycle `C1`. |

---

## 6. Concurrency & Locking (Race Conditions)
*Objective: Verify deadlock safety and atomicity defined in the Architecture plan.*

| Test ID | Test Scenario | Expected Outcome |
|:---:|:---|:---|
| **CONC-01** | **Transfer vs. Cycle Start**<br>Process 1: Starts Cycle for Plan `A` (locks Plan `A`).<br>Process 2: Transfers Model `M` from Plan `A` to `B` (needs lock on Plan `A`). | Operations must serialize (one waits for other).<br>Result must be consistent:<br>- If Cycle starts first, `M` is in scope. Transfer queues.<br>- If Transfer happens first, `M` is NOT in scope. Cycle starts.<br>**NO Deadlocks.** |

---

## Recommended Test Implementation Locations

1.  **Backend Unit/Integration**: `api/tests/test_monitoring_plan_membership_and_scope.py`
    *   *Cover sections 1, 2, 3.*
    *   **Critical:** Mark DB-01 and CONC-01 with `@pytest.mark.postgres` and use `postgres_db_session` fixture.
    *   DB-01 partial unique index won't fire in SQLite; CONC-01 locking semantics differ in SQLite.
2.  **Regression/Dependencies**:
    *   `api/tests/test_dashboard_commentary.py` (or check `test_dashboard.py` if exists) — REG-01
    *   `api/tests/test_models.py` (Timeline checks) — REG-02
    *   `api/tests/test_kpi_report.py` — REG-03
    *   `api/tests/test_model_overlays.py` — REG-04
    *   `api/tests/test_rls_endpoints.py` (Section 5 — Permissions)

---

## 7. Seeded Data & Test Fixture Requirements
*Objective: Summary of data required to execute the test suite.*

### Standard Pytest Fixtures (Available in `api/tests/conftest.py`)
*   `db_session` / `postgres_db_session`: Provides an isolated database sandbox.
*   `test_user` / `auth_headers`: Authenticated regular user context.
*   `validator_user` / `validator_headers`: Authenticated validator context (if needed by endpoint permission checks).
*   `admin_user` / `admin_headers`: Authenticated Admin user context (required for Transfer & Plan Management).
*   `sample_model`: A clean Model entity ready for plan assignment.

### Database Engine Requirements (Critical)
*   **Postgres-only assertions**:
    *   DB-01 (partial unique index: “one active membership per model”) requires Postgres to be meaningful.
    *   CONC-01 requires Postgres to exercise `SELECT ... FOR UPDATE` and deadlock/serialization behavior.
*   **SQLite caveat** (`db_session`): in-memory SQLite will not reliably enforce Postgres partial indexes and may not reproduce row-lock semantics.

### Test-Specific Helper Data (To be created in setup)
*   **Plan A ("Source Plan")**: `MonitoringPlan` with active status.
    *   *Frequency*: Quarterly or Monthly.
*   **Plan B ("Destination Plan")**: `MonitoringPlan` with active status.
*   **Initial Membership**: `sample_model` must be assigned to Plan A via `MonitoringMembershipService` (ensuring Ledger + Projection are in sync).

### Required for Cycle Start / Scope Materialization
*   **Published Plan Version**: `POST /monitoring/cycles/{cycle_id}/start` requires an active published `MonitoringPlanVersion` for the cycle’s plan.
    *   Seed at least one `MonitoringPlanVersion` with `is_active=True` for Plan A (and Plan B if you start cycles there).

### Setup for Permissions/RLS Tests
*   **User A (Owner)**: A user with `read` access to `sample_model` (via RLS/Ownership).
*   **User B (Stranger)**: A user with **NO** access to `sample_model`.
*   **Historical Cycle**: A cycle under Plan A that has been closed (Status: `APPROVED` or `CANCELLED`) containing `sample_model`.

### Setup for Transfer Blockers
*   **Blocking Cycle**: A cycle under Plan A with status `DATA_COLLECTION`.
*   **Non-Blocking Cycle**: A cycle under Plan A with status `PENDING`.

### Setup for Legacy Fallback Tests (HIST-05, HIST-06, HIST-07)
*   **HIST-05**: Create a cycle with `plan_version_id` populated AND `monitoring_plan_model_snapshots` rows for that version, but **deliberately omit** `monitoring_cycle_model_scopes` rows.
*   **HIST-06**: Create a cycle with `plan_version_id=NULL`, NO scope rows, but WITH `monitoring_results` rows containing `model_id` values.
*   **HIST-07**: Create a cycle with NO scope, NO version, NO results—only the plan's current active memberships exist.

### Setup for Regression Tests (Section 4)
*   **REG-01 (News Feed)**: Insert `MonitoringResult` with `alert_triggered=true` or a populated `narrative` field. Verify the feed endpoint includes these before transfer.
*   **REG-02 (Timeline)**: Create audit log entries for cycle status transitions (e.g., `PENDING → DATA_COLLECTION → APPROVED`). These should appear in the model's activity timeline.
*   **REG-03 (KPI Report)**: Ensure at least one historical cycle exists with `period_start_date` in the "Last Month" window. Query the KPI endpoint and verify it counts that cycle's models.
*   **REG-04 (Overlay Validation)**: Create a finding/exception record linked to `cycle_id` and `model_id`. Verify the linkage query (e.g., via model overlays endpoint or validation checks).


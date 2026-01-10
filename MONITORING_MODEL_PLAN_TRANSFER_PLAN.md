# Monitoring Plan Membership Ledger + Immutable Cycle Scope (One Plan per Model) — Implementation Plan

## Executive Summary
This plan introduces two small, durable primitives to make monitoring-plan membership changes (including transfers) safe and auditable without breaking historical monitoring views:

1) a **membership ledger** that records plan assignment over time (who/when/why) and enforces “one active plan per model”, and
2) an **immutable cycle model scope** that records which models were in scope for each monitoring cycle, so history never depends on current membership.

The plan is intentionally incremental: it layers these primitives onto the existing schema and then refactors the highest-risk endpoints to stop joining historical activity through current membership.

---

## Background (Current System)
The current monitoring subsystem already persists a lot of durable history:

- Monitoring cycles live in `monitoring_cycles` and can be bound to a plan version via `monitoring_cycles.plan_version_id` (nullable).
- Plan versions live in `monitoring_plan_versions`.
- Plan version snapshots exist for:
  - metrics: `monitoring_plan_metric_snapshots`
  - models: `monitoring_plan_model_snapshots`
- Monitoring results live in `monitoring_results` and are keyed by `cycle_id`, `plan_metric_id`, and optional `model_id`.

However, “which models are in a plan” is currently represented primarily as a current-state junction table:

- `monitoring_plan_models` (and ORM access via `MonitoringPlan.models`)

Several endpoints and validations still derive historical monitoring participation by joining through this current-state membership (or by reading `cycle.plan.models`). That approach is fragile: when a model is removed from Plan A and later added to Plan B, any historical query that depends on “current membership” can lose visibility into prior cycles.

---

## Why This Plan (What’s Missing)
The system has plan version snapshots, but snapshots alone don’t fully solve transfers and audit requirements in a minimal way:

- `monitoring_plan_model_snapshots` capture “models in scope at version publish time”, not “who moved this model, when, and why”.
- `plan_version_id` is nullable, and some code paths still fall back to live plan models when `plan_version_id` is not set.
- Even when snapshots exist, historical endpoints must be disciplined about not joining via `monitoring_plan_models`.

This plan adds the missing primitives to make history robust:

- a membership ledger for audit + correctness + “one plan at a time”, and
- an immutable cycle scope table so cycle history cannot disappear after a membership change.

---

## Design Constraints (Compatibility)
To integrate safely with the current codebase:

- We keep `monitoring_plan_models` in phase 1 to avoid breaking existing current-state UI flows.
- We do not change the `monitoring_results` keying (still uses `cycle_id`, `plan_metric_id`, optional `model_id`).
- We keep plan versioning/snapshots in place and treat them as complementary to cycle scope.
- We assume transfers affect future cycles only (boundary-safe); historical cycles/results remain immutable.

Additional non-functional constraints (critical):

- **No silent drift:** it must be hard (ideally impossible) for `monitoring_plan_models` and the membership ledger to diverge.
- **No history permission regressions:** users who can view a model (via RLS) must not lose access to historical monitoring cycles/results for that model simply because the model’s *current* plan membership changed.
- **No race gaps during cycle start:** cycle scope materialization must be transactionally consistent with membership at the moment the cycle is started.

This plan replaces the prior “transfer via current membership” approach with a design that:

1) records **auditable plan membership over time**, and
2) ensures **monitoring cycle scope is immutable**, so historical monitoring never disappears after transfers.

It is written to integrate cleanly with the current codebase, which already has:

- `monitoring_plan_models` (current-state membership)
- monitoring plan versioning (`monitoring_plan_versions`) and snapshots (`monitoring_plan_model_snapshots`, `monitoring_plan_metric_snapshots`)
- `monitoring_cycles.plan_version_id` (nullable)
- monitoring results keyed by `cycle_id`, `plan_metric_id`, optional `model_id` (`monitoring_results`)

---

## Problem
Today, several endpoints derive “which models a cycle applies to” by joining through **current plan membership** (`monitoring_plan_models`) or `cycle.plan.models`. When a model is moved between plans, those queries can lose historical context.

Separately, we need an auditable way to express:

- **when** a model was assigned to which plan
- **who/why** the change occurred
- and a first-class “transfer” operation that does not rewrite history

---

## Goals
- **One plan at a time:** a model can be in at most one monitoring plan concurrently.
- **Preserve history:** completed monitoring cycles/results must remain discoverable after transfers.
- **Audit-friendly:** record who/when/why for membership changes and transfers.
- **Minimal disruption:** integrate with existing monitoring plan versions/snapshots and current endpoints.

---

## Non‑Goals (initial scope)
- No mid-cycle splitting or retroactive editing of historical cycles/results.
- No automatic “scheduled transfer” engine (can be a future enhancement).
- No removal of existing tables in phase 1 (we keep compatibility and migrate incrementally).

---

## Core Design (Two Sources of Truth, With Clear Precedence)

### 1) Membership ledger (auditable, time-bounded)
Introduce a membership history table that is the authoritative record of *plan assignment over time*.

### 2) Cycle model scope (immutable)
Introduce a cycle scope table that is the authoritative record of *which models were in scope for a specific monitoring cycle*.

### Precedence rules (must be enforced across the API)
1. For cycle history: **use cycle scope first** (immutable).
2. For current plan membership UI: use `monitoring_plan_models` as a projection/cache of the active ledger row.
3. `monitoring_plan_model_snapshots` remains useful for **plan version history UI** and as **backfill support**, but cycle membership queries should not depend on “current membership”.

---

## Data Model Changes

### A) New table: `monitoring_plan_memberships`
Time-bounded membership rows.

Recommended columns:
- `membership_id` (PK)
- `model_id` (FK → `models.model_id`, indexed)
- `plan_id` (FK → `monitoring_plans.plan_id`, indexed)
- `effective_from` (DATE or TIMESTAMP; recommended TIMESTAMP using UTC)
- `effective_from` (TIMESTAMP; recommended UTC)
- `effective_to` (nullable; NULL = active)
- `reason` (TEXT, nullable)
- `changed_by_user_id` (FK → `users.user_id`, nullable for backfills)
- `created_at` / `updated_at`

Constraints / invariants:
- `effective_to IS NULL OR effective_to >= effective_from`
- **One active plan per model**:
  - Postgres partial unique index: `UNIQUE (model_id) WHERE effective_to IS NULL`
- Optional (nice-to-have): prevent duplicate open membership to the same plan:
  - `UNIQUE (plan_id, model_id) WHERE effective_to IS NULL`

### B) New table: `monitoring_cycle_model_scopes`
Immutable cycle scope rows.

Recommended columns:
- `cycle_id` (FK → `monitoring_cycles.cycle_id`, indexed)
- `model_id` (FK → `models.model_id`, indexed)
- `model_name` (VARCHAR, snapshot at lock time; optional but useful)
- `locked_at` (DATETIME, copied from cycle lock timestamp)
- `scope_source` (VARCHAR, required; one of: `membership_ledger`, `version_snapshot`, `results_inference`, `current_membership_inference`, `unknown`)
- `source_details` (JSON, nullable; store small provenance e.g. `{"plan_version_id": 123}` or `{"inferred_at": "..."}`)

Constraints:
- `UNIQUE (cycle_id, model_id)`

Rationale:
- The existing system snapshots metrics via `plan_version_id → monitoring_plan_metric_snapshots`.
- The missing piece is a cycle-level model scope source that is stable even when a model moves plans later.

---

## Migration & Backfill Strategy (Safe for Existing Data)

### Step 1: Create the two new tables + indexes
No behavior change yet.

### Step 2: Backfill memberships from `monitoring_plan_models`
For each row `(plan_id, model_id)` in `monitoring_plan_models`, insert a membership row:
- `effective_from = NOW()` (or `CURRENT_DATE` if using DATE)
- `effective_to = NULL`
- `changed_by_user_id = NULL`
- `reason = 'Backfilled from monitoring_plan_models'`

Note: This does not recover older membership history; it establishes a correct baseline.

### Step 3: Backfill cycle model scopes for historical cycles
Backfill priority:
1. If `monitoring_cycles.plan_version_id` is set: use `monitoring_plan_model_snapshots(version_id = plan_version_id)` as the source.
2. Else (legacy/missing version): use the best available approximation:
   - If the plan currently has only one model, scope that model.
   - Else, scope the distinct set of `monitoring_results.model_id` for that cycle (ignoring NULL model_id).

Critical edge case: cycles with **aggregate-only** results

- `monitoring_results.model_id` is nullable. Some cycles may have only plan-level/aggregate results (all NULL model_id).
- For such cycles (no `plan_version_id` and no model IDs in results), backfill must **not** silently create an empty scope.

Required behavior:
- If we cannot infer a non-empty scope from version snapshots or results, fall back to one of:
  - `current_membership_inference`: populate scope from the plan’s current membership **but mark `scope_source` accordingly**, OR
  - `unknown`: populate no scope rows but explicitly record a cycle-level warning/flag (requires an additional cycle flag column or an out-of-band audit log entry).

Rationale: an “empty scope” is often more misleading than an explicitly “inferred/unknown” scope.

This backfill is best-effort for cycles with missing `plan_version_id`; it is still better than “history disappears after transfer”.

---

## Backend Behavior Changes

### A) Cycle lock must materialize model scope
When a cycle transitions into a status where scope is considered locked (existing system already locks `plan_version_id` at DATA_COLLECTION start):

1. Ensure `cycle.plan_version_id` is set (existing behavior)
2. Insert rows into `monitoring_cycle_model_scopes` for the models in scope at that moment.

Source of models in scope at lock time (recommended):
- Use `monitoring_plan_memberships` where `effective_to IS NULL` and `plan_id == cycle.plan_id`.

Concurrency requirement (must implement):

- The cycle start / lock transaction must prevent a concurrent transfer from changing membership mid-snapshot.
- The current code already uses `SELECT ... FOR UPDATE` when selecting the active plan version during `POST /monitoring/cycles/{cycle_id}/start`.
- Extend this to also lock the relevant membership state during scope materialization.

Concrete locking guidance (SQLAlchemy / Postgres):

1) Lock the plan row (serializes membership mutations and cycle starts for the same plan):
- `db.query(MonitoringPlan).filter(MonitoringPlan.plan_id == cycle.plan_id).with_for_update().one()`

2) Lock the plan’s active memberships before computing scope:
- `db.query(MonitoringPlanMembership).filter(MonitoringPlanMembership.plan_id == cycle.plan_id, MonitoringPlanMembership.effective_to.is_(None)).with_for_update().all()`

3) Compute scope from the locked membership rows, then insert `monitoring_cycle_model_scopes`.

Deadlock avoidance rule (must follow everywhere):

- Always acquire locks in this order:
  1) `monitoring_plans` row(s) (ascending by plan_id if more than one)
  2) membership row(s) for specific models (ascending by model_id)
  3) other rows (cycle/version/etc)

This ensures transfers (two plans) and cycle starts (one plan) cannot deadlock under load.

This ensures scope is an atomic snapshot tied to `version_locked_at`.

This ensures cycle scope aligns with “one plan at a time” and does not depend on the plan’s later membership changes.

### B) Centralize membership/scope resolution helpers
Create a small helper module (example: `api/app/core/monitoring_scope.py`) used by:

- Dashboard feed
- Model activity timeline
- KPI reports
- CSV import validation
- Overlay validation checks

Rules:
- For cycle → models: prefer `monitoring_cycle_model_scopes`.
- If missing (older cycles): fall back to `plan_version_id → monitoring_plan_model_snapshots`.
- If both missing: fall back to best-effort as in the backfill logic.

Important: these helpers must also be usable by access-control checks (see Permissions/RLS below), otherwise “history visible in lists” can still fail when a user clicks through to a cycle detail.

### C) Membership mutations must write ledger + projection
Anywhere that currently mutates `MonitoringPlan.models` / `monitoring_plan_models` must be updated so history cannot be bypassed.

Critical requirement (must implement): single-writer service

- The codebase today directly assigns `plan.models = models` (e.g. `PATCH /monitoring/plans/{plan_id}`), which would bypass the ledger unless carefully rewritten.
- To avoid drift, introduce a single “membership writer” service (example: `MonitoringMembershipService`) and mandate:
  - All membership changes (add/remove/replace/transfer) go through that service.
  - The service performs the ledger write + projection update in the same DB transaction.
  - Direct writes to `plan.models` are prohibited outside that service.

If this discipline cannot be reliably enforced, consider a database-level safeguard (e.g., triggers) as a follow-up, but start with a service + tests.

- Adding a model to a plan:
- Adding a model to a plan (one-plan-at-a-time semantics):
  - Close the model’s existing active membership (if any) and open the new membership row.
  - Update `monitoring_plan_models` so the plan UI remains correct.
- Removing a model from a plan:
- Removing a model from a plan:
  - Close the active membership row.
  - Remove from `monitoring_plan_models`.

This keeps `monitoring_plan_models` as an always-correct projection of the ledger.

Additional safety tests (required):

- A regression test that executes the existing plan update endpoint(s) that set `plan.models = ...` and asserts membership ledger is updated accordingly.
- A regression test that attempts to violate “one active plan per model” and expects a DB error.

---

## Permissions / RLS (Must Not Regress History)

Verified risk in current code:

- Plan visibility for non-admin/non-validator users can depend on `plan.models` intersecting with the user’s accessible models.
- Cycle visibility delegates to plan visibility (`_can_view_cycle → _can_view_plan`) in multiple paths.
- If a model is transferred away from a plan, `plan.models` no longer includes that model, and users who could previously view a cycle (because they could view the model) may lose access to the cycle detail.

Required mitigation:

- Update cycle view authorization to allow access if the user can access **any model in the cycle scope**.
  - i.e., for non-admin users, authorize viewing a cycle if `accessible_model_ids ∩ cycle_scope_model_ids` is non-empty.
- Avoid using current plan membership as the sole determinant for cycle history access.

Acceptance criteria:

- A user with RLS access to a model can still view historical cycles/results for that model even after the model transfers to a different plan.

---

## Transfer Operation (One Plan at a Time)

### API: `POST /models/{model_id}/monitoring-plan-transfer`
Request:
- `to_plan_id`
- `reason`

Behavior (single transaction):
1. Identify current active membership row for the model (`effective_to IS NULL`).
2. Enforce boundary rule (minimal safe version):
  - Allow transfer only if the source plan has **no cycles in an in-progress state**.
  - Based on current `MonitoringCycleStatusEnum`, treat these statuses as “in progress / transfer-blocking”:
    - `DATA_COLLECTION`, `UNDER_REVIEW`, `PENDING_APPROVAL`, `ON_HOLD`
  - Transfers are allowed when the only cycles are:
    - `PENDING` (not started yet)
    - `APPROVED` / `CANCELLED` (closed)

  Rationale: cycle start locks version at `PENDING → DATA_COLLECTION`, and results submission/editing occurs in `DATA_COLLECTION`/`UNDER_REVIEW`.

3. Acquire deadlock-safe locks (must use consistent ordering):
  - Lock both plan rows (`monitoring_plans`) in ascending plan_id order (source and destination).
  - Lock the model’s active membership row using `SELECT ... FOR UPDATE`.
  - If transfer is initiated via a plan update endpoint that replaces many models at once, lock affected memberships in ascending model_id order.
3. Close current membership (`effective_to = NOW()`)
4. Open new membership (`plan_id = to_plan_id`, `effective_from = NOW()`, `effective_to = NULL`)
5. Update `monitoring_plan_models`:
   - remove from source plan
   - add to destination plan
6. Emit an audit log entry with from/to/reason

### Why transfers won’t break history
- Historical cycles are retrieved via cycle scope, not current membership.
- Cycle scope is materialized at lock time and immutable.

---

## Impacted Code Paths (Known Hotspots)

These currently rely on current membership and should be refactored to use cycle scope helpers:

- Dashboard monitoring feed currently joins `monitoring_plan_models` for monitoring cycles and then reads `cycle.plan.models` for context.
- Model activity timeline joins `monitoring_plan_models` to locate monitoring cycles.
- KPI reporting queries monitored models via `monitoring_plan_models`.
- Overlay validation checks read `cycle.plan.models` to confirm a model is in a cycle.
- CSV import validation uses live plan models when `cycle.plan_version_id` is NULL.

The goal is not to remove all uses of `monitoring_plan_models`, but to limit it to “current scope” and never to determine historical participation.

---

## Refactor Map (Concrete Targets to Update First)

This section lists the specific places in the current codebase that rely on `monitoring_plan_models` or `cycle.plan.models` in ways that can cause historical monitoring activity to disappear after a transfer.

Rule of thumb for the refactor:
- If you are answering “which models were in scope for cycle X?” → use `monitoring_cycle_model_scopes` (fallback to version snapshots/backfill helper).
- If you are answering “what is the current plan for model X?” → use the active row in `monitoring_plan_memberships` (and/or `monitoring_plan_models` as the projection).

### A) Must update (history correctness)

1) `api/app/api/dashboard.py` — `GET /news-feed`
- Today: queries monitoring cycles by joining through `monitoring_plan_models`, then uses `cycle.plan.models` to compute model context.
- Change: fetch cycles independent of current membership, then compute “model context” by intersecting accessible model IDs with cycle scope (`monitoring_cycle_model_scopes`).

2) `api/app/api/models.py` — model activity timeline (monitoring portion)
- Today: joins `monitoring_plan_models` to find monitoring cycles for a model.
- Change: find cycles via `monitoring_cycle_model_scopes` (cycle_id where scope contains model_id) and/or via results for the model (if that’s the existing behavior). Do not join through current plan membership.

3) `api/app/api/kpi_report.py` — KPI queries relying on “monitored models”
- Today: pulls model IDs via `monitoring_plan_models` and uses that as the population.
- Change: define “currently monitored models” via active memberships (`monitoring_plan_memberships.effective_to IS NULL`).
- For “latest cycle/result per model”: do not require current membership; use cycle scope (or result linkage) to locate relevant cycles.

4) `api/app/api/model_overlays.py` — `_validate_monitoring_cycle` and related membership checks
- Today: checks membership using `cycle.plan.models`.
- Change: validate that `(cycle_id, model_id)` exists in `monitoring_cycle_model_scopes` (fallback helper only for legacy cycles where scopes were not backfilled).

5) `api/app/api/monitoring.py` — CSV import/preview validation for results
- Today: if `cycle.plan_version_id` is NULL, it uses live `cycle.plan.models` to determine valid model IDs.
- Change: use `monitoring_cycle_model_scopes` regardless of `plan_version_id`; keep version snapshots for metric thresholds, but not model membership.

### B) Should update (consistency, but not strictly history)

6) `api/app/core/monitoring_plan_conflicts.py`
- Today: conflict detection likely uses `monitoring_plan_models`.
- Change: treat conflicts as “current membership conflicts” and compute from active memberships (same semantics, more reliable). This prevents drift if `monitoring_plan_models` ever becomes a derived table.

7) `api/app/api/my_portfolio.py`
- Today: likely uses `monitoring_plan_models` for “my monitored models” style queries.
- Change: use active membership ledger for current-state membership; keep `monitoring_plan_models` as a projection only if needed for performance.

### C) Should remain (current-state UX)

8) Plan management endpoints/UI that show “models currently in plan”
- Keep using `monitoring_plan_models` (or switch to active memberships) but enforce that all mutations write the ledger and keep the projection in sync.

---

## TDD Plan (Red → Green → Refactor)

### Phase 1 — Backend tests (Red)
Create: `api/tests/test_monitoring_plan_membership_and_scope.py`.

Add tests for:

1) **One plan at a time**
- Attempt to create two open membership rows for the same model fails (DB constraint).

2) **Transfer updates ledger + projection**
- Transfer closes old membership, opens new membership, updates `monitoring_plan_models`.

3) **Cycle scope materialization**
- When a cycle is locked/advanced into data collection, `monitoring_cycle_model_scopes` is created from active membership.

Add concurrency test coverage:

- Two transactions: one starts a cycle while another attempts a transfer; verify the transfer blocks or fails safely and scope is consistent.

Add explicit status tests:

- Transfer allowed when the only cycle status is `PENDING`.
- Transfer rejected when any cycle exists in `DATA_COLLECTION`, `UNDER_REVIEW`, `PENDING_APPROVAL`, or `ON_HOLD`.

4) **History does not disappear after transfer**
- Create a cycle under Plan A, lock scope, then transfer model to Plan B.
- Historical queries (timeline/feed/KPI) still return the Plan A cycle for that model.

5) **Permissions do not regress after transfer**
- A non-admin user with RLS access to the model can still open the historical cycle detail endpoint after transfer.

### Phase 2 — Backend implementation (Green)
Implement:

1) Alembic migration: create tables + indexes, backfill memberships, backfill cycle scopes.
2) Core helper(s) for cycle scope resolution.
3) Update monitoring cycle lock path to materialize cycle scope.
4) Update plan membership mutation endpoints to write ledger + update projection.
5) Implement transfer endpoint.

### Phase 3 — Frontend tests (Red)
Target existing monitoring UIs where membership changes happen:

- Transfer action (authorized users only), requires destination plan + reason.
- Model monitoring view shows current plan and membership history.

### Phase 4 — Frontend implementation (Green)
- Add API client methods for membership history + transfer.
- Minimal UI integration (no extra dashboards/pages beyond what’s needed).

---

## Rollout & Safety

### Incremental rollout
1) Ship schema + backfill + helpers (no UI changes) and refactor history queries to stop depending on current membership.
2) Ship transfer endpoint and update existing membership mutation flows to write the ledger.
3) Ship minimal transfer UI.

### Operational checks
- After deployment, validate:
  - every non-pending cycle has a populated model scope
  - membership ledger is consistent with `monitoring_plan_models`

---

## Appendix — Concrete Query Snippets (SQL + SQLAlchemy)

These are reference snippets to make the locking/validation rules unambiguous.

### A) Detect transfer-blocking cycles for a plan

SQL (Postgres):

```sql
-- Transfer is blocked if any cycle is in one of these statuses.
SELECT 1
FROM monitoring_cycles c
WHERE c.plan_id = :plan_id
  AND c.status IN ('DATA_COLLECTION', 'UNDER_REVIEW', 'PENDING_APPROVAL', 'ON_HOLD')
LIMIT 1;
```

SQLAlchemy:

```python
blocking = db.query(MonitoringCycle.cycle_id).filter(
    MonitoringCycle.plan_id == plan_id,
    MonitoringCycle.status.in_([
        MonitoringCycleStatus.DATA_COLLECTION.value,
        MonitoringCycleStatus.UNDER_REVIEW.value,
        MonitoringCycleStatus.PENDING_APPROVAL.value,
        MonitoringCycleStatus.ON_HOLD.value,
    ])
).first()
if blocking:
    raise HTTPException(status_code=400, detail="Transfer not allowed: plan has an active cycle")
```

### B) Cycle start: deadlock-safe locking + scope materialization

Lock ordering rule:
1) lock plan row
2) lock active memberships
3) lock active plan version (already done today)

SQL (conceptual):

```sql
-- 1) Serialize cycle start + membership changes for the plan
SELECT plan_id
FROM monitoring_plans
WHERE plan_id = :plan_id
FOR UPDATE;

-- 2) Lock the active membership rows for this plan (models in scope)
SELECT membership_id, model_id
FROM monitoring_plan_memberships
WHERE plan_id = :plan_id
  AND effective_to IS NULL
FOR UPDATE;
```

SQLAlchemy (conceptual):

```python
# Lock plan row first
db.query(MonitoringPlan).filter(MonitoringPlan.plan_id == cycle.plan_id).with_for_update().one()

# Lock active memberships next
memberships = db.query(MonitoringPlanMembership).filter(
    MonitoringPlanMembership.plan_id == cycle.plan_id,
    MonitoringPlanMembership.effective_to.is_(None)
).order_by(MonitoringPlanMembership.model_id.asc()).with_for_update().all()

# Then lock active version (this already exists in start_cycle)
active_version = db.query(MonitoringPlanVersion).filter(
    MonitoringPlanVersion.plan_id == cycle.plan_id,
    MonitoringPlanVersion.is_active.is_(True)
).with_for_update().first()

# Materialize scope
locked_at = utc_now()
for m in memberships:
    db.add(MonitoringCycleModelScope(
        cycle_id=cycle.cycle_id,
        model_id=m.model_id,
        locked_at=locked_at,
        scope_source="membership_ledger",
    ))
```

### C) Transfer: lock both plans + the model’s active membership

SQL (conceptual):

```sql
-- Lock both plan rows in ascending order to prevent deadlocks
SELECT plan_id FROM monitoring_plans
WHERE plan_id IN (:source_plan_id, :dest_plan_id)
ORDER BY plan_id
FOR UPDATE;

-- Lock the model's active membership row
SELECT membership_id, plan_id
FROM monitoring_plan_memberships
WHERE model_id = :model_id
  AND effective_to IS NULL
FOR UPDATE;
```

### D) Authorization: allow cycle view if user has access to any model in scope

SQL (conceptual):

```sql
-- If accessible_model_ids is a set/list computed by RLS,
-- allow if there exists any intersection with cycle scope.
SELECT 1
FROM monitoring_cycle_model_scopes s
WHERE s.cycle_id = :cycle_id
  AND s.model_id = ANY(:accessible_model_ids)
LIMIT 1;
```

---

## Documentation Updates (required)

Update:

1) `ARCHITECTURE.md`
- Document `monitoring_plan_memberships` and `monitoring_cycle_model_scopes`.
- State the invariant: one active plan per model.
- State precedence rules for history queries.

2) `docs/USER_GUIDE_PERFORMANCE_MONITORING.md`
- Add “Transferring a model between monitoring plans” with boundary rule and expectation that historical cycles remain visible.

---

## Future Enhancements (optional)
- Scheduled transfers (future-dated membership rows) that take effect at next cycle lock.
- Remove or fully derive `monitoring_plan_models` once all code paths read from the ledger.
- Add explicit cycle metric scope snapshots if needed (today plan version snapshots cover metrics well).

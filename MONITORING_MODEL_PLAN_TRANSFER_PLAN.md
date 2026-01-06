# Monitoring Plan Model Transfers (Preserve History) — Implementation Plan

## Problem
Today, a model’s inclusion in performance monitoring plans is effectively “current state” only (via `monitoring_plan_models`). If a model is removed from Plan A and added to Plan B, historical results remain in the database, but the product lacks a clean, auditable way to:
- represent **when** the model was in each plan,
- support a **transfer** UX (move from one plan to another),
- and still show **historical plan context** on the model’s monitoring view/reporting.

## Goals
- Allow moving a model from one monitoring plan to another while **preserving historical monitoring cycles/results**.
- Make membership changes **audit-friendly** (who/when/why).
- Keep the implementation **minimal** and compatible with existing monitoring cycles/version snapshots.

## Non‑Goals (initial scope)
- No retroactive rewriting of prior cycles, plan versions, or results.
- No mid-cycle “split cycle” logic; transfers should apply to **future cycles**.
- No complex scheduling engine (phase 1 can restrict transfers to safe boundaries).

---

## Proposed Clean/Simple Design
Introduce a **time-bounded model↔plan assignment history** that represents current + past membership.

### Key rule
**Transfers only affect future cycles.** Historical cycles/results stay bound to the original plan/cycle/version they were created under.

### Why this works
The monitoring subsystem already persists results by `cycle_id`/`plan_version_id` and model, so historical facts remain immutable. The missing piece is a first-class concept for “membership over time” to power UI and audit/reporting.

---

## Impact Assessment (Existing UI/Reports)
This change is safe only if we **don’t rely on current plan membership** (`monitoring_plan_models`) to fetch *historical* monitoring activity. A quick repo scan shows `monitoring_plan_models` is used in multiple places, and we’ll need to classify each usage:

### A) Usages that should remain “current membership”
These should continue to read from `monitoring_plan_models` (or “active assignments”) because they represent what’s currently in scope:
- Plan management UI and API: list models currently in a plan.
- Conflict detection (“a model can’t be in overlapping plan frequencies at the same time”).
- KPI-style “% of models monitored” metrics (current-state view).

### B) Usages that must not break historical views
Any endpoint/UI that builds **history** by joining cycles through `monitoring_plan_models` will lose history after a transfer (because the model is no longer in the old plan).

Known examples to fix:
- `api/app/api/models.py` (Model activity timeline) currently finds monitoring cycles for a model by joining `monitoring_cycles → monitoring_plans → monitoring_plan_models`.
- `api/app/api/dashboard.py` (Dashboard activity feed) currently finds monitoring cycles for accessible models by joining through `monitoring_plan_models`.
- `api/app/api/kpi_report.py` (KPI 4.11 “latest RED breach”) currently identifies “latest” cycles/results via current membership.

Fix approach (preferred):
- Derive model↔cycle participation from **cycle-locked snapshots**: `monitoring_cycles.plan_version_id → monitoring_plan_model_snapshots`.
- Fallback when `plan_version_id` is NULL: derive participation from the new assignments table (effective window overlaps cycle period), not from current membership.

### C) Mutation entrypoints that must be updated
If we introduce an assignments table but keep `monitoring_plan_models` for current state, any API path that mutates `plan.models` (e.g., `PATCH /monitoring/plans/{plan_id}`) must also create/close assignment rows; otherwise history can be bypassed and the two sources diverge.

### D) Frontend areas to review
- Model monitoring tab “Add to existing plan” flow (today it patches the plan’s model list).
- Monitoring plan management pages (model list, add/remove flows).
- Any dashboards/reports that show monitoring activity per model (ensure they use cycles/results, not current membership).

### E) Regression checklist (minimum)
- A model moved from Plan A → Plan B still shows Plan A cycles/results in:
  - Model activity timeline
  - Any model-level monitoring history views
- Plan A shows the model as removed (current membership).
- Plan B shows the model as present (current membership).
- KPI/dashboards based on “monitored models” remain stable (model is still monitored).

---

## Phase 0 — Decisions (confirm before coding)
1. **Transfer effective timing**
   - Recommended for simplicity: transfers are only allowed when the source plan has **no active cycle** (or only a `PENDING` cycle) so membership can be changed immediately and safely.
   - Later enhancement: allow “schedule transfer at next cycle start.”
2. **Multiplicity**
   - If business allows models in multiple plans, the history table should allow multiple concurrent assignments.
   - If business intends exactly one “primary” plan per model, add a constraint to allow only one active assignment per model.

---

## Phase 1 — Data Model

### A) New table: `monitoring_plan_model_assignments`
Purpose: record membership intervals with audit fields.

Suggested columns:
- `assignment_id` (PK)
- `plan_id` (FK → `monitoring_plans.plan_id`, required, indexed)
- `model_id` (FK → `models.model_id`, required, indexed)
- `effective_from` (date, required)
- `effective_to` (date, nullable)
- `change_reason` (text, nullable)
- `changed_by_user_id` (FK → `users.user_id`, nullable but preferred)
- `created_at`, `updated_at`

Suggested constraints/indexes:
- CHECK: `effective_to IS NULL OR effective_to >= effective_from`
- UNIQUE (partial): at most one open row per `(plan_id, model_id)` where `effective_to IS NULL`
- Optional UNIQUE (partial): at most one open row per `model_id` (only if “single active plan” is required)

### B) Relationship to existing `monitoring_plan_models`
Keep `monitoring_plan_models` as the **current-state association** to minimize disruption to existing code paths.

The assignments table becomes the source of truth for history; the join table remains a convenience for “currently in plan.”

---

## Phase 2 — Backend Behavior & API

### A) Backfill migration
On deploy:
- For each `(plan_id, model_id)` currently in `monitoring_plan_models`, insert an assignment row:
  - `effective_from = CURRENT_DATE` (or best-known proxy if available)
  - `effective_to = NULL`
  - `change_reason = 'backfill'`

### B) New endpoints (minimal)
1. `GET /models/{model_id}/monitoring-plan-assignments`
   - Returns current + historical assignments, ordered by `effective_from DESC`.

2. `POST /models/{model_id}/monitoring-plan-transfer`
   - Body:
     - `from_plan_id` (required)
     - `to_plan_id` (required)
     - `effective_from` (optional; default `CURRENT_DATE` or next safe boundary)
     - `reason` (required)
   - Behavior:
     - Validate permissions (likely Admin / Monitoring governance).
     - Validate model is currently in `from_plan_id` (present in `monitoring_plan_models` AND has open assignment).
     - Validate transfer boundary safety:
       - If the source plan has an active cycle beyond `PENDING`, return 400 with guidance (“transfer at next cycle boundary”).
     - Close current assignment for `(from_plan_id, model_id)` by setting `effective_to`.
     - Create new assignment row for `(to_plan_id, model_id)` with `effective_from` and `effective_to=NULL`.
     - Update `monitoring_plan_models`:
       - remove `(from_plan_id, model_id)`
       - add `(to_plan_id, model_id)`
     - Audit log entry capturing from/to/reason/effective date.

### C) Update existing model monitoring query
Current endpoint used by the Model Monitoring tab should include:
- **Current plans** from `monitoring_plan_models`
- **Historical plans** from assignments table (distinct plans with closed assignments)

This makes historical plans discoverable from the model page even after transfer.

### D) Retrofit “historical monitoring” endpoints to not depend on current membership
To avoid losing history after a transfer, update the following logic to map cycles to models using snapshots/assignments:

1. **Model activity timeline** (`api/app/api/models.py`)
   - Replace the `monitoring_plan_models` join with:
     - Primary path: join `MonitoringPlanModelSnapshot` via `MonitoringCycle.plan_version_id` and filter `snapshot.model_id == model_id`.
     - Fallback path (only if `plan_version_id` is NULL): join assignments where `assignment.model_id == model_id` and `assignment.plan_id == cycle.plan_id` and `assignment.effective_from/effective_to` overlaps `cycle.period_start_date..period_end_date`.

2. **Dashboard feed** (`api/app/api/dashboard.py`)
   - Replace “cycles for accessible models” selection with:
     - Primary: join `MonitoringPlanModelSnapshot` and filter `snapshot.model_id IN accessible_model_ids`; select distinct cycles ordered by `cycle.updated_at DESC`.
     - Fallback for `plan_version_id` NULL: use assignment overlap logic.
   - Build “model context” (1 model name vs “N models”) from snapshot model_ids intersected with `accessible_model_ids` (not `cycle.plan.models`, which represents current membership).

3. **KPI 4.11 (latest RED)** (`api/app/api/kpi_report.py`)
   - Ensure “latest cycle for a model” is derived from historical participation:
     - Primary: latest `MonitoringCycle` where snapshots include `model_id`.
     - Fallback: assignments overlap.
   - Keep existing business semantics initially (if needed), but avoid tying “latest” to current membership so transfers don’t temporarily hide RED breaches.
   - Note: current implementation effectively inspects a cycle’s results without filtering to the specific model; decide and document the intended per-model semantics as part of implementation.

---

## Phase 3 — Frontend UX

### A) Model Details → Monitoring tab
Add a “Transfer to another plan” action (authorized users only):
- Select destination plan (dropdown)
- Capture reason
- Submit to transfer endpoint

Display:
- Current plan(s)
- Past plan(s) (collapsed “History” section), derived from assignments

### B) Plan-side UX (optional)
On Monitoring Plan detail, add a “Remove model” action that:
- closes the open assignment
- removes from `monitoring_plan_models`
- does not affect historical cycles/results

---

## Phase 4 — Testing

Backend tests:
- Transfer disallowed if source plan has an active cycle beyond `PENDING`.
- Transfer creates/updates assignment rows correctly (close old, open new).
- Transfer updates `monitoring_plan_models` as expected.
- Model monitoring list includes historical plan after transfer.

Frontend tests:
- Transfer modal submits correct payload.
- After transfer, Monitoring tab reflects new current plan and shows old plan under history.

---

## Phase 5 — Future Enhancements (optional)
- Scheduled transfers: allow creating a future-dated assignment and applying `monitoring_plan_models` changes at cycle start.
- Stronger invariants: enforce “one active plan per model” if desired.
- Reporting: add “plan at time of cycle” derived from `cycle.plan_id` (immutable) and show assignment intervals for audit context.

---

## Rollout Notes
- Start with boundary-safe transfers only (simplest).
- Keep existing results immutable; never delete cycles/results on transfer.
- Add admin tooling to repair assignments if backfill needs correction.

# Monitoring Plan Frequency Overlap Rule Plan

Goal
- Prevent a model from being scoped to more than one monitoring plan with the same frequency.
- Return a clear, user-facing error message when a conflict blocks create/update.

Scope
- Backend enforcement only (API create/update of monitoring plans).
- Applies when:
  - Creating a plan with `model_ids`.
  - Updating a plan’s `model_ids`.
  - Updating a plan’s `frequency`.
  - Activating a plan (if `is_active` is set to true and conflicts exist).
- Open question to confirm: should inactive plans be ignored in conflict checks? (Default assumption below: only active plans are considered.)

Assumptions (confirm)
- Conflict checks only consider `MonitoringPlan.is_active == true`.
- A model can be included in multiple plans of different frequencies without restriction.

Implementation plan
1) Add a reusable conflict-check helper
   - Location: new `api/app/core/monitoring_plan_conflicts.py` (avoid API module coupling).
   - Inputs:
     - `model_ids: List[int]`
     - `frequency: str`
     - `exclude_plan_id: Optional[int] = None`
     - `active_only: bool = True` (default)
   - Query:
     - Join `monitoring_plan_models` + `MonitoringPlan`.
     - Filter by `model_id in model_ids` and `MonitoringPlan.frequency == frequency`.
     - If `active_only`, filter `MonitoringPlan.is_active == True`.
     - Exclude `MonitoringPlan.plan_id == exclude_plan_id`.
   - Output: per-model conflicts with `plan_id`, `plan_name`, `frequency`, `is_active`.

2) Enforce rule in create flow
   - File: `api/app/api/monitoring.py` (`create_monitoring_plan`).
   - After `plan_data` is validated and before inserting models:
     - If `plan_data.model_ids` is non-empty, call helper with `plan_data.frequency`.
     - If conflicts exist, raise HTTP 400 with a clear message.

3) Enforce rule in update flow
   - File: `api/app/api/monitoring.py` (`update_monitoring_plan`).
   - Determine candidate frequency and model_ids:
     - `new_frequency = update_data.frequency or plan.frequency`
     - `new_model_ids = update_data.model_ids or [m.model_id for m in plan.models]`
   - If `new_model_ids` non-empty and (models/frequency/is_active change):
     - Call helper with `exclude_plan_id=plan_id`.
     - If conflicts exist, raise HTTP 400 and do not update.
   - If `is_active` is being set to true, run the same check.

4) Error messaging
   - Provide a user-facing error string (not list/object) so UI displays it consistently.
   - Suggested format:
     - "Model <name> (ID <id>) already belongs to active monitoring plan(s) with frequency <Frequency>: #<plan_id> <plan_name>. A model can only be in one active monitoring plan per frequency."
   - For multiple models, concatenate with semicolons or newlines.
   - Include a stable phrase (e.g., "one active monitoring plan per frequency") so tests can assert it.

Test plan
- Add tests in `api/tests/test_monitoring.py`:
  1) Create plan A (Monthly) with model X.
  2) Create plan B (Monthly) with model X -> 400, message includes model ID and plan ID/name.
  3) Create plan C (Quarterly) with model X -> 201 (allowed).
  4) Update plan D (Monthly) to add model X -> 400.
  5) Update plan A frequency to Quarterly while model X is in plan C (Quarterly) -> 400.
  6) If `is_active` gating is used: update plan B to `is_active=true` with conflicting model -> 400.

Notes
- If the product requires conflicts against inactive plans too, drop the `is_active` filter.
- The monitoring plan association is many-to-many and cannot enforce this via a simple DB constraint; API-level validation is the practical enforcement point.

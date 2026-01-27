# RLS Enforcement Audit (P1)

**Date**: 2026-01-03  
**Last updated**: 2026-01-04 (overdue revalidation report + IRP RLS coverage)

## Scope
- Focus on endpoints that return model-scoped data to non-privileged users.
- RLS helpers: `apply_model_rls`, `apply_validation_request_rls`, `apply_exception_rls`,
  `can_access_model`, `can_access_validation_request`, `can_see_recommendation`.

## Inventory (Initial - Covered)

| Area | Endpoint | Handler | RLS enforcement | Notes |
| --- | --- | --- | --- | --- |
| Models | `GET /models/` | `api/app/api/models.py:list_models` | `apply_model_rls` | Filters list for basic users. |
| Models | `GET /models/{model_id}` | `api/app/api/models.py` | `can_access_model` | Detail access via model-level RLS. |
| Model Versions | Multiple `GET` | `api/app/api/model_versions.py` | `can_access_model` | Per-model access checks for lists/details. |
| Validation Requests | `GET /validation-workflow/requests/` | `api/app/api/validation_workflow.py:list_validation_requests` | `apply_validation_request_rls` | List filter via associated models. |
| Validation Requests | `GET /validation-workflow/requests/{request_id}` | `api/app/api/validation_workflow.py:get_validation_request` | `can_access_validation_request` | Detail access via associated models. |
| Exceptions | `GET /exceptions/` | `api/app/api/exceptions.py:list_exceptions` | `apply_exception_rls` | List filter via associated models. |
| Exceptions | `GET /exceptions/{exception_id}` | `api/app/api/exceptions.py` | `can_access_exception` | Detail access via associated models. |
| Recommendations | `GET /recommendations/` | `api/app/api/recommendations.py:list_recommendations` | Custom filter | Manual model/assignee filter; hides DRAFT. |
| Recommendations | `GET /recommendations/{recommendation_id}` | `api/app/api/recommendations.py:get_recommendation` | `can_see_recommendation` | Detail access check. |
| Dashboard | `GET /dashboard/news-feed` | `api/app/api/dashboard.py:get_news_feed` | `apply_model_rls` | Pulls accessible model IDs first. |
| Monitoring | `GET /monitoring/plans` | `api/app/api/monitoring.py:list_monitoring_plans` | Covered | Plan list filtered by plan access. |
| Monitoring | `GET /monitoring/plans/{plan_id}` | `api/app/api/monitoring.py:get_monitoring_plan` | Covered | Plan detail gated by plan access. |
| Monitoring | `GET /monitoring/plans/{plan_id}/cycles` | `api/app/api/monitoring.py:list_plan_cycles` | Covered | Plan access enforced before listing cycles. |
| Monitoring | `GET /monitoring/cycles/{cycle_id}` | `api/app/api/monitoring.py:get_monitoring_cycle` | Covered | Cycle access enforced (plan access or assignee). |
| Monitoring | `GET /monitoring/cycles/{cycle_id}/results` | `api/app/api/monitoring.py:list_cycle_results` | Covered | Cycle access enforced before results. |
| Monitoring | `GET /monitoring/cycles/{cycle_id}/approvals` | `api/app/api/monitoring.py:list_cycle_approvals` | Covered | Cycle access enforced (includes eligible approvers). |
| Monitoring | `GET /monitoring/cycles/{cycle_id}/report/pdf` | `api/app/api/monitoring.py:generate_cycle_report_pdf` | Covered | Cycle access enforced; unauthorized returns 404. |
| Attestations | `GET /attestations/records` | `api/app/api/attestations.py:list_records` | Role gate | Admin/Validator only; standard users use `/attestations/my-attestations`. |
| Attestations | `GET /attestations/records/{attestation_id}` | `api/app/api/attestations.py:get_record` | `can_attest_for_model` | Model-scoped access enforced for non-admins. |
| Decommissioning | `GET /decommissioning/` | `api/app/api/decommissioning.py:list_decommissioning_requests` | Covered | `apply_model_rls` applied to list. |
| Decommissioning | `GET /decommissioning/{request_id}` | `api/app/api/decommissioning.py:get_decommissioning_request` | Covered | Detail gated by `can_access_model`. |
| Teams | `GET /teams/{team_id}/models` | `api/app/api/teams.py:get_team_models` | Covered | Model list filtered by `apply_model_rls`. |
| IRP | `GET /irps/` | `api/app/api/irp.py:list_irps` | `apply_model_rls` | List limited to IRPs covering accessible MRSAs. |
| IRP | `GET /irps/{irp_id}` | `api/app/api/irp.py:get_irp` | `_require_irp_access` | Detail requires MRSA access; non-privileged users only see accessible MRSAs. |
| IRP | `GET /irps/coverage/check` | `api/app/api/irp.py:check_irp_coverage` | `apply_model_rls` | Coverage status limited to accessible MRSAs. |
| IRP | `GET /irps/mrsa-review-status` | `api/app/api/irp.py:get_mrsa_review_status` | `apply_model_rls` | Review status limited to accessible MRSAs. |
| Reports | `GET /overdue-revalidation-report/` | `api/app/api/overdue_revalidation_report.py:get_overdue_revalidation_report` | Admin-only | Report restricted to Admin role. |

## Pending Review (Next Pass)
- None (current inventory reviewed).

## Baseline Tests (Added)
- `api/tests/test_rls_endpoints.py`:
  - `GET /models/` filters out models not accessible to the caller.
  - `GET /exceptions/` filters out exceptions tied to inaccessible models.
  - `GET /validation-workflow/requests/` filters out requests for inaccessible models.
  - `GET /recommendations/` filters out recommendations tied to inaccessible models.
  - `GET /monitoring/plans` filters out plans not accessible to the caller.
  - `GET /monitoring/cycles/{cycle_id}` allows assignee access even without model access.
  - `GET /monitoring/cycles/{cycle_id}/approvals` returns 404 for unauthorized users; eligible approvers can view.
  - `GET /monitoring/cycles/{cycle_id}/report/pdf` returns 404 for unauthorized users; cycle viewers reach status validation.
  - `GET /decommissioning/` and `GET /decommissioning/{request_id}` enforce model access.
  - `GET /teams/{team_id}/models` enforces model access.
  - `GET /overdue-revalidation-report/` rejects non-admins.
  - `GET /irps/` filters IRPs by accessible MRSAs.
  - `GET /irps/{irp_id}` returns only accessible MRSAs for non-privileged users.

## Detailed Next Steps (For Audit)

### 1) Decide the monitoring read-access rules (required before code changes)
**Goal**: define who can view monitoring plans/cycles/results.

**Proposed rule (documented for review):**
- Admin/Validator: full access.
- Monitoring team members: can view plans/cycles/results for their team plans.
- Data provider: can view plans/cycles/results for plans where they are the data provider.
- Cycle assignee: can view cycles/results assigned to them.
- Model owners/delegates: can view plans/cycles/results for plans containing models they can access (via `can_access_model`).

**Decision points for reviewer:**
- Should global/regional approvers have read access here?
- Should assignee-only access include only the cycle detail/result endpoints, or also plan list?

**Deliverable**: short note in this file confirming the final rule set.

### 2) Implement monitoring read-access gating (after rule approval)
**Target files**: `api/app/api/monitoring.py`

**Approach:**
- Add helpers (local to `monitoring.py`) to check read access:
  - `can_view_plan(plan, user, db)` (team member/data provider/admin/validator + model access)
  - `can_view_cycle(cycle, user, db)` (plan access or assignee)
- Apply gating in:
  - `list_monitoring_plans` (filter or 403 if empty?)
  - `get_monitoring_plan`
  - `list_plan_cycles`
  - `get_monitoring_cycle`
  - `list_cycle_results`
- Ensure endpoints that already use edit permissions remain unchanged.

**Notes for reviewer**:
- Keep read-access logic separate from edit-access logic (`check_plan_edit_permission`, `check_cycle_edit_permission`).
- Avoid N+1: use joins to filter when possible (plan.team members, data_provider, cycles.assigned_to).

### 3) Fix decommissioning list/detail exposure
**Target files**: `api/app/api/decommissioning.py`

**Approach:**
- For `GET /decommissioning/`:
  - Join `Model` and apply `apply_model_rls`.
- For `GET /decommissioning/{request_id}`:
  - After fetch, enforce `can_access_model(request.model_id, current_user, db)` or return 404.
- Ensure validator/admin views remain unaffected.

**Decision**:
- Enforce `can_access_model` strictly. Do not grant access to creators once they no longer have model access.

### 4) Apply RLS to team model listings
**Target files**: `api/app/api/teams.py`

**Approach:**
- In `GET /teams/{team_id}/models`, apply `apply_model_rls` before building responses.
- Confirm that admins still see all team models.

### 5) Add regression tests (API-level)
**Target file**: `api/tests/test_rls_endpoints.py`

**New tests to add:**
- **Monitoring plans list**: non-member/non-provider user should not see plans; team member should.
- **Monitoring cycle detail/results**: non-access user should get 404/403; assignee or team member should.
- **Decommissioning list/detail**: non-owner user cannot see other model requests.
- **Team models**: ensure `/teams/{team_id}/models` hides models not accessible to caller.

**Fixtures/Data Setup**:
- Create monitoring team, plan, cycle, and assign data provider/assignee.
- Create decommissioning request for a model owned by a different user.
- Use existing `sample_model`, `second_user`, and taxonomy fixtures to avoid new dependencies.

### 6) Re-run targeted tests
Run `python3 -m pytest tests/test_rls_endpoints.py` and confirm new tests pass.

### 7) Update audit documentation
- Mark items in the inventory table as **Covered** once enforced.
- Record any deliberate exclusions (admin-only endpoints, UAT tools).

### 8) Align monitoring report/PDF + approvals with cycle read-access (implemented)
**Goal**: ensure “report-like” endpoints cannot bypass monitoring RLS, while allowing eligible approvers to see the context they’re approving.

**Audit findings (confirmed):**
- `list_cycle_approvals` has no access gate and leaks approval metadata to any authenticated user.
- `generate_cycle_report_pdf` uses a flawed approver check (`approver_id` is `None` for pending approvals), omits model owners/data providers/assignees, and returns 403 instead of 404.
- `_can_view_cycle` needs explicit “eligible approver” logic so read access works for pending approvals.
- Cycle CSV export is already guarded; trend/performance endpoints are plan-scoped and acceptable because the PDF includes its own trends.

**Policy to implement (for audit approval):**
- **Read access** to cycle-scoped resources must use the same gate as cycle detail/results:
  - Admin/Validator
  - Monitoring team members (for the plan’s team)
  - Plan data provider
  - Model owners/delegates for any model in the plan (via `can_access_model` / `apply_model_rls`)
  - Cycle assignee (assignee-only access remains cycle-scoped)
  - **Eligible approver**:
    - Global approver can view cycles with an active Global approval requirement, and cycles they previously approved/rejected (i.e., any `MonitoringCycleApproval` row with `approver_id == current_user.user_id`)
    - Regional approver can view cycles with an active Regional approval requirement for one of their regions, and cycles they previously approved/rejected (same `approver_id` rule)
- **Write access** (approve/reject/void) remains role-based and unchanged; the only change is ensuring approvers can also read the cycle/report they are asked to approve.
- Unauthorized reads should return **404** (not 403) to avoid leaking plan/cycle existence, consistent with other RLS-gated monitoring endpoints.

**Endpoints in scope:**
- `GET /monitoring/cycles/{cycle_id}/report/pdf` (`api/app/api/monitoring.py:generate_cycle_report_pdf`)
- `GET /monitoring/cycles/{cycle_id}/approvals` (`api/app/api/monitoring.py:list_cycle_approvals`)
- Confirm no change needed (already gated): cycle CSV export + trend/performance/version export endpoints.

**Implementation summary:**
1) **Update cycle view helper** in `api/app/api/monitoring.py`
   - Extend `_can_view_cycle(...)` to include “eligible approver” access (do **not** extend `_can_view_plan`).
   - Prefer a small helper like `_can_view_cycle_as_approver(db, cycle, user)` so the policy is explicit and testable.
   - Do not rely on `approval.approver_id == user_id` for *pending* approvals (it’s `None` until action); use approval type + region requirements to determine eligibility.
2) **Wire read endpoints to the unified gate**
   - `generate_cycle_report_pdf`: replace its custom `has_access` logic with `_require_cycle_view_access(...)` and return 404 on failure.
   - `list_cycle_approvals`: call `_require_cycle_view_access(...)` before returning approvals (currently leaks approval metadata to any authenticated user who guesses a `cycle_id`).
3) **Add minimal regression tests** in `api/tests/test_rls_endpoints.py`
   - Global approver can read cycle + approvals list for a cycle requiring Global approval (even without model access/team membership).
   - Regional approver can read cycle + approvals list for a cycle requiring Regional approval in one of their regions.
   - Non-privileged user with no access receives 404 for approvals list and PDF endpoint.
   - PDF test strategy: use a cycle status that triggers a fast 400 (“PDF only for PENDING_APPROVAL/APPROVED”) to validate the access gate without requiring full PDF generation.
4) **Audit trail update**
   - Inventory rows and baseline tests updated for approvals list + PDF report endpoints.

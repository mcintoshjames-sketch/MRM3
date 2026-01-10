# Validation Detail User Lookup Least-Privilege Plan

## Purpose
Resolve validation detail page failures for non-admin users (e.g., validators) while preserving least-privilege access to user directories. Provide narrow, task-specific user lists instead of full `/auth/users` access.

## Background & Issue Summary
- The validation detail page currently fetches `/auth/users` during initial load to populate:
  - “Add Validator Assignment” modal (validator/admin list)
  - “Create Recommendation” modal (assignee list)
- `/auth/users` is **admin-only**; non-admins receive **403**, causing the entire `Promise.all` fetch to fail.
- Result: the page renders “Validation Project Not Found” even when access to the validation request is allowed.
- This pattern appears in other user-facing pages, creating similar failure modes where a non-admin gets blocked by an admin-only user directory call.

## Security Principle
Adopt least-privilege by replacing broad user directory access with narrowly scoped, role-appropriate endpoints that return only the fields required by each UI task.

## Proposed Changes

### 1) Backend: Task-Specific User Endpoints
Introduce two dedicated endpoints with minimal response payloads:

1. **Assignable Validators**
   - **Endpoint**: `GET /validation-workflow/assignable-validators`
   - **Purpose**: Populate “Add Validator Assignment” modal.
   - **AuthZ**: `ADMIN` and `VALIDATOR` only.
   - **Response Fields**: `user_id`, `full_name`, `email`, `role_code`, `role_display`
   - **Filtering**: Only users with `role_code` in `['VALIDATOR', 'ADMIN']`

2. **Recommendation Assignees**
   - **Endpoint** (recommended): `GET /models/{model_id}/assignees`
   - **Purpose**: Populate “Assigned To” list in Recommendation Create modal for a specific model.
   - **AuthZ**: Users who can access the model (owner, developer, shared owner/developer, active delegate), plus admins/validators.
   - **Response Fields**: `user_id`, `full_name`, `email` (email is used by the UI search filter).
   - **Filtering**: Users with relationship to the model (owner/developer/delegates/shared) AND assigned validators.

3. **User Search (Fallback)**
   - **Endpoint**: `GET /users/search`
   - **Purpose**: Allow searching for specific users by email to assign recommendations to cross-functional stakeholders not in the default list.
   - **AuthZ**: Authenticated users.
   - **Parameters**: `email` (exact match or prefix).
   - **Response Fields**: `user_id`, `full_name`, `email`.

> Alternative (if model-specific filtering is not desired):  
> `GET /recommendations/assignees` restricted to `ADMIN`/`VALIDATOR` and filtered to active users in the same LOB/region.  
> This still avoids a full user directory dump.

### 2) Backend: Minimal Schemas
Add a small response schema (e.g., `AssignableUserResponse`) that excludes sensitive fields and only includes the fields listed above.

### 3) Frontend: Lazy User Fetch
Update `web/src/pages/ValidationRequestDetailPage.tsx`:
- Remove `/auth/users` from the initial `fetchData()` `Promise.all` (update destructuring to handle index shift).
- Fetch assignable validators only when the “Add Validator Assignment” modal opens, and store in a dedicated state (e.g., `assignableValidators`) used by that modal.
- Fetch assignees when the Recommendation Create modal opens and a model is selected.
- Add "Search by Email" functionality to the Recommendation modal for users not in the default list.
- Handle errors non-fatally (modal shows a message, main page still renders).

### 4) Frontend: Pass Model-Specific Assignees
Prefer to encapsulate assignee fetching inside `RecommendationCreateModal` so it can load on model change without the parent managing modal state.

## Why This Fix Preserves Least Privilege
- Avoids giving validators and standard users access to the entire user directory.
- Limits exposure to only the users needed for the current task.
- Keeps admin-only `/auth/users` intact for admin pages.

## Audit Findings & Mitigations
1. **Validator Assignment Dropdown Regression**
   - **Risk**: Removing `/auth/users` without updating the modal state source will leave the dropdown empty.
   - **Mitigation**: Introduce `assignableValidators` state and wire the dropdown to that list.
2. **Promise.all Destructuring Shift**
   - **Risk**: Removing one fetch changes indices and breaks subsequent assignments.
   - **Mitigation**: Update destructuring explicitly when `/auth/users` is removed.
3. **Recommendation Assignee Scope Regression**
   - **Risk**: Restricting assignees to model owners/developers/delegates may block valid cross-functional assignments.
   - **Mitigation**: Add a fallback search-by-email endpoint (single user lookup) or confirm requirements before restricting scope.
4. **Modal Fetching Responsibility**
   - **Risk**: Parent-managed assignee fetch adds complexity and state coupling.
   - **Mitigation**: Keep assignee fetching inside `RecommendationCreateModal` with model-change triggers.

## Implementation Steps
1. **Backend**
   - Add new schemas for minimal user payloads.
   - Implement `/validation-workflow/assignable-validators`.
   - Implement `/models/{model_id}/assignees`.
   - Implement `/users/search` (email fallback).
2. **Frontend**
   - Remove `/auth/users` from validation detail page initial load and update the `Promise.all` destructuring to avoid index shifts.
   - Add modal-driven fetch logic for assignable validators and wire the modal to use the new state (not the global `users` list).
   - Encapsulate recommendation assignee fetching inside `RecommendationCreateModal` (or update props to carry assignees + selected model state if parent-managed).
3. **Broader Remediation (Other Pages)**
   - Replace `/auth/users` on pages accessible to non-admins with scoped endpoints or lazy modal fetches:
     - `web/src/pages/ModelsPage.tsx`
     - `web/src/pages/ModelDetailsPage.tsx`
     - `web/src/pages/RecommendationsPage.tsx`
     - `web/src/pages/ValidationRequestDetailPage.tsx`
     - `web/src/pages/AuditPage.tsx`
     - `web/src/components/ModelRegionsSection.tsx`
   - For modal-only calls (non-fatal but still privileged), use scoped endpoints or fetch-on-open:
     - `web/src/components/ModelLimitationsTab.tsx`
     - `web/src/components/RecommendationEditModal.tsx`
     - `web/src/pages/RecommendationDetailPage.tsx`
     - `web/src/pages/MonitoringCycleDetailPage.tsx`
4. **Docs**
   - Update USER_GUIDE_MODEL_VALIDATION.md to mention assignee list is model-scoped (if implemented).

## Testing Plan
- **Backend**
  - Verify admin/validator access to `/validation-workflow/assignable-validators` (200).
  - Verify standard user access to the endpoint returns 403.
  - Verify model-scoped assignees endpoint enforces model access (404/403 when unauthorized).
- **Frontend**
  - Load validation detail page as validator (no 403 cascade).
  - Open “Add Assignment” modal and confirm list loads.
  - Open Recommendation modal and confirm assignee list loads for selected model.

## Audit Notes
- No database schema changes.
- No changes to RLS policies.
- Added endpoints are read-only with restricted output fields.

## Rollback Plan
- Revert frontend to previous `/auth/users` usage.
- Remove new endpoints and schema additions.
  - (This would reintroduce the 403 issue; rollback should be coordinated with a known admin-only usage path.)

## Answered Questions
1. Should recommendation assignees be limited to model owners/developers/delegates, or can any user be assigned? Recommendation assignees should be limited to model owners, developers, delegates, shared model owner, or shared model developer.
2. If assignee scope is restricted, should we allow a targeted search-by-email fallback to avoid functional regressions? Yes, you should implement the search-by-email fallback.
3. Should validator assignments allow only `VALIDATOR`, or also `ADMIN` (current behavior)? Current behavior is fine.
4. Should model-scoped assignee selection include the current primary validator for collaboration? Yes, include all assigned validators.

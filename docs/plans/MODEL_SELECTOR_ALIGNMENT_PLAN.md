# Model Selector Alignment Plan

Goal
- Align model selection UIs to a searchable experience that supports model name and model ID input, and displays IDs in results only (not in the collapsed selection).

Scope (targets to update)
- `web/src/pages/RecommendationsPage.tsx` (Model filter select)
- `web/src/components/monitoring/QualitativeStatusTimeline.tsx` (model filter select)
- `web/src/components/monitoring/CycleResultsPanel.tsx` (model selector select)
- `web/src/pages/ValidationWorkflowPage.tsx` (`MultiSelectDropdown` models list)
- `web/src/pages/MonitoringPlansPage.tsx` (`MultiSelectDropdown` models list)
- `web/src/components/ManageModelsModal.tsx` (add model search)
- `web/src/pages/DecommissioningRequestPage.tsx` (replacement model search)
- `web/src/pages/ExceptionsReportPage.tsx` (create exception model search)
- `web/src/pages/AttestationCyclesPage.tsx` (model override search)
- `web/src/components/ModelHierarchyModal.tsx` (search list)
- `web/src/components/ModelDependencyModal.tsx` (search list)
- `web/src/components/RecommendationCreateModal.tsx` (refactor to shared model search component)

Already aligned
- `web/src/pages/MonitoringPlanDetailPage.tsx` (Add Model modal already supports name/ID and shows ID)
- `web/src/components/RecommendationEditModal.tsx` (no model selector; Assigned To is searchable)

Proposed approach
- Create a reusable single-select model search component (input + dropdown) with:
  - filtering by `model_name` or `model_id`
  - dropdown results include `model_name` and `model_id`
  - collapsed value shows only `model_name` (no ID)
  - consistent empty/disabled states
  - configurable max results (default 50)
- Enhance `MultiSelectDropdown` to accept optional `searchKeys` or a `searchText` per option so model ID can be searched without changing visible labels.
- Replace plain `<select>` model pickers with the reusable component where feasible.

Execution plan
1) Add reusable model search component
   - New component file (e.g., `web/src/components/ModelSearchSelect.tsx`)
   - Props: `models`, `value`, `onChange`, `disabled`, `placeholder`, `showId`, `allowClear`
1.5) Dependency check (before altering labels)
   - Audit `MultiSelectDropdown` call sites for any logic that reads `option.label` for filters/sorts or submission payloads
   - Confirm any stored values are IDs, not labels (e.g., `model_id` / `model_ids`), and UI labels are presentation-only
2) Update single-select pickers
   - Replace `<select>`/name-only search in:
     - Recommendations filter (`RecommendationsPage.tsx`)
     - QualitativeStatusTimeline filter
     - CycleResultsPanel model select
     - ManageModelsModal add-model search
     - DecommissioningRequestPage replacement model
     - ExceptionsReportPage create-exception model
     - AttestationCyclesPage model override
     - ModelHierarchyModal / ModelDependencyModal
3) Update multi-select pickers
   - `ValidationWorkflowPage.tsx` and `MonitoringPlansPage.tsx` to allow search by ID
   - Preferred: extend `MultiSelectDropdown` to accept `searchText` so label can stay clean
   - Fallback (if safe): include `(ID: <id>)` in labels only after confirming no downstream dependency on label text
4) UX consistency pass
   - Ensure all dropdowns show model ID in results
   - Ensure collapsed selection remains name-only (no ID)
   - Match placeholder text and max-results behavior
5) Testing
   - Manual: verify search by ID works and selection persists
   - Unit (optional): add small UI test for `ModelSearchSelect`

Acceptance criteria
- Every model picker in scope supports search by model name and model ID.
- Search results show model IDs; collapsed selection does not show IDs.
- No regression in existing selection flows (single/multi select).

Notes / open questions
- If adding IDs to `MultiSelectDropdown` labels, confirm that downstream filters/sorts do not depend on label text.

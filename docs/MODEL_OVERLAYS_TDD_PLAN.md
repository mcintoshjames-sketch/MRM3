# TDD Implementation Plan: Model Overlays & Significant Management Judgements (Underperformance)

## Goal

Enable the organization to answer the regulatory question:

> “What model overlays or significant management judgements are currently in place due to model underperformance, if any?”

with a reliable, audit-friendly report of overlays/judgements that are **currently in effect**, explicitly marked as **underperformance-related**, and scoped to the **live operational model population** (i.e., exclude models that are not in use per Model Status).

## Non-Goals (to keep this minimal)

- No new approval workflow for applying/retiring overlays (recording only).
- No automatic creation of overlays from monitoring outcomes (user-entered record).
- No attempt to compute/validate quantitative “underperformance” beyond referencing existing monitoring results/outcomes.
- No changes to existing Exceptions/Recommendations detection logic beyond optional linking for traceability.

## Proposed Minimal Design (summary)

Create a small, model-scoped entity to record “overlay / management judgement” items that can be:
- **In effect** (not retired and within its effective date window), or
- **Retired** (historical; no longer in effect).

Each record can optionally reference monitoring artifacts (results/cycles) and other related items (recommendations/limitations) for traceability, but **underperformance classification must not depend on those links**.

### Data Model (new table)

**`model_overlays`**

Minimum fields:
- `overlay_id` (PK)
- `model_id` (FK → `models.model_id`, required)
- `overlay_kind` (enum-like string): `OVERLAY` | `MANAGEMENT_JUDGEMENT` (required)
- `is_underperformance_related` (bool; required; default `true`) (explicitly classifies the overlay for the regulatory question)
- `description` (text; what is applied; required)
- `rationale` (text; why it’s applied; required)
- `effective_from` (date; required)
- `effective_to` (date; nullable; optional; if set, the overlay is not “currently in effect” after this date even if not explicitly retired)
- `region_id` (FK → `regions.region_id`; nullable; NULL = global)
- `trigger_monitoring_result_id` (FK → `monitoring_results.result_id`; nullable)
- `trigger_monitoring_cycle_id` (FK → `monitoring_cycles.cycle_id`; nullable; convenience when result granularity is not available)
- `related_recommendation_id` (FK → `recommendations.recommendation_id`; nullable)
- `related_limitation_id` (FK → `model_limitations.limitation_id`; nullable)
- `evidence_url` (string; nullable) OR `evidence_description` (text; nullable) (pick one minimal evidence mechanism)
- retirement fields (align with `ModelLimitation` pattern): `is_retired` (bool), `retirement_date`, `retirement_reason`, `retired_by_id`
- audit fields: `created_by_id`, `created_at`, `updated_at`

Immutability (auditability):
- Treat `rationale` as **immutable after creation**. If justification changes materially, retire the old overlay and create a new one (UI can offer “Clone” for convenience).
- Prefer the same immutability pattern for `description`, `overlay_kind`, `is_underperformance_related`, `effective_from`, and `region_id` to reduce audit ambiguity. Allow only evidence/link fields to be updated.

Suggested minimal constraints:
- Add a database-level CHECK constraint matching the `ModelLimitation` pattern:
  - `(is_retired = FALSE AND retirement_date IS NULL AND retirement_reason IS NULL AND retired_by_id IS NULL) OR (is_retired = TRUE AND retirement_date IS NOT NULL AND retirement_reason IS NOT NULL AND retired_by_id IS NOT NULL)`
- If `trigger_monitoring_result_id` is set, it must belong to the same `model_id` (and same `region_id` if region-specific overlay is used).
- Optional: if `trigger_monitoring_cycle_id` is set, it must belong to a plan that includes the model (or be enforced at API-level if DB enforcement is too heavy).
- If `related_limitation_id` is set, it must belong to the same `model_id` (enforce at API-level; optional DB enforcement if simple).

### API Surface (minimal)

Model-scoped endpoints (mirrors `limitations` pattern):
- `GET /models/{model_id}/overlays` (list; default `include_retired=false`, filters: `region_id`, `overlay_kind`, `is_underperformance_related`)
- `POST /models/{model_id}/overlays` (create)
- `GET /overlays/{overlay_id}` (detail)
- `PATCH /overlays/{overlay_id}` (update **evidence/link fields only**; core fields like `rationale` are immutable)
- `POST /overlays/{overlay_id}/retire` (retire action with reason + date)

Audit logging (required for regulatory defensibility):
- Create an `AuditLog` entry for CREATE, evidence/link UPDATE, and RETIRE actions, capturing old/new values for changed fields (pattern: existing audit-log tests in `api/tests/test_authorization_audit.py`).

Report endpoint (for the regulatory question):
- `GET /reports/model-overlays` (returns overlays/judgements that are **currently in effect** and **underperformance-related** with filters: `region_id`, `team_id`, `risk_tier`, `overlay_kind`)
  - “Underperformance-related” is defined by `is_underperformance_related=true` (not by presence/absence of monitoring links).
  - “Currently in effect” is defined by: `is_retired=false` AND `effective_from <= today` AND (`effective_to IS NULL OR effective_to >= today`).
  - The report must join `models` and filter to “in use” model statuses (default: `Model.status == 'Active'`). Add an explicit query parameter to include `Pending Decommission` if business policy considers those still “in use”.
  - Include a boolean in the response like `has_monitoring_traceability` to show whether a monitoring result/cycle is linked (without excluding records).

### UI (minimal)

- **Model Inventory (Model Details)**: add a new tab or section “Overlays & Judgements” showing:
  - Currently in-effect overlays (default)
  - Toggle to include retired
  - Create/Edit/Retire actions for authorized roles
  - Display trigger links (Monitoring Cycle/Result, Recommendation) when provided
- **Reports**: add “Model Overlays” report page listing in-effect underperformance-related overlays with CSV export (pattern: Exceptions / Critical Limitations report pages).

### Authorization (proposed minimal)

Follow the existing “model-scoped access” conventions:
- View/list: anyone who can view the model (owner/developer/delegate/admin/validator per existing RLS approach).
- Create/update/retire: **Admin + Validator only** (restricted write access by default due to “Management Judgement” regulatory sensitivity).

## Acceptance Criteria

1. A user (Admin/Validator) can record an overlay/judgement on a model with description, immutable rationale, effective dates, an explicit underperformance flag, and optional monitoring/recommendation/limitation links.
2. A regulator-facing report can list all overlays/judgements that are currently in effect and underperformance-related, scoped to “in use” models by model status, and export them (including items without monitoring linkages).
3. Overlays can be retired with a reason, preserving history and audit trail; core fields cannot be “edited into a different judgement” in-place.
4. Docs are updated:
   - `ARCHITECTURE.md` documents the new subsystem.
   - Model Inventory user guide explains where overlays live and who maintains them.
   - Performance Monitoring user guide explains when/how to capture overlays for underperformance events.

---

## TDD Plan (Red → Green → Refactor)

### Phase 0: Spike decisions (no code yet)

Decide and write down (in the PR description / plan doc updates) the few choices that impact tests:
- Evidence: `evidence_url` vs `evidence_description` (or both).
- Region scoping: allow NULL (global) + optional region-specific overlays.
- Model lifecycle scoping for the regulatory report: default to `Model.status == Active`; decide whether to include `Pending Decommission` in “in use”.
- Whether to treat `description` as immutable like `rationale` (recommended), or allow typo-only edits with explicit audit logging.

### Phase 1: Backend — tests first

Create a new test module (example name): `api/tests/test_model_overlays.py`.

Write failing tests modeled after `api/tests/test_limitations.py` and `api/tests/test_exceptions.py`:

**1. List behavior**
- Lists empty for model with no overlays.
- Returns only non-retired overlays by default.
- `include_retired=true` returns both non-retired and retired overlays.
- Filters by `overlay_kind`, `region_id`, and `is_underperformance_related`.

**2. Create overlay**
- Validator/Admin can create overlay with required fields.
- Model owners cannot create overlays (403) under the restricted-write policy.
- Missing required fields returns 422/400 (depending on validation layer).
- If `trigger_monitoring_result_id` is provided, reject if it refers to a different model (and optionally mismatched region).
- If `related_limitation_id` is provided, reject if it refers to a limitation for a different model.

**3. Update overlay**
- Allowed to update **evidence/link fields only** on non-retired overlays (e.g., `evidence_url`/`evidence_description`, `trigger_*`, `related_*`).
- Attempting to update immutable fields (especially `rationale`) returns 400 and instructs user to retire + re-create.
- Attempting to update a retired overlay returns 400.
- Any allowed update creates an `audit_logs` entry with field-level old/new values.

**4. Retire overlay**
- Retire requires `retirement_reason` (min length), sets retirement fields (`is_retired=true`, `retirement_date`, `retired_by_id`), and preserves history.
- Retired overlays are excluded by default from list endpoints.
- Retire creates an `audit_logs` entry.

**5. Report endpoint**
- Returns overlays that are currently in effect (`effective_from`/`effective_to` window), non-retired, and `is_underperformance_related=true`.
- Joins `models` and filters to “in use” statuses for the regulatory view (default: `Active`; optionally include `Pending Decommission` based on Phase 0 decision).
- Does not require monitoring linkages to include an overlay; instead exposes linkage presence in the response for transparency.
- Filters: `region_id`, `team_id`, `risk_tier` behave consistently with other reports (verify response contains only matching models).

### Phase 2: Backend — make tests pass (minimal implementation)

Implement only what’s necessary to satisfy tests:

1. **SQLAlchemy model**
   - Add `api/app/models/model_overlay.py` (and export in `api/app/models/__init__.py`).
   - Add relationships to `Model`, `Region`, `MonitoringResult`, `MonitoringCycle`, `Recommendation`, `ModelLimitation`.

2. **Alembic migration**
   - New revision to create `model_overlays` table and indexes.
   - Add DB CHECK constraints for retirement-field consistency (copy `ModelLimitation` pattern) and allowed enum-like values where appropriate.

3. **Pydantic schemas**
   - Add `api/app/schemas/model_overlay.py` for list/detail/create/update/retire payloads.

4. **API routes**
   - Add `api/app/api/model_overlays.py` or extend `models.py` with clearly scoped routes.
   - Enforce Admin/Validator-only write operations; allow read access per model-scoped access rules.
   - Enforce “trigger must match model” at API level (simple join/lookup).
   - Add audit logging for CREATE / evidence-link UPDATE / RETIRE actions.

5. **Report route**
   - Add to existing reports router structure (or a small file `api/app/api/model_overlays_report.py`).
   - Keep response payload minimal but report-friendly: model name, overlay kind, region, effective dates, description, trigger pointers.

Refactor step (once green):
- Extract shared “model access” checks and filter helpers to match existing patterns (avoid duplicating RLS logic).

### Phase 3: Frontend — tests first (targeted)

Add UI tests (Vitest + RTL) focusing on the minimal flows:

1. **Model Details: Overlays & Judgements section**
- Renders “No overlays” empty state.
- Renders list of in-effect overlays.
- “Include retired” toggle changes list behavior (mock API response).
- “Add overlay” modal validates required fields before submit.

2. **Reports: Model Overlays**
- Renders table from API payload.
- Filters trigger refetch and change visible rows.

### Phase 4: Frontend — implement UI to pass tests

1. API client: `web/src/api/modelOverlays.ts` (pattern: `web/src/api/limitations.ts`, `web/src/api/exceptions.ts`).
2. Model Details integration:
   - Add new component `web/src/components/ModelOverlaysTab.tsx` (or section component).
   - Wire into `web/src/pages/ModelDetailsPage.tsx`.
3. Reports integration:
   - Add `ModelOverlaysReportPage.tsx` under `/reports`.
   - Link from Reports hub (`ReportsPage.tsx`) and route in `web/src/App.tsx`.

Refactor step:
- Reuse table/filter UI patterns from Exceptions/Critical Limitations pages to keep this small.

### Phase 5: Documentation updates (explicitly required)

1. **`ARCHITECTURE.md`**
   - Add a new section: “Model Overlays & Management Judgements”.
   - Document purpose, data model fields, endpoints, authorization, UI pages, and report endpoint.
   - Cross-reference related systems: Monitoring Results, Recommendations, Exceptions (UNMITIGATED_PERFORMANCE) for context.

2. **Model Inventory user guide**
   - Update `docs/USER_GUIDE_MODEL_INVENTORY.md` to include:
     - Where overlays/judgements are viewed on a model.
     - Who can create/retire them.
     - How to interpret global vs regional overlays (if implemented).

3. **Performance Monitoring user guide**
   - Update `docs/USER_GUIDE_PERFORMANCE_MONITORING.md` to include:
     - When an overlay/judgement should be recorded (e.g., after a cycle is approved and underperformance is confirmed).
     - How to link the overlay to the relevant monitoring result/cycle and any recommendation.
     - How this supports regulatory reporting.

### Phase 6: End-to-end sanity + regression

- Run API tests subset: `pytest api/tests/test_model_overlays.py` plus any impacted suites.
- Run frontend tests related to new components/pages.
- Quick manual workflow checklist:
  - Create an underperformance overlay (optionally with monitoring trigger) → appears in model tab and report.
  - Retire overlay → disappears from default lists, appears when “include retired” enabled.
  - Report filters behave as expected.

---

## Suggested File/Module Touch Points (implementation checklist)

Backend:
- `api/app/models/model_overlay.py` (new)
- `api/app/schemas/model_overlay.py` (new)
- `api/app/api/model_overlays.py` (new) and router registration in `api/app/main.py`
- `api/alembic/versions/*_add_model_overlays.py` (new)
- `api/tests/test_model_overlays.py` (new)

Frontend:
- `web/src/api/modelOverlays.ts` (new)
- `web/src/components/ModelOverlaysTab.tsx` (new)
- `web/src/pages/ModelOverlaysReportPage.tsx` (new)
- `web/src/App.tsx` + `web/src/pages/ReportsPage.tsx` (routing/navigation)

Docs:
- `ARCHITECTURE.md`
- `docs/USER_GUIDE_MODEL_INVENTORY.md`
- `docs/USER_GUIDE_PERFORMANCE_MONITORING.md`

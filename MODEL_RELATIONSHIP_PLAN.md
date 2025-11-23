# Model Relationship & Dependency Feature Plan

## Goals & Scope
- Represent model-to-model relationships for two purposes:
  1) Hierarchy: identify sub-models of a parent model; enable list/report filters to include/exclude sub-models.
  2) Dependencies: capture feeder → consumer model relationships with rich metadata about the downstream dependency and data flow.
     - Graph must be a DAG (no cycles); writes that introduce a cycle fail with a clear validation error listing the loop.
- Maintain a simple, 3NF-friendly schema that avoids wide “null forest” tables and keeps metadata extensible via taxonomy/config.
- Prepare for future lineage visualization (model chain map) and data-flow reporting without over-building now.

## Current State (baseline)
- Models are in `models` with owner/developer/vendor/regions and versions; no self-references today.
- No feeder/consumer linkage or hierarchy tables exist.
- Taxonomy system is available for configurable labels/codes.
- Audit logging exists and should be reused for relationship changes.

## Proposed Data Model (no DDL yet)
- **ModelHierarchy** (join table for parent/sub-models)
  - `id` PK
  - `parent_model_id` FK → models.model_id (ON DELETE CASCADE)
  - `child_model_id` FK → models.model_id (ON DELETE CASCADE)
  - `relation_type` (FK → taxonomy_values, taxonomy “Model Hierarchy Type”; initial value: SUB_MODEL)
  - `effective_date`, `end_date` (nullable) for temporal accuracy
  - `notes` (short free text)
  - Unique constraint on (parent_model_id, child_model_id, relation_type, effective_date NULLS FIRST) to prevent duplicates.
- **ModelFeedDependency** (join table for feeder/consumer dependencies; model-level edges only for now)
  - **Core (Phase 1, surfaced in UI):**
    - `id` PK
    - `feeder_model_id` FK → models.model_id (ON DELETE CASCADE)
    - `consumer_model_id` FK → models.model_id (ON DELETE CASCADE)
    - `dependency_type_id` FK → taxonomy_values (taxonomy “Model Dependency Type”; controlled vocab)
    - `description` short text (brief summary of the dependency)
    - `effective_date`, `end_date` (nullable)
    - `is_active` (bool, default true)
    - Unique constraint on (feeder_model_id, consumer_model_id, dependency_type_id) to prevent duplicate edges of the same type; multiple types per pair are allowed.
    - Validation: block self-links and any write that would introduce a cycle (detect and return a clear error with the loop path).
  - **Metadata extension (not exposed in UI yet):**
    - Separate table `model_dependency_metadata` (1:1 with dependency) with nullable fields: `feed_frequency_id`, `interface_type_id`, `criticality_id` (taxonomies), `data_fields_summary`, `data_contract_id` FK, plus optional `notes`.
    - Keeps core table lean while allowing richer governance data later.
- **Taxonomies to seed/configure**
  - Model Hierarchy Type: SUB_MODEL (room for future variants).
  - Model Dependency Type (used now): INPUT_DATA, SCORE, PARAMETER, GOVERNANCE_SIGNAL, OTHER.
  - (Future) Feed Frequency, Interface Type, Dependency Criticality (for metadata table) — can be seeded later.
- **Constraints/validations**
  - Prevent self-reference (parent ≠ child; feeder ≠ consumer).
  - **Single-parent rule**: A model can have at most ONE parent (enforced via unique constraint on child_model_id). Multiple children are allowed.
    - Rationale: Ensures clear ownership, accountability, and governance hierarchy. Prevents ambiguous approval chains and conflicting validation requirements.
    - If a model is used by multiple contexts, model this as a dependency (data flow), not hierarchy.
  - Optional guard to prevent cycles for hierarchy (e.g., child cannot ultimately be ancestor of parent); treat as future enhancement.
  - Effective/end date validation (end_date >= effective_date when both set).

## API Surface (planned, no implementation yet)
- **Hierarchy endpoints** (under `/models/{id}/hierarchy`):
  - List children (with optional `include_inactive`).
  - List parents for a given model.
  - Create/update/delete hierarchy link (Admin only).
- **Dependency endpoints** (under `/models/{id}/dependencies`):
  - List inbound (feeders) and outbound (consumers) with simplified fields (type, description, dates, active).
  - Create/update/delete dependency link with cycle detection on write; uniqueness on (feeder, consumer, dependency type); Admin (and optionally Validator) for updates.
- **Reporting/filters**
  - Model list/search: add filters `include_sub_models=true|false` and `has_feeders/has_consumers`.
  - Reports: support “expand hierarchy” toggle when summarizing counts/compliance.
- **Version awareness (future)**
  - Keep schema at model-level now; add optional version_id FKs later if we need version-specific dependencies.

## UI/UX Considerations
Model Details page:
  - New tabs/sections: “Hierarchy” (Parents/Sub-models) and “Dependencies” (Feeds In/Feeds Out).
  - Actions: Add link (modal/form) choosing model, dependency type (controlled vocab), brief description, effective/end dates, active toggle. Hide advanced metadata (frequency/interface/criticality) for now.
  - Table columns (Phase 1): Model name (link), dependency type, description, active/dated range, last updated.
  - Toggles for including sub-models in related views/reports.
- Reporting:
  - Add lineage preview (text/table first); map visualization deferred.
  - Export CSV for hierarchy/dependencies respecting filters.
- Validation messaging:
  - Prevent self-link on save.
  - Warn (but don’t block initially) on potential cycles; log for later enhancement.

## Audit, Security, and Governance
- Audit log on create/update/delete of hierarchy/dependency links (who, when, before/after values).
- Role gating: Admins, model owners/developers, and validators can modify links; read for authorized users consistent with existing model access rules.
- Respect existing RLS/access rules: only show related models a user can view.

## Migration Strategy (future implementation steps)
1) Create new tables `model_hierarchy` and `model_feed_dependencies` with constraints and indexes on FKs for join performance.
2) Seed new taxonomies (Dependency Type, Feed Frequency, Interface Type, Dependency Criticality, Model Hierarchy Type).
3) Backfill: none required initially; optional script to import known relationships later.

## Risks & Open Questions
- None remaining; open questions addressed (DAG enforcement, model-level granularity, controlled vocab with multiplicity, metadata path via 1:1 table, data contracts placeholder, access control set).

## Phased Delivery Plan (recommended)
1) **Schema + Taxonomy**: add tables, constraints, indexes; seed hierarchy + dependency type taxonomies (defer frequency/interface/criticality until needed).
2) **API CRUD**: backend endpoints with simplified dependency fields (type, description, dates, active) + validation (no self-link, uniqueness, cycle detection) + audit logging; unit tests.
3) **UI Read**: display hierarchy/dependencies on Model Details (read-only, simplified columns).
4) **UI Write**: add/create/update/delete flows with dependency type + description + dates; CSV exports; enforce DAG on write.
5) **Reporting**: filters/toggles for include-sub-models; basic dependency CSV.
6) **Lineage Preview**: simple chain rendering (text/table) using DAG-friendly data.
7) **Enhancements (future)**: expose metadata table fields (frequency, interface, criticality, data contract), optional version-level link table, map visualization.

---

## Implementation Progress

### ✅ Phase 1: Schema + Taxonomy (Completed 2025-11-23)

**Database Models:**
- Created `ModelHierarchy` table with parent-child relationships
  - Constraints: self-reference prevention, **unique constraint on child_model_id (single parent rule)**, unique constraint on (parent, child, type, effective_date), date range validation
  - Foreign keys: parent_model_id, child_model_id → models.model_id (CASCADE)
  - Fields: relation_type_id, effective_date, end_date, notes
- Created `ModelFeedDependency` table with feeder-consumer relationships
  - Constraints: self-reference prevention, unique constraint on (feeder, consumer, type), date range validation
  - Foreign keys: feeder_model_id, consumer_model_id → models.model_id (CASCADE)
  - Fields: dependency_type_id, description, effective_date, end_date, is_active
- Created `ModelDependencyMetadata` table (1:1 with dependency, not yet exposed in UI)
  - Fields: feed_frequency_id, interface_type_id, criticality_id, data_fields_summary, data_contract_id, notes

**Taxonomies Seeded:**
- Model Hierarchy Type: SUB_MODEL
- Model Dependency Type: INPUT_DATA, SCORE, PARAMETER, GOVERNANCE_SIGNAL, OTHER

**Migration:**
- File: `api/alembic/versions/3d1d60cd95d2_add_model_hierarchy_and_dependency_.py`
- Applied to database with all constraints and indexes

**Files:**
- `api/app/models/model_hierarchy.py`
- `api/app/models/model_feed_dependency.py`
- `api/app/models/model_dependency_metadata.py`
- Updated `api/app/models/model.py` with relationship properties
- Updated `api/app/models/__init__.py` with exports

---

### ✅ Phase 2: API CRUD (Completed 2025-11-23)

**API Endpoints - Hierarchy:**
- `GET /models/{id}/hierarchy/children` - List child models (with include_inactive param)
- `GET /models/{id}/hierarchy/parents` - List parent models
- `POST /models/{id}/hierarchy` - Create relationship (Admin only)
- `PATCH /hierarchy/{id}` - Update relationship (Admin only)
- `DELETE /hierarchy/{id}` - Delete relationship (Admin only)

**API Endpoints - Dependencies:**
- `GET /models/{id}/dependencies/inbound` - List feeder models
- `GET /models/{id}/dependencies/outbound` - List consumer models
- `POST /models/{id}/dependencies` - Create dependency with **cycle detection** (Admin only)
- `PATCH /dependencies/{id}` - Update dependency (Admin only)
- `DELETE /dependencies/{id}` - Delete dependency (Admin only)

**Cycle Detection:**
- DFS-based algorithm prevents circular dependencies
- Maintains DAG (Directed Acyclic Graph) constraint
- Returns detailed error with cycle path and model names
- Example: "A → B → C → A" detected and blocked with clear message

**Business Rules Enforced:**
- Self-reference prevention (parent ≠ child, feeder ≠ consumer)
- **Single-parent constraint**: Validates child doesn't already have an active parent before creating new hierarchy relationship
- Uniqueness constraints
- Date range validation (end_date >= effective_date)
- Admin-only access for modifications
- Full audit logging for all CREATE/UPDATE/DELETE operations

**Pydantic Schemas:**
- `api/app/schemas/model_relationships.py`
- Request schemas: Create, Update
- Response schemas: Full response, Summary
- Nested info schemas: ModelInfo, RelationTypeInfo, DependencyTypeInfo

**Testing:**
- `api/tests/test_model_hierarchy.py` - 26 tests (all passing)
- `api/tests/test_model_dependencies.py` - 26 tests (all passing)
- Coverage: CRUD operations, validation, access control, audit logging, cycle detection (5 comprehensive tests)

**Files:**
- `api/app/api/model_hierarchy.py`
- `api/app/api/model_dependencies.py`
- `api/app/schemas/model_relationships.py`
- Updated `api/app/main.py` with router registration

---

### ✅ Phase 3: UI Read (Completed 2025-11-23)

**Components Created:**
- `web/src/components/ModelHierarchySection.tsx`
  - Displays parent models table
  - Displays sub-models (children) table
  - Empty state when no relationships exist
  - Clickable links to related models
- `web/src/components/ModelDependenciesSection.tsx`
  - Displays inbound dependencies (feeders) table
  - Displays outbound dependencies (consumers) table
  - Active/inactive status badges
  - Dependency type badges with color coding
  - Clickable links to related models

**Model Details Page Integration:**
- Added "Hierarchy" tab to `web/src/pages/ModelDetailsPage.tsx`
- Added "Dependencies" tab to `web/src/pages/ModelDetailsPage.tsx`
- Both tabs fetch data from Phase 2 API endpoints
- Loading states and error handling
- Responsive design matching existing UI patterns

**Table Columns:**
- **Hierarchy**: Model Name, Relationship Type, Effective Date, End Date, Notes
- **Dependencies**: Model Name, Dependency Type, Description, Status, Effective Date

**Seed Data for UAT:**
- Created `api/seed_relationships.py` with example data:
  - Enterprise Credit Risk Model with 3 sub-models (PD, LGD, EAD)
  - Data lineage: Market Data Feed → Pricing Engine → Portfolio VaR Model
  - Stress Testing Model with multiple inbound dependencies
- 9 models, 3 hierarchy relationships, 6 dependencies created

**Files:**
- `web/src/components/ModelHierarchySection.tsx`
- `web/src/components/ModelDependenciesSection.tsx`
- Updated `web/src/pages/ModelDetailsPage.tsx`
- `api/seed_relationships.py`

**UAT Test Cases:**
- View Model #46 (Enterprise Credit Risk Model) - see 3 sub-models
- View Model #52 (Portfolio VaR Model) - see inbound from Pricing Engine, outbound to Stress Testing
- View Model #54 (Stress Testing Model) - see multiple inbound dependencies

---

### ✅ Phase 4: UI Write (Completed 2025-11-23)

**Components Created:**
- `web/src/components/ModelHierarchyModal.tsx`
  - Create/edit modal for hierarchy relationships
  - Parent or child relationship type selection
  - Model search with filtering
  - Relationship type dropdown (from taxonomy)
  - Effective/end date pickers with validation
  - Notes field (500 char limit)
  - Form validation (required fields, date range validation)
  - Error handling with user-friendly messages
- `web/src/components/ModelDependencyModal.tsx`
  - Create/edit modal for dependency relationships
  - Inbound (feeder) or outbound (consumer) direction
  - Model search with filtering
  - Dependency type dropdown (INPUT_DATA, SCORE, PARAMETER, GOVERNANCE_SIGNAL, OTHER)
  - Description field (500 char limit)
  - Effective/end date pickers with validation
  - Active/inactive checkbox
  - Cycle detection error display with detailed feedback
  - Form validation and error handling

**Section Updates:**
- Updated `web/src/components/ModelHierarchySection.tsx`
  - Add Parent/Add Sub-Model buttons (admin-only)
  - Edit/Delete actions per row (admin-only)
  - Modal integration for create/edit operations
  - Confirmation dialog for delete
  - Auto-refresh data after changes
  - Empty state now shows action buttons for admins
- Updated `web/src/components/ModelDependenciesSection.tsx`
  - Add Inbound/Add Outbound buttons (admin-only)
  - Edit/Delete actions per row (admin-only)
  - Modal integration for create/edit operations
  - Confirmation dialog for delete
  - Cycle detection feedback in UI
  - Auto-refresh data after changes
  - Empty state now shows action buttons for admins

**Page Integration:**
- Updated `web/src/pages/ModelDetailsPage.tsx`
  - Pass `modelName` prop to both hierarchy and dependencies sections
  - Required for modal display context

**Business Rules Enforced:**
- Admin-only access: All create/edit/delete buttons only visible to Admin role users
- Self-reference prevention: Cannot select current model in relationship forms
- Uniqueness: API enforces unique constraints on relationships
- Date validation: End date must be >= effective date
- Cycle detection: On dependency creation, API checks for circular dependencies and returns detailed error with cycle path
- Character limits: Notes/description fields limited to 500 characters with live counter

**User Experience:**
- Inline edit/delete buttons appear only for admins
- Modals overlay with backdrop, keyboard accessible (Esc to close)
- **Improved model search**: Type-ahead filtering with clickable list interface (replaced basic dropdown)
- **Enhanced autocomplete**: Results appear as you type, showing only matching models
- Visual selection feedback with highlighted selected item
- **Single-parent enforcement**: "Add Parent Model" button is disabled if model already has an active parent, with tooltip explaining the business rule
- Loading states during form submission
- Error messages displayed prominently in modal
- Confirmation dialogs prevent accidental deletions
- Success flows: modal closes, data refreshes automatically

**Bug Fixes (2025-11-23):**
- Fixed empty dropdown issue: Changed taxonomy lookup from non-existent `code` field to `name` field
  - Was: `t.code === 'MODEL_HIERARCHY_TYPE'` → Now: `t.name === 'Model Hierarchy Type'`
  - Was: `t.code === 'MODEL_DEPENDENCY_TYPE'` → Now: `t.name === 'Model Dependency Type'`
- Improved model selection UX: Replaced `<select size={5}>` with searchable list component
  - Type-ahead filtering with instant results
  - Clickable list items with hover states
  - Clear visual feedback for selected model
  - Better usability for large model inventories (100+ models)
- Added client-side validation for required fields before API submission
- **Fixed dropdown pre-population in edit mode**: API was returning summary schemas without ID fields
  - Updated `ModelHierarchySummary` to include `relation_type_id` and `notes`
  - Updated `ModelDependencySummary` to include `dependency_type_id`
  - Modified all 4 list endpoints to return these fields
  - Dropdowns now correctly pre-populate with current values when editing relationships

**Files Modified:**
- `web/src/components/ModelHierarchySection.tsx`
- `web/src/components/ModelDependenciesSection.tsx`
- `web/src/pages/ModelDetailsPage.tsx`

**Files Created:**
- `web/src/components/ModelHierarchyModal.tsx`
- `web/src/components/ModelDependencyModal.tsx`

**Testing Recommendations:**
1. **Hierarchy Write:**
   - Navigate to Model #46 (Enterprise Credit Risk Model) as Admin
   - Click "Add Sub-Model", select another model, save
   - Edit existing hierarchy relationship (change dates/notes)
   - Delete a hierarchy relationship
   - Verify non-admins see no action buttons

2. **Dependency Write:**
   - Navigate to Model #52 (Portfolio VaR Model) as Admin
   - Click "Add Inbound Dependency", select Market Data Feed, choose INPUT_DATA type
   - Try to create a circular dependency (e.g., A→B→C→A) and verify cycle error
   - Edit existing dependency (change type, toggle active status)
   - Delete a dependency relationship

3. **Validation:**
   - Try to create relationship without selecting model (should fail)
   - Try to set end date before effective date (should fail client-side)
   - Verify character counters work for notes/description

---

### ✅ Phase 5: Reporting (Completed 2025-11-23)

**CSV Export Functionality:**
- Added export buttons to `ModelHierarchySection` for parent and child relationships
- Added export buttons to `ModelDependenciesSection` for inbound and outbound dependencies
- Export includes all relevant fields: model names, types, dates, descriptions, status
- Filename format: `model_{model_id}_{type}_{YYYY-MM-DD}.csv`
- Export buttons appear alongside Add buttons in section headers

**Model List Filtering:**
- Added `include_sub_models` checkbox filter to `ModelsPage`
- Default behavior: Excludes sub-models from main model list (cleaner inventory view)
- When enabled: Shows all models including those that are children in hierarchy
- Filter integrates with existing multi-select filters (development type, status, owner, vendor, region)
- Backend API endpoint (`GET /models/`) supports `exclude_sub_models` parameter
- Automatically refetches data when filter changes

**API Endpoints for Advanced Reporting:**
- `GET /models/{id}/hierarchy/descendants` - Recursively fetch all descendants (children, grandchildren, etc.)
  - Returns flat list of all sub-models in the tree
  - Supports `include_inactive` parameter
  - Prevents infinite loops with cycle detection
  - Useful for "expand all sub-models" reporting feature
  
- `GET /models/{id}/dependencies/lineage` - Trace complete dependency chain for impact analysis
  - Parameters: `direction` (upstream/downstream/both), `max_depth`, `include_inactive`
  - Returns nested structure showing:
    - Upstream feeders (models that provide data to this model)
    - Downstream consumers (models that receive data from this model)
  - Each node includes: model_id, model_name, dependency_type, description, depth
  - Recursive traversal up to configurable max depth (default 10)
  - Enables lineage visualization and impact analysis

**Implementation Details:**
- Frontend: Added exportToCSV functions with proper CSV formatting (quoted fields)
- Frontend: `include_sub_models` state managed with useEffect for auto-refetch
- Backend: Efficient sub-model filtering using single query for hierarchy child IDs
- Backend: Recursive traversal with visited set to prevent cycles
- Backend: Leverages existing RLS (row-level security) for access control

**Files Modified:**
- `web/src/components/ModelHierarchySection.tsx` - CSV export buttons
- `web/src/components/ModelDependenciesSection.tsx` - CSV export buttons
- `web/src/pages/ModelsPage.tsx` - Include sub-models filter with backend integration
- `api/app/api/models.py` - Added exclude_sub_models parameter and filtering logic
- `api/app/api/model_hierarchy.py` - Added /descendants endpoint
- `api/app/api/model_dependencies.py` - Added /lineage endpoint

**Usage Examples:**
1. **CSV Export**: Click "Export CSV" button on any hierarchy/dependency section to download data
2. **Sub-Models Filter**: Toggle "Include Sub-Models" checkbox on Models page to show/hide children
3. **Hierarchy Expansion API**: `GET /models/46/hierarchy/descendants` - Get all sub-models under Enterprise Credit Risk Model
4. **Lineage API**: `GET /models/52/dependencies/lineage?direction=both` - See full data flow for Portfolio VaR Model

---

### ⏳ Phase 6: Lineage Preview (Planned)

**Planned Features:**
- Text/table rendering of dependency chains
- DAG traversal for upstream/downstream visualization
- Simple lineage viewer

**Not Yet Implemented**

---

### ⏳ Phase 7: Enhancements (Future)

**Planned Features:**
- Expose ModelDependencyMetadata fields in UI
- Version-level dependency links (optional)
- Interactive map visualization
- Advanced filters and search

**Not Yet Implemented**

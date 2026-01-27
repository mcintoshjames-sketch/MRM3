# Lineage Applications Direction Refactor Plan

## Goal
Enable the End-to-End Model Lineage PDF export to include related applications by storing whether each model-application relationship is upstream or downstream of the model. Update the Add Supporting Application modal and user guide(s) to capture and explain this direction.

## Current State (Summary)
- `model_applications` links models to MAP applications but does not store direction.
- Lineage export (`/models/{model_id}/dependencies/lineage/pdf`) only includes model-to-model dependencies.
- Supporting applications are managed in the Model Details > Relationships > Supporting Applications UI.

## Target State
- Each model-application relationship includes an explicit direction: upstream or downstream.
- Supporting Applications UI captures direction on create (and supports editing).
- Lineage PDF export appends applications in the correct direction.
- User guide(s) document how to classify direction for supporting applications.

## Proposed Data Model Changes
1. **Add direction column to `model_applications`.**
   - New column: `relationship_direction` (string enum).
   - Allowed values: `UPSTREAM`, `DOWNSTREAM`, `UNKNOWN`.
   - `UNKNOWN` is the default for ambiguous legacy relationships and should be excluded from lineage exports until remediated.
2. **Model + schema updates.**
   - `api/app/models/model_application.py`: add `relationship_direction`.
   - `api/app/schemas/model_application.py`: include `relationship_direction` in create/update/response schemas.

## Migration & Backfill Strategy
1. **Alembic migration:**
   - Add `relationship_direction` column (nullable initially, or default to `UNKNOWN`).
   - Add a check constraint for allowed values.
2. **Backfill:**
   - Map known relationship types:
     - `DATA_SOURCE` -> `UPSTREAM`
     - `OUTPUT_CONSUMER` -> `DOWNSTREAM`
     - `REPORTING` -> `DOWNSTREAM`
   - For ambiguous types (`EXECUTION`, `MONITORING`, `DATA_STORAGE`, `ORCHESTRATION`, `VALIDATION`, `OTHER`):
     - Set `UNKNOWN` and require manual update.
3. **Enforcement:**
   - Keep the column nullable or `UNKNOWN`-tolerant in the database to avoid breaking existing records.
   - Enforce a required direction for new/edited relationships at the API/UI layer.

## API Changes
1. **Create/update endpoints**
   - `POST /models/{model_id}/applications` accepts `relationship_direction`.
   - `PATCH /models/{model_id}/applications/{application_id}` allows changing `relationship_direction`.
2. **Response**
   - `ModelApplicationResponse` includes `relationship_direction`.
3. **Validation**
   - Validate direction is in allowed set.
4. **Lineage data**
   - Add related application nodes into lineage export flow.
   - Attach `upstream_applications` and `downstream_applications` arrays to **every model node** in the recursive lineage tree, not just the root.
   - Extend the lineage response shape (ad-hoc dict) to include these fields for each node so both the PDF generator and UI can access them.

## UI Changes (Supporting Applications)
1. **Add direction selector in modal**
   - Add a required field: "Direction" with `Upstream` / `Downstream`.
   - Provide help text: Upstream = provides inputs; Downstream = consumes outputs.
2. **Auto-suggest direction from relationship type**
   - When relationship type is `DATA_SOURCE` default to Upstream.
   - When relationship type is `OUTPUT_CONSUMER` or `REPORTING` default to Downstream.
   - Allow user override.
3. **Display direction in list**
   - Add a new column or badge for direction in the Supporting Applications table.
   - Show a warning badge or helper text when direction is `UNKNOWN` (e.g., "Missing Direction").
4. **Editing**
   - Add an Edit action (or inline control) to update direction for existing relationships.

## Lineage PDF Export Changes
1. **Include applications in path building**
   - Update path collection logic to treat application nodes as leaf nodes.
   - **Upstream paths:** if a model node has `upstream_applications`, each application becomes a start node for a path segment leading into the model chain.
   - **Downstream paths:** if a model node has `downstream_applications`, each application becomes a terminal node appended to the path segment leaving the model chain.
   - Exclude `UNKNOWN` direction applications from lineage paths to avoid misleading diagrams.
2. **PDF rendering**
   - Add support for application nodes with a distinct label (e.g., prefix "App:") and color.
   - Display relationship type (e.g., "Data Source", "Output Consumer") as the node type label.

## Documentation Updates
1. **USER_GUIDE_MODEL_INVENTORY.md**
   - Add a Supporting Applications subsection under Relationships.
   - Explain direction selection (upstream vs downstream) with examples.
   - Note impact on lineage/export reporting.
2. **Any other relevant guides**
   - If MRSA/IRP guide mentions downstream application relationships, align terminology.

## Tests
1. **Backend**
   - Update `api/tests/test_map_applications.py` to include direction in create/update.
   - Add validation tests for invalid direction values.
   - Add lineage export tests verifying recursive application attachment and path building.
2. **Frontend**
   - Add or update UI tests (if present) for the modal direction field and list display.

## Rollout & Verification
1. Run migration and verify existing relationships backfill correctly.
2. Create and edit a supporting application with direction.
3. Export lineage PDF and confirm applications appear in correct positions.

## Open Questions / Decisions Needed
- Which relationship types should default to upstream vs downstream beyond the explicit mappings above?
- Do we want to surface direction in the lineage UI (not just PDF) or keep it PDF-only for now?

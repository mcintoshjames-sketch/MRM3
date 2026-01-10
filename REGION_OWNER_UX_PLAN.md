# Region Owner UX Implementation Plan (Audited)

## Context & Objective
The system has two similarly-named concepts:

- **Global co-owner (region-agnostic)**: `models.shared_owner_id` (shown today as “Shared Owner (Co-Owner)” on the main model form)
- **Regional owner (per deployment region)**: `model_regions.shared_model_owner_id` (this is the field we want to expose as “Region Owner”)

Backend support for **per-region owner** already exists via the `model_regions` join table and dedicated endpoints.

However, the UI does not effectively expose this capability end-to-end:
1.  **Create Model**: Only allows selecting Region IDs. No ability to specify a regional owner during creation.
2.  **Edit Model**: Deployment regions are managed separately via a “Model Regions” section. It supports creating/removing regions but does not support editing existing region metadata (including owner) in-place.

Additionally, the current backend `PATCH /models/{id}` implementation updates `region_ids` by deleting all `ModelRegion` rows and recreating them, which would **wipe any existing per-region owner values**.

The objective is to implement a unified, optimal UX for managing Deployment Regions and their specific Regional Owners in both the "Create" and "Edit" workflows.

## Current Code Reality (Audit Notes)

This plan is written so a coding agent can execute it accurately in this repo.

### Existing backend APIs/schemas
- Model-region schema already exists: `api/app/schemas/model_region.py` (`ModelRegionCreate`, `ModelRegionUpdate`, `ModelRegion`).
- Model-region endpoints already exist: `api/app/api/model_regions.py`
    - `GET /models/{model_id}/regions` (returns `ModelRegion[]` including `shared_model_owner_id`)
    - `POST /models/{model_id}/regions` (creates a region row, supports `shared_model_owner_id`)
    - `PUT /model-regions/{id}` (updates `shared_model_owner_id`, etc.)
    - `DELETE /model-regions/{id}` (**Admin only**)

### Existing models endpoints behavior
- `POST /models` currently accepts `region_ids` (and auto-includes `wholly_owned_region_id`) and creates `ModelRegion` rows, but **does not set** `shared_model_owner_id`.
- `PATCH /models/{id}` currently accepts `region_ids` and implements it by deleting all existing `ModelRegion` rows for the model, then recreating them (thus losing per-region metadata like owner/notes/version_id).

## Recommendation Summary

Unify UX across Create and Edit:

- Keep a fast multi-select for choosing regions.
- Immediately below it, show per-region rows to optionally set “Region Owner” (and potentially other region metadata later).

Back-end strategy:

- **Preferred**: Extend `POST /models` and `PATCH /models/{id}` to accept a richer `model_regions` payload (list of `{region_id, shared_model_owner_id}`) and implement a safe “sync” that preserves metadata and updates owners.
- **Fallback**: If backend changes are undesirable, implement the create/update using the existing model-regions endpoints (`POST /models/{id}/regions` and `PUT /model-regions/{id}`), but be explicit about admin-only deletion and the current `PATCH /models/{id}` wiping behavior.

## UX & Component Architecture

### 1. New Reusable Component: `UserSearchSelect`
Refactor the existing “typeahead + dropdown + email lookup” user search logic (currently embedded in the Create Model form in `web/src/pages/ModelsPage.tsx`) into a reusable component to avoid duplication across per-region rows.

Notes:
- The current UX uses both a local assignees list and an email lookup (`GET /users/search?email=...`). The component should support the same behaviors.
- “Region Owner” should accept any valid user (not only those already in assignees), so keep the email lookup capability.

**Props:**
- `value`: `number | null` (Selected User ID)
- `onChange`: `(userId: number | null, userObject?: User) => void`
- `placeholder`: string
- `label`: string (optional)

### 2. New Component: `RegionOwnerConfigList`
A component that bridges the gap between bulk selection and specific configuration.

**Logic:**
- Takes a list of selected `Region` objects or IDs.
- Renders a row for each region.
- Each row contains:
    - Region Name (read-only)
    - `UserSearchSelect` for "Regional Owner"
    - "Remove" button (optional, to unselect the region)
- Includes an optional bulk action: "Apply selected owner to all regions".

Data contract recommendation (frontend-only):

```ts
type RegionOwnerConfig = {
    region_id: number;
    shared_model_owner_id: number | null;
};
```

## Implementation Steps

### Phase 1: Frontend Refactoring

#### 1. Extract User Search
- **Source**: `web/src/pages/ModelsPage.tsx`
- **Destination**: `web/src/components/UserSearchSelect.tsx`
- **Action**: Move the debounce logic, API call to `/users/search`, and dropdown rendering into the new component.

#### 2. Create Region Config Component
- **File**: `web/src/components/RegionOwnerConfigList.tsx`
- **Behavior**:
    - Display list based on `selectedRegionIds`.
    - Maintain internal state or bubble up state for `{ region_id: number, shared_model_owner_id: number | null }[]`.

### Phase 2: Create Model Workflow (`ModelsPage.tsx`)

#### 1. UI Update
- Keep `MultiSelectDropdown` for "Deployment Regions" (fast selection).
- **Add**: `RegionOwnerConfigList` immediately below it.
- **Interaction**:
    - When a user selects "US" and "EU" in the dropdown, the Config List shows two rows.
    - User can optionally assign "Jane Doe" to "UK".

#### 2. State Management
- Recommended approach: keep `region_ids: number[]` as the UI source-of-truth for the multi-select, and maintain a separate `region_owner_configs: RegionOwnerConfig[]` derived from it.
- When region_ids changes, add/remove config rows accordingly (preserving existing `shared_model_owner_id` values where possible).
- Ensure the wholly-owned region is always included (current UX copy already promises this).

#### 3. API Payload
- Update `handleSubmit` to send a rich `model_regions` structure (recommended) or to make follow-up API calls to set owners.

Important: backend `POST /models` currently only accepts `region_ids` (see `api/app/schemas/model.py`) and will create model-region rows without owners. If the agent chooses not to extend the backend, the Create flow must:

1) Create the model with `region_ids`
2) Fetch created model id from response
3) For each region with an owner, call `POST /models/{modelId}/regions` (but note: the region row may already exist from `POST /models`; so you may need a safer backend path or a `PUT` path to update existing rows)

This is why extending `POST /models` to accept `model_regions` is the cleanest.

### Phase 3: Edit Model Workflow (`ModelDetailsPage.tsx`)

#### 1. UI Integration
- **Move**: "Deployment Regions" from the sidebar/bottom section *into* the main "Edit Model" modal.
- **Replace**: The simple region logic with the `MultiSelectDropdown` + `RegionOwnerConfigList` combination used in Create.

#### 2. Data Pre-population
- When opening "Edit Model", fetch existing `model_regions` (including `shared_model_owner_id`).
- Populate the `RegionOwnerConfigList` with existing owners.

#### 3. API Interaction
- The `PATCH /models/{id}` endpoint MUST be adjusted if region owner is introduced.

Current risk:
- `PATCH /models/{id}` handling of `region_ids` deletes all `ModelRegion` rows and recreates them, which will wipe `shared_model_owner_id` and other region metadata.

Preferred backend approach:
- Add `model_regions: List[{region_id, shared_model_owner_id}]` to `ModelUpdate`.
- Implement a “sync without wipe”:
    - For each payload region_id:
        - If row exists, update `shared_model_owner_id` if changed.
        - If not exists, insert.
    - For deletions:
        - Decide policy: either allow owners to remove regions via `PATCH /models/{id}` sync, or preserve admin-only deletion semantics.

If you keep admin-only deletion for `DELETE /model-regions/{id}`, then the Edit UI should either:
- Hide “remove region” for non-admins, OR
- Allow removal via `PATCH /models/{id}` (which already effectively does deletion today), and reconcile the permission inconsistency later.

### Phase 4: Backend Updates

#### 1. Pydantic Schemas (`api/app/schemas/model.py`)
- Update `ModelCreate` to accept `model_regions`: `List[ModelRegionCreatePayload]` (optional), while keeping `region_ids` for backward compatibility.
- Define `ModelRegionCreatePayload`:
    ```python
    class ModelRegionCreatePayload(BaseModel):
        region_id: int
        shared_model_owner_id: Optional[int] = None
    ```

Also update `ModelUpdate` similarly.

#### 2. Endpoint Logic (`api/app/api/endpoints/models.py`)
- File is `api/app/api/models.py` in this repo.
- **`POST /models`**: If `model_regions` is present, use it as the source of truth (plus auto-include wholly-owned region). Create `ModelRegion` rows with `shared_model_owner_id`.
- **`PATCH /models/{id}`**:
    - Detect if `model_regions` is present in update data.
    - If present, perform a "Sync":
        1. Identify regions to remove (present in DB but not in payload).
        2. Identify regions to add (present in payload but not in DB).
        3. Identify regions to update (present in both, check if `shared_model_owner_id` changed).

Important: if `region_ids` is still supported, it should be implemented via the same sync logic (NOT delete+recreate), otherwise region owner values will be lost.

## Files Involved
1.  `web/src/components/UserSearchSelect.tsx` (New)
2.  `web/src/components/RegionOwnerConfigList.tsx` (New)
3.  `web/src/pages/ModelsPage.tsx` (Create Form)
4.  `web/src/pages/ModelDetailsPage.tsx` (Edit Form)
5.  `api/app/schemas/model.py` (Request Schema)
6.  `api/app/api/models.py` (Controller Logic)
7.  `api/app/api/model_regions.py` (Existing endpoints; may remain unchanged if models endpoints are extended)

## Considerations
- **Backward Compatibility**: Ensure the default `region_ids` approach still works if the rich payload is optional, OR strictly cut over to the new payload format.
- **Validation**: Ensure `shared_model_owner_id` refers to a valid user.

## Acceptance Criteria (for the coding agent)

- Create Model form:
    - Selecting deployment regions shows per-region “Region Owner (Optional)” rows.
    - Submitting can create region owners in the backend without manual follow-up edits.
- Edit Model form:
    - Existing region owners are displayed and can be edited in place.
    - Updating model metadata does not wipe existing regional owner values.
- Permissions:
    - Non-admin behavior is explicitly defined for “remove region” (either disabled, or supported via `PATCH /models/{id}` sync).


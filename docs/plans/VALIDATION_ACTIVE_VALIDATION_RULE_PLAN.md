# Active Validation Overlap Rule Plan

Goal
- Enforce active validation overlap rules:
  - Active = any status not in APPROVED/CANCELLED.
  - A model may participate in any number of TARGETED validations.
  - A model may participate in at most one non-TARGETED validation at a time.
  - TARGETED is the only exception (INTERIM is treated as non-TARGETED).

Scope
- Backend enforcement in validation creation and model-add flows:
  - `api/app/api/validation_workflow.py` (create request, update request models).
  - `api/app/api/model_versions.py` (auto-create validation for version changes).
  - `api/app/api/models.py` (auto-create validation on model creation/approval).
- Error messaging surfaced to users during create/add flows.

Implementation plan
1) Add a reusable conflict-check helper
   - Location: new `api/app/core/validation_conflicts.py` (avoid API module circular imports).
   - Input: `model_ids`, `new_validation_type_code`, `exclude_request_id=None`.
   - Query: join `ValidationRequestModelVersion` + `ValidationRequest` + `TaxonomyValue` (validation type)
     - Filter by `model_id in model_ids`.
     - Filter by status code not in APPROVED/CANCELLED (active).
     - Exclude `exclude_request_id` when updating a request.
   - Output: per-model summary of active validations:
     - `non_targeted_active` list (request_id, type_code/label, status_code/label).
     - `targeted_active` list (same fields).
   - Conflict rule evaluation:
     - If `new_validation_type_code != "TARGETED"` and `non_targeted_active` is not empty -> conflict.
     - If `new_validation_type_code == "TARGETED"` and `non_targeted_active` count > 1 -> conflict (existing violation; do not allow new association).
   - Provide a helper to format a user-friendly error message (string) that lists model IDs/names and the conflicting request IDs/types/statuses.

2) Enforce rule in validation request creation
   - File: `api/app/api/validation_workflow.py` (`create_validation_request`).
   - After resolving `validation_type` (for code), before any request creation:
     - Call conflict helper for `request_data.model_ids`.
     - If conflicts exist, raise HTTP 400 with a clear message explaining the rule and listing conflicts.
   - Optional: also run the check in the `check_warnings` path to fail fast before UI confirmation.

3) Enforce rule in model add/remove flow
   - File: `api/app/api/validation_workflow.py` (`update_request_models`).
   - Before inserting new associations:
     - If `add_models` is non-empty, call conflict helper for those model IDs.
     - Use `exclude_request_id=request_id` so the current request doesn’t self-block.
     - Use the current request’s validation type code as `new_validation_type_code`.
     - Raise HTTP 400 with a message listing conflicts.

4) Enforce rule in auto-create validation flows
   - File: `api/app/api/model_versions.py`
     - Before creating the auto validation request, call the helper using
       `new_validation_type_code` (TARGETED or INTERIM).
     - If conflicts exist, raise HTTP 400 and do not create the validation.
   - File: `api/app/api/models.py`
     - In both auto-create blocks, call the helper before creating the validation.
     - If conflicts exist, return HTTP 400 with the same message.

5) Error messaging
   - Ensure message is a simple string for `create_validation_request` so the UI renders it
     (ValidationWorkflowPage only displays string `detail` today).
   - Suggested message format:
     - "Model <name> (ID <id>) already has active non-TARGETED validation(s): #<id> (<type>, <status>). A model may only be in one non-TARGETED validation at a time; TARGETED validations can overlap."
   - For multiple models, concatenate with line breaks or semicolons.

Test plan
- Add tests in `api/tests/test_validation_workflow.py`:
  - Creating a non-TARGETED validation when a non-TARGETED active exists -> 400 with message.
  - Creating a TARGETED validation when one non-TARGETED active exists -> allowed.
  - Creating a TARGETED validation when two non-TARGETED actives exist -> 400 (existing violation guard).
  - Adding a model to a non-TARGETED request when it already has a different non-TARGETED active -> 400.
  - Adding a model to a TARGETED request when it already has one non-TARGETED active -> allowed.
- If enforcing in auto-create flows:
  - Add targeted tests in `api/tests/test_version_creation_blockers.py` or relevant model tests
    to confirm a version-triggered INTERIM validation is blocked when a non-TARGETED active exists.

Notes
- Active status = any status not in APPROVED/CANCELLED (do not exclude ON_HOLD).
- TARGETED is the only exception; INTERIM is treated as non-TARGETED for overlap checks.

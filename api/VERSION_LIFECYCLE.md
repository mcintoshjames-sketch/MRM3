# Model Version Lifecycle Management

## Overview

Model versions automatically transition through status states based on their linked validation request's progress. This ensures version statuses always reflect the current validation state.

## Version Status States

```
DRAFT → IN_VALIDATION → APPROVED → ACTIVE → SUPERSEDED
         ↓ (cancel/hold)
       DRAFT
```

### Status Definitions

| Status | Description | Can Edit | Can Delete |
|--------|-------------|----------|------------|
| **DRAFT** | Initial state when version created | ✓ Yes | ✓ Yes |
| **IN_VALIDATION** | Validation work in progress | ✗ No | ✗ No |
| **APPROVED** | Validation completed successfully | ✗ No | ✗ No |
| **ACTIVE** | Deployed to production (one per model) | ✗ No | ✗ No |
| **SUPERSEDED** | Replaced by newer active version | ✗ No | ✗ No |

## Automatic Status Transitions

The system automatically updates version statuses when validation request statuses change:

### 1. DRAFT → IN_VALIDATION

**Trigger**: Validation request moves to `IN_PROGRESS` status

**When it happens**:
- Admin marks submission as received (auto-transitions PLANNING → IN_PROGRESS)
- Manual status change via PATCH `/validation-workflow/requests/{id}/status`

**What it means**: Validation work has begun on this version

```python
# Example: When validation moves to IN_PROGRESS
validation_status: "IN_PROGRESS"
→ version.status: "DRAFT" → "IN_VALIDATION"
```

### 2. IN_VALIDATION → APPROVED

**Trigger**: Validation request moves to `APPROVED` status

**When it happens**:
- All required approvals have been granted
- Manual status change to APPROVED

**What it means**: Version has passed validation and can be deployed

```python
# Example: When validation is approved
validation_status: "APPROVED"
→ version.status: "IN_VALIDATION" → "APPROVED"
```

### 3. IN_VALIDATION → DRAFT (Reversion)

**Trigger**: Validation request moves to `CANCELLED` or `ON_HOLD` status

**When it happens**:
- Admin declines/cancels validation request
- Validation placed on hold
- Manual status change to CANCELLED or ON_HOLD

**What it means**: Validation stopped; version reverts to editable draft state

```python
# Example: When validation is cancelled
validation_status: "CANCELLED" or "ON_HOLD"
→ version.status: "IN_VALIDATION" → "DRAFT"
```

### 4. APPROVED → ACTIVE (Manual)

**Trigger**: Manual activation via API endpoint

**Endpoint**: `PATCH /models/{model_id}/versions/{version_id}/activate`

**Requirements**:
- Version must be in APPROVED status
- User must be model owner, developer, or admin

**Side effect**: Previous ACTIVE version automatically becomes SUPERSEDED

```python
# Example: Manual activation
PATCH /versions/123/activate
→ version_123.status: "APPROVED" → "ACTIVE"
→ version_100.status: "ACTIVE" → "SUPERSEDED"  # Previous active
```

### 5. ACTIVE → SUPERSEDED (Automatic)

**Trigger**: Another version of the same model is activated

**When it happens**: Automatically when activating a new version

**What it means**: This version is no longer in production

**Rule**: Only one ACTIVE version per model at any time

## Implementation Details

### Code Location

Automatic transitions are implemented in:
- **Function**: `update_version_statuses_for_validation()`
- **File**: `api/app/api/validation_workflow.py` (lines 213-280)
- **Called from**:
  - `update_validation_request_status()` - Status changes
  - `decline_validation_request()` - Cancellations
  - `mark_submission_received()` - Submission tracking

### Audit Trail

All automatic status changes are logged with:
- **Entity**: `ModelVersion`
- **Action**: `AUTO_STATUS_UPDATE`
- **Changes**: Old status → New status
- **Trigger**: Which validation request status caused the change

### Database

No additional tables required. Uses existing:
- `model_versions.status` column
- `validation_requests.current_status_id` column
- `audit_logs` table for tracking changes

## Example Workflow

### Scenario: New Major Model Change

```
1. Developer creates version 2.0.0 (MAJOR change)
   → Status: DRAFT
   → Auto-creates validation request in INTAKE status

2. Admin reviews and transitions to PLANNING
   → Version status: Still DRAFT

3. Model owner submits validation materials
   Admin marks submission received → Validation auto-transitions to IN_PROGRESS
   → Version status: DRAFT → IN_VALIDATION ✨ Automatic!

4. Validators complete work
   Reviewer signs off → Validation transitions to PENDING_APPROVAL
   → Version status: Still IN_VALIDATION

5. All approvers grant approval → Validation transitions to APPROVED
   → Version status: IN_VALIDATION → APPROVED ✨ Automatic!

6. Model owner activates version
   PATCH /versions/{id}/activate
   → Version status: APPROVED → ACTIVE
   → Previous version: ACTIVE → SUPERSEDED ✨ Automatic!
```

### Scenario: Cancelled Validation

```
1. Version 3.0.0 created with MAJOR change
   → Status: DRAFT
   → Validation request created in INTAKE

2. Validation progresses to IN_PROGRESS
   → Version status: DRAFT → IN_VALIDATION ✨ Automatic!

3. Critical issue discovered - Admin cancels validation
   PATCH /requests/{id}/decline with reason
   → Validation status: IN_PROGRESS → CANCELLED
   → Version status: IN_VALIDATION → DRAFT ✨ Automatic!

4. Developer can now edit version 3.0.0 again
   (Version is back in editable DRAFT state)
```

## Testing

### Verify Status Alignment

Run the verification script to check that all version statuses align with their validation statuses:

```bash
docker compose exec api python3 test_version_lifecycle.py
```

### Fix Misaligned Statuses

If you find versions with incorrect statuses (from before automatic transitions were enabled):

```bash
docker compose exec api python3 fix_version_statuses.py
```

## Migration from Old Data

For existing systems being upgraded:

1. **Run fix script**: `python3 fix_version_statuses.py`
2. **Verify alignment**: `python3 test_version_lifecycle.py`
3. **Going forward**: All transitions are automatic

## API Impact

### No Breaking Changes

Existing endpoints work exactly as before. The only change is that version statuses now update automatically as a side effect of validation status changes.

### New Behavior

Users will notice:
- Version statuses change automatically during validation workflow
- Cannot approve version if status is not IN_VALIDATION
- Cannot activate version if status is not APPROVED
- Edit/delete restrictions enforced based on current status

## Benefits

1. **Data Integrity**: Version status always reflects validation state
2. **Workflow Enforcement**: Can't skip steps (e.g., can't approve DRAFT version)
3. **Audit Trail**: All status changes logged automatically
4. **User Experience**: Less manual status management required
5. **Compliance**: Clear lifecycle tracking for regulatory purposes

## Troubleshooting

### "Cannot approve version with status DRAFT"

**Cause**: Version hasn't moved to IN_VALIDATION yet

**Solution**: Ensure linked validation request has reached IN_PROGRESS status

### "Cannot activate version with status IN_VALIDATION"

**Cause**: Validation not yet approved

**Solution**: Complete validation workflow; wait for APPROVED status

### Version stuck in IN_VALIDATION

**Possible causes**:
1. Validation request not yet approved
2. Status change didn't trigger (check audit logs)

**Solution**: Check validation request status; may need manual status update

## Future Enhancements

Potential additions:
- Email notifications when version status changes
- UI indicators showing which statuses are automatic vs. manual
- Version status history tracking
- Rollback capabilities for superseded versions

# Refactor: Implement Unconditional Approval Reset for "Send Back to In Progress"

## Background

The validation workflow has two ways to send a request back for rework from PENDING_APPROVAL status:

1. **"Send Back" (approver action)** → Transitions to REVISION status
2. **"Send Back to In Progress" (admin action)** → Transitions to IN_PROGRESS status

These two paths serve different business purposes and should handle approval reset differently:

### REVISION Workflow (Approver "Send Back") - Current Behavior ✅ KEEP AS-IS

**Purpose**: Handle minor corrections or clarifications that don't fundamentally change the validation

**Use Cases**: "Fix this typo", "clarify this wording", "add supporting documentation"

**Logic**:
- **When entering REVISION**: Creates a snapshot capturing:
  - Scorecard overall rating
  - List of recommendation IDs linked to the validation
  - List of limitation IDs linked to the validation
  - Which approver sent it back
- **When resubmitting (REVISION → PENDING_APPROVAL)**: Compares current state to snapshot to detect material changes
- **Approval Reset Logic (INTELLIGENT)**:
  - Always resets the approver who sent it back
  - Resets all "Approved" approvals ONLY IF material changes detected
  - Always resets all "Sent Back" approvals

**Why this is correct**: Minor fixes shouldn't require everyone to re-approve if nothing substantial changed. Only when rating/recommendations/limitations change should all approvers review again.

### IN_PROGRESS Sendback (Admin Override) - Current Behavior ❌ NEEDS FIXING

**Purpose**: Handle substantial rework situations where the validation needs to go back to the drawing board

**Use Cases**: "Significant portions need redoing", "approach is fundamentally flawed", "major gaps identified"

**Current Problematic Behavior**:
- **When entering IN_PROGRESS from PENDING_APPROVAL**:
  - ✅ Voids all conditional approvals (correct)
  - ❌ Does NOT reset traditional (Global/Regional) approvals
  - ❌ Does NOT create a snapshot
- **When returning (IN_PROGRESS → PENDING_APPROVAL)**:
  - ❌ Does NOT track what changes were made

**Problem**: If a Global Approver already approved before admin sends back to In Progress, that approval remains valid even after substantive rework is done. This defeats the purpose of the admin override for major rework.

**Desired Behavior**:
- **When entering IN_PROGRESS from PENDING_APPROVAL**:
  - ✅ Create snapshot (for audit trail)
  - ✅ Void conditional approvals, reset ALL traditional approvals (Global/Regional) unconditionally to Pending
  - ✅ No material change detection needed - it's always a full reset
- **When returning (IN_PROGRESS → PENDING_APPROVAL)**:
  - ✅ Track material changes for audit/transparency purposes only
  - ✅ All approvers must re-approve (already reset when sent to IN_PROGRESS)

**Why this makes sense**: 
- Different severity levels: REVISION = minor fixes, IN PROGRESS = major rework
- Privilege alignment: Admin-only action should have more drastic consequences
- Stakeholder expectations: If something went all the way back to IN PROGRESS, everyone should expect to re-review
- Simpler logic: No need for conditional reset - always reset is cleaner

## Goal

Implement unconditional traditional-approval reset (with conditional approvals voided) when admin sends a request back to IN_PROGRESS, while maintaining the current intelligent REVISION workflow behavior.

## Requirements

### 0. Access Control + Required Reason (NEW)

**Admin-only enforcement**:
- `PENDING_APPROVAL → IN_PROGRESS` must be admin-only in backend (not just UI).
- If a non-admin attempts this transition, return 403 with a clear error.

**Mandatory reason**:
- Require a non-empty `change_reason` when admin sends back to IN_PROGRESS.
- Ensure UI enforces this (no empty submit).

### 1. Create Snapshot When Transitioning PENDING_APPROVAL → IN_PROGRESS

**File**: `api/app/api/validation_workflow.py`

**Location**: In the `update_validation_request_status` function, in the section that handles `PENDING_APPROVAL → IN_PROGRESS` transition (around line 3499).

**What to do**:
- Before transitioning, create a snapshot using the existing `create_revision_snapshot()` function
- Add a context discriminator:
  - `snapshot["context_type"] = "admin_in_progress_sendback"`
- Include metadata about who initiated the sendback (admin user ID)
  - `snapshot["sent_back_to_in_progress_by_user_id"] = current_user.user_id`
- Store the snapshot in `ValidationStatusHistory.additional_context` (JSON format)

**Purpose**: Create an audit trail of the validation state when sent back to IN_PROGRESS. While we reset traditional approvals unconditionally (and void conditional approvals), having the snapshot allows us to track what actually changed during the rework period for transparency and compliance purposes.

**Example**:
```python
# When moving FROM PENDING_APPROVAL TO IN_PROGRESS (admin-only)
if old_status_code == "PENDING_APPROVAL" and new_status_code == "IN_PROGRESS":
    # Enforce admin-only + required reason
    # (Reject if non-admin or change_reason missing/empty)
    # Create snapshot of current state for audit trail and change tracking
    snapshot = create_revision_snapshot(db, validation_request)
    snapshot["context_type"] = "admin_in_progress_sendback"
    snapshot["sent_back_to_in_progress_by_user_id"] = current_user.user_id
    
    # Store snapshot in the status history entry that will be created
    # (You'll need to modify create_status_history_entry to accept additional_context,
    # or manually create the history entry here with the snapshot)
    
    # ... rest of existing logic for voiding conditional approvals AND resetting traditional approvals
```

### 2. Reset ALL Approvals Unconditionally When Transitioning PENDING_APPROVAL → IN_PROGRESS

**File**: `api/app/api/validation_workflow.py`

**Location**: Same section as above (PENDING_APPROVAL → IN_PROGRESS)

**What to do**:
- After voiding conditional approvals, also reset ALL traditional (Global/Regional) approvals
- Set their `approval_status` back to "Pending" regardless of current state
- Clear `approved_at` and `comments`
- **Proxy fields**: ValidationApproval does not include `is_proxy_approval` or `proxy_evidence` (no reset needed). If such fields are added later, include them in the reset.
- Create audit logs for each reset approval
- **CRITICAL**: This is unconditional for traditional approvals - we ALWAYS reset Global/Regional approvals when using admin "Send Back to In Progress", regardless of whether material changes will occur. The business logic is: if an admin is sending it back to IN_PROGRESS, it requires major rework and everyone must re-review.

**Example**:
```python
# Reset ALL traditional approvals (Global/Regional) - UNCONDITIONAL
traditional_approvals = db.query(ValidationApproval).filter(
    ValidationApproval.request_id == request_id,
    ValidationApproval.approval_type.in_(["Global", "Regional"]),
    ValidationApproval.approval_status.in_(["Approved", "Sent Back", "Pending"]),  # Include all states
    ValidationApproval.voided_by_id.is_(None)
).all()

for approval in traditional_approvals:
    old_status = approval.approval_status
    
    # Always reset to Pending, even if already Pending (for consistency)
    approval.approval_status = "Pending"
    approval.approved_at = None
    approval.comments = None
    # Note: ValidationApproval does not have proxy fields to reset here.
    
    # Create audit log for reset
    reset_audit = AuditLog(
        entity_type="ValidationApproval",
        entity_id=approval.approval_id,
        action="RESET",
        user_id=current_user.user_id,
        changes={
            "reason": f"Admin sent validation back to In Progress (major rework required): {status_update.change_reason or 'No reason provided'}",
            "old_approval_status": old_status,
            "new_approval_status": "Pending",
            "approval_type": approval.approval_type,
            "request_id": request_id,
            "reset_type": "unconditional"  # Flag that this was unconditional (unlike REVISION which is conditional)
        },
        timestamp=utc_now()
    )
    db.add(reset_audit)
```

### 3. Track Material Changes When Returning to PENDING_APPROVAL After Admin Sendback (Audit Only)

**File**: `api/app/api/validation_workflow.py`

**Location**: In the `update_validation_request_status` function, add new logic for IN_PROGRESS → PENDING_APPROVAL transition.

**What to do**:
- When transitioning to PENDING_APPROVAL after admin sendback, check for a stored snapshot in status history
- This must run even if the path is `IN_PROGRESS → REVIEW → PENDING_APPROVAL`
- Compare current state to snapshot using the same material change detection logic as REVISION workflow
- Log whether material changes were detected in the audit trail
- Add the change summary to status history (either by attaching `additional_context` to the existing status change entry or by creating a dedicated history entry with a distinct `context_type` to avoid duplication)
- **IMPORTANT**: This is ONLY for audit/transparency purposes. Unlike the REVISION workflow, we do NOT use this to conditionally reset approvals because we already unconditionally reset traditional approvals (and void conditional approvals) when entering IN_PROGRESS. This tracking just documents what actually changed during the rework period.

**Example**:
```python
# When moving TO PENDING_APPROVAL (after admin sendback)
if new_status_code == "PENDING_APPROVAL":
    # Check if this is a return from an admin sendback (context_type match)
    last_sendback_entry = db.query(ValidationStatusHistory).filter(
        ValidationStatusHistory.request_id == request_id,
        ValidationStatusHistory.additional_context.isnot(None),
        ValidationStatusHistory.additional_context.contains('"context_type": "admin_in_progress_sendback"')
    ).order_by(desc(ValidationStatusHistory.changed_at)).first()
    # NOTE: This should find the most recent admin sendback for this request.
    # If needed, add old/new status filters to scope to PENDING_APPROVAL -> IN_PROGRESS transitions.
    
    if last_sendback_entry and last_sendback_entry.additional_context:
        snapshot = json.loads(last_sendback_entry.additional_context)
        
        # Compare current state to snapshot (same logic as REVISION workflow)
        current_rating = None
        if validation_request.scorecard_result:
            current_rating = validation_request.scorecard_result.overall_rating
        
        current_rec_ids = set(...)  # Same logic as REVISION workflow
        current_lim_ids = set(...)  # Same logic as REVISION workflow
        
        material_change = (
            current_rating != snapshot.get("overall_rating") or
            current_rec_ids != set(snapshot.get("recommendation_ids", [])) or
            current_lim_ids != set(snapshot.get("limitation_ids", []))
        )
        
        # Create audit log documenting what changed (for transparency only - approvals already reset)
        audit_log = AuditLog(
            entity_type="ValidationRequest",
            entity_id=request_id,
            action="RETURN_FROM_IN_PROGRESS_SENDBACK",
            user_id=current_user.user_id,
            changes={
                "material_change_detected": material_change,
                "change_details": {
                    "rating_changed": current_rating != snapshot.get("overall_rating"),
                    "recommendations_changed": current_rec_ids != set(snapshot.get("recommendation_ids", [])),
                    "limitations_changed": current_lim_ids != set(snapshot.get("limitation_ids", []))
                },
                "note": "All approvals were already reset when sent to IN_PROGRESS - this tracking is for audit purposes only",
                "reason": status_update.change_reason
            },
            timestamp=utc_now()
        )
        db.add(audit_log)

        # Also attach material-change audit to status history for visibility
        # (Update the existing status history entry for this transition, or create a dedicated
        # entry with context_type "admin_in_progress_sendback_audit" to avoid duplicates.)
```

### 4. Update create_status_history_entry to Support additional_context

**File**: `api/app/api/validation_workflow.py`

**Location**: The `create_status_history_entry` function (around line 1016)

**What to do**:
- Add optional `additional_context` parameter
- Store it in the ValidationStatusHistory record if provided

**Example**:
```python
def create_status_history_entry(
    db: Session,
    request_id: int,
    old_status_id: Optional[int],
    new_status_id: int,
    changed_by_id: int,
    change_reason: Optional[str] = None,
    additional_context: Optional[str] = None  # Add this parameter
):
    """Create a status history entry."""
    history = ValidationStatusHistory(
        request_id=request_id,
        old_status_id=old_status_id,
        new_status_id=new_status_id,
        changed_by_id=changed_by_id,
        change_reason=change_reason,
        additional_context=additional_context,  # Add this
        changed_at=utc_now()
    )
    db.add(history)
```

### 5. Update the Call to create_status_history_entry for PENDING_APPROVAL → IN_PROGRESS

**File**: `api/app/api/validation_workflow.py`

**Location**: After creating the snapshot, when calling `create_status_history_entry`

**What to do**:
- Pass the snapshot as `additional_context` parameter
- Ensure it's JSON-encoded

**Example**:
```python
# Create status history with snapshot
create_status_history_entry(
    db, request_id, old_status_id, new_status.value_id,
    current_user.user_id, status_update.change_reason,
    additional_context=json.dumps(snapshot)
)
```

### 6. Add Explicit Context Type for REVISION Sendback (NEW)

**File**: `api/app/api/validation_workflow.py`

**Location**: In the approval send-back handler that creates the REVISION snapshot.

**What to do**:
- Add `snapshot["context_type"] = "revision_sendback"` when constructing the snapshot.
- Update the REVISION resubmission query to only look for this context type:
  - `ValidationStatusHistory.additional_context.contains('"context_type": "revision_sendback"')`

**Purpose**: Avoid mixing admin sendback snapshots with revision snapshots.

## Implementation Notes

### Code Organization
- The main changes are in `api/app/api/validation_workflow.py` in the `update_validation_request_status` function
- Look for the section starting around line 3499 with comment `# ===== VOID CONDITIONAL APPROVALS WHEN SENDING BACK =====`
- The existing snapshot/comparison logic for REVISION workflow is around lines 3552-3644 (update it to filter by `context_type`)
- The REVISION snapshot is created in the approval send-back handler (add `context_type` there too)

### Key Differences Between REVISION and IN_PROGRESS Workflows

| Aspect | REVISION (Approver Sendback) | IN_PROGRESS (Admin Sendback) |
|--------|------------------------------|------------------------------|
| **Purpose** | Minor corrections/clarifications | Major rework/substantial changes |
| **When to Use** | "Fix typo", "clarify wording" | "Fundamental issues", "major gaps" |
| **Snapshot Created** | ✅ Yes | ✅ Yes |
| **Approval Reset** | Conditional (based on material changes) | Unconditional for traditional approvals; conditional approvals are voided |
| **Material Change Detection** | Used to decide approval reset | Audit trail only (approvals already reset) |
| **Privilege Required** | Approver role | Admin role |
| **Business Logic** | Intelligent - preserve approvals if nothing material changed | Simple - always full reset for major rework |

### Testing Considerations
After implementation, test:
1. **Happy Path - Major Rework**:
   - Admin sends request back to In Progress from Pending Approval (with Global and Regional approvals already granted)
   - Verify conditional approvals are voided; traditional approvals are reset to Pending
   - Verify snapshot is created in status history
   - Make substantive changes (change scorecard rating, add recommendation, add limitation)
   - Advance back to Pending Approval
   - Verify audit logs document material changes detected
   - Verify all approvers must re-approve

2. **Edge Case - Minimal Changes**:
   - Admin sends back to In Progress
   - Make NO material changes (same rating, same recs, same limitations)
   - Advance back to Pending Approval
   - Verify audit logs show NO material changes
   - Verify all approvers STILL must re-approve (unlike REVISION where they wouldn't need to)
   - This confirms the unconditional reset is working correctly

3. **REVISION Workflow Still Works**:
   - Approver sends back via "Send Back" button (→ REVISION)
   - Make NO material changes
   - Resubmit to Pending Approval
   - Verify only the sending approver's vote was reset (other approvals preserved)
   - This confirms REVISION workflow wasn't broken by the changes

4. **Material Change Detection Coverage (NEW)**:
   - Scorecard rating change (e.g., rating A → B) should reset all Approved approvals on REVISION resubmission
   - Recommendation change (add/remove) should reset all Approved approvals on REVISION resubmission
   - Limitation change (add/remove) should reset all Approved approvals on REVISION resubmission
   - No material change should preserve Approved approvals (only sender + Sent Back reset)
   - Mixed approval states: some Approved, some Sent Back; verify Sent Back always resets, Approved resets only when material change
   - Repeat the material change scenarios for admin sendback flow (audit logging), confirming approvals were already reset at sendback

### Backward Compatibility
- Existing validations in IN_PROGRESS status won't have snapshots - that's OK
- The material change detection gracefully handles missing snapshots
- No breaking changes to API contracts
- Frontend doesn't need changes - "Send Back to In Progress" button already exists

## Files to Modify

1. `api/app/api/validation_workflow.py`
   - Function: `create_status_history_entry` - add `additional_context` parameter
   - Function: `update_validation_request_status` - modify PENDING_APPROVAL → IN_PROGRESS section
   - Function: `update_validation_request_status` - add admin sendback audit detection on return to PENDING_APPROVAL
   - Approval send-back handler (REVISION) - add `context_type` and filter resubmission query
2. Frontend (taxonomy/validation workflow UI)
   - Require `change_reason` in the admin "Send Back to In Progress" flow
3. Tests
   - Add unit/integration tests for material change detection and approval reset logic for both workflows

## Success Criteria

✅ When admin sends back to In Progress:
- Snapshot is created and stored in status history
- Conditional approvals are voided; traditional approvals (Global/Regional) are unconditionally reset to Pending
- Audit logs document the reset with "unconditional" flag
- This happens regardless of whether changes will be material
- Transition is blocked for non-admins
- A non-empty change_reason is required

✅ When returning to Pending Approval after In Progress sendback:
- Material change detection runs (reusing REVISION workflow logic)
- Audit logs document whether material changes occurred during rework
- All approvers must re-approve (because approvals were already reset when entering IN_PROGRESS)
- Transparency about what changed during rework period
- Status history includes audit context for the admin sendback return

✅ REVISION workflow unchanged:
- Still creates snapshot when entering REVISION
- Still intelligently resets approvals based on material changes
- Preserves approvals when changes are non-material

✅ Business logic alignment:
- REVISION = minor fixes, intelligent approval handling
- IN_PROGRESS = major rework, unconditional full reset of traditional approvals (conditional approvals voided)
- Different tools for different severity levels

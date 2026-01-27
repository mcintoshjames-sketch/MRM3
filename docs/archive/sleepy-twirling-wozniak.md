# Plan: Add "Send Back" Option for Validation Approvals

## Summary
Add a third approval decision option "Send Back" for Global and Regional approvers. When selected, requires mandatory comments and transitions the validation request to a new "REVISION" status. The team can edit, respond, and resubmit for approval. Includes intelligent approval reset logic and PDF export for "effective challenge" documentation.

---

## User Requirements (Confirmed)

| Requirement | Decision |
|-------------|----------|
| **Approval Reset Behavior** | Only sending-back approver resets, UNLESS scorecard overall rating changes OR recommendations added/removed OR limitations added/removed - then reset ALL approvals |
| **Response Mechanism** | Use status history `change_reason` for team's response |
| **REVISION Editing** | Yes - same editing permissions as REVIEW status |
| **History Display** | Existing status history sufficient + PDF export for "effective challenge" |

---

## Implementation Phases

### Phase 1: Database Changes

#### 1.1 Add `additional_context` to ValidationStatusHistory
**File:** [api/app/models/validation.py](api/app/models/validation.py) (line ~660)

```python
additional_context: Mapped[Optional[str]] = mapped_column(
    Text, nullable=True,
    comment="JSON storing action-specific details (e.g., revision snapshots)"
)
```

**Purpose:** Store snapshot of overall_rating, recommendation_ids, limitation_ids when entering REVISION for comparison on resubmission.

#### 1.2 Create Alembic Migration
**New file:** `api/alembic/versions/xxxx_add_sendback_support.py`

```python
def upgrade():
    op.add_column('validation_status_history',
        sa.Column('additional_context', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('validation_status_history', 'additional_context')
```

#### 1.3 Add REVISION Status to Seed Data
**File:** [api/app/seed.py](api/app/seed.py) (line ~1305)

Add to "Validation Request Status" taxonomy:
```python
{
    "code": "REVISION",
    "label": "Revision",
    "description": "Sent back by approver for revisions - awaiting validator updates",
    "sort_order": 5.5
}
```

---

### Phase 2: Backend API Changes

#### 2.1 Update State Machine
**File:** [api/app/api/validation_workflow.py](api/app/api/validation_workflow.py) (lines 652-668)

```python
valid_transitions = {
    # ... existing ...
    "PENDING_APPROVAL": ["APPROVED", "REVISION", "REVIEW", "IN_PROGRESS", "CANCELLED", "ON_HOLD"],
    "REVISION": ["PENDING_APPROVAL", "CANCELLED", "ON_HOLD"],  # NEW
    "ON_HOLD": ["INTAKE", "PLANNING", "IN_PROGRESS", "REVIEW", "PENDING_APPROVAL", "REVISION", "CANCELLED"],
}
```

#### 2.2 Update ValidationApprovalUpdate Schema
**File:** [api/app/schemas/validation.py](api/app/schemas/validation.py) (lines 335-346)

Add "Sent Back" to allowed `approval_status` values:
```python
@field_validator('approval_status')
def validate_status(cls, v):
    allowed = ['Pending', 'Approved', 'Rejected', 'Sent Back']
    if v not in allowed:
        raise ValueError(f'approval_status must be one of {allowed}')
    return v
```

#### 2.3 Add Snapshot Helper Function
**File:** [api/app/api/validation_workflow.py](api/app/api/validation_workflow.py) (new function ~line 80)

```python
def create_revision_snapshot(db: Session, validation_request: ValidationRequest) -> dict:
    """Create snapshot for comparison on resubmission."""
    from app.models.recommendation import Recommendation
    from app.models.limitation import ModelLimitation

    overall_rating = validation_request.scorecard_result.overall_rating if validation_request.scorecard_result else None

    recommendation_ids = [r.recommendation_id for r in db.query(Recommendation).filter(
        Recommendation.validation_request_id == validation_request.request_id
    ).all()]

    limitation_ids = [l.limitation_id for l in db.query(ModelLimitation).filter(
        ModelLimitation.validation_request_id == validation_request.request_id
    ).all()]

    return {
        "snapshot_at": utc_now().isoformat(),
        "overall_rating": overall_rating,
        "recommendation_ids": sorted(recommendation_ids),
        "limitation_ids": sorted(limitation_ids)
    }
```

#### 2.4 Modify submit_approval Endpoint
**File:** [api/app/api/validation_workflow.py](api/app/api/validation_workflow.py) (lines 3392-3561)

Add "Sent Back" handling:

```python
if update_data.approval_status == "Sent Back":
    # Only Global and Regional approvers can send back
    if approval.approval_type not in ["Global", "Regional"]:
        raise HTTPException(400, "Only Global and Regional approvers can send back")

    # Comments are mandatory
    if not update_data.comments or not update_data.comments.strip():
        raise HTTPException(400, "Comments are required when sending back for revision")

    # Create snapshot BEFORE transitioning
    snapshot = create_revision_snapshot(db, validation_request)
    snapshot["sent_back_by_approval_id"] = approval.approval_id

    # Update this approval
    approval.approval_status = "Sent Back"
    approval.comments = update_data.comments
    approval.approved_at = utc_now()

    # Transition to REVISION status
    revision_status = get_taxonomy_value_by_code(db, "Validation Request Status", "REVISION")
    old_status_id = validation_request.current_status_id
    validation_request.current_status_id = revision_status.value_id

    # Create status history with snapshot
    history = ValidationStatusHistory(
        request_id=validation_request.request_id,
        old_status_id=old_status_id,
        new_status_id=revision_status.value_id,
        changed_by_id=current_user.user_id,
        change_reason=f"Sent back by {approval.approver_role}: {update_data.comments}",
        additional_context=json.dumps(snapshot),
        changed_at=utc_now()
    )
    db.add(history)
```

#### 2.5 Add Resubmission Logic with Conditional Reset
**File:** [api/app/api/validation_workflow.py](api/app/api/validation_workflow.py) (in status update handler ~line 2200)

```python
if old_status_code == "REVISION" and new_status_code == "PENDING_APPROVAL":
    # Find most recent revision snapshot
    last_revision = db.query(ValidationStatusHistory).filter(
        ValidationStatusHistory.request_id == request_id,
        ValidationStatusHistory.additional_context.isnot(None)
    ).order_by(desc(ValidationStatusHistory.changed_at)).first()

    if last_revision and last_revision.additional_context:
        snapshot = json.loads(last_revision.additional_context)

        # Compare current state to snapshot
        current_rating = validation_request.scorecard_result.overall_rating if validation_request.scorecard_result else None
        current_rec_ids = set(r.recommendation_id for r in db.query(Recommendation).filter(...).all())
        current_lim_ids = set(l.limitation_id for l in db.query(ModelLimitation).filter(...).all())

        material_change = (
            current_rating != snapshot.get("overall_rating") or
            current_rec_ids != set(snapshot.get("recommendation_ids", [])) or
            current_lim_ids != set(snapshot.get("limitation_ids", []))
        )

        # Reset approvals
        for approval in validation_request.approvals:
            if approval.approval_status == "Sent Back":
                # Always reset the sender
                approval.approval_status = "Pending"
                approval.approved_at = None
            elif approval.approval_status == "Approved" and material_change:
                # Reset others only if material changes detected
                approval.approval_status = "Pending"
                approval.approved_at = None
```

#### 2.6 Add Effective Challenge PDF Export Endpoint
**File:** [api/app/api/validation_workflow.py](api/app/api/validation_workflow.py) (new endpoint)

```python
@router.get("/requests/{request_id}/effective-challenge-report")
def export_effective_challenge_report(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate PDF documenting effective challenge process (send-backs and responses)."""
    from fpdf import FPDF
    import io
    from fastapi.responses import StreamingResponse

    # Fetch validation request with history
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.status_history),
        joinedload(ValidationRequest.approvals)
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(404, "Validation request not found")

    # Find all REVISION entries (send-backs) and subsequent PENDING_APPROVAL entries (responses)
    revision_entries = [h for h in validation_request.status_history
                       if h.new_status and h.new_status.code == "REVISION"]
    resubmit_entries = [h for h in validation_request.status_history
                       if h.old_status and h.old_status.code == "REVISION"
                       and h.new_status and h.new_status.code == "PENDING_APPROVAL"]

    # Generate PDF with rounds...
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Effective Challenge Report', ln=True, align='C')
    # ... content for each round ...

    pdf_bytes = pdf.output()
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=effective_challenge_VR{request_id}.pdf"}
    )
```

---

### Phase 3: Frontend Changes

#### 3.1 Update Status Colors
**File:** [web/src/pages/ValidationRequestDetailPage.tsx](web/src/pages/ValidationRequestDetailPage.tsx)

```typescript
// Add to status color function (~line 451)
case 'REVISION': return 'bg-orange-100 text-orange-800';

// Add to approval status colors (~line 475)
case 'Sent Back': return 'bg-orange-100 text-orange-800';
```

#### 3.2 Update Approval Modal
**File:** [web/src/pages/ValidationRequestDetailPage.tsx](web/src/pages/ValidationRequestDetailPage.tsx) (lines 2695-2804)

Add "Send Back" option (only for Global/Regional approvers):
```tsx
<select value={approvalUpdate.status} onChange={...}>
    <option value="">Select decision...</option>
    <option value="Approved">Approve</option>
    <option value="Rejected">Reject</option>
    {(approval.approval_type === 'Global' || approval.approval_type === 'Regional') && (
        <option value="Sent Back">Send Back for Revision</option>
    )}
</select>

{approvalUpdate.status === 'Sent Back' && (
    <>
        <p className="text-orange-600 text-sm mt-2">
            This will move the validation to Revision status for the team to address your feedback.
        </p>
        <p className="text-xs text-gray-500">Comments are required.</p>
    </>
)}
```

Add validation:
```typescript
if (approvalUpdate.status === 'Sent Back' && !approvalUpdate.comments?.trim()) {
    setApprovalValidationError('Comments are required when sending back');
    return;
}
```

#### 3.3 Add Resubmit Button
**File:** [web/src/pages/ValidationRequestDetailPage.tsx](web/src/pages/ValidationRequestDetailPage.tsx)

```tsx
{request.current_status?.code === 'REVISION' && (
    <button
        onClick={() => handleStatusChange('PENDING_APPROVAL')}
        className="btn-primary"
    >
        Resubmit for Approval
    </button>
)}
```

#### 3.4 Add PDF Export Button
**File:** [web/src/pages/ValidationRequestDetailPage.tsx](web/src/pages/ValidationRequestDetailPage.tsx)

```tsx
<button
    onClick={async () => {
        const response = await client.get(
            `/validation-workflow/requests/${id}/effective-challenge-report`,
            { responseType: 'blob' }
        );
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `effective_challenge_VR${id}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
    }}
    className="btn-secondary text-sm"
>
    Export Challenge Report (PDF)
</button>
```

---

### Phase 4: Tests

**File:** [api/tests/test_validation_workflow.py](api/tests/test_validation_workflow.py)

Add test cases:
1. `test_send_back_requires_comments` - 400 if comments empty
2. `test_send_back_transitions_to_revision` - Status changes to REVISION
3. `test_send_back_only_global_regional` - Conditional approvers cannot send back
4. `test_resubmit_resets_sender_approval` - Sender's approval becomes Pending
5. `test_resubmit_no_changes_keeps_approved` - Others keep Approved if no material changes
6. `test_resubmit_with_rating_change_resets_all` - Rating change resets all
7. `test_resubmit_with_recommendation_added_resets_all` - Recommendation added resets all
8. `test_resubmit_with_limitation_removed_resets_all` - Limitation removed resets all
9. `test_multiple_sendback_rounds` - Multiple cycles work correctly
10. `test_effective_challenge_pdf_export` - PDF generates with content

---

## Files to Modify

| File | Changes |
|------|---------|
| `api/app/models/validation.py` | Add `additional_context` to ValidationStatusHistory |
| `api/app/seed.py` | Add REVISION taxonomy value |
| `api/app/schemas/validation.py` | Add "Sent Back" to approval_status validation |
| `api/app/api/validation_workflow.py` | State machine, send-back logic, resubmission logic, PDF export |
| `api/alembic/versions/xxxx_....py` | Migration for additional_context column |
| `web/src/pages/ValidationRequestDetailPage.tsx` | Modal updates, status colors, resubmit button, PDF button |
| `api/tests/test_validation_workflow.py` | New test cases |
| `CLAUDE.md` | Document REVISION status in workflow section |

---

## Implementation Order

1. **Migration + Model** - Add `additional_context` column
2. **Seed Data** - Add REVISION status (run docker compose up to re-seed)
3. **State Machine** - Update valid_transitions
4. **Schema** - Add "Sent Back" validation
5. **Send-back Logic** - Modify PATCH /approvals endpoint
6. **Resubmission Logic** - Add conditional reset on status change
7. **PDF Export** - New endpoint
8. **Frontend** - All UI changes
9. **Tests** - Write and run tests

---

## Risk Mitigation

- **Atomicity**: Wrap send-back operations (approval update + status transition + history) in single transaction
- **Backwards Compatibility**: "Sent Back" is additive; existing approvals unaffected
- **Edge Cases**: Test multiple rounds, edge timing, concurrent approvals

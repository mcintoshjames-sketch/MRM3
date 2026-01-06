# Review: USER_GUIDE_ATTESTATION.md

This document contains findings from reviewing the attestation user guide against the current codebase implementation.

---

## Summary

The user guide is comprehensive and well-organized. Most documented features align with the implementation. However, there are several material omissions, a few inconsistencies, and areas needing clarification.

---

## Material Omissions

### 1. Delegation Feature Not Documented

**Location**: Not mentioned anywhere in the user guide

**Implementation**: The system supports model delegates who can attest on behalf of model owners. This is a significant feature.

* **Backend**: `api/app/models/model_delegate.py` defines the `ModelDelegate` model with a `can_attest` permission flag.
* **Backend**: `api/app/api/attestations.py` - The `can_attest_for_model()` helper function (lines 166-184) checks if a user can attest via delegation:
```python
delegate = db.query(ModelDelegate).filter(
    ModelDelegate.model_id == model.model_id,
    ModelDelegate.user_id == user.user_id,
    ModelDelegate.revoked_at == None,
    ModelDelegate.can_attest == True
).first()

```


* **Frontend**: `web/src/components/DelegatesSection.tsx` and `web/src/pages/BatchDelegatesPage.tsx` provide delegation management UI.

**Recommendation**: Add a section explaining:

* How model owners can delegate attestation rights to other users.
* How to access the delegation feature (from Model details page).
* The `can_attest` permission checkbox.
* How delegated attestations appear to delegates on "My Attestations" page.

---

### 2. Reports Endpoints Not Documented

**Location**: Not mentioned in user guide

**Implementation**: The API includes report endpoints that provide valuable data for administrators:

* `GET /attestations/reports/coverage?cycle_id={id}` - Returns detailed coverage report by risk tier.
* `GET /attestations/reports/timeliness?cycle_id={id}` - Returns timeliness metrics and past-due items.

**Files**:

* `/api/app/api/attestations.py` lines 2097-2307

**Recommendation**: Add a "Reports" subsection under "For Administrators" explaining available reports and their metrics.

---

### 3. MODEL_VERSION Change Type Not Documented

**Location**: Section "For Administrators" > "Viewing Linked Inventory Changes"

**Implementation**: The guide mentions three change types (`MODEL_EDIT`, `NEW_MODEL`, `DECOMMISSION`), but the code also supports `MODEL_VERSION`:

```python
class AttestationChangeType(str, enum.Enum):
    MODEL_EDIT = "MODEL_EDIT"
    MODEL_VERSION = "MODEL_VERSION"  # New version of a model (via Submit Model Change)
    NEW_MODEL = "NEW_MODEL"
    DECOMMISSION = "DECOMMISSION"

```

**Files**:

* `/api/app/models/attestation.py` lines 66-72
* `/api/app/schemas/attestation.py` lines 52-57
* `/web/src/pages/AttestationDetailPage.tsx` line 40

**Recommendation**: Document `MODEL_VERSION` as a fourth change type, explaining it's used when a model owner submits a version/change through the "Submit Model Change" workflow.

---

### 4. Admin-Only Force Close Justification Not Documented

**Location**: Section "Coverage Targets & Compliance" > "Blocking Gaps"

**Implementation**: The force close feature requires a justification reason that is captured in the audit log. The guide mentions Force Close but doesn't explain the justification requirement.

**Code** (`/api/app/api/attestations.py` lines 557-564):

```python
create_audit_log(
    ...
    action="CLOSE",
    ...
    changes={"forced": force, "drafts_cleaned_up": draft_count}
)

```

**Frontend** (`/web/src/pages/AttestationCyclesPage.tsx`):

* `forceCloseReason` state variable suggests UI collects a reason.

**Recommendation**: Clarify that when force-closing, administrators must provide a justification reason that is recorded for audit purposes.

---

### 5. Linked Changes Tab Missing from Admin Tab List

**Location**: Section "For Administrators" > "Managing Attestation Cycles"

**Current**: Lists eight tabs: "Cycles, Scheduling Rules, Coverage Targets, Review Queue, High Fluctuation Owners, All Records, Linked Changes, and Questions"

**Issue**: While Linked Changes is listed, there's no detailed documentation about this tab's functionality.

**Implementation**:

* `/api/app/api/attestations.py` endpoint `GET /admin/linked-changes` (lines 2767-2859)
* Frontend tab at `/web/src/pages/AttestationCyclesPage.tsx`

**Recommendation**: Add a section under "For Administrators" documenting the Linked Changes tab:

* **Purpose**: View all inventory changes linked to attestations across cycles.
* **Filters**: By cycle and by change type.
* **Navigation**: Links to related approval workflows.

---

### 6. Evidence API Endpoints Not Documented

**Location**: Not mentioned in user guide (though evidence submission is mentioned)

**Implementation**: There are separate API endpoints for managing evidence:

* `POST /attestations/records/{attestation_id}/evidence` - Add evidence URL.
* `DELETE /attestations/evidence/{evidence_id}` - Remove evidence.

**Files**: `/api/app/api/attestations.py` lines 1171-1291

**Recommendation**: Consider adding a note about evidence management if useful for technical documentation or API integrators.

---

## Inconsistencies

### 1. Status Terminology: "Admin Review" vs "Submitted"

**Location**: Section "For Model Owners" > "Finding Your Attestations"

**User Guide Says**: "Each model shows: ... Current status (Pending, Submitted, Accepted, Rejected, or Admin Review)"

**Implementation**: The `AttestationRecordStatus` enum includes:

```python
class AttestationRecordStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ADMIN_REVIEW = "ADMIN_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

```

**Finding**: The `ADMIN_REVIEW` status exists in the enum but the user guide doesn't clearly explain when an attestation enters this status vs regular `SUBMITTED`. In the code, the status goes directly from PENDING to SUBMITTED (or auto-ACCEPTED). The ADMIN_REVIEW status appears unused in the main workflow.

**Recommendation**: Either:

1. Remove `ADMIN_REVIEW` from the status list in the user guide if it's not actively used, OR
2. Document when attestations enter `ADMIN_REVIEW` status if this is a planned feature.

---

### 2. Questions Tab: "Add New Question" Method

**Location**: Section "Questions Configuration" > "Important Notes"

**User Guide Says**: "To add a new question, use the Taxonomy page to add a value to the 'Attestation Question' taxonomy."

**Implementation**: This is correct. The Questions tab only provides editing of existing questions (via `/attestations/questions/{value_id}` PATCH endpoint). New questions must be created through the Taxonomy system.

**Finding**: This is accurate but may confuse users who expect to add questions directly from the Questions tab.

**Recommendation**: Consider adding clearer guidance or a link/button on the Questions tab UI directing admins to the Taxonomy page for adding new questions.

---

### 3. Scope Rules Section Title vs. Content

**Location**: Section "Scheduling Rules"

**User Guide Says**: Refers to "Scheduling Rules" and "Scope Rules" in the Table of Contents.

**Finding**: The Table of Contents references "[Scheduling Rules](https://www.google.com/search?q=%23scheduling-rules)" correctly, but there's no separate "Scope Rules" section. This appears to be a labeling inconsistency in the TOC.

**Recommendation**: The Table of Contents entry 6 says "Scheduling Rules" which is correct. No action needed, but verify the section numbering is accurate.

---

## Clarifications Needed

### 1. Frequency Filtering for Questions

**Location**: Section "Questions Configuration" > "Frequency Scope Options"

**Current Documentation**: Explains ANNUAL, QUARTERLY, and BOTH options.

**Implementation**: Questions are filtered based on the model's applied attestation frequency. The endpoint `GET /attestations/questions?frequency={ANNUAL|QUARTERLY}` filters appropriately.

**Clarification Needed**: Explain that when a model owner views an attestation form, they only see questions matching their attestation frequency (determined by scheduling rules). A model owner attesting quarterly sees QUARTERLY and BOTH questions; annual attesters see ANNUAL and BOTH.

---

### 2. Auto-Accept Criteria - Linked Changes

**Location**: Section "For Reviewers" > "Auto-Accepted Attestations"

**User Guide Says**:

* "All questions are answered 'Yes'"
* "No optional comments are provided"
* "No linked inventory changes"

**Implementation** (`/api/app/api/attestations.py` lines 130-153 and 973-983):

```python
def is_clean_attestation(responses: list, decision_comment: Optional[str]) -> bool:
    all_yes = all(r.answer is True for r in responses)
    has_response_comments = any(r.comment and r.comment.strip() for r in responses)
    if decision_comment and decision_comment.strip():
        return False
    return all_yes and not has_response_comments

# Later in submit_attestation:
if auto_accept:
    linked_changes_count = db.query(AttestationChangeLink).filter(...).count()
    if linked_changes_count > 0:
        auto_accept = False

```

**Finding**: The documentation is accurate. The only clarification might be that the check for linked changes happens after the initial "clean" check.

---

### 3. Bulk Attestation - All Questions Must Be Answered

**Location**: Section "Bulk Attestation" > "Important Notes"

**Clarification Needed**: The guide should emphasize that bulk attestation requires all questions to have boolean (Yes/No) answers - partial/null answers are only allowed in drafts, not submissions.

**Implementation** (`/api/app/api/attestations.py` lines 3203-3210):

```python
for response in submit_in.responses:
    if response.answer is None:
        raise HTTPException(
            status_code=400,
            detail="All questions must have a Yes or No answer"
        )

```

---

### 4. Cycle Cannot Be Updated After Opening

**Location**: Section "For Administrators" > "Creating a New Cycle" and FAQ

**Implementation**: Once a cycle is OPEN, it cannot be updated (`/api/app/api/attestations.py` lines 398-417):

```python
if cycle.status != AttestationCycleStatus.PENDING.value:
    raise HTTPException(
        status_code=400,
        detail="Cannot update cycle after it has been opened"
    )

```

**FAQ Says**: "The submission due date cannot be changed after the cycle is opened."

**Clarification**: The FAQ is slightly misleading - ALL cycle fields (name, period dates, notes) cannot be changed after opening, not just the due date.

---

### 5. Dashboard Stats Endpoint

**Location**: Not documented

**Implementation**: `GET /attestations/dashboard/stats` provides aggregated statistics for admin dashboard:

* pending_count
* submitted_count
* overdue_count
* pending_changes (count of all linked changes)
* active_cycles

**Recommendation**: Document this endpoint if it's relevant for users or integrations.

---

## API Endpoint Reference

### Cycles

* `GET /attestations/cycles` - List all cycles
* `POST /attestations/cycles` - Create new cycle (Admin)
* `GET /attestations/cycles/{cycle_id}` - Get cycle details
* `PATCH /attestations/cycles/{cycle_id}` - Update cycle (Admin, only when PENDING)
* `POST /attestations/cycles/{cycle_id}/open` - Open cycle (Admin)
* `POST /attestations/cycles/{cycle_id}/close?force={bool}` - Close cycle (Admin)
* `GET /attestations/cycles/reminder` - Check if reminder should show (Admin)

### Records

* `GET /attestations/my-attestations` - Get current user's attestations
* `GET /attestations/my-upcoming` - Get dashboard widget data
* `GET /attestations/records` - List all records (Admin/Validator)
* `GET /attestations/records/{attestation_id}` - Get record details
* `POST /attestations/records/{attestation_id}/submit` - Submit attestation
* `POST /attestations/records/{attestation_id}/accept` - Accept (Admin)
* `POST /attestations/records/{attestation_id}/reject` - Reject (Admin)

### Evidence

* `POST /attestations/records/{attestation_id}/evidence` - Add evidence
* `DELETE /attestations/evidence/{evidence_id}` - Remove evidence

---

## Conclusion

The user guide is well-written and covers most functionality. Priority updates should be:

1. **High Priority**: Document the delegation feature for attestations.
2. **Medium Priority**: Add `MODEL_VERSION` to linked change types.
3. **Medium Priority**: Document the Linked Changes tab functionality.
4. **Low Priority**: Clarify `ADMIN_REVIEW` status usage.
5. **Low Priority**: Add reports documentation.


This review document is now cleaned and properly formatted for Markdown compatibility. I have corrected the spacing, ensured header consistency, and optimized the table layouts for better readability.

---

# Review: USER_GUIDE_MODEL_EXCEPTIONS.md

**Review Date**: 2026-01-05

**Reviewed Against**: Current codebase implementation

**Status**: Documentation generally accurate with minor clarifications needed

---

## Summary

The user guide is well-structured and accurately describes the Model Exceptions feature. The documentation aligns closely with the implemented functionality in both the backend API and frontend components. A few minor omissions and clarifications are identified below.

---

## Material Omissions

### 1. Manual Exception Creation Feature Not Fully Documented

**Finding**: The user guide mentions in Section 10 (Role-Based Access) that Administrators can "Create exceptions manually" but does not provide detailed instructions on how to do this.

**Current Implementation**:

* `POST /exceptions/` - Creates a manual exception (Admin only)
* **Frontend**: "Create Exception" button in both `ExceptionsReportPage.tsx` and `ModelExceptionsTab.tsx`
* **Statuses**: Supports setting initial status as either `OPEN` or `ACKNOWLEDGED`
* **Requirements**: `model_id`, `exception_type`, `description` (min 10 characters)
* **Optional**: `acknowledgment_notes` (when creating in `ACKNOWLEDGED` status)

**Recommendation**: Add a new section documenting the manual creation process:

1. Navigate to the Model Exceptions report page (or Model Details -> Exceptions tab).
2. Click **Create Exception** button (Admin only).
3. Search and select the model.
4. Choose exception type and enter description (minimum 10 characters).
5. Optionally create as already **ACKNOWLEDGED**.
6. Click **Create**.

### 2. Model-Specific Detection Endpoint Not Documented

**Finding**: Documentation mentions "Detect All Exceptions" but not the ability to scan individual models.

**Current Implementation**:

* `POST /exceptions/detect/{model_id}` - Runs detection for a specific model (Admin only).
* Returns the same `DetectionResponse` with counts by type.

**Recommendation**: Document this capability for API consumers or if exposed in the UI.

### 3. Exception Badge Count Behavior

**Finding**: Section 5 states the badge shows "OPEN" exceptions only. The implementation includes a status filter showing all non-closed statuses by default.

**Current Implementation (`ModelExceptionsTab.tsx`)**:

* **Default behavior**: Shows `OPEN` and `ACKNOWLEDGED` (excludes `CLOSED`).
* The API endpoint `/exceptions/model/{model_id}` uses `include_closed=false` by default.

---

## Important Inconsistencies

### 1. Navigation Path Discrepancy

**Documentation States**:

> "In the left navigation, click **Model Exceptions**"

**Actual Implementation**:

* **Path**: Under "Reports" section: `/reports/exceptions`
* **Menu Text**: "Model Exceptions" (nested under Reports).
* **Permission**: Only visible to users with `canManageValidations`.

**Recommendation**: Update to: *"In the left navigation, under the **Reports** section, click **Model Exceptions**."*

### 2. Access Control Roles

**Documentation States**:

> "Admin / Validator / Global Approver / Regional Approver"

**Actual Implementation**:

* Uses `apply_exception_rls()` for Row-Level Security.
* Uses `is_admin()` check for write operations.

**Recommendation**: Verify that the RLS implementation in `app.core.rls` explicitly grants these four roles organization-wide visibility.

---

## Key Clarifications Needed

### 1. Type 1 Exception Detection Timing

**Documentation States**:

> "Auto-closure is evaluated when results are entered/recorded (it is not tied to cycle approval)"

**Actual Implementation (`exception_detection.py`)**:

* **Detection**: Only considers results from `APPROVED` cycles.
* **Auto-closure**: Triggers immediately when a `GREEN`/`YELLOW` result is recorded (pre-approval).

**Recommendation**: Separate these behaviors in the text to avoid confusion.

### 2. API Endpoint Reference

| Endpoint | Method | Description |
| --- | --- | --- |
| `/exceptions/` | GET | List exceptions (paginated) |
| `/exceptions/` | POST | Create manual exception (Admin) |
| `/exceptions/summary` | GET | Get summary statistics |
| `/exceptions/{exception_id}/acknowledge` | POST | Acknowledge exception (Admin) |
| `/exceptions/detect-all` | POST | Detect for all active models (Admin) |

---

## Verification Checklist

| Feature | Documentation | Implementation | Match |
| --- | --- | --- | --- |
| Exception Types (3) | Yes | Yes | OK |
| Exception Statuses | Yes | Yes | OK |
| Exception Code Format | Yes | Yes | OK |
| Closure Narrative (min 10 chars) | Yes | Yes | OK |
| Type 1 Auto-close (GREEN/YELLOW) | Yes | Yes | OK |
| CSV Export | Yes | Yes | OK |

---

## Conclusion

The guide is comprehensive, but requires four primary updates:

1. **Manual Creation**: Document the Admin "Create Exception" workflow.
2. **Navigation**: Correct the path to the Reports section.
3. **Timing**: Clarify that Detection requires Approval, while Auto-close does not.
4. **Filters**: Note that the default view includes both Open and Acknowledged statuses.

Would you like me to generate the specific Markdown text for the new **Manual Exception Creation** section to be inserted into the guide?
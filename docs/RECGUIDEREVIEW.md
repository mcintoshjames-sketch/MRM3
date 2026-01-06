# User Guide Review: Model Recommendations

**Review Date:** 2026-01-05

This document identifies material omissions, important inconsistencies, and key clarifications needed between the User Guide (`docs/USER_GUIDE_RECOMMENDATIONS.md`) and the current codebase implementation.

---

## 1. Material Omissions

### 1.1 Missing Workflow States

The User Guide documents 7 workflow states, but the actual implementation in `api/app/seed.py` includes 12 distinct states.

**Workflow State Mapping:**

| Code | Label | Missing from Guide |
| --- | --- | --- |
| `REC_DRAFT` | Draft | No |
| `REC_PENDING_RESPONSE` | Pending Response | No |
| `REC_PENDING_ACKNOWLEDGEMENT` | Pending Acknowledgement | No |
| `REC_IN_REBUTTAL` | **In Rebuttal** | **YES** |
| `REC_PENDING_ACTION_PLAN` | **Pending Action Plan** | **YES** |
| `REC_PENDING_VALIDATOR_REVIEW` | **Pending Validator Review** | **YES** |
| `REC_OPEN` | Open | No |
| `REC_REWORK_REQUIRED` | Rework Required | No |
| `REC_PENDING_CLOSURE_REVIEW` | Pending Closure Review | No |
| `REC_PENDING_APPROVAL` | Pending Final Approval | No |
| `REC_CLOSED` | Closed | No |
| `REC_DROPPED` | Dropped | No |

**Recommendation:** Add a complete workflow state diagram including:

* **In Rebuttal**: Status when developer submits a rebuttal awaiting validator review.
* **Pending Action Plan**: Status after rebuttal is overridden (one-strike rule applied).
* **Pending Validator Review**: Status when action plan is submitted awaiting validator approval.

### 1.2 Missing "Skip Action Plan" Feature

The implementation includes a "Skip Action Plan" feature for low-priority (Consideration) recommendations.

* **Logic:** When action plan is not required (configured per-priority), the developer can skip directly from `REC_PENDING_RESPONSE` to `REC_PENDING_VALIDATOR_REVIEW`.
* **Endpoints:** `POST /recommendations/{id}/skip-action-plan` and `GET /recommendations/{id}/can-skip-action-plan`.

### 1.3 Missing "Decline Acknowledgement" Feature

From `REC_PENDING_ACKNOWLEDGEMENT`, a developer can decline (with reason), which transitions the record back to `REC_PENDING_VALIDATOR_REVIEW` for reconsideration.

### 1.4 Missing Timeframe Configuration Details

The guide incorrectly implies timeframe calculation is based only on `max_days`. It is actually a **three-dimensional matrix**:

1. **Recommendation Priority** (High, Medium, Low, Consideration)
2. **Model Risk Tier** (Tier 1, 2, 3, 4)
3. **Model Usage Frequency** (Daily, Monthly, Quarterly, Annually)

### 1.5 Missing API Endpoint Documentation

While the guide is functional, technical users require visibility into the following transition endpoints:

| Endpoint | Action | Transition |
| --- | --- | --- |
| `/submit` | Submit to Developer | `DRAFT`  `PENDING_RESPONSE` |
| `/rebuttal` | Submit Rebuttal | `PENDING_RESPONSE`  `IN_REBUTTAL` |
| `/finalize` | Finalize Action Plan | `PEND_VAL_REVIEW`  `PEND_ACK` |
| `/acknowledge` | Acknowledge | `PEND_ACK`  `OPEN` |
| `/void` | Void (Admin Only) | Voids specific approval requirements |

---

## 2. Important Inconsistencies

### 2.1 Workflow Terminology Discrepancy

* **Guide:** States "Finalize & Send" moves a recommendation to **Pending Response**.
* **Implementation:** The UI button "Finalize & Send" calls `submitToDeveloper()`. The word "Finalize" is reserved in the API for moving from Validator Review to Acknowledgement.
* **Fix:** Rename guide terminology to "Submit to Developer."

### 2.2 Rebuttal Flow Terminology

* **Guide:** Says an overridden rebuttal moves directly to "requiring an action plan."
* **Implementation:** It moves to an intermediate state `REC_PENDING_ACTION_PLAN`.

### 2.3 Evidence Links vs. URL Only

* **Guide:** Suggests only URLs are supported.
* **Implementation:** The `ClosureEvidence` model supports URLs **and** absolute file paths, along with metadata like `file_size_bytes` and `file_type`.

---

## 3. Key Clarifications Needed

### 3.1 Role Clarification for Editing

The implementation allows editing in more states than documented, but with different permissions:

* **Full Edit:** `DRAFT`, `PENDING_RESPONSE`, `PENDING_VALIDATOR_REVIEW`.
* **Limited Edit** (Assignee/Date only): `PENDING_ACKNOWLEDGEMENT`, `OPEN`, `REWORK_REQUIRED`.

### 3.2 Regional Override Logic

The resolution logic follows a **"Most Restrictive Wins"** principle:

1. If **ANY** regional override requires an action plan, it is required.
2. If **ALL** overrides say "False," it is not required.
3. `NULL` values inherit from the base configuration.

### 3.3 Task Completion Validation

The system validates that all tasks are `COMPLETED` or `TASK_COMPLETED` specifically at the moment of **submitting for closure**, not during the earlier action plan phases.

---

## 4. Missing Edge Cases

### 4.1 Rebuttal "One-Strike" Rule

The code enforces that if a rebuttal was previously `OVERRIDE`, the system blocks any further rebuttal attempts regardless of the current status.

### 4.2 Approval Reset on Rejection

**Crucial Omission:** When an approval is rejected, **ALL** previously granted approvals for that recommendation are reset to `PENDING` and the status returns to `REWORK_REQUIRED`.

---

## Summary of Findings

| Category | Count |
| --- | --- |
| Material Omissions | 6 |
| Important Inconsistencies | 4 |
| Key Clarifications Needed | 5 |
| Missing Edge Cases | 2 |

**Priority Action:** Update the documentation to include the 12-state workflow diagram and the "Most Restrictive Wins" logic for regional overrides.

Would you like me to draft the specific "Most Restrictive Wins" logic section for the updated User Guide?
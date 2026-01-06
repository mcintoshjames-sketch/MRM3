# Review: Model Inventory User Guide

**Document Reviewed:** `/docs/USER_GUIDE_MODEL_INVENTORY.md`
**Review Date:** 2026-01-05
**Reviewer:** Gemini (as Claude Code)

---

## Summary

This review compares the Model Inventory User Guide against the current codebase implementation. The document is generally accurate and comprehensive, but several material omissions, inconsistencies, and clarifications have been identified.

---

## 1. Material Omissions

### 1.1 Model Submission - Missing Required Fields

**Location:** Section "Submitting a New Model Record"

**Issue:** The documentation lists `Usage Frequency` as the only additional required field beyond basic model information, but the code reveals additional required fields:

**Code Reference:** `/api/app/schemas/model.py` (ModelCreate schema)

* `description` is **required** (with validation that it cannot be blank).
* `initial_implementation_date` is **required**.
* `developer_id` is **required for In-House models**.

**Recommendation:** Update the required fields table as follows:

| Field | Description | Required |
| --- | --- | --- |
| **Description** | Purpose and functionality of the model | Yes |
| **Initial Implementation Date** | First production deployment date | Yes |
| **Developer** | Required for In-House development type | Conditional |

### 1.2 Missing "Model External ID" Field

**Location:** Section "Editable (Mutable) Fields"

**Issue:** The documentation mentions "Model ID (External)," but the code shows this field does not exist in the Model schema. There is no `model_id_external` or `external_id` in the database model.

### 1.3 Missing Shared Developer Field

**Location:** Section "Editable (Mutable) Fields"

**Issue:** The documentation lists "Shared Owner" but omits "Shared Developer" which exists in the codebase.

**Code Reference:** `/api/app/models/model.py`

```python
shared_developer_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True,
    comment="Optional co-developer for shared development scenarios")

```

### 1.4 Missing "Ownership Type" and "Regulatory Categories"

**Location:** Section "Editable (Mutable) Fields"

**Issue:** Two significant taxonomy-driven fields are missing from the documentation:

* `ownership_type_id`: Classification for ownership.
* `regulatory_categories`: Many-to-many relationship for regulatory regimes (CCAR/DFAST, Basel, etc.).

### 1.5 Missing Non-Model/MRSA Classification

**Location:** General

**Issue:** The codebase supports a significant classification system for non-model tools that requires oversight. This is entirely undocumented in the guide.

**Code Reference:** `/api/app/models/model.py`

* `is_model`: Boolean for actual models vs. tools.
* `is_mrsa`: True for Model Risk-Sensitive Applications.
* `mrsa_risk_level_id` / `mrsa_risk_rationale`: Supporting fields for MRSA.

---

## 2. Important Inconsistencies

### 2.1 Inherent Risk Matrix - Inconsistent Results

**Location:** Section "Inherent Risk Matrix"

**Issue:** The documented matrix uses a 5-tier scale, whereas the code implements a 4-tier scale with different logic.

**Matrix Comparison:**

| Quantitative / Qualitative | Code Result | Documentation Says | Match? |
| --- | --- | --- | --- |
| **HIGH / HIGH** | HIGH | Critical | ❌ No |
| **HIGH / MEDIUM** | MEDIUM | High | ❌ No |
| **HIGH / LOW** | LOW | Medium | ❌ No |
| **MEDIUM / HIGH** | MEDIUM | High | ❌ No |
| **LOW / HIGH** | LOW | Medium | ❌ No |
| **LOW / LOW** | VERY_LOW | Very Low | ✅ Yes |

### 2.2 Validation Workflow States

**Location:** Section "Approval Status (Validation-Based)"

**Issue:** Documentation only mentions 5 stages. The code defines 8 primary states plus a revision state.

**Required Update:** Add INTAKE, CANCELLED, ON_HOLD, and REVISION to the workflow documentation.

### 2.3 Decommissioning Approval Workflow

**Location:** Section "Model Decommissioning - Approval Workflow"

**Issue:** The code includes `VALIDATOR_APPROVED` and `WITHDRAWN` states which are missing from the guide's linear workflow.

---

## 3. Key Clarifications Needed

* **3.1 Score Thresholds:** Clarify as: `Score >= 2.1: HIGH`; `1.6 <= Score < 2.1: MEDIUM`; `Score < 1.6: LOW`.
* **3.2 Weight Snapshots:** Explain that weights are "snapshotted" at assessment time and do not change if global weights are updated later.
* **3.3 Database Constraints:** Note that "Critical" limitations **must** have a user awareness description or the record will fail to save.
* **3.4 PDF Export:** Add the Risk Assessment PDF export capability to the "Exporting Data" section.

---

## 4. Recommendations Summary

| Priority | Action Item | Component |
| --- | --- | --- |
| **P1 - High** | Fix Inherent Risk Matrix to match `risk_calculation.py` | Risk Engine |
| **P1 - High** | Update required fields (Description, Implementation Date) | Model Submission |
| **P1 - High** | Correct Status values (Add `NULL`/Approved and `rejected`) | Workflow |
| **P2 - Med** | Document MRSA / Non-Model classification logic | Governance |
| **P2 - Med** | Add Shared Developer to editable fields documentation | Model Details |
| **P3 - Low** | Clarify "Substantive" vs "Intake" validation stages | Workflow |

---

## Appendix: File References

| Component | File Path |
| --- | --- |
| Model ORM | `/api/app/models/model.py` |
| Risk Calculation | `/api/app/core/risk_calculation.py` |
| Decommissioning | `/api/app/models/decommissioning.py` |
| Validation API | `/api/app/api/validation_workflow.py` |

Would you like me to generate the specific Markdown text for the **MRSA Classification** section so you can insert it into the guide?
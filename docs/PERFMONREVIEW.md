# Performance Monitoring User Guide Review

**Review Date:** 2026-01-05

**Reviewer:** Code Analysis Tool

**Document Reviewed:** `/docs/USER_GUIDE_PERFORMANCE_MONITORING.md`

---

## Summary

This review compares the Performance Monitoring User Guide against the current codebase implementation. The guide is generally accurate and comprehensive. Below are findings organized by category.

---

## 1. Material Omissions (Features in Code Not Documented)

### 1.1 PDF Report Generation

**Finding:** The API includes a PDF report generation endpoint that is not documented in the user guide.

**Code Reference:**

* `api/app/api/monitoring.py` line 5755: `@router.get("/monitoring/cycles/{cycle_id}/report/pdf")`

**Endpoint Details:**

* **Path:** `GET /monitoring/cycles/{cycle_id}/report/pdf`
* **Parameters:**
* `include_trends` (bool, default: True) - Whether to include trend charts
* `trend_periods` (int, default: 4) - Number of historical cycles for trends


* **Features:** Cover page, Executive summary, Detailed results table, Breach analysis, and Time-series trend charts.
* **Access:** Restricted to `PENDING_APPROVAL` or `APPROVED` cycles only.

**Recommendation:** Add a section or appendix documenting the PDF report generation capability.

### 1.2 Cycle Export to CSV

**Finding:** The API includes a cycle results export endpoint that is briefly mentioned but not fully documented.

**Code Reference:** `api/app/api/monitoring.py` line 5660: `@router.get("/monitoring/plans/{plan_id}/cycles/{cycle_id}/export")`

**Recommendation:** Expand the "Exporting Data" section to document the full CSV export capabilities.

### 1.3 Version Export Functionality

**Finding:** Plan versions can be exported, which is not mentioned in the guide.

**Code Reference:** `api/app/api/monitoring.py` line 1950: `@router.get("/monitoring/plans/{plan_id}/versions/{version_id}/export")`

**Recommendation:** Document the version export capability in the Plan Versioning section.

### 1.4 Plan Deactivation Summary and Options

**Finding:** Before deactivating a plan, the system provides a summary of pending items and allows cleanup options.

**Code Reference:** `api/app/api/monitoring.py` line 904-955.

**Recommendation:** Add documentation about the deactivation workflow, specifically the pre-deactivation summary and options to cancel pending approvals.

### 1.5 Advance Cycle Endpoint

**Finding:** There is an endpoint to manually advance a plan to its next cycle.

**Code Reference:** `api/app/api/monitoring.py` line 2366: `@router.post("/monitoring/plans/{plan_id}/advance-cycle")`

**Recommendation:** Document this administrative capability.

### 1.6 Breach Justification Enforcement

**Finding:** The system enforces that all **RED** results must have narratives before allowing transition to `PENDING_APPROVAL`.

**Code Reference:** `api/app/api/monitoring.py` line 4873-4904.

**Recommendation:** Clarify that this is programmatically enforced and document the error response format.

---

## 2. Important Inconsistencies

### 2.1 Outcome Values (UNCONFIGURED)

**Finding:** Appendix A lists outcomes (GREEN, YELLOW, RED, N/A) but misses `UNCONFIGURED`.

**Code Reference:** `api/app/api/monitoring.py` line 2945.

**Recommendation:** Add `UNCONFIGURED` to the Outcome Values table in Appendix A.

### 2.2 Status Enum Case Sensitivity

**Finding:** Code uses uppercase (e.g., `DATA_COLLECTION`), while the guide uses mixed case.

**Recommendation:** Ensure the guide consistently uses uppercase status codes to match API responses.

### 2.3 Hold/Postpone Endpoint Path

**Finding:** The guide lists these as separate actions, but the API uses a single endpoint: `/monitoring/cycles/{cycle_id}/postpone`.

**Recommendation:** Clarify that `indefinite_hold: true` creates a "Hold," while `false` with a date creates an "Extension."

---

## 3. Key Clarifications Needed

### 3.1 KPM Category vs. Evaluation Types

**Clarification Needed:** Distinguish between:

* **KPM Category Type:** QUANTITATIVE or QUALITATIVE (display grouping).
* **KPM Evaluation Type:** QUANTITATIVE (numeric), QUALITATIVE (judgment), or OUTCOME_ONLY (direct selection).

### 3.2 Outcome Calculation Logic

**Actual Logic Order:**

1. Check `UNCONFIGURED`.
2. Check **RED** thresholds (Min/Max).
3. Check **YELLOW** thresholds (Min/Max).
4. Default to **GREEN**.

### 3.3 Admin Proxy Approval Evidence

**Finding:** Admins **must** provide `approval_evidence` when approving on behalf of others.

**Recommendation:** Emphasize that this field is mandatory, not optional, for proxy approvals.

---

## 4. API Endpoint Reference

### Plan Workflow

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/monitoring/plans/{plan_id}/advance-cycle` | Manually advance to next cycle |
| `GET` | `/monitoring/plans/{plan_id}/deactivation-summary` | Pre-deactivation check |
| `POST` | `/monitoring/cycles/{cycle_id}/postpone` | Extend due date or place on hold |

### Reporting & Export

* `GET /monitoring/metrics/{plan_metric_id}/trend` - Get metric trend data
* `GET /monitoring/plans/{plan_id}/cycles/{cycle_id}/export` - Export cycle results
* `GET /monitoring/cycles/{cycle_id}/report/pdf` - Generate PDF report

---

## 5. Conclusion

The Performance Monitoring User Guide is largely accurate. The main areas for improvement are documenting the **PDF Report Generation**, the **Deactivation Workflow**, and the **UNCONFIGURED** outcome status.

Would you like me to generate the specific Markdown text for the missing "PDF Report Generation" section so you can paste it directly into the user guide?
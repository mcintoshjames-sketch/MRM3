The provided Markdown had several issues: escaped newlines (`\n`) preventing proper rendering, inconsistent spacing in tables, and minor syntax errors in code blocks. I have cleaned up the document to ensure it renders correctly in any standard Markdown viewer.

---

# Review: USER_GUIDE_MRSA_IRP.md

**Review Date:** 2026-01-05

**Reviewer:** Claude Opus 4.5 (automated review)

**Document Reviewed:** `/docs/USER_GUIDE_MRSA_IRP.md`

---

## Executive Summary

This review compares the User Guide for MRSA and IRP Management against the current codebase. The guide is largely accurate and comprehensive. However, several inconsistencies and omissions were identified that should be addressed to ensure documentation accuracy.

**Overall Assessment:** The documentation is well-structured and covers most functionality. Key areas needing attention include:

* Missing documentation for the "My MRSA Reviews" page for non-admin users
* Route path and navigation clarifications
* Exception management workflow details

---

## 1. Material Omissions

### 1.1 Missing Page: "My MRSA Reviews" for Non-Admin Users

**Finding:** The user guide does not document the "My MRSA Reviews" page (`/my-mrsa-reviews`) which is available to all users (including non-admins like Model Owners and Validators).

**Evidence:**

* Frontend component exists at: `web/src/pages/MyMRSAReviewsPage.tsx`
* Route is defined in `web/src/App.tsx`
* This page allows users to track MRSA review status for MRSAs they own, develop, or support as a delegate

**Recommendation:** Add a new section documenting:

* **Access:** Available to all authenticated users
* **Purpose:** Track MRSA review status for user's own MRSAs
* **Functionality:** Uses the same `MRSAReviewDashboardWidget` component but filtered to user's MRSAs
* **Navigation:** Should mention this in the Model Owner Workflow section

### 1.2 Row-Level Security for IRP Access

**Finding:** The user guide does not document that non-admin users can view IRPs and IRP details if they have access to at least one MRSA covered by that IRP.

**Evidence:**

* `api/app/api/irp.py` implements RLS via `_get_accessible_mrsa_ids()` and `_require_irp_access()`
* Non-admin users can view IRP detail page but only see MRSAs they have access to
* `web/src/pages/IRPDetailPage.tsx` shows different back link based on role

**Recommendation:** Add documentation explaining that:

* Non-admins can navigate to `/irps/:id` (IRP detail page) if they have access to a covered MRSA
* The "Covered MRSAs" tab will only show MRSAs the user has access to
* The IRP list page (`/irps`) is admin-only but IRP detail pages have broader read access

### 1.3 Missing "requires_irp" Field on Taxonomy Values

**Finding:** The guide mentions that risk levels determine IRP requirements, but does not document that this is controlled by the `requires_irp` field on `TaxonomyValue`.

**Evidence:**

* `api/app/models/taxonomy.py` line 65-68: `requires_irp` field on `TaxonomyValue`
* Used in coverage check: `api/app/api/irp.py` line 736: `mrsa.mrsa_risk_level.requires_irp`
* Seed data sets this flag: `api/app/seed.py` line 573: `"requires_irp": True`

**Recommendation:** Add technical note in Appendix explaining:

* The `requires_irp` flag on MRSA Risk Level taxonomy values controls whether IRP coverage is required
* Administrators can add custom risk levels and set this flag via Taxonomy management

### 1.4 Missing Exception Management API Documentation

**Finding:** The guide mentions review exceptions but does not document the full exception management API.

**Evidence:**

* API endpoints exist in `api/app/api/mrsa_review_policy.py`:
* `GET /mrsa-review-exceptions/` - List all exceptions
* `GET /mrsa-review-exceptions/{mrsa_id}` - Get exception for specific MRSA
* `POST /mrsa-review-exceptions/` - Create exception (Admin only)
* `PATCH /mrsa-review-exceptions/{exception_id}` - Update/revoke exception



**Recommendation:** Add a section documenting exception management:

* How to create review due date exceptions
* Required fields: `mrsa_id`, `override_due_date`, `reason`
* Admin-only access for exception management
* How exceptions affect review status calculations

---

## 2. Important Inconsistencies

### 2.1 Default Warning Days Value Discrepancy

**Finding:** Potential discrepancy in default warning days value.

**Evidence:**

* User Guide Section 5: "Default High-Risk Policy: Frequency 24 months, Initial Review 3 months, Warning **90** days"
* `api/app/schemas/mrsa_review_policy.py` line 33: `warning_days: int = 30` (schema default)
* Frontend form in `MRSAReviewPoliciesPage.tsx` lines 36-39 uses 90 days as default

**Recommendation:** Verify which default is authoritative. The schema default is 30 days but UI form defaults to 90 days. Update documentation to match the actual seeded policy values.

### 2.2 Navigation Path for MRSA Review Policies

**Finding:** The guide states the path as "Configuration > Workflow & Policies > MRSA Review Policies" but this may not match the actual navigation.

**Evidence:**

* User Guide Section 5: "Go to **Configuration** > **Workflow & Policies** > **MRSA Review Policies**"
* The route `/mrsa-review-policies` exists and is accessible
* Actual sidebar navigation structure should be verified against `Layout.tsx`

**Recommendation:** Verify the actual navigation path in the sidebar and update documentation accordingly.

### 2.3 IRP List Columns - Missing Actions Column

**Finding:** The guide lists columns but omits the Actions column visible to admins.

**Evidence:**

* User Guide Section 4 lists: ID, Process Name, Contact, Status, MRSAs, Latest Review, Latest Certification
* `web/src/pages/IRPsPage.tsx` shows additional: Actions column (Edit/Delete for admins)

**Recommendation:** Update the table in Section 4 to include the "Actions" column (visible to Administrators only).

### 2.4 IRP Detail Back Link Behavior

**Finding:** The IRP detail page has different back link behavior based on user role.

**Evidence:**

* `web/src/pages/IRPDetailPage.tsx` lines 125-126:
```typescript
const backLink = canManageIrpsFlag ? '/irps' : '/my-mrsa-reviews';
const backLabel = canManageIrpsFlag ? 'IRPs' : 'My MRSA Reviews';

```


* Non-admins are directed to "My MRSA Reviews" page, not the IRP list

**Recommendation:** Document this navigation behavior to help users understand their context when viewing IRP details.

---

## 3. Key Clarifications Needed

### 3.1 MRSA-IRP Linking API Clarification

**Finding:** The guide states "MRSA coverage is managed separately from the MRSA detail page after IRP creation" but the API actually supports linking during IRP creation and update.

**Evidence:**

* `api/app/schemas/irp.py` lines 91 and 100: `IRPCreate` and `IRPUpdate` both have `mrsa_ids: Optional[List[int]]`
* `api/app/api/irp.py` handles MRSA linking in create and update endpoints

**Clarification Needed:** The guide should clarify that MRSAs **can** be linked during IRP creation via API, even if the current UI form doesn't expose it.

### 3.2 Validator Role Access Clarification

**Finding:** The guide states Validators can "participate in validation activities" but doesn't specify their exact access to IRP/MRSA features.

**Clarification Needed:** Be explicit that:

* Validators can view MRSAs and review status.
* Validators cannot access the `/irps` list page.
* Validators cannot add reviews or certifications.

---

## 4. API Endpoint Reference (Recommended Addition)

### IRP Management

| Endpoint | Method | Description | Access |
| --- | --- | --- | --- |
| `/irps/` | GET | List IRPs (filtered for non-admins) | All users |
| `/irps/` | POST | Create IRP | Admin only |
| `/irps/{irp_id}` | GET | Get IRP detail | All users* |
| `/irps/{irp_id}/reviews` | POST | Create review | Admin only |
| `/irps/mrsa-review-status` | GET | Get review status for all accessible MRSAs | All users |

**Non-admins must have access to at least one MRSA covered by the IRP.*

---

## 5. Frontend Route Reference (Recommended Addition)

| Route | Component | Access | Notes |
| --- | --- | --- | --- |
| `/irps` | IRPsPage | Admin only | IRP list with MRSA Review Status tab |
| `/irps/:id` | IRPDetailPage | All users* | Filtered view for non-admins |
| `/my-mrsa-reviews` | MyMRSAReviewsPage | All users | **NOT DOCUMENTED** |

---

## 6. Recommended Actions

### High Priority

1. **Add documentation for "My MRSA Reviews" page** (`/my-mrsa-reviews`).
2. **Clarify non-admin access to IRP detail pages**.
3. **Document MRSA review exception management workflow**.

### Medium Priority

4. Verify and update default warning days value (30 vs 90).
5. Update IRP list table to include Actions column.

---

## 7. Positive Observations

1. **IRP and MRSA definitions** are clear and correct.
2. **Review status definitions** (CURRENT, UPCOMING, OVERDUE, etc.) are accurate.
3. **Permission matrix** in Appendix E is largely accurate.

---

*This review was conducted by analyzing the codebase files in `/api/app/`, `/web/src/`, and comparing against the user guide documentation.*

Would you like me to generate a template for the missing "My MRSA Reviews" section to help you update the guide?
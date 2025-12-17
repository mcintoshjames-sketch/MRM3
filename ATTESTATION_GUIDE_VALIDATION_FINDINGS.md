# Attestation Guide Validation Findings (Guide vs Implementation)

*Date:* 2025-12-15

## Scope
This document validates **docs/ATTESTATION_USER_GUIDE.md** against the current implementation:
- Backend contract (enums + endpoints): `api/app/schemas/attestation.py`, `api/app/api/attestations.py`
- Frontend UX (primary pages): `web/src/pages/MyAttestationsPage.tsx`, `web/src/pages/AttestationDetailPage.tsx`, `web/src/pages/AttestationCyclesPage.tsx`, `web/src/pages/BulkAttestationPage.tsx`, `web/src/hooks/useBulkAttestation.ts`

It produces two outputs:
1) A **docs patch list** (what to change in the user guide so it is accurate today)
2) A **UX/code fix shortlist** (small, high-ROI changes to make the product match the intended UX)

---

## A) Docs Patch List (Recommended Updates to `docs/ATTESTATION_USER_GUIDE.md`)

### 1) Key Concepts → Attestation Cycle status
**Current guide:** cycle status described as *Pending/Open/Closed*.

**Implementation:** backend includes `UNDER_REVIEW` as a cycle status (`AttestationCycleStatusEnum`).

**Doc update:**
- Expand the cycle status description to: **PENDING → OPEN → UNDER_REVIEW → CLOSED**.
- Add a short note that `UNDER_REVIEW` is typically an **admin/reviewer workflow** state (i.e., cycle-level review/closure gating), even if the UI surfaces it minimally.

### 2) Key Concepts → Attestation Record status
**Current guide:** record status described as *Pending/Submitted/Accepted/Rejected*.

**Implementation:** backend includes `ADMIN_REVIEW` (`AttestationRecordStatusEnum`).

**Doc update:**
- Add `ADMIN_REVIEW` to the canonical record status list **or** explicitly state: “The UI displays a simplified set of statuses; the backend may use internal statuses such as `ADMIN_REVIEW`.”
- Recommend using the UI labels when communicating with owners (e.g., “Submitted – Pending Review”).

### 3) For Model Owners → Completing an Attestation → “Add supporting evidence”
**Current guide:** instructs owners to click **“Add Evidence”** and enter a URL + description.

**Implementation (frontend):** the Attestation Detail page does not currently render an “Add Evidence” UI (evidence types are defined in code, but no add/remove controls exist).

**Doc update (choose Option A):**
- **Option A (accurate today):** remove the “Click Add Evidence” step and replace with: “Evidence is not currently captured in the attestation form UI.”


### 4) For Model Owners → Completing an Attestation → “Make inventory changes” actions
**Current guide:** lists **Edit Model** and **Decommission Model** as the navigation buttons.

**Implementation (frontend):** the Attestation Detail page offers **three** change actions:
- Edit Model Details
- Submit Model Change (model version/change record)
- Decommission Model

**Doc update:**
- Update this section to list all three actions and match the visible button names (or close variants).
- Add one sentence clarifying what “Submit Model Change” means (a versioned change record / change submission).

### 5) For Model Owners → Urgency indicators
**Current guide:** shows a Green/Yellow/Red table.

**Implementation (frontend):** badges shown are:
- “Due Soon” when within 7 days
- “Overdue” when past due
- No explicit “Green/On track” badge for > 7 days

**Doc update:**
- Replace the table with the actual behavior (Due Soon / Overdue) and note that when a due date is > 7 days away, no urgency badge is shown.

### 6) For Model Owners → “If Your Attestation is Rejected”
**Current guide:** says it returns to “Pending” status.

**Implementation:** records can remain `REJECTED` and are editable/resubmittable (the UI supports resubmission while status is REJECTED).

**Doc update:**
- Change wording to: “Status becomes **Rejected**. You can edit your responses and resubmit.”
- Keep the “rejection reason shown in details” statement (the UI displays `review_comment`).

### 7) For Model Owners → “Can I save my attestation and finish later?” (FAQ)
**Current guide:** “responses are saved as you go.”

**Implementation (frontend):** no per-question save endpoint is called; responses are submitted at the end. (Bulk has draft autosave; individual attestation does not.)

**Doc update:**
- Update FAQ to: “Your responses are retained in the page while you’re working; they are not persisted to the server until you submit.”
- Optionally add: “If you refresh, you may lose in-progress changes.” (until a product change is made)

### 8) Bulk Attestation → Draft Mode wording
**Current guide:** says you can click “Save Draft” and drafts also auto-save.

**Implementation:** bulk drafts auto-save (debounced) and drafts are cleared on submit/close.

**Doc update:**
- Add one concrete sentence like: “Drafts auto-save a few seconds after changes; ‘Save Draft’ is optional for immediate persistence.”

### 9) For Administrators → Tabs list
**Current guide:** says the admin Attestations page has **seven tabs**.

**Implementation:** admin Attestations page includes **Linked Changes** as an additional tab.

**Doc update:**
- Update to **eight tabs** and include “Linked Changes”.

### 10) Coverage Targets & Compliance → “override if necessary”
**Current guide:** implies admins can override and close anyway.

**Implementation:** backend supports forcing close via API (`force` param), but the UI may not expose a “Force Close” action.

**Doc update:**
- Clarify whether “override” is currently available in the UI.
- If not, describe the operational path: either adjust targets or coordinate an admin/ops action (depending on policy).

---

## B) UX / Code Fix Shortlist (High-ROI Product Improvements)

### P0 — Status contract alignment (backend enums vs frontend types)
**Problem:** Backend includes `ADMIN_REVIEW` for records and `UNDER_REVIEW` for cycles; the UI currently types/labels a simplified set. This can cause confusion and type drift.

**Proposed change:**
- Update frontend types and badge rendering to handle `ADMIN_REVIEW` and `UNDER_REVIEW` safely.
- Decide on product semantics: either fully surface those states or map them to user-friendly labels.

**Acceptance criteria:**
- No runtime/type errors if backend returns `ADMIN_REVIEW` / `UNDER_REVIEW`.
- UI displays consistent labels and explanations for all statuses that can be returned.

### P1 — Force close cycles (with guardrails)
**Problem:** Backend supports force-closing cycles even with blocking gaps, but UI guidance implies an override exists.

**Proposed change:** Add an admin-only “Force Close” option when blocking gaps exist:
- Requires explicit confirmation
- Requires a reason (free text) to support auditability

**Acceptance criteria:**
- Force close is only visible to Admin.
- Submits `force=true` to the close endpoint and records the reason (if backend supports; otherwise include as audit log details or add field).
- UI clearly differentiates Close vs Force Close.



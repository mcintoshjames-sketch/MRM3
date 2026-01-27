# Model Governance UAT Use Cases and Tests (US Bank)

## Purpose
Provide a reusable UAT pack for a typical US bank model governance tool, mapped to the capabilities in this application. Each use case includes test steps, expected results, and screenshot evidence guidance. Use this document to run interactive UAT and log issues.

## Scope
- Model inventory and ownership
- Validation workflow and alerts
- Recommendations tracking
- Performance monitoring
- Exceptions and approvals
- Attestations
- IRP and MRSA review management
- Decommissioning
- Reports and audit trail

## Environment and Access
- Frontend: http://localhost:5174 (docker) or http://localhost:5173 (local dev)
- Backend: http://localhost:8001
- Default seeded users (from `api/app/seed.py`):
  - Admin: admin@example.com / admin123
  - Validator: validator@example.com / validator123
  - Model Owner: user@example.com / user123
  - Global Approver: globalapprover@example.com / approver123
  - Regional Approver: usapprover@example.com / approver123

## Evidence and Screenshot Capture
- Use a consistent naming scheme: `UAT-<test-id>-<step>.png`.
- **AI Execution**: Use the available screenshot tool or `node scripts/screenshot.js <url> <filename>` for static states.
- For modals or multi-step flows, capture the state immediately after the action completes.
- Save evidence under `screenshots/uat/` (create folder if needed).

## Execution Log
| Test ID | Status (Pass/Fail/Blocked) | Tester | Date | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| UAT-01.1 | Pass | Codex | 2025-12-28 | UAT-01.1-01-create-form.png; UAT-01.1-02-model-list.png; UAT-01.1-03-model-detail.png | Model created and visible in list/detail. |
| UAT-01.2 | Fail | Codex | 2025-12-29 | UAT-01.2-01-model-users.png; UAT-01.2-02-owner-view.png | Model Owner list did not show the assigned model after user assignment. |
| UAT-01.3 | Fail | Codex | 2025-12-28 | UAT-01.3-01-access-denied.png | No access-denied message observed for Model Owner. |
| UAT-02.1 | Pass | Codex | 2025-12-29 | UAT-02.1-01-version-create.png; UAT-02.1-02-version-history.png | Version created and visible in history. |
| UAT-03.1 | Fail | Codex | 2025-12-28 | UAT-03.1-01-create-validation.png; UAT-03.1-02-validation-list.png | Post-submit list view rendered blank; project visibility not confirmed. |
| UAT-03.2 | Fail | Codex | 2025-12-29 | UAT-03.2-00-admin-assignments.png; UAT-03.2-00-admin-assignments-list.png; UAT-03.2-01-validator-detail.png; UAT-03.2-02-status-change.png | Validator assignment did not persist (assignments remain 0), so validator status update actions were unavailable. |
| UAT-04.1 | Fail | Codex | 2025-12-28 | UAT-04.1-01-lead-time.png; UAT-04.1-02-out-of-order.png | Out-of-Order card did not show active filter state. |
| UAT-05.1 | Pass | Codex | 2025-12-28 | UAT-05.1-01-create-rec.png; UAT-05.1-02-rec-list.png | Recommendation created and visible in list. |
| UAT-05.2 | Blocked | Codex | 2025-12-29 | UAT-05.2-01-open-filter.png; UAT-05.2-02-overdue-filter.png; UAT-05.2-03-closed-rec.png; UAT-05.3-01-action-plan-missing.png | Filters toggled; open-only behavior after closing still blocked by missing action plan/rebuttal actions. |
| UAT-05.3 | Fail | Codex | 2025-12-29 | UAT-05.3-01-action-plan-missing.png | Model Owner cannot access Submit Action Plan/Rebuttal actions after acknowledgement. |
| UAT-06.1 | Pass | Codex | 2025-12-29 | UAT-06.1-01-plan-create.png; UAT-06.1-02-plan-detail.png | Plan created and detail page opened. |
| UAT-06.2 | Pass | Codex | 2025-12-29 | UAT-06.2-01-cycle-start.png; UAT-06.2-02-cycle-results.png | Cycle created and results visible in grid view. |
| UAT-06.3 | Pass | Codex | 2025-12-29 | UAT-06.3-02-breach-alert.png | RED result opens breach explanation panel. |
| UAT-07.1 | Pass | Codex | 2025-12-29 | UAT-07.1-01-exceptions-filter.png; UAT-07.1-02-exception-detail.png | Exception detail view opened successfully. |
| UAT-07.2 | Fail | Codex | 2025-12-28 | UAT-07.2-01-approver-dashboard.png | Approver dashboard loaded the login screen. |
| UAT-07.3 | Blocked | Codex | 2025-12-28 |  | Self-approval block not tested. |
| UAT-08.1 | Fail | Codex | 2025-12-28 | UAT-08.1-01-create-cycle.png; UAT-08.1-02-cycle-list.png | Cycle list screenshot blank; creation not verified. |
| UAT-08.2 | Pass | Codex | 2025-12-29 | UAT-08.2-01-attestation-form.png; UAT-08.2-02-attestation-submitted.png | Model owner submitted attestation successfully. |
| UAT-08.3 | Pass | Codex | 2025-12-29 | UAT-08.3-01-negative-attestation.png | Negative attestation submitted with required comment. |
| UAT-09.1 | Pass | Codex | 2025-12-29 | UAT-09.1-01-irp-create.png; UAT-09.1-02-irp-list.png | IRP created and visible in list. |
| UAT-09.2 | Pass | Codex | 2025-12-29 | UAT-09.2-01-irp-detail.png; UAT-09.2-02-mrsa-status.png | IRP review added and visible in detail. |
| UAT-10.1 | Blocked | Codex | 2025-12-29 | UAT-10.1-01-decom-form.png; UAT-10.1-02-decom-status.png | Last Production Date still not accepted; browser validation blocks submission. |
| UAT-10.2 | Pass | Codex | 2025-12-29 | UAT-10.2-01-pending-decom.png; UAT-10.2-02-decom-decision.png | Validator review submitted; status moved to VALIDATOR APPROVED. |
| UAT-11.1 | Pass | Codex | 2025-12-28 | UAT-11.1-01-pre-submission.png; UAT-11.1-02-missing-commentary.png | Card filters reflected in dropdowns. |
| UAT-11.2 | Pass | Codex | 2025-12-28 | UAT-11.2-01-ready-filter.png; UAT-11.2-02-pending-filter.png | Card filters toggled and view updated. |
| UAT-12.1 | Pass | Codex | 2025-12-29 | UAT-12.1-01-audit-filter.png; UAT-12.1-02-audit-entry.png | Audit log filtered by model shows create/update entries. |

## Use Cases and UAT Tests

### UC-01: Model Intake and Classification
**Business goal**: Register new models with required metadata, ownership, and classification.
**Primary roles**: Admin, Model Owner

**UAT-01.1 Create a new model**
- Steps:
  1. Login as Admin.
  2. Navigate to `Models` (/models).
  3. Click `+ Add Model`.
  4. Fill required fields using a unique name (e.g., `Model-Auto-{Timestamp}`) to avoid constraint errors.
  5. Save.
- Expected results:
  - Model appears in the list and detail page.
  - Required metadata is persisted.
- Evidence:
  - `UAT-01.1-01-create-form.png`
  - `UAT-01.1-02-model-list.png`
  - `UAT-01.1-03-model-detail.png`

**UAT-01.3 RBAC Negative Testing (Segregation of Duties)**
- Steps:
  1. Log in as Model Owner (user@example.com).
  2. Attempt to navigate to `/admin` or delete a model they do not own.
  3. Attempt to change the "Risk Tier" of a model (Admin only).
- Expected results:
  - User is redirected or sees a "403 Forbidden" / "Access Denied" message.
  - Critical fields remain unchanged.
- Evidence:
  - `UAT-01.3-01-access-denied.png`

**UAT-01.2 Assign model users and verify access**
- Steps:
  1. From the model detail page, add a user to the model (owner or contributor).
  2. Log out and log in as the Model Owner (user@example.com).
  3. Verify the model is visible and details render correctly.
- Expected results:
  - Assigned users can access the model.
  - Non-assigned users are restricted if RBAC is enforced.
- Evidence:
  - `UAT-01.2-01-model-users.png`
  - `UAT-01.2-02-owner-view.png`

### UC-02: Model Change and Version Governance
**Business goal**: Track model changes and version history for auditability.
**Primary roles**: Admin

**UAT-02.1 Create a model change record (version)**
- Steps:
  1. Open a model detail page.
  2. Create a new change record/version (if the UI exposes versioning controls).
  3. Verify the version appears in version history.
- Expected results:
  - New version is listed with metadata and timestamps.
- Evidence:
  - `UAT-02.1-01-version-create.png`
  - `UAT-02.1-02-version-history.png`

### UC-03: Validation Workflow
**Business goal**: Submit and manage validation projects with clear status transitions.
**Primary roles**: Admin, Validator

**UAT-03.1 Create a validation project (Independence Check)**
- Steps:
  1. Navigate to `Validations` (/validation-workflow).
  2. Click `+ New Validation Project`.
  3. Select a model, validation type, priority, and due dates.
  4. **Independence Check**: Verify that as an Admin/Validator, you can assign a specific Validator, but ensure Model Owners cannot self-assign or choose their own Validator (if testing as Owner).
  5. Save.
- Expected results:
  - The project appears in the list with correct status and metadata.
  - Validator assignment adheres to independence policy.
- Evidence:
  - `UAT-03.1-01-create-validation.png`
  - `UAT-03.1-02-validation-list.png`

**UAT-03.2 Validator updates status**
- Steps:
  1. Log in as Validator.
  2. Open the validation request and update status (e.g., Intake -> In Progress -> Complete).
  3. Save changes at each step.
- Expected results:
  - Status changes are visible to Admin and Validator.
  - Status history updates.
- Evidence:
  - `UAT-03.2-01-validator-detail.png`
  - `UAT-03.2-02-status-change.png`

### UC-04: Validation Alerts (Lead Time and Out-of-Order)
**Business goal**: Surface policy violations that require governance attention.
**Primary roles**: Admin

**UAT-04.1 Review validation alerts**
- Steps:
  1. Navigate to `Validation Alerts` (/validation-alerts).
  2. Toggle between Lead Time Violations and Out-of-Order tabs.
- Expected results:
  - Tab filters are mutually exclusive and filter the list.
  - Clear filters resets view.
- Evidence:
  - `UAT-04.1-01-lead-time.png`
  - `UAT-04.1-02-out-of-order.png`

### UC-05: Recommendations and Issues Tracking
**Business goal**: Capture and track remediation actions through closure.
**Primary roles**: Admin, Validator, Model Owner

**UAT-05.1 Create a recommendation**
- Steps:
  1. Navigate to `Recommendations` (/recommendations).
  2. Click `+ New Recommendation`.
  3. Set model, priority, category, target date, and assignee.
  4. Save.
- Expected results:
  - Recommendation appears in the list and detail page.
- Evidence:
  - `UAT-05.1-01-create-rec.png`
  - `UAT-05.1-02-rec-list.png`

**UAT-05.2 Validate filters and open-only behavior**
- Steps:
  1. Click `Total Open`, `Overdue`, and `High Priority` cards.
  2. Verify `Clear filters` resets the card filter.
  3. Open a recommendation and set status to Closed or Dropped.
  4. Confirm it no longer appears under `Total Open`.
- Expected results:
  - Cards are mutually exclusive and filter correctly.
  - Open-only excludes Closed/Dropped.
- Evidence:
  - `UAT-05.2-01-open-filter.png`
  - `UAT-05.2-02-overdue-filter.png`
  - `UAT-05.2-03-closed-rec.png`

**UAT-05.3 Finding Remediation & Rebuttal Workflow**
- Steps:
  1. Log in as Model Owner.
  2. Open a new Recommendation assigned to you.
  3. Submit a "Rebuttal" or "Action Plan" (do not just close it).
  4. Log in as Validator and review the Action Plan.
  5. Accept the plan to move status to "Open/In Progress".
- Expected results:
  - Status transitions: Pending -> Rebuttal/Action Plan -> Open.
  - Finding cannot be closed without an accepted plan.
- Evidence:
  - `UAT-05.3-01-action-plan-missing.png`

### UC-06: Performance Monitoring
**Business goal**: Establish monitoring plans and track cycles and results.
**Primary roles**: Admin

**UAT-06.1 Create a monitoring plan**
- Steps:
  1. Navigate to `Performance Monitoring` (/monitoring-plans).
  2. Create a plan (name, frequency, team, data provider).
  3. Add models and metrics if available.
- Expected results:
  - Plan appears in the list and detail page.
- Evidence:
  - `UAT-06.1-01-plan-create.png`
  - `UAT-06.1-02-plan-detail.png`

**UAT-06.2 Start a cycle and review results**
- Steps:
  1. Open the plan and start a cycle.
  2. Enter results (or use seeded data).
  3. Verify the cycle appears in the overview with correct status.
- Expected results:
  - Cycle status and results are visible in the overview.
- Evidence:
  - `UAT-06.2-01-cycle-start.png`
  - `UAT-06.2-02-cycle-results.png`

**UAT-06.3 Threshold Breach Alert**
- Steps:
  1. Open an active monitoring cycle.
  2. Enter a metric result that exceeds the defined "Red" threshold (e.g., if limit is <5%, enter 10%).
  3. Save the results.
- Expected results:
  - The system flags the result as "Red/Breach".
  - An alert or exception is generated (verify in Alerts or Exceptions tab).
- Evidence:
  - `UAT-06.3-02-breach-alert.png`

### UC-07: Exceptions and Approvals
**Business goal**: Review exceptions and approvals for governance oversight.
**Primary roles**: Admin, Approver

**UAT-07.1 Exceptions report filters**
- Steps:
  1. Navigate to `Model Exceptions` (/reports/exceptions).
  2. Apply filters (status, severity, model).
  3. Open an exception detail.
- Expected results:
  - Filters update the list.
  - Exception detail renders with evidence.
- Evidence:
  - `UAT-07.1-01-exceptions-filter.png`
  - `UAT-07.1-02-exception-detail.png`

**UAT-07.2 Approver dashboard workflow**
- Steps:
  1. Log in as Approver (globalapprover@example.com).
  2. Navigate to `Approver Dashboard` (/approver-dashboard).
  3. Review a pending approval and record a decision.
- Expected results:
  - Approval decision persists and status updates.
- Evidence:
  - `UAT-07.2-01-approver-dashboard.png`
  - `UAT-07.2-02-approval-decision.png`

**UAT-07.3 Verify Self-Approval Block (SoD)**
- Steps:
  1. Log in as a user who is both a Model Owner and an Approver (or temporarily assign roles).
  2. Submit a model change or decommissioning request as the Owner.
  3. Attempt to approve that specific request.
- Expected results:
  - The "Approve" button is disabled or hidden for the requester.
  - System enforces "Four Eyes" principle (Maker != Checker).
- Evidence:
  - `UAT-07.3-01-approval-blocked.png`

### UC-08: Attestation Management
**Business goal**: Collect periodic attestations and review responses.
**Primary roles**: Admin, Model Owner

**UAT-08.1 Create an attestation cycle**
- Steps:
  1. Navigate to `Attestation Management` (/attestations).
  2. Click `Create Cycle`, fill required fields, and save.
  3. Verify cycle appears in the list.
- Expected results:
  - Cycle appears and records are generated.
- Evidence:
  - `UAT-08.1-01-create-cycle.png`
  - `UAT-08.1-02-cycle-list.png`

**UAT-08.2 Model owner submits attestation**
- Steps:
  1. Log in as Model Owner (user@example.com).
  2. Navigate to `My Attestations` (/my-attestations).
  3. Open an attestation and submit responses.
- Expected results:
  - Status changes to Submitted.
- Evidence:
  - `UAT-08.2-01-attestation-form.png`
  - `UAT-08.2-02-attestation-submitted.png`

**UAT-08.3 Negative Attestation**
- Steps:
  1. Log in as Model Owner.
  2. Open an attestation request.
  3. Select "I do not attest" or "Attest with updates".
  4. Provide the required commentary/reasoning.
  5. Submit.
- Expected results:
  - Submission is accepted but flagged for review.
  - Status reflects the qualified attestation (e.g., "Submitted - With Updates").
- Evidence:
  - `UAT-08.3-01-negative-attestation.png`

### UC-09: IRP and MRSA Review Management
**Business goal**: Track Independent Review Processes and MRSA review status.
**Primary roles**: Admin

**UAT-09.1 Create an IRP**
- Steps:
  1. Navigate to `IRP Management` (/irps).
  2. Click `+ Add IRP` and fill required fields.
  3. Save and verify the IRP list updates.
- Expected results:
  - IRP appears in list with correct metadata.
- Evidence:
  - `UAT-09.1-01-irp-create.png`
  - `UAT-09.1-02-irp-list.png`

**UAT-09.2 Review MRSA status tab**
- Steps:
  1. Open an IRP detail page.
  2. Navigate to the MRSA Review Status tab.
  3. Create a review entry if supported.
- Expected results:
  - MRSA review status is visible and filterable.
- Evidence:
  - `UAT-09.2-01-irp-detail.png`
  - `UAT-09.2-02-mrsa-status.png`

### UC-10: Decommissioning Workflow
**Business goal**: Retire models with proper approvals and evidence.
**Primary roles**: Model Owner, Validator, Approver

**UAT-10.1 Submit decommissioning request**
- Steps:
  1. Open a model detail page.
  2. Click `Decommission` and submit a request with required fields.
- Expected results:
  - Request shows status `PENDING`.
- Evidence:
  - `UAT-10.1-01-decom-form.png`
  - `UAT-10.1-02-decom-status.png`

**UAT-10.2 Review pending decommissioning**
- Steps:
  1. Log in as Validator or Approver.
  2. Navigate to `Pending Decommissioning` (/pending-decommissioning).
  3. Review and record approval or rejection.
- Expected results:
  - Status updates and is visible in request history.
- Evidence:
  - `UAT-10.2-01-pending-decom.png`
  - `UAT-10.2-02-decom-decision.png`

### UC-11: Governance Reports
**Business goal**: Provide management reporting for overdue items and deployment readiness.
**Primary roles**: Admin

**UAT-11.1 Overdue revalidation report filters**
- Steps:
  1. Navigate to `Overdue Revalidation Report` (/reports/overdue-revalidation).
  2. Toggle Pre-Submission, Validation Overdue, Missing Commentary cards.
  3. Verify dropdown filters reflect the card state.
- Expected results:
  - Quick filters and dropdowns are consistent.
- Evidence:
  - `UAT-11.1-01-pre-submission.png`
  - `UAT-11.1-02-missing-commentary.png`

**UAT-11.2 Ready-to-deploy report filters**
- Steps:
  1. Navigate to `Ready to Deploy` (/reports/ready-to-deploy).
  2. Toggle Ready to Deploy and Pending Tasks cards.
- Expected results:
  - Cards filter the list and show clear status.
- Evidence:
  - `UAT-11.2-01-ready-filter.png`
  - `UAT-11.2-02-pending-filter.png`

### UC-12: Audit and Evidence Trail
**Business goal**: Ensure governance actions are captured for audit.
**Primary roles**: Admin, Validator

**UAT-12.1 Audit log verification**
- Steps:
  1. Navigate to `Audit Logs` (/audit).
  2. Filter by recent actions (model created, validation status change, recommendation closed).
- Expected results:
  - Audit records exist for key actions with actor and timestamp.
- Evidence:
  - `UAT-12.1-01-audit-filter.png`
  - `UAT-12.1-02-audit-entry.png`

## Issue Log
| Issue ID | Use Case | Test ID | Severity (Low/Med/High) | Description | Steps to Reproduce | Expected | Actual | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ISS-01 | UC-01 | UAT-01.3 | Med | Model Owner access denial not shown for Attestation Management | Login as user@example.com, navigate to /attestations | Access denied message or blocked route | Redirected to Models list without denial | UAT-01.3-01-access-denied.png | Open |
| ISS-02 | UC-03 | UAT-03.1 | Med | Validation list view rendered blank after submitting a project | Create validation project, submit, return to list | List shows new validation | List screenshot blank | UAT-03.1-02-validation-list.png | Open |
| ISS-03 | UC-04 | UAT-04.1 | Low | Out-of-Order Validations card did not activate | Open /validation-alerts, click Out-of-Order Validations | Card highlights and list filters | View remained on All Alerts | UAT-04.1-02-out-of-order.png | Open |
| ISS-04 | UC-07 | UAT-07.2 | High | Approver dashboard inaccessible after login | Login as globalapprover@example.com, go to /approver-dashboard | Approver Dashboard loads | Login screen displayed | UAT-07.2-01-approver-dashboard.png | Open |
| ISS-05 | UC-08 | UAT-08.1 | Med | Attestation cycle list view blank after creation | Create cycle, expect list refresh | Cycle list visible with new row | Page captured blank/white | UAT-08.1-02-cycle-list.png | Open |
| ISS-06 | UC-01 | UAT-01.2 | Med | Assigned Model Owner cannot see newly assigned model | Assign user@example.com to model, log in as Model Owner, search models | Assigned model visible in list | Assigned model not visible | UAT-01.2-02-owner-view.png | Open |
| ISS-07 | UC-03 | UAT-03.2 | High | Validator assignment does not persist on validation request | Admin adds validator assignment in request detail | Assignment appears in list and enables validator actions | Assignments remain 0 after save | UAT-03.2-00-admin-assignments-list.png | Open |
| ISS-08 | UC-05 | UAT-05.3 | High | Model Owner cannot submit action plan/rebuttal because action buttons never render | Create recommendation, finalize & send, login as Model Owner, open recommendation | Submit Action Plan/Rebuttal available after acknowledgement | No action buttons appear; remediation workflow blocked | UAT-05.3-01-action-plan-missing.png | Open |

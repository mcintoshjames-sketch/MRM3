# Monitoring Cycle Auto-Advance Refactor Plan

Goal
- Make event-driven auto-advance safe and predictable by aligning it with cycle completion and explicit postponement handling.
- Support simple deadline extensions without unnecessary status changes.
- Enforce plan creation with a required initial cycle period end date.
- Add cancellation flow that can optionally deactivate the plan.
- Prevent deleting plans that have any approved or in-progress cycles.
- Introduce ON_HOLD cycle status with postponement tracking and audit trail.

Scope
- Backend: monitoring plan/cycle schemas, endpoints, workflow transitions, audit logging, and delete guards.
- Frontend: monitoring plan create form, cycle actions UI, and cancel/postpone modals.
- Tests: backend workflow tests, cancel/postpone flows, plan creation validation, delete guard.

Decisions (per request)
- Plan creation must require an "Initial reporting cycle period end date".
- Cancel cycle flow asks whether to deactivate the plan; if not, auto-advance due dates.
- Manual overrides are split:
  - Extend due date: keep status as DATA_COLLECTION and update due dates.
  - Hold cycle: set status to ON_HOLD for indefinite pauses.
- ON_HOLD is reserved for true holds; simple extensions do not require a resume step.

Data Model Changes
1) MonitoringCycleStatus enum
   - Add ON_HOLD.
   - Update any status checks to include ON_HOLD in "in-progress" or "active" sets as appropriate.

2) MonitoringCycle fields
   - Add:
     - hold_reason: Optional[str]
     - hold_start_date: Optional[date]
     - original_due_date: Optional[date]
     - postponed_due_date: Optional[date]
     - postponement_count: int = 0
   - Migration:
     - Add columns with nullable defaults.
     - Backfill original_due_date = submission_due_date for existing cycles.
     - Backfill postponement_count to 0.

3) MonitoringPlan create schema
   - Add required field: initial_period_end_date (date).
   - Use this to compute plan.next_submission_due_date and plan.next_report_due_date.

Backend Workflow Changes
1) Create Monitoring Plan
   - Require initial_period_end_date; reject requests missing it (400 with clear error).
   - Compute:
     - submission_due_date = initial_period_end_date + data_submission_lead_days.
     - report_due_date = submission_due_date + reporting_lead_days.
   - Set plan.next_*_due_date from these values.

2) Cancel Cycle
   - Extend CycleCancelRequest with deactivate_plan: bool.
   - If deactivate_plan == true:
     - Set plan.is_active = false.
     - Do not auto-advance.
     - Audit log: plan deactivated + cancel reason.
   - If deactivate_plan == false:
     - Auto-advance plan due dates (existing event-driven behavior).
   - Ensure cancel remains blocked for APPROVED cycles.

3) Auto-advance on APPROVED
   - Keep event-driven auto-advance in _check_and_complete_cycle.
   - Base cadence should be cycle.period_end_date to avoid schedule drift when submission due dates are extended.
     - Next period end = current period_end_date + frequency.
     - Next submission due = next period end + data_submission_lead_days.
   - Skip if plan.is_active == false.
   - Only log when dates actually change.

4) Extend Due Date vs Hold Cycle
   - New endpoint: POST /monitoring/cycles/{cycle_id}/postpone
     - Allowed only when status == DATA_COLLECTION.
     - Input: new_due_date, reason, justification, indefinite_hold: bool = false.
     - If indefinite_hold == false (default):
       - Keep status = DATA_COLLECTION.
       - original_due_date (set if null) = cycle.submission_due_date
       - postponed_due_date = new_due_date
       - postponement_count += 1
       - cycle.submission_due_date = new_due_date
       - cycle.report_due_date = new_due_date + reporting_lead_days
       - plan.next_submission_due_date = new_due_date (aligns plan)
       - plan.next_report_due_date = new_report_due_date
       - Audit log: extend details (old/new dates, reason, justification).
     - If indefinite_hold == true:
       - status = ON_HOLD
       - hold_reason, hold_start_date = today
       - original_due_date (set if null) = cycle.submission_due_date
       - postponed_due_date = new_due_date (optional hold-until date)
       - cycle.submission_due_date/report_due_date updated if new_due_date provided
       - Do not treat cycle as overdue while ON_HOLD.
       - Audit log: hold details (reason, optional hold-until date).
   - New endpoint: POST /monitoring/cycles/{cycle_id}/resume
     - Allowed when status == ON_HOLD.
     - Sets status back to DATA_COLLECTION.
     - Audit log: resume action.
   - Submission rules:
     - submit_cycle remains DATA_COLLECTION-only; ON_HOLD requires resume.

5) Delete Monitoring Plan Guard
   - Block delete when any cycles exist with status:
     - APPROVED, PENDING, DATA_COLLECTION, UNDER_REVIEW, PENDING_APPROVAL, ON_HOLD.
   - Allow delete when only CANCELLED cycles exist (or no cycles).
   - Return a helpful error listing the count of blocking cycles.

Frontend UX Changes
1) Create New Plan Form
   - Add required date field: "Initial reporting cycle period end date".
   - Explain that it sets the first submission/report due dates.
   - Validate before submit and show inline error.

2) Cancel Cycle Modal
   - Add checkbox: "Deactivate monitoring plan".
   - If checked, call cancel endpoint with deactivate_plan=true.
   - If unchecked, auto-advance happens server-side.
   - Show confirm copy describing the impact on due dates.

3) Postpone Submission
   - Add "Extend Due Date" button when cycle status == DATA_COLLECTION.
   - Modal fields:
     - New date (required)
     - Reason (dropdown + free text)
     - Justification (required text)
     - Optional checkbox: "Place cycle on hold" (sets indefinite_hold=true).
   - Call /postpone endpoint.
   - Add "Resume Cycle" button when status == ON_HOLD.

4) Cycle Status UI
   - Display ON_HOLD status badge and hold details (reason + new date).
   - Show original vs postponed dates for transparency.
   - Catch-up logic: if auto-advance creates a past-due cycle, UI should surface it as immediately overdue (expected behavior).

Reporting / Metrics
- Track postponement_count on each cycle and aggregate per plan/model when needed.
- Add a small display in Plan details or Cycle history if required.

Audit / Compliance
- Add audit log entries for:
  - Plan auto-advance on APPROVED/CANCELLED.
  - Plan deactivation on cancel.
  - Extend due date, hold, and resume actions.

Testing Plan
Backend
- Create plan without initial_period_end_date -> 400.
- Create plan with date -> next_submission/report dates set correctly.
- Cancel cycle:
  - deactivate_plan=true -> plan inactive; no auto-advance.
  - deactivate_plan=false -> auto-advance once.
- Auto-advance on approve:
  - uses cycle due date base; respects plan.is_active.
- Postpone:
  - only DATA_COLLECTION allowed.
  - extend keeps DATA_COLLECTION and updates due dates.
  - hold sets ON_HOLD and suppresses overdue.
  - resume returns to DATA_COLLECTION.
- Submit from ON_HOLD should fail with a clear message (resume required).
- Delete plan with APPROVED or in-progress cycles -> 409/400.
- Delete plan with only CANCELLED cycles -> allowed.

Frontend
- Create plan form requires date; validation messaging.
- Cancel modal includes deactivate toggle.
- Postpone/resume buttons appear only for correct statuses.

Rollout
- Introduce migration first.
- Deploy backend updates.
- Deploy frontend changes.
- Monitor audit logs for unexpected auto-advances.

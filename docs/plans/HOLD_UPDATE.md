ON_HOLD Functionality & Status Transition UI Improvements
Summary
Improve the validation workflow ON_HOLD functionality by:
Restricting "Update Status" button to only Hold and Cancel actions with mandatory reasons
Computing hold time and excluding it from team SLA calculations
Adding "Resume from Hold" functionality with previous status tracking
Updating the user guide
Design Decision: Hold Time and SLA
Two SLA concepts exist:
Team SLA (validation_team_sla_due_date) - Measures team performance
Model Compliance Deadline (model_validation_due_date) - Regulatory deadline
Recommendation: Hold time exclusion applies to Team SLA only. Regulatory deadlines remain fixed - the business can't extend compliance deadlines just because work was paused. But the team shouldn't be penalized for hold periods outside their control.
Files to Modify
File	Changes
api/app/models/validation.py	Add total_hold_days, previous_status_before_hold, adjusted_validation_team_sla_due_date properties
api/app/schemas/validation.py	Add ValidationRequestHold, ValidationRequestCancel, ValidationRequestResume schemas
api/app/api/validation_workflow.py	Add /hold, /cancel, /resume endpoints; modify dashboard SLA queries
web/src/pages/ValidationRequestDetailPage.tsx	Replace status dropdown with Hold/Cancel/Resume buttons and modals
docs/USER_GUIDE_MODEL_VALIDATION.md	Update sections 4 (workflow stages) and 12 (SLA tracking)
Phase 1: Backend - Hold Time Computation
1.1 Add computed properties to ValidationRequest model
File: api/app/models/validation.py (after line 576)
@property
def total_hold_days(self) -> int:
    """Total days spent in ON_HOLD status, computed from status history."""
    hold_days = 0
    hold_start = None
    sorted_history = sorted(self.status_history, key=lambda x: x.changed_at)

    for entry in sorted_history:
        if entry.new_status and entry.new_status.code == "ON_HOLD":
            hold_start = entry.changed_at
        elif hold_start is not None:
            delta = entry.changed_at - hold_start
            hold_days += delta.days
            hold_start = None

    # If currently on hold, add time to now
    if hold_start is not None:
        delta = utc_now() - hold_start
        hold_days += delta.days

    return hold_days

@property
def previous_status_before_hold(self) -> Optional[str]:
    """Get status code before most recent ON_HOLD (for Resume functionality)."""
    if not self.current_status or self.current_status.code != "ON_HOLD":
        return None

    sorted_history = sorted(self.status_history, key=lambda x: x.changed_at, reverse=True)
    for entry in sorted_history:
        if entry.new_status and entry.new_status.code == "ON_HOLD":
            return entry.old_status.code if entry.old_status else None
    return None

@property
def adjusted_validation_team_sla_due_date(self) -> Optional[date]:
    """Team SLA due date adjusted for hold time (extends deadline by hold days)."""
    base_due = self.validation_team_sla_due_date
    if not base_due:
        return None
    return base_due + timedelta(days=self.total_hold_days)
1.2 Update response schema
File: api/app/schemas/validation.py - Add to ValidationRequestResponse:
total_hold_days: int = 0
previous_status_before_hold: Optional[str] = None
adjusted_validation_team_sla_due_date: Optional[date] = None
Phase 2: Backend - Dedicated Endpoints
2.1 Add new schemas
File: api/app/schemas/validation.py (after line 124)
class ValidationRequestHold(BaseModel):
    """Put validation on hold - reason required."""
    hold_reason: str = Field(..., min_length=10)

class ValidationRequestCancel(BaseModel):
    """Cancel validation request - reason required."""
    cancel_reason: str = Field(..., min_length=10)

class ValidationRequestResume(BaseModel):
    """Resume from hold."""
    resume_notes: Optional[str] = None
    target_status_code: Optional[str] = None  # Override, defaults to previous status
2.2 Add endpoints
File: api/app/api/validation_workflow.py
@router.post("/requests/{request_id}/hold")
def put_request_on_hold(request_id: int, data: ValidationRequestHold, ...):
    """Put validation request on hold with mandatory reason."""
    # Validate current status allows transition to ON_HOLD
    # Update current_status_id to ON_HOLD taxonomy value
    # Create status history entry with hold_reason
    # Update linked model version status (IN_VALIDATION -> DRAFT)
    # Create audit log

@router.post("/requests/{request_id}/cancel")
def cancel_request(request_id: int, data: ValidationRequestCancel, ...):
    """Cancel validation request with mandatory reason."""
    # Similar to hold but transitions to CANCELLED (terminal)

@router.post("/requests/{request_id}/resume")
def resume_from_hold(request_id: int, data: ValidationRequestResume, ...):
    """Resume validation from hold, returning to previous status."""
    # Validate currently ON_HOLD
    # Determine target status (from previous_status_before_hold or override)
    # Validate transition is allowed
    # Update status and create history entry
Phase 3: Backend - SLA Adjustments (CAREFUL)
3.1 Modify validation_team_sla_status property
File: api/app/models/validation.py (line 527) Change the comparison to use adjusted_validation_team_sla_due_date:
@property
def validation_team_sla_status(self) -> str:
    # ... existing checks ...

    # Use adjusted date that accounts for hold time
    adjusted_due = self.adjusted_validation_team_sla_due_date
    if not adjusted_due:
        return "Unknown"

    if today <= adjusted_due:
        return "In Progress (On Time)"
    else:
        return "In Progress (Past SLA)"
3.2 Modify dashboard SLA violations endpoint
File: api/app/api/validation_workflow.py (line 3992) In get_sla_violations(), use adjusted due date:
# Change: days_since_submission > lead_time_days
# To: days_since_submission > (lead_time_days + req.total_hold_days)
Phase 4: Frontend - UI Changes
4.1 Replace Update Status button with dedicated actions
File: web/src/pages/ValidationRequestDetailPage.tsx Current (lines 1185-1193):
<button onClick={() => setShowStatusModal(true)}>Update Status</button>
New:
{/* Show when NOT terminal and NOT on hold */}
{!['APPROVED', 'CANCELLED', 'ON_HOLD'].includes(currentStatusCode) && (
  <>
    <button onClick={() => setShowHoldModal(true)} className="btn-warning">
      Put on Hold
    </button>
    <button onClick={() => setShowCancelModal(true)} className="btn-danger">
      Cancel Request
    </button>
  </>
)}

{/* Show when ON_HOLD */}
{currentStatusCode === 'ON_HOLD' && (
  <>
    <button onClick={() => setShowResumeModal(true)} className="btn-success">
      Resume Work
    </button>
    <button onClick={() => setShowCancelModal(true)} className="btn-danger">
      Cancel Request
    </button>
  </>
)}
4.2 Add new modals
Put on Hold Modal:
Yellow/amber theme
Mandatory reason textarea (min 10 chars)
Warning: "SLA clock will be paused while on hold"
Cancel Request Modal:
Red theme with warning banner
Mandatory reason textarea
Confirmation: "This action cannot be undone"
Resume from Hold Modal:
Green theme
Shows: "On hold for {total_hold_days} days"
Shows: "Will resume to: {previous_status_before_hold}"
Optional notes field
4.3 Update existing status modal filter
File: web/src/pages/ValidationRequestDetailPage.tsx (line 2646) Remove ON_HOLD and CANCELLED from generic dropdown (keep for admin override if needed):
.filter((opt) => !['REVISION', 'ON_HOLD', 'CANCELLED'].includes(opt.code))
4.4 Add hold indicator banner
When request is ON_HOLD, show yellow banner:
⏸️ This validation request is ON HOLD
   Duration: {total_hold_days} days | Previous status: {previous_status_before_hold}
   Reason: {last hold reason from history}
Phase 5: Documentation Updates
5.1 Update Section 4 - The Validation Workflow Stages
File: docs/USER_GUIDE_MODEL_VALIDATION.md Add after "Special Statuses" subsection:
### Putting a Request On Hold

Use **Put on Hold** when validation work must be temporarily paused due to:
- Waiting for model owner to provide additional documentation
- External dependencies (audit, regulatory review)
- Resource constraints

**What happens when on hold:**
- Model version status reverts from IN_VALIDATION to DRAFT
- Team SLA clock is paused (hold time is excluded from SLA calculations)
- Compliance deadline remains unchanged (regulatory dates are fixed)
- Complete audit trail is maintained

**To resume:** Click "Resume Work" to return to the previous workflow stage.
5.2 Update Section 12 - Key Dates & SLA Tracking
Add explanation of hold time handling:
### Hold Time and SLA Calculations

When a validation is put on hold:
- **Team SLA**: Extended by the number of days on hold
- **Model Compliance Deadline**: Not affected (regulatory deadlines are fixed)

Example:
- Submission received: Jan 1
- Lead time: 90 days → Team SLA due: April 1
- Request on hold: Jan 15-30 (15 days)
- Adjusted Team SLA due: April 16 (original + 15 hold days)
Implementation Order
Phase 1 - Backend computed properties (low risk, no schema changes)
Phase 2 - New endpoints with dedicated schemas
Phase 3 - SLA adjustments (high risk - test carefully)
Phase 4 - Frontend UI changes
Phase 5 - Documentation
Testing - Full regression + manual E2E
Risk Mitigation
No new migrations needed - computed from existing status_history
Backward compatible - existing /status endpoint unchanged for non-hold/cancel
SLA changes are additive - extend dates rather than modify core calculations
Rollback safe - new endpoints can be removed without breaking existing flow
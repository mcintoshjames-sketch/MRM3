# Model Validation Workflow User Guide

## Table of Contents

1. [Introduction](#1-introduction)
2. [Understanding the Validation Lifecycle](#2-understanding-the-validation-lifecycle)
3. [Creating a Validation Request](#3-creating-a-validation-request)
4. [The Validation Workflow Stages](#4-the-validation-workflow-stages)
5. [Validation Plan & Scope](#5-validation-plan--scope)
6. [Assignments & Team Roles](#6-assignments--team-roles)
7. [Outcomes & Ratings](#7-outcomes--ratings)
8. [Approvals Process](#8-approvals-process)
9. [Revalidation Lifecycle](#9-revalidation-lifecycle)
10. [Model Version Integration](#10-model-version-integration)
11. [Dashboards & Monitoring](#11-dashboards--monitoring)
12. [Key Dates & SLA Tracking](#12-key-dates--sla-tracking)
13. [Frequently Asked Questions](#13-frequently-asked-questions)

---

## 1. Introduction

### What is Model Validation?

Model validation is an independent review process that assesses whether a model is fit for its intended purpose. The validation workflow in this system provides a structured approach to:

- Track validation requests from initiation to completion
- Document validation scope, findings, and outcomes
- Manage approvals from required stakeholders
- Monitor compliance with revalidation schedules
- Maintain audit trails for regulatory reporting

### Who Uses This Workflow?

| Role | Primary Activities |
|------|-------------------|
| **Model Owner** | Submits documentation, responds to findings, receives validation outcomes |
| **Validator** | Conducts validation work, documents findings, proposes ratings |
| **Reviewer** | Reviews validation work quality before approvals |
| **Approvers** | Provide sign-off on validation outcomes (Validation Head, Risk Officers, Regional Approvers) |
| **Admin** | Manages workflow configuration, policies, and reporting |

---

## 2. Understanding the Validation Lifecycle

### Validation Types

The system supports different types of validations based on their purpose:

| Type | Description | When Used |
|------|-------------|-----------|
| **Initial** | First-ever validation of a new model | When a model enters the inventory |
| **Comprehensive** | Full periodic revalidation | Scheduled reviews based on risk tier |
| **Targeted** | Focused review of specific aspects | Following material changes or findings |
| **Interim** | Temporary approval with expiration | Time-limited approvals requiring full validation |

### The Workflow State Machine

Every validation request moves through a defined set of stages:

```
┌─────────┐    ┌──────────┐    ┌─────────────┐    ┌────────┐    ┌──────────────────┐    ┌──────────┐
│ INTAKE  │───►│ PLANNING │───►│ IN PROGRESS │───►│ REVIEW │───►│ PENDING APPROVAL │───►│ APPROVED │
└─────────┘    └──────────┘    └─────────────┘    └────────┘    └──────────────────┘    └──────────┘
     │               │                │                │                 │
     │               │                │                │                 │
     ▼               ▼                ▼                ▼                 ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                          ON HOLD / CANCELLED (from any stage)                      │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Creating a Validation Request

### Step-by-Step: Creating a New Request

1. **Navigate to Validation Workflow**
   - Go to **Validation Workflow** from the main navigation
   - Click **"New Validation Request"** button

2. **Select Model(s)**
   - Choose one or more models to validate together
   - The system suggests related models based on grouping history
   - Multi-model validations are useful for related models that share common components

3. **Choose Validation Type**
   - Select the appropriate type (Initial, Comprehensive, Targeted, Interim)
   - For new models with no prior validations, "Initial" is automatically suggested

4. **Set Priority**
   - **Urgent**: Time-sensitive validations with compressed timelines
   - **Standard**: Normal priority following standard SLAs

5. **Enter Target Completion Date**
   - The system validates this against:
     - Risk-tier-based lead time requirements
     - Model change implementation dates
     - Revalidation deadlines
   - Warnings appear if the date conflicts with policy requirements

6. **Select Regions** (if applicable)
   - For regional validations, specify which regions are in scope
   - The system suggests regions based on models' regional associations

7. **Provide Trigger Reason**
   - Document why this validation is being initiated
   - Examples: "Annual revalidation", "Material methodology change", "Regulatory requirement"

8. **Submit**
   - The request is created in **INTAKE** status
   - Audit trail records the creation with timestamp and creator

### Auto-Generated Validation Requests

Validation requests can be automatically created in certain scenarios:

- **Major Model Changes**: When a model version with a "Major" change type is created, the system can auto-generate a validation request
- **Revalidation Cycles**: Admins can configure automatic request creation as revalidation dates approach

---

## 4. The Validation Workflow Stages

### Stage 1: Intake

**Purpose**: Initial review and acceptance of the validation request

**Who**: Admin or Validation Manager

**Key Activities**:
- Review the request for completeness
- Verify the models and scope are appropriate
- Accept or decline the request

**Status Transitions**:
- → **Planning**: When request is accepted and ready for resource allocation
- → **Cancelled**: If request is declined (with documented reason)

**Automatic Behavior**:
- When a validator is assigned during Intake, the status automatically moves to Planning

---

### Stage 2: Planning

**Purpose**: Resource allocation and scope definition

**Who**: Validation Manager, assigned Validators

**Key Activities**:
- Assign validators to the request
- Create the validation plan (scope components)
- Estimate effort and set timelines
- Mark documentation submission as received

**Status Transitions**:
- → **In Progress**: When validation work begins (typically when submission is received)
- → **On Hold**: If work is paused temporarily
- → **Intake**: If sent back for additional information

**Key Action - Marking Submission Received**:
For periodic revalidations, the model owner must submit documentation. When received:
1. Click **"Mark Submission Received"**
2. Enter the submission date
3. Optionally record submission metadata (document version, external IDs)
4. The system calculates SLA timelines based on this date

---

### Stage 3: In Progress

**Purpose**: Active validation work is being performed

**Who**: Assigned Validators

**Key Activities**:
- Conduct validation testing and analysis
- Document work components and progress
- Create findings and recommendations
- Prepare validation outcome

**Status Transitions**:
- → **Review**: When work is complete and ready for QA
- → **On Hold**: If work must be paused
- → **Planning**: If scope changes require replanning

**Model Version Integration**:
When a request moves to In Progress, linked model versions automatically transition from **DRAFT** to **IN_VALIDATION** status. During the early validation stages (Intake, Planning, In Progress), Validators and Admins can still edit the version details if corrections are needed. Once validation reaches **Review** or later stages, the version becomes locked to preserve the record of what was validated.

---

### Stage 4: Review

**Purpose**: Quality assurance and peer review of validation work

**Who**: Designated Reviewer (validator with reviewer role)

**Key Activities**:
- Review validation work for completeness
- Verify methodology and conclusions
- **Document the validation outcome** (required before moving to Pending Approval)
- Provide sign-off or request revisions

> **Important**: A validation outcome must be documented before the request can transition to Pending Approval. Navigate to the **Outcome** tab to enter the overall rating, executive summary, and effective date. The system will block the transition if no outcome exists.

**Reviewer Sign-Off**:
1. Navigate to the **Assignments** tab
2. Find your assignment marked as "Reviewer"
3. Click **"Sign Off"**
4. Add any comments
5. Confirm sign-off

**Status Transitions**:
- → **Pending Approval**: After reviewer sign-off **(outcome must be created first)**
- → **In Progress**: If work needs revisions
- → **Revision**: If specific changes are requested

---

### Stage 5: Pending Approval

**Purpose**: Stakeholder sign-off on validation results

**Who**: Required Approvers (Validation Head, Risk Officers, Regional Approvers)

**Key Activities**:
- Review validation outcome and rating
- Provide approval, rejection, or send back for revisions
- Document approval decision with comments

**Status Transitions**:
- → **Approved**: When all required approvals are granted
- → **In Progress** or **Review**: If sent back for additional work
- → **Revision**: If specific changes are required before re-approval

#### Pre-Transition Warnings

When attempting to advance a validation request to **PENDING_APPROVAL** status, the system checks for conditions that may require attention. These warnings do not block the transition but alert you to outstanding items that should be addressed.

**How Warnings Appear:**

1. Click the button to advance to Pending Approval
2. If any warnings exist, a modal displays with warning details
3. You can choose to **Proceed Anyway** or **Cancel** to address issues first

**Warning Types:**

| Warning | Condition | Recommended Action |
|---------|-----------|-------------------|
| **OPEN_FINDINGS** | Prior validations have unresolved findings still marked as open | Review open findings and update their status or document why they remain open |
| **PENDING_RECOMMENDATIONS** | The model has active recommendations that haven't been addressed | Verify recommendations are being tracked and have appropriate response plans |
| **UNADDRESSED_ATTESTATIONS** | Pending attestation items exist that haven't been completed | Complete required attestations or document why they're pending |

**Example Warning Display:**

```
⚠ Pre-Transition Warnings

The following items should be reviewed before requesting approval:

• OPEN_FINDINGS: There are 3 unresolved findings from prior validations
• PENDING_RECOMMENDATIONS: 2 active recommendations require response

You may proceed, but approvers will see these outstanding items.

[Proceed Anyway]  [Cancel]
```

**Best Practice:** Address warnings before requesting approval. While the system allows you to proceed with warnings, resolving them first:
- Reduces questions from approvers
- Demonstrates thorough completion of validation work
- Ensures compliance documentation is complete

---

### Stage 6: Approved

**Purpose**: Validation is complete

**Outcome**:
- Model validation is officially recorded
- Effective date and any expiration date are captured
- Linked model versions transition to **APPROVED** status
- The validation becomes the basis for future revalidation scheduling

---

### Special Statuses

**On Hold**

Use the **"Put on Hold"** button when validation work must be temporarily paused due to:
- Waiting for model owner to provide additional documentation
- External dependencies (audit, regulatory review)
- Resource constraints or reassignment

**What happens when on hold:**
- A mandatory reason is required (minimum 10 characters)
- Model version status reverts from **IN_VALIDATION** to **DRAFT**
- **Team SLA clock is paused** - hold time is excluded from SLA calculations
- Compliance deadline remains unchanged (regulatory dates are fixed)
- Complete audit trail is maintained
- A yellow banner displays on the request showing hold duration and reason

**To resume:** Click **"Resume Work"** to return to the previous workflow stage. The system automatically tracks which stage the request was in before being put on hold.

**SLA Impact:** When calculating whether the validation team met their SLA, all time spent on hold is subtracted. For example:
- Submission received: Jan 1
- Lead time SLA: 90 days → Team SLA due: April 1
- Request on hold: Jan 15-30 (15 days)
- **Adjusted Team SLA due: April 16** (original + 15 hold days)

**Cancelled**

Use the **"Cancel Request"** button to permanently terminate a validation request. This action cannot be undone.

- A mandatory reason is required (minimum 10 characters)
- Request moves to terminal **CANCELLED** status
- Linked model versions revert to **DRAFT** status
- Preserved in history for audit purposes

**Revision**
- Sent back for specific changes
- Approver or reviewer requests modifications
- Work resumes with targeted focus

---

## 5. Validation Plan & Scope

### What is a Validation Plan?

The validation plan documents which components of the bank's validation standard will be performed. It is based on a **Figure 3 Matrix** that defines expectations by risk tier.

### Validation Components

The bank's validation standard defines **30 components** organized into 11 sections:

| Section | Example Components |
|---------|-------------------|
| 1. Executive Summary | Summary, Key Findings, Rating |
| 2. Introduction | Model Overview, Scope Statement |
| 3. Conceptual Soundness | Methodology Review, Assumptions Analysis |
| 4. Ongoing Monitoring | Benchmarking, Sensitivity Analysis |
| 5. Outcome Analysis | Back-testing, Performance Testing |
| 6. Model Risk | Limitations, Weaknesses |
| 7-11. Supporting Sections | Conclusion, Deployment, Monitoring, References, Appendix |

### Expectations by Risk Tier

For each component, the expectation depends on the model's risk tier:

| Expectation | Meaning |
|-------------|---------|
| **Required** | Must be performed for models of this tier |
| **If Applicable** | Perform if relevant to the model |
| **Not Expected** | Typically not needed for this tier |

### Creating a Validation Plan

1. Navigate to the validation request's **Plan** tab
2. Click **"Create Validation Plan"**
3. The system pre-populates defaults based on risk tier:
   - Required → Planned
   - Not Expected → Not Planned
   - If Applicable → Planned (you can adjust)

### Recording Deviations

When your plan differs from the standard expectation, a **deviation** is flagged:

**Example Deviations**:
- Required component marked as "Not Planned"
- Not Expected component marked as "Planned"

**Deviation Requirements**:
1. Each deviation must have a documented **rationale**
2. Material deviations (changing overall approach) require additional justification
3. Deviations are tracked for compliance reporting

**Example Rationale**:
> "Process Verification testing not applicable - model is a licensed vendor solution (Bloomberg BVAL). Vendor provides certification of calculation accuracy. Will rely on vendor certification plus independent benchmarking."

### Plan Versioning

The validation plan is linked to a **configuration version** that captures the standard expectations at the time of validation:

- When a plan is created, it uses current active expectations
- When validation moves to Review or Pending Approval, the plan is **locked**
- If validation is sent back, the plan **unlocks** for edits
- Historical validations always show the expectations that applied at that time

---

## 6. Assignments & Team Roles

### Validator Roles

| Role | Responsibilities |
|------|-----------------|
| **Primary Validator** | Lead validator responsible for overall coordination |
| **Validator** | Team member performing validation work |
| **Reviewer** | Designated quality reviewer who must sign off |

### Assigning Validators

1. Go to the **Assignments** tab
2. Click **"Add Validator"**
3. Select the validator from the user list
4. Indicate their role:
   - Check "Primary" if they're the lead
   - Check "Reviewer" if they'll perform QA sign-off
5. Confirm **Independence Attestation** (required)
6. Save the assignment

### Independence Requirements

The system enforces validator independence:
- A validator **cannot** be assigned if they are the model owner or developer
- Independence attestation must be confirmed during assignment
- Violations are blocked with an explanatory error message

### Removing Validators

When removing a validator:
- If removing the primary validator, you must designate a new primary
- You cannot remove the last validator from a request
- The system tracks all assignment changes in the audit log

---

## 7. Outcomes & Ratings

### Validation Outcome

When validation work is complete, the outcome must be documented. The outcome can be entered starting from the **Review** stage, and **must be created before the request can move to Pending Approval**.

1. Navigate to the **Outcome** tab
2. Enter the required information:
   - **Overall Rating**: Select from configured ratings
   - **Executive Summary**: Document key conclusions
   - **Effective Date**: When the validation takes effect
   - **Expiration Date**: Required for INTERIM validations

### Overall Ratings

| Rating | Meaning |
|--------|---------|
| **Fit for Purpose** | Model is suitable for its intended use without material concerns |
| **Not Fit for Purpose** | Model has critical issues requiring significant remediation before use |

> **Note:** Findings and recommendations are tracked separately from the overall rating. A model rated "Fit for Purpose" may still have open recommendations that need to be addressed.

### INTERIM Validations

For INTERIM (temporary) validations:
- An **expiration date is required**
- The model must complete a full validation before expiration
- The system tracks interim expirations for compliance monitoring

---

## 8. Approvals Process

### Understanding Approvals

Validation outcomes require sign-off from designated approvers before becoming official. The system supports multiple approval types:

### Approval Types

| Type | Description |
|------|-------------|
| **Global** | Required for all validations (e.g., Validation Head) |
| **Regional** | Required when model is used in specific regions |
| **Additional** | Role-based approvals triggered by model attributes (e.g., risk tier, validation type) |

### Approver Roles

Typical approver roles include:
- **Validation Head**: Overall validation function sign-off
- **Model Owner**: Acknowledges validation results
- **Risk Officer**: Risk management oversight
- **Regional Approver**: Region-specific sign-off (for regional validations)

### Submitting an Approval

When you're a required approver:

1. Navigate to the **Approvals** tab
2. Find your pending approval
3. Review the validation outcome and supporting documentation
4. Click **"Submit Approval"**
5. Choose your decision:
   - **Approved**: You agree with the outcome
   - **Rejected**: You disagree with the outcome (rare, requires justification)
   - **Sent Back**: Request revisions before making a decision
6. Add comments explaining your decision
7. Submit

### Automatic Status Transitions

- When **all required approvals** are granted, the request automatically moves to **APPROVED**
- If any approver selects **Sent Back**, the request returns to the appropriate prior stage

### Regional Approvals

For models used in multiple regions with `requires_regional_approval` enabled:
- Each region generates a separate approval requirement
- Regional approvers sign off for their respective regions
- The validation is only complete when all regional approvals are granted

### Proxy Approvals

In some cases, approvals can be submitted on behalf of another approver:
- The system tracks proxy approvals separately
- Proxy evidence must be documented
- Audit trails record both the submitter and the represented approver

---

## 9. Revalidation Lifecycle

### Understanding Periodic Revalidation

Models must be revalidated on a schedule based on their risk tier. The revalidation lifecycle involves:

1. **Submission Due Date**: When model documentation should be submitted
2. **Grace Period**: Additional time allowed for late submissions
3. **Validation Due Date**: Final deadline for completing validation

### Timeline Overview

```
[Last Validation] ─────► [Submission Due] ─────► [Grace Period End] ─────► [Validation Due]
     Complete                 │                         │                        │
                              │                         │                        │
                    [Model Owner               [3 months                [Lead Time
                     submits docs]              buffer]                 from grace end]
```

### Key Dates Explained

| Date | Calculation | Purpose |
|------|-------------|---------|
| **Submission Due** | Last Validation + Frequency (from policy) | When model owner should submit documentation |
| **Grace Period End** | Submission Due + 3 months | Final deadline for documentation submission |
| **Model Validation Due** | Grace Period End + Lead Time | Compliance deadline for completed validation |
| **Team SLA Due** | Submission Received + Lead Time | Performance metric for validation team |

### Two Different "Due Dates"

The system distinguishes between two perspectives:

**Model Validation Due Date** (Compliance View)
- Fixed based on prior validation date + policy
- Determines if the MODEL is overdue
- Does not change regardless of when documentation is submitted

**Validation Team SLA Due** (Performance View)
- Based on when documentation was actually received
- Measures team efficiency
- Accounts for late submissions from model owners

**Example**:
> - Last Validation: January 1, 2024
> - Frequency: 12 months → Submission Due: January 1, 2025
> - Grace Period: 3 months → Grace End: April 1, 2025
> - Lead Time: 90 days → Model Validation Due: June 30, 2025
>
> If model owner submits on March 1, 2025:
> - Team SLA Due: May 30, 2025 (90 days from submission)
> - Model Validation Due: Still June 30, 2025 (unchanged)

### Submission Statuses

| Status | Meaning |
|--------|---------|
| **Not Yet Due** | Before submission due date |
| **Due** | At or after due date, within grace period |
| **In Grace Period** | Past due date, grace period not expired |
| **Overdue** | Past grace period |
| **Submitted On Time** | Documentation received by due date |
| **Submitted In Grace Period** | Documentation received during grace period |
| **Submitted Late** | Documentation received after grace period |

### Validation Compliance Statuses

| Status | Meaning |
|--------|---------|
| **On Track** | Within submission due date |
| **In Grace Period** | Submission due passed but within grace |
| **At Risk** | Past grace period, approaching validation due |
| **Overdue** | Past validation due date |
| **Validated On Time** | Completed before validation due date |
| **Validated Late** | Completed after validation due date |

---

## 10. Model Version Integration

### Automatic Version Status Updates

Model versions are automatically updated based on validation status:

| Validation Status | Version Status |
|-------------------|----------------|
| Request moves to **IN_PROGRESS** | Version: DRAFT → **IN_VALIDATION** |
| Request reaches **APPROVED** | Version: IN_VALIDATION → **APPROVED** |
| Request is **CANCELLED** or **ON_HOLD** | Version: IN_VALIDATION → **DRAFT** |

### Version Activation

After approval, the model owner can activate the approved version:
1. Navigate to the model's Versions tab
2. Find the approved version
3. Click **"Activate"**
4. The version becomes **ACTIVE**, and any prior active version becomes **SUPERSEDED**

### Version States

| Status | Meaning | Editable |
|--------|---------|----------|
| **DRAFT** | Initial state, not yet validated | ✓ Yes |
| **IN_VALIDATION** | Validation in progress | ✓ Conditional* |
| **APPROVED** | Validation complete | ✗ No |
| **ACTIVE** | Currently deployed | ✗ No |
| **SUPERSEDED** | Replaced by newer version | ✗ No |

*\*IN_VALIDATION versions can be edited by Validators/Admins while the validation request is in Intake, Planning, or In Progress stages. Once validation reaches Review or later, the version is locked and shows "Locked" in the Actions column.*

---

## 11. Dashboards & Monitoring

### Validation Workflow Dashboard

The main validation list provides filtering and sorting:

**Filters Available**:
- Status (Intake, Planning, In Progress, etc.)
- Priority (Urgent, Standard)
- Validation Type (Initial, Comprehensive, Targeted, Interim)
- Region
- Overdue only
- Model name search

### Model Owner View

Model owners can see:
- **My Models**: Quick access to owned inventory
- **Pending Submissions**: Models awaiting documentation
- **Active Validations**: Ongoing validations for their models

### Admin Dashboard Widgets

**Overdue Submissions**
- Models past grace period without documentation submitted
- Sorted by days overdue

**Overdue Validations**
- Validations past their due date
- Shows compliance risk

**Upcoming Revalidations**
- Models due for validation in next 30/60/90 days
- Helps with resource planning

### Revalidation Status Indicators

On the Model Details page, the system displays:
- Current revalidation status (Upcoming, In Grace Period, Overdue, etc.)
- Days until next submission/validation due
- Link to active validation request (if exists)
- History of prior validations

---

## 12. Key Dates & SLA Tracking

### Validation Policy Configuration

Administrators configure validation policies per risk tier:

| Setting | Description |
|---------|-------------|
| **Frequency (months)** | How often models of this tier require revalidation |
| **Grace Period (months)** | Additional time allowed for late submissions |
| **Lead Time (days)** | Expected time from submission to completion |

### Typical Configuration

| Risk Tier | Frequency | Grace Period | Lead Time |
|-----------|-----------|--------------|-----------|
| **High** | 12 months | 3 months | 90 days |
| **Medium** | 18 months | 3 months | 90 days |
| **Low** | 24 months | 3 months | 60 days |

### SLA Calculations

**Assignment SLA**: Time to assign validators after request creation
**Begin Work SLA**: Time to start work after assignment
**Complete Work SLA**: Risk-tier-based lead time from submission
**Approval SLA**: Time to complete all approvals after review

### Status Duration Tracking

The system tracks how long requests spend in each status:
- **Days in Status**: Shows on the request list
- **Aging Report**: Summarizes requests by status and duration
- **Workload Report**: Shows validator assignments and capacity

### Hold Time and SLA Calculations

When a validation request is put **on hold**, the system adjusts SLA calculations:

| SLA Type | Hold Time Treatment |
|----------|---------------------|
| **Team SLA** | Extended by hold duration - team not penalized for paused periods |
| **Model Compliance Deadline** | Not affected - regulatory dates remain fixed |

**How it works:**
1. System tracks each ON_HOLD period via status history
2. Total hold days are calculated automatically
3. Team SLA due date is extended by the total hold duration
4. SLA violation reports exclude hold time from calculations

**Example:**
- Submission received: January 1
- Lead time policy: 90 days → Team SLA due: April 1
- On hold: January 15-30 (15 days)
- **Adjusted Team SLA due: April 16** (original + 15 hold days)

The adjusted due date appears in:
- Validation request details
- SLA violation dashboard
- Team workload reports

**Note:** While Team SLA is adjusted, the regulatory compliance deadline for the model (based on prior validation expiration) is **not** adjusted. This reflects the business reality that regulatory deadlines cannot be extended by internal workflow pauses.

---

## 13. Frequently Asked Questions

### General Questions

**Q: Can I validate multiple models together?**
A: Yes, the system supports multi-model validation requests. This is useful for related models that share common components or are typically validated together.

**Q: What happens if I need to put a validation on hold?**
A: Click the **"Put on Hold"** button and provide a mandatory reason (minimum 10 characters). The system will:
- Pause the Team SLA clock (hold time is excluded from SLA calculations)
- Revert linked model versions to DRAFT status
- Display a yellow banner showing hold duration and reason
When ready, click **"Resume Work"** to return to the previous workflow stage. See [Section 4 - Special Statuses](#special-statuses) for full details.

**Q: How do I know if a validation is overdue?**
A: The system displays overdue indicators on the validation list and model details pages. You can also filter for overdue validations specifically.

### For Model Owners

**Q: When do I need to submit documentation?**
A: Submit documentation by your submission due date. If you miss this date, you have a grace period (typically 3 months) before the submission is considered overdue.

**Q: How do I know my model needs revalidation?**
A: Check the revalidation status on your model's details page. The system shows upcoming due dates, and your dashboard highlights pending submissions.

**Q: What if I submit documentation late?**
A: Late submissions are tracked and visible in reporting. While you still have until the grace period end before being marked as overdue, timely submission is expected.

### For Validators

**Q: Why can't I be assigned to certain models?**
A: The system enforces independence requirements. You cannot be assigned to validate a model where you are the owner or developer.

**Q: What if I need additional information from the model owner?**
A: You can communicate needs through findings and recommendations. If substantial additional work is needed, consider whether the status should move to On Hold or be sent back to Planning.

**Q: How do I sign off as a reviewer?**
A: Go to the Assignments tab, find your reviewer assignment, and click "Sign Off". You can add comments with your sign-off.

### For Approvers

**Q: What does "Send Back" mean?**
A: Choosing "Send Back" returns the validation for additional work. Use this when you're not ready to approve but don't want to reject outright—for example, when clarifications or minor changes are needed.

**Q: Can I delegate my approval to someone else?**
A: The system supports proxy approvals with appropriate documentation. However, this should be used sparingly and with proper authorization.

### Technical Questions

**Q: What happens to model versions during validation?**
A: When validation moves to In Progress, linked versions transition to IN_VALIDATION status. During early validation stages (Intake, Planning, In Progress), Validators and Admins can still edit the version if corrections are needed—look for the **Edit** link in the Actions column. Once validation reaches Review or later stages, the version is locked to preserve the validation record (shown as "Locked" in the UI). When approved, versions become APPROVED status and can be activated.

**Q: How are validation policies configured?**
A: Administrators configure policies through the Taxonomy and Validation Policy admin pages. Each risk tier can have different frequencies, grace periods, and lead times.

---

## Appendix: Status Reference

### Validation Request Statuses

| Status | Description | Next Possible Statuses |
|--------|-------------|----------------------|
| **Intake** | Request submitted, awaiting acceptance | Planning, Cancelled |
| **Planning** | Assigning resources, defining scope | In Progress, On Hold, Intake |
| **In Progress** | Active validation work | Review, On Hold, Planning |
| **Review** | QA and peer review | Pending Approval, In Progress, Revision |
| **Pending Approval** | Awaiting stakeholder sign-off | Approved, In Progress, Review, Revision |
| **Revision** | Sent back for specific changes | In Progress, Review |
| **Approved** | Validation complete | (Terminal) |
| **On Hold** | Temporarily paused | Planning, In Progress |
| **Cancelled** | Request terminated | (Terminal) |

### Approval Statuses

| Status | Description |
|--------|-------------|
| **Pending** | Awaiting approver action |
| **Approved** | Approver granted approval |
| **Rejected** | Approver rejected outcome |
| **Sent Back** | Approver requests revisions |

---

*Last Updated: December 2025*

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
| **Initial** | First-ever validation of a new model (only if no prior full validation exists) | When a model enters the inventory |
| **Comprehensive** | Full periodic revalidation | Scheduled reviews based on risk tier |
| **Targeted** | Focused review of specific aspects | Following material changes or findings |
| **Interim** | Temporary approval with expiration | Time-limited approvals requiring full validation |
| **Change** | Validation of a specific model change (draft version) | When a specific model version must be validated before implementation |

> **Configurable**: Validation types are managed by administrators via the Validation Type taxonomy. The list above reflects the current/default configuration in this system.

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
   - Select the appropriate type (Initial, Comprehensive, Targeted, Interim, Change)
   - For new models with no prior full validations, "Initial" is automatically suggested and only available when no prior full validation (Initial or Comprehensive) exists
   - **Change validations** require selecting a specific draft version for each model (if no draft exists, create a model change first)

4. **Set Priority**
   - **Urgent**: Time-sensitive validations with compressed timelines
   - **Standard**: Normal priority following standard SLAs

5. **Enter Target Completion Date**
   - The system validates this against:
     - Risk-tier-based lead time requirements
     - Model change implementation dates
     - Revalidation deadlines
   - Warnings appear if the date conflicts with policy requirements

6. **Specific Region Scope (Optional)**
   - Add regions only when the validation is limited to certain geographies
   - Leave blank if the validation is global (not specific to a region)
   - The system suggests regions based on models' regional associations
   - **Region scope must match deployments**: every selected model must be deployed in the selected regions, or the request will be blocked
   - If selected models have different regional footprints, consider leaving scope blank so the validation remains global

7. **Provide Trigger Reason**
   - Document why this validation is being initiated
   - Examples: "Annual revalidation", "Material methodology change", "Regulatory requirement"

8. **Submit**
   - The request is created in **INTAKE** status
   - Audit trail records the creation with timestamp and creator

### Auto-Generated Validation Requests

Validation requests can be automatically created in certain scenarios:

- **Major Model Changes**: When a model version with a "Major" change type is created, the system can auto-generate a validation request
- **Note on Revalidation**: Periodic revalidation requests are currently initiated manually based on Dashboard alerts and reports.

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
- → **On Hold**: If the request must be paused before work begins

> **Note**: In the UI, "Decline" is recorded as **Cancelled** with a required reason.

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
- → **Cancelled**: If the request is terminated during planning

**Key Action - Marking Submission Received**:
For periodic revalidations, the model owner must submit documentation. When received:
1. Click **"Mark Submission Received"**
2. Enter the submission date
3. Optionally record submission metadata (document version, external IDs)
4. The system calculates SLA timelines based on this date

**Editing Project Details**:
Use **Edit Project Details** on the validation detail page to update:
- External Project ID
- Priority
- Target Completion Date
- Trigger Reason

You can also set a **Latest Target Date Override** (with a reason):
- If **submission has not been received**, this is a target **submission** date; the system adds lead time to compute the latest completion target.
- If **submission has been received**, this is the validator’s target **completion** date.
- This override can be set even when the request is not overdue and appears as **Latest Target Date** in the Project Overview.

> **Availability**: Edits are allowed until the request reaches **Pending Approval** or **Approved**.

**Managing Models on a Request (Intake/Planning)**:
If you need to add or remove models after creation:
- Open the validation detail page and click **Manage Models**
- Add/remove models and link draft versions for **Change** validations
- The system rechecks lead time, regional scope, approvals, and validation plan expectations
- **Validator independence** is revalidated against the updated model list

**Allow unassigning conflicting validators if needed**:
- If any current validators become conflicted (owner/developer of a newly added model), the update is blocked by default
- Checking this box lets the change proceed and **automatically unassigns** the conflicting validators
- The unassignment is recorded in the audit log

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
- → **Review**: If a Reviewer is assigned
- → **Pending Approval**: If **NO** Reviewer is assigned (Review stage is skipped)
- → **On Hold**: If work must be paused
- → **Planning**: If scope changes require replanning
- → **Cancelled**: If the request is terminated during active work

**Model Version Integration**:
When a request moves to In Progress, linked model versions automatically transition from **DRAFT** to **IN_VALIDATION** status. During the early validation stages (Intake, Planning, In Progress), Validators and Admins can still edit the version details if corrections are needed. Once validation reaches **Review** or later stages, the model version details becomes locked to preserve the record of what was validated.

---

### Stage 4: Review

**Purpose**: Quality assurance and peer review of validation work

**Skipped When**: No Reviewer is assigned to the request. The workflow proceeds directly from In Progress to Pending Approval.

**Who**: Designated Reviewer (validator with reviewer role)

**Key Activities**:
- Review validation work for completeness
- Verify methodology and conclusions
- **Document the validation outcome** (required before moving to Pending Approval)
- Record the reviewer decision (agree or send back for revisions)

> **Important**: A validation outcome must be documented before the request can transition to Pending Approval. Navigate to the **Outcome** tab to enter the overall rating, executive summary, and effective date. The system will block the transition if no outcome exists.

**Reviewer Decision (Agree or Send Back)**:
1. Navigate to the **Assignments** tab
2. Find your assignment marked as "Reviewer"
3. Choose **Sign Off** to agree, or **Send Back** if revisions are needed
4. Add comments (recommended for clarity)
5. Confirm your decision

The reviewer’s decision is recorded in the audit trail and determines the next step.

**Status Transitions**:
- → **Pending Approval**: When the reviewer agrees **(outcome must be created first)**
- → **In Progress**: If the reviewer sends back for revisions
- → **On Hold**: If work must be paused during review
- → **Cancelled**: If the request is terminated during review

---

### Stage 5: Pending Approval

**Purpose**: Stakeholder sign-off on validation results

**Who**: Required Approvers (Validation Head, Risk Officers, Regional Approvers)

**Key Activities**:
- Review validation outcome and rating
- Provide approval or send back for revisions (use **Cancel Request** for true rejections)
- Document approval decision with comments

**Status Transitions**:
- → **Approved**: When all required approvals are granted
- → **Revision**: If sent back by an approver for minor corrections (automatic when approver selects "Send Back")
- → **In Progress**: Admin can use "Send Back to In Progress" button for substantial rework (admin-only override)
- → **On Hold**: If work must be paused during approvals
- → **Cancelled**: If the request is terminated during approvals

**Two Sendback Workflows**:

The system provides two different ways to send a request back for rework, each designed for different scenarios:

1. **"Send Back" (Approver → REVISION)**: For minor corrections and clarifications
   - Use when: Typos need fixing, wording needs clarification, supporting docs need adding
   - Approval behavior: Intelligent reset based on material changes
   - When resubmitted: System compares new state to when sent back:
     - If NO material changes (same rating, same recommendations, same limitations): Only the sending approver's vote is reset
     - If material changes detected: All "Approved" votes are reset; all approvers review again
   - Best for: Quick fixes that don't fundamentally alter the validation

2. **"Send Back to In Progress" (Admin Override → IN PROGRESS)**: For substantial rework
   - Use when: Significant portions need redoing, approach is fundamentally flawed, major gaps identified
   - Approval behavior: ALL approvals (Global, Regional, Conditional) unconditionally reset to Pending
   - When resubmitted: All approvers must re-review from scratch, regardless of what changed
   - Requires: Admin privileges
   - Best for: Major rework situations requiring fresh review by all stakeholders

> **Note**: Both workflows create a snapshot of the validation state (scorecard rating, recommendations, limitations) for audit trail purposes and to track what changes during rework.

---

### Stage 5.5: Revision

**Purpose**: Address minor corrections or clarifications requested by approvers

**Who**: Model Validator, Validation Owner

**How You Get Here**: An approver used "Send Back" during Stage 5 (Pending Approval)

**Key Activities**:
- Review approver's feedback and comments
- Make requested corrections or clarifications
- Add supporting documentation if needed
- Resubmit to Pending Approval when ready

**Status Transitions**:
- → **Pending Approval**: When corrections are complete and ready for re-review
- → **On Hold**: If work must be paused
- → **Cancelled**: If the request is terminated

**Approval Implications**:
When you resubmit from REVISION to PENDING_APPROVAL, the system intelligently determines which approvals need to be re-granted:
- **No Material Changes**: If you only fixed typos or added clarifying text without changing the rating, recommendations, or limitations, then only the approver who sent it back needs to re-approve
- **Material Changes**: If the scorecard rating changed, or recommendations/limitations were added/removed, then all "Approved" votes are reset and everyone must re-review

#### Pre-Transition Warnings

When attempting to advance a validation request to **PENDING_APPROVAL** status, the system checks for conditions that may require attention. These warnings do not block the transition but alert you to outstanding items that should be addressed.

**How Warnings Appear:**

1. Click the button to advance to Pending Approval
2. If any warnings exist, a modal displays with warning details
3. You can choose to **Proceed Anyway** or **Cancel** to address issues first

**Warning Types:**

| Warning | Condition | Severity | Recommended Action |
|---------|-----------|----------|-------------------|
| **PENDING_RECOMMENDATIONS** | The model has active recommendations not yet Closed or Superseded | Warning | Verify recommendations are being tracked and have appropriate response plans |
| **UNADDRESSED_ATTESTATIONS** | Pending attestation items exist that haven't been completed | Warning | Complete required attestations or document why they're pending |

**Example Warning Display:**

```
⚠ Pre-Transition Warnings

Please review the following before advancing to Pending Approval:

WARNINGS (2)
─────────────────────────────────────────
• Credit Risk Scorecard - Pending Recommendations
  2 active recommendations require response

• Credit Risk Scorecard - Unaddressed Attestations
  1 pending attestation item needs attention

These are advisory warnings. You may proceed after reviewing.

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
- Model version status behavior:
  - **Initial Validations**: Reverts from **IN_VALIDATION** to **DRAFT**
  - **Re-validations**: Approved models generally remain **APPROVED**, unless the validation due date passes while on hold (see *Expiration* below)
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
- Linked model versions revert to **DRAFT** status (for initial validations only; approved models remain **APPROVED** unless already expired)
- Preserved in history for audit purposes

**Revision**
- Sent back for specific changes
- Approver or reviewer requests modifications
- Work resumes with targeted focus

### Expiration

For re-validations of approved models, the model normally retains its **APPROVED** status while the new validation is in progress. However, if the defined re-validation due date passes before the validation is complete:

- **Validation In Progress**: If substantive work (Planning or later) is actively underway, the model status changes to **VALIDATION_IN_PROGRESS** (overdue but active).
- **Expired**: If the due date passes and no active validation is in substantive stages (or if the active request is put On Hold), the status changes to **EXPIRED**.

> **Note**: Putting a re-validation request **On Hold** may cause the model to expire if the hold duration pushes the timeline past the due date.

---

## 5. Validation Plan & Scope

### What is a Validation Plan?

The validation plan documents which components of the bank's validation standard will be performed. It uses a **risk-based matrix** that automatically defines expectations (Required, If Applicable, Not Expected) based on the model's risk tier.

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
- If you remove the **last** validator while the request is still in **Planning**, the request automatically reverts to **Intake**
- In other stages, removing the last validator is blocked
- The system tracks all assignment changes in the audit log

---

## 7. Outcomes & Ratings

### Validation Outcome

When validation work is complete, the outcome must be documented. The outcome can be entered starting from the **Review** stage, and **must be created before the request can move to Pending Approval**.

1. Navigate to the **Outcome** tab
2. Enter the required information:
   - **Overall Rating**: Select from configured ratings (labels may vary by organization)
   - **Executive Summary**: Document key conclusions
   - **Effective Date**: When the validation takes effect
   - **Expiration Date**: Required for INTERIM validations

### Validation Scorecard

If your organization uses the **Scorecard** feature, the validation detail page includes a **Scorecard** tab. It provides structured ratings by section and criterion and summarizes the overall assessment.

**What you’ll see:**
- A section-by-section rating summary
- Individual criterion ratings with optional comments
- An overall scorecard outcome
- A one‑click PDF export for sharing and record‑keeping

**Current rating scale (default configuration):**
- Green / Green‑ / Yellow+ / Yellow / Yellow‑ / Red (numeric 6–1)
- N/A (0) for not applicable criteria

> **Configurable**: Scorecard sections, criteria, weights, and prompts are admin‑managed. The Scorecard tab always reflects the current configuration in your environment.

### Findings & Recommendations

Recommendations are used to track remediation work identified during validation. They have their own lifecycle (e.g., Open → In Progress → Closed) and are tracked independently of the overall validation outcome.

> **Configurable**: Recommendation statuses and priorities are administrator‑configured. For details on creating and managing recommendations, see the **[Recommendations User Guide](USER_GUIDE_RECOMMENDATIONS.md)**.

### Limitations Linked to Validation

The **Limitations** tab on a validation request shows limitations linked to that request. This view is read‑only; limitations are created and managed from the **Model → Limitations** tab and then linked to the validation.

> **Configurable**: Limitation categories and significance labels are taxonomy‑driven and may differ from the examples shown in screenshots.

### Overall Ratings

| Rating | Meaning |
|--------|---------|
| **Fit for Purpose** | Model is suitable for its intended use without material concerns |
| **Not Fit for Purpose** | Model has critical issues requiring significant remediation before use |

> **Note:** Findings and recommendations are tracked separately from the overall rating. A model rated "Fit for Purpose" may still have open recommendations that need to be addressed.
> **Configurable**: Rating labels are taxonomy‑driven. The table above reflects the current/default labels in this system.

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

### Submitting an Approval

When you're a required approver:

1. Navigate to the **Approvals** tab
2. Find your pending approval
3. Review the validation outcome and supporting documentation
4. Click **"Decision"** (or **"Decision on Behalf"** if you're an Admin acting for the designated approver)
5. Choose your decision:
   - **Approved**: You agree with the outcome
   - **Sent Back**: Request revisions before making a decision (returns to REVISION status)
6. Add comments explaining your decision
7. Submit

> **Note**: To reject a validation entirely (e.g., wrong scope, invalid model), a **Validator** or **Admin** should **cancel the request** rather than using the approval process. The **Cancel Request** button is located on the validation request page and requires a cancellation reason. Approvers cannot perform this action directly.

### Automatic Status Transitions

- When **all required approvals** are granted, the request automatically moves to **APPROVED**
- If any approver selects **Sent Back**, the request returns to the appropriate prior stage

### Regional Approvals

For models used in multiple regions with `requires_regional_approval` enabled:
- Each region generates a separate approval requirement
- Regional approvers sign off for their respective regions
- The validation is only complete when all regional approvals are granted

### How Regional Approvals Are Determined

When a validation transitions to Pending Approval, the system determines which
regions require sign-off based on the validation's scope:

#### Scoped Validations
If the validation request has **explicitly selected regions** OR is linked to a
**REGIONAL-scope model version**, regional approvals are required ONLY for:
- Regions explicitly selected in the validation request
- Regions affected by the linked REGIONAL-scope version
- The model's governance region (wholly-owned region, always required)

**Example**: A model deployed to UK, EU, and APAC is undergoing a targeted APAC
validation. Only APAC and any governance region will require regional approval—
UK and EU approvers do NOT need to sign off.

#### Global Validations
If NO regions are selected AND the linked version has GLOBAL scope (or no version
is linked), regional approvals are required for ALL regions where the model operates:
- Model's governance region (wholly-owned)
- All model deployment regions

**Example**: A comprehensive revalidation of a model deployed to UK, EU, and APAC
with no regional scope selected will require sign-off from all three regional
approvers (if those regions have `requires_regional_approval` enabled).

#### Summary Table (Priority Order)

| Priority | Condition | Regional Approvals Required |
|----------|-----------|---------------------------|
| 1 (Highest) | User explicitly selects regions | Selected regions + REGIONAL version regions + governance |
| 2 | Any linked version is GLOBAL | All deployment regions + governance |
| 3 | Only REGIONAL versions linked | Version's affected regions + governance |
| 4 (Fallback) | No versions linked | All deployment regions + governance |

> **Note on Mixed Scopes**: If a validation covers multiple models and one has a
> GLOBAL version while another has a REGIONAL version, the system requires
> approval from ALL deployment regions. This ensures the GLOBAL version receives
> proper oversight from all jurisdictions where the model operates.

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

The impact on version status depends on whether you are validating a **new version** (starting as DRAFT) or re-validating an **existing version** (already APPROVED).

#### Scenario A: New Model or New Version
*Applies when validating a new model or a major version update (e.g., v2.0).*

| Validation Status | Version Status Change |
|-------------------|-------------------|
| Request moves to **IN_PROGRESS** | DRAFT → **IN_VALIDATION** |
| Request reaches **APPROVED** | IN_VALIDATION → **APPROVED** |
| Request is **CANCELLED** or **ON_HOLD** | IN_VALIDATION → **DRAFT** |

#### Scenario B: Revalidation of Existing Version
*Applies when performing periodic review of a version that is already in production.*

| Validation Status | Version Status Change |
|-------------------|-------------------|
| Request moves to **IN_PROGRESS** | **APPROVED** (No Change) |
| Request reaches **APPROVED** | **APPROVED** (No Change) |
| Request is **CANCELLED** or **ON_HOLD** | **APPROVED** (No Change) |

> **Note**: Even if the version status remains APPROVED, the model may be flagged as **EXPIRED** or **VALIDATION_IN_PROGRESS** at the model level if the validation due date passes. See [Validation Compliance Statuses](#validation-compliance-statuses) for details.

### Version Activation

After approval, the model owner can activate the approved version:
1. Navigate to the model's Versions tab
2. Find the approved version
3. Click **"Activate"**
4. The version becomes **ACTIVE**, and any prior active version becomes **SUPERSEDED**

### Version States

| Status | Meaning | Editable? |
|--------|---------|----------|
| **DRAFT** | Initial state, not yet validated | **Yes** (Conditional*) |
| **IN_VALIDATION** | Validation work is in progress | **No** (Locked) |
| **APPROVED** | Validation complete | **No** (Locked) |
| **ACTIVE** | Currently deployed | **No** (Locked) |
| **SUPERSEDED** | Replaced by newer version | **No** (Locked) |

*\*Conditional Editing*: 
- **Unlinked Drafts**: Model Owners can fully edit DRAFT versions that are not yet attached to a validation request.
- **Linked Drafts (Intake/Planning)**: Once a version is linked to a validation request (in Intake or Planning stages), it is **locked for Model Owners** but can still be edited by **Validators/Admins**.

**What can be edited?**
When a version is in an editable state, specific fields can be updated:
- **Version Number**: e.g., changing from 1.0 to 1.1 (must be unique)
- **Change Type**: e.g., upgrading from Minor to Major
- **Change Description**: The detailed release notes
- **Planned Production Date**: The targeted implementation date

---

## 11. Dashboards & Monitoring

### Validation Workflow Dashboard

The main validation list provides filtering and sorting:

**Filters Available**:
- Status (Intake, Planning, In Progress, etc.)
- Priority (Urgent, Standard — list is configurable)
- Validation Type (Initial, Comprehensive, Targeted, Interim, Change — list is configurable)
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

> **Configurable**: These values reflect the current/default configuration in this environment. Your organization can adjust them in the Validation Policies page.

### Configuring Validation Policies (Configuration Section)

Administrators can configure both **risk-tier-based policies** and **workflow SLA timelines** through dedicated configuration pages. This section walks through how to access and modify these settings.

#### Accessing Policy Configuration

Navigate to the configuration pages using the sidebar:

1. Click on the **Configuration** section in the left navigation panel
2. Under **Workflow & Policies**, you'll find two configuration pages:
   - **Workflow Config** — Global workflow SLA timelines
   - **Validation Policies** — Risk-tier-specific validation settings

> **Note:** Only users with the **Admin** role can modify these settings. Non-admin users can view the configurations but cannot make changes.

#### Validation Policies Page

**Path:** Configuration → Validation Policies

This page displays a table of validation policies, one row per risk tier (High, Medium, Low). Each policy controls:

| Field | Description | Typical Range |
|-------|-------------|---------------|
| **Re-Validation Frequency** | Time from last validation completion to next validation submission/intake | 12–24 months |
| **Grace Period** | Additional time after submission due date before the item is considered overdue | 1–6 months |
| **Completion Lead Time** | Additional days after grace period ends to complete the validation | 30–120 days |
| **Description** | Optional notes explaining the policy rationale | Free text |

**To edit a policy:**
1. Click the **Edit** button on the desired risk tier row
2. Modify the numeric values in the input fields
3. Click **Save** to apply changes, or **Cancel** to discard

**Info Box Reference:**
The page includes a helpful calculation example showing how these values combine to determine when a validation becomes overdue:

```
Overdue Calculation Example (Tier 2: 18 months, 3 months grace, 90 days)
Last validation completed: Jan 1, 2024

• Submission due: Jul 1, 2025 (+ 18 months frequency)
• Submission overdue: Oct 1, 2025 (+ 3 months grace period)
• Validation overdue: Dec 30, 2025 (+ 90 days lead time)
```

#### Workflow SLA Configuration Page

**Path:** Configuration → Workflow Config

This page configures the **service level agreement timelines** that apply to all validation requests regardless of risk tier. These timelines track team performance during the workflow:

| Field | Description | Typical Value |
|-------|-------------|---------------|
| **Assignment / Claim Period** | Time allowed for a validation project to be assigned to a validator or claimed (from Intake to having a primary validator assigned) | 10 days |
| **Begin Work Period** | Time allowed for assigned validators to begin work after assignment or claim (from Planning to In Progress status) | 5 days |
| **Approval Period** | Time allowed for approvals to be obtained after requesting approval (from Pending Approval to Approved status) | 10 days |

**To update SLA settings:**
1. Modify the numeric values in the input fields (range: 1–365 days)
2. Click **Save Configuration**
3. The "Last updated" timestamp at the bottom confirms when changes were applied

**Work Completion Lead Time Note:**
The page displays an informational section explaining that work completion lead time is **not** configured here—it's determined by each model's inherent risk tier and configured in the **Validation Policies** page. This allows different completion expectations based on model complexity and risk exposure.

#### How Policies Propagate to Due Dates

The system combines values from **both** configuration pages to calculate due dates displayed throughout the application. The **Validation Overdue Date** is the sum of all policy and SLA components:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     DUE DATE CALCULATION FLOW                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAST VALIDATION COMPLETION DATE                                        │
│            │                                                            │
│            ▼                                                            │
│  ┌─────────────────────────────────────────┐                           │
│  │ + Frequency Months (from Validation     │                           │
│  │   Policies, based on risk tier)         │                           │
│  └─────────────────────────────────────────┘                           │
│            │                                                            │
│            ▼                                                            │
│  ════════════════════════════════════════════                          │
│         SUBMISSION DUE DATE                                             │
│  ════════════════════════════════════════════                          │
│            │                                                            │
│            ▼                                                            │
│  ┌─────────────────────────────────────────┐                           │
│  │ + Grace Period Months (from Validation  │                           │
│  │   Policies, based on risk tier)         │                           │
│  └─────────────────────────────────────────┘                           │
│            │                                                            │
│            ▼                                                            │
│  ════════════════════════════════════════════                          │
│         SUBMISSION OVERDUE DATE                                         │
│         (Grace Period End)                                              │
│  ════════════════════════════════════════════                          │
│            │                                                            │
│            ▼                                                            │
│  ┌─────────────────────────────────────────┐                           │
│  │ + Completion Lead Time Days             │  ← Validation Policies    │
│  │   (from Validation Policies)            │                           │
│  ├─────────────────────────────────────────┤                           │
│  │ + Assignment / Claim Period Days        │                           │
│  │   (from Workflow Config)                │  ← Workflow SLA           │
│  ├─────────────────────────────────────────┤                           │
│  │ + Begin Work Period Days                │                           │
│  │   (from Workflow Config)                │  ← Workflow SLA           │
│  ├─────────────────────────────────────────┤                           │
│  │ + Approval Period Days                  │                           │
│  │   (from Workflow Config)                │  ← Workflow SLA           │
│  └─────────────────────────────────────────┘                           │
│            │                                                            │
│            ▼                                                            │
│  ════════════════════════════════════════════                          │
│         VALIDATION OVERDUE DATE                                         │
│         (Model Compliance Deadline)                                     │
│  ════════════════════════════════════════════                          │
│                                                                         │
│  Formula: Grace Period End + Lead Time + Assignment + Begin Work +      │
│           Approval Days                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Complete Calculation Example:**
Using default settings (Tier 2: 18 months frequency, 3 months grace, 90 days lead time + 10+5+10 SLA days):

```
Last validation completed: Jan 1, 2024

• Submission Due:     Jul 1, 2025   (+ 18 months frequency)
• Submission Overdue: Oct 1, 2025   (+ 3 months grace period)
• Validation Overdue: Jan 24, 2026  (+ 90 lead time + 10 assignment + 5 begin work + 10 approval = 115 days)
```

**Workflow SLA Timelines Serve Dual Purposes:**
1. **Contribute to Validation Overdue Date** — The three SLA periods (Assignment, Begin Work, Approval) are added to the Lead Time Days when calculating the final validation overdue deadline
2. **Track Team Performance** — These same timelines are used to:
   - Calculate "time remaining" displayed in each workflow phase
   - Generate overdue alerts for delayed validations
   - Track performance metrics and SLA adherence
   - Identify validation process bottlenecks

**Key Distinction:**
- **Model Compliance Deadline** (Validation Overdue Date) = Sum of Lead Time Days + All SLA Periods; the regulatory/policy deadline that cannot be extended
- **Individual Phase SLAs** = Internal team performance targets for each workflow stage

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
| **Intake** | Request submitted, awaiting acceptance | Planning, Cancelled, On Hold |
| **Planning** | Assigning resources, defining scope | In Progress, Cancelled, On Hold |
| **In Progress** | Active validation work | Review, Cancelled, On Hold |
| **Review** | QA and peer review | Pending Approval, In Progress, Cancelled, On Hold |
| **Pending Approval** | Awaiting stakeholder sign-off | Approved, Revision, Review, In Progress, Cancelled, On Hold |
| **Revision** | Sent back for specific changes | Pending Approval, Cancelled, On Hold |
| **Approved** | Validation complete | (Terminal) |
| **On Hold** | Temporarily paused | Intake, Planning, In Progress, Review, Pending Approval, Revision, Cancelled |
| **Cancelled** | Request terminated | (Terminal) |

> **Note**: In the standard UI, **Resume Work** returns the request to the previous stage before it was put on hold. If a different target stage is needed, contact an admin.

### Approval Statuses

| Status | Description |
|--------|-------------|
| **Pending** | Awaiting approver action |
| **Approved** | Approver granted approval |
| **Sent Back** | Approver requests revisions (returns to REVISION status) |

---

*Last Updated: December 2025*

<!-- Added: Configuring Validation Policies (Admin) subsection covering admin UI walkthrough for Validation Policies and Workflow SLA Configuration pages -->

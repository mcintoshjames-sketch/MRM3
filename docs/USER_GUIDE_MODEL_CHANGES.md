# User Guide: Model Changes & Version Management

## Table of Contents

1. [Introduction](#1-introduction)
2. [Understanding Model Versions](#2-understanding-model-versions)
3. [Version Lifecycle States](#3-version-lifecycle-states)
4. [Creating a New Version (Submitting a Change)](#4-creating-a-new-version-submitting-a-change)
5. [Version Creation Blockers](#5-version-creation-blockers)
6. [Change Types & Categories](#6-change-types--categories)
7. [Version Progression Through Validation](#7-version-progression-through-validation)
8. [Version Deployment](#8-version-deployment)
9. [Managing Deployment Tasks](#9-managing-deployment-tasks)
10. [Regional Deployment Considerations](#10-regional-deployment-considerations)
11. [Bulk Deployment Operations](#11-bulk-deployment-operations)
12. [Ready to Deploy Report](#12-ready-to-deploy-report)
13. [Best Practices](#13-best-practices)
14. [Frequently Asked Questions](#14-frequently-asked-questions)

---

## 1. Introduction

### What is a Model Version?

A **model version** is a formal record of a change to a model over time. Every time a model is modified—whether it's a methodology update, data change, implementation fix, or parameter calibration—the change is tracked as a new version.

### Why Track Model Changes?

Model version management serves several critical purposes:

- **Regulatory Compliance**: Regulators require complete audit trails of model changes
- **Validation Linkage**: Each validation is tied to a specific version, proving what was reviewed
- **Deployment Control**: Ensures only validated versions reach production
- "Change Impact Analysis**: Understand what changed and when across model history
- **Rollback Capability**: Maintain historical versions for comparison or reversion
- **Approval Governance**: Enforce that changes go through proper validation before use

### The Version Management Philosophy

The system enforces a **sequential validation pipeline** philosophy:

> **One change at a time, properly validated before the next begins.**

This approach ensures:
- Clear audit trails—each change is documented and validated independently
- No orphaned work—versions don't get lost in the pipeline
- Sequential governance—validation decisions apply to a known, frozen state
- Regulatory traceability—every production change has validation evidence

---

## 2. Understanding Model Versions

### Version Anatomy

Each version record contains:

| Field | Description | Example |
|-------|-------------|---------|
| **Version Number** | Semantic identifier for this release | `2.1.0`, `3.0.0` |
| **Change Type** | MAJOR or Minor classification | MAJOR |
| **Change Category** ⚙ | Taxonomy-driven category | "Model Theory Changes" |
| **Change Description** | Detailed explanation of what changed | "Updated credit loss methodology from vintage analysis to CECL approach" |
| **Planned Production Date** | Intended deployment date | 2025-06-15 |
| **Actual Production Date** | When actually deployed (set during deployment) | 2025-06-20 |
| **Status** | Current lifecycle state | DRAFT, IN_VALIDATION, APPROVED, ACTIVE, SUPERSEDED |
| **Linked Validation** | Associated validation request | Request #42 |

### Version Numbering Conventions

While the system doesn't enforce a specific numbering scheme, most organizations follow **semantic versioning**:

```
MAJOR.MINOR.PATCH

Examples:
1.0.0 → 1.0.1  (Patch: Bug fix, no methodology change)
1.0.1 → 1.1.0  (Minor: New feature, backward compatible)
1.1.0 → 2.0.0  (Major: Breaking change, methodology overhaul)
```

**Best Practice**: Align your numbering with your change type:
- **MAJOR** change type → Increment major version (1.x.x → 2.0.0)
- **Minor** change type → Increment minor or patch version (1.0.x → 1.0.1 or 1.1.0)

### The Active Version Concept

At any given time, a model can have only **one ACTIVE version**—this is the version currently running in production. When a newer version is activated:

1. The new version becomes **ACTIVE**
2. The previous active version becomes **SUPERSEDED**
3. The transition is logged with timestamp and user

This ensures a single source of truth for "What is running in production right now?"

---

## 3. Version Lifecycle States

### The Complete Journey

```
┌──────────┐     ┌────────────────┐     ┌──────────┐     ┌────────┐     ┌────────────┐
│  DRAFT   │────►│ IN_VALIDATION  │────►│ APPROVED │────►│ ACTIVE │────►│ SUPERSEDED │
└──────────┘     └────────────────┘     └──────────┘     └────────┘     └────────────┘
     │                   │
     │                   │ (Cancel or Hold)
     │                   ▼
     └──────────► Back to DRAFT
```

### Status Definitions

| Status | Description | Editable | Can Delete |
|--------|-------------|----------|------------|
| **DRAFT** | Initial state, not yet submitted for validation | ✓ Yes | ✓ Yes |
| **IN_VALIDATION** | Validation in progress | ✓ Conditional* | ✗ No |
| **APPROVED** | Validation complete, ready for deployment | ✗ No | ✗ No |
| **ACTIVE** | Currently deployed in production | ✗ No | ✗ No |
| **SUPERSEDED** | Was active but replaced by newer version | ✗ No | ✗ No |

*\*IN_VALIDATION versions can be edited by Validators and Admins **only while** the linked validation request is in early stages (Intake, Planning, or In Progress). Once validation reaches Review or later, the version is **locked** to preserve the validation record.*

### Status Transition Rules

**DRAFT → IN_VALIDATION**
- **Trigger**: Automatic when linked validation request moves to In Progress
- **Requirements**: Version must be linked to a validation request
- **Effect**: Version becomes locked unless user is Validator/Admin and validation is in early stages

**IN_VALIDATION → APPROVED**
- **Trigger**: Automatic when linked validation request reaches Approved status
- **Requirements**: All validation approvals granted
- **Effect**: Version is fully locked, ready for deployment

**APPROVED → ACTIVE**
- **Trigger**: Manual deployment action by model owner or admin
- **Requirements**: Version must be APPROVED status
- **Effect**:
  - This version becomes ACTIVE
  - Previous ACTIVE version (if exists) becomes SUPERSEDED
  - Deployment timestamp recorded

**IN_VALIDATION → DRAFT (Reversion)**
- **Trigger**: Validation is cancelled or put on hold
- **Requirements**: Validation in terminal/hold state
- **Effect**: Version unlocked, can be edited or deleted again

---

## 4. Creating a New Version (Submitting a Change)

### Step-by-Step: Submit a Model Change

1. **Navigate to Model Details**
   - Go to the **Models** page
   - Click on the model you want to modify
   - You'll see a **Submit Change** button (green) in the page header

2. **Click "Submit Change"**
   - This opens the Create New Version modal
   - The system first checks if you're allowed to create a version (see Blockers below)

3. **Complete Version Details**

   | Field | Instructions | Required |
   |-------|--------------|----------|
   | **Version Number** | Enter semantic version (e.g., 2.1.0) | Yes |
   | **Change Type** | Select MAJOR or Minor | Yes |
   | **Change Category** ⚙ | Select from taxonomy dropdown | Yes |
   | **Change Description** | Detailed explanation of what changed | Yes |
   | **Planned Production Date** | When you intend to deploy this change | Yes |

4. **Understanding Change Description**

   A good change description should include:
   - **What changed**: Specific components modified
   - **Why it changed**: Business or technical rationale
   - **Impact**: Expected effect on model outputs or users

   **Example - Poor Description**:
   > "Updated the model"

   **Example - Good Description**:
   > "Replaced vintage-based loss methodology with CECL expected credit loss approach. Updated input data to include forward-looking macroeconomic scenarios. Expected to increase loss reserves by 15-20% due to longer forecast horizon. Change driven by new accounting standard effective January 2026."

5. **Submit**
   - Click **Create Version**
   - The version is created in DRAFT status
   - You can now link it to a validation request or continue editing

### What Happens After Creation

Once created, the version appears in the model's **Versions** tab with:
- Status badge (DRAFT)
- Edit and Delete actions available
- Option to link to validation request
- Option to create validation request for this version

---

## 5. Version Creation Blockers

The system enforces **sequential validation pipeline** rules. You cannot create a new version if:

### Blocker B1: Undeployed Version Exists

**Condition**: A previous version exists in DRAFT, IN_VALIDATION, or APPROVED status (not yet ACTIVE)

**Why It Matters**: This ensures changes proceed to production before new work begins. Having multiple pending versions creates:
- Confusion about which version is being validated
- Risk of orphaned work
- Unclear audit trails

**What You'll See**:
```
❌ Cannot Create New Version

Version 2.0.0 (APPROVED) has not been deployed yet.
Please deploy or cancel this version before creating a new one.

Current undeployed version:
• Version 2.0.0 - Status: APPROVED
• Created: 2025-05-15
• Description: Updated credit risk methodology
```

**Resolution Options**:
1. **Deploy the existing version** if it's ready
2. **Delete the existing version** if the change is no longer needed (DRAFT versions only)
3. **Wait for validation** if version is IN_VALIDATION
4. **Cancel the linked validation** if the change is obsolete

---

### Blocker B2: Version in Active Validation

**Condition**: A version is currently linked to a validation request that is NOT in APPROVED status

**Why It Matters**: A model can only have one validation in progress at a time. Starting a new change while validation is ongoing would:
- Fragment validation efforts
- Create uncertainty about what's being validated
- Violate regulatory expectation of sequential review

**What You'll See**:
```
❌ Cannot Create New Version

Version 2.0.0 is currently under active validation.
Please wait for validation to complete before creating a new version.

Active validation:
• Version: 2.0.0
• Validation Request: #42 - "Comprehensive Annual Review 2025"
• Status: IN_PROGRESS
• Assigned Validator: Jane Smith

[View Validation Request]
```

**Resolution Options**:
1. **Wait for validation to complete** (most common)
2. **Cancel the validation request** if the change is no longer needed
3. **Put validation on hold** if work needs to pause temporarily

---

### Understanding the Blocker Philosophy

These blockers implement the principle:

> **Complete each change's journey through validation and deployment before starting the next.**

This prevents:
- ❌ Multiple draft versions piling up
- ❌ Confusion about "which version are we validating?"
- ❌ Orphaned work (versions that never get deployed)
- ❌ Audit trail gaps (what happened to version 2.1.0?)

Instead, it enforces:
- ✅ Clear sequential progression
- ✅ One validation at a time
- ✅ Definitive deployment decisions
- ✅ Clean audit history

---

## 6. Change Types & Categories

### Change Type Classification

Every version must be classified as either MAJOR or Minor:

| Type | Definition | Typical Triggers | Validation Impact |
|------|------------|------------------|-------------------|
| **MAJOR** | Significant changes affecting methodology, assumptions, or model behavior | • Methodology changes<br>• New data sources<br>• Algorithm updates<br>• Output definition changes | **Comprehensive re-validation typically required** |
| **Minor** | Incremental changes that don't alter fundamental approach | • Bug fixes<br>• Parameter recalibration<br>• Documentation updates<br>• Performance optimizations | May not require full re-validation; targeted review may suffice |

### Change Categories (Taxonomy-Driven) ⚙

The system provides a configurable taxonomy of change categories. **Default categories** include:

| Category | Description | Examples |
|----------|-------------|----------|
| **Model Theory Changes** | Modifications to methodology, assumptions, or conceptual foundation | Switching from logistic to neural network, changing loss calculation methodology |
| **Implementation Changes** | Updates to code, algorithms, or calculation logic | Refactoring code, fixing calculation bugs, optimizing performance |
| **Data/Input Changes** | Changes to data sources, inputs, or preprocessing | New data vendor, additional variables, different sampling approach |
| **Parameter Changes** | Recalibration of model parameters or coefficients | Annual coefficient updates, threshold adjustments based on back-testing |
| **Output/Reporting Changes** | Modifications to outputs, reports, or result presentation | New report format, additional output metrics, dashboard changes |
| **Documentation Changes** | Updates to documentation only, no functional changes | User guide updates, technical specification corrections |

> **Note**: Administrators can customize the change category taxonomy through the Taxonomy management page. Categories can be added, modified, or deactivated based on organizational needs.

### Matching Type to Category

**Best Practice Alignment**:

```
MAJOR Change Type → Typically paired with:
  • Model Theory Changes
  • Implementation Changes (if significant)
  • Data/Input Changes (if material new sources)

Minor Change Type → Typically paired with:
  • Parameter Changes
  • Output/Reporting Changes
  • Documentation Changes
  • Implementation Changes (if just bug fixes)
```

**Example Scenarios**:

| Scenario | Type | Category | Rationale |
|----------|------|----------|-----------|
| Switching from FICO score to internal credit score | MAJOR | Data/Input Changes | Material change in primary input |
| Annual coefficient recalibration using same methodology | Minor | Parameter Changes | Routine update, no methodology change |
| Rewriting code in Python (was Excel) but same logic | MAJOR | Implementation Changes | Platform migration, even if logic unchanged |
| Fixing typos in user documentation | Minor | Documentation Changes | No functional impact |
| Adding macroeconomic overlay to loss forecasts | MAJOR | Model Theory Changes | Fundamental methodology enhancement |

---

## 7. Version Progression Through Validation

### Automatic Status Updates

Model versions automatically progress through states based on their linked validation request:

```
Version Created (DRAFT)
         │
         │ Validation moves to IN_PROGRESS
         ▼
    IN_VALIDATION ◄──────┐
         │                │ Validation goes ON_HOLD
         │                │ or CANCELLED
         │                │
         │                │ (reverts to DRAFT)
         │                │
         │ Validation     │
         │ reaches        │
         │ APPROVED       │
         ▼                │
     APPROVED ────────────┘
         │
         │ Manual deployment
         │ by model owner
         ▼
      ACTIVE
         │
         │ Newer version activated
         ▼
    SUPERSEDED
```

### Editing Permissions During Validation

The version's **editability** depends on validation stage:

| Validation Stage | Who Can Edit | What Shows in UI |
|------------------|--------------|------------------|
| **No linked validation** | Owner, Developer, Admin | "Edit" button |
| **INTAKE** (linked) | Validator, Admin | "Edit" button |
| **PLANNING** (linked) | Validator, Admin | "Edit" button |
| **IN_PROGRESS** (linked) | Validator, Admin | "Edit" button |
| **REVIEW or later** | No one | "Locked" label |
| **APPROVED** | No one | "Locked" label |

**Why Lock at Review?**

Once validation reaches the Review stage, the version must be frozen to ensure:
- Validators review exactly what will be deployed
- Approvers sign off on a fixed version
- The audit trail shows what was validated
- No last-minute changes slip in after QA

**What If I Need to Change a Locked Version?**

If you discover an issue after the version is locked:
1. **Put the validation on hold** or **send it back** to an earlier stage
2. The version automatically reverts to DRAFT (editable)
3. Make the necessary corrections
4. Resume the validation
5. The version returns to IN_VALIDATION when work resumes

---

## 8. Version Deployment

After a version is validated and APPROVED, it must be deployed to production. **Deployment is tracked per-region**—a version may be deployed to different geographic regions at different times, each with its own deployment date and status. This regional granularity allows for:

- **Staged rollouts**: Deploy to one region first, then others
- **Regional compliance**: Some regions require separate approval before deployment
- **Flexible scheduling**: Each region can have its own planned deployment date

The deployment process is managed through the **Deploy Modal**.

### Accessing the Deploy Modal

The Deploy Modal can be opened from two locations:

1. **Model Versions Tab**:
   - Navigate to the model's **Versions** tab
   - Find the APPROVED or ACTIVE version
   - Click the **Deploy** button

2. **Validation Detail Page**:
   - After a validation request reaches APPROVED status
   - Click the **Deploy Approved Version** button
   - This automatically pre-selects the validated version

### Deploy Modal Overview

The Deploy Modal displays:

| Section | Information Shown |
|---------|-------------------|
| **Version Info** | Version number, change type, change description |
| **Validation Status** | Whether the version has an approved validation |
| **Region Checklist** | All regions where the model is used/can be deployed |
| **Current Deployment** | For each region: which version is currently active and when it was deployed |
| **Lock Icons 🔒** | Indicates regions requiring separate regional approval (see below) |

### Two Deployment Modes

#### Deploy Now (Immediate)

**When to Use**: The version is ready to go into production immediately.

**What Happens**:
1. You select one or more regions
2. Enter the **Actual Production Date** (defaults to today)
3. Add optional **Deployment Notes**
4. Click **Deploy Now**
5. System creates **confirmed** deployment tasks
6. Model's regional deployment status updates immediately
7. If version has no approved validation, you must provide **Validation Override Reason**

**Validation Override**:

If you deploy before validation is approved, the system requires explanation:

```
⚠ Validation Override Required

This version does not have an approved validation.
Please provide a reason for deploying without validation.

Common reasons:
• Emergency production fix
• Interim approval granted
• Low-risk documentation-only change

Reason: [___________________________________________]
```

#### Schedule for Later (Pending)

**When to Use**: The version will be deployed on a future date.

**What Happens**:
1. You select one or more regions
2. Enter the **Planned Production Date** (future date)
3. Add optional **Deployment Notes**
4. Click **Schedule for Later**
5. System creates **pending** deployment tasks
6. Tasks appear in **My Deployment Tasks** for later confirmation
7. No validation override required (approval may be obtained before planned date)

**Apply Same Date to All**: When deploying to multiple regions, use this button to set the same planned date for all selected regions simultaneously.

---

## 10. Regional Deployment Considerations

### The Lock Icon 🔒

Some regions display a **lock icon** next to their name in the Deploy Modal. This indicates the region requires **separate regional approval**.

### When Does the Lock Appear?

A lock appears when **both** conditions are true:

1. The region has `requires_regional_approval = true` configured (set by administrators)
2. The region was **NOT** included in the validation request's scope

**Example Scenario**:

> - Model is validated for **US and EU** regions
> - Model is also deployed in **UK** region (requires regional approval)
> - Validation scope: US, EU
> - When deploying:
>   - US: ✓ No lock (included in validation)
>   - EU: ✓ No lock (included in validation)
>   - UK: 🔒 Lock icon (NOT in validation scope)

### What Happens When You Deploy to a Locked Region?

Deploying to a locked region **automatically triggers** a regional approval workflow:

1. Deployment task is created
2. System creates a **Regional Approval Request**
3. Designated regional approver receives notification
4. Regional approver must review and approve before deployment is confirmed
5. Deployment proceeds once regional approval is granted

### Footer Explanation

The Deploy Modal always shows a footer note explaining locked regions:

```
🔒 Lock Icon: Indicates regions requiring separate regional approval because
they were not included in the validation scope. Deploying to these regions
will trigger an automatic regional approval request.

Selected regions requiring regional approval: 1
```

---

## 9. Managing Deployment Tasks

### My Deployment Tasks Page

Navigate to **My Deployment Tasks** from the sidebar to see all deployment tasks assigned to you (as model owner, developer, or designated deployer).

### Task Status Icons

| Icon | Status | Description |
|------|--------|-------------|
| 🟢 | **Confirmed** | Deployment has been completed and confirmed |
| 🟡 | **Pending** | Awaiting confirmation on planned date |
| 🔴 | **Overdue** | Past the planned production date without confirmation |
| ⚫ | **Cancelled** | Deployment was cancelled |

### Available Filters

**Quick Filters** (one-click):

| Filter | Shows |
|--------|-------|
| **All** | All tasks regardless of status |
| **Overdue** | Tasks past their planned date (🔴) |
| **Due Today** | Tasks planned for today |
| **This Week** | Tasks planned within the current week |
| **Due Soon** | Tasks due within the next 7 days |
| **Upcoming** | Tasks with future planned dates beyond 7 days |

**Additional Filters**:

| Filter Type | Purpose |
|-------------|---------|
| **Search Box** | Filter by model name, version number, or region code |
| **Date Range** | Select start and end dates to filter by planned production date |
| **Status Filter** | Show only Pending, Confirmed, Overdue, or Cancelled tasks |

### Single Task Actions

For individual tasks, you can:

**Confirm Deployment**:
1. Click the **Confirm** button
2. Enter the **Actual Production Date**
3. Add optional **Confirmation Notes**
4. If validation is not approved, provide **Validation Override Reason**
5. Submit

**Adjust Date**:
1. Click the **Adjust Date** button
2. Enter the **New Planned Date**
3. Add optional **Adjustment Reason**
4. Submit

**Cancel Task**:
1. Click the **Cancel** button
2. Provide **Cancellation Reason** (optional but recommended)
3. Confirm cancellation

---

## 11. Bulk Deployment Operations

When managing multiple deployment tasks, bulk operations save time and ensure consistency.

### Selecting Multiple Tasks

1. Use the **checkboxes** in the leftmost column of the task table
2. Select individual tasks or use **Select All** at the top
3. Bulk action buttons appear above the table when tasks are selected

### Bulk Confirm

**Purpose**: Confirm multiple deployments with the same actual production date.

**Steps**:
1. Select multiple **Pending** tasks (checkboxes)
2. Click **Confirm Selected** button
3. The **Bulk Confirmation Modal** opens showing:
   - List of all selected deployments
   - Lock icons 🔒 for regions requiring regional approval
   - Warning count: "X regions will trigger regional approval"
4. Enter the **Actual Production Date** (applies to all)
5. Add optional **Confirmation Notes** (applies to all)
6. If any tasks require validation override, provide **Validation Override Reason**
7. Click **Confirm All**

**What Happens**:
- All selected tasks transition to **Confirmed** status
- Regional approval requests created for locked regions
- Model deployment status updated for each region
- Audit trail recorded for each deployment

### Bulk Adjust Dates

**Purpose**: Reschedule multiple pending deployments to a new date.

**Steps**:
1. Select multiple **Pending** tasks
2. Click **Adjust Dates** button
3. Enter the **New Planned Date** (applies to all)
4. Add optional **Adjustment Reason**
5. Click **Update Dates**

**What Happens**:
- All selected tasks update their planned production date
- Tasks remain in Pending status
- Adjustment is logged in audit trail

**Use Case**: Deployment window shifts due to business constraints or technical dependencies.

### Bulk Cancel

**Purpose**: Cancel multiple pending deployments.

**Steps**:
1. Select multiple **Pending** tasks
2. Click **Cancel Selected** button
3. Add optional **Cancellation Reason** (recommended for audit trail)
4. Click **Cancel All**

**What Happens**:
- All selected tasks move to **Cancelled** status
- Tasks remain in history but cannot be confirmed
- Cancellation logged with timestamp and user

**Use Case**: Version is superseded by a newer version, or deployment decision reversed.

### Important Notes

- Only **Pending** tasks can be confirmed, adjusted, or cancelled
- **Confirmed** and **Cancelled** tasks are locked from further changes
- All bulk operations are logged in the audit trail
- Bulk operations cannot mix tasks from different model versions (system enforces version consistency)

---

## 12. Ready to Deploy Report

### Overview

The **Ready to Deploy** report provides a centralized view of all model versions that are ready for production deployment across different regions.

**Access**:
- Navigate to **Reports** section
- Click **Ready to Deploy** report
- Or use the **Ready to Deploy** link in the navigation sidebar

### Report Structure

The report displays **one row per (version, region) combination**:

| Column | Description |
|--------|-------------|
| **Model Name** | Name of the model |
| **Model ID** | Unique model identifier |
| **Version** | Version number ready for deployment |
| **Region** | Geographic region for deployment |
| **Validation Status** | Current validation state |
| **Version Source** | How the version was determined (Explicit or Inferred) |
| **Last Updated** | When the version information was last modified |
| **Actions** | Deploy button to open Deploy Modal |

### Understanding Version Source

The **Version Source** column indicates how the system determined which version to display:

| Source | Meaning | Trust Level |
|--------|---------|-------------|
| **Explicit** | The version was explicitly selected or linked to a validation request | ✅ High - Direct validation linkage |
| **Inferred** | The system inferred the relevant version based on model state (most recent approved version) | ⚠️ Medium - Requires verification |

**Why This Matters**:

- **Explicit** versions have a direct audit trail linking the validation decision to a specific version
- **Inferred** versions require verification that the deployed version matches the validation scope
- Regulatory reviewers may ask about version traceability—the source field provides transparency
- Best practice: Ensure all validations explicitly link to versions for complete audit trails

### Available Filters

| Filter | Description |
|--------|-------------|
| **My Models Only** | Show only models where you are the owner or developer |
| **Region** | Filter by specific geographic region (dropdown) |
| **Validation Status** | Filter by validation completion state (Approved, In Progress, etc.) |
| **Search** | Filter by model name or version number |

### Using the Report

**Typical Workflow**:

1. **Filter to your models**: Enable "My Models Only"
2. **Select a region**: Choose the region you're deploying to
3. **Review validation status**: Ensure versions are approved
4. **Check version source**: Verify explicit linkage for regulatory compliance
5. **Click Deploy**: Opens the Deploy Modal pre-filtered to the selected region
6. **Execute deployment**: Follow the deployment process described in Section 8

---

## 13. Best Practices

### Version Creation

✅ **DO**:
- Create versions as soon as changes are planned, even if not implemented yet
- Use descriptive version numbers that follow your organization's convention
- Write detailed change descriptions explaining the "why" not just the "what"
- Link versions to validation requests early in the process
- Choose change types (MAJOR/Minor) that align with validation expectations

❌ **DON'T**:
- Create multiple draft versions that pile up without deployment
- Use vague change descriptions like "Updated model"
- Skip version creation for "small" changes—all changes must be tracked
- Create a version while another is in active validation (blocker B2)

### Change Documentation

✅ **DO**:
- Document technical details AND business rationale
- Explain expected impact on model outputs
- Reference related validation requests, regulatory requirements, or business initiatives
- Include information useful for validators who will review the change

❌ **DON'T**:
- Rely solely on code comments—the change description is the formal record
- Assume everyone knows the context—write for future reviewers
- Use jargon without explanation—make it readable across departments

### Deployment Planning

✅ **DO**:
- Deploy versions promptly after validation approval
- Use "Schedule for Later" when the deployment date is known in advance
- Provide clear deployment notes explaining the deployment context
- Verify regional approval requirements before deploying to new regions
- Confirm deployment tasks within 24 hours of actual deployment

❌ **DON'T**:
- Leave approved versions undeployed indefinitely
- Deploy without validation unless emergency justification exists
- Ignore regional approval locks—they exist for compliance reasons
- Forget to confirm deployment tasks after deployment completes

### Version Lifecycle Management

✅ **DO**:
- Monitor versions in IN_VALIDATION status and follow up on validation progress
- Activate approved versions when ready for production
- Keep the version history clean—delete abandoned DRAFT versions
- Review SUPERSEDED versions periodically to understand change history

❌ **DON'T**:
- Leave DRAFT versions lingering that will never be validated
- Activate versions without proper deployment through the deployment task workflow
- Delete versions that have been deployed (ACTIVE/SUPERSEDED)—they're part of the permanent audit trail

---

## 14. Frequently Asked Questions

### General Questions

**Q: Can I have multiple versions in DRAFT status?**

A: No. The system enforces a **sequential validation pipeline** with two blockers:
- **B1**: No undeployed versions (DRAFT, IN_VALIDATION, or APPROVED)
- **B2**: No version in active validation

You must deploy or delete the existing version before creating a new one.

**Q: What if I need to make an urgent fix while a validation is in progress?**

A: You have two options:
1. **Put the current validation on hold** → Version reverts to DRAFT → Make urgent fix → Resume validation
2. **Create emergency deployment** with validation override (requires strong justification)

The first option is preferred for audit trail integrity.

**Q: Can I delete a version after it's been validated?**

A: It depends on the version status:
- **DRAFT**: ✅ Yes, can be deleted
- **IN_VALIDATION**: ✗ No, cancel the validation first
- **APPROVED**: ✗ No, permanent audit record
- **ACTIVE**: ✗ No, permanent audit record
- **SUPERSEDED**: ✗ No, permanent audit record

Once a version reaches APPROVED status, it becomes part of the permanent audit trail.

---

### Version Creation Questions

**Q: Why does the system show a "Blocker B1" error when I try to create a version?**

A: There's an existing version that hasn't been deployed yet. The system requires you to either:
- Deploy the existing version, OR
- Delete it (if DRAFT), OR
- Wait for its validation to complete

This ensures changes proceed sequentially through the pipeline.

**Q: What's the difference between MAJOR and Minor change types?**

A:
- **MAJOR**: Significant changes affecting methodology, assumptions, or model behavior → Typically requires comprehensive re-validation
- **Minor**: Incremental changes like bug fixes, parameter updates, or documentation → May only require targeted review

Align this with your organization's validation policy—different risk tiers may have different thresholds for what constitutes "major."

**Q: Do I need to create a version for documentation-only changes?**

A: Yes, if you want a formal record. Even documentation changes should be tracked for audit purposes. However, mark it as:
- Change Type: **Minor**
- Change Category: **Documentation Changes**
- This may not require formal validation depending on your organization's policy

---

### Deployment Questions

**Q: What's the difference between "Deploy Now" and "Schedule for Later"?**

A:
- **Deploy Now**: Creates confirmed deployment tasks, updates production status immediately, requires validation override if not validated
- **Schedule for Later**: Creates pending deployment tasks, lets you plan future deployment, no override needed

Use "Schedule for Later" when you know the deployment date but aren't ready to execute yet.

**Q: Why do some regions show a lock icon 🔒?**

A: The region requires **separate regional approval** because it was not included in the original validation scope. Deploying to this region will trigger an automatic regional approval request.

**Q: Can I deploy the same version to different regions on different dates?**

A: Yes! Each region can have its own deployment date. This is common when:
- Regional compliance requirements differ
- Regions have different business calendars or blackout periods
- Phased rollouts are used to manage risk

**Q: What happens if I miss a deployment task's planned date?**

A: The task shows 🔴 **Overdue** status. This is a reminder, not a blocker—you can still confirm the deployment. However:
- Overdue tasks are tracked in reporting
- Consistent overdue deployments may indicate planning issues
- Best practice: Update the planned date if deployment is intentionally delayed

---

### Regional Approval Questions

**Q: How do I know which regions require regional approval?**

A: Check for the 🔒 lock icon in the Deploy Modal. The footer also displays a count:
> "Selected regions requiring regional approval: X"

**Q: Who is the regional approver?**

A: Regional approvers are configured by administrators in the approver roles system. Contact your Model Risk Management administrator if you need to know who approves for a specific region.

**Q: What if the regional approver rejects the deployment?**

A: The deployment task remains in **Pending** status and cannot be confirmed until regional approval is granted. You may need to:
- Provide additional documentation to the regional approver
- Address concerns raised in the rejection
- Modify the deployment approach (e.g., deploy to a different region first)

---

### Validation Integration Questions

**Q: Can I edit a version while it's IN_VALIDATION?**

A: It depends on the validation stage:
- **Intake, Planning, In Progress**: Yes, if you're a Validator or Admin
- **Review or later**: No, version is locked

To edit a locked version, put the validation on hold (reverts to DRAFT), make changes, then resume.

**Q: What happens to the version if I cancel the validation?**

A: The version automatically reverts from **IN_VALIDATION** to **DRAFT** status. You can then:
- Edit or delete the version
- Link it to a different validation request
- Leave it as a draft for future validation

**Q: Why doesn't my version automatically become ACTIVE after validation approval?**

A: APPROVED → ACTIVE transition is **manual** to give you control over deployment timing. After validation approval, you have two separate actions available:

1. **Activate** (blue button) - Changes the global version status from APPROVED to ACTIVE and supersedes the previous active version. This marks the version as the official current version in the inventory.

2. **Deploy** (purple button) - Creates regional deployment tasks to track when the version goes live in each region. This handles the operational rollout.

These are intentionally separate because:
- You may want to activate a version as the official record before all regional deployments complete
- You may want to schedule regional deployments in advance before activating
- Regional rollouts can be staggered while maintaining a single active version globally

**Typical workflow**: Activate the version to mark it as current, then use Deploy to track regional rollouts.

---

*Last Updated: December 2025*

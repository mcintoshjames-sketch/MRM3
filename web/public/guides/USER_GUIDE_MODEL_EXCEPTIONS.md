# Model Exceptions User Guide

## Table of Contents

1. [Introduction](#1-introduction)
2. [Understanding Model Exceptions](#2-understanding-model-exceptions)
3. [Exception Types](#3-exception-types)
4. [Exception Lifecycle](#4-exception-lifecycle)
5. [Viewing Exceptions](#5-viewing-exceptions)
6. [Acknowledging Exceptions](#6-acknowledging-exceptions)
7. [Closing Exceptions](#7-closing-exceptions)
8. [Automatic Exception Closure](#8-automatic-exception-closure)
9. [Exception Detection](#9-exception-detection)
10. [Role-Based Access](#10-role-based-access)
11. [Exceptions Report](#11-exceptions-report)
12. [Integration with Other Workflows](#12-integration-with-other-workflows)
13. [Frequently Asked Questions](#13-frequently-asked-questions)
14. [Appendix A: Status Reference](#appendix-a-status-reference)

---

## 1. Introduction

### What are Model Exceptions?

Model Exceptions are formal records that track situations where a model has deviated from expected governance standards or operational requirements. The system automatically detects these situations and creates exceptions that require acknowledgment and resolution.

Think of exceptions as "flags" that signal something requires attention—whether it's a performance issue, a model being used outside its intended scope, or a model deployed before completing validation.

### Why Model Exceptions Matter

Model exceptions provide a structured approach to:

| Benefit | Description |
|---------|-------------|
| **Risk Visibility** | Identify and track models with governance concerns |
| **Regulatory Compliance** | Demonstrate proactive monitoring and issue resolution |
| **Accountability** | Create an audit trail of how issues are identified and resolved |
| **Prioritization** | Focus attention on models requiring immediate action |
| **Trend Analysis** | Track patterns to identify systemic issues |

### Who Uses Model Exceptions?

| Role | Primary Activities |
|------|-------------------|
| **Model Owner** | Reviews exceptions on owned models, understands issues |
| **Administrator** | Acknowledges, closes, and manages all exceptions |
| **Validator** | Views exceptions during validation assessments |
| **Compliance/Risk** | Monitors exception metrics and trends |

---

## 2. Understanding Model Exceptions

### The Exception Framework

Model exceptions operate on a simple lifecycle:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXCEPTION DETECTED                                 │
│  System identifies a governance issue with a model                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐             │
│   │     OPEN     │───►│   ACKNOWLEDGED   │───►│    CLOSED    │             │
│   └──────────────┘    └──────────────────┘    └──────────────┘             │
│          │                    │                      │                       │
│          │                    │                      │                       │
│     Exception          Admin confirms         Issue resolved                │
│     detected           awareness of          (manually or                   │
│                        the issue             automatically)                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Exception Codes

Every exception receives a unique code in the format:

```
EXC-YYYY-NNNNN
```

For example: `EXC-2025-00042`

This code:
- **EXC**: Identifies it as an exception
- **YYYY**: The year the exception was detected
- **NNNNN**: A sequential number

Use this code when referencing exceptions in communications or documentation.

---

## 3. Exception Types

The system tracks three types of exceptions, each addressing a different governance concern:

### Type 1: Unmitigated Performance Problem

**What it means**: A model has shown critical performance issues (RED monitoring results) that either:
- Persist across multiple monitoring cycles, OR
- Have no documented remediation plan (recommendation)

**Why it matters**: Performance issues can affect business decisions. Unaddressed RED results indicate the model may not be fit for its intended use.

**Common causes**:
- Model degradation over time
- Changes in underlying data patterns
- Missing or delayed remediation actions

**How to resolve**: Create a recommendation documenting the remediation plan, or demonstrate that performance has returned to acceptable levels.

---

### Type 2: Model Used Outside Intended Purpose

**What it means**: During the annual attestation, the model owner indicated that the model is being used outside its validated scope.

**Why it matters**: Models are validated for specific use cases. Using a model outside its intended purpose introduces unvalidated risk.

**Common causes**:
- Business expansion into new use cases
- Gradual scope creep over time
- Misunderstanding of model limitations

**How to resolve**: Either update the model's validation to cover the new use case, or restrict model usage to the validated scope.

---

### Type 3: Model In Use Prior to Full Validation

**What it means**: A model version was deployed and confirmed in use before validation approval was obtained.

**Why it matters**: Deploying unvalidated models introduces unknown risks to business decisions.

**Common causes**:
- Urgent business needs bypassing normal processes
- Miscommunication about validation status
- Process gaps in deployment controls

**How to resolve**: Complete a full validation (not interim) for the model to demonstrate it is fit for purpose.

---

### Summary Comparison

| Type | Trigger | Auto-Closes? | Resolution Path |
|------|---------|--------------|-----------------|
| **Unmitigated Performance** | RED monitoring without recommendation | Yes (when metric improves) | Create recommendation OR improve performance |
| **Outside Intended Purpose** | Attestation indicates misuse | No (manual only) | Update validation scope OR restrict usage |
| **Prior to Validation** | Deployment before approval | Yes (on full validation approval) | Complete full validation |

---

## 4. Exception Lifecycle

### Status: OPEN

**Definition**: The exception has been detected by the system and requires attention.

**Who can see it**: Model owners, administrators, and users with access to the model.

**What happens next**: An administrator should review and acknowledge the exception.

**Visual indicator**: Red status badge

---

### Status: ACKNOWLEDGED

**Definition**: An administrator has confirmed awareness of the exception and its implications.

**Who can act**: Administrators only

**What it means**: The organization is aware of the issue and is working toward resolution.

**Notes**: Administrators can optionally add acknowledgment notes explaining the context or planned actions.

**Visual indicator**: Yellow status badge

---

### Status: CLOSED

**Definition**: The exception has been resolved, either manually by an administrator or automatically by the system.

**Closure requirements** (for manual closure):
- **Closure narrative**: A description of how the issue was resolved (minimum 10 characters)
- **Closure reason**: Selected from predefined options

**Closure reasons**:
- **No longer an exception**: The underlying condition has been resolved
- **Exception overridden**: Management has accepted the risk
- **Other**: Custom circumstances requiring explanation

**Visual indicator**: Green status badge

---

### Lifecycle Flow

```
                          ┌─────────────────────────────────────────┐
                          │           EXCEPTION DETECTED            │
                          │     (System automatically creates)      │
                          └─────────────────────────────────────────┘
                                            │
                                            ▼
                          ┌─────────────────────────────────────────┐
                          │                 OPEN                    │
                          │  • Visible to relevant users            │
                          │  • Requires acknowledgment              │
                          │  • Counted in open exception metrics    │
                          └─────────────────────────────────────────┘
                                            │
                                            │ Admin clicks "Acknowledge"
                                            │ (optional notes)
                                            ▼
                          ┌─────────────────────────────────────────┐
                          │            ACKNOWLEDGED                 │
                          │  • Organization is aware                │
                          │  • Resolution in progress               │
                          │  • Still counts as "not closed"         │
                          └─────────────────────────────────────────┘
                                            │
                          ┌─────────────────┴─────────────────┐
                          │                                   │
                    Manual Close                        Auto-Close
                    (Admin action)                    (System trigger)
                          │                                   │
                          ▼                                   ▼
                          ┌─────────────────────────────────────────┐
                          │                CLOSED                   │
                          │  • Issue resolved                       │
                          │  • Full audit trail preserved           │
                          │  • No longer counts in open metrics     │
                          └─────────────────────────────────────────┘
```

---

## 5. Viewing Exceptions

### From the Model Details Page

1. Navigate to **Models** and select a model
2. Click the **Exceptions** tab
3. View all exceptions for that model

**What you'll see**:
- Exception code and type
- Current status
- Detection date
- Description of the issue
- The exception description (often includes the source record IDs)

**Exception count badge**: The **Exceptions** tab shows a red count badge indicating the number of **OPEN** exceptions (acknowledged exceptions are not included in the badge count).

---

### From the Model Exceptions Report Page

The report page provides organization-wide visibility for **Administrators**, **Validators**, **Global Approvers**, and **Regional Approvers**. Other users can also access the report but will only see exceptions for models they have access to.

1. In the left navigation, click **Model Exceptions**
2. View exceptions (organization-wide for privileged roles; otherwise limited to models you can access)

**Available filters**:
- **Status**: Open, Acknowledged, Closed, or All
- **Type**: Filter by exception type
- **Region**: Filter by model deployment region

**Summary cards** show:
- Total Open exceptions
- Total Acknowledged exceptions
- Total Closed exceptions
- Breakdown by exception type

---

## 6. Acknowledging Exceptions

### Who Can Acknowledge

Only **Administrators** can acknowledge exceptions.

### When to Acknowledge

Acknowledge an exception when:
- You have reviewed the exception and understand its implications
- You want to signal that the organization is aware of the issue
- You are beginning to work on a resolution

### How to Acknowledge

1. Navigate to the exception (from Model Details or the Model Exceptions report page)
2. Click the **Acknowledge** button
3. Optionally enter acknowledgment notes
4. Click **Confirm**

### What Happens After Acknowledgment

- Status changes from OPEN to ACKNOWLEDGED
- A record is added to the exception's status history
- The exception remains visible and tracked
- Acknowledgment date and user are recorded

---

## 7. Closing Exceptions

### Who Can Close

Only **Administrators** can manually close exceptions.

### When to Close

Close an exception when:
- The underlying issue has been resolved
- Management has made a decision to accept the risk
- The exception is no longer applicable

### Closure Requirements

Both fields are required to close an exception:

| Field | Requirement |
|-------|-------------|
| **Closure Narrative** | Minimum 10 characters explaining how the issue was resolved |
| **Closure Reason** | Select from: "No longer an exception", "Exception overridden", or "Other" |

### How to Close

1. Navigate to the exception
2. Click the **Close** button
3. Select a closure reason from the dropdown
4. Enter a closure narrative explaining the resolution
5. Click **Close Exception**

### Example Closure Narratives

**Type 1 (Unmitigated Performance)**:
> "KS statistic returned to green in Q3 2025 monitoring cycle after implementation of model recalibration. See REC-2025-00015 for remediation details."

**Type 2 (Outside Intended Purpose)**:
> "Model scope updated and revalidation completed to include commercial lending use case. Validation VR-2025-00089 approved on 2025-08-15."

**Type 3 (Prior to Validation)**:
> "Full validation completed and approved. Model is now validated for production use. See validation request VR-2025-00102."

---

## 8. Automatic Exception Closure

Some exceptions can be closed automatically by the system when the underlying condition is resolved.

### Type 1: Auto-Close on Performance Improvement

**Trigger**: When a GREEN or YELLOW monitoring result is recorded for the same model/metric that previously had a RED result and an OPEN/ACKNOWLEDGED Type 1 exception exists.

**Automatic closure details**:
- Narrative: "Metric returned to GREEN/YELLOW in cycle [id]" (system-generated)
- Reason: "No longer an exception"
- Closed by: System (no user attributed)

**Important**: This only applies to Type 1 exceptions. Auto-closure is evaluated when results are entered/recorded (it is not tied to cycle approval).

---

### Type 3: Auto-Close on Full Validation Approval

**Trigger**: When a **full** validation request (not interim) is approved for the model.

**What qualifies as "full" validation**:
- Initial Validation
- Comprehensive Validation
- Targeted Review

**What does NOT trigger auto-close**:
- Interim Validation (model remains in exception status)

**Automatic closure details**:
- Narrative: "Auto-closed: Full validation approved on [date]"
- Reason: "No longer an exception"
- Closed by: System (no user attributed)

---

### Type 2: Manual Close Only

Type 2 exceptions (Outside Intended Purpose) are **never** automatically closed.

**Rationale**: This exception type requires human judgment to confirm that either:
- The model's scope has been properly updated through revalidation, OR
- The model is no longer being used outside its intended purpose

An administrator must manually close these exceptions with appropriate documentation.

---

### Auto-Close Indicator

In the exception detail views, auto-closed exceptions are indicated by:
- "Auto-closed" labeling and/or an **Auto-Closed: Yes** field
- A system-generated closure narrative (no “closed by” user)

---

## 9. Exception Detection

### How Exceptions Are Detected

Exceptions are detected automatically at specific workflow points:

| Exception Type | Detection Trigger |
|----------------|-------------------|
| **Unmitigated Performance** | When a monitoring cycle is approved with RED results |
| **Outside Intended Purpose** | When an attestation is submitted with "No" for use restrictions |
| **Prior to Validation** | When a deployment task is confirmed before validation approval |

### Manual Detection (Admin Only)

Administrators can manually run detection from the **Model Exceptions** report page:

1. In the left navigation, click **Model Exceptions**
2. Click **Detect All Exceptions**
3. The system scans **active** models and creates any new exceptions it finds

### Detection Summary

After detection runs, you'll see a summary showing:
- Type 1 exceptions created
- Type 2 exceptions created
- Type 3 exceptions created
- Total new exceptions

### One Exception Per Source Record

The system creates **at most one exception per source record** (monitoring result, attestation response, or deployment task). This is enforced by a database constraint.

**Practical implication for Type 1 exceptions**: A RED monitoring result may qualify as an exception for multiple reasons:
- Missing a recommendation, AND
- Persisting from a previous cycle (persistent RED)

In this case, **only one exception will be created**. The exception description indicates which condition triggered the exception. Once an exception exists for that monitoring result, no additional exceptions will be created for the same result.

**Duplicate Prevention**:
- If an exception already exists for a source entity, a new one will not be created
- This ensures clean audit trails and prevents exception duplication

---

## 10. Role-Based Access

### What All Users Can Do

| Action | Availability |
|--------|--------------|
| View exceptions on models they have access to | All users |
| See exception counts (per model) | All users |
| View exception details and history | All users |
| Filter exceptions by status (Model Details → Exceptions) | All users |

### What Privileged Roles Can Do (Report Page)

The following roles have organization-wide visibility on the **Model Exceptions** report page:
- **Administrator**
- **Validator**
- **Global Approver**
- **Regional Approver**

| Action | Availability |
|--------|--------------|
| View organization-wide exception summaries | Admin, Validator, Global Approver, Regional Approver |
| Filter by status/type/region | Admin, Validator, Global Approver, Regional Approver |
| Export the current view to CSV | All users (exports only what user can see) |

### What Only Administrators Can Do

| Action | Admin Only |
|--------|------------|
| Acknowledge exceptions | Yes |
| Close exceptions | Yes |
| Create exceptions manually | Yes |
| Trigger exception detection | Yes |

### Model Owner Visibility

Model owners see their models' exceptions in:
- Model Details page → Exceptions tab
- Activity Timeline (exception events)

---

## 11. Exceptions Report

### Accessing the Report

1. In the left navigation, click **Model Exceptions**

### Report Features

**Summary Cards**:
- Open exceptions count
- Acknowledged exceptions count
- Closed exceptions count
- Total exceptions

**Breakdown by Type**:
- Count of each exception type (displayed below summary cards)

**Filters**:
- **Status**: All, Open, Acknowledged, Closed
- **Exception Type**: All, Unmitigated Performance, Outside Intended Purpose, Prior to Validation
- **Region**: Filter by model deployment region

**Pagination**:
- 50 exceptions per page
- Navigate between pages

### Exception List Columns

| Column | Description |
|--------|-------------|
| **Code** | Unique exception identifier (EXC-YYYY-NNNNN) |
| **Model** | Model name (clickable link) |
| **Type** | Exception type (friendly label) |
| **Status** | Current status with color indicator |
| **Detected** | Date the exception was detected |
| **Actions** | View details, Acknowledge, Close (based on permissions) |

### CSV Export

Click **Export CSV** to download the **current page/view** (up to 50 rows) with:
- Exception code, model ID, model name
- Exception type, status, description
- Detected date, acknowledged date, closed date
- Auto-closed flag

---

## 12. Integration with Other Workflows

### Monitoring Workflow Integration

**Exception Creation**:
- When a monitoring cycle is approved with RED results that lack recommendations, Type 1 exceptions are created
- RED results persisting across consecutive cycles also trigger Type 1 exceptions

**Exception Auto-Close**:
- When new monitoring results show improvement (GREEN or YELLOW), Type 1 exceptions auto-close

**Creating Recommendations from Breaches**:
- From the monitoring results grid, you can create a recommendation directly linked to a RED metric
- Properly linked recommendations prevent Type 1 exceptions from being created

---

### Attestation Workflow Integration

**Exception Creation**:
- When a model owner answers "No" to the use restrictions question (ATT_Q10_USE_RESTRICTIONS), a Type 2 exception is created
- This occurs when the attestation is submitted

**Resolution**:
- Type 2 exceptions must be manually closed after addressing the scope issue
- Consider revalidating the model to cover additional use cases

---

### Validation Workflow Integration

**Exception Auto-Close**:
- When a full validation request is approved, Type 3 exceptions on that model auto-close
- Interim validations do NOT trigger auto-close

**Exception Visibility**:
- Open exceptions are visible during validation planning
- Validators can see if a model has governance concerns

---

### Deployment Workflow Integration

**Exception Creation**:
- When a deployment task is confirmed with `deployed_before_validation_approved = True`, a Type 3 exception is created
- This flags models in use without completed validation

---

### Activity Timeline Integration

Exception events appear in the model's activity timeline:
- Exception detected (OPEN)
- Exception acknowledged
- Exception closed (manual or auto)

This provides a complete audit trail within the model's history.

---

### Dashboard Integration

**News Feed**:
- Exception status changes appear in the dashboard news feed
- Provides organization-wide visibility of exception activity

**Model Details**:
- The Model Details **Exceptions** tab shows an open/acknowledged count badge

---

## 13. Frequently Asked Questions

### General Questions

**Q: How do I know if my model has exceptions?**
A: Navigate to your model's detail page and look for a red count badge on the **Exceptions** tab. Administrators, Validators, and Approver roles can use the **Model Exceptions** report page for organization-wide visibility.

**Q: Can exceptions be deleted?**
A: No, exceptions cannot be deleted. They can only be closed. This ensures a complete audit trail for regulatory compliance.

**Q: Who gets notified when an exception is created?**
A: Currently, notifications are not sent automatically. Users should check Model Details → **Exceptions** for their models; Administrators, Validators, and Approver roles can also review the **Model Exceptions** report page for organization-wide visibility.

---

### Exception Detection Questions

**Q: Why wasn't an exception created for my RED monitoring result?**
A: Type 1 exceptions are only created when:
1. The monitoring cycle has been **approved** (not while in progress)
2. There is no active recommendation linked to that specific metric
Check if a recommendation exists for the RED result or if the cycle is still in progress.

**Q: My model was deployed before validation—why is there no exception?**
A: Type 3 exceptions are only created when the deployment task is marked as confirmed AND the `deployed_before_validation_approved` flag is set. If the flag wasn't set during deployment confirmation, no exception will be created.

**Q: Can I prevent exceptions from being created?**
A: Yes, for Type 1 exceptions:
- Create recommendations for RED results during the monitoring review phase
- Link recommendations to the specific metric using "Create Recommendation" from the breach panel

---

### Acknowledgment and Closure Questions

**Q: What's the difference between acknowledging and closing?**
A:
- **Acknowledging** signals awareness—the issue is recognized and being worked on
- **Closing** signals resolution—the issue has been addressed and documented

**Q: Can I close an exception without acknowledging it first?**
A: Yes, you can close an exception directly from OPEN status. However, acknowledging first provides a clearer audit trail showing when the organization became aware of the issue.

**Q: Why can't I close a Type 2 exception?**
A: Type 2 exceptions (Outside Intended Purpose) can be closed, but only manually by an administrator. They never auto-close because human judgment is required to confirm the issue has been properly addressed.

**Q: What happens if I close an exception but the issue recurs?**
A: If the same underlying condition triggers again (e.g., another RED result without a recommendation), a **new** exception will be created with a new exception code. The original closed exception remains in history.

---

### Auto-Close Questions

**Q: My metric improved but the exception didn't auto-close. Why?**
A: Check that:
1. A GREEN or YELLOW result was recorded for the **same model and metric** (the exception is metric-specific)
2. The exception is still OPEN or ACKNOWLEDGED (not already closed)

**Q: The validation was approved but the Type 3 exception is still open. Why?**
A: Type 3 exceptions only auto-close on **full** validation approval. Check:
1. The validation type is not "Interim"
2. The validation request has reached APPROVED status
3. The validation is for the same model as the exception

**Q: Can I prevent auto-close if I want to keep tracking the issue?**
A: Auto-close cannot be prevented. However, if the underlying issue recurs, a new exception will be created automatically.

---

### Reporting Questions

**Q: How do I export all exceptions for a specific model?**
A: Use the model’s **Exceptions** tab to review that model’s exceptions. The **Model Exceptions** report page export downloads the **current page/view**, so exporting “everything” may require paging or using the API.

**Q: Are closed exceptions included in metrics?**
A: Closed exceptions do not count toward "open exception" KPIs, but they are included in total counts and historical reports.

---

## Appendix A: Status Reference

### Exception Statuses

| Status | Description | Who Can Act | Next Statuses |
|--------|-------------|-------------|---------------|
| **OPEN** | Exception detected, awaiting review | Administrators | ACKNOWLEDGED, CLOSED |
| **ACKNOWLEDGED** | Organization aware, resolution in progress | Administrators | CLOSED |
| **CLOSED** | Exception resolved | (Terminal) | — |

### Exception Types

| Type | Code | Description |
|------|------|-------------|
| **Type 1** | UNMITIGATED_PERFORMANCE | RED monitoring result persisting or without recommendation |
| **Type 2** | OUTSIDE_INTENDED_PURPOSE | Model used outside validated scope |
| **Type 3** | USE_PRIOR_TO_VALIDATION | Model deployed before validation approval |

### Closure Reasons

| Code | Label | When to Use |
|------|-------|-------------|
| NO_LONGER_EXCEPTION | No longer an exception | The underlying condition has been resolved |
| EXCEPTION_OVERRIDDEN | Exception overridden | Management has accepted the risk |
| OTHER | Other | Custom circumstances |

### Status Colors

| Status | Color | Visual |
|--------|-------|--------|
| **OPEN** | Red | Requires immediate attention |
| **ACKNOWLEDGED** | Yellow | In progress, being addressed |
| **CLOSED** | Green | Resolved, no action needed |

---

*Last Updated: December 2025*

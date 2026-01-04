# Performance Monitoring User Guide

## Table of Contents

1. [Introduction](#1-introduction)
2. [Understanding Performance Monitoring](#2-understanding-performance-monitoring)
3. [Key Concepts](#3-key-concepts)
4. [Monitoring Plan Lifecycle](#4-monitoring-plan-lifecycle)
5. [The Monitoring Cycle Workflow](#5-the-monitoring-cycle-workflow)
6. [Entering Monitoring Results](#6-entering-monitoring-results)
7. [Understanding Metrics and Thresholds](#7-understanding-metrics-and-thresholds)
   - [Creating Recommendations from Breaches](#creating-recommendations-from-breaches)
   - [Exception Automation (Type 1)](#exception-automation-type-1-unmitigated-performance)
8. [Approvals Process](#8-approvals-process)
9. [Plan Versioning](#9-plan-versioning)
10. [Role-Based Workflows](#10-role-based-workflows)
11. [My Monitoring Tasks](#11-my-monitoring-tasks)
12. [Trend Analysis & Historical Views](#12-trend-analysis--historical-views)
13. [Dashboards & Reporting](#13-dashboards--reporting)
14. [Frequently Asked Questions](#14-frequently-asked-questions)
15. [Appendix A: Status Reference](#appendix-a-status-reference)
16. [Appendix B: CSV Import Guide](#appendix-b-csv-import-guide)

---

## 1. Introduction

### What is Performance Monitoring?

Performance Monitoring is the ongoing process of measuring and assessing model performance against established thresholds and expectations. Unlike validation (which is a point-in-time assessment), monitoring is a continuous activity that tracks how models behave over time.

The Performance Monitoring module provides a structured approach to:

- Define Key Performance Metrics (KPMs) for each model or group of models
- Set thresholds that define acceptable, warning, and critical performance levels
- Execute regular monitoring cycles on a defined schedule
- Track results over time to identify trends and issues
- Escalate breaches requiring management attention
- Maintain audit trails for regulatory compliance

### Why Performance Monitoring Matters

Effective model performance monitoring helps organizations:

| Benefit | Description |
|---------|-------------|
| **Early Warning** | Detect model degradation before it impacts business decisions |
| **Regulatory Compliance** | Demonstrate ongoing oversight as required by regulators (SR 11-7, SS1/23) |
| **Risk Management** | Identify models that may need revalidation or remediation |
| **Accountability** | Establish clear ownership for monitoring activities |
| **Documentation** | Build an audit trail of model performance over time |

### Who Uses Performance Monitoring?

| Role | Primary Activities |
|------|-------------------|
| **Model Owner** | Reviews monitoring results for owned models, responds to breaches |
| **Data Provider** | Submits monitoring results on a regular schedule |
| **Monitoring Team Member** | Configures monitoring plans, reviews results, escalates issues |
| **Approver** | Provides sign-off on monitoring cycle results |
| **Administrator** | Manages teams, oversees all monitoring activity |

---

## 2. Understanding Performance Monitoring

### The Monitoring Framework

Performance monitoring operates on a **Plan → Cycle → Results** framework:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MONITORING PLAN                                    │
│  Defines: What to monitor, how often, who is responsible                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│   │   Cycle Q1   │───►│   Cycle Q2   │───►│   Cycle Q3   │───► ...        │
│   └──────────────┘    └──────────────┘    └──────────────┘                 │
│          │                   │                   │                          │
│          ▼                   ▼                   ▼                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│   │   Results    │    │   Results    │    │   Results    │                 │
│   │  (Metrics)   │    │  (Metrics)   │    │  (Metrics)   │                 │
│   └──────────────┘    └──────────────┘    └──────────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Monitoring Frequencies

Plans can be configured for different monitoring frequencies:

| Frequency | Period Length | Typical Use Case |
|-----------|---------------|------------------|
| **Monthly** | 1 month | High-risk models, trading models |
| **Quarterly** | 3 months | Most production models (default) |
| **Semi-Annual** | 6 months | Lower-risk or stable models |
| **Annual** | 12 months | Low-risk models with infrequent use |

### Key Dates in a Monitoring Cycle

Each monitoring cycle has important dates that drive the workflow:

| Date | Definition | Example |
|------|------------|---------|
| **Period Start** | Beginning of the monitoring window | January 1, 2025 |
| **Period End** | End of the monitoring window | March 31, 2025 |
| **Submission Due** | When results must be submitted | April 15, 2025 |
| **Report Due** | When the final report must be complete | May 15, 2025 |

---

## 3. Key Concepts

### Monitoring Plans

A **Monitoring Plan** is the master configuration that defines:

- **Name and description** of the monitoring program
- **Frequency** of monitoring cycles
- **Models in scope** (which models are monitored)
- **Metrics** to track with their thresholds
- **Monitoring Team** responsible for oversight
- **Data Provider** who enters results

Think of a monitoring plan as a template that generates recurring cycles.

### Monitoring Cycles

A **Monitoring Cycle** is a single execution of a monitoring plan for a specific time period. Each cycle:

- Has defined start and end dates
- Collects results for all metrics in the plan
- Goes through a workflow from data collection to approval
- Produces an approved monitoring report

### Key Performance Metrics (KPMs)

**Key Performance Metrics** are the specific measurements used to assess model performance. Examples include:

| Metric Type | Examples |
|-------------|----------|
| **Accuracy** | RMSE, MAE, R-squared |
| **Discrimination** | KS statistic, Gini coefficient, AUC |
| **Stability** | PSI (Population Stability Index), CSI |
| **Calibration** | Hosmer-Lemeshow, binomial test |
| **Usage** | Query volume, decision override rate |

### Thresholds and Outcomes

Each quantitative metric has **thresholds** that determine its outcome:

```
                    RED                 YELLOW              GREEN              YELLOW                RED
                  (Critical)           (Warning)          (Healthy)          (Warning)           (Critical)
    ◄──────────────────┼───────────────────┼───────────────────┼───────────────────┼──────────────────►
                    red_min          yellow_min         (Center)         yellow_max          red_max
```

| Outcome | Meaning | Required Action |
|---------|---------|-----------------|
| **GREEN** | Performance within acceptable range | No action needed |
| **YELLOW** | Performance in warning zone | Monitor closely, may need investigation |
| **RED** | Performance in critical zone | Requires justification and potential escalation |

### Monitoring Teams

A **Monitoring Team** is a group of users responsible for overseeing monitoring activities. Team members can:

- Configure and modify monitoring plans
- Start monitoring cycles
- Review and approve results
- Request management approval

---

## 4. Monitoring Plan Lifecycle

### Creating a New Monitoring Plan

Setting up a monitoring plan involves several steps:

#### Step 1: Define the Plan Basics

1. Navigate to **Monitoring Plans** from the main menu
2. Click **"Create Plan"**
3. Enter the required information:
   - **Plan Name**: Descriptive name (e.g., "Credit Scorecard Monitoring")
   - **Frequency**: How often monitoring occurs
   - **Initial reporting cycle period end date**: Sets the first cycle period end
   - **Data Submission Lead Days**: Days after period end for submission
   - **Monitoring Team**: Team responsible for oversight
   - **Data Provider**: Person responsible for submitting results
   - **Reporting Lead Days**: Days between submission due and report due

**Note**: The system calculates the first cycle due dates as:
- **Submission Due Date** = Period End Date + Data Submission Lead Days
- **Report Due Date** = Submission Due Date + Reporting Lead Days

#### Step 2: Add Models to Scope

1. Go to the **Models** tab
2. Click **"Add Models"**
3. Search and select models to include in the plan
4. Models can be added or removed before publishing a version

#### Step 3: Configure Metrics

1. Go to the **Metrics** tab
2. Click **"Add Metric"**
3. For each metric, configure:
   - **KPM**: Select from the master KPM library
   - **Thresholds**: Set yellow and red boundaries
   - **Qualitative Guidance**: For judgment-based metrics
   - **Sort Order**: Display order in results grid

#### Step 4: Publish a Version

1. Go to the **Versions** tab
2. Click **"Publish New Version"**
3. Enter:
   - **Version Name** (optional): e.g., "Initial Configuration"
   - **Effective Date**: When this version takes effect
4. Click **"Publish"**

Publishing creates a snapshot of your metrics and models, ensuring that any future changes don't affect cycles already in progress.

### Modifying an Existing Plan

When you need to update a monitoring plan:

1. **Edit Metrics or Models**: Make changes in the respective tabs
2. **Warning Indicator**: The system shows "Unpublished Changes" when modifications exist
3. **Publish New Version**: Changes only apply to new cycles after publishing

**Important**: Cycles that are already in progress use the version that was active when they started. Your changes will not affect them.

---

## 5. The Monitoring Cycle Workflow

### Cycle Status Flow

Every monitoring cycle progresses through defined stages:

```
┌─────────┐         ┌──────────────────┐         ┌──────────────┐
│ PENDING │────────►│ DATA COLLECTION  │────────►│ UNDER REVIEW │
└─────────┘  Start  └──────────────────┘  Submit └──────────────┘
                            │                           │
                            │                           │ Request
                            │                           │ Approval
                            ▼                           ▼
                    ┌──────────────────┐    ┌──────────────────────┐
                    │    CANCELLED     │    │  PENDING APPROVAL    │
                    └──────────────────┘    └──────────────────────┘
                                                       │
                                                       │ All Approvals
                                                       │ Granted
                                                       ▼
                                               ┌──────────────┐
                                               │   APPROVED   │
                                               └──────────────┘
```

### Stage 1: Pending

**Purpose**: Cycle has been created but not yet started

**Who**: Monitoring Team Members

**Key Activities**:
- Review cycle dates and assignments
- Ensure the correct plan version is active
- Prepare data sources for collection

**Next Step**: Start the cycle to begin data collection

---

### Stage 2: Data Collection

**Purpose**: Active data entry period

**Who**: Data Provider, Team Members

**Key Activities**:
- Enter metric results (manually or via CSV import)
- System automatically calculates outcomes based on thresholds
- Add narratives explaining results, especially for breaches
- Review data quality before submission

**Important Behaviors**:
- When a cycle starts, it **locks to the current active plan version**
- This ensures threshold configurations remain stable during the cycle
- Results can be added, updated, or deleted during this stage

**Next Step**: Submit the cycle when all results are entered

---

### Optional Actions During Data Collection

You can adjust timing without changing the core workflow:

- **Extend Due Date**: Keeps the cycle in DATA_COLLECTION and updates the submission/report due dates.
- **Hold Cycle**: Places the cycle in **ON_HOLD** for an indefinite pause. Overdue alerts are suppressed until the cycle is resumed.

To continue work on a held cycle, use **Resume Cycle** to return it to DATA_COLLECTION.

---

### Stage 3: Under Review

**Purpose**: Quality assurance and review period

**Who**: Monitoring Team Members

**Key Activities**:
- Review all submitted results for accuracy
- Ensure all metrics have been addressed
- Verify narratives adequately explain any anomalies
- Prepare the monitoring report
- Make any necessary corrections to results

**Important Behaviors**:
- Results can still be edited during this stage
- Team reviews before requesting management approval

**Next Step**: Request approval when review is complete

---

### Stage 4: Pending Approval

**Purpose**: Awaiting management sign-off

**Who**: Designated Approvers

**Key Activities**:
- Approvers review the monitoring results and report
- Provide approval or rejection with comments
- System tracks approval status for each required approver

**Important Behaviors**:
- All RED results must have justification narratives before this stage
- A report URL must be provided when requesting approval
- Results cannot be modified once in Pending Approval

**Next Step**: Cycle moves to Approved when all required approvals are granted

---

### Stage 5: Approved

**Purpose**: Cycle is complete

**Outcome**:
- Results are finalized and locked
- Audit trail is complete
- Cycle contributes to historical trend analysis
- Next cycle can be created

---

### Special Status: Cancelled

Cycles can be cancelled from any status except Approved:
- Requires documented cancellation reason
- Cannot be undone
- Preserves history for audit purposes
 - Optional: Deactivate the monitoring plan on cancel
   - **If deactivated**: The plan stops auto-advancing to new cycles
   - **If not deactivated**: The plan auto-advances to the next cycle as usual

---

## 6. Entering Monitoring Results

### Understanding the Results Grid

The results entry interface presents a grid layout:

```
┌────────────────────┬────────────────┬────────────────┬────────────────┐
│      Metric        │    Model A     │    Model B     │    Model C     │
├────────────────────┼────────────────┼────────────────┼────────────────┤
│ KS Statistic       │  0.42 (GREEN)  │  0.38 (YELLOW) │  0.31 (RED)    │
├────────────────────┼────────────────┼────────────────┼────────────────┤
│ PSI                │  0.08 (GREEN)  │  0.12 (GREEN)  │  0.18 (YELLOW) │
├────────────────────┼────────────────┼────────────────┼────────────────┤
│ Override Rate      │  5.2% (GREEN)  │  8.1% (GREEN)  │  12.4% (YELLOW)│
└────────────────────┴────────────────┴────────────────┴────────────────┘
```

### Manual Data Entry

To enter results manually:

1. Navigate to the monitoring cycle
2. Go to the **Results** tab
3. Click on a cell to enter a value
4. The system automatically:
   - Calculates the outcome (GREEN/YELLOW/RED)
   - Applies color coding
   - Saves your entry

### Adding Narratives

Narratives provide context for your results:

1. Click on a result cell
2. Enter or update the narrative in the panel
3. Save your changes

**When Narratives Are Required**:
- All RED outcomes require a justification narrative
- Qualitative metrics always require a narrative
- Narratives help approvers understand the context

### CSV Bulk Import

For efficient data entry across many models and metrics:

1. Click **"Import CSV"** on the Results tab
2. Download the template (pre-populated with your models and metrics)
3. Fill in your data following the format:
   ```csv
   model_id,metric_id,value,outcome,narrative
   1,101,0.42,,Model performing well
   2,101,0.38,,Slight decline - monitoring
   3,101,0.31,,Below threshold - under investigation
   ```
4. Upload your file
5. **Preview** the import (dry run) to check for errors
6. **Execute** the import when satisfied

**CSV Import Rules**:
- Quantitative metrics: Provide numeric value, outcome is calculated
- Qualitative metrics: Provide outcome code (GREEN/YELLOW/RED)
- Invalid rows are rejected with specific error messages

For detailed CSV import instructions, see the [CSV Import Guide](#appendix-b-csv-import-guide).

### Plan-Level vs. Model-Specific Results

Results can be entered at two levels:

| Level | When to Use | Example |
|-------|-------------|---------|
| **Model-Specific** | Different values per model | "Model A: KS=0.42, Model B: KS=0.38" |
| **Plan-Level** | Single value applies to all | "Portfolio-wide override rate: 6.2%" |

**Important**: You cannot mix both levels for the same metric. Choose one approach per metric and use it consistently.

---

## 7. Understanding Metrics and Thresholds

### Quantitative Metrics

Quantitative metrics have numeric values that are automatically evaluated against thresholds.

**Example: KS Statistic (Higher is Better)**

| Threshold | Value | Meaning |
|-----------|-------|---------|
| red_min | 0.30 | Values below 0.30 are critical |
| yellow_min | 0.35 | Values below 0.35 are warning |
| (healthy zone) | 0.35 - 1.0 | Acceptable performance |

**Outcome Calculation**:
- Value = 0.42 → GREEN (above yellow_min)
- Value = 0.33 → YELLOW (between red_min and yellow_min)
- Value = 0.28 → RED (below red_min)

**Example: PSI (Lower is Better)**

| Threshold | Value | Meaning |
|-----------|-------|---------|
| yellow_max | 0.10 | Values above 0.10 are warning |
| red_max | 0.25 | Values above 0.25 are critical |

**Outcome Calculation**:
- Value = 0.08 → GREEN (below yellow_max)
- Value = 0.15 → YELLOW (between yellow_max and red_max)
- Value = 0.30 → RED (above red_max)

### Qualitative Metrics

Qualitative metrics require human judgment and cannot be automatically calculated.

**Examples**:
- Documentation quality assessment
- User satisfaction rating
- Governance compliance check

For qualitative metrics:
- No numeric value is required
- Select the outcome directly (GREEN/YELLOW/RED)
- Always provide a narrative explaining your assessment
- Follow the qualitative guidance in the metric configuration

### Configuring Thresholds

When setting up thresholds, consider:

1. **Metric Direction**: Is higher better or lower better?
2. **Industry Standards**: What do regulations or best practices suggest?
3. **Historical Performance**: What has the model achieved previously?
4. **Risk Appetite**: How much deviation is acceptable?

**Threshold Validation Rules**:
- Yellow thresholds must be less severe than red thresholds
- All boundary values must be logically consistent
- The system prevents invalid configurations

### Handling Breaches (RED Outcomes)

When a metric shows RED:

1. **Immediate Action**: Add a justification narrative explaining:
   - Why the breach occurred
   - What investigation has been done
   - What remediation is planned

2. **Before Requesting Approval**: All RED outcomes must have narratives

3. **Escalation**: Consider whether the breach requires:
   - Management escalation
   - Model use restrictions
   - Revalidation trigger

### Creating Recommendations from Breaches

When a metric shows RED, you can create a recommendation directly from the breach panel to document remediation actions:

1. **Navigate to the Result**: Click on a RED result cell in the monitoring grid
2. **Open Breach Panel**: The annotation panel shows breach details
3. **Click "Create Recommendation"**: Opens the recommendation creation modal
4. **Pre-populated Fields**: The system automatically sets:
   - **Model**: The model with the breach
   - **Monitoring Cycle**: The current cycle
   - **Linked Metric**: The specific metric that breached (`plan_metric_id`)
   - **Context**: Pre-filled description referencing the breach

**Why This Matters**: Linking recommendations to specific metrics ensures that when the system evaluates whether a RED result needs escalation, it can correctly determine whether a remediation plan exists for that particular metric (see [Exception Automation](#exception-automation-type-1-unmitigated-performance) below).

### Exception Automation (Type 1: Unmitigated Performance)

The system automatically detects and creates exceptions for RED monitoring results that lack remediation plans. This occurs **only after a monitoring cycle is approved**, giving teams time to create recommendations during the review phase.

#### When Exceptions Are Triggered

Type 1 (Unmitigated Performance) exceptions are created when:

| Trigger Condition | Description |
|-------------------|-------------|
| **No Recommendation** | RED result with no active recommendation linked to that specific metric |
| **Persistent RED** | Same metric shows RED in two consecutive APPROVED cycles |

#### What "Active Recommendation" Means

A recommendation is considered "active" if:
- It is linked to the **same metric** (`plan_metric_id`) as the RED result
- It is linked to the **same monitoring cycle**
- Its status is not in terminal recommendation statuses (e.g., `REC_CLOSED`, `REC_DROPPED`, `REC_CANCELLED`,
  `REC_COMPLETED`, `REC_VOIDED`, `REC_WITHDRAWN`)

**Example Scenarios**:

| Scenario | Exception Created? | Why |
|----------|-------------------|-----|
| RED result, no recommendation | ✅ Yes | No remediation plan exists |
| RED result + Open recommendation for **that metric** | ❌ No | Active remediation in progress |
| RED result + Open recommendation for **different metric** | ✅ Yes | Recommendation doesn't address this breach |
| RED result + Closed recommendation | ✅ Yes | Remediation complete but breach persists |
| Two consecutive RED cycles for same metric | ✅ Yes | Persistent performance issue |

#### Timing: Why Only on Approved Cycles

Exception detection only runs on **APPROVED** cycles, not cycles still in progress:

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ DATA_COLLECTION │────►│  UNDER_REVIEW    │────►│ PENDING_APPROVAL │
└─────────────────┘     └──────────────────┘     └──────────────────┘
        │                       │                        │
        │                       │                        │
   No exception            No exception            No exception
   detection               detection               detection
        │                       │                        │
        │                       │                        ▼
        │                       │               ┌──────────────────┐
        │                       └──────────────►│    APPROVED      │
        │                                       └──────────────────┘
        │                                               │
        │                                               ▼
        └─────────────────────────────────────  Exception Detection
                                                     Runs Here
```

**Rationale**: During DATA_COLLECTION and UNDER_REVIEW phases, teams are still working on results and creating recommendations. Running exception detection prematurely would create false positives.

#### Workflow for Handling RED Results

**Best Practice**: Create recommendations for RED results **before** requesting cycle approval.

1. **During Data Collection**: Enter all metric results
2. **Identify RED Outcomes**: Review any metrics showing RED
3. **Create Recommendations**: For each RED result:
   - Click the RED cell
   - Use "Create Recommendation" button
   - Document the remediation plan
4. **Request Approval**: When all RED results have recommendations
5. **Cycle Approved**: Exception detection runs
   - RED results WITH linked recommendations → No exception
   - RED results WITHOUT recommendations → Exception created

#### Viewing Exceptions

Once exceptions are created:
- Navigate to **Model Details** → **Exceptions** tab
- Badge shows count of open exceptions
- Filter by status: OPEN, ACKNOWLEDGED, CLOSED
- Each exception shows:
  - Exception type (e.g., UNMITIGATED_PERFORMANCE)
  - Source metric and result
  - Detection date
  - Status history

---

## 8. Approvals Process

### Understanding Approval Requirements

When a cycle moves to Pending Approval, the system automatically creates approval requirements:

| Approval Type | Description | When Required |
|---------------|-------------|---------------|
| **Global** | Overall sign-off from monitoring governance | Always required |
| **Regional** | Sign-off from regional stakeholders | When models are deployed in regions requiring approval |

### Submitting an Approval

If you are a designated approver:

1. Navigate to the monitoring cycle
2. Go to the **Approvals** tab
3. Find your pending approval requirement
4. Review:
   - All metric results
   - The monitoring report (linked)
   - Any breach justifications
5. Click **"Decision"** to open the decision modal
6. Select your decision (Approve or Reject) and add comments

### Approval Workflow

```
Cycle in PENDING_APPROVAL
         │
         ├──────► Global Approver reviews ──────► APPROVED
         │                                            │
         │                                            │
         ├──────► Regional Approver 1 reviews ───────►├──► All Required
         │                                            │    Approvals
         │                                            │    Granted?
         └──────► Regional Approver 2 reviews ───────►│         │
                                                      │         ▼
                                                      │    ┌──────────┐
                                                      └───►│ APPROVED │
                                                           └──────────┘
```

### Admin Proxy Approvals

In cases where the designated approver is unavailable, an Administrator can approve on their behalf:

1. Admin navigates to the approval requirement
2. Admin clicks **"Decision on Behalf"**
3. Admin must provide **approval evidence** (e.g., email confirmation, meeting minutes)
4. The system records:
   - That this was a proxy approval
   - The evidence provided
   - Full audit trail

### Rejection and Voiding

**Rejection**:
- Approver can reject with required comments
- Cycle remains in Pending Approval
- Issues must be addressed and resubmitted

**Voiding** (Admin Only):
- Removes an approval requirement without replacement
- Requires documented reason
- Used for exceptional circumstances

---

## 9. Plan Versioning

### Why Versioning Matters

Plan versioning ensures consistency and auditability:

- **Consistency**: Active cycles use a fixed configuration
- **Auditability**: Know exactly what thresholds applied to each cycle
- **Flexibility**: Update plans without disrupting in-progress work

### How Versioning Works

```
Plan Created
     │
     ▼
Version 1 Published (Active) ◄────── Cycle Q1 locked to V1
     │
     ▼
Metrics Updated (is_dirty = true)
     │
     ▼
Version 2 Published (Active) ◄────── Cycle Q2 locked to V2
     │                                    │
     │                                    │
Version 1 (Inactive)                 Cycle Q1 still uses V1
```

### The "Unpublished Changes" Indicator

When you modify a plan's metrics or models:
- The system sets a "dirty" flag
- The UI shows "Unpublished Changes" warning
- Changes won't affect cycles until you publish a new version

### Publishing a New Version

1. Navigate to the plan's **Versions** tab
2. Click **"Publish New Version"**
3. Provide:
   - **Version Name**: Optional descriptive name
   - **Effective Date**: When this version becomes active
4. Click **"Publish"**

**What Gets Captured**:
- All current metric configurations (thresholds, guidance)
- All current models in scope
- KPM names and evaluation types
- Timestamp and publisher information

### Viewing Version History

The Versions tab shows:
- All published versions with dates
- Which version is currently active
- Metrics and models captured in each version
- Which cycles used each version

---

## 10. Role-Based Workflows

### For Data Providers

Your primary responsibility is submitting monitoring results on schedule.

**Typical Workflow**:

1. **Check My Tasks**: Go to "My Monitoring Tasks" to see your assignments
2. **Access the Cycle**: Click on a cycle in DATA_COLLECTION status
3. **Enter Results**:
   - Use manual entry for a few values
   - Use CSV import for bulk data
4. **Add Narratives**: Explain any anomalies, especially RED outcomes
5. **Submit**: Click "Submit Cycle" when complete

**What You Can Do**:
- Enter and update results
- Submit cycles (DATA_COLLECTION → UNDER_REVIEW)
- View cycle history

**What You Cannot Do**:
- Start cycles (that's for team members)
- Request approval (that's for team members)
- Cancel cycles

---

### For Monitoring Team Members

You provide oversight of the monitoring process and ensure quality.

**Typical Workflow**:

1. **Configure Plans**: Set up metrics, thresholds, and models
2. **Publish Versions**: Ensure configuration changes are published
3. **Start Cycles**: Move cycles from Pending to Data Collection
4. **Review Results**: Check submitted data for quality and completeness
5. **Request Approval**: When review is complete, send to approvers
6. **Handle Escalations**: Address any approval rejections

**What You Can Do**:
- All Data Provider activities, plus:
- Edit plan configurations
- Start and cancel cycles
- Request management approval
- Publish plan versions

---

### For Approvers

You provide governance oversight and sign-off on monitoring results.

**Typical Workflow**:

1. **Receive Notification**: (Outside system) Learn that a cycle needs approval
2. **Review Results**: Examine all metrics and their outcomes
3. **Check Breaches**: Verify that RED results have adequate justification
4. **Review Report**: Read the linked monitoring report
5. **Make Decision**: Approve or reject with comments

**Types of Approvers**:
- **Global Approver**: Signs off on all cycles
- **Regional Approver**: Signs off for specific regions

---

### For Administrators

You manage the overall monitoring function and have full system access.

**Key Responsibilities**:
- Create and manage monitoring teams
- Oversee all monitoring plans and cycles
- Approve on behalf of unavailable approvers
- Monitor governance dashboard for compliance
- Handle escalations and exceptions

**Admin Dashboard Access**:
- View all overdue cycles
- See pending approvals across the organization
- Track completion rates and trends

---

## 11. My Monitoring Tasks

### Accessing Your Tasks

The "My Monitoring Tasks" page shows all cycles where you have responsibility:

1. Navigate to **My Monitoring** from the main menu
2. View your personalized task list
3. Filter by role (Data Provider, Team Member, Assignee)

### Understanding Your Task List

Each task card shows:

| Field | Description |
|-------|-------------|
| **Plan Name** | The monitoring plan this cycle belongs to |
| **Period** | The monitoring period (e.g., Q3 2025) |
| **Status** | Current cycle status |
| **Your Role** | Why this cycle appears in your list |
| **Due Date** | When results or report are due |
| **Overdue** | Red indicator if past due |

### Task Actions by Role

| Your Role | Cycle Status | Available Actions |
|-----------|--------------|-------------------|
| Data Provider | DATA_COLLECTION | Enter results, Submit cycle |
| Data Provider | UNDER_REVIEW | View results (read-only) |
| Team Member | PENDING | Start cycle |
| Team Member | DATA_COLLECTION | Enter results, Submit cycle |
| Team Member | UNDER_REVIEW | Review results, Request approval |
| Assignee | DATA_COLLECTION | Enter results, Submit cycle |

**On Hold**: Cycles in ON_HOLD appear as "On Hold" and do not require action until resumed.

### Priority Sorting

Tasks are sorted by priority:
1. **Overdue** cycles (most urgent)
2. **Approaching due date** (within 7 days)
3. **Pending approval** cycles
4. **Normal** status

---

## 12. Trend Analysis & Historical Views

### Overview

Trend analysis helps you understand how model performance changes over time by visualizing metric results across multiple monitoring cycles. The system provides two different visualization types depending on the metric's evaluation method:

- **Line Charts**: For quantitative metrics with numeric values and thresholds
- **Status Timelines**: For qualitative/outcome-only metrics that rely on human judgment

### Accessing Trend Charts

From the **Monitoring Plan** page:

1. Navigate to the **Metrics** tab
2. Find the metric you want to analyze
3. Click the **📊 Trend** button in the "Results by Metric (Last 10 Cycles)" column
4. The system opens the appropriate visualization based on the metric type

### Quantitative Metric Trends (Line Charts)

For metrics with numeric values (e.g., KS Statistic, PSI, Gini):

**Chart Features**:
- **Multi-line display**: When multiple models are in the plan, each model appears as a separate colored line
- **Threshold zones**: Background shading shows GREEN, YELLOW, and RED performance zones
- **Threshold lines**: Dashed lines mark the yellow and red boundaries
- **Interactive tooltips**: Hover over data points to see exact values
- **Summary statistics**: Latest value, threshold levels, and data point count

**Model Filter**:
- **All Results (Multi-Line)**: Show all models on one chart (default)
- **Plan Level (All Models)**: Show only plan-level aggregated results
- **Individual Model**: Show a single model's trend line

**Example Use Cases**:
- Compare PSI stability across multiple credit models
- Track if a model's KS is trending toward threshold breach
- Identify seasonal patterns in model performance

### Qualitative Metric Trends (Status Timelines)

For metrics evaluated by human judgment (e.g., Documentation Quality, Governance Compliance):

**Timeline Features**:
- **Status boxes**: Each cycle is represented by a colored box showing the outcome (GREEN/YELLOW/RED/N/A)
- **Date labels**: ISO-formatted dates below each box (e.g., "Dec '24")
- **Interactive tooltips**: Hover over any status box to see:
  - **Cycle period**: The monitoring period dates
  - **Outcome**: The assessed outcome (GREEN/YELLOW/RED/N/A)
  - **Narrative excerpt**: First 200 characters of the explanation
  - **Action prompt**: "Click for full details" reminder
- **Click for details**: Click any box to open the full breach annotation panel with complete narrative
- **Chronological order**: Timeline flows left to right, oldest to newest
- **Cycle limit**: Displays the **last 10 cycles** to keep the view manageable
  - If more than 10 cycles exist, a truncation indicator shows: "(showing last 10 of 25)"

**Status Box Color Coding**:

| Outcome | Color | Text Color | Meaning |
|---------|-------|------------|---------|
| **GREEN** | Green background | White text | Acceptable performance |
| **YELLOW** | Yellow background | Dark gray text | Warning zone (accessible contrast) |
| **RED** | Red background | White text | Critical issue |
| **N/A** | Gray background | Dark gray text | No assessment provided |

**Model Filter** (when multiple models in plan):
- **All Results**: Show outcomes from all models in chronological order
- **Plan Level (All Models)**: Show only plan-level qualitative assessments
- **Individual Model**: Filter to one specific model's outcomes

**Example Scenario**:

```
Documentation Quality - Last 10 Cycles

[GREEN] [GREEN] [YELLOW] [GREEN] [GREEN] [RED] [YELLOW] [GREEN] [GREEN] [GREEN]
Dec '24  Jan '25  Feb '25  Mar '25  Apr '25 May '25 Jun '25  Jul '25  Aug '25 Sep '25

Hover over the RED box in May '25:
┌─────────────────────────────────────────┐
│ Q2 2025 (Apr 1 - Jun 30)                │
│ Outcome: RED                            │
│                                         │
│ Documentation review found significant  │
│ gaps in model assumptions section.      │
│ Risk management sign-off missing for... │
│                                         │
│ Click for full details                  │
└─────────────────────────────────────────┘
```

### Why Different Visualizations?

**Quantitative metrics** (line charts):
- Show continuous numeric trends
- Reveal gradual degradation or improvement
- Allow threshold-based automatic evaluation
- Example: PSI trending from 0.08 → 0.12 → 0.18 shows gradual data drift

**Qualitative metrics** (status timelines):
- Show discrete judgment-based outcomes
- No meaningful "trend line" since values aren't comparable numbers
- Focus on outcome patterns and narrative context
- Example: Documentation quality may be GREEN for months, then RED due to missing approvals

### Using Trends for Decision Making

**Early Warning Detection**:
- **Quantitative**: Line approaching yellow threshold → Investigate before breach
- **Qualitative**: Pattern of YELLOW outcomes → Systemic issue may need attention

**Remediation Validation**:
- After creating a recommendation for a RED result, check next cycle
- Did the outcome improve to YELLOW or GREEN?
- If still RED, consider escalating to model use restrictions or revalidation

**Regulatory Documentation**:
- Export trend charts (screenshot or CSV) for validation reports
- Demonstrate ongoing oversight and responsiveness to issues
- Show effectiveness of remediation actions over time

### Best Practices

1. **Review trends quarterly**: Even if current cycle is GREEN, trends may show degradation
2. **Compare models**: Use multi-line view to identify underperforming models
3. **Document narrative patterns**: For qualitative metrics, consistent YELLOW outcomes may indicate threshold miscalibration
4. **Consider seasonality**: Some metrics (e.g., usage patterns) may have expected seasonal variation
5. **Create recommendations proactively**: Don't wait for RED—address YELLOW trends before they escalate

---

## 13. Dashboards & Reporting

### Admin Monitoring Overview

Administrators see a governance dashboard showing:

**Summary Cards**:
- Overdue cycles count
- Pending approval count
- In-progress cycles count
- Completed in last 30 days

**Priority Cycle List**:
- All cycles sorted by urgency
- Color-coded status indicators
- Approval progress (e.g., "1/2 approvals")
- Results summary (green/yellow/red counts)

### Plan-Level Reporting

Each monitoring plan provides:

**Metrics Tab**:
- All configured metrics with thresholds
- Active/inactive status
- Sort order

**Cycles Tab**:
- Historical cycle list
- Status progression
- Due dates and completion dates
- Link to detailed results

**Versions Tab**:
- Published version history
- Effective dates
- Metric snapshots

### Cycle-Level Reporting

Each cycle provides:

**Results Tab**:
- Complete results grid
- Outcome color coding
- Narrative text
- Historical comparison (if available)

**Approvals Tab**:
- Required approvals
- Approval status
- Approver comments
- Proxy approval evidence

### Exporting Data

**CSV Export** is available for:
- Monitoring plans list
- Cycle results
- Historical trend data

Click the **"Export CSV"** button on any list view to download.

---

## 13. Frequently Asked Questions

### General Questions

**Q: What's the difference between monitoring and validation?**
A: Validation is a comprehensive, point-in-time assessment of whether a model is fit for purpose. Monitoring is ongoing measurement of how the model performs in production. Think of validation as the "annual physical" and monitoring as "daily vital signs."

**Q: How often should models be monitored?**
A: Monitoring frequency depends on model risk and usage:
- High-risk, frequently-used models: Monthly
- Standard production models: Quarterly (most common)
- Lower-risk or stable models: Semi-annually or annually

**Q: Can I change thresholds after a cycle has started?**
A: You can change thresholds in the plan, but the change won't affect cycles already in progress. Active cycles are locked to the plan version that was active when they started. Publish a new version for future cycles.

---

### For Data Providers

**Q: What if I can't get data for a metric?**
A: If data is unavailable, leave the value blank and provide a narrative explaining why. The narrative should describe:
- Why the data couldn't be obtained
- When it might become available
- Any alternative assessments performed

**Q: Can I update results after submitting?**
A: Yes, results can be updated while the cycle is in UNDER_REVIEW status. Once the cycle moves to PENDING_APPROVAL, results are locked.

**Q: What happens if I miss the submission deadline?**
A: The cycle will show as overdue on dashboards. Work with your monitoring team to complete submission as soon as possible. Late submissions are tracked for governance reporting.

---

### For Team Members

**Q: Why can't the data provider start the cycle?**
A: Starting a cycle is a governance action that locks the configuration version. This is reserved for team members who have oversight responsibility. Data providers focus on data entry.

**Q: What should I check before requesting approval?**
A: Before requesting approval, verify:
1. All metrics have results or explanatory narratives
2. All RED outcomes have justification narratives
3. The monitoring report is complete and linked
4. Data quality has been reviewed

**Q: Can I cancel an approved cycle?**
A: No, approved cycles cannot be cancelled. They represent finalized, auditable records. If corrections are needed, document them in the next cycle.

---

### For Approvers

**Q: What am I approving exactly?**
A: You are approving:
- The monitoring results and their accuracy
- The adequacy of breach justifications
- The monitoring report conclusions
- That appropriate governance has been followed

**Q: Can I partially approve?**
A: Each approval is independent. If there are multiple approvers (e.g., Global and Regional), each makes their own decision. You cannot partially approve your own requirement.

**Q: What if I disagree with a result but don't want to reject the whole cycle?**
A: Add comments with your concerns when approving. For significant issues, reject with specific feedback. The team can address your concerns and resubmit for approval.

---

### Technical Questions

**Q: What happens if I upload a CSV with errors?**
A: The system validates your CSV before importing. In preview mode, you'll see which rows have errors and why. Only valid rows are imported. See the [CSV Import Guide](#appendix-b-csv-import-guide) for details.

**Q: How are outcomes calculated for quantitative metrics?**
A: The system checks thresholds in order:
1. If value < red_min OR value > red_max → RED
2. If value < yellow_min OR value > yellow_max → YELLOW
3. Otherwise → GREEN
4. If no thresholds configured → UNCONFIGURED

**Q: What's the difference between voiding and rejecting an approval?**
A: Rejection is an approver saying "I don't approve this." Voiding (admin only) removes the approval requirement entirely—as if it was never needed. Voiding is for exceptional circumstances like organizational changes.

---

### Exception and Recommendation Questions

**Q: Why did an exception get created for my RED result even though I have a recommendation?**
A: The system checks that the recommendation is linked to the **same metric** that has the RED result. If you created a general recommendation for the model but didn't link it to the specific metric (`plan_metric_id`), an exception will still be created. Use the "Create Recommendation" button from the breach panel to ensure proper linkage.

**Q: When does exception detection run?**
A: Exception detection runs only when a monitoring cycle moves to APPROVED status. This gives teams time during DATA_COLLECTION and UNDER_REVIEW to create recommendations before exceptions are triggered. If you approve a cycle with RED results and no linked recommendations, exceptions will be created automatically.

**Q: Can I prevent exceptions by creating recommendations after the cycle is approved?**
A: No. Exception detection runs at the moment of cycle approval. However, you can:
1. **Acknowledge** the exception to indicate you're aware of it
2. **Close** the exception with a resolution narrative once remediation is complete
3. For future cycles, create recommendations during the review phase before approval

**Q: What happens if the same metric is RED in two consecutive cycles?**
A: A "Persistent RED" exception is created, even if a recommendation exists. This escalates performance issues that persist despite remediation efforts. The previous cycle must also be APPROVED for this comparison to occur.

**Q: How do I see all exceptions for a model?**
A: Navigate to **Model Details** → **Exceptions** tab. A red badge shows the count of open exceptions. You can filter by status (OPEN, ACKNOWLEDGED, CLOSED) and see the source of each exception (which monitoring result triggered it).

---

## Appendix A: Status Reference

### Cycle Statuses

| Status | Description | Who Can Act | Next Statuses |
|--------|-------------|-------------|---------------|
| **PENDING** | Cycle created, awaiting start | Team Members | DATA_COLLECTION, CANCELLED |
| **DATA_COLLECTION** | Active data entry period | Data Provider, Team Members | UNDER_REVIEW, ON_HOLD, CANCELLED |
| **ON_HOLD** | Cycle paused; overdue alerts suppressed | Team Members, Data Provider | DATA_COLLECTION, CANCELLED |
| **UNDER_REVIEW** | Team reviewing results | Team Members | PENDING_APPROVAL, CANCELLED |
| **PENDING_APPROVAL** | Awaiting approver sign-off | Approvers | APPROVED |
| **APPROVED** | Cycle complete | (Terminal) | — |
| **CANCELLED** | Cycle terminated | (Terminal) | — |

### Approval Statuses

| Status | Description |
|--------|-------------|
| **Pending** | Awaiting approver decision |
| **Approved** | Approver granted approval |
| **Rejected** | Approver rejected the cycle |
| **Voided** | Approval requirement removed (Admin) |

### Outcome Values

| Outcome | Color | Meaning |
|---------|-------|---------|
| **GREEN** | 🟢 | Performance within acceptable range |
| **YELLOW** | 🟡 | Performance in warning zone |
| **RED** | 🔴 | Performance in critical zone |
| **N/A** | ⚪ | No value provided |
| **UNCONFIGURED** | ⚫ | No thresholds configured |

---


---

## Appendix B: CSV Import Guide

This guide explains how to bulk import monitoring results using CSV files.

## Overview

The CSV import feature allows you to efficiently enter monitoring results for multiple models and metrics at once, rather than entering them one by one through the UI. This is particularly useful when:

- You have results from external monitoring systems
- You need to enter data for many models in a monitoring plan
- You want to transfer results from spreadsheets

## CSV Format Requirements

### Required Columns

Your CSV file must include the following columns:

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `model_id` | Integer | Yes | The model ID from the monitoring plan |
| `metric_id` | Integer | Yes | The metric ID from the monitoring plan |
| `value` | Decimal | Conditional | Numeric value (required for quantitative metrics) |
| `outcome` | Text | Optional | Outcome code: GREEN, YELLOW, or RED |
| `narrative` | Text | Optional | Commentary or explanation |

### Example CSV

```csv
model_id,metric_id,value,outcome,narrative
1,101,0.85,,Model performing well
1,102,0.92,,Above target
2,101,0.67,,Below threshold - under review
2,102,0.78,,Acceptable performance
3,101,,,Qualitative assessment
3,102,,GREEN,Manual override for qualitative metric
```

## Important Rules

### Quantitative vs Qualitative Metrics

The system handles metrics differently based on their type:

**Quantitative Metrics (numeric-based)**
- **Must provide a numeric `value`** - the `outcome` column is ignored
- Outcome (GREEN/YELLOW/RED) is automatically calculated from configured thresholds
- If you provide an outcome value, it will be silently ignored

**Qualitative Metrics (judgment-based)**
- Numeric `value` is optional
- You may provide an explicit `outcome` (GREEN, YELLOW, or RED)
- Outcome is not calculated from thresholds

### Validation Rules

The import will reject rows with:
- Invalid or missing `model_id`
- Invalid or missing `metric_id`
- Model not included in the monitoring plan
- Metric not included in the monitoring plan
- Invalid numeric value (non-numeric text in value column)
- Invalid outcome code (must be GREEN, YELLOW, RED, or empty)
- Quantitative metric without a numeric value

### Cycle Status Requirements

CSV import is only available when the monitoring cycle is in one of these statuses:
- **Data Collection** - Primary data entry phase
- **Under Review** - Review phase where corrections can still be made

Import is blocked when the cycle is in:
- Pending
- On Hold
- Pending Approval
- Approved
- Rejected

## Import Process

### Step 1: Download Template

From the Monitoring Cycle page, click **"Import CSV"** to open the import panel. Use the **"Download Template"** button to get a pre-populated CSV with:
- All valid model IDs and names for the plan
- All valid metric IDs and names for the plan
- Empty columns for value, outcome, and narrative

### Step 2: Prepare Your Data

Fill in your CSV file following these guidelines:

1. Keep the header row unchanged
2. Enter one result per row (model + metric combination)
3. For quantitative metrics, always provide a numeric value
4. For qualitative metrics, provide an outcome code if known
5. Add narrative comments as needed

### Step 3: Preview (Dry Run)

Upload your CSV file with **"Preview"** mode enabled (default). This shows:

- **Valid Rows**: Rows that will be processed, showing whether each is a new entry ("create") or updating an existing entry ("update")
- **Error Rows**: Rows that will be skipped, with specific error messages
- **Summary**: Total counts of creates, updates, and errors

**Review the preview carefully before proceeding!**

### Step 4: Execute Import

Once satisfied with the preview:

1. Click **"Execute Import"** to process the data
2. The system will create new results and update existing ones
3. A summary shows the final counts

## Outcome Calculation

### How Thresholds Work

For quantitative metrics, outcomes are calculated using configured thresholds:

| Zone | Condition |
|------|-----------|
| **RED** | Value < red_min OR value > red_max |
| **YELLOW** | Value < yellow_min OR value > yellow_max (but not in RED zone) |
| **GREEN** | All other values (within acceptable range) |
| **UNCONFIGURED** | No thresholds configured for this metric |

### Example

If a metric has:
- `red_max = 0.95` (values > 95% are RED)
- `yellow_max = 0.90` (values > 90% are YELLOW)

Then:
- Value 0.97 → RED
- Value 0.92 → YELLOW
- Value 0.85 → GREEN

## Common Issues and Solutions

### "Model X is not in this monitoring plan"

The model ID in your CSV doesn't match any model in the current monitoring plan. Check:
- You're importing to the correct monitoring cycle
- The model hasn't been removed from the plan
- You're using the correct model ID (from the template)

### "Metric X is not in this monitoring plan"

The metric ID doesn't match any active metric in the plan. Check:
- The metric is still active in the plan configuration
- You're using the correct metric ID (from the template)

### "Quantitative metrics require a numeric value"

You tried to import a row for a quantitative metric without a value. For quantitative metrics, you must always provide a numeric value - the outcome cannot be set directly.

### "Invalid numeric value"

The value column contains non-numeric text. Ensure values are:
- Plain numbers (e.g., `0.85`, `95`, `1.23`)
- No currency symbols, percentages, or other characters
- Use period (.) as decimal separator

### "Invalid outcome"

The outcome column contains an unrecognized value. Valid options are:
- `GREEN`
- `YELLOW`
- `RED`
- Empty (blank)

Case doesn't matter (green, Green, GREEN all work).

## Permissions

To import CSV results, you must have one of:
- **Plan Owner**: You created or own the monitoring plan
- **Team Member**: You're a member of the plan's monitoring team
- **Admin**: System administrator role

## API Reference

For programmatic access, the import endpoint is:

```
POST /monitoring/cycles/{cycle_id}/results/import
```

Parameters:
- `file`: CSV file (multipart/form-data)
- `dry_run`: Boolean (default: true) - Preview without saving

Response includes:
- `valid_rows`: Array of processable rows with actions
- `error_rows`: Array of rejected rows with error messages
- `summary`: Counts of total, created, updated, skipped, and errors

## Best Practices

1. **Always preview first** - Use dry run mode to catch errors before importing
2. **Use the template** - Download the template to ensure correct IDs
3. **Import in batches** - For very large datasets, consider splitting into multiple files
4. **Review thresholds** - Ensure metric thresholds are configured before importing quantitative data
5. **Document changes** - Use the narrative column to explain notable values
6. **Verify after import** - Review the imported results in the UI to confirm accuracy

*Last Updated: December 2025 (Merged CSV Import Guide as Appendix B)*

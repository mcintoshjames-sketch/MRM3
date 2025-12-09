# Performance Monitoring User Guide

## Table of Contents

1. [Introduction](#1-introduction)
2. [Understanding Performance Monitoring](#2-understanding-performance-monitoring)
3. [Key Concepts](#3-key-concepts)
4. [Monitoring Plan Lifecycle](#4-monitoring-plan-lifecycle)
5. [The Monitoring Cycle Workflow](#5-the-monitoring-cycle-workflow)
6. [Entering Monitoring Results](#6-entering-monitoring-results)
7. [Understanding Metrics and Thresholds](#7-understanding-metrics-and-thresholds)
8. [Approvals Process](#8-approvals-process)
9. [Plan Versioning](#9-plan-versioning)
10. [Role-Based Workflows](#10-role-based-workflows)
11. [My Monitoring Tasks](#11-my-monitoring-tasks)
12. [Dashboards & Reporting](#12-dashboards--reporting)
13. [Frequently Asked Questions](#13-frequently-asked-questions)

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
   - **Monitoring Team**: Team responsible for oversight
   - **Data Provider**: Person responsible for submitting results
   - **Reporting Lead Days**: Days between submission due and report due

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

For detailed CSV import instructions, see the [CSV Import Guide](USER_GUIDE_MONITORING_CSV_IMPORT.md).

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
5. Click **"Approve"** or **"Reject"**
6. Add comments explaining your decision

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
2. Admin clicks **"Approve on Behalf"**
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

### Priority Sorting

Tasks are sorted by priority:
1. **Overdue** cycles (most urgent)
2. **Approaching due date** (within 7 days)
3. **Pending approval** cycles
4. **Normal** status

---

## 12. Dashboards & Reporting

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
A: The system validates your CSV before importing. In preview mode, you'll see which rows have errors and why. Only valid rows are imported. See the [CSV Import Guide](USER_GUIDE_MONITORING_CSV_IMPORT.md) for details.

**Q: How are outcomes calculated for quantitative metrics?**
A: The system checks thresholds in order:
1. If value < red_min OR value > red_max → RED
2. If value < yellow_min OR value > yellow_max → YELLOW
3. Otherwise → GREEN
4. If no thresholds configured → UNCONFIGURED

**Q: What's the difference between voiding and rejecting an approval?**
A: Rejection is an approver saying "I don't approve this." Voiding (admin only) removes the approval requirement entirely—as if it was never needed. Voiding is for exceptional circumstances like organizational changes.

---

## Appendix: Status Reference

### Cycle Statuses

| Status | Description | Who Can Act | Next Statuses |
|--------|-------------|-------------|---------------|
| **PENDING** | Cycle created, awaiting start | Team Members | DATA_COLLECTION, CANCELLED |
| **DATA_COLLECTION** | Active data entry period | Data Provider, Team Members | UNDER_REVIEW, CANCELLED |
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

*Last Updated: December 2025*

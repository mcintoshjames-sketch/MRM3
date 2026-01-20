# User Guide: MRSA and IRP Management

## Table of Contents

1. [Introduction](#1-introduction)
2. [Key Concepts](#2-key-concepts)
3. [Managing MRSAs](#3-managing-mrsas)
4. [Managing IRPs](#4-managing-irps)
5. [MRSA Review Tracking](#5-mrsa-review-tracking)
6. [Recording IRP Reviews](#6-recording-irp-reviews)
7. [IRP Certifications](#7-irp-certifications)
8. [Coverage Compliance](#8-coverage-compliance)
9. [Role-Based Workflows](#9-role-based-workflows)
10. [Frequently Asked Questions](#10-frequently-asked-questions)
11. [Appendix](#11-appendix)

---

## 1. Introduction

### What is an MRSA?

A **Model Risk-Sensitive Application (MRSA)** is a system or application that consumes model outputs but is not itself a model. MRSAs represent downstream applications that depend on model results for business decisions, reporting, or automated processes.

Examples of MRSAs include:
- Automated decisioning systems that use credit scores
- Reporting dashboards that display model outputs
- Regulatory filing systems that incorporate model calculations
- Trading platforms that execute based on pricing models

### What is an IRP?

An **Independent Review Process (IRP)** is a governance mechanism that provides oversight for high-risk MRSAs. IRPs ensure that applications consuming model outputs are properly controlled, documented, and periodically assessed.

### Why This Matters

MRSAs can propagate model risk downstream. If a model produces inaccurate outputs, any application using those outputs may make flawed decisions. The MRSA/IRP framework ensures:

- **Visibility**: Track which applications depend on model outputs
- **Risk Classification**: Identify high-risk applications requiring oversight
- **Governance**: Establish review processes for critical applications
- **Compliance**: Document periodic assessments and certifications

### Who Uses This Feature

| Role | Primary Activities |
|------|-------------------|
| **Administrator** | Full IRP management: create, edit, delete IRPs; configure MRSA review policies; manage review exceptions; issue certifications; link MRSAs to IRPs |
| **Validator** | View MRSAs and review status via My MRSA Reviews; view IRP details for accessible MRSAs (read-only); cannot access IRP list page or add reviews/certifications |
| **Model Owner** | Register MRSAs, assign risk classifications, monitor MRSA review status via My MRSA Reviews, view IRP coverage |

---

## 2. Key Concepts

### MRSA Risk Levels

MRSAs are classified by risk level, which determines governance requirements:

| Risk Level | Description | IRP Required? |
|------------|-------------|---------------|
| **High-Risk** | Critical applications with significant business impact | Yes |
| **Low-Risk** | Non-critical applications with limited impact | No |

Risk levels are configurable via the Taxonomy system. Administrators can add additional risk levels as needed.

High-Risk MRSAs are subject to periodic independent reviews (default frequency is 24 months when the policy is active).

### MRSA Review Policies

High-risk MRSAs are tracked against a configurable review policy tied to each MRSA risk level. Policies define the recurring review frequency, the initial review deadline for newly created MRSAs, and the warning window used to flag upcoming reviews.

If no active policy exists for a risk level, the review status will display **No Requirement**. See [MRSA Review Tracking](#5-mrsa-review-tracking) for details.

### MRSA Review Status

Review status is calculated from the latest IRP review across any linked IRP and the policy for the MRSA risk level. Status badges appear on dashboards and the Models list to highlight upcoming or overdue reviews.

### IRP Coverage

An IRP can cover multiple MRSAs. This many-to-many relationship allows:
- A single governance process to oversee related applications
- Efficient review cycles across application families
- Consolidated certification for grouped MRSAs

```
    ┌─────────────────┐
    │      IRP        │
    │  (Credit Apps)  │
    └────────┬────────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐
│ MRSA  │ │ MRSA  │ │ MRSA  │
│  #1   │ │  #2   │ │  #3   │
└───────┘ └───────┘ └───────┘
```

### IRP Review Outcomes

Periodic reviews assess the adequacy of MRSA governance:

| Outcome | Description | Indicator |
|---------|-------------|-----------|
| **Satisfactory** | MRSA governance meets standards | Green |
| **Conditionally Satisfactory** | Minor issues identified requiring attention | Yellow |
| **Not Satisfactory** | Significant deficiencies found | Red |

### IRP Certifications

Certifications are formal sign-offs by MRM administrators confirming that an IRP's design and controls are adequate for the MRSAs it covers.

---

## 3. Managing MRSAs

### Viewing MRSAs

MRSAs are displayed on the **Models** page. To filter for MRSAs:

1. Navigate to **Models** in the sidebar
2. Use the view toggle to select **MRSAs Only**
3. The list shows all registered MRSAs with their risk levels

### Viewing MRSA Review Status

When viewing MRSAs, you can surface the review tracking fields directly in the Models list:

1. Open the column chooser and enable:
   - **MRSA Review Status**
   - **MRSA Last Review**
   - **MRSA Next Due**
2. Use the **MRSA Review Status** filter to focus on Upcoming, Overdue, No IRP, or Never Reviewed items.
3. If an approved exception exists, the **MRSA Next Due** column will show an "Exception" date beneath the standard due date.

Review status fields are only populated for MRSAs; non-MRSAs display a dash.

### Creating an MRSA

To register a new MRSA:

1. Navigate to **Models** > **Add Model**
2. Complete the form with:
   - **Name**: Descriptive name for the application
   - **Description**: Purpose and function of the MRSA
   - **Owner**: Person responsible for the application
   - **Is Model**: Set to **No**
   - **Is MRSA**: Set to **Yes**
   - **MRSA Risk Level**: Select High-Risk or Low-Risk
   - **Risk Rationale**: Explain the risk classification decision
3. Click **Save**

### Editing MRSA Details

1. Navigate to the MRSA detail page
2. Click **Edit**
3. Update fields as needed
4. Click **Save**

### MRSA Risk Classification

When classifying an MRSA's risk level, consider:

- **Business Impact**: Financial or operational consequences of errors
- **Data Sensitivity**: Regulatory or privacy implications
- **Decision Automation**: Degree of human oversight in downstream decisions
- **Volume**: Number of transactions or decisions affected

---

## 4. Managing IRPs

### Accessing IRPs

*Requires Administrator role*

Navigate to **IRPs** in the sidebar to view the IRP management page. This navigation item is only visible to Administrators.

### IRP List View

The IRP list displays:

| Column | Description |
|--------|-------------|
| ID | Unique identifier |
| Process Name | Name of the independent review process |
| Contact | Primary contact person for the IRP |
| Status | Active or Inactive |
| MRSAs | Number of covered MRSAs |
| Latest Review | Most recent review date and outcome |
| Latest Certification | Most recent certification date |
| Actions | Edit and Delete buttons (Admin only) |

**Filtering Options**:
- Filter by **Contact** (multi-select)
- Filter by **Status**: All, Active, or Inactive
- Filter by **Review Date** range
- Filter by **Certification Status**: All, Certified, or Not Certified

**Export**: Click **Export CSV** to download the IRP list.

### Non-Admin IRP Access

While the IRP list page (`/irps`) is restricted to Administrators, non-admin users can access IRP detail pages under certain conditions:

**Who can view IRP details:**
- Any user who has access to at least one MRSA covered by that IRP
- Access is determined by MRSA ownership, developer assignment, or delegate roles

**What non-admins see on IRP detail pages:**
- IRP overview information (name, description, contact, status)
- **Covered MRSAs** tab shows only MRSAs the user has access to (not all MRSAs)
- **Reviews** and **Certifications** tabs are read-only
- No edit or delete capabilities

**Navigation behavior:**
- When non-admins click "Back" from an IRP detail page, they return to **My MRSA Reviews** (not the IRP list)
- Links to IRP details appear in the My MRSA Reviews widget and on MRSA detail pages

### MRSA Review Status Widget

The IRP Management page includes an **MRSA Review Status** widget that summarizes review obligations across all MRSAs (Administrator-only view):

- Summary counts for Current, Upcoming, and Overdue
- Filters for **Needs Attention** (Overdue, No IRP, Never Reviewed), **Upcoming**, or **All**
- CSV export for the current view
- Admins see a link to **MRSA Review Policies**

### Creating an IRP

*Requires Administrator role*

1. Click **Add IRP**
2. Complete the form:
   - **Process Name**: Descriptive name (e.g., "Credit Risk Applications Review")
   - **Contact**: Select the IRP contact person
   - **Description**: Scope and purpose of the review process
3. Click **Create**

**Note**: MRSA coverage is managed separately from the MRSA detail page after IRP creation.

### Editing an IRP

*Requires Administrator role*

1. On the IRP list page, click the **Edit** icon on the IRP row
2. Update fields as needed (Process Name, Contact, Description, Active status)
3. Click **Save**

**Note**: MRSA coverage cannot be edited from this form. Manage MRSA linkages from individual MRSA detail pages.

### Deactivating an IRP

*Requires Administrator role*

To deactivate an IRP without deleting it:
1. Edit the IRP
2. Set Status to **Inactive**
3. Click **Save**

Inactive IRPs remain in the system for historical reference but are hidden from the default list view.

### Deleting an IRP

*Requires Administrator role*

1. Click the **Delete** button on the IRP row
2. Confirm the deletion

**Note**: Deletion is permanent. Consider deactivating instead to preserve history.

---

## 5. MRSA Review Tracking

High-risk MRSAs are tracked against configurable review policies. Review status is based on the latest IRP review across any linked IRP and the policy tied to the MRSA risk level.

### Review Policy Fields

- **Frequency Months**: Recurring review cycle after the most recent IRP review
- **Initial Review Months**: Deadline for the first review after MRSA creation if no reviews exist
- **Warning Days**: Window before the due date when status changes to Upcoming
- **Active**: Only active policies are used for status calculations

**Default High-Risk Policy**: Frequency 24 months, Initial Review 3 months, Warning 90 days.

### Review Status Definitions

| Status | Meaning | Typical Action |
|--------|---------|----------------|
| **CURRENT** | Review due date is beyond the warning window | Continue normal monitoring |
| **UPCOMING** | Review due within warning window | Schedule the review |
| **OVERDUE** | Review due date has passed (no grace period) | Escalate and complete the review |
| **NEVER_REVIEWED** | No reviews recorded yet; initial review deadline applies | Schedule the initial review |
| **NO_IRP** | MRSA has no linked IRP while a policy is active | Link to an IRP immediately |
| **NO_REQUIREMENT** | No active policy for the risk level | No review tracking required |

### How Status Is Calculated

1. The system looks up the active policy for the MRSA's risk level.
2. If no policy is active, the MRSA is labeled **No Requirement**.
3. If an MRSA with an active policy has no linked IRP, the status is **No IRP**.
4. The latest review date across all linked IRPs sets the next due date.
5. If no reviews exist, the due date is **MRSA created date + Initial Review Months** and the status is **Never Reviewed**.
6. If an approved exception exists, the due date is overridden and flagged in the UI.

### Where to Monitor Review Status

- **IRP Management**: MRSA Review Status widget with filters and CSV export (Admin only)
- **My MRSA Reviews**: Dedicated page for non-admin users to track their MRSAs (see below)
- **Models List**: MRSA Review Status, MRSA Last Review, and MRSA Next Due columns with status filters
- **Admin Dashboard**: Past-Due MRSA Reviews feed highlighting overdue, no-IRP, and never-reviewed items

### My MRSA Reviews Page

*Available to all non-admin users (Model Owners, Validators, Users)*

The **My MRSA Reviews** page (`/my-mrsa-reviews`) provides a personalized view of MRSA review status for MRSAs the user owns, develops, or supports as a delegate.

**Accessing My MRSA Reviews:**
1. Navigate to **My MRSA Reviews** in the sidebar (visible to non-admin users)
2. View the MRSA Review Status widget filtered to your MRSAs

**Features:**
- Summary counts for Current, Upcoming, and Overdue items
- Quick filters for items needing attention (Overdue, No IRP, Never Reviewed)
- CSV export of your MRSA review status
- Direct links to MRSA detail pages

**Note:** From the My MRSA Reviews page, users can click through to IRP detail pages for any IRP covering their MRSAs (see [Non-Admin IRP Access](#non-admin-irp-access) below)

### Configuring MRSA Review Policies (Admin)

1. Go to **Configuration** > **Workflow & Policies** > **MRSA Review Policies**.
2. Review the policy list by MRSA risk level.
3. Click **Edit** to update frequency, initial review window, warning days, or active status.
4. Use **Create MRSA Review Policy** to add a policy for new risk levels.
5. Click **Save** to apply changes (status calculations update immediately).

### Managing Review Due Date Exceptions (Admin)

Administrators can create exceptions to override the calculated review due date for specific MRSAs. This is useful for temporary deferrals or special circumstances.

**Creating an Exception:**

*Requires Administrator role*

1. Navigate to the exception management interface
2. Select the MRSA requiring an exception
3. Provide the following:
   - **Override Due Date**: The new due date for the review
   - **Reason**: Justification for the exception (required)
4. Click **Create Exception**

**Exception Behavior:**
- When an exception is active, the UI displays an "Exception" date beneath the standard due date
- The exception due date takes precedence over the calculated due date for status determination
- Exceptions are tracked with the approving administrator and timestamp

**Revoking an Exception:**
1. Locate the active exception for the MRSA
2. Update the exception to set **is_active** to false
3. The MRSA reverts to its calculated due date

**API Endpoints for Exception Management:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mrsa-review-exceptions/` | GET | List all exceptions |
| `/mrsa-review-exceptions/{mrsa_id}` | GET | Get exception for specific MRSA |
| `/mrsa-review-exceptions/` | POST | Create exception (Admin only) |
| `/mrsa-review-exceptions/{id}` | PATCH | Update or revoke exception |

---

## 6. Recording IRP Reviews

IRP reviews document periodic assessments of MRSA governance.

### Viewing Review History

1. Navigate to the IRP detail page
2. Click the **Reviews** tab
3. View the chronological list of all reviews

### Adding a Review

1. Navigate to the IRP detail page
2. Click the **Reviews** tab
3. Click **Add Review**
4. Complete the form:
   - **Review Date**: Date the review was conducted
   - **Outcome**: Select the review outcome
   - **Notes**: Document findings and observations
5. Click **Create Review**

### Review Outcomes

| Outcome | When to Use |
|---------|-------------|
| **Satisfactory** | MRSA controls are operating effectively; no material issues |
| **Conditionally Satisfactory** | Minor gaps identified; remediation actions defined |
| **Not Satisfactory** | Material control weaknesses; immediate attention required |

### How Reviews Affect MRSA Review Status

- The review tracker uses the most recent review date from any IRP linked to the MRSA.
- Adding a new review resets the next due date based on the policy frequency.
- If an MRSA has coverage but no reviews, it remains **Never Reviewed** until the first review is recorded.

### Review Best Practices

- Conduct reviews at regular intervals (e.g., annually)
- Document specific findings, not just outcomes
- Track remediation actions for conditional outcomes
- Escalate unsatisfactory outcomes to management

---

## 7. IRP Certifications

Certifications are formal attestations that an IRP's design is adequate.

### Viewing Certification History

1. Navigate to the IRP detail page
2. Click the **Certifications** tab
3. View the chronological list of all certifications

### Adding a Certification

*Requires Administrator role*

1. Navigate to the IRP detail page
2. Click the **Certifications** tab
3. Click **Add Certification**
4. Complete the form:
   - **Certification Date**: Date of the certification
   - **Conclusion Summary**: Summary of the certification conclusions
5. Click **Create Certification**

### When to Certify

Certifications are typically issued:
- After initial IRP establishment
- Following material changes to the IRP or covered MRSAs
- As part of annual governance cycles
- After remediation of unsatisfactory review findings

---

## 8. Coverage Compliance

### High-Risk MRSA Governance

High-Risk MRSAs **should** be covered by an IRP as a best practice. The system tracks coverage status but does not currently enforce it during save.

High-risk MRSAs are also tracked against MRSA review policies. Use MRSA review status to identify **No IRP**, **Never Reviewed**, and **Overdue** items that require action.

### Checking Coverage Status

On MRSA detail pages:
- The **IRP Coverage** section shows linked IRPs
- Coverage status indicates whether the MRSA has any linked IRPs

On the IRP detail page (Admin only):
- The **Covered MRSAs** tab lists all MRSAs linked to this IRP

### Managing MRSA Coverage

MRSA-IRP linkages are managed from the **MRSA detail page**:

1. Navigate to the MRSA detail page
2. Scroll to the **IRP Coverage** section
3. Click **+ Link to IRP** to add coverage
4. Select an IRP from the list
5. Click **Link to IRP**

To remove coverage:
1. In the IRP Coverage section, click **Unlink** next to the IRP

*Both operations require Administrator role.*

**Important**: The current implementation counts any linked IRP toward coverage, including inactive IRPs.

---

## 9. Role-Based Workflows

### Administrator Workflow

```
┌─────────────────────────────────────────────────────────┐
│                  ADMINISTRATOR                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Configure Taxonomies                                │
│     └─► Set up MRSA Risk Levels                         │
│     └─► Set up IRP Review Outcomes                      │
│     └─► Configure MRSA Review Policies                  │
│                                                         │
│  2. Create and Manage IRPs                              │
│     └─► Define process scope                            │
│     └─► Assign IRP contact                              │
│     └─► Add reviews and certifications                  │
│                                                         │
│  3. Link MRSAs to IRPs                                  │
│     └─► Navigate to MRSA detail page                    │
│     └─► Use "+ Link to IRP" in IRP Coverage section     │
│     └─► Select appropriate IRP                          │
│                                                         │
│  4. Issue Certifications                                │
│     └─► Review IRP design adequacy                      │
│     └─► Document conclusions                            │
│                                                         │
│  5. Monitor Compliance                                  │
│     └─► Track MRSA review status and past-due items     │
│     └─► Ensure High-Risk MRSAs have coverage            │
│     └─► Review unsatisfactory findings                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Model Owner Workflow

```
┌─────────────────────────────────────────────────────────┐
│                   MODEL OWNER                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Register MRSAs                                      │
│     └─► Identify model-consuming applications           │
│     └─► Document MRSA purpose and scope                 │
│                                                         │
│  2. Classify Risk                                       │
│     └─► Assess business impact                          │
│     └─► Assign risk level                               │
│     └─► Document risk rationale                         │
│                                                         │
│  3. Participate in Governance                           │
│     └─► Track MRSA review status via My MRSA Reviews    │
│     └─► View IRP coverage status on MRSA detail page    │
│     └─► Access IRP details for covered MRSAs            │
│     └─► Support IRP reviews when requested              │
│     └─► Address findings from IRP assessments           │
│                                                         │
│  Note: MRSA-IRP linking requires Administrator role     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 10. Frequently Asked Questions

### General Questions

**Q: What's the difference between a Model and an MRSA?**

A: A Model performs calculations, predictions, or valuations. An MRSA is an application that uses model outputs but doesn't perform modeling itself. For example, a credit scoring model is a Model; an automated loan decisioning system that uses those scores is an MRSA.

**Q: Can an MRSA be covered by multiple IRPs?**

A: Yes. The system supports many-to-many relationships. An MRSA can be linked to multiple IRPs, and each IRP can cover multiple MRSAs.

**Q: What happens if I change an MRSA from Low-Risk to High-Risk?**

A: The risk level will be updated. High-Risk MRSAs should have IRP coverage as a best practice, but the system does not currently enforce this requirement during save.

### IRP Management

**Q: Who can create IRPs?**

A: Only Administrators can create, edit, or delete IRPs. The IRP Management page is only accessible to Administrators.

**Q: Can anyone record reviews?**

A: Only Administrators can add reviews since the IRP Management pages are restricted to the Administrator role.

**Q: Who can issue certifications?**

A: Only Administrators can issue certifications. This provides a formal control point for MRM sign-off on IRP adequacy.

**Q: Should I delete or deactivate an obsolete IRP?**

A: Deactivating is preferred. This preserves historical review and certification records while removing the IRP from active governance.

### MRSA Review Tracking

**Q: Where do I configure MRSA review frequency and warning windows?**

A: Administrators can manage these settings on the **MRSA Review Policies** page under **Configuration** > **Workflow & Policies**. Changes apply immediately to review status calculations.

**Q: Why does an MRSA show "No Requirement"?**

A: There is no active review policy for the MRSA's risk level (commonly for low-risk MRSAs or when a policy is inactive).

**Q: What does "Never Reviewed" mean?**

A: The MRSA has IRP coverage, but no reviews have been recorded yet. The due date is based on the MRSA creation date plus the policy's initial review window.

**Q: How do I request a review due date exception?**

A: Administrators can record a review exception to override the due date. When an exception is active, the UI displays an "Exception" date. Exceptions are currently managed by administrators.

### Coverage and Compliance

**Q: How do I know if all High-Risk MRSAs are covered?**

A: Use the Models page filtered to MRSAs Only. High-Risk MRSAs without IRP coverage will be flagged. You can also export the list to review offline.

**Q: Can a Low-Risk MRSA be linked to an IRP?**

A: Yes. While not required, Low-Risk MRSAs can be included in IRP coverage for additional governance.

**Q: How do I link an MRSA to an IRP?**

A: Navigate to the MRSA detail page and use the "+ Link to IRP" button in the IRP Coverage section. You cannot add MRSAs when creating or editing an IRP directly. This operation requires Administrator role.

---

## 11. Appendix

### A. MRSA Risk Level Taxonomy

| Code | Label | Requires IRP |
|------|-------|--------------|
| HIGH_RISK | High-Risk | Yes |
| LOW_RISK | Low-Risk | No |

*Additional risk levels can be configured by Administrators via the Taxonomy page.*

**Technical Note: `requires_irp` Flag**

The "Requires IRP" column is controlled by the `requires_irp` field on each taxonomy value. This boolean flag determines whether MRSAs with that risk level require IRP coverage:

- When `requires_irp = true`: The system expects IRP coverage for MRSAs with this risk level. MRSAs without coverage will show "No IRP" status.
- When `requires_irp = false`: IRP coverage is optional. These MRSAs will show "No Requirement" status if no review policy is active.

Administrators can configure custom risk levels and set this flag via the Taxonomy management page. The flag is evaluated when calculating MRSA review status and coverage compliance.

### B. IRP Review Outcome Taxonomy

| Code | Label | Indicator Color |
|------|-------|-----------------|
| SATISFACTORY | Satisfactory | Green |
| CONDITIONALLY_SATISFACTORY | Conditionally Satisfactory | Yellow |
| NOT_SATISFACTORY | Not Satisfactory | Red |

### C. MRSA Review Status Codes

| Status | Description |
|--------|-------------|
| CURRENT | Review due date is beyond the warning window |
| UPCOMING | Due within warning window |
| OVERDUE | Past due date (no grace period) |
| NEVER_REVIEWED | No IRP review recorded yet; initial review deadline applies |
| NO_IRP | MRSA has no linked IRP while a policy is active |
| NO_REQUIREMENT | No active policy for the MRSA risk level |

### D. Navigation Reference

| Page | Path | Access | Description |
|------|------|--------|-------------|
| Models (MRSAs) | /models | All users | MRSA list with filters |
| My MRSA Reviews | /my-mrsa-reviews | Non-admin users | Personal MRSA review tracking |
| IRPs | /irps | Admin only | IRP management list |
| IRP Detail | /irps/:id | Conditional* | Individual IRP with tabs |
| Taxonomy | /taxonomy | Admin only | Configure risk levels and outcomes |
| MRSA Review Policies | /mrsa-review-policies | Admin only | Configure MRSA review frequencies and warnings |

*Non-admins can access IRP detail pages if they have access to at least one MRSA covered by the IRP.

### E. Permission Matrix

| Action | Admin | Validator | User |
|--------|-------|-----------|------|
| Access IRP list page (/irps) | Yes | No | No |
| View IRP detail page* | Yes | Yes* | Yes* |
| Create IRP | Yes | No | No |
| Edit IRP | Yes | No | No |
| Delete IRP | Yes | No | No |
| Add Review | Yes | No | No |
| Add Certification | Yes | No | No |
| Manage MRSA Review Policies | Yes | No | No |
| Manage Review Exceptions | Yes | No | No |
| Access My MRSA Reviews page | No | Yes | Yes |
| View MRSAs | Yes | Yes | Yes |
| Create MRSA | Yes | Yes | Yes |
| Edit MRSA | Yes | Yes | Owned only |
| Link MRSA to IRP | Yes | No | No |

*Non-admins can view IRP detail pages only if they have access to at least one MRSA covered by that IRP. The Covered MRSAs tab is filtered to show only accessible MRSAs.

---

*Last Updated: 2026-01-19*

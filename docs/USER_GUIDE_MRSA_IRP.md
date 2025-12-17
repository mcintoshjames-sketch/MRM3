# User Guide: MRSA and IRP Management

## Table of Contents

1. [Introduction](#1-introduction)
2. [Key Concepts](#2-key-concepts)
3. [Managing MRSAs](#3-managing-mrsas)
4. [Managing IRPs](#4-managing-irps)
5. [Recording IRP Reviews](#5-recording-irp-reviews)
6. [IRP Certifications](#6-irp-certifications)
7. [Coverage Compliance](#7-coverage-compliance)
8. [Role-Based Workflows](#8-role-based-workflows)
9. [Frequently Asked Questions](#9-frequently-asked-questions)
10. [Appendix](#10-appendix)

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
| **Administrator** | Full IRP management: create, edit, delete IRPs; issue certifications; link MRSAs to IRPs |
| **Validator** | View MRSAs, participate in validation activities |
| **Model Owner** | Register MRSAs, assign risk classifications, view IRP coverage status on MRSA detail pages |

---

## 2. Key Concepts

### MRSA Risk Levels

MRSAs are classified by risk level, which determines governance requirements:

| Risk Level | Description | IRP Required? |
|------------|-------------|---------------|
| **High-Risk** | Critical applications with significant business impact | Yes |
| **Low-Risk** | Non-critical applications with limited impact | No |

Risk levels are configurable via the Taxonomy system. Administrators can add additional risk levels as needed.

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

**Filtering Options**:
- Toggle **Active Only** to hide inactive IRPs

**Export**: Click **Export CSV** to download the IRP list.

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

## 5. Recording IRP Reviews

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

### Review Best Practices

- Conduct reviews at regular intervals (e.g., annually)
- Document specific findings, not just outcomes
- Track remediation actions for conditional outcomes
- Escalate unsatisfactory outcomes to management

---

## 6. IRP Certifications

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

## 7. Coverage Compliance

### High-Risk MRSA Governance

High-Risk MRSAs **should** be covered by an IRP as a best practice. The system tracks coverage status but does not currently enforce it during save.

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

## 8. Role-Based Workflows

### Administrator Workflow

```
┌─────────────────────────────────────────────────────────┐
│                  ADMINISTRATOR                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Configure Taxonomies                                │
│     └─► Set up MRSA Risk Levels                         │
│     └─► Set up IRP Review Outcomes                      │
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
│     └─► View IRP coverage status on MRSA detail page    │
│     └─► Support IRP reviews when requested              │
│     └─► Address findings from IRP assessments           │
│                                                         │
│  Note: MRSA-IRP linking requires Administrator role     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Frequently Asked Questions

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

### Coverage and Compliance

**Q: How do I know if all High-Risk MRSAs are covered?**

A: Use the Models page filtered to MRSAs Only. High-Risk MRSAs without IRP coverage will be flagged. You can also export the list to review offline.

**Q: Can a Low-Risk MRSA be linked to an IRP?**

A: Yes. While not required, Low-Risk MRSAs can be included in IRP coverage for additional governance.

**Q: How do I link an MRSA to an IRP?**

A: Navigate to the MRSA detail page and use the "+ Link to IRP" button in the IRP Coverage section. You cannot add MRSAs when creating or editing an IRP directly. This operation requires Administrator role.

---

## 10. Appendix

### A. MRSA Risk Level Taxonomy

| Code | Label | Requires IRP |
|------|-------|--------------|
| HIGH_RISK | High-Risk | Yes |
| LOW_RISK | Low-Risk | No |

*Additional risk levels can be configured by Administrators via the Taxonomy page.*

### B. IRP Review Outcome Taxonomy

| Code | Label | Indicator Color |
|------|-------|-----------------|
| SATISFACTORY | Satisfactory | Green |
| CONDITIONALLY_SATISFACTORY | Conditionally Satisfactory | Yellow |
| NOT_SATISFACTORY | Not Satisfactory | Red |

### C. Navigation Reference

| Page | Path | Description |
|------|------|-------------|
| Models (MRSAs) | /models | MRSA list with filters |
| IRPs | /irps | IRP management list |
| IRP Detail | /irps/:id | Individual IRP with tabs |
| Taxonomy | /taxonomy | Configure risk levels and outcomes |

### D. Permission Matrix

| Action | Admin | Validator | User |
|--------|-------|-----------|------|
| Access IRP pages | Yes | No | No |
| Create IRP | Yes | No | No |
| Edit IRP | Yes | No | No |
| Delete IRP | Yes | No | No |
| Add Review | Yes | No | No |
| Add Certification | Yes | No | No |
| View MRSAs | Yes | Yes | Yes |
| Create MRSA | Yes | Yes | Yes |
| Edit MRSA | Yes | Yes | Owned only |
| Link MRSA to IRP | Yes | No | No |

---

*Last Updated: December 2024*

# User Guide: Model Inventory

This guide explains how to work with the Model Inventory in the Quantitative Methods Information System (QMIS). It covers submitting model records, understanding model details, and using key inventory functions.

> **Legend**: Fields marked with ⚙ are populated from administrator-configurable taxonomies. These controlled vocabularies can be customized by administrators through the Taxonomy management page.

---

## Table of Contents

1. [Overview](#overview)
2. [Submitting a New Model Record](#submitting-a-new-model-record)
3. [Understanding the Model Details Page](#understanding-the-model-details-page)
   - [Editable (Mutable) Fields](#editable-mutable-fields)
   - [Calculated (Read-Only) Fields](#calculated-read-only-fields)
   - [How Calculations Work](#how-calculations-work)
4. [Risk Assessment](#risk-assessment)
   - [Qualitative Assessment](#qualitative-assessment)
   - [Quantitative Assessment](#quantitative-assessment)
   - [Inherent Risk Matrix](#inherent-risk-matrix)
   - [Final Risk Tier](#final-risk-tier)
5. [Model Versions (Changes)](#model-versions-changes)
   - [Version Lifecycle](#version-lifecycle)
   - [Creating a New Version](#creating-a-new-version)
   - [Change Types](#change-types)
6. [Model Relationships](#model-relationships)
   - [Model Hierarchy (Parent-Child)](#model-hierarchy-parent-child)
   - [Data Dependencies](#data-dependencies)
7. [Model Limitations](#model-limitations)
   - [Recording a Limitation](#recording-a-limitation)
   - [Significance Levels](#significance-levels)
   - [Managing User Awareness](#managing-user-awareness)
8. [Model Decommissioning](#model-decommissioning)
   - [Initiating Decommissioning](#initiating-decommissioning)
   - [Approval Workflow](#approval-workflow)
   - [Decommissioning Reasons](#decommissioning-reasons)
9. [Exporting Data](#exporting-data)

---

## Overview

The Model Inventory provides a centralized repository for tracking all quantitative models in the organization. Each model record contains:

- **Identification**: Model name, description, and unique model ID
- **Ownership**: Model owner, developer, and associated business line
- **Risk Profile**: Risk tier, assessment factors, and approval status
- **Lifecycle Status**: Current validation state and approval history
- **Relationships**: Connections to parent models and data dependencies
- **Documentation**: Limitations, versions, and change history

---

## Submitting a New Model Record

To register a new model in the inventory:

1. Navigate to **Models** in the side navigation
2. Click **Add New Model**
3. Complete the required fields:

| Field | Description | Required |
|-------|-------------|----------|
| **Model Name** | A unique, descriptive name for the model | Yes |
| **Description** | Purpose and functionality of the model | No |
| **Development Type** | "In-House" or "Third-Party" | Yes |
| **Model Owner** | The business user accountable for the model | Yes |
| **Model Developer** | The individual or team who built the model | No |
| **Vendor** | Required if Development Type is "Third-Party" | Conditional |
| **Usage Frequency** ⚙ | How often the model is used (e.g., Daily, Monthly) | Yes |

4. Click **Submit** to create the model record

> **Note**: Additional fields such as Risk Tier, deployed regions, and model users can be added after the initial submission by editing the model details.

---

## Understanding the Model Details Page

The Model Details page displays comprehensive information organized into tabs:

- **Details** - Core model information and edit controls
- **Versions** - Change history and version management
- **Validations** - Related validation requests
- **Relationships** - Hierarchy and dependencies
- **Limitations** - Documented model limitations
- **Recommendations** - Validation recommendations for this model
- **Exceptions** - Model exceptions and compensating controls
- **Risk Assessment** - Risk evaluation factors and ratings
- **Monitoring** - Performance monitoring data
- **Activity** - Timeline of all model changes
- **Decommissioning** - Retirement request management

### Editable (Mutable) Fields

These fields can be modified by users with appropriate permissions:

| Field | Description |
|-------|-------------|
| Model Name | Display name (changes tracked in history) |
| Description | Purpose and functionality description |
| Development Type | In-House or Third-Party |
| Owner | User responsible for the model |
| Developer | User or team who developed the model |
| Shared Owner | Secondary owner (if applicable) |
| Monitoring Manager | Person managing ongoing monitoring |
| Vendor | Third-party vendor (for vendor-developed models) |
| Risk Tier ⚙ | Assigned risk classification (Tier 1/2/3) |
| Status ⚙ | Current model status |
| Model ID (External) | External reference identifier |
| Usage Frequency ⚙ | Operational frequency of model use |
| Model Users | Individuals using the model |
| Deployed Regions | Geographic deployment locations |
| Methodology ⚙ | Underlying methodology type |

### Calculated (Read-Only) Fields

These fields are automatically computed by the system and cannot be directly edited:

| Field | How It's Calculated |
|-------|---------------------|
| **Business Line** | Derived from the model owner's assigned Line of Business (LOB) |
| **Approval Status** | Calculated from validation history (see details below) |
| **Model Last Updated** | Actual production date from the most recent ACTIVE version (not planned or legacy dates) |
| **Is AI/ML** | Determined from the selected methodology taxonomy value |
| **Scorecard Outcome** | Overall rating from validation scorecard assessments |
| **Residual Risk** | Final risk rating after considering all factors |
| **Revalidation Status** | Due date and compliance status based on policy |

### How Calculations Work

#### Record Approval Status

When a new model record is created, it goes through an administrative approval process before it becomes active in the inventory. This is separate from validation approval.

| Status | Meaning |
|--------|---------|
| **Draft** | New model record awaiting administrator review |
| **Approved** | Record has been approved and is active in the inventory |
| **Needs Revision** | Administrator has requested changes before approval |

> **Note**: Record approval is about the model's existence in the inventory, not its validation state. A model can be approved as a record but still require validation.

#### Approval Status (Validation-Based)

The validation approval status indicates the model's current validation state. It is computed automatically based on validation history and revalidation due dates:

| Status | Meaning |
|--------|---------|
| **APPROVED** | Model has an approved validation and is NOT overdue for revalidation |
| **INTERIM_APPROVED** | Model has interim (limited) approval and is NOT overdue for revalidation |
| **VALIDATION_IN_PROGRESS** | Model IS overdue AND has an active validation in a substantive stage (Planning or later) |
| **EXPIRED** | Model IS overdue with NO substantive validation work in progress |
| **NEVER_VALIDATED** | No validation has ever been completed for this model |

**Key Logic**:
- The system first determines if the model is **overdue** based on the revalidation due date from validation policy
- If NOT overdue: Status is APPROVED or INTERIM_APPROVED (even if a new validation has started)
- If overdue: Status depends on whether substantive validation work is in progress
  - **Substantive stages**: Planning, Assigned, In Progress, Review, Pending Approval
  - **Non-substantive stage**: Intake (just creating the request doesn't count)
- This means a model can show APPROVED while a new validation is in early stages, which accurately reflects its current validated state

#### Business Line

The business line is automatically populated from the model owner's organizational assignment. When the owner changes, the business line updates accordingly. This ensures models are properly categorized within the organizational structure.

#### Model Last Updated

This date reflects when the model was last changed in production. The system looks for the most recent version with status "ACTIVE" and uses its **actual production date** (not the planned date or legacy date). If no active version exists, this field remains empty.

#### Is AI/ML Classification

Models are automatically classified as AI/ML based on their selected methodology. When a methodology tagged as AI/ML-related is assigned to the model, this flag is set to "Yes" automatically.

---

## Risk Assessment

The Risk Assessment tab provides a comprehensive framework for evaluating model risk. The assessment combines multiple approaches to determine the final risk classification.

### Qualitative Assessment

The qualitative assessment evaluates the model across four weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Reputation, Regulatory & Financial Risk** | 30% | Impact on reputation, compliance, and financial reporting |
| **Complexity** | 30% | Technical sophistication and methodology complexity |
| **Usage & Dependency** | 20% | Business reliance and downstream model dependencies |
| **Stability** | 20% | Likelihood and magnitude of errors |

For each factor, you assign a rating:
- **High** (Score: 3)
- **Medium** (Score: 2)
- **Low** (Score: 1)

**How the Score is Calculated:**

The system computes a weighted average:

```
Qualitative Score = (Reputation/Regulatory/Financial × 0.30) + (Complexity × 0.30) +
                    (Usage/Dependency × 0.20) + (Stability × 0.20)
```

The resulting score maps to a qualitative rating:
- Score ≥ 2.1 = **HIGH**
- Score ≥ 1.6 = **MEDIUM**
- Score < 1.6 = **LOW**

### Quantitative Assessment

The quantitative assessment provides a direct rating based on quantitative factors such as backtesting results, model performance metrics, and statistical validation outcomes.

Ratings available:
- **HIGH** - Significant quantitative concerns
- **MEDIUM** - Moderate quantitative concerns
- **LOW** - Minimal quantitative concerns

### Inherent Risk Matrix

The Inherent Risk combines the qualitative and quantitative assessments using a matrix lookup:

| Qualitative ↓ / Quantitative → | HIGH | MEDIUM | LOW |
|-------------------------------|------|--------|-----|
| **HIGH** | Critical | High | Medium |
| **MEDIUM** | High | Medium | Low |
| **LOW** | Medium | Low | Very Low |

### Final Risk Tier ⚙

The Final Risk Tier represents the official risk classification used for governance and validation scheduling:

- **Tier 1 (High Risk)** - Requires annual validation, strictest controls
- **Tier 2 (Medium Risk)** - Requires validation every 2 years
- **Tier 3 (Low Risk)** - Requires validation every 3 years
- **Tier 4 (Very Low Risk)** - Requires validation every 4 years, lightest controls

**Override Capability**: Administrators can override the calculated risk tier if business justification exists. Any override requires documented rationale, which is captured in the audit trail.

---

## Model Versions (Changes)

Model versions track all changes to the model over time, maintaining a complete audit history of modifications.

### Version Lifecycle

Each version progresses through defined states:

| Status | Description |
|--------|-------------|
| **DRAFT** | Version is being prepared, not yet submitted |
| **IN_VALIDATION** | Version is under review by the validation team |
| **APPROVED** | Version has passed validation review |
| **ACTIVE** | Version is currently deployed in production |
| **SUPERSEDED** | Version was previously active but replaced by a newer version |

```
DRAFT → IN_VALIDATION → APPROVED → ACTIVE → SUPERSEDED
```

### Creating a New Version

To record a model change:

1. Navigate to the model's **Details** page
2. Click the **Submit Change** button (green) in the page header
3. Complete the version details:
   - **Version Number** - Typically follows semantic versioning (e.g., 1.2.0)
   - **Change Type** - MAJOR or minor
   - **Change Category** ⚙ - Category from the change taxonomy
   - **Change Description** - Detailed explanation of what changed
   - **Production Date** - When the change goes/went into production

### Change Types

| Type | Description | Validation Impact |
|------|-------------|-------------------|
| **MAJOR** | Significant changes to methodology, inputs, or outputs | Typically triggers re-validation |
| **Minor** | Bug fixes, calibration updates, documentation | May not require re-validation |

The change taxonomy ⚙ provides additional categorization:
- Model Theory Changes
- Implementation Changes
- Data/Input Changes
- Parameter Changes
- Output/Reporting Changes

---

## Model Relationships

Models often operate within a network of interconnected systems. The Relationships tab documents these connections.

### Model Hierarchy (Parent-Child)

A hierarchical relationship exists when one model is a component of a larger model framework.

**Key Points:**
- A model can have only **one parent** (single-parent constraint)
- A model can have **multiple children** (sub-models)
- Hierarchy establishes governance accountability chains

**Examples:**
- Enterprise Credit Model (Parent) → Retail Scoring Model (Child)
- ALM Framework (Parent) → Interest Rate Model (Child)

**To Add a Hierarchy Relationship:**
1. Go to the **Relationships** tab
2. Click **Add Parent** or **Add Sub-Model**
3. Search for and select the related model
4. Specify the relationship type ⚙ and effective date

### Data Dependencies

Dependencies track data flow between models—which models provide inputs to others.

**Dependency Types** ⚙:

| Type | Description |
|------|-------------|
| **INPUT_DATA** | Model receives raw data from another model |
| **SCORE** | Model consumes scores/outputs from another model |
| **PARAMETER** | Model uses parameters calibrated by another model |
| **GOVERNANCE_SIGNAL** | Model receives governance indicators |
| **OTHER** | Other dependency relationships |

**Direction:**
- **Inbound** (Feeder Models) - Models that provide data TO this model
- **Outbound** (Consumer Models) - Models that receive data FROM this model

Understanding dependencies is critical when:
- Decommissioning a model (downstream impact assessment)
- Planning changes (impact on dependent models)
- Investigating issues (tracing data lineage)

---

## Model Limitations

Documented limitations provide transparency about model constraints and how they are managed.

### Recording a Limitation

To add a limitation:

1. Navigate to the **Limitations** tab
2. Click **Add Limitation**
3. Complete the details:
   - **Description** - Detailed explanation of the limitation
   - **Impact Assessment** - Assessment of the limitation's potential impact
   - **Category** ⚙ - Classification from taxonomy
   - **Significance** - Critical or Non-Critical
   - **Conclusion** - Mitigate or Accept
   - **Conclusion Rationale** - Explanation for the chosen conclusion
   - **User Awareness Description** - Required for Critical limitations

### Significance Levels

| Level | Definition | Requirements |
|-------|------------|--------------|
| **Critical** | Significant impact on model reliability or business decisions | Must document User Awareness Description explaining how users are informed |
| **Non-Critical** | Minor constraint with limited impact | No additional documentation required |

### Managing User Awareness

For **Critical** limitations, you must document:
- How model users are made aware of the limitation
- What controls or compensating processes exist
- Monitoring in place to track the limitation's impact

**Conclusion Options:**

| Option | Meaning |
|--------|---------|
| **Mitigate** | Active steps are being taken to reduce or eliminate the limitation |
| **Accept** | The limitation is acknowledged and accepted given current constraints |

### Retiring a Limitation

When a limitation is resolved:

1. Click **Retire** on the limitation
2. Document the resolution in the retirement notes
3. The limitation remains in history but is marked as inactive

---

## Model Decommissioning

When a model is no longer needed, the decommissioning process ensures proper retirement with appropriate approvals and documentation.

### Initiating Decommissioning

1. Navigate to the model's **Decommissioning** tab (or click **Decommission** button)
2. Complete the decommissioning request:

| Field | Description | Required |
|-------|-------------|----------|
| **Reason** ⚙ | Why the model is being retired | Yes |
| **Last Production Date** | Final date the model will be used | Yes |
| **Replacement Model** | Model replacing this one (if applicable) | Conditional |
| **Archive Location** | Where model artifacts will be stored | Yes |
| **Downstream Impact Verified** | Confirmation that dependent systems are addressed | Yes |
| **Gap Justification** | Required if there's a gap between retirement and replacement | Conditional |

### Approval Workflow

Decommissioning requests progress through multiple approval stages:

```
Submitted → Validator Review → Owner Review → Regional/Global Approvals → Completed
```

1. **Validator Review** - Independent validation team reviews the request
2. **Owner Review** - Model owner confirms the retirement (if different from requestor)
3. **Regional Approvals** - Approvals from each deployed region
4. **Global Approval** - Final enterprise-level approval

At each stage, approvers can:
- **Approve** - Move the request forward
- **Reject** - Return the request with feedback
- **Request Changes** - Ask for modifications before approval

### Decommissioning Reasons ⚙

| Reason | Description | Replacement Required |
|--------|-------------|---------------------|
| **REPLACEMENT** | Model being replaced by a new model | Yes |
| **CONSOLIDATION** | Model being merged into another model | Yes |
| **OBSOLETE** | Model no longer needed for business | No |
| **REGULATORY** | Decommissioning due to regulatory requirements | No |
| **OTHER** | Other reasons (document in comments) | No |

**Gap Justification:** If the replacement model's implementation date is after the decommissioned model's last production date, you must explain how the business will operate during this gap period.

---

## Exporting Data

Data can be exported from various screens for reporting and analysis:

### Available Exports

| Screen | Export Options |
|--------|----------------|
| Models List | CSV with all visible columns |
| Model Versions | CSV and PDF |
| Model Dependencies | CSV (Inbound and Outbound separately) |
| Model Hierarchy | CSV |

### How to Export

1. Navigate to the relevant screen
2. Apply any filters to refine the data
3. Click the **Export to CSV** or **Export to PDF** button
4. The file downloads automatically with a date-stamped filename

> **Tip**: Exports include the currently displayed/filtered data, not the entire dataset. Apply filters first to export specific subsets.

---

## Summary

The Model Inventory serves as the central source of truth for model governance. Key points to remember:

- **Complete Required Fields** when submitting new models
- **Understand Calculated Fields** are derived automatically—focus on maintaining accurate source data
- **Conduct Risk Assessments** thoroughly using both qualitative and quantitative factors
- **Document All Changes** through the version management system
- **Maintain Relationships** to ensure accurate impact analysis
- **Record Limitations** transparently, especially Critical ones
- **Follow Decommissioning Process** to properly retire models with appropriate approvals

For additional questions or support, contact the Model Risk Management team.

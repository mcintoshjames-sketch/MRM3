# User Guide: Model Inventory

This guide explains how to work with the Model Inventory in the Quantitative Methods Information System (QMIS). It covers submitting model records, understanding model details, and using key inventory functions.

> **Legend**: Fields marked with ⚙ are populated from administrator-configurable taxonomies. These controlled vocabularies can be customized by administrators through the Taxonomy management page.

---

## Table of Contents

1. [Overview](#overview)
2. [Model vs Non-Model Classification](#model-vs-non-model-classification)
3. [Submitting a New Model Record](#submitting-a-new-model-record)
4. [Understanding the Model Details Page](#understanding-the-model-details-page)
   - [Editable (Mutable) Fields](#editable-mutable-fields)
   - [Calculated (Read-Only) Fields](#calculated-read-only-fields)
   - [How Calculations Work](#how-calculations-work)
5. [Organizational Grouping](#organizational-grouping)
   - [Lines of Business (LOB)](#lines-of-business-lob)
   - [Teams](#teams)
   - [How Models Are Grouped](#how-models-are-grouped)
6. [Model Tags](#model-tags)
   - [Understanding Tags](#understanding-tags)
   - [Adding Tags to a Model](#adding-tags-to-a-model)
   - [Bulk Tagging](#bulk-tagging)
   - [Tag Reports](#tag-reports)
7. [Risk Assessment](#risk-assessment)
   - [Qualitative Assessment](#qualitative-assessment)
   - [Quantitative Assessment](#quantitative-assessment)
   - [Inherent Risk Matrix](#inherent-risk-matrix)
   - [Final Risk Tier](#final-risk-tier)
8. [Model Versions (Changes)](#model-versions-changes)
   - [Quick Overview](#quick-overview)
   - [Deployment Process](#deployment-process)
   - [Comprehensive Documentation](#comprehensive-documentation)
9. [Model Relationships](#model-relationships)
   - [Model Hierarchy (Parent-Child)](#model-hierarchy-parent-child)
   - [Data Dependencies](#data-dependencies)
   - [End-to-End Model Lineage](#end-to-end-model-lineage)
10. [Model Limitations](#model-limitations)
    - [Recording a Limitation](#recording-a-limitation)
    - [Significance Levels](#significance-levels)
    - [Managing User Awareness](#managing-user-awareness)
11. [Model Overlays & Judgements](#model-overlays--judgements)
    - [Recording an Overlay or Judgement](#recording-an-overlay-or-judgement)
    - [Effectiveness and Retirement](#effectiveness-and-retirement)
12. [Model Decommissioning](#model-decommissioning)
    - [Initiating Decommissioning](#initiating-decommissioning)
    - [Approval Workflow](#approval-workflow)
    - [Decommissioning Reasons](#decommissioning-reasons)
13. [Exporting Data](#exporting-data)

---

## Overview

The Model Inventory provides a centralized repository for tracking all quantitative models in the organization. Each model record contains:

- **Identification**: Model name, description, unique model ID, and optional external model ID
- **Ownership**: Model owner, developer, and associated business line
- **Coverage**: Products, portfolios, or lines of business covered by the model
- **Risk Profile**: Risk tier, assessment factors, and approval status
- **Lifecycle Status**: Current validation state and approval history
- **Relationships**: Connections to parent models and data dependencies
- **Documentation**: Limitations, versions, and change history

---

## Model vs Non-Model Classification

The inventory supports tracking both actual models and non-model tools that require oversight. This distinction is important for governance and regulatory compliance.

### Classification Types

| Classification | Description |
|----------------|-------------|
| **Model** (`is_model = true`) | Traditional quantitative models requiring full validation |
| **Non-Model** (`is_model = false`) | Tools or applications that are not models but may require oversight |
| **MRSA** (`is_mrsa = true`) | Model Risk-Sensitive Applications - non-models requiring IRP oversight |

### Model Risk-Sensitive Applications (MRSAs)

MRSAs are non-model tools that, while not meeting the formal definition of a model, still pose sufficient risk to require documented oversight. Examples include:

- Spreadsheet-based decision tools
- Automated data processing pipelines
- Simplified calculation engines
- Rule-based systems with business impact

**MRSA Fields**:

| Field | Description |
|-------|-------------|
| **Is MRSA** | Boolean flag indicating this is an MRSA requiring oversight |
| **MRSA Risk Level** ⚙ | Risk classification (High-Risk or Low-Risk) |
| **MRSA Risk Rationale** | Narrative explaining the risk level assignment |
| **Associated IRPs** | Independent Review Processes (IRPs) covering this MRSA |

When creating or editing a record:
1. Set **Is Model** to "No" for non-model entries
2. If the non-model requires oversight, set **Is MRSA** to "Yes"
3. Assign an **MRSA Risk Level** and provide a **Risk Rationale**
4. Link to relevant **IRPs** that provide oversight

> **Note**: Non-models with `is_mrsa = false` are tracked for inventory completeness but do not require the same governance as models or MRSAs.

---

## Submitting a New Model Record

To register a new model in the inventory:

1. Navigate to **Models** in the side navigation
2. Click **Add New Model**
3. Complete the required fields:

| Field | Description | Required |
|-------|-------------|----------|
| **Model Name** | A unique, descriptive name for the model | Yes |
| **External Model ID** | Optional legacy/external system identifier | No |
| **Description** | Purpose and functionality of the model | Yes |
| **Products Covered** | Products, portfolios, or lines of business covered by the model | No |
| **Development Type** | "In-House" or "Third-Party" | Yes |
| **Model Owner** | The business user accountable for the model | Yes |
| **Model Developer** | The individual or team who built the model | Conditional (required for In-House) |
| **Vendor** | Required if Development Type is "Third-Party" | Conditional |
| **Initial Implementation Date** | First production deployment date | Yes |
| **Usage Frequency** ⚙ | How often the model is used (e.g., Daily, Monthly) | Yes |
| **Deployment Regions** | Regions where the model is deployed (multi-select) | No |
| **Regional Owner (per region)** | Optional owner for a specific deployment region | No |

4. Click **Submit** to create the model record

> **Note**: Additional fields such as Risk Tier, regional owners, and model users can be added after the initial submission by editing the model details.

---

## Understanding the Model Details Page

The Model Details page displays comprehensive information organized into tabs:

- **Details** - Core model information and edit controls
- **Versions** - Change history and version management
- **Validations** - Related validation requests
- **Relationships** - Hierarchy and dependencies
- **Limitations** - Documented model limitations
- **Overlays** - Underperformance overlays and management judgements
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
| Products Covered | Products, portfolios, or lines of business covered by the model |
| Development Type | In-House or Third-Party |
| Owner | User responsible for the model |
| Developer | User or team who developed the model |
| Shared Owner | Secondary owner (if applicable) |
| Shared Developer | Secondary developer (if applicable) |
| Monitoring Manager | Person managing ongoing monitoring |
| Vendor | Third-party vendor (for vendor-developed models) |
| Risk Tier ⚙ | Assigned risk classification (Tier 1/2/3/4) |
| Status ⚙ | Current model status |
| External Model ID | Optional legacy/external system identifier |
| Usage Frequency ⚙ | Operational frequency of model use |
| Ownership Type ⚙ | Classification for model ownership |
| Regulatory Categories ⚙ | Applicable regulatory regimes (CCAR/DFAST, Basel, etc.) |
| Model Users | Individuals using the model |
| Deployment Regions | Geographic deployment locations and optional regional owners |
| Methodology ⚙ | Underlying methodology type |
| Tags | Assigned categorization labels |

#### Deployment Regions & Regional Owners

- Select one or more deployment regions in the model edit form (or during creation).
- For each selected region, you can optionally assign a **Regional Owner** to reflect local accountability.
- The wholly-owned region (if selected) is automatically included in the deployment list.

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
  - **Substantive stages**: Planning, In Progress, Review, Pending Approval, Revision
  - **Non-substantive stage**: Intake (just creating the request doesn't count)
- This means a model can show APPROVED while a new validation is in early stages, which accurately reflects its current validated state

**Validation Request Workflow States**:
The full set of validation request workflow states are:

| State | Description |
|-------|-------------|
| **INTAKE** | Initial request submission and triage |
| **PLANNING** | Scoping and resource allocation |
| **IN_PROGRESS** | Active validation work underway |
| **REVIEW** | Internal QA and compilation of results |
| **PENDING_APPROVAL** | Awaiting stakeholder sign-offs |
| **REVISION** | Returned for revisions after review |
| **APPROVED** | Validation complete with all approvals |
| **ON_HOLD** | Temporarily paused (with reason tracking) |
| **CANCELLED** | Terminated before completion (with justification) |

#### Business Line

The business line is automatically populated from the model owner's organizational assignment. When the owner changes, the business line updates accordingly. This ensures models are properly categorized within the organizational structure.

#### Model Last Updated

This date reflects when the model was last changed in production. The system looks for the most recent version with status "ACTIVE" and uses its **actual production date** (not the planned date or legacy date). If no active version exists, this field remains empty.

#### Is AI/ML Classification

Models are automatically classified as AI/ML based on their selected methodology. When a methodology tagged as AI/ML-related is assigned to the model, this flag is set to "Yes" automatically.

---

## Organizational Grouping

Models are organized within the enterprise's organizational hierarchy through Lines of Business (LOBs) and Teams. This structure enables reporting, filtering, and governance at various organizational levels.

### Lines of Business (LOB)

LOB units represent the organizational hierarchy of the enterprise. The structure supports multiple levels:

| Level | Name | Description |
|-------|------|-------------|
| 1 | SBU (Strategic Business Unit) | Top-level organizational division |
| 2 | LOB1 | First-level business line |
| 3 | LOB2 | Second-level business line |
| ... | LOB*n* | Additional levels as needed |

**Key Characteristics:**
- Each LOB unit has a unique **Org Unit** identifier (5 characters)
- LOB units form a tree structure with parent-child relationships
- Users are assigned to LOB units, which determines their organizational affiliation
- The **Business Line** field on a model is derived automatically from the model owner's LOB assignment

**Example Hierarchy:**
```
Corporate Banking (SBU)
├── Commercial Lending (LOB1)
│   ├── Real Estate Finance (LOB2)
│   └── Asset-Based Lending (LOB2)
└── Treasury Services (LOB1)
    ├── Cash Management (LOB2)
    └── Trade Finance (LOB2)
```

### Teams

Teams provide an additional grouping layer that spans across the LOB hierarchy. While LOB units represent the formal organizational structure, Teams allow flexible grouping for reporting and collaboration purposes.

**Purpose:**
- Group related LOB units that work together on similar risk domains
- Enable cross-organizational reporting and dashboards
- Provide workload distribution views for validation planning

**Pre-configured Teams:**
| Team | Description |
|------|-------------|
| Credit Risk Team | Groups LOB units focused on credit risk modeling |
| Market Risk Team | Groups LOB units focused on market risk modeling |
| Operations Team | Groups LOB units focused on operational processes |

**How Teams Work:**
- Each LOB unit can be assigned to one Team
- All users within that LOB unit inherit the Team assignment
- Models inherit the Team through their owner's LOB → Team relationship
- Team assignment is optional; LOB units can exist without a Team

### How Models Are Grouped

Models are grouped through a chain of relationships:

```
Model → Owner (User) → LOB Unit → Team
```

**Automatic Derivation:**
1. When a model is assigned an **Owner**, the system reads the owner's **LOB Unit**
2. The model's **Business Line** field displays the owner's LOB path (e.g., "Corporate Banking > Commercial Lending")
3. If the owner's LOB Unit belongs to a **Team**, the model is included in that Team's reports

**Changing Organizational Grouping:**
- To change a model's Business Line, change the model's **Owner** to a user in the desired LOB
- To change a model's Team assignment, the administrator must reassign the owner's LOB Unit to a different Team

**Filtering and Reporting:**
- Use the **Business Line** filter on the Models list to view models by LOB
- Use Team-based reports to see models grouped across related LOB units
- Export data includes the full LOB path for organizational analysis

> **Note**: LOB hierarchy and Team management are administrator functions. See the [Administration Guide](USER_GUIDE_ADMINISTRATION.md) for details on configuring organizational structure.

---

## Model Tags

Tags provide a flexible way to categorize and organize models across various dimensions, such as regulatory initiatives, project assignments, or technology classifications. Tags are organized into categories managed by administrators.

### Understanding Tags

**Tag Categories** group related tags together. Each category has:
- **Name** - Descriptive category name (e.g., "Regulatory Initiative", "Project")
- **Color** - Visual identifier used for display badges
- **Sort Order** - Display order in dropdowns and reports

**Tags** within categories represent individual classification values:
- Tags inherit their category's color unless overridden
- Tags can be marked inactive to prevent new assignments while preserving history
- Multiple tags from different categories can be applied to a single model

**Common Use Cases:**
- **Regulatory Initiatives** - Tag models affected by specific regulations (e.g., SR 11-7, CCAR, DFAST)
- **Projects** - Tag models involved in specific transformation projects
- **Technology** - Tag models by technology stack (e.g., Python, SAS, R)
- **Business Priority** - Tag models by strategic importance

### Adding Tags to a Model

**From the Models List:**
1. Navigate to **Models** in the side navigation
2. Click on a model row to open its details
3. In the **Details** tab, locate the **Tags** section
4. Click **Edit** to open the tag selector
5. Search or browse categories to select applicable tags
6. Click checkboxes to add tags (multi-select supported)
7. Click **Save** to apply changes

**From the Model Details Page:**
1. Open the model's Details tab
2. Find the Tags section below the basic information
3. Click the **Edit** button (pencil icon)
4. Use the searchable dropdown to select tags by category
5. Remove existing tags by clicking the X on the tag badge
6. Save your changes

**Permissions:**
- Model owners, developers, and delegates with `can_submit_changes` permission can add/remove tags
- Administrators can manage tags for any model

**Tag History:**
All tag assignments and removals are tracked in the model's audit history. You can view:
- Who added or removed each tag
- When the change was made
- Full history of tag changes over time

### Bulk Tagging

For administrators who need to apply tags to multiple models at once, the Models page offers bulk tagging functionality.

**Entering Bulk Edit Mode:**
1. Navigate to **Models** in the side navigation
2. Click the **Bulk Edit** button in the top-right toolbar
3. The table will show checkboxes next to each model row

**Selecting Models:**
- Click individual checkboxes to select specific models
- Use the header checkbox to "Select all on page" (current page only)
- Selection persists when navigating between pages
- Selected rows are highlighted in blue

**Bulk Actions:**
Once models are selected, a toolbar appears with the following options:

| Action | Description |
|--------|-------------|
| **Assign Tag** | Opens a modal to select a tag to add to all selected models |
| **Remove Tag** | Opens a modal to select a tag to remove from all selected models |
| **Export Selected** | Downloads a CSV containing only the selected models |
| **Clear Selection** | Deselects all currently selected models |

**Assigning a Tag in Bulk:**
1. Select the models you want to tag
2. Click **Assign Tag** in the toolbar
3. Optionally filter by category, then select the tag
4. Click **Assign Tag** to apply
5. Success message shows: "Tagged 5 models with 'CCAR' successfully"

**Removing a Tag in Bulk:**
1. Select the models to remove the tag from
2. Click **Remove Tag** in the toolbar
3. Select the tag to remove
4. Click **Remove Tag** to apply
5. Success message shows: "Removed 'CCAR' tag from 3 models successfully"

**Notes:**
- If some models already have (or don't have) the tag, the success message includes a breakdown
- Bulk operations are only available to administrators
- All bulk tag changes are recorded in each model's audit history

### Tag Reports

The **Model Tags Report** provides analytics on tag usage across the inventory:

**Accessing the Report:**
1. Navigate to **Reports** in the side navigation
2. Select **Model Tags Report** from the Operations category

**Report Features:**

| Section | Information |
|---------|-------------|
| **Summary Statistics** | Total tags, total categories, models with tags, untagged models |
| **Category Breakdown** | Tag count and model usage per category |
| **Models by Tag** | Filter to see which models have a specific tag |
| **Untagged Models** | List of models without any tags assigned |

**Filters:**
- Filter by category to focus on specific tag groups
- Filter by specific tag to see assigned models
- Show only untagged models to identify gaps in categorization

**Export:**
The report supports CSV export including:
- Model details with all assigned tags
- Tag usage statistics
- Untagged model lists

### Tag Administration

> **Note**: Tag and category management is restricted to administrators.

Administrators can manage tags via **Taxonomy → Tags** tab:

**Creating Categories:**
1. Click **Add Category**
2. Enter name, description, and color
3. Set sort order for display positioning
4. Save the category

**Creating Tags:**
1. Select a category from the left panel
2. Click **Add Tag**
3. Enter tag name and optional description
4. Optionally override the category color
5. Save the tag

**Managing Existing Tags:**
- **Edit** - Modify name, description, or color
- **Deactivate** - Hide from selection while preserving existing assignments
- **Delete** - Remove unused tags (blocked if assigned to any model)

**Category Deletion Rules:**
- System categories cannot be deleted
- Categories with tags assigned to models cannot be deleted
- Categories with unused tags will cascade-delete all their tags

---

## Risk Assessment

The Risk Assessment tab provides a comprehensive framework for evaluating model risk. The assessment combines multiple approaches to determine the final risk classification.

### Qualitative Assessment ⚙

> **Note**: Qualitative risk factors are administrator-configurable. Administrators can add, modify, reorder, or deactivate factors through the system's qualitative factor management interface. Factor weights can be customized and must sum to 100%. Each factor can have custom rating guidance for HIGH, MEDIUM, and LOW ratings.

The qualitative assessment evaluates the model across weighted factors. **By default**, the system includes four standard factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Reputation, Regulatory Compliance and/or Financial Reporting Risk** | 30% | Impact on reputation, compliance, and financial reporting |
| **Complexity of the Model** | 30% | Technical sophistication and methodology complexity |
| **Model Usage and Model Dependency** | 20% | Business reliance and downstream model dependencies |
| **Stability of the Model** | 20% | Likelihood and magnitude of errors |

For each factor, you assign a rating:
- **High** (Score: 3)
- **Medium** (Score: 2)
- **Low** (Score: 1)

Each factor includes configurable guidance text to help assessors make consistent ratings.

**How the Score is Calculated:**

The system computes a weighted average using the active factors and their configured weights:

```
Qualitative Score = Σ(Factor Rating × Factor Weight)

Example with default factors:
  = (Reputation/Regulatory/Financial × 0.30) + (Complexity × 0.30) +
    (Usage/Dependency × 0.20) + (Stability × 0.20)
```

The resulting score maps to a qualitative rating:
- Score ≥ 2.1 = **HIGH**
- Score ≥ 1.6 = **MEDIUM**
- Score < 1.6 = **LOW**

**Weight Snapshots**: When an assessment is saved, the system captures a snapshot of each factor's weight at that time. This ensures historical assessments remain accurate even if administrators later modify factor weights.

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
| **HIGH** | High | Medium | Low |
| **MEDIUM** | Medium | Medium | Low |
| **LOW** | Low | Low | Very Low |

> **Note**: The matrix produces a 4-tier result: High, Medium, Low, or Very Low. These map directly to Risk Tiers 1-4.

### Final Risk Tier ⚙

The Final Risk Tier represents the official risk classification used for governance and validation scheduling:

- **Tier 1 (High Risk)** - Requires annual validation, strictest controls
- **Tier 2 (Medium Risk)** - Requires validation every 2 years
- **Tier 3 (Low Risk)** - Requires validation every 3 years
- **Tier 4 (Very Low Risk)** - Requires validation every 4 years, lightest controls

**Override Capability**: Administrators can override the calculated risk tier if business justification exists. Any override requires documented rationale, which is captured in the audit trail.

---

## Model Versions (Changes)

Model versions track all changes to the model over time, maintaining a complete audit history of modifications. The version management system ensures that model changes are properly documented, validated, and deployed in a controlled manner.

### Quick Overview

- **Version Lifecycle**: DRAFT → IN_VALIDATION → APPROVED → ACTIVE → SUPERSEDED
- **Change Types**: MAJOR (significant methodology/data changes) or Minor (bug fixes, calibration updates)
- **Change Categories** ⚙: Model Theory, Implementation, Data/Input, Parameter, Output/Reporting
- **Version Blockers**: System prevents creating a new version if an undeployed version exists or if a version is in active validation

### Deployment Process

After a version is validated and approved, it must be deployed to production across the appropriate geographic regions. The deployment system provides:

- **Deploy Modal**: Accessed from the Versions tab or Validation Detail page
- **Regional Deployment**: Deploy to specific regions with separate production dates
- **Regional Approval Locks** 🔒: Some regions require separate regional approval
- **My Deployment Tasks**: Track pending, confirmed, and overdue deployment tasks
- **Bulk Operations**: Confirm, adjust, or cancel multiple deployments at once
- **Ready to Deploy Report**: Centralized view of all versions ready for production

### Comprehensive Documentation

For complete details on model version management and deployment, including:
- Version lifecycle states and transitions
- Version creation blockers and resolutions
- Change type selection guidance
- Regional deployment workflows
- Deployment task management
- Bulk deployment operations
- Ready to Deploy report usage

**See the dedicated guide**: [Model Changes User Guide](USER_GUIDE_MODEL_CHANGES.md)

The standalone guide provides step-by-step instructions, visual diagrams, best practices, and frequently asked questions for managing model versions and deployments.

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

### End-to-End Model Lineage

The **Lineage** tab provides a visual representation of the complete data flow chain for a model, tracing upstream feeders and downstream consumers across multiple levels.

**Lineage Controls:**

| Control | Description |
|---------|-------------|
| **Direction** | View upstream only, downstream only, or both |
| **Max Depth** | How many levels to traverse (3, 5, 10, or 20) |
| **Include Inactive** | Show inactive models in the lineage |
| **Include Hierarchy** | Include parent/sub-model relationships in the visualization |

**PDF Export:**

The lineage view can be exported as a PDF document for documentation, presentations, or regulatory submissions:

1. Navigate to the model's **Lineage** tab
2. Configure the desired options (direction, depth, hierarchy)
3. Click **Export PDF**
4. The PDF downloads with filename `lineage_model_{id}.pdf`

**PDF Contents:**

The exported PDF includes:

- **Legend** - Color-coded explanation of all visual elements
- **Horizontal Data Flow** - Solid arrows showing feeder → model → consumer relationships
  - **Green boxes** - Upstream feeder models
  - **Blue box** - Center model (the model being viewed)
  - **Purple boxes** - Downstream consumer models
  - **Amber boxes** - Supporting applications
- **Vertical Hierarchy** (when Include Hierarchy is checked):
  - **Cyan boxes above** - Parent model (connected with dashed line)
  - **Cyan boxes below** - Sub-models/children (connected with dashed lines)

**Visual Elements:**

| Element | Color | Line Style | Meaning |
|---------|-------|------------|---------|
| Center Model | Blue | — | The model being analyzed |
| Upstream Models | Green | Solid arrow | Models providing data inputs |
| Downstream Models | Purple | Solid arrow | Models consuming outputs |
| Applications | Amber | Solid arrow | Supporting applications |
| Parent/Sub-Models | Cyan | Dashed line | Hierarchy relationships |

> **Tip**: The Include Hierarchy option is enabled by default. Disable it to generate a simpler PDF showing only the horizontal data flow without parent/sub-model relationships.

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

> **Important**: Critical limitations **require** a User Awareness Description. The system will not allow you to save a Critical limitation without this field completed. This ensures that all significant limitations have documented user communication plans.

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

## Model Overlays & Judgements

Model overlays and management judgements capture **underperformance-driven adjustments** applied to models. These records provide an audit-ready view of overlays that are **currently in effect**.

### Recording an Overlay or Judgement

To add an overlay:

1. Navigate to the **Overlays** tab
2. Click **Add Overlay** (Admin/Validator only)
3. Complete the details:
   - **Kind** - Overlay or Management Judgement
   - **Underperformance-related** - Explicit flag for regulatory reporting
   - **Description** - What adjustment is being applied
   - **Rationale** - Why the overlay is needed
   - **Effective From / To** - Date window for applicability
   - **Region** - Optional; leave blank for global overlays
4. (Optional) Link to monitoring cycles/results, recommendations, or limitations for traceability

### Effectiveness and Retirement

- An overlay is **in effect** when it is **not retired** and today falls within the effective date window.
- **Retire** overlays when they are no longer needed; provide a retirement reason.
- Core fields are immutable once recorded; if the judgement changes, retire the old overlay and create a new one.

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
PENDING → VALIDATOR_APPROVED → APPROVED (or REJECTED/WITHDRAWN)
```

**Workflow States**:

| Status | Description |
|--------|-------------|
| **PENDING** | Request submitted, awaiting validator review |
| **VALIDATOR_APPROVED** | Validator has approved; awaiting owner/regional/global approvals |
| **APPROVED** | All required approvals complete; model will be retired |
| **REJECTED** | Request denied by an approver |
| **WITHDRAWN** | Request withdrawn by the requestor before completion |

**Approval Stages**:

1. **Validator Review** - Independent validation team reviews the request
2. **Owner Review** - Model owner confirms the retirement (if different from requestor)
3. **Regional Approvals** - Approvals from each deployed region
4. **Global Approval** - Final enterprise-level approval

At each stage, approvers can:
- **Approve** - Move the request forward
- **Reject** - Return the request with feedback
- **Request Changes** - Ask for modifications before approval

> **Note**: Requestors can **withdraw** a pending request at any point before final approval if circumstances change.

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
| Risk Assessment | PDF (comprehensive assessment report) |

Models List exports reflect the active column selection. Use the **Columns** picker to include per-region **Regional Owner (XX)** fields (one column per region code). Cells are blank when no regional owner is assigned.

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

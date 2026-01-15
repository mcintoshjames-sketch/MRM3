# User Guide: System Administration

This guide explains administrative functions in the Quantitative Methods Information System (QMIS). It covers user management, Microsoft Entra directory integration, and governance reports for maintaining data integrity.

> **Access**: The features described in this guide are only available to users with the **Admin** role.

---

## Table of Contents

1. [Overview](#overview)
2. [Accessing Administration Features](#accessing-administration-features)
3. [User Management](#user-management)
   - [Viewing Users](#viewing-users)
   - [Creating Users Manually](#creating-users-manually)
   - [Editing Users](#editing-users)
   - [User Roles](#user-roles)
4. [Microsoft Entra Directory Integration](#microsoft-entra-directory-integration)
   - [How It Works](#how-it-works)
   - [Entra Directory Tab](#entra-directory-tab)
   - [Provisioning Users from Entra](#provisioning-users-from-entra)
   - [User Account States](#user-account-states)
   - [Syncing User Status](#syncing-user-status)
   - [Handling Deleted Users](#handling-deleted-users)
5. [Disabled Users Governance](#disabled-users-governance)
   - [Dashboard Alert](#dashboard-alert)
   - [Disabled Users Report](#disabled-users-report)
   - [Remediation Workflow](#remediation-workflow)
6. [Reference Data Management](#reference-data-management)
7. [Taxonomy Configuration](#taxonomy-configuration)

---

## Overview

System administrators are responsible for:

- **User Management**: Creating, editing, and managing user accounts
- **Directory Sync**: Keeping application users synchronized with the corporate directory (Microsoft Entra ID)
- **Governance Oversight**: Identifying and remediating models assigned to disabled users
- **Reference Data**: Managing vendors, regions, teams, and other configuration data
- **Taxonomy**: Configuring controlled vocabularies used throughout the application

---

## Accessing Administration Features

Administration features are accessed through the **Configuration** section in the left sidebar:

1. Click **Configuration** to expand the section (if collapsed)
2. Under **Reference Data**, click **Reference Data** to access:
   - **Vendors** tab - Third-party vendor management
   - **Users** tab - User account management
   - **Entra Directory** tab - Corporate directory browser

Other administrative pages include:
- **Taxonomy** - Controlled vocabulary management
- **Regions** - Geographic region configuration
- **Teams** - Team structure management
- **Workflow Config** - Workflow settings

---

## User Management

### Viewing Users

The Users tab displays all application users with key information:

| Column | Description |
|--------|-------------|
| **Name** | User's full name (links to user detail page) |
| **Email** | User's email address |
| **Role** | Application role (Admin, Validator, User, etc.) |
| **LOB** | Line of Business assignment |
| **Regions** | Assigned regions for regional approvers |
| **Local Status** | Application account status (ENABLED/DISABLED) |
| **Azure State** | Entra directory sync status |

### Creating Users Manually

To create a user without Entra provisioning:

1. Navigate to **Reference Data** > **Users** tab
2. Click **Add User**
3. Complete the required fields:

| Field | Description | Required |
|-------|-------------|----------|
| **Email** | User's email address | Yes |
| **Full Name** | Display name | Yes |
| **Password** | Initial password | Yes |
| **Role** | Application role | Yes |
| **LOB** | Line of Business | No |
| **Regions** | For regional approvers | Conditional |

4. Click **Create User**

> **Note**: Users created manually will not have Entra synchronization unless linked later via the Entra Directory.

### Editing Users

1. Click on a user's name to open their detail page, or click the edit icon
2. Modify the desired fields
3. Click **Save Changes**

### User Roles

| Role | Description |
|------|-------------|
| **Admin** | Full system access including configuration and all administrative functions |
| **Validator** | Can manage validation workflows and view all models |
| **Global Approver** | Can approve validations across all regions |
| **Regional Approver** | Can approve validations for assigned regions only |
| **User** | Standard access for model owners and developers |

---

## Microsoft Entra Directory Integration

### How It Works

QMIS integrates with Microsoft Entra ID (formerly Azure AD) to:

1. **Browse the corporate directory** - Search for employees by name, email, or department
2. **Provision users** - Create application accounts linked to Entra identities
3. **Sync account status** - Detect when employees are disabled or deleted in Entra
4. **Enforce access control** - Prevent disabled users from logging in

### Entra Directory Tab

The Entra Directory tab provides a searchable view of the corporate directory:

| Column | Description |
|--------|-------------|
| **Name** | Employee's display name |
| **Email** | Corporate email address |
| **Job Title** | Position/title |
| **Department** | Organizational department |
| **Office** | Physical office location |
| **Status** | Account enabled/disabled in Entra |
| **In Recycle Bin** | Whether the account is soft-deleted |

**Search**: Use the search box to find employees by name, email, department, or job title.

### Provisioning Users from Entra

To create an application user from the corporate directory:

1. Navigate to **Reference Data** > **Entra Directory** tab
2. Search for the employee
3. Click **Provision** on their row
4. In the modal:
   - Select the **Role** for the new user
   - Optionally assign **Regions** (for regional approvers)
   - Optionally assign a **Line of Business**
5. Click **Provision User**

The system will:
- Create an application user account
- Link it to the Entra identity via `azure_object_id`
- Set `azure_state` to `EXISTS`
- Set `local_status` to `ENABLED`

> **Note**: Provisioned users authenticate via SSO. No password is set in the application.

### User Account States

Users have two status fields that work together:

#### Local Status (`local_status`)

The application-level account status:

| Value | Description |
|-------|-------------|
| **ENABLED** | User can log in and use the application |
| **DISABLED** | User cannot log in; blocked at authentication |

#### Azure State (`azure_state`)

The status synced from Microsoft Entra:

| Value | UI Label | Description |
|-------|----------|-------------|
| **EXISTS** | IT Lockout | User exists in Entra but `account_enabled=false`. Account is disabled but not deleted. |
| **SOFT_DELETED** | Soft Deleted | User was deleted from Entra but is in the recycle bin (recoverable for ~30 days). |
| **NOT_FOUND** | Hard Deleted | User was permanently deleted from Entra. No longer exists in the directory. |
| *null* | - | User was created manually without Entra linking. |

### Syncing User Status

The application does **not** automatically sync with Entra in real-time. Administrators must manually trigger synchronization.

#### Sync a Single User

1. Navigate to **Reference Data** > **Users** tab
2. Find the user in the list
3. Click the **Sync** button (refresh icon) on their row

#### Sync All Users

1. Navigate to **Reference Data** > **Users** tab
2. Click **Sync All from Azure** at the top of the page
3. Confirm when prompted

**What happens during sync:**

1. For each user with an `azure_object_id`:
   - Query Entra for the user's current status
   - If found and `account_enabled=true`: Set `azure_state=EXISTS`, `local_status=ENABLED`
   - If found and `account_enabled=false`: Set `azure_state=EXISTS`, `local_status=DISABLED`
   - If in recycle bin: Set `azure_state=SOFT_DELETED`, `local_status=DISABLED`
   - If not found: Set `azure_state=NOT_FOUND`, `local_status=DISABLED`

### Handling Deleted Users

When an employee leaves the organization:

1. **IT disables their Entra account** - Account is disabled but exists
2. **After retention period, IT deletes the account** - Moves to recycle bin (soft delete)
3. **After 30 days, account is permanently deleted** - Hard delete

**Administrator workflow:**

1. Run **Sync All from Azure** periodically (e.g., weekly)
2. Check the **Disabled Users Report** for affected models
3. Reassign model roles before the user's data becomes orphaned

---

## Disabled Users Governance

### Dashboard Alert

When models have disabled users in key roles, an alert appears on the Admin Dashboard:

- **Location**: Admin Dashboard, below the attestation reminder
- **Color**: Amber/yellow border indicating a governance concern
- **Content**: Count of affected models with preview of first 5
- **Action**: Click "View Report" for the full list

### Disabled Users Report

Access the full report via:
- Dashboard alert "View Report" link
- **Reports** > **Governance** > **Models with Disabled Users**

The report shows:

#### Summary Cards

| Card | Description |
|------|-------------|
| **Total Affected Models** | Count of models with at least one disabled user in a key role |
| **Hard Deleted Users** | Users permanently removed from Entra (`NOT_FOUND`) |
| **Soft Deleted Users** | Users in Entra recycle bin (`SOFT_DELETED`) |
| **IT Lockout Users** | Users disabled but not deleted (`EXISTS` with disabled account) |

#### Filters

- **Azure State**: Filter by Hard Deleted, Soft Deleted, or IT Lockout
- **Role Type**: Filter by affected role (Owner, Developer, etc.)

#### Report Table

| Column | Description |
|--------|-------------|
| **Model ID** | Internal model identifier |
| **Model Name** | Links to model detail page |
| **Affected Role** | The role held by the disabled user |
| **User Name** | Links to user detail page |
| **Email** | User's email address |
| **Azure State** | Current Entra sync status |
| **Actions** | Link to edit the model |

#### Export

Click **Export CSV** to download the report for offline analysis or audit documentation.

### Remediation Workflow

When you identify models with disabled users:

1. **Assess urgency** based on Azure State:
   - **IT Lockout**: May be temporary (leave of absence). Verify with HR/IT before reassigning.
   - **Soft Deleted**: User has departed. Reassign within 30 days before hard deletion.
   - **Hard Deleted**: User is gone. Reassign immediately.

2. **Identify replacement**:
   - Contact the model's business line
   - Check if there's a documented delegate or backup owner
   - Consult with the departing user's manager

3. **Reassign the role**:
   - Click on the model name to open the model detail page
   - Edit the model and update the Owner, Developer, or other affected role
   - Save changes

4. **Document the change**:
   - The system automatically logs role changes in the audit trail
   - Add a comment if needed explaining the reassignment reason

5. **Verify completion**:
   - Return to the Disabled Users Report
   - Confirm the model no longer appears (after page refresh)

---

## Reference Data Management

The Reference Data page consolidates management of core entities:

| Tab | Purpose |
|-----|---------|
| **Vendors** | Manage third-party model vendors |
| **Users** | Application user management |
| **Entra Directory** | Corporate directory browser and provisioning |

Additional reference data pages:
- **Regions** - Geographic regions for model deployment and approvals
- **Teams** - Team structure for organizing users and models
- **Tags** - Categorization tags for models

---

## Taxonomy Configuration

Taxonomies are controlled vocabularies used throughout the application to ensure consistent classification and reporting. Access via **Configuration** > **Taxonomy**.

### Managing Taxonomies

Administrators can:

- Add new taxonomy values
- Edit labels, codes, and descriptions
- Set sort order for dropdown displays
- Activate/deactivate values (deactivated values are hidden from dropdowns but preserved in historical records)
- Configure bucket taxonomies for range-based classifications

> **Note**: System taxonomies (marked with a lock icon) cannot be deleted but can have their values modified.

---

### Taxonomy Reference

The following sections describe each taxonomy, its purpose, and the values available.

---

#### Model Risk Tier

**Purpose**: Classifies models by criticality and materiality to determine validation intensity and monitoring frequency.

| Code | Label | Description |
|------|-------|-------------|
| `TIER_1` | Tier 1 - High Risk | Critical models with significant financial or regulatory impact. Require comprehensive validation and frequent monitoring. |
| `TIER_2` | Tier 2 - Medium Risk | Important models with moderate impact. Require standard validation and periodic monitoring. |
| `TIER_3` | Tier 3 - Low Risk | Non-critical models with limited impact. Require basic validation and less frequent monitoring. |
| `TIER_4` | Tier 4 - Very Low Risk | Minimal-impact models with very limited scope. Require lightweight validation and minimal monitoring. |

**Used in**: Model details, validation scheduling, validation policy configuration.

---

#### Validation Type

**Purpose**: Categorizes the type of validation activity being performed.

| Code | Label | Description |
|------|-------|-------------|
| `INITIAL` | Initial Validation | First-time validation of a new model before production deployment. |
| `COMPREHENSIVE` | Comprehensive Validation | Full deep-dive validation covering all aspects of model performance. Used for periodic revalidations. |
| `TARGETED` | Targeted Review | Focused review on specific model aspects or identified issues. |
| `INTERIM` | Interim Model Change Review | Auto-generated validation for model changes with imminent implementation dates. Expedited review to validate changes before production deployment. |

**Used in**: Validation requests.

---

#### Validation Outcome

**Purpose**: Records the result of a validation activity.

| Code | Label | Description |
|------|-------|-------------|
| `PASS` | Pass | Model validation passed with no material findings. |
| `PASS_WITH_FINDINGS` | Pass with Findings | Model validation passed but with findings that require remediation. |
| `FAIL` | Fail | Model validation failed and requires significant remediation. |

**Used in**: Validation outcomes.

---

#### Validation Priority

**Purpose**: Indicates the urgency of a validation request for resource allocation.

| Code | Label | Description |
|------|-------|-------------|
| `URGENT` | Urgent | Time-sensitive validation requiring prioritized resources. |
| `STANDARD` | Standard | Normal priority - standard processing timeline. |

**Used in**: Validation requests.

---

#### Validation Request Status

**Purpose**: Tracks the workflow state of validation requests through the validation lifecycle.

| Code | Label | Description |
|------|-------|-------------|
| `INTAKE` | Intake | Initial validation request submission - awaiting assignment and planning. |
| `PLANNING` | Planning | Scoping and resource allocation phase. |
| `IN_PROGRESS` | In Progress | Active validation work being performed. |
| `REVIEW` | Review | Internal QA and compilation of findings. |
| `PENDING_APPROVAL` | Pending Approval | Awaiting stakeholder sign-offs. |
| `REVISION` | Revision | Sent back by approver for revisions - awaiting validator updates. |
| `APPROVED` | Approved | Validation complete with all approvals. |
| `ON_HOLD` | On Hold | Temporarily paused - requires reason tracking. |
| `CANCELLED` | Cancelled | Terminated before completion - requires justification. |

**Used in**: Validation workflow management.

---

#### Overall Rating

**Purpose**: Final determination of whether a model is suitable for its intended use.

| Code | Label | Description |
|------|-------|-------------|
| `FIT_FOR_PURPOSE` | Fit for Purpose | Model is suitable for its intended use without material concerns. |
| `NOT_FIT_FOR_PURPOSE` | Not Fit for Purpose | Model is not suitable for its intended use and requires significant remediation. |

**Used in**: Validation outcomes.

---

#### Model Ownership Type

**Purpose**: Classifies models by their regional scope and ownership structure.

| Code | Label | Description |
|------|-------|-------------|
| `GLOBAL` | Global | Single global implementation with no regional specificity. |
| `REGIONALLY_OWNED` | Regionally Owned | Models owned and maintained by a specific region. |
| `GLOBAL_WITH_REGIONAL_IMPACT` | Global with Regional Impact | Global models with region-specific implementations or adaptations. |

**Used in**: Model details, approval routing.

---

#### Approval Role

**Purpose**: Defines the roles eligible to approve validation requests. Administrators can configure which approval roles are required for different scenarios.

| Code | Label | Description |
|------|-------|-------------|
| `GLOBAL_APPROVER` | Global Approver | Global approver role for cross-regional validations. |
| `REGIONAL_APPROVER` | Regional Approver | Regional approver role (supports region-coded variants). |
| `REGIONAL_VALIDATOR` | Regional Validator | Regional validator role (supports region-coded variants). |
| `MODEL_OWNER` | Model Owner | Model owner approval. |
| `MODEL_RISK_COMMITTEE` | Model Risk Committee | Committee-level approver. |
| `SENIOR_MANAGEMENT` | Senior Management | Senior management approver. |
| `COMMITTEE` | Committee | Generic committee approver. |

**Used in**: Validation approval workflows, conditional approval rules.

---

#### Model Hierarchy Type

**Purpose**: Defines types of hierarchical (parent-child) relationships between models.

| Code | Label | Description |
|------|-------|-------------|
| `SUB_MODEL` | Sub-Model | Child model that is a component or subset of a parent model. |

**Used in**: Model hierarchy relationships.

---

#### Model Dependency Type

**Purpose**: Classifies data flow relationships between models (feeder/consumer relationships).

| Code | Label | Description |
|------|-------|-------------|
| `INPUT_DATA` | Input Data | Feeder model provides raw data inputs to consumer model. |
| `SCORE` | Score/Output | Feeder model provides calculated scores or predictions to consumer model. |
| `PARAMETER` | Parameter | Feeder model provides configuration parameters or coefficients to consumer model. |
| `GOVERNANCE_SIGNAL` | Governance Signal | Feeder model provides governance flags or override signals to consumer model. |
| `OTHER` | Other | Other types of model dependencies not covered by standard categories. |

**Used in**: Model dependency relationships, lineage visualization.

---

#### Application Relationship Type

**Purpose**: Describes how models interact with applications from the Managed Application Portfolio (MAP).

| Code | Label | Description |
|------|-------|-------------|
| `DATA_SOURCE` | Data Source | Application provides input data to the model. |
| `EXECUTION` | Execution Platform | Application runs or hosts the model. |
| `OUTPUT_CONSUMER` | Output Consumer | Application consumes model outputs or scores. |
| `MONITORING` | Monitoring/Alerting | Application monitors model performance. |
| `REPORTING` | Reporting/Dashboard | Application displays model results. |
| `DATA_STORAGE` | Data Storage | Application stores model data or results. |
| `ORCHESTRATION` | Workflow/Orchestration | Application orchestrates model execution. |
| `VALIDATION` | Validation Support | Application supports model validation process. |
| `OTHER` | Other | Other relationship type. |

**Used in**: Model-application linkages.

---

#### Recommendation Priority

**Purpose**: Determines the urgency and approval requirements for validation recommendations.

| Code | Label | Description |
|------|-------|-------------|
| `HIGH` | High | High priority - requires prompt action with senior oversight. Full approval workflow required. |
| `MEDIUM` | Medium | Standard priority - requires timely remediation. Full approval workflow required. |
| `LOW` | Low | Low priority - can be scheduled as resources permit. Validator approval sufficient. |
| `CONSIDERATION` | Consideration | Minor suggestion or observation - action plan not required. Developer acknowledges and closes. |

**Used in**: Validation recommendations.

---

#### Recommendation Status

**Purpose**: Tracks the workflow state of recommendations through their remediation lifecycle.

| Code | Label | Description |
|------|-------|-------------|
| `REC_DRAFT` | Draft | Initial draft - validator is still composing the recommendation. |
| `REC_PENDING_RESPONSE` | Pending Response | Finalized and sent to developer - awaiting acknowledgement. |
| `REC_PENDING_ACKNOWLEDGEMENT` | Pending Acknowledgement | Developer must acknowledge or submit rebuttal. |
| `REC_IN_REBUTTAL` | In Rebuttal | Developer submitted rebuttal - awaiting validator review. |
| `REC_PENDING_ACTION_PLAN` | Pending Action Plan | Acknowledged - developer must submit action plan. |
| `REC_PENDING_VALIDATOR_REVIEW` | Pending Validator Review | Action plan submitted - awaiting validator approval. |
| `REC_OPEN` | Open | Action plan approved - remediation work in progress. |
| `REC_REWORK_REQUIRED` | Rework Required | Validator rejected closure evidence - additional work needed. |
| `REC_PENDING_CLOSURE_REVIEW` | Pending Closure Review | Closure evidence submitted - awaiting validator review. |
| `REC_PENDING_APPROVAL` | Pending Final Approval | Validator approved closure - awaiting stakeholder approvals. |
| `REC_CLOSED` | Closed | All approvals received - recommendation successfully closed. |
| `REC_DROPPED` | Dropped | Rebuttal accepted - recommendation withdrawn. |

**Used in**: Recommendation workflow management.

---

#### Recommendation Category

**Purpose**: Classifies recommendations by the type of issue identified.

| Code | Label | Description |
|------|-------|-------------|
| `DATA_QUALITY` | Data Quality | Issues related to input data, data sources, or data transformations. |
| `METHODOLOGY` | Methodology | Issues with model theory, algorithms, or statistical methods. |
| `IMPLEMENTATION` | Implementation | Issues with code, systems, or technical implementation. |
| `DOCUMENTATION` | Documentation | Issues with model documentation, specifications, or user guides. |
| `MONITORING` | Monitoring | Issues with ongoing performance monitoring or controls. |
| `GOVERNANCE` | Governance | Issues with model governance, ownership, or approval processes. |
| `OTHER` | Other | Other issues not covered by standard categories. |

**Used in**: Validation recommendations.

---

#### Action Plan Task Status

**Purpose**: Tracks the status of individual tasks within recommendation action plans.

| Code | Label | Description |
|------|-------|-------------|
| `NOT_STARTED` | Not Started | Task has not been started yet. |
| `IN_PROGRESS` | In Progress | Task is currently being worked on. |
| `COMPLETED` | Completed | Task has been completed. |

**Used in**: Recommendation action plans.

---

#### Model Usage Frequency

**Purpose**: Documents how frequently a model is executed in production.

| Code | Label | Description |
|------|-------|-------------|
| `DAILY` | Daily | Model runs daily or more frequently. |
| `MONTHLY` | Monthly | Model runs monthly. |
| `QUARTERLY` | Quarterly | Model runs quarterly. |
| `ANNUALLY` | Annually | Model runs annually. |

**Used in**: Model details.

---

#### Exception Closure Reason

**Purpose**: Documents why a model exception was closed.

| Code | Label | Description |
|------|-------|-------------|
| `NO_LONGER_EXCEPTION` | No longer an exception | The underlying condition that triggered the exception has been resolved. |
| `EXCEPTION_OVERRIDDEN` | Exception overridden | Management has approved an override for this exception. |
| `OTHER` | Other | Other closure reason - see narrative for details. |

**Used in**: Exception management.

---

#### Regulatory Category

**Purpose**: Links models to the regulatory or prudential regimes they support.

| Code | Label | Description |
|------|-------|-------------|
| `CCAR_DFAST` | CCAR / DFAST Stress Testing | Models used for Federal Reserve stress tests and internal CCAR projections. |
| `BASEL_CREDIT` | Basel Regulatory Capital – Credit Risk (RWA) | Calculates Basel risk-weighted assets for credit portfolios (PD/LGD/EAD). |
| `MARKET_RISK` | Market Risk Capital (VaR / FRTB / Stressed VaR / RNIV) | Trading book capital models including VaR, stressed VaR, RNIV, and FRTB. |
| `CCR_CVA` | Counterparty Credit Risk / CVA Capital | Exposure, PFE, and CVA models supporting counterparty credit risk capital. |
| `ICAAP` | Internal Economic Capital / ICAAP | Economic capital and ICAAP models beyond regulatory minima. |
| `CECL` | CECL / Allowance for Credit Losses (ACL) | Expected credit loss and allowance models under U.S. GAAP CECL. |
| `IFRS9_ECL` | IFRS 9 Expected Credit Loss | IFRS 9 staging and expected credit loss models for non-U.S. entities. |
| `FAIR_VALUE` | Fair Value / Valuation for Financial Reporting | ASC 820 fair value and valuation models for financial reporting. |
| `LIQUIDITY` | Liquidity Risk & LCR / NSFR | Liquidity coverage, NSFR, and cashflow forecasting models. |
| `IRRBB` | Interest Rate Risk in the Banking Book (IRRBB) | IRRBB models for EVE/NII metrics and customer behaviour assumptions. |
| `ALM_FTP` | Asset/Liability Management (ALM) / FTP | Structural balance sheet, FTP, and hedge optimization models. |
| `AML_SANCTIONS` | AML / Sanctions / Transaction Monitoring | AML/BSA transaction monitoring, sanctions screening, and customer risk scoring. |
| `FRAUD` | Fraud Detection | Fraud detection across cards, payments, and digital channels. |
| `CONDUCT_RISK` | Conduct Risk / Fair Lending / UDAAP | Models supporting conduct, fair lending, and UDAAP surveillance. |
| `OP_RISK` | Operational Risk Capital / Scenario Models | Operational risk capital, LDA, and scenario aggregation models. |
| `REG_REPORTING` | Regulatory Reporting (FFIEC, FR Y-9C, FR Y-14, Call Reports, etc.) | Models feeding data to regulatory reports and schedules. |
| `INT_REPORTING` | Internal Risk & Board Reporting | Models that drive internal risk dashboards and board reporting. |
| `PRICING` | Pricing & Valuation – Internal / Customer | Pricing and valuation models used primarily for business decisioning. |
| `MARGIN_COLL` | Margin & Collateral Models (IM / VM / Haircuts) | Margin, collateral, and haircut models for IM/VM and eligibility. |
| `MRM_META` | Model Risk Management / Meta-Models | Models that quantify or aggregate model risk (scores, capital add-ons). |
| `NON_REG` | Non-Regulatory / Business Only | Business-impacting models with no direct regulatory regime linkage. |

**Used in**: Model details, regulatory reporting.

---

#### Model Type

**Purpose**: Functional classification describing what the model does. This is a comprehensive list of model types across risk domains.

**Credit Risk Models:**
| Code | Label | Description |
|------|-------|-------------|
| `RETAIL_PD` | Retail PD Model | Predicts probability of default for retail exposures. |
| `WHOLESALE_PD` | Wholesale PD Model | Predicts probability of default for wholesale obligors. |
| `LGD` | LGD Model (Loss Given Default) | Estimates loss severity conditional on default. |
| `EAD_CCF` | EAD / CCF Model | Estimates exposure or credit conversion factors at default. |
| `APP_SCORECARD` | Application Scorecard | Origination scorecard for approve/decline, limits, and pricing. |
| `BEHAV_SCORECARD` | Behavioural Scorecard | Scores existing accounts based on recent behaviour. |
| `COLL_SCORECARD` | Collections Scorecard | Prioritizes delinquent accounts for collections strategies. |
| `INTERNAL_RATING` | Internal Rating Model | Assigns internal ratings mapped to PD/LGD bands. |
| `TRANSITION_MATRIX` | Transition / Migration Model | Projects migrations between delinquency or rating states. |
| `PREPAYMENT` | Prepayment Model | Predicts early payoff, refinance, or attrition. |
| `CURE_RECOVERY` | Cure / Recovery Model | Models probability, timing, and magnitude of cure or recovery. |

**Market Risk & Valuation Models:**
| Code | Label | Description |
|------|-------|-------------|
| `PRICING_LINEAR` | Pricing Model – Linear | Values bonds, swaps, forwards, and other linear instruments. |
| `PRICING_EXOTIC` | Pricing Model – Options & Exotics | Values options and structured products using advanced methods. |
| `CURVE_CONSTRUCT` | Curve / Surface Construction | Builds discount curves, credit curves, vol surfaces, and correlations. |
| `VAR_ES` | VaR / Expected Shortfall (ES) | Computes market risk via VaR or ES methodologies. |
| `SENSITIVITY_AGG` | Sensitivity / Greeks Aggregation | Aggregates position sensitivities for hedging or limits. |
| `XVA` | XVA Model (CVA / DVA / FVA / MVA) | Calculates derivative valuation adjustments. |
| `RISK_SIMULATION` | Risk Factor Simulation | Simulates joint paths of market risk factors. |

**Treasury & ALM Models:**
| Code | Label | Description |
|------|-------|-------------|
| `NMD` | Non-Maturity Deposit (NMD) Model | Models NMD balances, stability, and rate sensitivity. |
| `LIQUIDITY_RUNOFF` | Liquidity Runoff Model | Projects stressed inflows/outflows and survival horizons. |
| `BAL_SHEET_DYN` | Balance Sheet Evolution Model | Simulates balance sheet composition under scenarios. |
| `IRRBB` | IRRBB Model (EVE / NII) | Projects EVE/NII impacts under rate scenarios. |
| `FTP` | Funds Transfer Pricing (FTP) | Allocates funding and liquidity costs across products. |

**Provisioning & Capital Models:**
| Code | Label | Description |
|------|-------|-------------|
| `ECL_ENGINE` | Expected Credit Loss (ECL) Engine | Combines components to produce lifetime expected losses. |
| `RESERVE_ALLOC` | Provision / Reserve Allocation | Allocates allowance or reserves across portfolios. |
| `ECON_CAPITAL` | Economic Capital Model | Computes economic capital via loss distributions and correlations. |
| `STRESS_TEST_PROJ` | Stress Testing Projection Model | Generates stressed projections of PPNR, losses, and capital. |
| `REG_METRIC_CALC` | Regulatory Metric Calculation | Calculates regulatory ratios such as capital, leverage, or liquidity. |

**Compliance Models:**
| Code | Label | Description |
|------|-------|-------------|
| `AML_TXN_MON` | Transaction Monitoring (AML) | Scores transactions or accounts and issues AML alerts. |
| `AML_CUST_RISK` | Customer Risk Rating (AML/KYC) | Assigns inherent AML risk scores to customers. |
| `SANCTIONS` | Sanctions Screening | Performs sanctions list matching and similarity scoring. |
| `FRAUD` | Fraud Detection Model | Detects fraudulent transactions or accounts across channels. |
| `FAIR_LENDING` | Fair Lending / Fairness Assessment | Quantifies disparate impact or bias in credit processes. |

**Operational Risk Models:**
| Code | Label | Description |
|------|-------|-------------|
| `OP_RISK_CAP` | Operational Risk Capital | Fits severity/frequency and computes op-risk capital. |
| `OP_RISK_SCEN` | Operational Risk Scenario | Aggregates scenario-based operational risk losses. |
| `CONDUCT_RISK` | Conduct Risk / Complaints Scoring | Scores complaints or events for conduct risk severity. |
| `VENDOR_RISK` | Vendor / Third-Party Risk Scoring | Scores third parties based on inherent risk and controls. |

**Business Models:**
| Code | Label | Description |
|------|-------|-------------|
| `PROPENSITY` | Propensity / Next-Best-Offer | Predicts acceptance likelihood for offers or products. |
| `CHURN` | Churn / Attrition Model | Predicts likelihood a customer will leave or reduce activity. |
| `PRICING_ELAST` | Pricing & Elasticity Model | Estimates demand or margin sensitivity to pricing changes. |
| `SEGMENTATION` | Segmentation / Clustering | Groups customers or exposures into segments. |
| `FORECAST_KPI` | Forecasting Model | Forecasts balances, volumes, revenues, or KPIs. |

**Meta-Models:**
| Code | Label | Description |
|------|-------|-------------|
| `AGGREGATION` | Aggregation / Composite Index | Combines multiple inputs into composite indices. |
| `ALLOCATION` | Mapping / Allocation Model | Allocates metrics between dimensions or entities. |
| `MRM_SCORING` | Model Risk Scoring | Scores models to determine tiering and validation intensity. |

**Used in**: Model details.

---

#### Qualitative Outcome

**Purpose**: Assessment outcomes for qualitative Key Performance Metrics (KPMs) using a traffic-light rating scale.

| Code | Label | Description |
|------|-------|-------------|
| `GREEN` | Green | KPM within acceptable parameters; no concerns identified. |
| `YELLOW` | Yellow | KPM warrants attention; minor concerns or approaching thresholds. |
| `RED` | Red | KPM breached thresholds or significant concerns identified; action required. |

**Used in**: KPM assessments, model monitoring.

---

#### Past Due Level (Bucket Taxonomy)

**Purpose**: Classifies models by how long they have been overdue for revalidation. This is a **bucket taxonomy** with contiguous day ranges. The `downgrade_notches` value affects the Final Model Risk Ranking.

| Code | Label | Day Range | Downgrade Notches | Description |
|------|-------|-----------|-------------------|-------------|
| `CURRENT` | Current | ≤ 0 days | 0 | Model is not past due (on or before due date). |
| `MINIMAL` | Minimal | 1 - 365 days | 1 | Model is 1-365 days past due. |
| `MODERATE` | Moderate | 366 - 730 days | 2 | Model is 366-730 days (1-2 years) past due. |
| `SIGNIFICANT` | Significant | 731 - 1095 days | 3 | Model is 731-1095 days (2-3 years) past due. |
| `CRITICAL` | Critical | 1096 - 1825 days | 3 | Model is 1096-1825 days (3-5 years) past due. |
| `OBSOLETE` | Obsolete | ≥ 1826 days | 3 | Model is more than 1825 days (5+ years) past due. |

**Used in**: Overdue revalidation report, risk ranking calculations.

> **Admin Note**: Bucket taxonomies require special handling. Buckets must be contiguous with no gaps or overlaps. Editing bucket ranges should be done carefully to maintain data integrity.

---

#### Model Approval Status

**Purpose**: Computed status indicating whether a model is approved for use based on its validation history.

| Code | Label | Description |
|------|-------|-------------|
| `NEVER_VALIDATED` | Never Validated | No validation request has ever been approved for this model. |
| `APPROVED` | Approved | Most recent validation is APPROVED with all required approvals complete. |
| `INTERIM_APPROVED` | Interim Approved | Most recent completed validation was of INTERIM type (temporary/expedited approval). |
| `VALIDATION_IN_PROGRESS` | Validation In Progress | Model is overdue but has an active validation request in planning stage or later. |
| `EXPIRED` | Expired | Model is overdue with no active validation or validation still in INTAKE stage. |

**Used in**: Model status display, compliance reporting.

---

#### Limitation Category

**Purpose**: Classifies model limitations discovered during validation.

| Code | Label | Description |
|------|-------|-------------|
| `DATA` | Data | Limitations related to data quality, availability, or representativeness. |
| `IMPLEMENTATION` | Implementation | Limitations in model implementation or technical constraints. |
| `METHODOLOGY` | Methodology | Limitations in modeling approach or theoretical foundation. |
| `MODEL_OUTPUT` | Model Output | Limitations in model outputs or their interpretation. |
| `OTHER` | Other | Other limitations not covered by above categories. |

**Used in**: Validation findings, model limitations.

---

#### MRSA Risk Level

**Purpose**: Classifies Model Risk-Sensitive Applications (MRSAs) by risk level to determine Independent Review Process (IRP) requirements.

| Code | Label | Requires IRP | Description |
|------|-------|--------------|-------------|
| `HIGH_RISK` | High-Risk | Yes | High-risk MRSA requiring Independent Review Process (IRP) coverage for oversight and governance. |
| `LOW_RISK` | Low-Risk | No | Low-risk MRSA not requiring formal IRP coverage but still subject to standard governance. |

**Used in**: MRSA management, IRP tracking.

---

#### IRP Review Outcome

**Purpose**: Records outcomes of Independent Review Process (IRP) periodic assessments.

| Code | Label | Description |
|------|-------|-------------|
| `SATISFACTORY` | Satisfactory | IRP review found MRSAs are adequately managed and controlled. |
| `CONDITIONALLY_SATISFACTORY` | Conditionally Satisfactory | IRP review found minor issues requiring attention within defined timeframe. |
| `NOT_SATISFACTORY` | Not Satisfactory | IRP review found significant deficiencies requiring immediate remediation. |

**Used in**: IRP reviews.

---

## Best Practices

1. **Sync regularly**: Run "Sync All from Azure" at least weekly to catch disabled accounts promptly.

2. **Monitor the dashboard**: Check the Disabled Users alert daily as part of admin duties.

3. **Document reassignments**: When changing model owners due to departures, note the reason for audit purposes.

4. **Coordinate with HR/IT**: For IT Lockout cases, verify the situation before reassigning roles - the user may be returning.

5. **Export for audits**: Use the CSV export feature to document governance reviews for compliance.

6. **Train delegates**: Ensure model owners have designated backups who can assume ownership if needed.

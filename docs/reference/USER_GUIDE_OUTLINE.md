# MRM System User Guide - Outline

## 1. Introduction
- **System Overview**: Purpose of the Model Risk Management (MRM) Inventory System.
- **Key Concepts**:
  - Models & Versions
  - Validations & Revalidations
  - Risk Tiers & Governance
- **User Roles & Permissions**:
  - **Model Owner/User**: Manages models, submits changes, provides documentation.
  - **Validator**: Conducts validations, reviews submissions, manages workflow.
  - **Admin**: System configuration, user management, policy setting.

## 2. Getting Started
- **Accessing the System**: Login procedures (Email/Password & SSO).
- **Navigation Tour**:
  - Sidebar Menu
  - Dashboard Widgets
  - Quick Actions
- **User Profile**: Managing account settings and preferences.

## 3. Model Management (For Model Owners)
- **Creating a New Model**:
  - Step-by-step wizard.
  - Defining Development Type (In-House vs. Third-Party).
  - Assigning Vendors (if applicable).
- **The Submission Workflow**:
  - **Draft**: Saving work in progress.
  - **Submit for Approval**: Triggering the governance review.
  - **Addressing Feedback**: Handling "Sent Back" status and resubmitting.
- **Managing Model Details**:
  - **Overview Tab**: Editing core metadata (Description, Risk Tier, etc.).
  - **Team Management**: Assigning Owners, Developers, and Delegates.
  - **Regions**: Defining where the model is used.
- **Version Control & Changes**:
  - **Recording a Change**: Creating a new Model Version.
  - **Scope Management**:
    - **Global Versions**: Applied to all regions.
    - **Regional Versions**: Specific overrides for certain geographies.
  - **Deployment Tracking**:
    - Marking versions as "Deployed".
    - Confirming production dates (Ratification tasks).

## 4. Validation Workflow (For Validators)
- **Validation Requests**:
  - **Creating a Request**:
    - Selecting Models (Single vs. Multi-model grouping).
    - Defining Scope (Global vs. Regional).
    - Setting Priority and Types.
  - **Auto-Generated Requests**: Understanding triggers from Major Model Changes.
- **The Validation Lifecycle**:
  - **Intake**: Reviewing submission completeness.
  - **Planning**: Assigning validators and setting timelines.
  - **Execution**: Tracking work components and findings.
  - **Review**: Peer review and sign-off.
  - **Approval**: Final governance approval.
- **Regional Approvals**:
  - Understanding when Regional Sign-off is required.
  - Managing multi-region approval chains.
- **Revalidation Management**:
  - **Periodic Reviews**: Tracking Comprehensive revalidation cycles.
  - **Deadlines**: Understanding Submission Due Dates vs. Validation Due Dates.
  - **Grace Periods**: Policy on late submissions.

## 5. Dashboards & Monitoring
- **Model Owner Dashboard**:
  - **My Models**: Quick access to owned inventory.
  - **Action Items**: Pending submissions, deployment confirmations, documentation requests.
- **Validator/Admin Dashboard**:
  - **Workload Management**: Active validations and assignments.
  - **Compliance Monitoring**:
    - Overdue Validations.
    - Models "Passed with Findings".
    - SLA Tracking.
- **Export Views**:
  - Creating custom data views.
  - Filtering and sorting.
  - Exporting data to CSV for external reporting.

## 6. Administration (For Admins)
- **User Management**:
  - Creating and editing users.
  - Importing from Microsoft Entra ID (Directory).
  - Managing Role assignments.
- **Vendor Management**:
  - Maintaining the approved vendor list.
- **System Configuration (Taxonomy)**:
  - Managing Dropdown Values (Risk Tiers, Model Types, etc.).
  - Configuring **Validation Policies**:
    - Setting Revalidation Frequencies by Risk Tier.
    - Defining Lead Times for Model Changes.
- **Regional Configuration**:
  - Managing Regions.
  - Toggling "Requires Regional Approval" settings.
- **Audit Logs**:
  - Searching system history.
  - Filtering by User, Entity, or Action.

## 7. Appendices
- **Glossary**: Definitions of MRM specific terms.
- **Status Reference**: Detailed explanation of all Model and Validation statuses.
- **FAQ**: Common questions and troubleshooting.

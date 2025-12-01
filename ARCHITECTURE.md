## Overview

Model Risk Management inventory system with a FastAPI backend, React/TypeScript frontend, and PostgreSQL database. Supports model cataloging, validation workflow, recommendations tracking, performance monitoring, regional deployment tracking, configurable taxonomies, and compliance reporting. Primary user roles: Admin (full control), Validator (workflow execution), Model Owner/Contributor (submit and track models), Regional/Global approvers (deployment approvals).

## Tech Stack
- Backend: FastAPI, SQLAlchemy 2.x ORM, Pydantic v2 schemas, Alembic migrations, JWT auth via python-jose, passlib/bcrypt for hashing.
- Frontend: React 18 + TypeScript + Vite + TailwindCSS, react-router-dom v6, Axios client with auth interceptor.
- Database: PostgreSQL (dockerized). In-memory SQLite used in tests.
- Testing: pytest for API; vitest + React Testing Library + happy-dom for web.

## Runtime & Deployment
- Local/dev via `docker compose up --build` (see `docker-compose.yml`). Services: `db` (Postgres on 5433), `api` (Uvicorn on 8001), `web` (Vite dev server on 5174).
- API entrypoint: `api/app/main.py` with CORS for localhost frontends.
- Env/config: `api/app/core/config.py` (DATABASE_URL, SECRET_KEY, algorithm, token expiry) loaded via `.env`; frontend uses `VITE_API_URL`.
- Migrations: Alembic in `api/alembic`; run inside container against hostname `db`.
- Seeding: `python -m app.seed` invoked at container start to create admin user, taxonomy values, regions, validation policies, component definitions, and demo directory data.

## Backend Architecture
- Entry & middleware: `app/main.py` registers routers and CORS.
- Routing modules (`app/api/`):
  - `auth.py`: login, user CRUD, mock Microsoft Entra directory search/provisioning.
  - `models.py`: model CRUD, regulatory metadata, cross-references to vendors, owners/developers, regulatory categories; RLS helpers in `app/core/rls.py`.
  - `model_versions.py`, `model_change_taxonomy.py`: versioning, change type taxonomy, change history.
  - `model_regions.py`, `regions.py`: normalized regions and model-region assignments.
  - `model_delegates.py`: delegate assignments for models.
  - `model_hierarchy.py`: parent-child model relationships (e.g., sub-models).
  - `model_dependencies.py`: feeder-consumer data flow relationships with DFS-based cycle detection to maintain DAG constraint.
  - `model_types.py`: hierarchical model type classification (categories and types).
  - `vendors.py`: vendor CRUD.
  - `taxonomies.py`: taxonomy/category and value management.
  - `validation_workflow.py`: end-to-end validation lifecycle (requests, status updates, assignments, outcomes, approvals, audit logging, component configurations, reports including deviation trends).
  - `workflow_sla.py`: SLA configuration endpoints.
  - `version_deployment_tasks.py`: deployment task tracking for model owners/approvers.
  - `approver_roles.py`: approver role/committee CRUD for additional model use approvals.
  - `conditional_approval_rules.py`: configurable rule management with English translation preview (additional approvals).
  - `map_applications.py`: search/retrieve applications from MAP (Managed Application Portfolio) inventory.
  - `model_applications.py`: model-application relationship CRUD with soft delete support.
  - `overdue_commentary.py`: overdue revalidation commentary CRUD (create, supersede, get history) for tracking explanations on overdue validations.
  - `decommissioning.py`: model decommissioning workflow with two-stage approval (validator review → global/regional approvals), replacement model handling, gap analysis, withdrawal support, PATCH updates (PENDING only with audit logging), and role-based dashboard endpoints (`pending-validator-review` for validators, `my-pending-owner-reviews` for model owners).
  - `audit_logs.py`: audit log search/filter.
  - `dashboard.py`: aging and workload summaries.
  - `export_views.py`: CSV/export-friendly endpoints.
  - `regional_compliance_report.py`: region-wise deployment & approval report.
  - `analytics.py`, `saved_queries.py`: analytics aggregations and saved-query storage.
  - `kpm.py`: KPM (Key Performance Metrics) library management - categories and individual metrics for ongoing model monitoring.
  - `monitoring.py`: Performance monitoring teams, plans, and plan metrics configuration with scheduling logic for submission/report due dates.
  - `recommendations.py`: Validation/monitoring findings lifecycle - action plans, rebuttals, closure workflow, approvals, and priority configuration with regional overrides.
  - `risk_assessment.py`: Model risk assessment CRUD with qualitative/quantitative scoring, inherent risk matrix calculation, overrides at three levels, per-region assessments, and automatic tier sync.
  - `qualitative_factors.py`: Admin-configurable qualitative risk factor management (CRUD for factors and rating guidance with weighted scoring).
- Core services:
  - DB session management (`core/database.py`), auth dependency (`core/deps.py`), security utilities (`core/security.py`), row-level security filters (`core/rls.py`).
  - PDF/report helpers in `validation_workflow.py` (FPDF) for generated artifacts.
- Models (`app/models/`):
  - Users & directory: `user.py`, `entra_user.py`, roles include Admin/Validator/Global Approver/Regional Approver/User.
  - Catalog: `model.py`, `vendor.py`, `taxonomy.py`, `region.py`, `model_version.py`, `model_region.py`, `model_delegate.py`, `model_change_taxonomy.py`, `model_version_region.py`, `model_type.py` (ModelType, ModelTypeCategory).
  - Model relationships: `model_hierarchy.py` (parent-child links with effective/end dates), `model_feed_dependency.py` (feeder-consumer data flows with active status tracking), `model_dependency_metadata.py` (extended metadata for dependencies, not yet exposed in UI).
  - Validation workflow: `validation.py` (ValidationRequest, ValidationStatusHistory, ValidationAssignment, ValidationOutcome, ValidationApproval, ValidationReviewOutcome, ValidationPlan, ValidationPlanComponent, ValidationComponentDefinition, ComponentDefinitionConfiguration/ConfigItem, ValidationPolicy, ValidationWorkflowSLA).
  - Overdue commentary: `overdue_revalidation_comment.py` (OverdueRevalidationComment - tracks explanations for overdue submissions/validations with supersession chain).
  - Decommissioning: `decommissioning.py` (DecommissioningRequest, DecommissioningStatusHistory, DecommissioningApproval - model retirement workflow with replacement tracking and gap analysis).
- Additional approvals: `conditional_approval.py` (ApproverRole, ConditionalApprovalRule, RuleRequiredApprover).
  - MAP Applications: `map_application.py` (mock application inventory), `model_application.py` (model-application links with relationship types).
  - KPM (Key Performance Metrics): `kpm.py` (KpmCategory, Kpm - library of ongoing monitoring metrics).
  - Performance Monitoring: `monitoring.py` (MonitoringTeam, MonitoringPlan, MonitoringPlanMetric, MonitoringPlanVersion, MonitoringPlanMetricSnapshot, monitoring_team_members, monitoring_plan_models junction tables).
  - Recommendations: `recommendation.py` (Recommendation, ActionPlanTask, RecommendationRebuttal, ClosureEvidence, RecommendationStatusHistory, RecommendationApproval, RecommendationPriorityConfig, RecommendationPriorityRegionalOverride).
  - Risk Assessment: `risk_assessment.py` (QualitativeRiskFactor, QualitativeFactorGuidance, ModelRiskAssessment, QualitativeFactorAssessment) - qualitative/quantitative scoring with inherent risk matrix and tier derivation.
  - Compliance/analytics: `audit_log.py`, `export_view.py`, `saved_query.py`, `version_deployment_task.py`, `validation_grouping.py`.
- Schemas: mirrored Pydantic models in `app/schemas/` for requests/responses.
- Authn/z: HTTP Bearer JWT tokens; `get_current_user` dependency enforces auth; role checks per endpoint; RLS utilities narrow visibility for non-privileged users.
- Audit logging: `AuditLog` persisted on key workflows (model changes, approvals, component config publishes, etc.).
- Reporting: Dedicated routers plus endpoints in `validation_workflow.py` for dashboard metrics and compliance reports (aging, workload, deviation trends).

## Frontend Architecture
- Entry: `src/main.tsx` mounts App within `AuthProvider` and `BrowserRouter`.
- Routing (`src/App.tsx`): guarded routes for login, dashboards (`/dashboard`, `/validator-dashboard`, `/my-dashboard`), models (list/detail/change records/decommissioning), validation workflow (list/detail/new), vendors (list/detail), users (list/detail), taxonomy (with KPM Library tab), audit logs, workflow configuration, batch delegates, regions, validation policies, component definitions, configuration history, approver roles, additional approval rules, monitoring plans (Admin only), reports hub (`/reports`), report detail pages (regional compliance, deviation trends), analytics, deployment tasks, pending submissions.
- Shared pieces:
  - Auth context (`src/contexts/AuthContext.tsx`) manages token/user; Axios client (`src/api/client.ts`) injects Bearer tokens and redirects on 401.
  - Layout (`src/components/Layout.tsx`) provides navigation shell.
  - Hooks/utilities: table sorting (`src/hooks/useTableSort.tsx`), CSV export helpers on pages.
- Pages (`src/pages/`): feature-specific UIs aligned to backend modules (e.g., `ModelsPage.tsx`, `ModelDetailsPage.tsx`, `DecommissioningRequestPage.tsx`, `PendingDecommissioningPage.tsx`, `ValidationWorkflowPage.tsx`, `ValidationRequestDetailPage.tsx`, `VendorsPage.tsx`, `TaxonomyPage.tsx` (with KPM Library tab), `AuditPage.tsx`, `WorkflowConfigurationPage.tsx`, `ApproverRolesPage.tsx`, `ConditionalApprovalRulesPage.tsx`, `MonitoringPlansPage.tsx`, `RegionalComplianceReportPage.tsx`, `DeviationTrendsReportPage.tsx`, `OverdueRevalidationReportPage.tsx`, `AnalyticsPage.tsx`, dashboards). Tables generally support sorting and CSV export; dates rendered via ISO splitting.
  - **DecommissioningRequestPage**: Includes downstream dependency warning (fetches outbound dependencies from model relationships API and displays amber warning banner listing consumer models before submission).
  - **ModelDetailsPage**: Decommissioning tab always visible with "Initiate Decommissioning" button (shown when model not retired and no active request exists).
  - **PendingDecommissioningPage**: Accessible by all authenticated users; shows role-specific pending requests (validators see pending reviews, model owners see requests awaiting their approval).
- Styling: Tailwind classes via `index.css` and Vite config; iconography via emojis/SVG inline.

## Data Model (conceptual)
- User & EntraUser directory entries; roles drive permissions.
- Model with vendor, owner/developer, taxonomy links (risk tier, model type, etc.), regulatory categories, delegates, and region assignments via ModelRegion. **Note**: Validation Type is associated with ValidationRequest, not Model (deprecated from Model UI).
- **ModelPendingEdit**: Edit approval workflow for approved models. When non-admin users edit an already-approved model, a pending edit record is created with `proposed_changes` and `original_values` (JSON). Admin reviews the changes via dashboard widget or model details page and can approve (applies changes) or reject (with comment). Includes `requested_by_id`, `reviewed_by_id`, `status` (pending/approved/rejected), `review_comment`, and timestamps.
- **Model Types**: Hierarchical classification with Categories (e.g., "Financial", "Operational") and Types (e.g., "Credit Risk", "Fraud Detection").
- **Model Relationships** (Admin-managed with full audit logging):
  - **ModelHierarchy**: Parent-child relationships (e.g., sub-models) with relation type taxonomy, effective/end dates, and notes. Prevents self-reference via database constraints.
  - **ModelFeedDependency**: Feeder-consumer data flow relationships with dependency type taxonomy, description, effective/end dates, and is_active flag. **Cycle detection enforced**: DFS algorithm prevents creation of circular dependencies to maintain DAG (Directed Acyclic Graph) constraint. Includes detailed error reporting with cycle path and model names.
  - **ModelDependencyMetadata**: 1:1 extended metadata for dependencies (feed frequency, interface type, criticality, data fields summary) for future governance tracking, not yet exposed in UI.
- ModelVersion tracks version metadata, change types, production dates, scope (global/regional) and links to ValidationRequest.
- ValidationRequest lifecycle with status history, assignments (validators), plan (components and deviations), approvals (traditional + conditional), outcomes/review outcomes, deployment tasks, and policies/SLA settings per risk tier. **Prior Validation Linking**: `prior_validation_request_id` (most recent APPROVED validation) and `prior_full_validation_request_id` (most recent APPROVED INITIAL/COMPREHENSIVE validation) are auto-populated when creating new validation requests.
- **ValidationPolicy**: Per-risk-tier configuration for validation scheduling with `frequency_months` (re-validation frequency), `grace_period_months` (additional time after submission due before overdue), and `model_change_lead_time_days` (days to complete validation after grace period). All fields are admin-configurable via `/validation-workflow/policies/` endpoints.
- **Conditional Model Use Approvals**: ApproverRole (committees/roles), ConditionalApprovalRule (configurable rules based on validation type, risk tier, governance region, deployed regions), RuleRequiredApprover (many-to-many link). ValidationApproval extended with approver_role_id, approval_evidence, voiding fields. Model extended with use_approval_date timestamp.
- Taxonomy/TaxonomyValue for configurable lists (risk tier, validation types, statuses, priorities, **Model Hierarchy Type, Model Dependency Type, Application Relationship Type**, etc.).
- MapApplication (mock MAP inventory) and ModelApplication (model-application links with relationship type, effective/end dates for soft delete).
- **Model Decommissioning**: DecommissioningRequest (model retirement workflow with status PENDING → VALIDATOR_APPROVED → APPROVED/REJECTED/WITHDRAWN), DecommissioningStatusHistory (audit trail), DecommissioningApproval (GLOBAL and REGIONAL approvals). Tracks reason (from Model Decommission Reason taxonomy), replacement model (required for REPLACEMENT/CONSOLIDATION reasons), last production date, gap analysis with justification, archive location. **Stage 1 Dual Approval**: When requestor is NOT the model owner, both Validator AND Owner approval are required before Stage 2 (tracked via `owner_approval_required`, `owner_reviewed_by_id`, `owner_reviewed_at`, `owner_comment`). Either can approve first; status stays PENDING until both complete. **Update Support**: PATCH endpoint allows creator or Admin to update requests while in PENDING status (with audit logging for all field changes).
- Region and VersionDeploymentTask for regional deployment approvals.
- **KPM Library**: KpmCategory (groupings like "Discriminatory Performance", "Calibration") and Kpm (individual metrics like "AUC", "Brier Score" with description, calculation, interpretation). Pre-seeded with 8 categories and ~30 KPMs covering model validation and ongoing monitoring metrics.
- **Performance Monitoring**: MonitoringTeam (groups of users responsible for monitoring), MonitoringPlan (recurring monitoring schedules for model sets with frequency: Monthly/Quarterly/Semi-Annual/Annual), MonitoringPlanMetric (KPM with yellow/red thresholds and qualitative guidance), MonitoringPlanVersion (immutable snapshots of metric configurations), MonitoringPlanMetricSnapshot (point-in-time metric config at version publish). Automatic due date calculation based on frequency and reporting lead days. **Version binding**: cycles lock to active plan version at DATA_COLLECTION start.
- **Component 9b (Performance Monitoring Plan Review)**: Validation plan component for assessing model's monitoring plan. ValidationPlanComponent extended with `monitoring_plan_version_id` and `monitoring_review_notes`. Required for Tier 1/2, IfApplicable for Tier 3. Validation enforced before Review/Pending Approval transitions.
- AuditLog captures actions across entities including relationship changes and conditional approval actions.
- SavedQuery/ExportView for analytics/reporting reuse.

## Request & Data Flow
1. Frontend calls Axios client -> FastAPI routes under `/auth`, `/models`, `/validation-workflow`, `/decommissioning`, `/vendors`, `/taxonomies`, `/model-types`, `/audit-logs`, `/regions`, `/model-versions`, `/model-change-taxonomy`, `/analytics`, `/saved-queries`, `/regional-compliance-report`, `/validation-workflow/compliance-report/*`, `/models/{id}/hierarchy/*`, `/models/{id}/dependencies/*`, etc.
2. `get_current_user` decodes JWT, routes apply role checks and RLS filters.
3. SQLAlchemy ORM persists/fetches entities; Alembic manages schema migrations. **Model relationships enforce business rules**: cycle detection prevents circular dependencies, self-reference constraints prevent invalid links, date range validation ensures data integrity.
4. Responses serialized via Pydantic schemas; frontend renders tables/cards with sorting/export.

## Reporting & Analytics
- Reports hub (`/reports`) lists available reports; detail pages for Regional Compliance, Deviation Trends, and Overdue Revalidation (CSV export, refresh).
- Backend report endpoints:
  - `GET /regional-compliance-report/` - Regional deployment and compliance
  - `GET /validation-workflow/compliance-report/deviation-trends` - Deviation trends
  - `GET /overdue-revalidation-report/` - Overdue items with commentary status (supports filters: overdue_type, comment_status, risk_tier, days_overdue_min, needs_update_only)
  - Dashboard reports (`/validation-workflow/dashboard/*`) and analytics aggregations (`/analytics`, saved queries)
- Export views in `export_views.py` provide CSV-friendly datasets.

## Conditional Model Use Approvals
- **Purpose**: Configurable additional approvals required for model use based on validation context and model attributes
- **Admin Configuration**:
  - ApproverRoles: Define committees/roles that can approve model use (e.g., "US MRM Committee", "Global Model Risk Officer")
  - ConditionalApprovalRules: Define when specific roles are required based on:
    - Validation type (e.g., Initial Validation, Annual Review)
    - Risk tier (e.g., Tier 1 High Risk)
    - Governance region (e.g., US wholly-owned)
    - Deployed regions (e.g., ANY of: US, UK, EU)
- **Rule Logic**:
  - Within dimension: OR logic (any value matches)
  - Across dimensions: AND logic (all non-empty dimensions must match)
  - Empty/null dimension = no constraint (matches ANY)
  - Deployed regions: rule applies if ANY overlap between model regions and rule regions
- **Evaluation Timing**:
  - When validation request is created
  - When validation request moves to "Pending Approval" status (handles cases where risk tier was null initially)
  - Admin can void approval requirements with reason
- **Approval Workflow**:
  - Any Admin can approve on behalf of any approver role
  - Evidence description required (e.g., meeting minutes reference, email approval)
  - Model.use_approval_date updated when all conditional approvals complete
- **English Translation**: Rules automatically generate human-readable explanations (e.g., "US Model Risk Management Committee approval required because validation type is Initial Validation AND model inherent risk tier is High (Tier 1) AND model governance region is US wholly-owned")
- **UI Components**:
  - `/approver-roles` - Admin management of approver roles/committees (CRUD with soft delete)
  - `/additional-approval-rules` - Admin management of rules with live English preview
  - ValidationRequestDetailPage Approvals tab - Shows required approvals, applied rules, submit/void actions
- **Backend Components**:
  - `app/core/rule_evaluation.py` - Rule matching and English translation logic
  - `app/api/approver_roles.py` - Approver role CRUD endpoints
- `app/api/conditional_approval_rules.py` - Additional approval rule CRUD with preview endpoint
  - `app/api/validation_workflow.py` - Integrated evaluation and approval submission
- **Audit Logging**: CONDITIONAL_APPROVAL_SUBMIT and CONDITIONAL_APPROVAL_VOID actions tracked with evidence/reason

## MAP Applications & Model-Application Relationships
- **Purpose**: Track supporting applications from the organization's Managed Application Portfolio (MAP) that are integral to a model's end-to-end process.
- **Data Model**:
  - **MapApplication**: Mock application inventory simulating integration with external MAP system. Fields: application_code, application_name, description, owner_name/email, department, technology_stack, criticality_tier, status, external_url.
  - **ModelApplication**: Junction table linking models to applications with relationship metadata. Fields: model_id, application_id, relationship_type_id (taxonomy), description, effective_date, end_date (soft delete), created_by_user_id.
- **Relationship Types** (taxonomy): DATA_SOURCE, EXECUTION, OUTPUT_CONSUMER, MONITORING, REPORTING, DATA_STORAGE, ORCHESTRATION, VALIDATION, OTHER.
- **Permissions**: Admin, Validator, model owner, and model developer can manage application links.
- **Soft Delete**: Removing a link sets end_date rather than deleting the record, preserving historical relationships.
- **API Endpoints**:
  - `GET /map/applications` - Search MAP inventory with filters (search, department, status, criticality)
  - `GET /map/applications/{id}` - Get application details
  - `GET /map/departments` - List available departments
  - `GET /models/{id}/applications` - List model's linked applications (optional include_inactive)
  - `POST /models/{id}/applications` - Add application link
  - `DELETE /models/{id}/applications/{app_id}` - Soft delete application link
- **Frontend**: "Applications" tab on Model Details page with search modal and relationship management.
- **Testing**: 20 tests in `tests/test_map_applications.py` covering MAP search, model-application CRUD, permissions, and soft delete.

## Overdue Revalidation Commentary
- **Purpose**: Track and explain delays in model revalidation submissions and validation completion. Enables MRM teams to monitor overdue items with documented explanations and target dates.
- **Commentary Types**:
  - **PRE_SUBMISSION**: For delays in model documentation submission (before validation work starts). Responsibility: Model owner, developer, or delegate.
  - **VALIDATION_IN_PROGRESS**: For delays in validation completion (after submission received). Responsibility: Assigned validator.
- **Data Model**:
  - **OverdueRevalidationComment**: Tracks explanations with supersession chain. Fields: validation_request_id, overdue_type, reason_comment, target_date, created_by_user_id, created_at, is_current, superseded_at, superseded_by_comment_id.
  - New comments automatically supersede previous current comment (is_current=False, superseded_by_comment_id set).
- **Staleness Detection**:
  - Comment is stale if older than 45 days OR if target_date has passed without resolution.
  - Stale comments trigger "Update required" alerts in UI.
- **Computed Completion Dates**:
  - PRE_SUBMISSION: target_submission_date + SLA lead_time_days
  - POST_SUBMISSION: validation_request.target_completion_date
- **Authorization Rules**:
  - Admin: Can submit on anyone's behalf for both types
  - PRE_SUBMISSION: Model owner, developer, or active delegate
  - VALIDATION_IN_PROGRESS: Assigned validator only
- **API Endpoints** (prefix: `/validation-workflow`):
  - `GET /requests/{id}/overdue-commentary` - Get current commentary with staleness check
  - `POST /requests/{id}/overdue-commentary` - Create/supersede commentary
  - `GET /requests/{id}/overdue-commentary/history` - Full comment history
  - `GET /models/{id}/overdue-commentary` - Convenience endpoint for model's latest request
  - `GET /dashboard/my-overdue-items` - User-specific overdue items with commentary status
- **Dashboard Integration**:
  - `GET /dashboard/overdue-submissions` and `GET /dashboard/overdue-validations` enhanced with commentary fields: comment_status, latest_comment, latest_comment_date, target_date, needs_comment_update.
- **Frontend Components**:
  - `OverdueCommentaryModal.tsx`: Form for submitting/updating explanations with comment history
  - `OverdueAlertBanner.tsx`: Reusable alert component for overdue status display
  - Overdue alert banners on ModelDetailsPage and ValidationRequestDetailPage show commentary status and "Provide Explanation" buttons
  - AdminDashboardPage enhancements:
    - "My Overdue Items" section: Personal task list showing items where the current user is responsible for providing explanations
    - Commentary status columns in Overdue Submissions and Overdue Validations tables
    - Color-coded badges: Current (green), Stale (yellow), Missing (red)
    - "Add Commentary" buttons for items needing updates
    - Commentary modal integration for quick updates without leaving dashboard
- **Testing**: 36 tests total (23 core in `test_overdue_commentary.py`, 13 dashboard integration in `test_dashboard_commentary.py`)

## KPM Library (Key Performance Metrics)
- **Purpose**: Standardized library of metrics for ongoing model performance monitoring, used in monitoring plans.
- **Data Model**:
  - **KpmCategory**: Metric groupings (e.g., "Discriminatory Performance", "Calibration", "Stability"). Fields: category_id, code, name, description, sort_order.
  - **Kpm**: Individual metrics within categories. Fields: kpm_id, category_id, name, description, calculation (formula/methodology), interpretation (guidance), sort_order, is_active, **evaluation_type** (Quantitative/Qualitative/Outcome Only).
- **Evaluation Types**:
  - **Quantitative**: Numerical results with configurable thresholds (yellow_min/max, red_min/max). Used for metrics like AUC, PSI, Brier Score.
  - **Qualitative**: Judgment-based assessments where SMEs apply rules/algorithms to determine R/Y/G outcome. Used for governance alignment, methodology assessments.
  - **Outcome Only**: Direct Red/Yellow/Green selection with supporting notes. Used for attestations and expert panel ratings.
- **Pre-seeded Data**: 13 categories with 47 KPMs:
  - 8 quantitative categories: Model calibration, Model performance, Model input data monitoring, Model stability, Global interpretability, Local interpretability, LLM monitoring, Fairness and governance.
  - 5 qualitative categories (from QUALCAT.json): Attestation-based (Outcome Only), Governance and usage alignment (Qualitative), Expert-judgment assessments (Qualitative), Model conditions and exception compliance (Qualitative), Algorithmic multi-step qualitative classification (mixed).
- **Qualitative Outcome Taxonomy**: "Qualitative Outcome" taxonomy with values: Green, Yellow, Red - used for recording qualitative KPM assessments.
- **API Endpoints**:
  - `GET /kpm/categories` - List all categories with their KPMs (optional active_only filter)
  - `POST /kpm/categories` - Create category (Admin)
  - `PATCH /kpm/categories/{id}` - Update category (Admin)
  - `DELETE /kpm/categories/{id}` - Delete category (Admin)
  - `GET /kpm/kpms` - List all KPMs
  - `GET /kpm/kpms/{id}` - Get single KPM
  - `POST /kpm/kpms` - Create KPM with category_id in body (Admin)
  - `PATCH /kpm/kpms/{id}` - Update KPM (Admin)
  - `DELETE /kpm/kpms/{id}` - Delete KPM (Admin)
- **Frontend**: "KPM Library" tab in TaxonomyPage for category and metric management with master-detail layout.

## Performance Monitoring Plans
- **Purpose**: Define recurring monitoring schedules for model performance review with configurable metrics and thresholds.
- **Data Model**:
  - **MonitoringTeam**: Groups of users responsible for monitoring. Fields: team_id, name, description, is_active, members (many-to-many via monitoring_team_members).
  - **MonitoringPlan**: Recurring monitoring schedule. Fields: plan_id, name, description, frequency (Monthly/Quarterly/Semi-Annual/Annual), monitoring_team_id, data_provider_user_id, reporting_lead_days, next_submission_due_date, next_report_due_date, is_active, models (many-to-many via monitoring_plan_models).
  - **MonitoringPlanMetric**: KPM configuration for a plan with thresholds. Fields: metric_id, plan_id, kpm_id, yellow_min/max, red_min/max, qualitative_guidance, sort_order, is_active.
  - **MonitoringPlanVersion**: Version snapshots of plan metric configurations. Fields: version_id, plan_id, version_number, version_name, description, effective_date, published_by_user_id, published_at, is_active.
  - **MonitoringPlanMetricSnapshot**: Point-in-time capture of metric configuration at version publish. Fields: snapshot_id, version_id, original_metric_id, kpm_id, yellow_min/max, red_min/max, qualitative_guidance, sort_order, is_active, kpm_name, kpm_category_name, evaluation_type.
- **Mixed KPM Type Support**: Plans can include a mix of quantitative and qualitative KPMs:
  - Quantitative KPMs: Configure numerical thresholds (yellow_min/max, red_min/max) for automatic R/Y/G determination.
  - Qualitative KPMs: Configure assessment guidance text; outcomes determined by SME judgment at monitoring time.
  - Outcome Only KPMs: Direct R/Y/G selection with notes (e.g., attestations).
- **Scheduling Logic**:
  - next_submission_due_date auto-calculated based on frequency (1/3/6/12 months from creation or last cycle)
  - next_report_due_date = next_submission_due_date + reporting_lead_days
  - "Advance Cycle" endpoint to manually progress to next period
- **Version Management**:
  - Manual "Publish" action creates immutable version snapshot (similar to ComponentDefinitionConfiguration)
  - Publishing deactivates previous active version and creates new version with metric snapshots
  - Cycles lock to active version at DATA_COLLECTION start
  - Version history preserved with cycle counts per version
  - CSV export of version metrics for comparison
  - Warning displayed when editing metrics with active cycles locked to previous versions
- **Access Control**:
  - **Team Management**: Admin only (create, update, delete teams)
  - **Plan Creation**: Admin only
  - **Plan Editing**: Admin OR members of the assigned monitoring team
    - Team members can update plan properties, add/update/remove metrics, and advance the plan cycle
    - Non-team members (except Admins) receive 403 Forbidden
  - **Version Publishing**: Admin or team member
  - **Audit Logging**: All plan/team/metric/version changes are logged with user attribution
- **API Endpoints** (prefix: `/monitoring`):
  - Teams: `GET /teams`, `GET /teams/{id}`, `POST /teams` (Admin), `PATCH /teams/{id}` (Admin), `DELETE /teams/{id}` (Admin)
  - Plans: `GET /plans`, `GET /plans/{id}`, `POST /plans` (Admin), `PATCH /plans/{id}` (Admin or team member), `DELETE /plans/{id}` (Admin or team member), `POST /plans/{id}/advance-cycle` (Admin or team member)
  - Metrics: `POST /plans/{id}/metrics` (Admin or team member), `PATCH /plans/{id}/metrics/{metric_id}` (Admin or team member), `DELETE /plans/{id}/metrics/{metric_id}` (Admin or team member)
  - Versions: `GET /plans/{id}/versions`, `GET /plans/{id}/versions/{version_id}`, `POST /plans/{id}/versions/publish`, `GET /plans/{id}/versions/{version_id}/export`
  - Model lookup: `GET /models/{model_id}/monitoring-plans` (for component 9b)
- **Frontend**: MonitoringPlansPage (Admin only) with tabs for Teams and Plans management. Metrics modal adapts configuration form based on KPM evaluation type: shows threshold fields for Quantitative KPMs, guidance text for Qualitative/Outcome Only. Versions modal displays version history with publish capability, version details with metric snapshots, and CSV export.

## Monitoring Cycles & Results (with Approval Workflow)
- **Purpose**: Capture periodic monitoring results with Red/Yellow/Green outcome calculation and formal approval workflow similar to validation projects.
- **Data Model**:
  - **MonitoringCycle**: Represents one monitoring period for a plan. Fields: cycle_id, plan_id, period_start_date, period_end_date, submission_due_date, report_due_date, status, assigned_to_user_id, submitted_at, submitted_by_user_id, completed_at, completed_by_user_id, notes, **plan_version_id** (locked at DATA_COLLECTION), **version_locked_at**, **version_locked_by_user_id**.
  - **MonitoringCycleApproval**: Approval records for cycles (Global + Regional). Fields: approval_id, cycle_id, approver_id, approval_type (Global/Regional), region_id, represented_region_id, is_required, approval_status (Pending/Approved/Rejected/Voided), comments, approved_at, voided_by_id, void_reason, voided_at.
  - **MonitoringResult**: Individual metric result for a cycle. Fields: result_id, cycle_id, plan_metric_id, model_id (optional for multi-model plans), numeric_value, outcome_value_id, calculated_outcome (GREEN/YELLOW/RED/N/A), narrative, supporting_data (JSON), entered_by_user_id.
- **Cycle Status Workflow**:
  ```
  PENDING → DATA_COLLECTION → UNDER_REVIEW → PENDING_APPROVAL → APPROVED
                                          ↘ CANCELLED          ↗
  ```
  - **PENDING**: Cycle created, awaiting start
  - **DATA_COLLECTION**: Active data entry period (results can be added)
  - **UNDER_REVIEW**: All results submitted, team reviewing quality
  - **PENDING_APPROVAL**: Awaiting required approvals (Global + Regional)
  - **APPROVED**: All approvals obtained, cycle complete and locked
  - **CANCELLED**: Terminated before completion
- **Approval Workflow**:
  - When cycle moves to PENDING_APPROVAL, system auto-creates approval requirements:
    - **Global Approval**: Always required (1 approval)
    - **Regional Approvals**: One per region where models in plan scope are deployed (based on model_regions table, only for regions with requires_regional_approval=true)
  - Approvers not pre-assigned; any user with appropriate role can approve
  - When all required approvals obtained, cycle auto-transitions to APPROVED
  - Admin can void approval requirements with documented reason
  - Rejection returns cycle to UNDER_REVIEW and resets other pending approvals
- **Outcome Calculation**:
  - **Quantitative metrics**: Auto-calculated based on MonitoringPlanMetric thresholds
    - GREEN: Value passes all threshold checks
    - YELLOW: Value below yellow_min or above yellow_max
    - RED: Value below red_min or above red_max
  - **Qualitative/Outcome Only metrics**: User directly selects outcome via outcome_value_id (taxonomy reference)
- **API Endpoints** (prefix: `/monitoring`):
  - Cycles: `POST /plans/{id}/cycles`, `GET /plans/{id}/cycles`, `GET /cycles/{id}`, `PATCH /cycles/{id}`, `DELETE /cycles/{id}`
  - Workflow: `POST /cycles/{id}/start`, `POST /cycles/{id}/submit`, `POST /cycles/{id}/cancel`, `POST /cycles/{id}/request-approval`
  - Results: `POST /cycles/{id}/results`, `GET /cycles/{id}/results`, `PATCH /results/{id}`, `DELETE /results/{id}`
  - Approvals: `GET /cycles/{id}/approvals`, `POST /cycles/{id}/approvals/{approval_id}/approve`, `POST /cycles/{id}/approvals/{approval_id}/reject`, `POST /cycles/{id}/approvals/{approval_id}/void`
- **Permission Model**:
  | Role | Cycles | Results | Approvals |
  |------|--------|---------|-----------|
  | Admin | Full CRUD, All workflow actions | Full CRUD | Approve on behalf (requires evidence), Reject, Void |
  | Global Approver | View | View | Approve Global approvals |
  | Regional Approver | View | View | Approve Regional for their authorized regions |
  | Team Member (Risk Function) | Full CRUD, Start/Request Approval/Cancel | Full CRUD | Request Approval only |
  | Data Provider | View, Submit results | Create, Update own | View only |
- **Approval Role Enforcement**:
  - **Global approvals**: Requires `Global Approver` role OR Admin with evidence
  - **Regional approvals**: Requires `Regional Approver` role with authorized regions OR Admin with evidence
  - **Admin proxy approvals**: Admin can approve on behalf but MUST provide `approval_evidence` (meeting minutes, email confirmation, etc.)
  - Response includes `is_proxy_approval: true` when Admin approves on behalf
- **Workflow Action Permissions** (enforced by `check_team_member_or_admin`):
  - **Start Cycle** (PENDING → DATA_COLLECTION): Admin or Team Member only - data providers cannot start cycles
  - **Submit Cycle** (DATA_COLLECTION → UNDER_REVIEW): Data providers, team members, and admins can submit (requires results completeness validation)
  - **Request Approval** (UNDER_REVIEW → PENDING_APPROVAL): Admin or Team Member only - data providers cannot advance to approval
  - **Cancel Cycle**: Admin or Team Member only - data providers cannot cancel
- **Results Completeness Validation** (enforced by `validate_results_completeness`):
  - Cycle must have at least one result entered before submission
  - Metrics without a value (null numeric_value and null outcome_value_id) require a narrative explanation
  - Returns detailed error messages listing which metrics are missing results or explanations
- **My Monitoring Tasks** (`GET /monitoring/my-tasks`):
  - Returns all active monitoring cycles the current user is involved with
  - User roles: `data_provider` (assigned as data provider), `team_member` (member of monitoring team), `assignee` (directly assigned to cycle)
  - Includes action_needed hints based on cycle status and user role
  - Shows overdue status and days until due for prioritization
- **Frontend**: ✅ Phases 4-7 COMPLETE (Cycles Tab, Results Entry, Approval UI, Reporting & Trends)
  - Phase 4: Cycles Tab with status badges, workflow actions, version info
  - Phase 5: Results Entry modal with threshold visualization, real-time outcome calculation
  - Phase 6: Approval UI with approve/reject/void modals, progress indicators
  - Phase 7: History tab with Performance Summary, Outcome Distribution bar, CSV Export
- **Reporting API Endpoints**:
  - `GET /monitoring/metrics/{plan_metric_id}/trend` - Time series trend data for a metric
  - `GET /monitoring/plans/{plan_id}/performance-summary` - Aggregate performance across cycles
  - `GET /monitoring/plans/{plan_id}/cycles/{cycle_id}/export` - Export cycle results to CSV

## Model Recommendations System
- **Purpose**: Track and manage validation/monitoring findings with action plans, rebuttals, and closure workflow.
- **Data Model**:
  - **Recommendation**: Core entity for tracking findings. Fields: recommendation_id, recommendation_code (auto-generated), model_id, validation_request_id (optional), monitoring_cycle_id (optional), title, description, root_cause_analysis, priority_id (taxonomy), category_id (taxonomy), current_status_id (taxonomy), assigned_to_id, original_target_date, current_target_date, created_by_id, finalized_at/by, acknowledged_at/by, closed_at/by, closure_summary.
  - **ActionPlanTask**: Tasks within action plan for a recommendation. Fields: task_id, recommendation_id, task_order, description, owner_id, target_date, completed_date, completion_status_id (taxonomy), completion_notes.
  - **RecommendationRebuttal**: Challenge to a recommendation with validator review. Fields: rebuttal_id, recommendation_id, submitted_by_id, rationale, supporting_evidence, submitted_at, reviewed_by_id, reviewed_at, review_decision (ACCEPT/OVERRIDE), review_comments, is_current.
  - **ClosureEvidence**: Supporting documentation for closure. Fields: evidence_id, recommendation_id, file_name, file_path, file_type, file_size_bytes, description, uploaded_by_id.
  - **RecommendationStatusHistory**: Audit trail of status changes with reason/context.
  - **RecommendationApproval**: Global/Regional approval requirements for closure. Fields: approval_id, recommendation_id, approval_type (GLOBAL/REGIONAL), region_id, approver_id, approval_status, comments, approval_evidence, voided_by_id, void_reason.
  - **RecommendationPriorityConfig**: Admin-configurable workflow settings per priority. Fields: config_id, priority_id, requires_final_approval, requires_action_plan, description.
  - **RecommendationPriorityRegionalOverride**: Regional overrides for priority configuration. Fields: override_id, priority_id, region_id, requires_action_plan (nullable), requires_final_approval (nullable), description. Unique constraint on (priority_id, region_id).
- **Priority Configuration with Regional Overrides**:
  - Base config per priority (High/Medium/Low/Consideration) sets default requires_action_plan and requires_final_approval.
  - Regional overrides allow different settings for models deployed in specific regions.
  - **Resolution Logic** (Most Restrictive Wins): If ANY region override requires action plan, it's required.
  - NULL values in overrides inherit from base config.
  - Example: Consideration priority may skip action plan globally, but US-deployed models require it.
- **Workflow States**:
  ```
  DRAFT → PENDING_RESPONSE → [Submit Action Plan OR Skip] → PENDING_VALIDATOR_REVIEW →
    PENDING_ACKNOWLEDGEMENT → OPEN → PENDING_CLOSURE → PENDING_APPROVAL → CLOSED
                           ↘ REBUTTAL_SUBMITTED → PENDING_RESPONSE (if rejected)
                                                → WITHDRAWN (if accepted)
  ```
- **Key Workflow Features**:
  - **Finalization**: Validator finalizes draft → moves to PENDING_RESPONSE
  - **Developer Response**: Submit action plan OR skip (if priority allows)
  - **Rebuttal**: Developer can challenge recommendation; validator reviews (ACCEPT/OVERRIDE)
  - **Acknowledgement**: Developer acknowledges finding → OPEN (active tracking)
  - **Closure**: Submit evidence → validator reviews → approval workflow (if required)
  - **Approvals**: Global + Regional (per model deployment regions) approval requirements
- **API Endpoints** (prefix: `/recommendations`):
  - CRUD: `POST /`, `GET /`, `GET /{id}`, `PATCH /{id}`
  - Workflow: `/finalize`, `/acknowledge`, `/decline-acknowledgement`, `/skip-action-plan`
  - Action Plan: `/action-plan`, `/action-plan/approve`, `/action-plan/reject`, `/action-plan/request-revisions`
  - Rebuttal: `/rebuttal`, `/rebuttal/{id}/review`
  - Closure: `/submit-closure`, `/review-closure`, `/evidence`
  - Approvals: `/approvals/{id}/approve`, `/approvals/{id}/reject`, `/approvals/{id}/void`
  - Priority Config: `GET/PATCH /priority-config/`, `/priority-config/{id}`, `/priority-config/regional-overrides/` (CRUD)
  - Dashboard: `/my-tasks`, `/open-summary`, `/overdue`
- **Frontend**: RecommendationsPage (list), RecommendationDetailPage (detail with workflow actions), TaxonomyPage "Recommendation Priority" tab (admin config with expandable regional overrides).
- **Testing**: 82 tests in `tests/test_recommendations.py` covering workflow, rebuttals, action plans, approvals, and regional overrides.

## Validation Scorecard System
- **Purpose**: Standardized framework for validators to assess and rate validation criteria across multiple sections, producing computed section and overall scores.
- **Workflow Position**: Completed AFTER validation plan/assignments and BEFORE final outcome determination. Scorecard ratings inform the outcome decision but are independent of it.
- **Data Model**:
  - **ScorecardSection**: Configurable assessment sections (e.g., "Evaluation of Conceptual Soundness", "Ongoing Monitoring/Benchmarking", "Outcome Analysis"). Fields: section_id, code, name, description, sort_order, is_active.
  - **ScorecardCriterion**: Individual criteria within sections. Fields: criterion_id, code, section_id, name, description_prompt, comments_prompt, include_in_summary, allow_zero, weight, sort_order, is_active.
  - **ValidationScorecardRating**: Per-criterion ratings for a validation request. Fields: rating_id, request_id (FK to ValidationRequest), criterion_code, rating, description, comments, created_at, updated_at.
  - **ValidationScorecardResult**: Computed scorecard results with configuration snapshot. Fields: result_id, request_id, overall_numeric_score, overall_rating, section_summaries (JSON), config_snapshot (JSON), computed_at.
- **Rating Scale**:
  - **Green (6)**: Excellent - fully meets expectations
  - **Green- (5)**: Good - meets expectations with minor observations
  - **Yellow+ (4)**: Acceptable - meets minimum with some concerns
  - **Yellow (3)**: Adequate - meets minimum requirements
  - **Yellow- (2)**: Marginal - barely acceptable
  - **Red (1)**: Unsatisfactory - fails to meet requirements
  - **N/A (0)**: Not Applicable - excluded from calculations
- **Score Computation**:
  - **Section Score**: Weighted average of criterion scores (N/A excluded), rounded half-up to nearest integer
  - **Overall Score**: Average of section scores (sections with all N/A excluded), rounded half-up
  - **Rating Derivation**: Score maps to rating (6→Green, 5→Green-, 4→Yellow+, 3→Yellow, 2→Yellow-, 1→Red, 0→null)
- **Configuration Source**: Criteria loaded from `SCORE_CRITERIA.json` at seed time into database tables. Admin can modify criteria via database.
- **Pre-seeded Configuration**: 3 sections with 14 criteria total:
  - Section 1 "Evaluation of Conceptual Soundness": 5 criteria (Documentation, Data, Methodology, Inputs/Outputs, Limitations)
  - Section 2 "Ongoing Monitoring/Benchmarking": 3 criteria (Benchmarking, Process Verification, Sensitivity Analysis)
  - Section 3 "Outcome Analysis": 6 criteria (Backtesting, Stress Testing, Boundary Testing, Accuracy Testing, Impact Analysis, Other Testing)
- **API Endpoints** (prefix: `/scorecard`):
  - `GET /config` - Get scorecard configuration (sections with nested criteria)
  - `GET /validation/{request_id}` - Get scorecard for a validation request
  - `POST /validation/{request_id}` - Create/update all ratings (bulk save)
  - `PATCH /validation/{request_id}/ratings/{criterion_code}` - Update single criterion rating
- **Frontend Components**:
  - `ValidationScorecardTab.tsx`: Full scorecard entry form with summary card, progress indicator, collapsible sections, auto-save on rating change
  - Integrated into ValidationRequestDetailPage as "Scorecard" tab (positioned after Plan, before Outcome)
- **Audit Logging**: CREATE and UPDATE actions logged with rating counts and overall score
- **Testing**: 56 unit tests covering rating conversions, score computations, section summaries, overall assessment, config loading, and edge cases

## Model Risk Assessment System
- **Purpose**: Derive model inherent risk tier from qualitative and quantitative factors using a standardized matrix approach with optional overrides at three levels.
- **Data Model**:
  - **QualitativeRiskFactor**: Admin-configurable assessment factors (e.g., "Model Complexity", "Data Quality", "Documentation", "Operational Impact"). Fields: factor_id, code, name, description, weight (0.0-1.0), sort_order, is_active.
  - **QualitativeFactorGuidance**: Rating guidance for each factor. Fields: guidance_id, factor_id, rating (HIGH/MEDIUM/LOW), points (1-3), description, sort_order.
  - **ModelRiskAssessment**: Per-model risk assessment with per-region support. Fields: assessment_id, model_id, region_id (null for global), quantitative_rating/comment/override, qualitative_override, derived_risk_tier_override (with comments), derived_risk_tier, derived_risk_tier_effective, final_tier_id, assessed_by_user_id, assessed_at, is_complete.
  - **QualitativeFactorAssessment**: Individual factor ratings for an assessment. Fields: factor_assessment_id, assessment_id, factor_id, rating (HIGH/MEDIUM/LOW), comment, score.
- **Scoring Logic**:
  - **Qualitative Score**: Weighted average of factor ratings where HIGH=3, MEDIUM=2, LOW=1
  - **Score Thresholds**: HIGH ≥2.1, MEDIUM ≥1.6, LOW <1.6
  - **Inherent Risk Matrix**: 3×3 grid combining Quantitative (rows) × Qualitative (columns):
    ```
              HIGH      MEDIUM    LOW
    HIGH      HIGH      MEDIUM    LOW
    MEDIUM    MEDIUM    MEDIUM    LOW
    LOW       LOW       LOW       VERY_LOW
    ```
  - **Tier Mapping**: HIGH→TIER_1, MEDIUM→TIER_2, LOW→TIER_3, VERY_LOW→TIER_4
- **Three Override Opportunities**:
  1. **Quantitative Override**: Override the quantitative rating with justification
  2. **Qualitative Override**: Override the calculated qualitative level with justification
  3. **Final Tier Override**: Override the derived inherent risk tier with justification
- **Per-Region Assessments**: Models can have both a global assessment (region_id=null) and region-specific assessments for deployment regions.
- **Automatic Tier Sync**: When assessment is completed (is_complete=true), the model's risk_tier_id is automatically updated to match the final_tier_id.
- **API Endpoints**:
  - Factor Config (Admin): `GET/POST /risk-assessment/factors/`, `PUT/DELETE /risk-assessment/factors/{id}`, `PATCH /risk-assessment/factors/{id}/weight`, `POST /risk-assessment/factors/validate-weights`, `POST /risk-assessment/factors/reorder`
  - Guidance: `POST /risk-assessment/factors/{id}/guidance`, `PUT/DELETE /risk-assessment/factors/guidance/{id}`
  - Assessments: `GET/POST /models/{id}/risk-assessments/`, `GET/PUT/DELETE /models/{id}/risk-assessments/{assessment_id}`
- **Frontend**:
  - ModelDetailsPage "Risk Assessment" tab with assessment form and results display
  - TaxonomyPage "Risk Factors" tab for admin factor configuration with weighted guidance
- **Audit Logging**: All factor changes, guidance updates, and assessment modifications are logged.
- **Testing**: 54 tests in `tests/test_risk_assessment_audit.py` covering factor CRUD, guidance management, weight validation, assessment workflow, scoring logic, and override handling.

## Security, Error Handling, Logging
- JWT auth with token expiry; passwords hashed with bcrypt.
- 401 handling: frontend interceptor removes token and redirects to `/login`.
- Authorization enforced in routers via role checks (Admin/Validator/etc.) and row-level security filters for users.
- Audit logging stored in `audit_logs` table; endpoints allow filtered retrieval.
- Errors surfaced as FastAPI HTTPExceptions with detail; frontend shows inline errors or toasts per page implementations.

## Configuration & Environments
- Backend settings via environment or `.env` (DATABASE_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES). Defaults in `core/config.py`.
- Frontend uses `VITE_API_URL` (defaults to `http://localhost:8001`); token stored in `localStorage`.
- Docker compose wires service URLs/ports; migrations must run inside the container to reach hostname `db`.

## Testing
- Backend: pytest suite in `api/tests/` with fixtures (`conftest.py`). Run `cd api && python -m pytest`. Additional shell scripts (`test_*.sh`, `test_*.py`) for targeted flows.
- Frontend: vitest in `web` (`pnpm test`, `pnpm test:run`, `pnpm test:coverage`).
- Full regression helper: `run_tests.sh` executes backend then frontend suites.

## Known Limitations & Technical Debt
- No real SSO; Microsoft Entra integration is mocked via `auth.py`/`entra_user.py`.
- Email/notification workflows are not implemented; approvals/assignments are in-app only.
- Reporting is limited to currently implemented endpoints (regional compliance, deviation trends, dashboards); additional reports referenced in design docs are not yet present.
- Background jobs/async tasks are absent; long-running work (PDF generation, exports) runs inline on request.

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
  - `methodology.py`: methodology library management - categories and methodologies with model linkage, search/filter, and soft delete.
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
  - `kpi_report.py`: KPI Report computing 21 model risk management metrics across categories (inventory, validation, monitoring, recommendations, governance, lifecycle, KRIs).
  - `analytics.py`, `saved_queries.py`: analytics aggregations and saved-query storage.
  - `kpm.py`: KPM (Key Performance Metrics) library management - categories and individual metrics for ongoing model monitoring.
  - `monitoring.py`: Performance monitoring teams, plans, and plan metrics configuration with scheduling logic for submission/report due dates.
  - `recommendations.py`: Validation/monitoring findings lifecycle - action plans, rebuttals, closure workflow, approvals, and priority configuration with regional overrides.
  - `risk_assessment.py`: Model risk assessment CRUD with qualitative/quantitative scoring, inherent risk matrix calculation, overrides at three levels, per-region assessments, and automatic tier sync.
  - `qualitative_factors.py`: Admin-configurable qualitative risk factor management (CRUD for factors and rating guidance with weighted scoring).
  - `scorecard.py`: Validation scorecard configuration (sections, criteria, weights), ratings per validation request, computed results, and configuration versioning with publish workflow.
  - `limitations.py`: Model limitations CRUD, retirement workflow, and critical limitations report with region filtering.
  - `attestations.py`: Full attestation workflow - cycles (create/open/close), scheduling rules (frequency, date windows), coverage targets, model-level records with submit/review/reject flow, bulk attestation submission, evidence attachments, and question configuration.
  - `residual_risk_map.py`: Residual risk map configuration - admin-configurable matrix mapping (Inherent Risk Tier × Scorecard Outcome) → Residual Risk level.
  - `fry.py`: FR Y-14 regulatory reporting structure - reports, schedules, metric groups, and line items CRUD for regulatory compliance mapping.
  - `validation_policies.py`: Validation policy configuration (frequency, grace period, lead time) per risk tier with admin CRUD.
  - `overdue_revalidation_report.py`: Overdue revalidation report with bucket classification and commentary status filtering.
  - `lob_units.py`: LOB (Line of Business) hierarchy CRUD, tree retrieval, CSV import/export with dry-run preview.
- Core services:
  - DB session management (`core/database.py`), auth dependency (`core/deps.py`), security utilities (`core/security.py`), row-level security filters (`core/rls.py`).
  - PDF/report helpers in `validation_workflow.py` (FPDF) for generated artifacts.
- Models (`app/models/`):
  - Users & directory: `user.py`, `entra_user.py`, `lob.py` (LOBUnit hierarchy with levels 1-6: SBU→LOB1→LOB2→LOB3→LOB4→LOB5+), roles include Admin/Validator/Global Approver/Regional Approver/User. **LOB Rollup**: `core/lob_utils.py` provides `get_lob_rollup_name()` to roll up deep LOB levels (LOB5+) to LOB4 for display purposes.
  - Catalog: `model.py`, `vendor.py`, `taxonomy.py`, `region.py`, `model_version.py`, `model_region.py`, `model_delegate.py`, `model_change_taxonomy.py`, `model_version_region.py`, `model_type.py` (ModelType, ModelTypeCategory), `methodology.py` (MethodologyCategory, Methodology).
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
  - Scorecard: `scorecard.py` (ScorecardSection, ScorecardCriterion, ValidationScorecardRating, ValidationScorecardResult, ScorecardConfigVersion, ScorecardSectionSnapshot, ScorecardCriterionSnapshot) - validation scorecard with configuration versioning.
  - Model Limitations: `limitation.py` (ModelLimitation) - inherent model constraints with significance classification, conclusion tracking, and retirement workflow.
  - Compliance/analytics: `audit_log.py`, `export_view.py`, `saved_query.py`, `version_deployment_task.py`, `validation_grouping.py`.
- Schemas: mirrored Pydantic models in `app/schemas/` for requests/responses.
- Authn/z: HTTP Bearer JWT tokens; `get_current_user` dependency enforces auth; role checks per endpoint; RLS utilities narrow visibility for non-privileged users.
- Audit logging: `AuditLog` persisted on key workflows (model changes, approvals, component config publishes, etc.).
- Reporting: Dedicated routers plus endpoints in `validation_workflow.py` for dashboard metrics and compliance reports (aging, workload, deviation trends).

## Frontend Architecture
- Entry: `src/main.tsx` mounts App within `AuthProvider` and `BrowserRouter`.
- Routing (`src/App.tsx`): guarded routes for login, role-specific dashboards (`/dashboard` Admin, `/validator-dashboard`, `/my-dashboard` Model Owner, `/approver-dashboard`), models (list/detail/change records/decommissioning), validation workflow (list/detail/new), recommendations (list/detail), monitoring (plans/cycles/my-tasks), attestation (cycles/my-attestations/bulk), vendors (list/detail), users (list/detail), taxonomy (with KPM Library tab), audit logs, workflow configuration, batch delegates, regions, validation policies, component definitions, configuration history, approver roles, additional approval rules, reports hub (`/reports`), report detail pages (regional compliance, deviation trends, overdue revalidation, critical limitations, name changes, KPI report), analytics, deployment tasks, pending submissions, reference data, FR Y-14 config.
- Shared pieces:
  - Auth context (`src/contexts/AuthContext.tsx`) manages token/user; Axios client (`src/api/client.ts`) injects Bearer tokens and redirects on 401.
  - Layout (`src/components/Layout.tsx`) provides navigation shell.
  - Hooks/utilities: table sorting (`src/hooks/useTableSort.tsx`), CSV export helpers on pages, column customization.
- **Column Customization**: ModelsPage supports dynamic column show/hide with persistence via ExportViews API. Users can select which columns to display from 26 available columns (including shared_owner, monitoring_manager, business_line_name, risk_tier, methodology, etc.), save custom views, and export CSV with selected columns. Pattern uses `columnRenderers` object mapping column keys to header/cell/csvValue functions, enabling unified rendering for both table display and CSV export.
- Pages (`src/pages/`): feature-specific UIs aligned to backend modules. Tables generally support sorting and CSV export; dates rendered via ISO splitting.
  - **Core**: `ModelsPage.tsx`, `ModelDetailsPage.tsx`, `VendorsPage.tsx`, `VendorDetailsPage.tsx`, `UsersPage.tsx`, `UserDetailsPage.tsx`, `TaxonomyPage.tsx` (with KPM Library tab), `AuditPage.tsx`
  - **Validation Workflow**: `ValidationWorkflowPage.tsx`, `ValidationRequestDetailPage.tsx`, `ValidationPoliciesPage.tsx`, `WorkflowConfigurationPage.tsx`, `ComponentDefinitionsPage.tsx`, `ConfigurationHistoryPage.tsx`
  - **Monitoring**: `MonitoringPlansPage.tsx`, `MonitoringPlanDetailPage.tsx`, `MonitoringCycleDetailPage.tsx`, `MyMonitoringPage.tsx`, `MyMonitoringTasksPage.tsx`
  - **Attestation**: `AttestationCyclesPage.tsx`, `AttestationDetailPage.tsx`, `MyAttestationsPage.tsx`, `BulkAttestationPage.tsx`, `AttestationReviewQueuePage.tsx`
  - **Recommendations**: `RecommendationsPage.tsx`, `RecommendationDetailPage.tsx`
  - **Decommissioning**: `DecommissioningRequestPage.tsx`, `PendingDecommissioningPage.tsx`
  - **Approvals**: `ApproverRolesPage.tsx`, `ConditionalApprovalRulesPage.tsx`
  - **Reports**: `ReportsPage.tsx`, `RegionalComplianceReportPage.tsx`, `DeviationTrendsReportPage.tsx`, `OverdueRevalidationReportPage.tsx`, `CriticalLimitationsReportPage.tsx`, `NameChangesReportPage.tsx`, `KPIReportPage.tsx`
  - **Dashboards**: `AdminDashboardPage.tsx`, `ValidatorDashboardPage.tsx`, `ModelOwnerDashboardPage.tsx`, `ApproverDashboardPage.tsx`
  - **Other**: `ModelChangeRecordPage.tsx`, `BatchDelegatesPage.tsx`, `RegionsPage.tsx`, `MyDeploymentTasksPage.tsx`, `MyPendingSubmissionsPage.tsx`, `AnalyticsPage.tsx`, `ReferenceDataPage.tsx`, `FryConfigPage.tsx`
  - **DecommissioningRequestPage**: Includes downstream dependency warning (fetches outbound dependencies from model relationships API and displays amber warning banner listing consumer models before submission).
  - **ModelDetailsPage**: Decommissioning tab always visible with "Initiate Decommissioning" button (shown when model not retired and no active request exists).
  - **PendingDecommissioningPage**: Accessible by all authenticated users; shows role-specific pending requests (validators see pending reviews, model owners see requests awaiting their approval).
- Styling: Tailwind classes via `index.css` and Vite config; iconography via emojis/SVG inline.

## Data Model (conceptual)
- User & EntraUser directory entries; roles drive permissions.
- Model with vendor, owner/developer, **shared_owner** (co-owner), **shared_developer** (co-developer), **monitoring_manager** (responsible for ongoing monitoring), taxonomy links (risk tier, model type, etc.), regulatory categories, delegates, and region assignments via ModelRegion. **Required fields**: `usage_frequency_id` (taxonomy reference). **Validation rules**: shared_owner ≠ owner, shared_developer ≠ developer. **Note**: Validation Type is associated with ValidationRequest, not Model (deprecated from Model UI).
- **ModelPendingEdit**: Edit approval workflow for approved models. When non-admin users edit an already-approved model, a pending edit record is created with `proposed_changes` and `original_values` (JSON). Admin reviews the changes via dashboard widget or model details page and can approve (applies changes) or reject (with comment). Includes `requested_by_id`, `reviewed_by_id`, `status` (pending/approved/rejected), `review_comment`, and timestamps.
- **Model Types**: Hierarchical classification with Categories (e.g., "Financial", "Operational") and Types (e.g., "Credit Risk", "Fraud Detection").
- **Methodology Library**: Categories (e.g., "AI/ML Tabular", "Statistical") and Methodologies (e.g., "Random Forest", "Linear Regression") assigned to models. **AI/ML Classification**: `is_aiml` boolean on MethodologyCategory flags whether models using that category's methodologies are AI/ML models. Models with no methodology show "Undefined". Admin-editable via Taxonomy UI; displayed in Models list (with filter) and Model Details page.
- **Model Relationships** (Admin-managed with full audit logging):
  - **ModelHierarchy**: Parent-child relationships (e.g., sub-models) with relation type taxonomy, effective/end dates, and notes. Prevents self-reference via database constraints.
  - **ModelFeedDependency**: Feeder-consumer data flow relationships with dependency type taxonomy, description, effective/end dates, and is_active flag. **Cycle detection enforced**: DFS algorithm prevents creation of circular dependencies to maintain DAG (Directed Acyclic Graph) constraint. Includes detailed error reporting with cycle path and model names.
  - **ModelDependencyMetadata**: 1:1 extended metadata for dependencies (feed frequency, interface type, criticality, data fields summary) for future governance tracking, not yet exposed in UI.
- ModelVersion tracks version metadata, change types, production dates, scope (global/regional) and links to ValidationRequest.
- ValidationRequest lifecycle with status history, assignments (validators), plan (components and deviations), approvals (traditional + conditional), outcomes/review outcomes, deployment tasks, and policies/SLA settings per risk tier. **Prior Validation Linking**: `prior_validation_request_id` (most recent APPROVED validation) and `prior_full_validation_request_id` (most recent APPROVED INITIAL/COMPREHENSIVE validation) are auto-populated when creating new validation requests.
- **ValidationPolicy**: Per-risk-tier configuration for validation scheduling with `frequency_months` (re-validation frequency), `grace_period_months` (additional time after submission due before overdue), and `model_change_lead_time_days` (days to complete validation after grace period). All fields are admin-configurable via `/validation-workflow/policies/` endpoints.
- **Conditional Model Use Approvals**: ApproverRole (committees/roles), ConditionalApprovalRule (configurable rules based on validation type, risk tier, governance region, deployed regions), RuleRequiredApprover (many-to-many link). ValidationApproval extended with approver_role_id, approval_evidence, voiding fields. Model extended with use_approval_date timestamp.
- Taxonomy/TaxonomyValue for configurable lists (risk tier, validation types, statuses, priorities, **Model Hierarchy Type, Model Dependency Type, Application Relationship Type**, etc.). **Bucket Taxonomies**: `taxonomy_type='bucket'` enables range-based values with `min_days`/`max_days` columns for contiguous day ranges (e.g., Past Due Level taxonomy classifies overdue models into Current/Minimal/Moderate/Significant/Critical/Obsolete buckets). Bucket taxonomies also support `downgrade_notches` column for configuring scorecard penalty in Final Risk Ranking calculation. Bucket taxonomies enforce contiguity validation (no gaps/overlaps), require admin role for modifications, and are used in Overdue Revalidation Report for severity classification and Final Risk Ranking for overdue penalty computation.
- MapApplication (mock MAP inventory) and ModelApplication (model-application links with relationship type, effective/end dates for soft delete).
- **Model Decommissioning**: DecommissioningRequest (model retirement workflow with status PENDING → VALIDATOR_APPROVED → APPROVED/REJECTED/WITHDRAWN), DecommissioningStatusHistory (audit trail), DecommissioningApproval (GLOBAL and REGIONAL approvals). Tracks reason (from Model Decommission Reason taxonomy), replacement model (required for REPLACEMENT/CONSOLIDATION reasons), last production date, gap analysis with justification, archive location. **Stage 1 Dual Approval**: When requestor is NOT the model owner, both Validator AND Owner approval are required before Stage 2 (tracked via `owner_approval_required`, `owner_reviewed_by_id`, `owner_reviewed_at`, `owner_comment`). Either can approve first; status stays PENDING until both complete. **Update Support**: PATCH endpoint allows creator or Admin to update requests while in PENDING status (with audit logging for all field changes).
- Region and VersionDeploymentTask for regional deployment approvals.
- **KPM Library**: KpmCategory (groupings like "Discriminatory Performance", "Calibration") and Kpm (individual metrics like "AUC", "Brier Score" with description, calculation, interpretation). Pre-seeded with 8 categories and ~30 KPMs covering model validation and ongoing monitoring metrics.
- **Performance Monitoring**: MonitoringTeam (groups of users responsible for monitoring), MonitoringPlan (recurring monitoring schedules for model sets with frequency: Monthly/Quarterly/Semi-Annual/Annual), MonitoringPlanMetric (KPM with yellow/red thresholds and qualitative guidance), MonitoringPlanVersion (immutable snapshots of metric configurations), MonitoringPlanMetricSnapshot (point-in-time metric config at version publish). Automatic due date calculation based on frequency and reporting lead days. **Version binding**: cycles lock to active plan version at DATA_COLLECTION start.
- **Component 9b (Performance Monitoring Plan Review)**: Validation plan component for assessing model's monitoring plan. ValidationPlanComponent extended with `monitoring_plan_version_id` and `monitoring_review_notes`. Required for Tier 1/2, IfApplicable for Tier 3. Validation enforced before Review/Pending Approval transitions.
- AuditLog captures actions across entities including relationship changes and conditional approval actions.
- SavedQuery/ExportView for analytics/reporting reuse.

## Request & Data Flow
1. Frontend calls Axios client -> FastAPI routes under `/auth`, `/models`, `/validation-workflow`, `/decommissioning`, `/vendors`, `/taxonomies`, `/model-types`, `/audit-logs`, `/regions`, `/model-versions`, `/model-change-taxonomy`, `/analytics`, `/saved-queries`, `/regional-compliance-report`, `/validation-workflow/compliance-report/*`, `/models/{id}/hierarchy/*`, `/models/{id}/dependencies/*`, `/scorecard/*`, etc.
2. `get_current_user` decodes JWT, routes apply role checks and RLS filters.
3. SQLAlchemy ORM persists/fetches entities; Alembic manages schema migrations. **Model relationships enforce business rules**: cycle detection prevents circular dependencies, self-reference constraints prevent invalid links, date range validation ensures data integrity.
4. Responses serialized via Pydantic schemas; frontend renders tables/cards with sorting/export.

## Reporting & Analytics
- Reports hub (`/reports`) lists available reports; detail pages for Regional Compliance, Deviation Trends, Overdue Revalidation, Name Changes, Critical Limitations, and KPI Report (CSV export, refresh).
- Backend report endpoints:
  - `GET /regional-compliance-report/` - Regional deployment and compliance
  - `GET /validation-workflow/compliance-report/deviation-trends` - Deviation trends
  - `GET /overdue-revalidation-report/` - Overdue items with commentary status (supports filters: overdue_type, comment_status, risk_tier, days_overdue_min, needs_update_only)
  - `GET /reports/critical-limitations` - Critical model limitations report with region filtering
  - `GET /kpi-report/` - KPI Report with 21 model risk management metrics (optional region_id filter)
  - Dashboard reports (`/validation-workflow/dashboard/*`) and analytics aggregations (`/analytics`, saved queries)
- Export views in `export_views.py` provide CSV-friendly datasets.

## KPI Report
- **Purpose**: Centralized KPI reporting for model risk management metrics, providing executive-level visibility into inventory, validation, monitoring, recommendations, and risk indicators.
- **Metrics** (21 total, organized by category):
  - **Model Inventory** (4.1-4.5): Total active models, breakdown by risk tier, breakdown by business line, % vendor models, % AI/ML models
  - **Validation** (4.6, 4.8, 4.9): % validated on time, average time to complete by risk tier, models with interim approval
  - **Key Risk Indicators** (4.7, 4.27): % overdue for validation (KRI), % high residual risk (KRI) - flagged with `is_kri: true`
  - **Monitoring** (4.10-4.12): % timely monitoring submissions, % breaching thresholds (RED), % with open performance issues
  - **Model Risk** (4.14): % models with critical limitations
  - **Recommendations** (4.18-4.21): Total open, % past due, average close time, % with high-priority open recs
  - **Governance** (4.22): % attestations received on time
  - **Model Lifecycle** (4.23-4.24): Models flagged for decommissioning, decommissioned in last 12 months
- **Metric Types**:
  - **count**: Simple integer (e.g., total models)
  - **ratio**: Numerator/denominator with percentage and drill-down model IDs
  - **duration**: Average time in days
  - **breakdown**: Distribution across categories with counts and percentages
- **Drill-Down Support**: Ratio metrics include `numerator_model_ids` array enabling click-through to filtered models list
- **Region Filtering**: Optional `region_id` query parameter scopes all metrics to models deployed in that region
- **API Endpoint**: `GET /kpi-report/?region_id={optional}`
- **Frontend**: `/reports/kpi` page with:
  - Region filter dropdown
  - Metrics grouped by category in expandable cards
  - KRI metrics highlighted with badge
  - Drill-down links for ratio metrics (navigates to `/models?model_ids=...`)
  - CSV export with all metrics and metadata

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
  - PRE_SUBMISSION: target_submission_date + `applicable_lead_time_days` (per-request, MAX across all models' risk tier policies)
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
- **API Validation Rules**:
  - **Target Date**: `original_target_date` cannot be in the past (returns 400: "Target date cannot be before the creation date")
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

## Model Limitations
- **Purpose**: Track inherent constraints, weaknesses, and boundaries of models that users and stakeholders need to be aware of. Limitations are discovered during validation but persist at the model level.
- **Data Model**:
  - **ModelLimitation**: Core entity with fields: limitation_id, model_id, validation_request_id (optional traceability), model_version_id (optional), recommendation_id (optional link to mitigation recommendation), significance (Critical/Non-Critical), category_id (from Limitation Category taxonomy), description, impact_assessment, conclusion (Mitigate/Accept), conclusion_rationale, user_awareness_description (required for Critical), is_retired, retirement_date, retirement_reason, retired_by_id, created_by_id, created_at, updated_at.
  - **Database constraints**: CHECK constraints enforce significance values, conclusion values, critical limitations must have user_awareness_description, retirement fields must be consistent (all set or all null).
- **Significance Classification**:
  - **Critical**: Significant model weaknesses requiring documented user awareness
  - **Non-Critical**: Minor limitations with lower impact
- **Conclusion Types**:
  - **Mitigate**: Limitation will be addressed (optionally linked to a Recommendation)
  - **Accept**: Limitation accepted with documented rationale
- **Limitation Categories** (taxonomy):
  - **Data**: Limitations related to data quality, coverage, availability
  - **Implementation**: Limitations in model implementation/coding
  - **Methodology**: Theoretical or methodological constraints
  - **Model Output**: Limitations affecting model outputs and decisions
  - **Other**: Miscellaneous limitations not fitting other categories
- **Lifecycle**:
  - Create: Validators/Admin document limitations during validation
  - Update: Edit non-retired limitations (significance, category, narratives)
  - Retire: Mark as retired with reason commentary (preserves history)
- **Authorization**: Admin and Validator roles can create, update, and retire limitations.
- **API Endpoints**:
  - `GET /models/{id}/limitations` - List limitations for a model (filters: include_retired, significance, conclusion, category_id)
  - `POST /models/{id}/limitations` - Create limitation (requires Validator/Admin)
  - `GET /limitations/{id}` - Get limitation details with relationships
  - `PATCH /limitations/{id}` - Update limitation (requires Validator/Admin, not retired)
  - `POST /limitations/{id}/retire` - Retire limitation with reason (requires Validator/Admin)
  - `GET /reports/critical-limitations` - Critical limitations report (filter by region)
- **Frontend**:
  - **ModelLimitationsTab**: "Limitations" tab on Model Details page with table view, filters (show retired, significance), and CRUD modals
  - **CriticalLimitationsReportPage**: Report page under `/reports/critical-limitations` with summary cards, category breakdown, and CSV export
- **Testing**: 27 tests in `tests/test_limitations.py` covering CRUD, authorization, retirement workflow, and critical limitations report.

## Validation Scorecard System
- **Purpose**: Standardized framework for validators to assess and rate validation criteria across multiple sections, producing computed section and overall scores.
- **Workflow Position**: Completed AFTER validation plan/assignments and BEFORE final outcome determination. Scorecard ratings inform the outcome decision but are independent of it.
- **Data Model**:
  - **ScorecardSection**: Configurable assessment sections (e.g., "Evaluation of Conceptual Soundness", "Ongoing Monitoring/Benchmarking", "Outcome Analysis"). Fields: section_id, code, name, description, sort_order, is_active.
  - **ScorecardCriterion**: Individual criteria within sections. Fields: criterion_id, code, section_id, name, description_prompt, comments_prompt, include_in_summary, allow_zero, weight, sort_order, is_active.
  - **ValidationScorecardRating**: Per-criterion ratings for a validation request. Fields: rating_id, request_id (FK to ValidationRequest), criterion_code, rating, description, comments, created_at, updated_at.
  - **ValidationScorecardResult**: Computed scorecard results with configuration snapshot. Fields: result_id, request_id, overall_numeric_score, overall_rating, section_summaries (JSON), config_snapshot (JSON), computed_at, config_version_id (FK to ScorecardConfigVersion).
  - **ScorecardConfigVersion**: Version metadata for scorecard configuration snapshots. Fields: version_id, version_number, version_name, description, effective_date, published_by_user_id, published_at, is_active.
  - **ScorecardSectionSnapshot**: Point-in-time snapshot of sections at version publish. Fields: snapshot_id, version_id, original_section_id, code, name, description, sort_order, is_active.
  - **ScorecardCriterionSnapshot**: Point-in-time snapshot of criteria with weights at version publish. Fields: snapshot_id, version_id, original_criterion_id, section_code, code, name, description_prompt, comments_prompt, include_in_summary, allow_zero, weight, sort_order, is_active.
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
- **Configuration Versioning**:
  - Manual "Publish" action creates immutable version snapshot (similar to MonitoringPlanVersion)
  - Publishing deactivates previous active version and creates new version with section/criterion snapshots
  - Scorecards can reference config_version_id to preserve historical accuracy
  - Version history preserved for audit and compliance
  - `has_unpublished_changes` flag computed by comparing section/criterion `updated_at` timestamps against `published_at`
  - Publish button conditionally shown in UI only when unpublished changes exist
- **API Endpoints** (prefix: `/scorecard`):
  - Configuration: `GET /config` - Get current scorecard configuration (sections with nested criteria)
  - Ratings: `GET /validation/{request_id}`, `POST /validation/{request_id}`, `PATCH /validation/{request_id}/ratings/{criterion_code}`
  - Admin Section CRUD: `GET /sections`, `GET /sections/{id}`, `POST /sections`, `PATCH /sections/{id}`, `DELETE /sections/{id}`
  - Admin Criterion CRUD: `GET /criteria`, `GET /criteria/{id}`, `POST /criteria`, `PATCH /criteria/{id}`, `DELETE /criteria/{id}`
  - Versioning: `GET /versions` (list all), `GET /versions/active` (current with has_unpublished_changes), `GET /versions/{id}` (detail with snapshots), `POST /versions/publish` (Admin)
- **Frontend Components**:
  - `ValidationScorecardTab.tsx`: Full scorecard entry form with summary card, progress indicator, collapsible sections, auto-save on rating change
  - Integrated into ValidationRequestDetailPage as "Scorecard" tab (positioned after Plan, before Outcome)
  - TaxonomyPage "Scorecard Configuration" tab: Section/criterion CRUD with version management
    - "Unpublished Changes" indicator (yellow badge) when config modified since last publish
    - "Publish New Version" button conditionally shown when changes exist
    - Version list with active indicator and usage counts
- **Audit Logging**: CREATE and UPDATE actions logged with rating counts and overall score
- **Testing**: 56 unit tests covering rating conversions, score computations, section summaries, overall assessment, config loading, and edge cases

## Residual Risk Map
- **Purpose**: Compute Residual (Final) Risk from the combination of Inherent Risk Tier and Validation Scorecard Outcome using a configurable matrix.
- **Data Model**:
  - **ResidualRiskMapConfig**: Versioned configuration storing the risk matrix. Fields: config_id, version_number, version_name, matrix_config (JSON), description, is_active, created_by_user_id, created_at, updated_at.
  - **matrix_config structure**: `{ row_axis_label, column_axis_label, row_values, column_values, result_values, matrix: { "High": { "Red": "High", "Yellow-": "High", ... }, ... } }`
- **Default Matrix** (seeded from `RESIDUAL_RISK_MAP.json`):
  ```
                      Scorecard Outcome
               Red    Yellow- Yellow  Yellow+ Green-  Green
  High         High   High    High    Medium  Medium  Low
  Medium       High   High    Medium  Medium  Low     Low
  Low          High   Medium  Medium  Low     Low     Low
  Very Low     Medium Medium  Low     Low     Low     Low
  Inherent Risk
  ```
- **Result Values**: High, Medium, Low (color-coded as red, amber, green in UI)
- **Computed Properties** (on ValidationRequest):
  - `scorecard_overall_rating`: Derived from ValidationScorecardResult when available
  - `residual_risk`: Computed via matrix lookup using model's inherent risk tier + scorecard outcome
- **API Endpoints** (prefix: `/residual-risk-map`):
  - `GET /` - Get active configuration
  - `GET /versions` - List all versions
  - `GET /versions/{id}` - Get specific version
  - `PATCH /` - Update configuration (creates new version, sets as active)
  - `POST /calculate` - Calculate residual risk for given inputs
- **Frontend Components**:
  - **TaxonomyPage "Residual Risk Map" tab**: Matrix display with edit capability, version history
  - **ModelDetailsPage "Risk Assessment Summary"**: Shows Inherent Risk Tier, Scorecard Outcome, and computed Residual Risk (from latest approved validation)
  - **OverdueRevalidationReportPage**: Residual Risk column with color-coded badges, included in CSV export
- **API Client**: `web/src/api/residualRiskMap.ts` with helper functions for color styling

## Final Model Risk Ranking (Overdue Penalty)
- **Purpose**: Compute a penalty-adjusted risk rating that accounts for overdue validation status by downgrading the scorecard outcome before residual risk calculation.
- **Data Model**:
  - **downgrade_notches**: Column added to `TaxonomyValue` for bucket taxonomies (specifically "Past Due Level"). Stores number of notches (0-5) to downgrade scorecard when model is in that past-due bucket.
- **Computation Flow**:
  1. Get model's most recent validation with scorecard result
  2. Calculate days overdue based on validation policy and completion date
  3. Determine past-due bucket (CURRENT, MINIMAL, MODERATE, SIGNIFICANT, CRITICAL, OBSOLETE)
  4. Apply downgrade notches to original scorecard (e.g., Green- → Yellow+ with 1 notch)
  5. Feed adjusted scorecard + inherent risk tier into Residual Risk Map
  6. Return final rating with full penalty details
- **Scorecard Scale** (ordered from best to worst):
  - Green (6) → Green- (5) → Yellow+ (4) → Yellow (3) → Yellow- (2) → Red (1)
  - Downgrade capped at Red (cannot go below)
- **Default Downgrade Notches** (seeded):
  - CURRENT (≤0 days): 0 notches
  - MINIMAL (1-365 days): 1 notch
  - MODERATE (366-730 days): 2 notches
  - SIGNIFICANT (731-1095 days): 3 notches
  - CRITICAL (1096-1825 days): 3 notches
  - OBSOLETE (≥1826 days): 3 notches
- **API Endpoint**:
  - `GET /models/{model_id}/final-risk-ranking` - Returns computed final rating with:
    - original_scorecard, days_overdue, past_due_level, downgrade_notches
    - adjusted_scorecard, inherent_risk_tier, final_rating
    - residual_risk_without_penalty (for comparison)
- **Frontend**:
  - TaxonomyPage: "Downgrade" column for bucket taxonomies showing downgrade_notches value
  - ModelDetailsPage: Enhanced "Risk Assessment Summary" with:
    - Row 1: Inherent Risk Tier, Original Scorecard, Base Residual Risk
    - Row 2 (when penalty applied): Overdue Status, Adjusted Scorecard, Final Risk Rating
    - "Overdue Penalty Applied" badge in section header
- **Computation Module**: `api/app/core/final_rating.py` with functions:
  - `downgrade_scorecard()` - Apply N-notch penalty
  - `get_past_due_level_with_notches()` - Get bucket with downgrade config
  - `lookup_residual_risk()` - Matrix lookup
  - `calculate_model_days_overdue()` - Days overdue calculation
  - `compute_final_model_risk_ranking()` - Main orchestration function

## Model Approval Status
- **Purpose**: Compute and track the validation approval status of models, answering "Is this model currently approved for use based on its validation history?"
- **Status Codes**:
  - **NEVER_VALIDATED**: No validation request has ever been approved for this model
  - **APPROVED**: Most recent validation is APPROVED with all required approvals complete
  - **INTERIM_APPROVED**: Most recent completed validation was of INTERIM type
  - **VALIDATION_IN_PROGRESS**: Model is overdue but has active validation in substantive stage (PLANNING or later)
  - **EXPIRED**: Model is overdue with no active validation or validation still in INTAKE
- **Key Logic**:
  - Models remain APPROVED throughout the revalidation window
  - Status only changes to VALIDATION_IN_PROGRESS or EXPIRED after the model becomes OVERDUE
  - INTAKE status does NOT count as substantive validation work
  - Substantive stages: PLANNING, ASSIGNED, IN_PROGRESS, REVIEW, PENDING_APPROVAL
- **Data Model**:
  - **ModelApprovalStatusHistory**: Audit trail for status changes. Fields: history_id, model_id, old_status, new_status, changed_at, trigger_type, trigger_entity_type, trigger_entity_id, notes.
  - Trigger types: VALIDATION_REQUEST_CREATED, VALIDATION_STATUS_CHANGE, APPROVAL_SUBMITTED, EXPIRATION_CHECK, BACKFILL, MANUAL
- **Integration Hooks** (in validation_workflow.py):
  - create_validation_request: Triggers status recalculation on new request
  - update_validation_request_status: Triggers on status transitions (especially APPROVED)
  - submit_approval: Triggers when approvals are submitted
- **Computed Fields** (on ModelDetailResponse):
  - `approval_status`: Status code (NEVER_VALIDATED, APPROVED, INTERIM_APPROVED, VALIDATION_IN_PROGRESS, EXPIRED)
  - `approval_status_label`: Human-readable label
- **API Endpoints**:
  - `GET /models/{id}/approval-status` - Get detailed approval status with context
  - `GET /models/{id}/approval-status/history` - Get status change history
  - `POST /models/approval-status/bulk` - Bulk compute status for multiple models (useful for dashboards)
  - `POST /models/approval-status/backfill` - Admin-only: Create initial history records for all models without existing records
- **Core Module**: `app/core/model_approval_status.py` with functions:
  - `compute_model_approval_status()` - Main computation function
  - `record_status_change()` - Record changes to history
  - `update_model_approval_status_if_changed()` - Check and record if status changed
  - `backfill_model_approval_status()` - Create initial records for existing models
- **Testing**: 29 tests in `tests/test_model_approval_status.py` covering status computation, helper functions, history recording, integration hooks, backfill utilities, and API endpoints.

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
- **Direct Tier Edit Blocking**: When a global assessment exists for a model, direct edits to the model's risk_tier_id are blocked (400 error). Users must update the Risk Assessment tab to change the tier. Frontend disables the Risk Tier dropdown with explanatory message.
- **Open Validations Impact Check**: Before saving a risk assessment with a tier change, the frontend checks for open validation requests via `GET /validation-workflow/risk-tier-impact/check/{model_id}?proposed_tier_code=TIER_X`. If open validations exist, a warning modal shows affected requests and requires user confirmation before proceeding.
- **Validation Workflow Integration**:
  - **REVIEW/PENDING_APPROVAL Blocking**: Validation requests cannot transition to REVIEW or PENDING_APPROVAL status unless all models have a completed risk assessment (both quantitative and qualitative ratings). Returns 400 error with specific model details.
  - **Outdated Assessment Warning**: If the risk assessment was last updated before the most recent approved validation completion date, a 409 Conflict warning is returned. Users can acknowledge the warning and proceed with `skip_assessment_warning=true`.
- **API Endpoints**:
  - Factor Config (Admin): `GET/POST /risk-assessment/factors/`, `PUT/DELETE /risk-assessment/factors/{id}`, `PATCH /risk-assessment/factors/{id}/weight`, `POST /risk-assessment/factors/validate-weights`, `POST /risk-assessment/factors/reorder`
  - Guidance: `POST /risk-assessment/factors/{id}/guidance`, `PUT/DELETE /risk-assessment/factors/guidance/{id}`
  - Assessments: `GET/POST /models/{id}/risk-assessments/`, `GET/PUT/DELETE /models/{id}/risk-assessments/{assessment_id}`, `GET /models/{id}/risk-assessments/status` (check global assessment existence/completion)
- **Frontend**:
  - ModelDetailsPage "Risk Assessment" tab with assessment form and results display
  - TaxonomyPage "Risk Factors" tab for admin factor configuration with weighted guidance
- **Audit Logging**: All factor changes, guidance updates, and assessment modifications are logged.
- **Testing**: 54 tests in `tests/test_risk_assessment_audit.py` covering factor CRUD, guidance management, weight validation, assessment workflow, scoring logic, and override handling.

## Model Risk Attestations
- **Purpose**: Annual/quarterly compliance attestation process where model owners affirm adherence to Model Risk and Validation Policy.
- **Data Model**:
  - **AttestationCycle**: Represents an attestation period. Fields: cycle_id, cycle_name, period_start_date, period_end_date, submission_due_date, status (PENDING/OPEN/CLOSED), opened_at/by, closed_at/by, notes.
  - **AttestationRecord**: Individual attestation for a model owner within a cycle. Fields: attestation_id, cycle_id, model_id, attesting_user_id, due_date, status (PENDING/SUBMITTED/ACCEPTED/REJECTED), attested_at, decision, decision_comment, reviewed_by_user_id, reviewed_at, review_comment.
  - **AttestationResponse**: Answers to attestation questions. Fields: response_id, attestation_id, question_id (taxonomy value reference), answer (boolean), comment.
  - **AttestationEvidence**: Supporting documentation. Fields: evidence_id, attestation_id, evidence_type, url, description, added_by_user_id.
  - **AttestationQuestionConfig**: Extended configuration for taxonomy-based questions. Fields: config_id, question_value_id, frequency_scope (ANNUAL/QUARTERLY/BOTH), requires_comment_if_no.
  - **AttestationSchedulingRule**: Rules determining attestation frequency. Fields: rule_id, rule_name, rule_type (GLOBAL_DEFAULT/OWNER_THRESHOLD/MODEL_SPECIFIC/REGION_SPECIFIC), frequency (ANNUAL/QUARTERLY), priority, is_active, owner_model_count_min, owner_high_fluctuation_flag, model_id, region_id, effective_date.
  - **CoverageTarget**: Per-risk-tier attestation coverage requirements. Fields: target_id, risk_tier_id, target_percentage, is_blocking (prevents cycle closure if not met), effective_date.
  - **AttestationChangeLink**: Lightweight tracking table linking attestations to inventory changes made through existing workflows. Fields: link_id, attestation_id, change_type (MODEL_EDIT/NEW_MODEL/DECOMMISSION), model_id, pending_edit_id (link to ModelPendingEdit), decommissioning_request_id (link to DecommissioningRequest), created_at. No approval workflow - changes are approved through their existing workflows (ModelPendingEdit, DecommissioningRequest).
  - **User.high_fluctuation_flag**: Boolean flag triggering quarterly attestations.
  - **ModelDelegate.can_attest**: Boolean allowing delegates to submit attestations.
- **Attestation Questions** (10 policy-based questions seeded):
  1. Policy Compliance - Attest models comply with Model Risk and Validation Policy
  2. Model Awareness - Made Model Validation aware of all models subject to validation
  3. No Material Changes - No material changes since last validation
  4. Purpose Documentation - Documented purpose and modeling choices
  5. Performance Issues - Made aware of models with deteriorating performance
  6. Escalation Commitment - Will bring model risk issues to attention of stakeholders
  7. Roles and Responsibilities - Comply with Policy roles and responsibilities
  8. Policy Exceptions - Made aware of any exceptions to Policy
  9. Limitations Notification - Will notify users of critical model limitations
  10. Use Restrictions Implemented - Restrictions on model use have been implemented
- **Question Configuration**:
  - All questions apply to BOTH annual and quarterly frequencies
  - Questions with `requires_comment_if_no=true` mandate explanation when answered "No"
- **Scheduling Rules** (priority-based evaluation):
  - **Global Default** (priority 1): Annual attestation for all model owners
  - **Owner Threshold** (priority 100): Quarterly attestation for owners with 30+ models OR high_fluctuation_flag set
  - Higher priority rules override lower priority
  - **Date Windows**: Rules have effective_date (immutable) and optional end_date (when rule expires)
  - **Validation**: OWNER_THRESHOLD must have at least one criterion; only one active GLOBAL_DEFAULT allowed
  - **Immutable Fields**: rule_type, effective_date, model_id, region_id cannot be changed after creation
  - **Deactivation**: Rules are soft-deleted (marked inactive) rather than hard deleted for audit purposes
- **Coverage Targets** (seeded defaults):
  - Tier 1 (High Risk): 100%, blocking
  - Tier 2 (Medium Risk): 100%, blocking
  - Tier 3 (Low Risk): 95%, non-blocking
  - Tier 4 (Very Low Risk): 90%, non-blocking
- **Workflow**:
  1. Admin creates attestation cycle with period dates and due date
  2. Admin opens cycle → attestation records auto-generated for model owners
  3. Model owners answer all questions and submit
  4. Admin/Validator reviews submitted attestations (accept/reject)
  5. Rejected attestations returned to owner with comments
  6. Admin closes cycle when coverage targets met (blocking targets enforced)
- **API Endpoints** (prefix: `/attestations`):
  - Cycles: `GET /cycles`, `POST /cycles`, `GET /cycles/{id}`, `PATCH /cycles/{id}`, `POST /cycles/{id}/open`, `POST /cycles/{id}/close`
  - Records: `GET /records`, `GET /records/{id}`, `POST /records/{id}/submit`, `POST /records/{id}/accept`, `POST /records/{id}/reject`
  - Questions: `GET /questions` (with optional frequency filter)
  - Evidence: `POST /records/{id}/evidence`, `DELETE /evidence/{id}`
  - Change Links: `POST /records/{id}/link-change` (create link), `GET /records/{id}/linked-changes` (list links)
  - Rules: `GET /rules`, `POST /rules`, `PATCH /rules/{id}`, `DELETE /rules/{id}`
  - Targets: `GET /targets`, `PATCH /targets/{tier_id}`
  - User Dashboard: `GET /my-attestations`, `GET /my-upcoming`
  - Reports: `GET /reports/coverage`, `GET /reports/timeliness`
  - Stats: `GET /dashboard/stats`
- **Inventory Change Integration** (Lightweight Link Tracking):
  - During attestation, model owners navigate to existing forms via action buttons in AttestationDetailPage
  - **MODEL_EDIT**: User clicks "Edit Model" → navigates to `/models/{id}` → creates ModelPendingEdit → link tracked
  - **NEW_MODEL**: User clicks "Register New Model" → navigates to `/models/new` → creates model → link tracked
  - **DECOMMISSION**: User clicks "Decommission Model" → navigates to decommission page → creates DecommissioningRequest → link tracked
  - SessionStorage passes attestation context to existing forms for automatic link creation
  - All approvals happen through existing workflows (ModelPendingEdit approval, Decommissioning approval)
  - No duplicate approval workflow in attestation system - just tracking for audit purposes
- **Frontend**:
  - **AttestationCyclesPage** (Admin only): Manage cycles, scheduling rules (with date windows), coverage targets, review queue, high fluctuation owners, all records, and questions (7 tabs)
    - **All Records tab**: Comprehensive view of all attestation records grouped by model owner with collapsible detail sections, cycle filter, expand/collapse all controls, and summary statistics (Total Records, Owners, Pending, Submitted, Accepted, Overdue)
    - **Questions tab**: Edit attestation survey questions including text, description, frequency scope (Annual/Quarterly/Both), sort order, active status, and comment requirements
  - **MyAttestationsPage**: Model owner view of pending/submitted/accepted/rejected attestations with urgency badges
  - **AttestationDetailPage**: Question-by-question submission form, evidence management, inventory change navigation buttons (Edit Model, Register New Model, Decommission Model), linked changes display section, review panel for Admin/Validator
  - **AttestationReviewQueuePage** (Admin/Validator): Queue of submitted attestations awaiting review
- **Navigation**: "My Attestations" link for all users with pending count badge, "Attestation Cycles" in Admin section
- **UI Enhancements**: When submitting with "No" answers but no linked changes, prompt modal guides users to make inventory changes via the navigation buttons
- **Testing**: 32 tests in `tests/test_attestations.py` covering cycles, questions, evidence, submission, review, scheduling rules, dashboard stats, and linked changes.

## LOB (Line of Business) Hierarchy
- **Purpose**: Organizational hierarchy for assigning users to business units, enabling LOB-based filtering and reporting.
- **Data Model**:
  - **LOBUnit**: Self-referential hierarchical model for business units. Fields:
    - Core: lob_id, parent_id (FK to self), code, name, org_unit (5-char external ID, globally unique), level (auto-calculated), sort_order, is_active, full_path (computed), created_at, updated_at
    - Metadata (typically on leaf nodes): description, contact_name, org_description, legal_entity_id, legal_entity_name, short_name, status_code, tier
  - **User.lob_id**: Required FK to LOBUnit - all users must belong to an LOB unit.
- **org_unit Field**:
  - **Purpose**: External organizational identifier for integration with enterprise systems
  - **Format**: Exactly 5 characters
    - **Real org_units**: 5 digits (e.g., "85033", "90555") - from source CSV
    - **Synthetic org_units**: S + 4 digits (e.g., "S0001") - auto-generated for nodes without source IDs (e.g., SBU level)
  - **Globally unique**: Enforced via unique constraint and index
  - **Validation**: Schema validators enforce 5-char format (digits or S+4 digits)
- **Hierarchy Features**:
  - **Multi-level nesting**: Supports unlimited hierarchy depth (e.g., SBU → LOB1 → LOB2 → LOB3 → LOB4 → LOB5)
  - **Level calculation**: Automatically computed from parent chain (root=0, children=parent.level+1)
  - **Full path computation**: Property returns breadcrumb trail (e.g., "OMEGA CAPITAL MARKETS > INSTITUTIONAL BANKING > GLOBAL TRANSACTION SVCS")
  - **Active/inactive status**: Soft delete via is_active flag; inactive nodes hidden by default
  - **Sort order**: Controls display order within siblings
  - **Padding support**: When LOB levels repeat the same org_unit (ragged hierarchy), import correctly handles "padding" where hierarchy stops early
- **User LOB Requirement**:
  - **All users must have an LOB assignment** - lob_id is required (NOT NULL) in UserCreate schema
  - Enforced at registration (manual user creation) and Entra provisioning (SSO import)
  - Frontend validation prevents form submission without LOB selection
  - Existing users without LOB receive default assignment via seed migration
- **CSV Import/Export**:
  - **Enterprise Format**: Supports denormalized enterprise CSV with columns:
    - SBU (root level name), Lob1Code/Lob1Description, Lob2Code/Lob2Description, ..., Lob5Code/Lob5Description
    - OrgUnit (leaf node 5-digit ID), OrgUnitDescription, OrgUnitContactName, OrgUnitLegalEntityId, OrgUnitLegalEntityName, OrgUnitShortName, OrgUnitStatusCode, OrgUnitTier
  - **Column mapping**: Lob*Code columns contain org_unit values; Lob*Description contains descriptions
  - **Synthetic org_unit generation**: SBU level (no source org_unit) gets S#### prefix
  - **Deduplication**: Same parent nodes appearing on multiple rows are merged
  - **Dry run preview**: Preview mode shows to_create, to_update, to_skip counts with detected_columns and max_depth
  - **Export**: Downloads current hierarchy as CSV
- **API Endpoints** (prefix: `/lob-units`):
  - `GET /` - List all LOB units (flat, optional include_inactive)
  - `GET /tree` - Get LOB units as nested tree structure with metadata fields (optional include_inactive)
  - `GET /{id}` - Get single LOB unit with user_count and metadata
  - `POST /` - Create LOB unit (Admin)
  - `PATCH /{id}` - Update LOB unit (Admin)
  - `DELETE /{id}` - Soft delete (deactivate) LOB unit (Admin)
  - `GET /{id}/users` - List users assigned to LOB unit
  - `POST /import-csv` - Import hierarchy from CSV (dry_run parameter for preview)
  - `GET /export-csv` - Export hierarchy to CSV
- **Frontend**:
  - **TaxonomyPage "LOB Units" tab**: Full CRUD with tree view, expand/collapse all, import/export CSV, user count badges
  - **LOB Detail Panel**: Selecting a node in tree view shows detail panel with org_unit, full_path, level, and metadata (contact_name, legal_entity_name, legal_entity_id, tier, status_code, short_name)
  - **UsersPage**: Searchable LOB dropdown for user creation/editing, LOB column in user list
  - **Entra Import Modal**: LOB selection required before provisioning SSO users
- **Pre-seeded Data**: Default "Enterprise" hierarchy with 9 units across 3 levels (synthetic S#### org_units)
- **Testing**: Tests cover CRUD operations, tree retrieval, CSV import/export, parent resolution, user assignment, and org_unit validation.

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

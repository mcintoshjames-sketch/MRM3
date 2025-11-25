## Overview

Model Risk Management inventory system with a FastAPI backend, React/TypeScript frontend, and PostgreSQL database. Supports model cataloging, validation workflow, regional deployment tracking, configurable taxonomies, and compliance reporting. Primary user roles: Admin (full control), Validator (workflow execution), Model Owner/Contributor (submit and track models), Regional/Global approvers (deployment approvals).

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
  - `audit_logs.py`: audit log search/filter.
  - `dashboard.py`: aging and workload summaries.
  - `export_views.py`: CSV/export-friendly endpoints.
  - `regional_compliance_report.py`: region-wise deployment & approval report.
  - `analytics.py`, `saved_queries.py`: analytics aggregations and saved-query storage.
- Core services:
  - DB session management (`core/database.py`), auth dependency (`core/deps.py`), security utilities (`core/security.py`), row-level security filters (`core/rls.py`).
  - PDF/report helpers in `validation_workflow.py` (FPDF) for generated artifacts.
- Models (`app/models/`):
  - Users & directory: `user.py`, `entra_user.py`, roles include Admin/Validator/Global Approver/Regional Approver/User.
  - Catalog: `model.py`, `vendor.py`, `taxonomy.py`, `region.py`, `model_version.py`, `model_region.py`, `model_delegate.py`, `model_change_taxonomy.py`, `model_version_region.py`, `model_type.py` (ModelType, ModelTypeCategory).
  - Model relationships: `model_hierarchy.py` (parent-child links with effective/end dates), `model_feed_dependency.py` (feeder-consumer data flows with active status tracking), `model_dependency_metadata.py` (extended metadata for dependencies, not yet exposed in UI).
  - Validation workflow: `validation.py` (ValidationRequest, ValidationStatusHistory, ValidationAssignment, ValidationOutcome, ValidationApproval, ValidationReviewOutcome, ValidationPlan, ValidationPlanComponent, ValidationComponentDefinition, ComponentDefinitionConfiguration/ConfigItem, ValidationPolicy, ValidationWorkflowSLA).
  - Overdue commentary: `overdue_revalidation_comment.py` (OverdueRevalidationComment - tracks explanations for overdue submissions/validations with supersession chain).
- Additional approvals: `conditional_approval.py` (ApproverRole, ConditionalApprovalRule, RuleRequiredApprover).
  - MAP Applications: `map_application.py` (mock application inventory), `model_application.py` (model-application links with relationship types).
  - Compliance/analytics: `audit_log.py`, `export_view.py`, `saved_query.py`, `version_deployment_task.py`, `validation_grouping.py`.
- Schemas: mirrored Pydantic models in `app/schemas/` for requests/responses.
- Authn/z: HTTP Bearer JWT tokens; `get_current_user` dependency enforces auth; role checks per endpoint; RLS utilities narrow visibility for non-privileged users.
- Audit logging: `AuditLog` persisted on key workflows (model changes, approvals, component config publishes, etc.).
- Reporting: Dedicated routers plus endpoints in `validation_workflow.py` for dashboard metrics and compliance reports (aging, workload, deviation trends).

## Frontend Architecture
- Entry: `src/main.tsx` mounts App within `AuthProvider` and `BrowserRouter`.
- Routing (`src/App.tsx`): guarded routes for login, dashboards (`/dashboard`, `/validator-dashboard`, `/my-dashboard`), models (list/detail/change records), validation workflow (list/detail/new), vendors (list/detail), users (list/detail), taxonomy, audit logs, workflow configuration, batch delegates, regions, validation policies, component definitions, configuration history, approver roles, additional approval rules, reports hub (`/reports`), report detail pages (regional compliance, deviation trends), analytics, deployment tasks, pending submissions.
- Shared pieces:
  - Auth context (`src/contexts/AuthContext.tsx`) manages token/user; Axios client (`src/api/client.ts`) injects Bearer tokens and redirects on 401.
  - Layout (`src/components/Layout.tsx`) provides navigation shell.
  - Hooks/utilities: table sorting (`src/hooks/useTableSort.tsx`), CSV export helpers on pages.
- Pages (`src/pages/`): feature-specific UIs aligned to backend modules (e.g., `ModelsPage.tsx`, `ValidationWorkflowPage.tsx`, `ValidationRequestDetailPage.tsx`, `VendorsPage.tsx`, `TaxonomyPage.tsx`, `AuditPage.tsx`, `WorkflowConfigurationPage.tsx`, `ApproverRolesPage.tsx`, `ConditionalApprovalRulesPage.tsx`, `RegionalComplianceReportPage.tsx`, `DeviationTrendsReportPage.tsx`, `OverdueRevalidationReportPage.tsx`, `AnalyticsPage.tsx`, dashboards). Tables generally support sorting and CSV export; dates rendered via ISO splitting.
- Styling: Tailwind classes via `index.css` and Vite config; iconography via emojis/SVG inline.

## Data Model (conceptual)
- User & EntraUser directory entries; roles drive permissions.
- Model with vendor, owner/developer, taxonomy links (risk tier, validation type, etc.), regulatory categories, delegates, and region assignments via ModelRegion.
- **Model Types**: Hierarchical classification with Categories (e.g., "Financial", "Operational") and Types (e.g., "Credit Risk", "Fraud Detection").
- **Model Relationships** (Admin-managed with full audit logging):
  - **ModelHierarchy**: Parent-child relationships (e.g., sub-models) with relation type taxonomy, effective/end dates, and notes. Prevents self-reference via database constraints.
  - **ModelFeedDependency**: Feeder-consumer data flow relationships with dependency type taxonomy, description, effective/end dates, and is_active flag. **Cycle detection enforced**: DFS algorithm prevents creation of circular dependencies to maintain DAG (Directed Acyclic Graph) constraint. Includes detailed error reporting with cycle path and model names.
  - **ModelDependencyMetadata**: 1:1 extended metadata for dependencies (feed frequency, interface type, criticality, data fields summary) for future governance tracking, not yet exposed in UI.
- ModelVersion tracks version metadata, change types, production dates, scope (global/regional) and links to ValidationRequest.
- ValidationRequest lifecycle with status history, assignments (validators), plan (components and deviations), approvals (traditional + conditional), outcomes/review outcomes, deployment tasks, and policies/SLA settings per risk tier.
- **Conditional Model Use Approvals**: ApproverRole (committees/roles), ConditionalApprovalRule (configurable rules based on validation type, risk tier, governance region, deployed regions), RuleRequiredApprover (many-to-many link). ValidationApproval extended with approver_role_id, approval_evidence, voiding fields. Model extended with use_approval_date timestamp.
- Taxonomy/TaxonomyValue for configurable lists (risk tier, validation types, statuses, priorities, **Model Hierarchy Type, Model Dependency Type, Application Relationship Type**, etc.).
- MapApplication (mock MAP inventory) and ModelApplication (model-application links with relationship type, effective/end dates for soft delete).
- Region and VersionDeploymentTask for regional deployment approvals.
- AuditLog captures actions across entities including relationship changes and conditional approval actions.
- SavedQuery/ExportView for analytics/reporting reuse.

## Request & Data Flow
1. Frontend calls Axios client -> FastAPI routes under `/auth`, `/models`, `/validation-workflow`, `/vendors`, `/taxonomies`, `/model-types`, `/audit-logs`, `/regions`, `/model-versions`, `/model-change-taxonomy`, `/analytics`, `/saved-queries`, `/regional-compliance-report`, `/validation-workflow/compliance-report/*`, `/models/{id}/hierarchy/*`, `/models/{id}/dependencies/*`, etc.
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

# Role-Based Authorization Analysis

*Generated on: 2025-12-31 18:13:56*

## Executive Summary

- **Total API Endpoints Analyzed**: 522
- **Total Features/Modules**: 47
- **Canonical Roles**: 5
- **Authorization Patterns Detected**: 6

## Canonical Roles

| Role Code | Display Name | Description |
|-----------|--------------|-------------|
| `ADMIN` | Admin | Full system access, configuration management, user administration |
| `GLOBAL_APPROVER` | Global Approver | Approve model deployments and validations globally |
| `REGIONAL_APPROVER` | Regional Approver | Approve model deployments within assigned regions |
| `USER` | User | Basic model owner/contributor access, view and submit models |
| `VALIDATOR` | Validator | Execute validation workflows, review models, assign tasks |

## Role Capabilities Matrix

| Feature | ADMIN | GLOBAL_APPROVER | REGIONAL_APPROVER | USER | VALIDATOR |
|---------|-----|-----|-----|-----|-----|
| Analytics | — | — | — | — | — |
| Approver Roles & Conditional Approvals | ✅ (3) | — | — | — | — |
| Attestations | ✅ (7) | — | — | — | — |
| Audit Logging | — | — | — | — | — |
| Authentication & User Management | ✅ (1) | — | ✅ (1) | — | — |
| Conditional Approval Rules | ✅ (4) | — | — | — | — |
| Dashboard | — | — | — | — | — |
| Exceptions | ✅ (5) | — | — | — | — |
| Export Views | — | — | — | — | — |
| Fry | ✅ (1) | — | — | — | — |
| Irp | ✅ (5) | — | — | — | — |
| KPM Library | — | — | — | — | — |
| Kpi Report | — | — | — | — | — |
| Limitations | — | — | — | — | — |
| Lob Units | ✅ (4) | — | — | — | — |
| MAP Applications | — | — | — | — | — |
| MRSA Review Policies | ✅ (5) | — | — | — | — |
| Methodology | — | — | — | — | — |
| Model Applications | ✅ (3) | — | — | — | — |
| Model Change Taxonomy | — | — | — | — | — |
| Model Decommissioning | ✅ (6) | — | — | — | — |
| Model Delegates | ✅ (2) | — | — | — | — |
| Model Dependencies | ✅ (3) | — | — | — | — |
| Model Hierarchy | ✅ (3) | — | — | — | — |
| Model Inventory | ✅ (9) | — | — | — | — |
| Model Regions | ✅ (1) | — | — | — | — |
| Model Types | — | — | — | — | — |
| Model Versions | ✅ (2) | — | — | — | — |
| My Portfolio | — | — | — | — | — |
| Overdue Commentary | — | — | — | — | — |
| Overdue Revalidation Report | ✅ (1) | — | — | — | — |
| Performance Monitoring | ✅ (11) | — | — | — | — |
| Qualitative Factors | — | — | — | — | — |
| Recommendations | ✅ (23) | — | — | — | — |
| Regional Management | ✅ (3) | — | — | — | — |
| Residual Risk Map | — | — | — | — | — |
| Risk Assessment | — | — | — | — | — |
| Roles | — | — | — | — | — |
| Saved Queries | — | — | — | — | — |
| Scorecard | — | — | — | — | — |
| Taxonomy Management | ✅ (4) | — | — | — | — |
| Uat Tools | ✅ (1) | — | — | ✅ (1) | ✅ (1) |
| Validation Policies | — | — | — | — | — |
| Validation Workflow | ✅ (40) | — | — | — | — |
| Vendor Management | — | — | — | — | — |
| Version Deployment Tasks | ✅ (2) | — | — | — | — |
| Workflow Sla | ✅ (1) | — | — | — | — |

## Detailed Role Privileges

### Admin (`ADMIN`)

**Accessible Endpoints**: 150

**Exclusive Capabilities** (148 endpoints):
- `DELETE /approvals/{approval_id}/unlink`
- `DELETE /assignments/{assignment_id}`
- `DELETE /delegates/{delegate_id}`
- `DELETE /dependencies/{dependency_id}`
- `DELETE /evidence/{evidence_id}`
- `DELETE /hierarchy/{hierarchy_id}`
- `DELETE /model-regions/{id}`
- `DELETE /mrsa-review-policies/{policy_id}`
- `DELETE /priority-config/regional-overrides/{override_id}`
- `DELETE /requests/{request_id}`
- *(+138 more)*

**Feature Access**:

#### Approver Roles & Conditional Approvals

- `DELETE /{role_id}`
- `PATCH /{role_id}`
- `POST /`

#### Attestations

- `DELETE /evidence/{evidence_id}`
- `GET /admin/linked-changes`
- `GET /records`
- `GET /records/{attestation_id}`
- `GET /records/{attestation_id}/linked-changes`
- *(+2 more endpoints)*

#### Authentication & User Management

- `POST /entra/provision`

#### Conditional Approval Rules

- `DELETE /{rule_id}`
- `PATCH /{rule_id}`
- `POST /`
- `POST /preview`

#### Exceptions

- `POST /`
- `POST /detect-all`
- `POST /detect/{model_id}`
- `POST /{exception_id}/acknowledge`
- `POST /{exception_id}/close`

#### Fry

- `POST /reports`

#### Irp

- `DELETE /{irp_id:int}`
- `PATCH /{irp_id:int}`
- `POST /`
- `POST /{irp_id:int}/certifications`
- `POST /{irp_id:int}/reviews`

#### Lob Units

- `DELETE /{lob_id}`
- `GET /export-csv`
- `PATCH /{lob_id}`
- `POST /`

#### MRSA Review Policies

- `DELETE /mrsa-review-policies/{policy_id}`
- `PATCH /mrsa-review-exceptions/{exception_id}`
- `PATCH /mrsa-review-policies/{policy_id}`
- `POST /mrsa-review-exceptions/`
- `POST /mrsa-review-policies/`

#### Model Applications

- `DELETE /{application_id}`
- `PATCH /{application_id}`
- `POST `

#### Model Decommissioning

- `GET /my-pending-approvals`
- `GET /pending-validator-review`
- `PATCH /{request_id}`
- `POST /{request_id}/approvals/{approval_id}`
- `POST /{request_id}/validator-review`
- *(+1 more endpoints)*

#### Model Delegates

- `DELETE /delegates/{delegate_id}`
- `POST /delegates/batch`

#### Model Dependencies

- `DELETE /dependencies/{dependency_id}`
- `PATCH /dependencies/{dependency_id}`
- `POST /models/{model_id}/dependencies`

#### Model Hierarchy

- `DELETE /hierarchy/{hierarchy_id}`
- `PATCH /hierarchy/{hierarchy_id}`
- `POST /models/{model_id}/hierarchy`

#### Model Inventory

- `GET /pending-edits/all`
- `GET /pending-submissions`
- `PATCH /{model_id}`
- `POST /`
- `POST /approval-status/backfill`
- *(+4 more endpoints)*

#### Model Regions

- `DELETE /model-regions/{id}`

#### Model Versions

- `PATCH /versions/{version_id}`
- `PATCH /versions/{version_id}/approve`

#### Overdue Revalidation Report

- `GET /`

#### Performance Monitoring

- `GET /monitoring/admin-overview`
- `GET /monitoring/approvals/my-pending`
- `GET /monitoring/cycles/{cycle_id}/report/pdf`
- `GET /monitoring/plans/{plan_id}`
- `POST /monitoring/cycles/{cycle_id}/approvals/{approval_id}/approve`
- *(+6 more endpoints)*

#### Recommendations

- `DELETE /priority-config/regional-overrides/{override_id}`
- `GET /my-tasks`
- `PATCH /priority-config/regional-overrides/{override_id}`
- `PATCH /priority-config/{priority_id}`
- `PATCH /timeframe-config/{config_id}`
- *(+18 more endpoints)*

#### Regional Management

- `DELETE /{region_id}`
- `POST /`
- `PUT /{region_id}`

#### Taxonomy Management

- `DELETE /values/{value_id}`
- `PATCH /values/{value_id}`
- `PATCH /{taxonomy_id}`
- `POST /{taxonomy_id}/values`

#### Uat Tools

- `POST /seed-uat-data`

#### Validation Workflow

- `DELETE /approvals/{approval_id}/unlink`
- `DELETE /assignments/{assignment_id}`
- `DELETE /requests/{request_id}`
- `DELETE /requests/{request_id}/plan`
- `GET /assignments/`
- *(+35 more endpoints)*

#### Version Deployment Tasks

- `GET /my-tasks`
- `GET /ready-to-deploy`

#### Workflow Sla

- `PATCH /validation`


### Global Approver (`GLOBAL_APPROVER`)

**Accessible Endpoints**: 0

**Feature Access**:


### Regional Approver (`REGIONAL_APPROVER`)

**Accessible Endpoints**: 1

**Feature Access**:

#### Authentication & User Management

- `POST /entra/provision`


### User (`USER`)

**Accessible Endpoints**: 1

**Feature Access**:

#### Uat Tools

- `POST /seed-uat-data`


### Validator (`VALIDATOR`)

**Accessible Endpoints**: 1

**Feature Access**:

#### Uat Tools

- `POST /seed-uat-data`


### All Authenticated Users (`ALL_AUTHENTICATED`)

**Accessible Endpoints**: 369

**Notes**:
- Applies to any logged-in user, may be filtered by RLS

**Feature Access**:

#### Analytics

- `POST /query`

#### Approver Roles & Conditional Approvals

- `GET /`
- `GET /{role_id}`

#### Attestations

- `DELETE /bulk/{cycle_id}/draft`
- `DELETE /rules/{rule_id}`
- `GET /bulk/{cycle_id}`
- `GET /cycles`
- `GET /cycles/reminder`
- *(+23 more endpoints)*

#### Audit Logging

- `GET /`
- `GET /actions`
- `GET /entities`
- `GET /entity-types`

#### Authentication & User Management

- `DELETE /users/{user_id}`
- `GET /entra/users`
- `GET /me`
- `GET /users`
- `GET /users/export/csv`
- *(+5 more endpoints)*

#### Conditional Approval Rules

- `GET /`
- `GET /{rule_id}`

#### Dashboard

- `GET /mrsa-reviews/overdue (RLS filtered)`
- `GET /mrsa-reviews/summary (RLS filtered)`
- `GET /mrsa-reviews/upcoming (RLS filtered)`
- `GET /news-feed (RLS filtered)`

#### Exceptions

- `GET / (RLS filtered)`
- `GET /closure-reasons`
- `GET /model/{model_id}`
- `GET /summary (RLS filtered)`
- `GET /{exception_id}`

#### Export Views

- `DELETE /{view_id}`
- `GET /`
- `GET /{view_id}`
- `PATCH /{view_id}`
- `POST /`

#### Fry

- `DELETE /line-items/{line_item_id}`
- `DELETE /metric-groups/{metric_group_id}`
- `DELETE /reports/{report_id}`
- `DELETE /schedules/{schedule_id}`
- `GET /line-items/{line_item_id}`
- *(+14 more endpoints)*

#### Irp

- `GET /`
- `GET /coverage/check (RLS filtered)`
- `GET /mrsa-review-status (RLS filtered)`
- `GET /{irp_id:int}`
- `GET /{irp_id:int}/certifications`
- *(+1 more endpoints)*

#### KPM Library

- `DELETE /kpm/categories/{category_id}`
- `DELETE /kpm/kpms/{kpm_id}`
- `GET /kpm/categories`
- `GET /kpm/kpms`
- `GET /kpm/kpms/{kpm_id}`
- *(+4 more endpoints)*

#### Kpi Report

- `GET /`

#### Limitations

- `GET /limitations/{limitation_id}`
- `GET /models/{model_id}/limitations`
- `GET /reports/critical-limitations`
- `GET /validation-requests/{request_id}/limitations`
- `PATCH /limitations/{limitation_id}`
- *(+2 more endpoints)*

#### Lob Units

- `GET /`
- `GET /tree`
- `GET /{lob_id}`
- `GET /{lob_id}/users`

#### MAP Applications

- `GET /applications`
- `GET /applications/{application_id}`
- `GET /departments`

#### MRSA Review Policies

- `GET /mrsa-review-exceptions/`
- `GET /mrsa-review-exceptions/{mrsa_id}`
- `GET /mrsa-review-policies/`
- `GET /mrsa-review-policies/{policy_id}`

#### Methodology

- `DELETE /methodology-library/categories/{category_id}`
- `DELETE /methodology-library/methodologies/{methodology_id}`
- `GET /methodology-library/categories`
- `GET /methodology-library/methodologies`
- `GET /methodology-library/methodologies/{methodology_id}`
- *(+4 more endpoints)*

#### Model Applications

- `GET `

#### Model Change Taxonomy

- `DELETE /change-taxonomy/categories/{category_id}`
- `DELETE /change-taxonomy/types/{change_type_id}`
- `GET /change-taxonomy/categories`
- `GET /change-taxonomy/types`
- `GET /change-taxonomy/types/{change_type_id}`
- *(+4 more endpoints)*

#### Model Decommissioning

- `GET /`
- `GET /models/{model_id}/implementation-date`
- `GET /my-pending-owner-reviews`
- `GET /{request_id}`
- `POST /`
- *(+1 more endpoints)*

#### Model Delegates

- `GET /models/{model_id}/delegates`
- `PATCH /delegates/{delegate_id}`
- `PATCH /delegates/{delegate_id}/revoke`
- `POST /models/{model_id}/delegates`

#### Model Dependencies

- `GET /models/{model_id}/dependencies/inbound`
- `GET /models/{model_id}/dependencies/lineage`
- `GET /models/{model_id}/dependencies/lineage/pdf`
- `GET /models/{model_id}/dependencies/outbound`

#### Model Hierarchy

- `GET /models/{model_id}/hierarchy/children`
- `GET /models/{model_id}/hierarchy/descendants`
- `GET /models/{model_id}/hierarchy/parents`

#### Model Inventory

- `DELETE /{model_id}`
- `GET / (RLS filtered)`
- `GET /export/csv (RLS filtered)`
- `GET /my-submissions`
- `GET /name-changes/stats`
- *(+16 more endpoints)*

#### Model Regions

- `GET /models/{model_id}/regions`
- `POST /models/{model_id}/regions`
- `PUT /model-regions/{id}`

#### Model Types

- `DELETE /model-types/categories/{category_id}`
- `DELETE /model-types/types/{type_id}`
- `GET /model-types/categories`
- `GET /model-types/types`
- `GET /model-types/types/{type_id}`
- *(+4 more endpoints)*

#### Model Versions

- `DELETE /versions/{version_id}`
- `GET /models/{model_id}/regional-versions`
- `GET /models/{model_id}/versions`
- `GET /models/{model_id}/versions/current`
- `GET /models/{model_id}/versions/export/csv`
- *(+8 more endpoints)*

#### My Portfolio

- `GET /reports/my-portfolio`
- `GET /reports/my-portfolio/pdf`

#### Overdue Commentary

- `GET /requests/{request_id}/overdue-commentary`
- `GET /requests/{request_id}/overdue-commentary/history`
- `GET /{model_id}/overdue-commentary`
- `POST /requests/{request_id}/overdue-commentary`

#### Overdue Revalidation Report

- `GET /regions`

#### Performance Monitoring

- `DELETE /monitoring/cycles/{cycle_id}`
- `DELETE /monitoring/plans/{plan_id}`
- `DELETE /monitoring/plans/{plan_id}/metrics/{metric_id}`
- `DELETE /monitoring/results/{result_id}`
- `DELETE /monitoring/teams/{team_id}`
- *(+33 more endpoints)*

#### Qualitative Factors

- `DELETE /guidance/{guidance_id}`
- `DELETE /{factor_id}`
- `GET /`
- `GET /{factor_id}`
- `PATCH /{factor_id}/weight`
- *(+6 more endpoints)*

#### Recommendations

- `GET /`
- `GET /dashboard/by-model/{model_id}`
- `GET /dashboard/open`
- `GET /dashboard/overdue`
- `GET /priority-config/`
- *(+10 more endpoints)*

#### Regional Management

- `GET /`
- `GET /{region_id}`

#### Residual Risk Map

- `GET /`
- `GET /versions`
- `GET /versions/{version_id}`
- `PATCH /`
- `POST /`
- *(+1 more endpoints)*

#### Risk Assessment

- `DELETE /models/{model_id}/risk-assessments/{assessment_id}`
- `GET /models/{model_id}/risk-assessments/`
- `GET /models/{model_id}/risk-assessments/history`
- `GET /models/{model_id}/risk-assessments/status`
- `GET /models/{model_id}/risk-assessments/{assessment_id}`
- *(+2 more endpoints)*

#### Roles

- `GET /roles`

#### Saved Queries

- `DELETE /{query_id}`
- `GET /`
- `GET /{query_id}`
- `PATCH /{query_id}`
- `POST /`

#### Scorecard

- `DELETE /criteria/{criterion_id}`
- `DELETE /sections/{section_id}`
- `GET /config`
- `GET /criteria`
- `GET /criteria/{criterion_id}`
- *(+15 more endpoints)*

#### Taxonomy Management

- `DELETE /{taxonomy_id}`
- `GET /`
- `GET /by-names/`
- `GET /export/csv`
- `GET /{taxonomy_id}`
- *(+1 more endpoints)*

#### Uat Tools

- `DELETE /backups/{backup_id}`
- `DELETE /reset-transactional-data`
- `GET /backups`
- `GET /data-summary`
- `POST /backup`
- *(+1 more endpoints)*

#### Validation Policies

- `DELETE /{policy_id}`
- `GET /`
- `PATCH /{policy_id}`
- `POST /`

#### Validation Workflow

- `GET /compliance-report/deviation-trends`
- `GET /component-definitions`
- `GET /component-definitions/{component_id}`
- `GET /configurations`
- `GET /configurations/{config_id}`
- *(+23 more endpoints)*

#### Vendor Management

- `DELETE /{vendor_id}`
- `GET /`
- `GET /export/csv`
- `GET /{vendor_id}`
- `GET /{vendor_id}/models`
- *(+2 more endpoints)*

#### Version Deployment Tasks

- `GET /version/{version_id}/deploy-modal`
- `GET /{task_id}`
- `PATCH /{task_id}/adjust`
- `PATCH /{task_id}/cancel`
- `PATCH /{task_id}/confirm`
- *(+4 more endpoints)*

#### Workflow Sla

- `GET /validation`


## Feature-Centric View

### Analytics

**Total Endpoints**: 1

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 1 endpoint(s)

**Sample Endpoints**:
- `POST /query` — Any authenticated


### Approver Roles & Conditional Approvals

**Total Endpoints**: 5

**Role Access Summary**:
- **ADMIN**: 3 endpoint(s)
- **ALL_AUTHENTICATED**: 2 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — ADMIN
- `GET /{role_id}` — Any authenticated
- `PATCH /{role_id}` — ADMIN
- `DELETE /{role_id}` — ADMIN


### Attestations

**Total Endpoints**: 35

**Role Access Summary**:
- **ADMIN**: 7 endpoint(s)
- **ALL_AUTHENTICATED**: 28 endpoint(s)

**Sample Endpoints**:
- `GET /admin/linked-changes` — ADMIN
- `GET /bulk/{cycle_id}` — Any authenticated
- `POST /bulk/{cycle_id}/draft` — Any authenticated
- `DELETE /bulk/{cycle_id}/draft` — Any authenticated
- `POST /bulk/{cycle_id}/submit` — Any authenticated


### Audit Logging

**Total Endpoints**: 4

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 4 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `GET /actions` — Any authenticated
- `GET /entities` — Any authenticated
- `GET /entity-types` — Any authenticated


### Authentication & User Management

**Total Endpoints**: 11

**Role Access Summary**:
- **ADMIN**: 1 endpoint(s)
- **ALL_AUTHENTICATED**: 10 endpoint(s)
- **REGIONAL_APPROVER**: 1 endpoint(s)

**Sample Endpoints**:
- `POST /entra/provision` — ADMIN, REGIONAL_APPROVER
- `GET /entra/users` — Any authenticated
- `POST /login` — Any authenticated
- `GET /me` — Any authenticated
- `POST /register` — Any authenticated


### Conditional Approval Rules

**Total Endpoints**: 6

**Role Access Summary**:
- **ADMIN**: 4 endpoint(s)
- **ALL_AUTHENTICATED**: 2 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — ADMIN
- `POST /preview` — ADMIN
- `GET /{rule_id}` — Any authenticated
- `PATCH /{rule_id}` — ADMIN


### Dashboard

**Total Endpoints**: 4

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 4 endpoint(s)

**Sample Endpoints**:
- `GET /mrsa-reviews/overdue` — Any authenticated [RLS]
- `GET /mrsa-reviews/summary` — Any authenticated [RLS]
- `GET /mrsa-reviews/upcoming` — Any authenticated [RLS]
- `GET /news-feed` — Any authenticated [RLS]


### Exceptions

**Total Endpoints**: 10

**Role Access Summary**:
- **ADMIN**: 5 endpoint(s)
- **ALL_AUTHENTICATED**: 5 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated [RLS]
- `POST /` — ADMIN
- `GET /closure-reasons` — Any authenticated
- `POST /detect-all` — ADMIN
- `POST /detect/{model_id}` — ADMIN


### Export Views

**Total Endpoints**: 5

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 5 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — Any authenticated
- `GET /{view_id}` — Any authenticated
- `PATCH /{view_id}` — Any authenticated
- `DELETE /{view_id}` — Any authenticated


### Fry

**Total Endpoints**: 20

**Role Access Summary**:
- **ADMIN**: 1 endpoint(s)
- **ALL_AUTHENTICATED**: 19 endpoint(s)

**Sample Endpoints**:
- `GET /line-items/{line_item_id}` — Any authenticated
- `PATCH /line-items/{line_item_id}` — Any authenticated
- `DELETE /line-items/{line_item_id}` — Any authenticated
- `GET /metric-groups/{metric_group_id}` — Any authenticated
- `PATCH /metric-groups/{metric_group_id}` — Any authenticated


### Irp

**Total Endpoints**: 11

**Role Access Summary**:
- **ADMIN**: 5 endpoint(s)
- **ALL_AUTHENTICATED**: 6 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — ADMIN
- `GET /coverage/check` — Any authenticated [RLS]
- `GET /mrsa-review-status` — Any authenticated [RLS]
- `GET /{irp_id:int}` — Any authenticated


### KPM Library

**Total Endpoints**: 9

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 9 endpoint(s)

**Sample Endpoints**:
- `GET /kpm/categories` — Any authenticated
- `POST /kpm/categories` — Any authenticated
- `PATCH /kpm/categories/{category_id}` — Any authenticated
- `DELETE /kpm/categories/{category_id}` — Any authenticated
- `GET /kpm/kpms` — Any authenticated


### Kpi Report

**Total Endpoints**: 1

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 1 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated


### Limitations

**Total Endpoints**: 7

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 7 endpoint(s)

**Sample Endpoints**:
- `GET /limitations/{limitation_id}` — Any authenticated
- `PATCH /limitations/{limitation_id}` — Any authenticated
- `POST /limitations/{limitation_id}/retire` — Any authenticated
- `GET /models/{model_id}/limitations` — Any authenticated
- `POST /models/{model_id}/limitations` — Any authenticated


### Lob Units

**Total Endpoints**: 8

**Role Access Summary**:
- **ADMIN**: 4 endpoint(s)
- **ALL_AUTHENTICATED**: 4 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — ADMIN
- `GET /export-csv` — ADMIN
- `GET /tree` — Any authenticated
- `GET /{lob_id}` — Any authenticated


### MAP Applications

**Total Endpoints**: 3

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 3 endpoint(s)

**Sample Endpoints**:
- `GET /applications` — Any authenticated
- `GET /applications/{application_id}` — Any authenticated
- `GET /departments` — Any authenticated


### MRSA Review Policies

**Total Endpoints**: 9

**Role Access Summary**:
- **ADMIN**: 5 endpoint(s)
- **ALL_AUTHENTICATED**: 4 endpoint(s)

**Sample Endpoints**:
- `GET /mrsa-review-exceptions/` — Any authenticated
- `POST /mrsa-review-exceptions/` — ADMIN
- `PATCH /mrsa-review-exceptions/{exception_id}` — ADMIN
- `GET /mrsa-review-exceptions/{mrsa_id}` — Any authenticated
- `GET /mrsa-review-policies/` — Any authenticated


### Methodology

**Total Endpoints**: 9

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 9 endpoint(s)

**Sample Endpoints**:
- `GET /methodology-library/categories` — Any authenticated
- `POST /methodology-library/categories` — Any authenticated
- `PATCH /methodology-library/categories/{category_id}` — Any authenticated
- `DELETE /methodology-library/categories/{category_id}` — Any authenticated
- `GET /methodology-library/methodologies` — Any authenticated


### Model Applications

**Total Endpoints**: 4

**Role Access Summary**:
- **ADMIN**: 3 endpoint(s)
- **ALL_AUTHENTICATED**: 1 endpoint(s)

**Sample Endpoints**:
- `GET ` — Any authenticated
- `POST ` — ADMIN
- `PATCH /{application_id}` — ADMIN
- `DELETE /{application_id}` — ADMIN


### Model Change Taxonomy

**Total Endpoints**: 9

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 9 endpoint(s)

**Sample Endpoints**:
- `GET /change-taxonomy/categories` — Any authenticated
- `POST /change-taxonomy/categories` — Any authenticated
- `PATCH /change-taxonomy/categories/{category_id}` — Any authenticated
- `DELETE /change-taxonomy/categories/{category_id}` — Any authenticated
- `GET /change-taxonomy/types` — Any authenticated


### Model Decommissioning

**Total Endpoints**: 12

**Role Access Summary**:
- **ADMIN**: 6 endpoint(s)
- **ALL_AUTHENTICATED**: 6 endpoint(s)

**Sample Endpoints**:
- `POST /` — Any authenticated
- `GET /` — Any authenticated
- `GET /models/{model_id}/implementation-date` — Any authenticated
- `GET /my-pending-approvals` — ADMIN
- `GET /my-pending-owner-reviews` — Any authenticated


### Model Delegates

**Total Endpoints**: 6

**Role Access Summary**:
- **ADMIN**: 2 endpoint(s)
- **ALL_AUTHENTICATED**: 4 endpoint(s)

**Sample Endpoints**:
- `POST /delegates/batch` — ADMIN
- `PATCH /delegates/{delegate_id}` — Any authenticated
- `DELETE /delegates/{delegate_id}` — ADMIN
- `PATCH /delegates/{delegate_id}/revoke` — Any authenticated
- `POST /models/{model_id}/delegates` — Any authenticated


### Model Dependencies

**Total Endpoints**: 7

**Role Access Summary**:
- **ADMIN**: 3 endpoint(s)
- **ALL_AUTHENTICATED**: 4 endpoint(s)

**Sample Endpoints**:
- `PATCH /dependencies/{dependency_id}` — ADMIN
- `DELETE /dependencies/{dependency_id}` — ADMIN
- `POST /models/{model_id}/dependencies` — ADMIN
- `GET /models/{model_id}/dependencies/inbound` — Any authenticated
- `GET /models/{model_id}/dependencies/lineage` — Any authenticated


### Model Hierarchy

**Total Endpoints**: 6

**Role Access Summary**:
- **ADMIN**: 3 endpoint(s)
- **ALL_AUTHENTICATED**: 3 endpoint(s)

**Sample Endpoints**:
- `PATCH /hierarchy/{hierarchy_id}` — ADMIN
- `DELETE /hierarchy/{hierarchy_id}` — ADMIN
- `POST /models/{model_id}/hierarchy` — ADMIN
- `GET /models/{model_id}/hierarchy/children` — Any authenticated
- `GET /models/{model_id}/hierarchy/descendants` — Any authenticated


### Model Inventory

**Total Endpoints**: 30

**Role Access Summary**:
- **ADMIN**: 9 endpoint(s)
- **ALL_AUTHENTICATED**: 21 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated [RLS]
- `POST /` — ADMIN
- `POST /approval-status/backfill` — ADMIN
- `POST /approval-status/bulk` — Any authenticated
- `GET /export/csv` — Any authenticated [RLS]


### Model Regions

**Total Endpoints**: 4

**Role Access Summary**:
- **ADMIN**: 1 endpoint(s)
- **ALL_AUTHENTICATED**: 3 endpoint(s)

**Sample Endpoints**:
- `PUT /model-regions/{id}` — Any authenticated
- `DELETE /model-regions/{id}` — ADMIN
- `GET /models/{model_id}/regions` — Any authenticated
- `POST /models/{model_id}/regions` — Any authenticated


### Model Types

**Total Endpoints**: 9

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 9 endpoint(s)

**Sample Endpoints**:
- `GET /model-types/categories` — Any authenticated
- `POST /model-types/categories` — Any authenticated
- `PATCH /model-types/categories/{category_id}` — Any authenticated
- `DELETE /model-types/categories/{category_id}` — Any authenticated
- `GET /model-types/types` — Any authenticated


### Model Versions

**Total Endpoints**: 15

**Role Access Summary**:
- **ADMIN**: 2 endpoint(s)
- **ALL_AUTHENTICATED**: 13 endpoint(s)

**Sample Endpoints**:
- `GET /models/{model_id}/regional-versions` — Any authenticated
- `POST /models/{model_id}/versions` — Any authenticated
- `GET /models/{model_id}/versions` — Any authenticated
- `GET /models/{model_id}/versions/current` — Any authenticated
- `GET /models/{model_id}/versions/export/csv` — Any authenticated


### My Portfolio

**Total Endpoints**: 2

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 2 endpoint(s)

**Sample Endpoints**:
- `GET /reports/my-portfolio` — Any authenticated [Ownership]
- `GET /reports/my-portfolio/pdf` — Any authenticated


### Overdue Commentary

**Total Endpoints**: 4

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 4 endpoint(s)

**Sample Endpoints**:
- `GET /requests/{request_id}/overdue-commentary` — Any authenticated
- `POST /requests/{request_id}/overdue-commentary` — Any authenticated
- `GET /requests/{request_id}/overdue-commentary/history` — Any authenticated
- `GET /{model_id}/overdue-commentary` — Any authenticated


### Overdue Revalidation Report

**Total Endpoints**: 2

**Role Access Summary**:
- **ADMIN**: 1 endpoint(s)
- **ALL_AUTHENTICATED**: 1 endpoint(s)

**Sample Endpoints**:
- `GET /` — ADMIN
- `GET /regions` — Any authenticated


### Performance Monitoring

**Total Endpoints**: 49

**Role Access Summary**:
- **ADMIN**: 11 endpoint(s)
- **ALL_AUTHENTICATED**: 38 endpoint(s)

**Sample Endpoints**:
- `GET /models/{model_id}/monitoring-plans` — Any authenticated
- `GET /monitoring/admin-overview` — ADMIN
- `GET /monitoring/approvals/my-pending` — ADMIN
- `GET /monitoring/cycles/{cycle_id}` — Any authenticated
- `PATCH /monitoring/cycles/{cycle_id}` — Any authenticated


### Qualitative Factors

**Total Endpoints**: 11

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 11 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — Any authenticated
- `PUT /guidance/{guidance_id}` — Any authenticated
- `DELETE /guidance/{guidance_id}` — Any authenticated
- `POST /reorder` — Any authenticated


### Recommendations

**Total Endpoints**: 38

**Role Access Summary**:
- **ADMIN**: 23 endpoint(s)
- **ALL_AUTHENTICATED**: 15 endpoint(s)

**Sample Endpoints**:
- `POST /` — ADMIN
- `GET /` — Any authenticated
- `GET /dashboard/by-model/{model_id}` — Any authenticated
- `GET /dashboard/open` — Any authenticated
- `GET /dashboard/overdue` — Any authenticated


### Regional Management

**Total Endpoints**: 5

**Role Access Summary**:
- **ADMIN**: 3 endpoint(s)
- **ALL_AUTHENTICATED**: 2 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — ADMIN
- `GET /{region_id}` — Any authenticated
- `PUT /{region_id}` — ADMIN
- `DELETE /{region_id}` — ADMIN


### Residual Risk Map

**Total Endpoints**: 6

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 6 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — Any authenticated
- `PATCH /` — Any authenticated
- `POST /calculate` — Any authenticated
- `GET /versions` — Any authenticated


### Risk Assessment

**Total Endpoints**: 7

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 7 endpoint(s)

**Sample Endpoints**:
- `GET /models/{model_id}/risk-assessments/` — Any authenticated
- `POST /models/{model_id}/risk-assessments/` — Any authenticated
- `GET /models/{model_id}/risk-assessments/history` — Any authenticated
- `GET /models/{model_id}/risk-assessments/status` — Any authenticated
- `GET /models/{model_id}/risk-assessments/{assessment_id}` — Any authenticated


### Roles

**Total Endpoints**: 1

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 1 endpoint(s)

**Sample Endpoints**:
- `GET /roles` — Any authenticated


### Saved Queries

**Total Endpoints**: 5

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 5 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — Any authenticated
- `GET /{query_id}` — Any authenticated
- `PATCH /{query_id}` — Any authenticated
- `DELETE /{query_id}` — Any authenticated


### Scorecard

**Total Endpoints**: 20

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 20 endpoint(s)

**Sample Endpoints**:
- `GET /config` — Any authenticated
- `GET /criteria` — Any authenticated
- `POST /criteria` — Any authenticated
- `GET /criteria/{criterion_id}` — Any authenticated
- `PATCH /criteria/{criterion_id}` — Any authenticated


### Taxonomy Management

**Total Endpoints**: 10

**Role Access Summary**:
- **ADMIN**: 4 endpoint(s)
- **ALL_AUTHENTICATED**: 6 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — Any authenticated
- `GET /by-names/` — Any authenticated
- `GET /export/csv` — Any authenticated
- `PATCH /values/{value_id}` — ADMIN


### Uat Tools

**Total Endpoints**: 7

**Role Access Summary**:
- **ADMIN**: 1 endpoint(s)
- **ALL_AUTHENTICATED**: 6 endpoint(s)
- **USER**: 1 endpoint(s)
- **VALIDATOR**: 1 endpoint(s)

**Sample Endpoints**:
- `POST /backup` — Any authenticated
- `GET /backups` — Any authenticated
- `DELETE /backups/{backup_id}` — Any authenticated
- `GET /data-summary` — Any authenticated
- `DELETE /reset-transactional-data` — Any authenticated


### Validation Policies

**Total Endpoints**: 4

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 4 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — Any authenticated
- `PATCH /{policy_id}` — Any authenticated
- `DELETE /{policy_id}` — Any authenticated


### Validation Workflow

**Total Endpoints**: 68

**Role Access Summary**:
- **ADMIN**: 40 endpoint(s)
- **ALL_AUTHENTICATED**: 28 endpoint(s)

**Sample Endpoints**:
- `PATCH /approvals/{approval_id}` — ADMIN
- `POST /approvals/{approval_id}/submit-additional` — ADMIN
- `DELETE /approvals/{approval_id}/unlink` — ADMIN
- `POST /approvals/{approval_id}/void` — ADMIN
- `GET /assignments/` — ADMIN


### Vendor Management

**Total Endpoints**: 7

**Role Access Summary**:
- **ALL_AUTHENTICATED**: 7 endpoint(s)

**Sample Endpoints**:
- `GET /` — Any authenticated
- `POST /` — Any authenticated
- `GET /export/csv` — Any authenticated
- `GET /{vendor_id}` — Any authenticated
- `PATCH /{vendor_id}` — Any authenticated


### Version Deployment Tasks

**Total Endpoints**: 11

**Role Access Summary**:
- **ADMIN**: 2 endpoint(s)
- **ALL_AUTHENTICATED**: 9 endpoint(s)

**Sample Endpoints**:
- `POST /bulk/adjust` — Any authenticated
- `POST /bulk/cancel` — Any authenticated
- `POST /bulk/confirm` — Any authenticated
- `GET /my-tasks` — ADMIN
- `GET /ready-to-deploy` — ADMIN


### Workflow Sla

**Total Endpoints**: 2

**Role Access Summary**:
- **ADMIN**: 1 endpoint(s)
- **ALL_AUTHENTICATED**: 1 endpoint(s)

**Sample Endpoints**:
- `GET /validation` — Any authenticated
- `PATCH /validation` — ADMIN


## Authorization Patterns

The following authorization mechanisms were detected:

- **Admin-only checks**: 156 occurrence(s)
- **Admin helper functions**: 28 occurrence(s)
- **Explicit 403 Forbidden exceptions**: 28 occurrence(s)
- **Row-level security filters applied**: 11 occurrence(s)
- **Explicit role comparisons in code**: 5 occurrence(s)
- **Ownership/access checks**: 3 occurrence(s)

## Analysis Methodology

This analysis was performed by:

1. **Static Code Analysis**: Parsing Python source files using the `ast` module
2. **Pattern Matching**: Identifying authorization patterns including:
   - FastAPI route decorators and dependencies
   - `get_current_user` dependency injections
   - Role enum comparisons (`UserRole.ADMIN`, etc.)
   - String-based role checks (`role == "Admin"`)
   - RLS filter applications
   - Ownership verification calls
   - HTTP 403 authorization exceptions
3. **Feature Categorization**: Grouping endpoints by module/feature
4. **Role Aggregation**: Building role-centric capability views

**Limitations**:
- Dynamic authorization logic may not be fully captured
- Conditional permissions based on runtime state are approximated
- Frontend authorization is not included in this backend-focused analysis

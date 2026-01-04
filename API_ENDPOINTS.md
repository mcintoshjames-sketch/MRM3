## API Endpoint Appendix (Generated from code)

- Generated from FastAPI router definitions in `api/app/api/*` and `api/app/main.py` include_router prefixes.

### analytics (prefixes: /analytics)
- POST /analytics/query

### approver_roles (prefixes: /approver-roles)
- GET /approver-roles/
- POST /approver-roles/
- DELETE /approver-roles/{role_id}
- GET /approver-roles/{role_id}
- PATCH /approver-roles/{role_id}

### attestations (prefixes: /attestations)
- GET /attestations/admin/linked-changes
- GET /attestations/bulk/{cycle_id}
- DELETE /attestations/bulk/{cycle_id}/draft
- POST /attestations/bulk/{cycle_id}/draft
- POST /attestations/bulk/{cycle_id}/submit
- GET /attestations/cycles
- POST /attestations/cycles
- GET /attestations/cycles/reminder
- GET /attestations/cycles/{cycle_id}
- PATCH /attestations/cycles/{cycle_id}
- POST /attestations/cycles/{cycle_id}/close
- POST /attestations/cycles/{cycle_id}/open
- GET /attestations/dashboard/stats
- DELETE /attestations/evidence/{evidence_id}
- GET /attestations/my-attestations
- GET /attestations/my-upcoming
- GET /attestations/questions
- GET /attestations/questions/all
- PATCH /attestations/questions/{value_id}
- GET /attestations/records
- GET /attestations/records/{attestation_id}
- POST /attestations/records/{attestation_id}/accept
- POST /attestations/records/{attestation_id}/evidence
- POST /attestations/records/{attestation_id}/link-change
- GET /attestations/records/{attestation_id}/linked-changes
- POST /attestations/records/{attestation_id}/reject
- POST /attestations/records/{attestation_id}/submit
- GET /attestations/reports/coverage
- GET /attestations/reports/timeliness
- GET /attestations/rules
- POST /attestations/rules
- DELETE /attestations/rules/{rule_id}
- PATCH /attestations/rules/{rule_id}
- GET /attestations/targets
- PATCH /attestations/targets/{tier_id}

### audit_logs (prefixes: /audit-logs)
- GET /audit-logs/
- GET /audit-logs/actions
- GET /audit-logs/entities
- GET /audit-logs/entity-types

### auth (prefixes: /auth)
- POST /auth/entra/provision
- GET /auth/entra/users
- POST /auth/login
- GET /auth/me
- POST /auth/register
- GET /auth/users
- GET /auth/users/export/csv
- DELETE /auth/users/{user_id}
- GET /auth/users/{user_id}
- PATCH /auth/users/{user_id}
- GET /auth/users/{user_id}/models

### conditional_approval_rules (prefixes: /additional-approval-rules)
- GET /additional-approval-rules/
- POST /additional-approval-rules/
- POST /additional-approval-rules/preview
- DELETE /additional-approval-rules/{rule_id}
- GET /additional-approval-rules/{rule_id}
- PATCH /additional-approval-rules/{rule_id}

### dashboard (prefixes: /dashboard)
- GET /dashboard/mrsa-reviews/overdue
- GET /dashboard/mrsa-reviews/summary
- GET /dashboard/mrsa-reviews/upcoming
- GET /dashboard/news-feed

### decommissioning (prefixes: /decommissioning)
- GET /decommissioning/
- POST /decommissioning/
- GET /decommissioning/models/{model_id}/implementation-date
- GET /decommissioning/my-pending-approvals
- GET /decommissioning/my-pending-owner-reviews
- GET /decommissioning/pending-validator-review
- GET /decommissioning/{request_id}
- PATCH /decommissioning/{request_id}
- POST /decommissioning/{request_id}/approvals/{approval_id}
- POST /decommissioning/{request_id}/owner-review
- POST /decommissioning/{request_id}/validator-review
- POST /decommissioning/{request_id}/withdraw

### exceptions (prefixes: /exceptions)
- GET /exceptions/
- POST /exceptions/
- GET /exceptions/closure-reasons
- POST /exceptions/detect-all
- POST /exceptions/detect/{model_id}
- GET /exceptions/model/{model_id}
- GET /exceptions/summary
- GET /exceptions/{exception_id}
- POST /exceptions/{exception_id}/acknowledge
- POST /exceptions/{exception_id}/close

### export_views (prefixes: /export-views)
- GET /export-views/
- POST /export-views/
- DELETE /export-views/{view_id}
- GET /export-views/{view_id}
- PATCH /export-views/{view_id}

### fry (prefixes: /fry)
- DELETE /fry/line-items/{line_item_id}
- GET /fry/line-items/{line_item_id}
- PATCH /fry/line-items/{line_item_id}
- DELETE /fry/metric-groups/{metric_group_id}
- GET /fry/metric-groups/{metric_group_id}
- PATCH /fry/metric-groups/{metric_group_id}
- GET /fry/metric-groups/{metric_group_id}/line-items
- POST /fry/metric-groups/{metric_group_id}/line-items
- GET /fry/reports
- POST /fry/reports
- DELETE /fry/reports/{report_id}
- GET /fry/reports/{report_id}
- PATCH /fry/reports/{report_id}
- GET /fry/reports/{report_id}/schedules
- POST /fry/reports/{report_id}/schedules
- DELETE /fry/schedules/{schedule_id}
- GET /fry/schedules/{schedule_id}
- PATCH /fry/schedules/{schedule_id}
- GET /fry/schedules/{schedule_id}/metric-groups
- POST /fry/schedules/{schedule_id}/metric-groups

### irp (prefixes: /irps)
- GET /irps/
- POST /irps/
- GET /irps/coverage/check
- GET /irps/mrsa-review-status
- DELETE /irps/{irp_id:int}
- GET /irps/{irp_id:int}
- PATCH /irps/{irp_id:int}
- GET /irps/{irp_id:int}/certifications
- POST /irps/{irp_id:int}/certifications
- GET /irps/{irp_id:int}/reviews
- POST /irps/{irp_id:int}/reviews

### kpi_report (prefixes: /kpi-report)
- GET /kpi-report/

### kpm (prefixes: (none))
- GET /kpm/categories
- POST /kpm/categories
- DELETE /kpm/categories/{category_id}
- PATCH /kpm/categories/{category_id}
- GET /kpm/kpms
- POST /kpm/kpms
- DELETE /kpm/kpms/{kpm_id}
- GET /kpm/kpms/{kpm_id}
- PATCH /kpm/kpms/{kpm_id}

### limitations (prefixes: (none))
- GET /limitations/{limitation_id}
- PATCH /limitations/{limitation_id}
- POST /limitations/{limitation_id}/retire
- GET /models/{model_id}/limitations
- POST /models/{model_id}/limitations
- GET /reports/critical-limitations
- GET /validation-requests/{request_id}/limitations

### lob_units (prefixes: /lob-units)
- GET /lob-units/
- POST /lob-units/
- GET /lob-units/export-csv
- POST /lob-units/import-csv
- GET /lob-units/tree
- GET /lob-units/tree-with-teams
- DELETE /lob-units/{lob_id}
- GET /lob-units/{lob_id}
- PATCH /lob-units/{lob_id}
- GET /lob-units/{lob_id}/users

### map_applications (prefixes: /map)
- GET /map/applications
- GET /map/applications/{application_id}
- GET /map/departments

### methodology (prefixes: (none))
- GET /methodology-library/categories
- POST /methodology-library/categories
- DELETE /methodology-library/categories/{category_id}
- PATCH /methodology-library/categories/{category_id}
- GET /methodology-library/methodologies
- POST /methodology-library/methodologies
- DELETE /methodology-library/methodologies/{methodology_id}
- GET /methodology-library/methodologies/{methodology_id}
- PATCH /methodology-library/methodologies/{methodology_id}

### model_applications (prefixes: /models/{model_id}/applications)
- GET /models/{model_id}/applications
- POST /models/{model_id}/applications
- DELETE /models/{model_id}/applications/{application_id}
- PATCH /models/{model_id}/applications/{application_id}

### model_change_taxonomy (prefixes: (none))
- GET /change-taxonomy/categories
- POST /change-taxonomy/categories
- DELETE /change-taxonomy/categories/{category_id}
- PATCH /change-taxonomy/categories/{category_id}
- GET /change-taxonomy/types
- POST /change-taxonomy/types
- DELETE /change-taxonomy/types/{change_type_id}
- GET /change-taxonomy/types/{change_type_id}
- PATCH /change-taxonomy/types/{change_type_id}

### model_delegates (prefixes: (none))
- POST /delegates/batch
- DELETE /delegates/{delegate_id}
- PATCH /delegates/{delegate_id}
- PATCH /delegates/{delegate_id}/revoke
- GET /models/{model_id}/delegates
- POST /models/{model_id}/delegates

### model_dependencies (prefixes: (none))
- DELETE /dependencies/{dependency_id}
- PATCH /dependencies/{dependency_id}
- POST /models/{model_id}/dependencies
- GET /models/{model_id}/dependencies/inbound
- GET /models/{model_id}/dependencies/lineage
- GET /models/{model_id}/dependencies/lineage/pdf
- GET /models/{model_id}/dependencies/outbound

### model_hierarchy (prefixes: (none))
- DELETE /hierarchy/{hierarchy_id}
- PATCH /hierarchy/{hierarchy_id}
- POST /models/{model_id}/hierarchy
- GET /models/{model_id}/hierarchy/children
- GET /models/{model_id}/hierarchy/descendants
- GET /models/{model_id}/hierarchy/parents

### model_regions (prefixes: (none))
- DELETE /model-regions/{id}
- PUT /model-regions/{id}
- GET /models/{model_id}/regions
- POST /models/{model_id}/regions

### model_types (prefixes: (none))
- GET /model-types/categories
- POST /model-types/categories
- DELETE /model-types/categories/{category_id}
- PATCH /model-types/categories/{category_id}
- GET /model-types/types
- POST /model-types/types
- DELETE /model-types/types/{type_id}
- GET /model-types/types/{type_id}
- PATCH /model-types/types/{type_id}

### model_versions (prefixes: (none))
- GET /models/{model_id}/regional-versions
- GET /models/{model_id}/versions
- POST /models/{model_id}/versions
- GET /models/{model_id}/versions/current
- GET /models/{model_id}/versions/export/csv
- GET /models/{model_id}/versions/export/pdf
- GET /models/{model_id}/versions/next-version
- GET /versions/ready-to-deploy
- GET /versions/ready-to-deploy/summary
- DELETE /versions/{version_id}
- GET /versions/{version_id}
- PATCH /versions/{version_id}
- PATCH /versions/{version_id}/activate
- PATCH /versions/{version_id}/approve
- PATCH /versions/{version_id}/production

### models (prefixes: /models)
- GET /models/
- POST /models/
- POST /models/approval-status/backfill
- POST /models/approval-status/bulk
- GET /models/export/csv
- GET /models/my-submissions
- GET /models/name-changes/stats
- GET /models/pending-edits/all
- GET /models/pending-submissions
- DELETE /models/{model_id}
- GET /models/{model_id}
- PATCH /models/{model_id}
- GET /models/{model_id}/activity-timeline
- GET /models/{model_id}/approval-status
- GET /models/{model_id}/approval-status/history
- POST /models/{model_id}/approve
- POST /models/{model_id}/comments
- GET /models/{model_id}/exceptions
- GET /models/{model_id}/exceptions/count
- GET /models/{model_id}/final-risk-ranking
- GET /models/{model_id}/name-history
- GET /models/{model_id}/pending-edits
- POST /models/{model_id}/pending-edits/{edit_id}/approve
- POST /models/{model_id}/pending-edits/{edit_id}/reject
- POST /models/{model_id}/resubmit
- GET /models/{model_id}/revalidation-status
- GET /models/{model_id}/roles-with-lob
- POST /models/{model_id}/send-back
- GET /models/{model_id}/submission-thread
- GET /models/{model_id}/validation-suggestions

### monitoring (prefixes: (none))
- GET /models/{model_id}/monitoring-plans
- GET /monitoring/admin-overview
- GET /monitoring/approvals/my-pending
- DELETE /monitoring/cycles/{cycle_id}
- GET /monitoring/cycles/{cycle_id}
- PATCH /monitoring/cycles/{cycle_id}
- GET /monitoring/cycles/{cycle_id}/approvals
- POST /monitoring/cycles/{cycle_id}/approvals/{approval_id}/approve
- POST /monitoring/cycles/{cycle_id}/approvals/{approval_id}/reject
- POST /monitoring/cycles/{cycle_id}/approvals/{approval_id}/void
- POST /monitoring/cycles/{cycle_id}/cancel
- POST /monitoring/cycles/{cycle_id}/postpone
- GET /monitoring/cycles/{cycle_id}/report/pdf
- POST /monitoring/cycles/{cycle_id}/request-approval
- GET /monitoring/cycles/{cycle_id}/results
- POST /monitoring/cycles/{cycle_id}/results
- POST /monitoring/cycles/{cycle_id}/results/import
- POST /monitoring/cycles/{cycle_id}/resume
- POST /monitoring/cycles/{cycle_id}/start
- POST /monitoring/cycles/{cycle_id}/submit
- GET /monitoring/metrics/{plan_metric_id}/trend
- GET /monitoring/my-tasks
- GET /monitoring/plans
- POST /monitoring/plans
- DELETE /monitoring/plans/{plan_id}
- GET /monitoring/plans/{plan_id}
- PATCH /monitoring/plans/{plan_id}
- GET /monitoring/plans/{plan_id}/active-cycles-warning
- POST /monitoring/plans/{plan_id}/advance-cycle
- GET /monitoring/plans/{plan_id}/cycles
- POST /monitoring/plans/{plan_id}/cycles
- GET /monitoring/plans/{plan_id}/cycles/{cycle_id}/export
- POST /monitoring/plans/{plan_id}/deactivate
- GET /monitoring/plans/{plan_id}/deactivation-summary
- POST /monitoring/plans/{plan_id}/metrics
- DELETE /monitoring/plans/{plan_id}/metrics/{metric_id}
- PATCH /monitoring/plans/{plan_id}/metrics/{metric_id}
- GET /monitoring/plans/{plan_id}/performance-summary
- GET /monitoring/plans/{plan_id}/versions
- POST /monitoring/plans/{plan_id}/versions/publish
- GET /monitoring/plans/{plan_id}/versions/{version_id}
- GET /monitoring/plans/{plan_id}/versions/{version_id}/export
- DELETE /monitoring/results/{result_id}
- PATCH /monitoring/results/{result_id}
- GET /monitoring/teams
- POST /monitoring/teams
- DELETE /monitoring/teams/{team_id}
- GET /monitoring/teams/{team_id}
- PATCH /monitoring/teams/{team_id}

### mrsa_review_policy (prefixes: (none))
- GET /mrsa-review-exceptions/
- POST /mrsa-review-exceptions/
- PATCH /mrsa-review-exceptions/{exception_id}
- GET /mrsa-review-exceptions/{mrsa_id}
- GET /mrsa-review-policies/
- POST /mrsa-review-policies/
- DELETE /mrsa-review-policies/{policy_id}
- GET /mrsa-review-policies/{policy_id}
- PATCH /mrsa-review-policies/{policy_id}

### my_portfolio (prefixes: (none))
- GET /reports/my-portfolio
- GET /reports/my-portfolio/pdf

### overdue_commentary (prefixes: /models, /validation-workflow)
- GET /models/{model_id}/overdue-commentary
- GET /validation-workflow/requests/{request_id}/overdue-commentary
- POST /validation-workflow/requests/{request_id}/overdue-commentary
- GET /validation-workflow/requests/{request_id}/overdue-commentary/history

### overdue_revalidation_report (prefixes: /overdue-revalidation-report)
- GET /overdue-revalidation-report/
- GET /overdue-revalidation-report/regions

### qualitative_factors (prefixes: /risk-assessment/factors)
- GET /risk-assessment/factors/
- POST /risk-assessment/factors/
- DELETE /risk-assessment/factors/guidance/{guidance_id}
- PUT /risk-assessment/factors/guidance/{guidance_id}
- POST /risk-assessment/factors/reorder
- POST /risk-assessment/factors/validate-weights
- DELETE /risk-assessment/factors/{factor_id}
- GET /risk-assessment/factors/{factor_id}
- PUT /risk-assessment/factors/{factor_id}
- POST /risk-assessment/factors/{factor_id}/guidance
- PATCH /risk-assessment/factors/{factor_id}/weight

### recommendations (prefixes: /recommendations)
- GET /recommendations/
- POST /recommendations/
- GET /recommendations/dashboard/by-model/{model_id}
- GET /recommendations/dashboard/open
- GET /recommendations/dashboard/overdue
- GET /recommendations/my-tasks
- GET /recommendations/priority-config/
- GET /recommendations/priority-config/regional-overrides/
- POST /recommendations/priority-config/regional-overrides/
- DELETE /recommendations/priority-config/regional-overrides/{override_id}
- PATCH /recommendations/priority-config/regional-overrides/{override_id}
- PATCH /recommendations/priority-config/{priority_id}
- GET /recommendations/priority-config/{priority_id}/regional-overrides/
- GET /recommendations/timeframe-config/
- POST /recommendations/timeframe-config/calculate
- GET /recommendations/timeframe-config/{config_id}
- PATCH /recommendations/timeframe-config/{config_id}
- GET /recommendations/{recommendation_id}
- PATCH /recommendations/{recommendation_id}
- POST /recommendations/{recommendation_id}/acknowledge
- POST /recommendations/{recommendation_id}/action-plan
- POST /recommendations/{recommendation_id}/action-plan/request-revisions
- GET /recommendations/{recommendation_id}/approvals
- POST /recommendations/{recommendation_id}/approvals/{approval_id}/approve
- POST /recommendations/{recommendation_id}/approvals/{approval_id}/reject
- POST /recommendations/{recommendation_id}/approvals/{approval_id}/void
- GET /recommendations/{recommendation_id}/can-skip-action-plan
- POST /recommendations/{recommendation_id}/closure-review
- POST /recommendations/{recommendation_id}/decline-acknowledgement
- POST /recommendations/{recommendation_id}/evidence
- POST /recommendations/{recommendation_id}/finalize
- GET /recommendations/{recommendation_id}/limitations
- POST /recommendations/{recommendation_id}/rebuttal
- POST /recommendations/{recommendation_id}/rebuttal/{rebuttal_id}/review
- POST /recommendations/{recommendation_id}/skip-action-plan
- POST /recommendations/{recommendation_id}/submit
- POST /recommendations/{recommendation_id}/submit-closure
- PATCH /recommendations/{recommendation_id}/tasks/{task_id}

### regional_compliance_report (prefixes: /regional-compliance-report)
- GET /regional-compliance-report/

### regions (prefixes: /regions)
- GET /regions/
- POST /regions/
- DELETE /regions/{region_id}
- GET /regions/{region_id}
- PUT /regions/{region_id}

### residual_risk_map (prefixes: /residual-risk-map)
- GET /residual-risk-map/
- PATCH /residual-risk-map/
- POST /residual-risk-map/
- POST /residual-risk-map/calculate
- GET /residual-risk-map/versions
- GET /residual-risk-map/versions/{version_id}

### risk_assessment (prefixes: (none))
- GET /models/{model_id}/risk-assessments/
- POST /models/{model_id}/risk-assessments/
- GET /models/{model_id}/risk-assessments/history
- GET /models/{model_id}/risk-assessments/status
- DELETE /models/{model_id}/risk-assessments/{assessment_id}
- GET /models/{model_id}/risk-assessments/{assessment_id}
- PUT /models/{model_id}/risk-assessments/{assessment_id}
- GET /models/{model_id}/risk-assessments/{assessment_id}/pdf

### roles (prefixes: (none))
- GET /roles

### saved_queries (prefixes: /saved-queries)
- GET /saved-queries/
- POST /saved-queries/
- DELETE /saved-queries/{query_id}
- GET /saved-queries/{query_id}
- PATCH /saved-queries/{query_id}

### scorecard (prefixes: /scorecard)
- GET /scorecard/config
- GET /scorecard/criteria
- POST /scorecard/criteria
- DELETE /scorecard/criteria/{criterion_id}
- GET /scorecard/criteria/{criterion_id}
- PATCH /scorecard/criteria/{criterion_id}
- GET /scorecard/sections
- POST /scorecard/sections
- DELETE /scorecard/sections/{section_id}
- GET /scorecard/sections/{section_id}
- PATCH /scorecard/sections/{section_id}
- GET /scorecard/validation/{request_id}
- POST /scorecard/validation/{request_id}
- GET /scorecard/validation/{request_id}/export-pdf
- PATCH /scorecard/validation/{request_id}/overall-narrative
- PATCH /scorecard/validation/{request_id}/ratings/{criterion_code}
- GET /scorecard/versions
- GET /scorecard/versions/active
- POST /scorecard/versions/publish
- GET /scorecard/versions/{version_id}

### taxonomies (prefixes: /taxonomies)
- GET /taxonomies/
- POST /taxonomies/
- GET /taxonomies/by-names/
- GET /taxonomies/export/csv
- DELETE /taxonomies/values/{value_id}
- PATCH /taxonomies/values/{value_id}
- DELETE /taxonomies/{taxonomy_id}
- GET /taxonomies/{taxonomy_id}
- PATCH /taxonomies/{taxonomy_id}
- POST /taxonomies/{taxonomy_id}/values

### teams (prefixes: /teams)
- GET /teams/
- POST /teams/
- DELETE /teams/{team_id}
- GET /teams/{team_id}
- PATCH /teams/{team_id}
- GET /teams/{team_id}/lob-tree
- POST /teams/{team_id}/lobs
- DELETE /teams/{team_id}/lobs/{lob_id}
- GET /teams/{team_id}/models

### uat_tools (prefixes: /uat)
- POST /uat/backup
- GET /uat/backups
- DELETE /uat/backups/{backup_id}
- GET /uat/data-summary
- DELETE /uat/reset-transactional-data
- POST /uat/restore/{backup_id}
- POST /uat/seed-uat-data

### validation_policies (prefixes: /validation-workflow/policies)
- GET /validation-workflow/policies/
- POST /validation-workflow/policies/
- DELETE /validation-workflow/policies/{policy_id}
- PATCH /validation-workflow/policies/{policy_id}

### validation_workflow (prefixes: /validation-workflow)
- PATCH /validation-workflow/approvals/{approval_id}
- POST /validation-workflow/approvals/{approval_id}/submit-additional
- DELETE /validation-workflow/approvals/{approval_id}/unlink
- POST /validation-workflow/approvals/{approval_id}/void
- GET /validation-workflow/assignments/
- DELETE /validation-workflow/assignments/{assignment_id}
- PATCH /validation-workflow/assignments/{assignment_id}
- POST /validation-workflow/assignments/{assignment_id}/send-back
- POST /validation-workflow/assignments/{assignment_id}/sign-off
- GET /validation-workflow/compliance-report/deviation-trends
- GET /validation-workflow/component-definitions
- GET /validation-workflow/component-definitions/{component_id}
- PATCH /validation-workflow/component-definitions/{component_id}
- GET /validation-workflow/configurations
- POST /validation-workflow/configurations/publish
- GET /validation-workflow/configurations/{config_id}
- GET /validation-workflow/dashboard/aging
- GET /validation-workflow/dashboard/my-overdue-items
- GET /validation-workflow/dashboard/out-of-order
- GET /validation-workflow/dashboard/overdue-submissions
- GET /validation-workflow/dashboard/overdue-validations
- GET /validation-workflow/dashboard/pending-additional-approvals
- GET /validation-workflow/dashboard/pending-assignments
- GET /validation-workflow/dashboard/recent-approvals
- GET /validation-workflow/dashboard/sla-violations
- GET /validation-workflow/dashboard/upcoming-revalidations
- GET /validation-workflow/dashboard/workload
- GET /validation-workflow/models/{model_id}/revalidation-status
- GET /validation-workflow/my-overdue-items
- GET /validation-workflow/my-pending-approvals
- GET /validation-workflow/my-pending-submissions
- GET /validation-workflow/my-validator-overdue-items
- PATCH /validation-workflow/outcomes/{outcome_id}
- GET /validation-workflow/reports/risk-mismatch
- GET /validation-workflow/requests/
- POST /validation-workflow/requests/
- POST /validation-workflow/requests/check-warnings
- GET /validation-workflow/requests/preview-regions
- DELETE /validation-workflow/requests/{request_id}
- GET /validation-workflow/requests/{request_id}
- PATCH /validation-workflow/requests/{request_id}
- GET /validation-workflow/requests/{request_id}/additional-approvals
- POST /validation-workflow/requests/{request_id}/approvals
- POST /validation-workflow/requests/{request_id}/assignments
- POST /validation-workflow/requests/{request_id}/cancel
- PATCH /validation-workflow/requests/{request_id}/decline
- GET /validation-workflow/requests/{request_id}/effective-challenge-report
- POST /validation-workflow/requests/{request_id}/hold
- POST /validation-workflow/requests/{request_id}/mark-submission
- PATCH /validation-workflow/requests/{request_id}/models
- POST /validation-workflow/requests/{request_id}/outcome
- DELETE /validation-workflow/requests/{request_id}/plan
- GET /validation-workflow/requests/{request_id}/plan
- PATCH /validation-workflow/requests/{request_id}/plan
- POST /validation-workflow/requests/{request_id}/plan
- GET /validation-workflow/requests/{request_id}/plan/pdf
- GET /validation-workflow/requests/{request_id}/plan/template-suggestions
- GET /validation-workflow/requests/{request_id}/pre-transition-warnings
- POST /validation-workflow/requests/{request_id}/resume
- POST /validation-workflow/requests/{request_id}/review-outcome
- PATCH /validation-workflow/requests/{request_id}/status
- PATCH /validation-workflow/requests/{request_id}/submit-documentation
- PATCH /validation-workflow/review-outcomes/{review_outcome_id}
- GET /validation-workflow/risk-tier-impact/check/{model_id}
- POST /validation-workflow/risk-tier-impact/force-reset
- GET /validation-workflow/test/models-needing-revalidation
- GET /validation-workflow/test/revalidation-status/{model_id}
- GET /validation-workflow/validators/{validator_id}/assignments

### vendors (prefixes: /vendors)
- GET /vendors/
- POST /vendors/
- GET /vendors/export/csv
- DELETE /vendors/{vendor_id}
- GET /vendors/{vendor_id}
- PATCH /vendors/{vendor_id}
- GET /vendors/{vendor_id}/models

### version_deployment_tasks (prefixes: /deployment-tasks)
- POST /deployment-tasks/bulk/adjust
- POST /deployment-tasks/bulk/cancel
- POST /deployment-tasks/bulk/confirm
- GET /deployment-tasks/my-tasks
- GET /deployment-tasks/ready-to-deploy
- POST /deployment-tasks/version/{version_id}/deploy
- GET /deployment-tasks/version/{version_id}/deploy-modal
- GET /deployment-tasks/{task_id}
- PATCH /deployment-tasks/{task_id}/adjust
- PATCH /deployment-tasks/{task_id}/cancel
- PATCH /deployment-tasks/{task_id}/confirm

### workflow_sla (prefixes: /workflow-sla)
- GET /workflow-sla/validation
- PATCH /workflow-sla/validation

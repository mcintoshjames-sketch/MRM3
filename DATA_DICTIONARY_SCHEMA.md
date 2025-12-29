# Data Dictionary Schema Appendix (Authoritative)

This file is generated from the SQLAlchemy ORM models under `api/app/models`.

It is intended to be the **authoritative** listing of tables/columns (types, nullability, PK/FK, defaults, comments).

## Table Index

- `action_plan_tasks`
- `approver_roles`
- `attestation_bulk_submissions`
- `attestation_change_links`
- `attestation_coverage_targets`
- `attestation_cycles`
- `attestation_evidence`
- `attestation_question_configs`
- `attestation_records`
- `attestation_responses`
- `attestation_scheduling_rules`
- `audit_logs`
- `closure_evidence`
- `component_definition_config_items`
- `component_definition_configurations`
- `conditional_approval_rules`
- `decommissioning_approvals`
- `decommissioning_requests`
- `decommissioning_status_history`
- `entra_users`
- `export_views`
- `fry_line_items`
- `fry_metric_groups`
- `fry_reports`
- `fry_schedules`
- `irp_certifications`
- `irp_reviews`
- `irps`
- `kpm_categories`
- `kpms`
- `lob_units`
- `map_applications`
- `methodologies`
- `methodology_categories`
- `model_applications`
- `model_approval_status_history`
- `model_change_categories`
- `model_change_types`
- `model_delegates`
- `model_dependency_metadata`
- `model_exception_status_history`
- `model_exceptions`
- `model_feed_dependencies`
- `model_hierarchy`
- `model_limitations`
- `model_name_history`
- `model_pending_edits`
- `model_regions`
- `model_regulatory_categories`
- `model_risk_assessments`
- `model_submission_comments`
- `model_type_categories`
- `model_types`
- `model_users`
- `model_version_regions`
- `model_versions`
- `models`
- `monitoring_cycle_approvals`
- `monitoring_cycles`
- `monitoring_plan_metric_snapshots`
- `monitoring_plan_metrics`
- `monitoring_plan_model_snapshots`
- `monitoring_plan_models`
- `monitoring_plan_versions`
- `monitoring_plans`
- `monitoring_results`
- `monitoring_team_members`
- `monitoring_teams`
- `mrsa_irp`
- `mrsa_review_exceptions`
- `mrsa_review_policies`
- `overdue_revalidation_comments`
- `qualitative_factor_assessments`
- `qualitative_factor_guidance`
- `qualitative_risk_factors`
- `recommendation_approvals`
- `recommendation_priority_configs`
- `recommendation_priority_regional_overrides`
- `recommendation_rebuttals`
- `recommendation_status_history`
- `recommendation_timeframe_configs`
- `recommendations`
- `regions`
- `residual_risk_map_configs`
- `rule_required_approvers`
- `scorecard_config_versions`
- `scorecard_criteria`
- `scorecard_criterion_snapshots`
- `scorecard_section_snapshots`
- `scorecard_sections`
- `taxonomies`
- `taxonomy_values`
- `user_regions`
- `users`
- `validation_approvals`
- `validation_assignments`
- `validation_component_definitions`
- `validation_findings`
- `validation_grouping_memory`
- `validation_outcomes`
- `validation_plan_components`
- `validation_plans`
- `validation_policies`
- `validation_request_models`
- `validation_request_regions`
- `validation_requests`
- `validation_review_outcomes`
- `validation_scorecard_ratings`
- `validation_scorecard_results`
- `validation_status_history`
- `validation_work_components`
- `validation_workflow_slas`
- `vendors`
- `version_deployment_tasks`

## Tables

### `action_plan_tasks`

- **Primary Key:** task_id
- **Foreign Keys:** completion_status_id → taxonomy_values.value_id, owner_id → users.user_id, recommendation_id → recommendations.recommendation_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| task_id | INTEGER | No | Yes |  |  |  |
| recommendation_id | INTEGER | No |  | recommendations.recommendation_id |  |  |
| task_order | INTEGER | No |  |  | 1 |  |
| description | TEXT | No |  |  |  |  |
| owner_id | INTEGER | No |  | users.user_id |  |  |
| target_date | DATE | No |  |  |  |  |
| completed_date | DATE | Yes |  |  |  |  |
| completion_status_id | INTEGER | No |  | taxonomy_values.value_id |  | NOT_STARTED, IN_PROGRESS, COMPLETED |
| completion_notes | TEXT | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1077905e0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107790a40> |  |

### `approver_roles`

- **Primary Key:** role_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| role_id | INTEGER | No | Yes |  |  |  |
| role_name | VARCHAR(200) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| is_active | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1074677e0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107467880> |  |

### `attestation_bulk_submissions`

- **Primary Key:** bulk_submission_id
- **Foreign Keys:** cycle_id → attestation_cycles.cycle_id, user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| bulk_submission_id | INTEGER | No | Yes |  |  |  |
| cycle_id | INTEGER | No |  | attestation_cycles.cycle_id |  |  |
| user_id | INTEGER | No |  | users.user_id |  |  |
| status | VARCHAR(20) | No |  |  | DRAFT |  |
| selected_model_ids | JSON | Yes |  |  |  |  |
| excluded_model_ids | JSON | Yes |  |  |  |  |
| draft_responses | JSON | Yes |  |  |  |  |
| draft_comment | TEXT | Yes |  |  |  |  |
| submitted_at | DATETIME | Yes |  |  |  |  |
| attestation_count | INTEGER | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1079c4b80> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1079c58a0> |  |

### `attestation_change_links`

- **Primary Key:** link_id
- **Foreign Keys:** attestation_id → attestation_records.attestation_id, decommissioning_request_id → decommissioning_requests.request_id, model_id → models.model_id, pending_edit_id → model_pending_edits.pending_edit_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| link_id | INTEGER | No | Yes |  |  |  |
| attestation_id | INTEGER | No |  | attestation_records.attestation_id |  |  |
| change_type | VARCHAR(20) | No |  |  |  |  |
| pending_edit_id | INTEGER | Yes |  | model_pending_edits.pending_edit_id |  |  |
| model_id | INTEGER | Yes |  | models.model_id |  |  |
| decommissioning_request_id | INTEGER | Yes |  | decommissioning_requests.request_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1079993a0> |  |

### `attestation_coverage_targets`

- **Primary Key:** target_id
- **Foreign Keys:** created_by_user_id → users.user_id, risk_tier_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| target_id | INTEGER | No | Yes |  |  |  |
| risk_tier_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| target_percentage | DECIMAL(5, 2) | No |  |  |  |  |
| is_blocking | BOOLEAN | No |  |  | True |  |
| effective_date | DATE | No |  |  |  |  |
| end_date | DATE | Yes |  |  |  |  |
| created_by_user_id | INTEGER | No |  | users.user_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10799afc0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10799b1a0> |  |

### `attestation_cycles`

- **Primary Key:** cycle_id
- **Foreign Keys:** closed_by_user_id → users.user_id, opened_by_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| cycle_id | INTEGER | No | Yes |  |  |  |
| cycle_name | VARCHAR(100) | No |  |  |  |  |
| period_start_date | DATE | No |  |  |  |  |
| period_end_date | DATE | No |  |  |  |  |
| submission_due_date | DATE | No |  |  |  |  |
| status | VARCHAR(20) | No |  |  | PENDING |  |
| opened_at | DATETIME | Yes |  |  |  |  |
| opened_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| closed_at | DATETIME | Yes |  |  |  |  |
| closed_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| notes | TEXT | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10793c180> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10793c4a0> |  |

### `attestation_evidence`

- **Primary Key:** evidence_id
- **Foreign Keys:** added_by_user_id → users.user_id, attestation_id → attestation_records.attestation_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| evidence_id | INTEGER | No | Yes |  |  |  |
| attestation_id | INTEGER | No |  | attestation_records.attestation_id |  |  |
| evidence_type | VARCHAR(30) | No |  |  | OTHER |  |
| url | VARCHAR(2000) | No |  |  |  |  |
| description | VARCHAR(500) | Yes |  |  |  |  |
| added_by_user_id | INTEGER | No |  | users.user_id |  |  |
| added_at | DATETIME | No |  |  | <function utc_now at 0x107971da0> |  |

### `attestation_question_configs`

- **Primary Key:** config_id
- **Foreign Keys:** question_value_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| config_id | INTEGER | No | Yes |  |  |  |
| question_value_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| frequency_scope | VARCHAR(20) | No |  |  | BOTH |  |
| requires_comment_if_no | BOOLEAN | No |  |  | False |  |

### `attestation_records`

- **Primary Key:** attestation_id
- **Foreign Keys:** attesting_user_id → users.user_id, bulk_submission_id → attestation_bulk_submissions.bulk_submission_id, cycle_id → attestation_cycles.cycle_id, model_id → models.model_id, reviewed_by_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| attestation_id | INTEGER | No | Yes |  |  |  |
| cycle_id | INTEGER | No |  | attestation_cycles.cycle_id |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| attesting_user_id | INTEGER | No |  | users.user_id |  |  |
| due_date | DATE | No |  |  |  |  |
| status | VARCHAR(20) | No |  |  | PENDING |  |
| attested_at | DATETIME | Yes |  |  |  |  |
| decision | VARCHAR(30) | Yes |  |  |  |  |
| decision_comment | TEXT | Yes |  |  |  |  |
| reviewed_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| reviewed_at | DATETIME | Yes |  |  |  |  |
| review_comment | TEXT | Yes |  |  |  |  |
| bulk_submission_id | INTEGER | Yes |  | attestation_bulk_submissions.bulk_submission_id |  |  |
| is_excluded | BOOLEAN | No |  |  | False | True if model was excluded from bulk attestation |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10793e3e0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10793e480> |  |

### `attestation_responses`

- **Primary Key:** response_id
- **Foreign Keys:** attestation_id → attestation_records.attestation_id, question_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| response_id | INTEGER | No | Yes |  |  |  |
| attestation_id | INTEGER | No |  | attestation_records.attestation_id |  |  |
| question_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| answer | BOOLEAN | No |  |  |  |  |
| comment | TEXT | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107970900> |  |

### `attestation_scheduling_rules`

- **Primary Key:** rule_id
- **Foreign Keys:** created_by_user_id → users.user_id, model_id → models.model_id, region_id → regions.region_id, updated_by_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| rule_id | INTEGER | No | Yes |  |  |  |
| rule_name | VARCHAR(100) | No |  |  |  |  |
| rule_type | VARCHAR(30) | No |  |  | GLOBAL_DEFAULT |  |
| frequency | VARCHAR(20) | No |  |  | ANNUAL |  |
| priority | INTEGER | No |  |  | 10 |  |
| is_active | BOOLEAN | No |  |  | True |  |
| owner_model_count_min | INTEGER | Yes |  |  |  | Minimum model count for owner to trigger this rule |
| owner_high_fluctuation_flag | BOOLEAN | Yes |  |  |  | If true, applies to owners with high_fluctuation_flag set |
| model_id | INTEGER | Yes |  | models.model_id |  |  |
| region_id | INTEGER | Yes |  | regions.region_id |  |  |
| effective_date | DATE | No |  |  |  |  |
| end_date | DATE | Yes |  |  |  |  |
| created_by_user_id | INTEGER | No |  | users.user_id |  |  |
| updated_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107973240> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107973920> |  |

### `audit_logs`

- **Primary Key:** log_id
- **Foreign Keys:** user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| log_id | INTEGER | No | Yes |  |  |  |
| entity_type | VARCHAR(50) | No |  |  |  |  |
| entity_id | INTEGER | No |  |  |  |  |
| action | VARCHAR(50) | No |  |  |  |  |
| user_id | INTEGER | No |  | users.user_id |  |  |
| changes | JSON | Yes |  |  |  |  |
| timestamp | DATETIME | No |  |  | <function utc_now at 0x10733a0c0> |  |

### `closure_evidence`

- **Primary Key:** evidence_id
- **Foreign Keys:** recommendation_id → recommendations.recommendation_id, uploaded_by_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| evidence_id | INTEGER | No | Yes |  |  |  |
| recommendation_id | INTEGER | No |  | recommendations.recommendation_id |  |  |
| file_name | VARCHAR(255) | No |  |  |  |  |
| file_path | TEXT | No |  |  |  | URL to evidence document |
| file_type | VARCHAR(50) | Yes |  |  |  |  |
| file_size_bytes | INTEGER | Yes |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| uploaded_by_id | INTEGER | No |  | users.user_id |  |  |
| uploaded_at | DATETIME | No |  |  | <function utc_now at 0x107793c40> |  |

### `component_definition_config_items`

- **Primary Key:** config_item_id
- **Foreign Keys:** component_id → validation_component_definitions.component_id, config_id → component_definition_configurations.config_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| config_item_id | INTEGER | No | Yes |  |  |  |
| config_id | INTEGER | No |  | component_definition_configurations.config_id |  |  |
| component_id | INTEGER | No |  | validation_component_definitions.component_id |  |  |
| expectation_high | VARCHAR(20) | No |  |  |  |  |
| expectation_medium | VARCHAR(20) | No |  |  |  |  |
| expectation_low | VARCHAR(20) | No |  |  |  |  |
| expectation_very_low | VARCHAR(20) | No |  |  |  |  |
| section_number | VARCHAR(10) | No |  |  |  |  |
| section_title | VARCHAR(200) | No |  |  |  |  |
| component_code | VARCHAR(20) | No |  |  |  |  |
| component_title | VARCHAR(200) | No |  |  |  |  |
| is_test_or_analysis | BOOLEAN | No |  |  | False |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |

### `component_definition_configurations`

- **Primary Key:** config_id
- **Foreign Keys:** created_by_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| config_id | INTEGER | No | Yes |  |  |  |
| config_name | VARCHAR(200) | No |  |  |  | e.g., '2025-11-22 Initial Configuration', 'Q2 2026 SR 11-7 Update' |
| description | TEXT | Yes |  |  |  | Details about this configuration version |
| effective_date | DATE | No |  |  |  | When this configuration took effect |
| created_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1075dc2c0> |  |
| is_active | BOOLEAN | No |  |  | True | Only one configuration is active at a time |

### `conditional_approval_rules`

- **Primary Key:** rule_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| rule_id | INTEGER | No | Yes |  |  |  |
| rule_name | VARCHAR(200) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| is_active | BOOLEAN | No |  |  | True |  |
| validation_type_ids | TEXT | Yes |  |  |  | Comma-separated validation type IDs (empty = any validation type) |
| risk_tier_ids | TEXT | Yes |  |  |  | Comma-separated risk tier IDs (empty = any risk tier) |
| governance_region_ids | TEXT | Yes |  |  |  | Comma-separated governance region IDs (empty = any governance region) |
| deployed_region_ids | TEXT | Yes |  |  |  | Comma-separated deployed region IDs (empty = any deployed region) |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107494900> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1074949a0> |  |

### `decommissioning_approvals`

- **Primary Key:** approval_id
- **Foreign Keys:** approved_by_id → users.user_id, region_id → regions.region_id, request_id → decommissioning_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| approval_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | decommissioning_requests.request_id |  |  |
| approver_type | VARCHAR(20) | No |  |  |  |  |
| region_id | INTEGER | Yes |  | regions.region_id |  |  |
| approved_by_id | INTEGER | Yes |  | users.user_id |  |  |
| approved_at | DATETIME | Yes |  |  |  |  |
| is_approved | BOOLEAN | Yes |  |  |  |  |
| comment | TEXT | Yes |  |  |  |  |

### `decommissioning_requests`

- **Primary Key:** request_id
- **Foreign Keys:** created_by_id → users.user_id, model_id → models.model_id, owner_reviewed_by_id → users.user_id, reason_id → taxonomy_values.value_id, replacement_model_id → models.model_id, validator_reviewed_by_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| request_id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| status | VARCHAR(30) | No |  |  | PENDING |  |
| reason_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| replacement_model_id | INTEGER | Yes |  | models.model_id |  |  |
| last_production_date | DATE | No |  |  |  |  |
| gap_justification | TEXT | Yes |  |  |  |  |
| archive_location | TEXT | No |  |  |  |  |
| downstream_impact_verified | BOOLEAN | No |  |  | False |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10763b880> |  |
| created_by_id | INTEGER | No |  | users.user_id |  |  |
| validator_reviewed_by_id | INTEGER | Yes |  | users.user_id |  |  |
| validator_reviewed_at | DATETIME | Yes |  |  |  |  |
| validator_comment | TEXT | Yes |  |  |  |  |
| owner_approval_required | BOOLEAN | No |  |  | False |  |
| owner_reviewed_by_id | INTEGER | Yes |  | users.user_id |  |  |
| owner_reviewed_at | DATETIME | Yes |  |  |  |  |
| owner_comment | TEXT | Yes |  |  |  |  |
| final_reviewed_at | DATETIME | Yes |  |  |  |  |
| rejection_reason | TEXT | Yes |  |  |  |  |

### `decommissioning_status_history`

- **Primary Key:** history_id
- **Foreign Keys:** changed_by_id → users.user_id, request_id → decommissioning_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| history_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | decommissioning_requests.request_id |  |  |
| old_status | VARCHAR(30) | Yes |  |  |  |  |
| new_status | VARCHAR(30) | No |  |  |  |  |
| changed_by_id | INTEGER | No |  | users.user_id |  |  |
| changed_at | DATETIME | No |  |  | <function utc_now at 0x10766a0c0> |  |
| notes | TEXT | Yes |  |  |  |  |

### `entra_users`

- **Primary Key:** entra_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| entra_id | VARCHAR(36) | No | Yes |  |  |  |
| user_principal_name | VARCHAR(255) | No |  |  |  |  |
| display_name | VARCHAR(255) | No |  |  |  |  |
| given_name | VARCHAR(100) | Yes |  |  |  |  |
| surname | VARCHAR(100) | Yes |  |  |  |  |
| mail | VARCHAR(255) | No |  |  |  |  |
| job_title | VARCHAR(255) | Yes |  |  |  |  |
| department | VARCHAR(255) | Yes |  |  |  |  |
| office_location | VARCHAR(255) | Yes |  |  |  |  |
| mobile_phone | VARCHAR(50) | Yes |  |  |  |  |
| account_enabled | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10730e5c0> |  |

### `export_views`

- **Primary Key:** view_id
- **Foreign Keys:** user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| view_id | INTEGER | No | Yes |  |  |  |
| user_id | INTEGER | No |  | users.user_id |  |  |
| entity_type | VARCHAR(50) | No |  |  |  | Entity type (e.g., 'models', 'validations') |
| view_name | VARCHAR(100) | No |  |  |  |  |
| is_public | BOOLEAN | No |  |  | False | If true, all users can see this view |
| columns | JSON | No |  |  |  | Array of column keys to include in export |
| description | TEXT | Yes |  |  |  | Optional description of what this view is for |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107606340> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1076063e0> |  |

### `fry_line_items`

- **Primary Key:** line_item_id
- **Foreign Keys:** metric_group_id → fry_metric_groups.metric_group_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| line_item_id | INTEGER | No | Yes |  |  |  |
| metric_group_id | INTEGER | No |  | fry_metric_groups.metric_group_id |  |  |
| line_item_text | TEXT | No |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1074b6980> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1074b6b60> |  |

### `fry_metric_groups`

- **Primary Key:** metric_group_id
- **Foreign Keys:** schedule_id → fry_schedules.schedule_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| metric_group_id | INTEGER | No | Yes |  |  |  |
| schedule_id | INTEGER | No |  | fry_schedules.schedule_id |  |  |
| metric_group_name | VARCHAR(200) | No |  |  |  |  |
| model_driven | BOOLEAN | No |  |  | False |  |
| rationale | TEXT | Yes |  |  |  |  |
| is_active | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1074b5760> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1074b5800> |  |

### `fry_reports`

- **Primary Key:** report_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| report_id | INTEGER | No | Yes |  |  |  |
| report_code | VARCHAR(50) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| is_active | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107497060> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107497100> |  |

### `fry_schedules`

- **Primary Key:** schedule_id
- **Foreign Keys:** report_id → fry_reports.report_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| schedule_id | INTEGER | No | Yes |  |  |  |
| report_id | INTEGER | No |  | fry_reports.report_id |  |  |
| schedule_code | VARCHAR(200) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| is_active | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1074b4220> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1074b42c0> |  |

### `irp_certifications`

- **Primary Key:** certification_id
- **Foreign Keys:** certified_by_user_id → users.user_id, irp_id → irps.irp_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| certification_id | INTEGER | No | Yes |  |  |  |
| irp_id | INTEGER | No |  | irps.irp_id |  | IRP being certified |
| certification_date | DATE | No |  |  |  | Date the certification was completed |
| certified_by_user_id | INTEGER | No |  | users.user_id |  | MRM person who performed the certification |
| conclusion_summary | TEXT | No |  |  |  | Narrative summary of the certification conclusion |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107914360> |  |

### `irp_reviews`

- **Primary Key:** review_id
- **Foreign Keys:** irp_id → irps.irp_id, outcome_id → taxonomy_values.value_id, reviewed_by_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| review_id | INTEGER | No | Yes |  |  |  |
| irp_id | INTEGER | No |  | irps.irp_id |  | IRP being reviewed |
| review_date | DATE | No |  |  |  | Date the review was completed |
| outcome_id | INTEGER | No |  | taxonomy_values.value_id |  | IRP Review Outcome taxonomy value (Satisfactory, etc.) |
| notes | TEXT | Yes |  |  |  | Notes and observations from the review |
| reviewed_by_user_id | INTEGER | No |  | users.user_id |  | User who performed the review |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1078e6ca0> |  |

### `irps`

- **Primary Key:** irp_id
- **Foreign Keys:** contact_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| irp_id | INTEGER | No | Yes |  |  |  |
| process_name | VARCHAR(255) | No |  |  |  | Name of the Independent Review Process |
| contact_user_id | INTEGER | No |  | users.user_id |  | Primary contact person responsible for this IRP |
| description | TEXT | Yes |  |  |  | Description of the IRP scope and purpose |
| is_active | BOOLEAN | No |  |  | True | Whether this IRP is currently active |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1078e5760> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1078e5800> |  |

### `kpm_categories`

- **Primary Key:** category_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| category_id | INTEGER | No | Yes |  |  |  |
| code | VARCHAR(100) | No |  |  |  |  |
| name | VARCHAR(200) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| category_type | VARCHAR(50) | No |  |  | Quantitative | Category type: Quantitative or Qualitative |

### `kpms`

- **Primary Key:** kpm_id
- **Foreign Keys:** category_id → kpm_categories.category_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| kpm_id | INTEGER | No | Yes |  |  |  |
| category_id | INTEGER | No |  | kpm_categories.category_id |  |  |
| name | VARCHAR(200) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| calculation | TEXT | Yes |  |  |  |  |
| interpretation | TEXT | Yes |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |
| evaluation_type | VARCHAR(50) | No |  |  | Quantitative | How this KPM is evaluated: Quantitative (thresholds), Qualitative (rules/judgment), Outcome Only (direct R/Y/G) |

### `lob_units`

- **Primary Key:** lob_id
- **Foreign Keys:** parent_id → lob_units.lob_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| lob_id | INTEGER | No | Yes |  |  |  |
| parent_id | INTEGER | Yes |  | lob_units.lob_id |  |  |
| code | VARCHAR(50) | No |  |  |  |  |
| name | VARCHAR(255) | No |  |  |  |  |
| level | INTEGER | No |  |  |  | Hierarchy depth: 1=SBU, 2=LOB1, 3=LOB2, etc. |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |
| org_unit | VARCHAR(5) | No |  |  |  | External org unit identifier (5 chars, e.g., 12345 or S0001) |
| description | TEXT | Yes |  |  |  |  |
| contact_name | VARCHAR(255) | Yes |  |  |  |  |
| org_description | TEXT | Yes |  |  |  |  |
| legal_entity_id | VARCHAR(50) | Yes |  |  |  |  |
| legal_entity_name | VARCHAR(255) | Yes |  |  |  |  |
| short_name | VARCHAR(100) | Yes |  |  |  |  |
| status_code | VARCHAR(20) | Yes |  |  |  |  |
| tier | VARCHAR(50) | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107281ee0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x106dded40> |  |

### `map_applications`

- **Primary Key:** application_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| application_id | INTEGER | No | Yes |  |  |  |
| application_code | VARCHAR(50) | No |  |  |  | Unique identifier from MAP system (e.g., APP-12345) |
| application_name | VARCHAR(255) | No |  |  |  | Display name of the application |
| description | TEXT | Yes |  |  |  | Description of the application's purpose |
| owner_name | VARCHAR(255) | Yes |  |  |  | Application owner/steward name |
| owner_email | VARCHAR(255) | Yes |  |  |  | Application owner email |
| department | VARCHAR(100) | Yes |  |  |  | Department responsible for the application |
| technology_stack | VARCHAR(255) | Yes |  |  |  | Technology stack (e.g., Python/AWS Lambda, Java/On-Prem) |
| criticality_tier | VARCHAR(20) | Yes |  |  |  | Application criticality: Critical, High, Medium, Low |
| status | VARCHAR(50) | No |  |  | Active | Application status: Active, Decommissioned, In Development |
| external_url | VARCHAR(500) | Yes |  |  |  | Link to MAP system record for this application |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10743aac0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10743ab60> |  |

### `methodologies`

- **Primary Key:** methodology_id
- **Foreign Keys:** category_id → methodology_categories.category_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| methodology_id | INTEGER | No | Yes |  |  |  |
| category_id | INTEGER | No |  | methodology_categories.category_id |  |  |
| name | VARCHAR(200) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| variants | TEXT | Yes |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |

### `methodology_categories`

- **Primary Key:** category_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| category_id | INTEGER | No | Yes |  |  |  |
| code | VARCHAR(50) | No |  |  |  |  |
| name | VARCHAR(100) | No |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_aiml | BOOLEAN | No |  |  | False |  |

### `model_applications`

- **Primary Key:** model_id, application_id
- **Foreign Keys:** application_id → map_applications.application_id, created_by_user_id → users.user_id, model_id → models.model_id, relationship_type_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| model_id | INTEGER | No | Yes | models.model_id |  |  |
| application_id | INTEGER | No | Yes | map_applications.application_id |  |  |
| relationship_type_id | INTEGER | No |  | taxonomy_values.value_id |  | Type of relationship (Data Source, Execution Platform, etc.) |
| description | TEXT | Yes |  |  |  | Notes about this specific relationship |
| effective_date | DATE | Yes |  |  |  | When this relationship became effective |
| end_date | DATE | Yes |  |  |  | When this relationship ended (soft delete) |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107464040> |  |
| created_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1074644a0> |  |

### `model_approval_status_history`

- **Primary Key:** history_id
- **Foreign Keys:** model_id → models.model_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| history_id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| old_status | VARCHAR(30) | Yes |  |  |  | Previous approval status (NULL for initial status) |
| new_status | VARCHAR(30) | No |  |  |  | New approval status |
| changed_at | DATETIME | No |  |  | <function utc_now at 0x1073bae80> |  |
| trigger_type | VARCHAR(50) | No |  |  |  | What triggered this change: VALIDATION_APPROVED, VALIDATION_STATUS_CHANGE, APPROVAL_SUBMITTED, EXPIRATION_CHECK, BACKFILL, MANUAL |
| trigger_entity_type | VARCHAR(50) | Yes |  |  |  | Entity type that triggered change: ValidationRequest, ValidationApproval, etc. |
| trigger_entity_id | INTEGER | Yes |  |  |  | ID of the entity that triggered the change |
| notes | TEXT | Yes |  |  |  | Additional context about the status change |

### `model_change_categories`

- **Primary Key:** category_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| category_id | INTEGER | No | Yes |  |  |  |
| code | VARCHAR(10) | No |  |  |  |  |
| name | VARCHAR(100) | No |  |  |  |  |
| sort_order | INTEGER | No |  |  |  |  |

### `model_change_types`

- **Primary Key:** change_type_id
- **Foreign Keys:** category_id → model_change_categories.category_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| change_type_id | INTEGER | No | Yes |  |  |  |
| category_id | INTEGER | No |  | model_change_categories.category_id |  |  |
| code | INTEGER | No |  |  |  |  |
| name | VARCHAR(200) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| mv_activity | VARCHAR(50) | Yes |  |  |  |  |
| requires_mv_approval | BOOLEAN | No |  |  | False |  |
| sort_order | INTEGER | No |  |  |  |  |
| is_active | BOOLEAN | No |  |  | True |  |

### `model_delegates`

- **Primary Key:** delegate_id
- **Foreign Keys:** delegated_by_id → users.user_id, model_id → models.model_id, revoked_by_id → users.user_id, user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| delegate_id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| user_id | INTEGER | No |  | users.user_id |  |  |
| can_submit_changes | BOOLEAN | No |  |  | False |  |
| can_manage_regional | BOOLEAN | No |  |  | False |  |
| can_attest | BOOLEAN | No |  |  | False | Can submit attestations on behalf of model owner |
| delegated_by_id | INTEGER | No |  | users.user_id |  |  |
| delegated_at | DATETIME | No |  |  | <function utc_now at 0x10738e980> |  |
| revoked_at | DATETIME | Yes |  |  |  |  |
| revoked_by_id | INTEGER | Yes |  | users.user_id |  |  |

### `model_dependency_metadata`

- **Primary Key:** id
- **Foreign Keys:** criticality_id → taxonomy_values.value_id, dependency_id → model_feed_dependencies.id, feed_frequency_id → taxonomy_values.value_id, interface_type_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| id | INTEGER | No | Yes |  |  |  |
| dependency_id | INTEGER | No |  | model_feed_dependencies.id |  |  |
| feed_frequency_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| interface_type_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| criticality_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| data_fields_summary | TEXT | Yes |  |  |  |  |
| notes | VARCHAR(1000) | Yes |  |  |  |  |
| data_contract_id | INTEGER | Yes |  |  |  |  |

### `model_exception_status_history`

- **Primary Key:** history_id
- **Foreign Keys:** changed_by_id → users.user_id, exception_id → model_exceptions.exception_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| history_id | INTEGER | No | Yes |  |  |  |
| exception_id | INTEGER | No |  | model_exceptions.exception_id |  |  |
| old_status | VARCHAR(20) | Yes |  |  |  | NULL for initial creation |
| new_status | VARCHAR(20) | No |  |  |  |  |
| changed_by_id | INTEGER | Yes |  | users.user_id |  | NULL for system-initiated changes |
| changed_at | DATETIME | No |  |  | <function utc_now at 0x107b23b00> |  |
| notes | TEXT | Yes |  |  |  |  |

### `model_exceptions`

- **Primary Key:** exception_id
- **Foreign Keys:** acknowledged_by_id → users.user_id, attestation_response_id → attestation_responses.response_id, closed_by_id → users.user_id, closure_reason_id → taxonomy_values.value_id, deployment_task_id → version_deployment_tasks.task_id, model_id → models.model_id, monitoring_result_id → monitoring_results.result_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| exception_id | INTEGER | No | Yes |  |  |  |
| exception_code | VARCHAR(16) | No |  |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| exception_type | VARCHAR(50) | No |  |  |  | UNMITIGATED_PERFORMANCE | OUTSIDE_INTENDED_PURPOSE | USE_PRIOR_TO_VALIDATION |
| monitoring_result_id | INTEGER | Yes |  | monitoring_results.result_id |  |  |
| attestation_response_id | INTEGER | Yes |  | attestation_responses.response_id |  |  |
| deployment_task_id | INTEGER | Yes |  | version_deployment_tasks.task_id |  |  |
| status | VARCHAR(20) | No |  |  | OPEN |  |
| description | TEXT | No |  |  |  |  |
| detected_at | DATETIME | No |  |  | <function utc_now at 0x1079c71a0> |  |
| auto_closed | BOOLEAN | No |  |  | False | True if closed automatically by system, False if closed manually by Admin |
| acknowledged_by_id | INTEGER | Yes |  | users.user_id |  |  |
| acknowledged_at | DATETIME | Yes |  |  |  |  |
| acknowledgment_notes | TEXT | Yes |  |  |  |  |
| closed_at | DATETIME | Yes |  |  |  |  |
| closed_by_id | INTEGER | Yes |  | users.user_id |  | NULL for auto-closed exceptions |
| closure_narrative | TEXT | Yes |  |  |  | Required when closing (min 10 chars) |
| closure_reason_id | INTEGER | Yes |  | taxonomy_values.value_id |  | FK to Exception Closure Reason taxonomy, required when closing |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1079c7880> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1079c7ce0> |  |

### `model_feed_dependencies`

- **Primary Key:** id
- **Foreign Keys:** consumer_model_id → models.model_id, dependency_type_id → taxonomy_values.value_id, feeder_model_id → models.model_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| id | INTEGER | No | Yes |  |  |  |
| feeder_model_id | INTEGER | No |  | models.model_id |  |  |
| consumer_model_id | INTEGER | No |  | models.model_id |  |  |
| dependency_type_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| description | VARCHAR(500) | Yes |  |  |  |  |
| effective_date | DATE | Yes |  |  |  |  |
| end_date | DATE | Yes |  |  |  |  |
| is_active | BOOLEAN | No |  |  | True |  |

### `model_hierarchy`

- **Primary Key:** id
- **Foreign Keys:** child_model_id → models.model_id, parent_model_id → models.model_id, relation_type_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| id | INTEGER | No | Yes |  |  |  |
| parent_model_id | INTEGER | No |  | models.model_id |  |  |
| child_model_id | INTEGER | No |  | models.model_id |  |  |
| relation_type_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| effective_date | DATE | Yes |  |  |  |  |
| end_date | DATE | Yes |  |  |  |  |
| notes | VARCHAR(500) | Yes |  |  |  |  |

### `model_limitations`

- **Primary Key:** limitation_id
- **Foreign Keys:** category_id → taxonomy_values.value_id, created_by_id → users.user_id, model_id → models.model_id, model_version_id → model_versions.version_id, recommendation_id → recommendations.recommendation_id, retired_by_id → users.user_id, validation_request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| limitation_id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  | The model this limitation applies to |
| validation_request_id | INTEGER | Yes |  | validation_requests.request_id |  | Validation request that originally identified this limitation |
| model_version_id | INTEGER | Yes |  | model_versions.version_id |  | Model version under review when limitation was discovered |
| recommendation_id | INTEGER | Yes |  | recommendations.recommendation_id |  | Linked recommendation for mitigation (optional) |
| significance | VARCHAR(20) | No |  |  |  | Critical or Non-Critical |
| category_id | INTEGER | No |  | taxonomy_values.value_id |  | Limitation category from taxonomy (Data, Implementation, Methodology, etc.) |
| description | TEXT | No |  |  |  | Narrative description of the nature of the limitation |
| impact_assessment | TEXT | No |  |  |  | Narrative assessment of the limitation's impact |
| conclusion | VARCHAR(20) | No |  |  |  | Mitigate or Accept |
| conclusion_rationale | TEXT | No |  |  |  | Explanation for the mitigate/accept decision |
| user_awareness_description | TEXT | Yes |  |  |  | How users are made aware of this limitation (required if Critical) |
| is_retired | BOOLEAN | No |  |  | False |  |
| retirement_date | DATETIME | Yes |  |  |  |  |
| retirement_reason | TEXT | Yes |  |  |  |  |
| retired_by_id | INTEGER | Yes |  | users.user_id |  |  |
| created_by_id | INTEGER | No |  | users.user_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1078c27a0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1078c2ac0> |  |

### `model_name_history`

- **Primary Key:** history_id
- **Foreign Keys:** changed_by_id → users.user_id, model_id → models.model_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| history_id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| old_name | VARCHAR(255) | No |  |  |  |  |
| new_name | VARCHAR(255) | No |  |  |  |  |
| changed_by_id | INTEGER | Yes |  | users.user_id |  |  |
| changed_at | DATETIME | No |  |  | <function utc_now at 0x1073b99e0> |  |
| change_reason | TEXT | Yes |  |  |  |  |

### `model_pending_edits`

- **Primary Key:** pending_edit_id
- **Foreign Keys:** model_id → models.model_id, requested_by_id → users.user_id, reviewed_by_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| pending_edit_id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| requested_by_id | INTEGER | No |  | users.user_id |  |  |
| requested_at | DATETIME | No |  |  | <function ModelPendingEdit.<lambda> at 0x107466020> |  |
| proposed_changes | JSON | No |  |  |  |  |
| original_values | JSON | No |  |  |  |  |
| status | VARCHAR(20) | No |  |  | pending |  |
| reviewed_by_id | INTEGER | Yes |  | users.user_id |  |  |
| reviewed_at | DATETIME | Yes |  |  |  |  |
| review_comment | TEXT | Yes |  |  |  |  |

### `model_regions`

- **Primary Key:** id
- **Foreign Keys:** model_id → models.model_id, region_id → regions.region_id, shared_model_owner_id → users.user_id, version_id → model_versions.version_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| region_id | INTEGER | No |  | regions.region_id |  |  |
| shared_model_owner_id | INTEGER | Yes |  | users.user_id |  |  |
| version_id | INTEGER | Yes |  | model_versions.version_id |  | Current active version deployed in this region |
| deployed_at | DATETIME | Yes |  |  |  | When this version was deployed to this region |
| deployment_notes | TEXT | Yes |  |  |  | Notes about this regional deployment |
| regional_risk_level | VARCHAR(20) | Yes |  |  |  |  |
| notes | TEXT | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107358a40> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107358b80> |  |

### `model_regulatory_categories`

- **Primary Key:** model_id, value_id
- **Foreign Keys:** model_id → models.model_id, value_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| model_id | INTEGER | No | Yes | models.model_id |  |  |
| value_id | INTEGER | No | Yes | taxonomy_values.value_id |  |  |

### `model_risk_assessments`

- **Primary Key:** assessment_id
- **Foreign Keys:** assessed_by_id → users.user_id, final_tier_id → taxonomy_values.value_id, model_id → models.model_id, region_id → regions.region_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| assessment_id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  | FK to models table |
| region_id | INTEGER | Yes |  | regions.region_id |  | FK to regions table. NULL = Global assessment |
| quantitative_rating | VARCHAR(10) | Yes |  |  |  | Direct quantitative rating: HIGH, MEDIUM, LOW |
| quantitative_comment | TEXT | Yes |  |  |  | Justification for quantitative rating |
| quantitative_override | VARCHAR(10) | Yes |  |  |  | Override for quantitative: HIGH, MEDIUM, LOW |
| quantitative_override_comment | TEXT | Yes |  |  |  | Justification for quantitative override |
| qualitative_calculated_score | NUMERIC(5, 2) | Yes |  |  |  | Weighted score from factor assessments (e.g., 2.30) |
| qualitative_calculated_level | VARCHAR(10) | Yes |  |  |  | Level derived from score: HIGH (>=2.1), MEDIUM (>=1.6), LOW (<1.6) |
| qualitative_override | VARCHAR(10) | Yes |  |  |  | Override for qualitative: HIGH, MEDIUM, LOW |
| qualitative_override_comment | TEXT | Yes |  |  |  | Justification for qualitative override |
| derived_risk_tier | VARCHAR(10) | Yes |  |  |  | Matrix lookup result: HIGH, MEDIUM, LOW, VERY_LOW |
| derived_risk_tier_override | VARCHAR(10) | Yes |  |  |  | Override for final tier: HIGH, MEDIUM, LOW, VERY_LOW |
| derived_risk_tier_override_comment | TEXT | Yes |  |  |  | Justification for final tier override |
| final_tier_id | INTEGER | Yes |  | taxonomy_values.value_id |  | FK to taxonomy_values for Model Risk Tier (TIER_1, TIER_2, TIER_3, TIER_4) |
| assessed_by_id | INTEGER | Yes |  | users.user_id |  | FK to users who performed the assessment |
| assessed_at | DATETIME | Yes |  |  |  | Timestamp when assessment was finalized |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10780bc40> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107830220> |  |

### `model_submission_comments`

- **Primary Key:** comment_id
- **Foreign Keys:** model_id → models.model_id, user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| comment_id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| user_id | INTEGER | No |  | users.user_id |  |  |
| comment_text | TEXT | No |  |  |  |  |
| action_taken | VARCHAR(50) | Yes |  |  |  | Action: submitted, sent_back, resubmitted, approved, rejected |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1073b8680> |  |

### `model_type_categories`

- **Primary Key:** category_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| category_id | INTEGER | No | Yes |  |  |  |
| name | VARCHAR(100) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |

### `model_types`

- **Primary Key:** type_id
- **Foreign Keys:** category_id → model_type_categories.category_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| type_id | INTEGER | No | Yes |  |  |  |
| category_id | INTEGER | No |  | model_type_categories.category_id |  |  |
| name | VARCHAR(200) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |

### `model_users`

- **Primary Key:** model_id, user_id
- **Foreign Keys:** model_id → models.model_id, user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| model_id | INTEGER | No | Yes | models.model_id |  |  |
| user_id | INTEGER | No | Yes | users.user_id |  |  |

### `model_version_regions`

- **Primary Key:** id
- **Foreign Keys:** region_id → regions.region_id, version_id → model_versions.version_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| id | INTEGER | No | Yes |  |  |  |
| version_id | INTEGER | No |  | model_versions.version_id |  |  |
| region_id | INTEGER | No |  | regions.region_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10738ce00> |  |

### `model_versions`

- **Primary Key:** version_id
- **Foreign Keys:** change_type_id → model_change_types.change_type_id, created_by_id → users.user_id, model_id → models.model_id, validation_request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| version_id | INTEGER | No | Yes |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| version_number | VARCHAR(50) | No |  |  |  |  |
| change_type | VARCHAR(20) | No |  |  |  |  |
| change_type_id | INTEGER | Yes |  | model_change_types.change_type_id |  |  |
| change_description | TEXT | No |  |  |  |  |
| created_by_id | INTEGER | No |  | users.user_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10735a520> |  |
| change_requires_mv_approval | BOOLEAN | Yes |  |  |  | Point-in-time snapshot: Did this change require MV approval at submission time? |
| scope | VARCHAR(20) | No |  |  | GLOBAL |  |
| planned_production_date | DATE | Yes |  |  |  | Planned/target production date |
| actual_production_date | DATE | Yes |  |  |  | Actual date when deployed to production |
| production_date | DATE | Yes |  |  |  | Legacy field - prefer planned/actual; maps to planned_production_date |
| status | VARCHAR(20) | No |  |  | DRAFT |  |
| validation_request_id | INTEGER | Yes |  | validation_requests.request_id |  |  |

### `models`

- **Primary Key:** model_id
- **Foreign Keys:** developer_id → users.user_id, methodology_id → methodologies.methodology_id, model_type_id → model_types.type_id, monitoring_manager_id → users.user_id, mrsa_risk_level_id → taxonomy_values.value_id, owner_id → users.user_id, ownership_type_id → taxonomy_values.value_id, risk_tier_id → taxonomy_values.value_id, shared_developer_id → users.user_id, shared_owner_id → users.user_id, status_id → taxonomy_values.value_id, submitted_by_user_id → users.user_id, usage_frequency_id → taxonomy_values.value_id, validation_type_id → taxonomy_values.value_id, vendor_id → vendors.vendor_id, wholly_owned_region_id → regions.region_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| model_id | INTEGER | No | Yes |  |  |  |
| model_name | VARCHAR(255) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| development_type | VARCHAR(50) | No |  |  | DevelopmentType.IN_HOUSE |  |
| owner_id | INTEGER | No |  | users.user_id |  |  |
| developer_id | INTEGER | Yes |  | users.user_id |  |  |
| shared_owner_id | INTEGER | Yes |  | users.user_id |  | Optional co-owner for shared ownership scenarios |
| shared_developer_id | INTEGER | Yes |  | users.user_id |  | Optional co-developer for shared development scenarios |
| monitoring_manager_id | INTEGER | Yes |  | users.user_id |  | User responsible for ongoing model monitoring |
| vendor_id | INTEGER | Yes |  | vendors.vendor_id |  |  |
| status | VARCHAR(50) | No |  |  | ModelStatus.IN_DEVELOPMENT |  |
| risk_tier_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| validation_type_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| model_type_id | INTEGER | Yes |  | model_types.type_id |  |  |
| methodology_id | INTEGER | Yes |  | methodologies.methodology_id |  |  |
| ownership_type_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| usage_frequency_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| status_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| wholly_owned_region_id | INTEGER | Yes |  | regions.region_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1072aae80> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1072d40e0> |  |
| row_approval_status | VARCHAR(20) | Yes |  |  |  | Status of this record in the approval workflow: Draft, needs_revision, rejected, or NULL (approved) |
| submitted_by_user_id | INTEGER | Yes |  | users.user_id |  | User who submitted this model for approval |
| submitted_at | DATETIME | Yes |  |  |  | Timestamp when model was first submitted |
| use_approval_date | DATETIME | Yes |  |  |  | Timestamp when model was approved for use (last required approval granted) |
| is_model | BOOLEAN | No |  |  | True | True for actual models, False for non-model tools/applications |
| is_mrsa | BOOLEAN | No |  |  | False | True for Model Risk-Sensitive Applications (non-models requiring oversight) |
| mrsa_risk_level_id | INTEGER | Yes |  | taxonomy_values.value_id |  | MRSA risk classification (High-Risk or Low-Risk) |
| mrsa_risk_rationale | TEXT | Yes |  |  |  | Narrative explaining the MRSA risk level assignment |

### `monitoring_cycle_approvals`

- **Primary Key:** approval_id
- **Foreign Keys:** approver_id → users.user_id, cycle_id → monitoring_cycles.cycle_id, region_id → regions.region_id, represented_region_id → regions.region_id, voided_by_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| approval_id | INTEGER | No | Yes |  |  |  |
| cycle_id | INTEGER | No |  | monitoring_cycles.cycle_id |  |  |
| approver_id | INTEGER | Yes |  | users.user_id |  |  |
| approval_type | VARCHAR(20) | No |  |  | Global |  |
| region_id | INTEGER | Yes |  | regions.region_id |  |  |
| represented_region_id | INTEGER | Yes |  | regions.region_id |  |  |
| is_required | BOOLEAN | No |  |  | True |  |
| approval_status | VARCHAR(50) | No |  |  | Pending |  |
| comments | TEXT | Yes |  |  |  |  |
| approved_at | DATETIME | Yes |  |  |  |  |
| approval_evidence | TEXT | Yes |  |  |  | Evidence description for Admin proxy approvals (meeting minutes, email, etc.) |
| voided_by_id | INTEGER | Yes |  | users.user_id |  |  |
| void_reason | TEXT | Yes |  |  |  |  |
| voided_at | DATETIME | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10770fb00> |  |

### `monitoring_cycles`

- **Primary Key:** cycle_id
- **Foreign Keys:** assigned_to_user_id → users.user_id, completed_by_user_id → users.user_id, plan_id → monitoring_plans.plan_id, plan_version_id → monitoring_plan_versions.version_id, submitted_by_user_id → users.user_id, version_locked_by_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| cycle_id | INTEGER | No | Yes |  |  |  |
| plan_id | INTEGER | No |  | monitoring_plans.plan_id |  |  |
| period_start_date | DATE | No |  |  |  |  |
| period_end_date | DATE | No |  |  |  |  |
| submission_due_date | DATE | No |  |  |  |  |
| report_due_date | DATE | No |  |  |  |  |
| status | VARCHAR(50) | No |  |  | PENDING |  |
| assigned_to_user_id | INTEGER | Yes |  | users.user_id |  |  |
| submitted_at | DATETIME | Yes |  |  |  |  |
| submitted_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| completed_at | DATETIME | Yes |  |  |  |  |
| completed_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| notes | TEXT | Yes |  |  |  |  |
| report_url | VARCHAR(500) | Yes |  |  |  | URL to the final monitoring report document for approvers to review |
| plan_version_id | INTEGER | Yes |  | monitoring_plan_versions.version_id |  | Version of monitoring plan this cycle is bound to (locked at DATA_COLLECTION start) |
| version_locked_at | DATETIME | Yes |  |  |  | When the version was locked for this cycle |
| version_locked_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1076e3c40> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10770d120> |  |

### `monitoring_plan_metric_snapshots`

- **Primary Key:** snapshot_id
- **Foreign Keys:** kpm_id → kpms.kpm_id, version_id → monitoring_plan_versions.version_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| snapshot_id | INTEGER | No | Yes |  |  |  |
| version_id | INTEGER | No |  | monitoring_plan_versions.version_id |  |  |
| original_metric_id | INTEGER | Yes |  |  |  |  |
| kpm_id | INTEGER | No |  | kpms.kpm_id |  |  |
| yellow_min | FLOAT | Yes |  |  |  |  |
| yellow_max | FLOAT | Yes |  |  |  |  |
| red_min | FLOAT | Yes |  |  |  |  |
| red_max | FLOAT | Yes |  |  |  |  |
| qualitative_guidance | TEXT | Yes |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |
| kpm_name | VARCHAR(200) | No |  |  |  |  |
| kpm_category_name | VARCHAR(200) | Yes |  |  |  |  |
| evaluation_type | VARCHAR(50) | No |  |  | Quantitative |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1076e1ee0> |  |

### `monitoring_plan_metrics`

- **Primary Key:** metric_id
- **Foreign Keys:** kpm_id → kpms.kpm_id, plan_id → monitoring_plans.plan_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| metric_id | INTEGER | No | Yes |  |  |  |
| plan_id | INTEGER | No |  | monitoring_plans.plan_id |  |  |
| kpm_id | INTEGER | No |  | kpms.kpm_id |  |  |
| yellow_min | FLOAT | Yes |  |  |  | Minimum value for yellow/warning status |
| yellow_max | FLOAT | Yes |  |  |  | Maximum value for yellow/warning status |
| red_min | FLOAT | Yes |  |  |  | Minimum value for red/critical status |
| red_max | FLOAT | Yes |  |  |  | Maximum value for red/critical status |
| qualitative_guidance | TEXT | Yes |  |  |  | Qualitative guidance for interpreting this metric in the plan context |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |

### `monitoring_plan_model_snapshots`

- **Primary Key:** snapshot_id
- **Foreign Keys:** model_id → models.model_id, version_id → monitoring_plan_versions.version_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| snapshot_id | INTEGER | No | Yes |  |  |  |
| version_id | INTEGER | No |  | monitoring_plan_versions.version_id |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| model_name | VARCHAR(255) | No |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1076e3560> |  |

### `monitoring_plan_models`

- **Primary Key:** plan_id, model_id
- **Foreign Keys:** model_id → models.model_id, plan_id → monitoring_plans.plan_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| plan_id | INTEGER | No | Yes | monitoring_plans.plan_id |  |  |
| model_id | INTEGER | No | Yes | models.model_id |  |  |

### `monitoring_plan_versions`

- **Primary Key:** version_id
- **Foreign Keys:** plan_id → monitoring_plans.plan_id, published_by_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| version_id | INTEGER | No | Yes |  |  |  |
| plan_id | INTEGER | No |  | monitoring_plans.plan_id |  |  |
| version_number | INTEGER | No |  |  |  |  |
| version_name | VARCHAR(200) | Yes |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| effective_date | DATE | No |  |  |  |  |
| published_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| published_at | DATETIME | No |  |  | <function utc_now at 0x1076bff60> |  |
| is_active | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1076e0400> |  |

### `monitoring_plans`

- **Primary Key:** plan_id
- **Foreign Keys:** data_provider_user_id → users.user_id, monitoring_team_id → monitoring_teams.team_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| plan_id | INTEGER | No | Yes |  |  |  |
| name | VARCHAR(255) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| frequency | VARCHAR(50) | No |  |  | MonitoringFrequency.QUARTERLY |  |
| monitoring_team_id | INTEGER | Yes |  | monitoring_teams.team_id |  |  |
| data_provider_user_id | INTEGER | Yes |  | users.user_id |  |  |
| reporting_lead_days | INTEGER | No |  |  | 30 | Days between data submission due date and report due date |
| next_submission_due_date | DATE | Yes |  |  |  | Next due date for data submission |
| next_report_due_date | DATE | Yes |  |  |  | Next due date for monitoring report |
| is_active | BOOLEAN | No |  |  | True |  |
| is_dirty | BOOLEAN | No |  |  | False | True when metrics or models have been changed since last version publish |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1076bccc0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1076bcd60> |  |

### `monitoring_results`

- **Primary Key:** result_id
- **Foreign Keys:** cycle_id → monitoring_cycles.cycle_id, entered_by_user_id → users.user_id, model_id → models.model_id, outcome_value_id → taxonomy_values.value_id, plan_metric_id → monitoring_plan_metrics.metric_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| result_id | INTEGER | No | Yes |  |  |  |
| cycle_id | INTEGER | No |  | monitoring_cycles.cycle_id |  |  |
| plan_metric_id | INTEGER | No |  | monitoring_plan_metrics.metric_id |  |  |
| model_id | INTEGER | Yes |  | models.model_id |  |  |
| numeric_value | FLOAT | Yes |  |  |  |  |
| outcome_value_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| calculated_outcome | VARCHAR(20) | Yes |  |  |  |  |
| narrative | TEXT | Yes |  |  |  |  |
| supporting_data | JSON | Yes |  |  |  |  |
| entered_by_user_id | INTEGER | No |  | users.user_id |  |  |
| entered_at | DATETIME | No |  |  | <function utc_now at 0x107739800> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107739ee0> |  |

### `monitoring_team_members`

- **Primary Key:** team_id, user_id
- **Foreign Keys:** team_id → monitoring_teams.team_id, user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| team_id | INTEGER | No | Yes | monitoring_teams.team_id |  |  |
| user_id | INTEGER | No | Yes | users.user_id |  |  |

### `monitoring_teams`

- **Primary Key:** team_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| team_id | INTEGER | No | Yes |  |  |  |
| name | VARCHAR(200) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| is_active | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10768b740> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10768b7e0> |  |

### `mrsa_irp`

- **Primary Key:** model_id, irp_id
- **Foreign Keys:** irp_id → irps.irp_id, model_id → models.model_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| model_id | INTEGER | No | Yes | models.model_id |  |  |
| irp_id | INTEGER | No | Yes | irps.irp_id |  |  |

### `mrsa_review_exceptions`

- **Primary Key:** exception_id
- **Foreign Keys:** approved_by_id → users.user_id, mrsa_id → models.model_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| exception_id | INTEGER | No | Yes |  |  |  |
| mrsa_id | INTEGER | No |  | models.model_id |  | MRSA model receiving the exception |
| override_due_date | DATE | No |  |  |  | Extended review due date |
| reason | TEXT | No |  |  |  | Justification for granting the exception |
| approved_by_id | INTEGER | No |  | users.user_id |  | Administrator who approved the exception |
| approved_at | DATETIME | No |  |  | <function utc_now at 0x107916a20> | Timestamp when exception was approved |
| is_active | BOOLEAN | No |  |  | True | Whether this exception is currently active |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107916e80> |  |

### `mrsa_review_policies`

- **Primary Key:** policy_id
- **Foreign Keys:** mrsa_risk_level_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| policy_id | INTEGER | No | Yes |  |  |  |
| mrsa_risk_level_id | INTEGER | No |  | taxonomy_values.value_id |  | MRSA Risk Level taxonomy value (High-Risk or Low-Risk) |
| frequency_months | INTEGER | No |  |  | 24 | Review frequency in months (default: 24 months / 2 years) |
| initial_review_months | INTEGER | No |  |  | 3 | Initial review due within N months of MRSA designation |
| warning_days | INTEGER | No |  |  | 90 | Number of days before due date to trigger warning alerts |
| is_active | BOOLEAN | No |  |  | True | Whether this policy is currently active |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107915940> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1079159e0> |  |

### `overdue_revalidation_comments`

- **Primary Key:** comment_id
- **Foreign Keys:** created_by_user_id → users.user_id, superseded_by_comment_id → overdue_revalidation_comments.comment_id, validation_request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| comment_id | INTEGER | No | Yes |  |  |  |
| validation_request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| overdue_type | VARCHAR(30) | No |  |  |  | PRE_SUBMISSION or VALIDATION_IN_PROGRESS |
| reason_comment | TEXT | No |  |  |  | Explanation for the overdue status |
| target_date | DATE | No |  |  |  | Target Submission Date (PRE_SUBMISSION) or Target Completion Date (VALIDATION_IN_PROGRESS) |
| created_by_user_id | INTEGER | No |  | users.user_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107639800> |  |
| is_current | BOOLEAN | No |  |  | True |  |
| superseded_at | DATETIME | Yes |  |  |  |  |
| superseded_by_comment_id | INTEGER | Yes |  | overdue_revalidation_comments.comment_id |  |  |

### `qualitative_factor_assessments`

- **Primary Key:** factor_assessment_id
- **Foreign Keys:** assessment_id → model_risk_assessments.assessment_id, factor_id → qualitative_risk_factors.factor_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| factor_assessment_id | INTEGER | No | Yes |  |  |  |
| assessment_id | INTEGER | No |  | model_risk_assessments.assessment_id |  | FK to model_risk_assessments |
| factor_id | INTEGER | No |  | qualitative_risk_factors.factor_id |  | FK to qualitative_risk_factors |
| rating | VARCHAR(10) | Yes |  |  |  | Rating for this factor: HIGH, MEDIUM, LOW (nullable for partial saves) |
| comment | TEXT | Yes |  |  |  | Optional justification for this factor rating |
| weight_at_assessment | NUMERIC(5, 4) | No |  |  |  | Snapshot of factor weight at time of assessment |
| score | NUMERIC(5, 2) | Yes |  |  |  | Calculated score: weight * points (e.g., 0.30 * 3 = 0.90) |

### `qualitative_factor_guidance`

- **Primary Key:** guidance_id
- **Foreign Keys:** factor_id → qualitative_risk_factors.factor_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| guidance_id | INTEGER | No | Yes |  |  |  |
| factor_id | INTEGER | No |  | qualitative_risk_factors.factor_id |  | FK to qualitative_risk_factors |
| rating | VARCHAR(10) | No |  |  |  | Rating level: HIGH, MEDIUM, or LOW |
| points | INTEGER | No |  |  |  | Points for this rating: 3 (HIGH), 2 (MEDIUM), 1 (LOW) |
| description | TEXT | No |  |  |  | Guidance text explaining when this rating applies |
| sort_order | INTEGER | No |  |  | 0 | Display order within the factor |

### `qualitative_risk_factors`

- **Primary Key:** factor_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| factor_id | INTEGER | No | Yes |  |  |  |
| code | VARCHAR(50) | No |  |  |  | Unique code identifier (e.g., REPUTATION_LEGAL) |
| name | VARCHAR(200) | No |  |  |  | Display name for the factor |
| description | TEXT | Yes |  |  |  | Full description of what this factor measures |
| weight | NUMERIC(5, 4) | No |  |  |  | Weight for weighted average calculation (e.g., 0.3000 for 30%) |
| sort_order | INTEGER | No |  |  | 0 | Display order in the assessment form |
| is_active | BOOLEAN | No |  |  | True | Active factors appear in new assessments |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1078099e0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107809a80> |  |

### `recommendation_approvals`

- **Primary Key:** approval_id
- **Foreign Keys:** approver_id → users.user_id, recommendation_id → recommendations.recommendation_id, region_id → regions.region_id, represented_region_id → regions.region_id, voided_by_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| approval_id | INTEGER | No | Yes |  |  |  |
| recommendation_id | INTEGER | No |  | recommendations.recommendation_id |  |  |
| approval_type | VARCHAR(20) | No |  |  |  | 'GLOBAL' or 'REGIONAL' |
| region_id | INTEGER | Yes |  | regions.region_id |  | Required if approval_type='REGIONAL', NULL for GLOBAL |
| represented_region_id | INTEGER | Yes |  | regions.region_id |  | Region the approver was representing at approval time (NULL for Global Approver) |
| approver_id | INTEGER | Yes |  | users.user_id |  |  |
| approved_at | DATETIME | Yes |  |  |  |  |
| is_required | BOOLEAN | No |  |  | True |  |
| approval_status | VARCHAR(20) | No |  |  | PENDING | PENDING, APPROVED, REJECTED, VOIDED |
| comments | TEXT | Yes |  |  |  |  |
| approval_evidence | TEXT | Yes |  |  |  | Description of approval evidence (meeting minutes, email, etc.) - required for Admin proxy approvals |
| voided_by_id | INTEGER | Yes |  | users.user_id |  |  |
| void_reason | TEXT | Yes |  |  |  |  |
| voided_at | DATETIME | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1077b71a0> |  |

### `recommendation_priority_configs`

- **Primary Key:** config_id
- **Foreign Keys:** priority_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| config_id | INTEGER | No | Yes |  |  |  |
| priority_id | INTEGER | No |  | taxonomy_values.value_id |  | FK to priority taxonomy value (High/Medium/Low/Consideration) |
| requires_final_approval | BOOLEAN | No |  |  | True | If true, closure requires Global + Regional approvals after Validator approval |
| requires_action_plan | BOOLEAN | No |  |  | True | If false, recommendations with this priority can skip action plan submission |
| enforce_timeframes | BOOLEAN | No |  |  | True | If true, target dates must be within max allowed timeframe; if false, timeframe is advisory only |
| description | TEXT | Yes |  |  |  | Admin notes explaining the configuration |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1077e5440> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1077e54e0> |  |

### `recommendation_priority_regional_overrides`

- **Primary Key:** override_id
- **Foreign Keys:** priority_id → taxonomy_values.value_id, region_id → regions.region_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| override_id | INTEGER | No | Yes |  |  |  |
| priority_id | INTEGER | No |  | taxonomy_values.value_id |  | FK to priority taxonomy value (High/Medium/Low/Consideration) |
| region_id | INTEGER | No |  | regions.region_id |  | FK to region for this override |
| requires_action_plan | BOOLEAN | Yes |  |  |  | Override for action plan requirement. NULL = inherit from base config |
| requires_final_approval | BOOLEAN | Yes |  |  |  | Override for final approval requirement. NULL = inherit from base config |
| enforce_timeframes | BOOLEAN | Yes |  |  |  | Override for timeframe enforcement. NULL = inherit from base config |
| description | TEXT | Yes |  |  |  | Admin notes explaining why this regional override exists |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1077e6520> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1077e6c00> |  |

### `recommendation_rebuttals`

- **Primary Key:** rebuttal_id
- **Foreign Keys:** recommendation_id → recommendations.recommendation_id, reviewed_by_id → users.user_id, submitted_by_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| rebuttal_id | INTEGER | No | Yes |  |  |  |
| recommendation_id | INTEGER | No |  | recommendations.recommendation_id |  |  |
| submitted_by_id | INTEGER | No |  | users.user_id |  |  |
| rationale | TEXT | No |  |  |  |  |
| supporting_evidence | TEXT | Yes |  |  |  |  |
| submitted_at | DATETIME | No |  |  | <function utc_now at 0x1077920c0> |  |
| reviewed_by_id | INTEGER | Yes |  | users.user_id |  |  |
| reviewed_at | DATETIME | Yes |  |  |  |  |
| review_decision | VARCHAR(20) | Yes |  |  |  | ACCEPT (issue dropped) or OVERRIDE (action plan required) |
| review_comments | TEXT | Yes |  |  |  |  |
| is_current | BOOLEAN | No |  |  | True |  |

### `recommendation_status_history`

- **Primary Key:** history_id
- **Foreign Keys:** changed_by_id → users.user_id, new_status_id → taxonomy_values.value_id, old_status_id → taxonomy_values.value_id, recommendation_id → recommendations.recommendation_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| history_id | INTEGER | No | Yes |  |  |  |
| recommendation_id | INTEGER | No |  | recommendations.recommendation_id |  |  |
| old_status_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| new_status_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| changed_by_id | INTEGER | No |  | users.user_id |  |  |
| changed_at | DATETIME | No |  |  | <function utc_now at 0x1077b5120> |  |
| change_reason | TEXT | Yes |  |  |  |  |
| additional_context | TEXT | Yes |  |  |  | JSON storing action-specific details |

### `recommendation_timeframe_configs`

- **Primary Key:** config_id
- **Foreign Keys:** priority_id → taxonomy_values.value_id, risk_tier_id → taxonomy_values.value_id, usage_frequency_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| config_id | INTEGER | No | Yes |  |  |  |
| priority_id | INTEGER | No |  | taxonomy_values.value_id |  | FK to priority taxonomy value (High/Medium/Low) |
| risk_tier_id | INTEGER | No |  | taxonomy_values.value_id |  | FK to model risk tier taxonomy value (Tier 1/2/3/4) |
| usage_frequency_id | INTEGER | No |  | taxonomy_values.value_id |  | FK to model usage frequency taxonomy value (Daily/Monthly/Quarterly/Annually) |
| max_days | INTEGER | No |  |  |  | Maximum days allowed from creation to target date (0 = immediate) |
| description | TEXT | Yes |  |  |  | Admin notes explaining this timeframe configuration |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1077e7ec0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107808360> |  |

### `recommendations`

- **Primary Key:** recommendation_id
- **Foreign Keys:** acknowledged_by_id → users.user_id, assigned_to_id → users.user_id, category_id → taxonomy_values.value_id, closed_by_id → users.user_id, created_by_id → users.user_id, current_status_id → taxonomy_values.value_id, finalized_by_id → users.user_id, model_id → models.model_id, monitoring_cycle_id → monitoring_cycles.cycle_id, plan_metric_id → monitoring_plan_metrics.metric_id, priority_id → taxonomy_values.value_id, validation_request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| recommendation_id | INTEGER | No | Yes |  |  |  |
| recommendation_code | VARCHAR(20) | No |  |  |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| validation_request_id | INTEGER | Yes |  | validation_requests.request_id |  | Link to originating validation (if applicable) |
| monitoring_cycle_id | INTEGER | Yes |  | monitoring_cycles.cycle_id |  | Link to originating monitoring cycle (if applicable) |
| plan_metric_id | INTEGER | Yes |  | monitoring_plan_metrics.metric_id |  | Link to specific metric that triggered this recommendation (if applicable) |
| title | VARCHAR(500) | No |  |  |  |  |
| description | TEXT | No |  |  |  |  |
| root_cause_analysis | TEXT | Yes |  |  |  |  |
| priority_id | INTEGER | No |  | taxonomy_values.value_id |  | High/Medium/Low - determines closure approval requirements |
| category_id | INTEGER | Yes |  | taxonomy_values.value_id |  | e.g., Data Quality, Methodology, Implementation, Documentation |
| current_status_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| created_by_id | INTEGER | No |  | users.user_id |  | Validator who identified the issue |
| assigned_to_id | INTEGER | No |  | users.user_id |  | Developer/Owner responsible for remediation |
| original_target_date | DATE | No |  |  |  |  |
| current_target_date | DATE | No |  |  |  |  |
| target_date_change_reason | TEXT | Yes |  |  |  | Explanation for why target date differs from calculated max or has been changed |
| closed_at | DATETIME | Yes |  |  |  |  |
| closed_by_id | INTEGER | Yes |  | users.user_id |  |  |
| closure_summary | TEXT | Yes |  |  |  |  |
| finalized_at | DATETIME | Yes |  |  |  |  |
| finalized_by_id | INTEGER | Yes |  | users.user_id |  |  |
| acknowledged_at | DATETIME | Yes |  |  |  |  |
| acknowledged_by_id | INTEGER | Yes |  | users.user_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10773bce0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107760cc0> |  |

### `regions`

- **Primary Key:** region_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| region_id | INTEGER | No | Yes |  |  |  |
| code | VARCHAR(10) | No |  |  |  |  |
| name | VARCHAR(100) | No |  |  |  |  |
| requires_regional_approval | BOOLEAN | No |  |  | false |  |
| enforce_validation_plan | BOOLEAN | No |  |  | false | When true, validation plans are required for requests scoped to this region |
| requires_standalone_rating | BOOLEAN | No |  |  | false | When true, models deployed to this region require a region-specific risk assessment |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10733b560> |  |

### `residual_risk_map_configs`

- **Primary Key:** config_id
- **Foreign Keys:** created_by_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| config_id | INTEGER | No | Yes |  |  |  |
| version_number | INTEGER | No |  |  | 1 | Sequential version number for tracking changes |
| version_name | VARCHAR(200) | Yes |  |  |  | Optional display name for this version |
| matrix_config | JSON | No |  |  |  | The residual risk matrix configuration |
| description | TEXT | Yes |  |  |  | Description or changelog for this version |
| is_active | BOOLEAN | No |  |  | True | Only one configuration should be active at a time |
| created_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1078c0e00> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1078c0fe0> |  |

### `rule_required_approvers`

- **Primary Key:** id
- **Foreign Keys:** approver_role_id → approver_roles.role_id, rule_id → conditional_approval_rules.rule_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| id | INTEGER | No | Yes |  |  |  |
| rule_id | INTEGER | No |  | conditional_approval_rules.rule_id |  |  |
| approver_role_id | INTEGER | No |  | approver_roles.role_id |  |  |

### `scorecard_config_versions`

- **Primary Key:** version_id
- **Foreign Keys:** published_by_user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| version_id | INTEGER | No | Yes |  |  |  |
| version_number | INTEGER | No |  |  |  | Sequential version number (1, 2, 3...) |
| version_name | VARCHAR(200) | Yes |  |  |  | Optional display name (e.g., 'Q4 2025 Updates') |
| description | TEXT | Yes |  |  |  | Changelog or notes for this version |
| published_by_user_id | INTEGER | Yes |  | users.user_id |  |  |
| published_at | DATETIME | No |  |  | <function utc_now at 0x107890900> |  |
| is_active | BOOLEAN | No |  |  | True | Only one version should be active at a time |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107890c20> |  |

### `scorecard_criteria`

- **Primary Key:** criterion_id
- **Foreign Keys:** section_id → scorecard_sections.section_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| criterion_id | INTEGER | No | Yes |  |  |  |
| code | VARCHAR(20) | No |  |  |  | Criterion code (e.g., '1.1', '2.3', '3.5') |
| section_id | INTEGER | No |  | scorecard_sections.section_id |  | FK to parent section |
| name | VARCHAR(255) | No |  |  |  | Display name (e.g., 'Model Development Documentation') |
| description_prompt | TEXT | Yes |  |  |  | Prompt guiding validator's description entry |
| comments_prompt | TEXT | Yes |  |  |  | Prompt guiding validator's comments entry |
| include_in_summary | BOOLEAN | No |  |  | True | Whether to include in section summary calculation |
| allow_zero | BOOLEAN | No |  |  | True | Whether N/A rating is allowed for this criterion |
| weight | NUMERIC(5, 2) | No |  |  | 1.0 | Weight for weighted average calculation |
| sort_order | INTEGER | No |  |  | 0 | Display order within section |
| is_active | BOOLEAN | No |  |  | True | Inactive criteria are hidden from new scorecards |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10785cd60> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10785ce00> |  |

### `scorecard_criterion_snapshots`

- **Primary Key:** snapshot_id
- **Foreign Keys:** version_id → scorecard_config_versions.version_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| snapshot_id | INTEGER | No | Yes |  |  |  |
| version_id | INTEGER | No |  | scorecard_config_versions.version_id |  |  |
| original_criterion_id | INTEGER | Yes |  |  |  | Reference to original criterion (may be deleted) |
| section_code | VARCHAR(20) | No |  |  |  | Parent section code (not FK - for resilience) |
| code | VARCHAR(20) | No |  |  |  | Criterion code at time of snapshot |
| name | VARCHAR(255) | No |  |  |  |  |
| description_prompt | TEXT | Yes |  |  |  |  |
| comments_prompt | TEXT | Yes |  |  |  |  |
| include_in_summary | BOOLEAN | No |  |  | True |  |
| allow_zero | BOOLEAN | No |  |  | True |  |
| weight | NUMERIC(5, 2) | No |  |  | 1.0 | Weight as configured at snapshot time |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1078937e0> |  |

### `scorecard_section_snapshots`

- **Primary Key:** snapshot_id
- **Foreign Keys:** version_id → scorecard_config_versions.version_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| snapshot_id | INTEGER | No | Yes |  |  |  |
| version_id | INTEGER | No |  | scorecard_config_versions.version_id |  |  |
| original_section_id | INTEGER | Yes |  |  |  | Reference to original section (may be deleted) |
| code | VARCHAR(20) | No |  |  |  | Section code at time of snapshot |
| name | VARCHAR(255) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107892200> |  |

### `scorecard_sections`

- **Primary Key:** section_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| section_id | INTEGER | No | Yes |  |  |  |
| code | VARCHAR(20) | No |  |  |  | Section code (e.g., '1', '2', '3') |
| name | VARCHAR(255) | No |  |  |  | Display name (e.g., 'Evaluation of Conceptual Soundness') |
| description | TEXT | Yes |  |  |  | Optional description of this section |
| sort_order | INTEGER | No |  |  | 0 | Display order in UI |
| is_active | BOOLEAN | No |  |  | True | Inactive sections are hidden from new scorecards |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1078337e0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107833880> |  |

### `taxonomies`

- **Primary Key:** taxonomy_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| taxonomy_id | INTEGER | No | Yes |  |  |  |
| name | VARCHAR(100) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| is_system | BOOLEAN | No |  |  | False |  |
| taxonomy_type | VARCHAR(20) | No |  |  | standard | Type of taxonomy: 'standard' or 'bucket' (range-based) |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10730f920> |  |

### `taxonomy_values`

- **Primary Key:** value_id
- **Foreign Keys:** taxonomy_id → taxonomies.taxonomy_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| value_id | INTEGER | No | Yes |  |  |  |
| taxonomy_id | INTEGER | No |  | taxonomies.taxonomy_id |  |  |
| code | VARCHAR(50) | No |  |  |  |  |
| label | VARCHAR(255) | No |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |
| min_days | INTEGER | Yes |  |  |  | Minimum days (inclusive) for bucket. NULL means unbounded (negative infinity). |
| max_days | INTEGER | Yes |  |  |  | Maximum days (inclusive) for bucket. NULL means unbounded (positive infinity). |
| downgrade_notches | INTEGER | Yes |  |  |  | Number of scorecard notches to downgrade for this past-due bucket (0-5) |
| requires_irp | BOOLEAN | Yes |  |  |  | For MRSA Risk Level taxonomy: True if this risk level requires IRP coverage |
| is_system_protected | BOOLEAN | No |  |  | False | If True, this value cannot be deleted or deactivated (used for exception detection questions) |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107338cc0> |  |

### `user_regions`

- **Primary Key:** user_id, region_id
- **Foreign Keys:** region_id → regions.region_id, user_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| user_id | INTEGER | No | Yes | users.user_id |  |  |
| region_id | INTEGER | No | Yes | regions.region_id |  |  |

### `users`

- **Primary Key:** user_id
- **Foreign Keys:** lob_id → lob_units.lob_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| user_id | INTEGER | No | Yes |  |  |  |
| email | VARCHAR(255) | No |  |  |  |  |
| full_name | VARCHAR(255) | No |  |  |  |  |
| password_hash | VARCHAR(255) | No |  |  |  |  |
| role | VARCHAR(50) | No |  |  | UserRole.USER |  |
| high_fluctuation_flag | BOOLEAN | No |  |  | False | Manual toggle by Admin; triggers quarterly attestations |
| lob_id | INTEGER | No |  | lob_units.lob_id |  | User's assigned LOB unit (required) |

### `validation_approvals`

- **Primary Key:** approval_id
- **Foreign Keys:** approver_id → users.user_id, approver_role_id → approver_roles.role_id, region_id → regions.region_id, represented_region_id → regions.region_id, request_id → validation_requests.request_id, unlinked_by_id → users.user_id, voided_by_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| approval_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| approver_id | INTEGER | Yes |  | users.user_id |  |  |
| approver_role | VARCHAR(100) | No |  |  |  |  |
| approval_type | VARCHAR(20) | No |  |  | Global |  |
| region_id | INTEGER | Yes |  | regions.region_id |  |  |
| represented_region_id | INTEGER | Yes |  | regions.region_id |  | Region the approver was representing at approval time (NULL for Global Approver) |
| is_required | BOOLEAN | No |  |  | True |  |
| approval_status | VARCHAR(50) | No |  |  | Pending |  |
| comments | TEXT | Yes |  |  |  |  |
| approved_at | DATETIME | Yes |  |  |  |  |
| unlinked_by_id | INTEGER | Yes |  | users.user_id |  |  |
| unlink_reason | TEXT | Yes |  |  |  |  |
| unlinked_at | DATETIME | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107580b80> |  |
| approver_role_id | INTEGER | Yes |  | approver_roles.role_id |  | FK to approver_roles (for conditional approvals); NULL for traditional approvals |
| approval_evidence | TEXT | Yes |  |  |  | Description of approval evidence (meeting minutes, email, etc.) |
| voided_by_id | INTEGER | Yes |  | users.user_id |  |  |
| void_reason | TEXT | Yes |  |  |  | Reason why this approval requirement was voided by Admin |
| voided_at | DATETIME | Yes |  |  |  |  |

### `validation_assignments`

- **Primary Key:** assignment_id
- **Foreign Keys:** request_id → validation_requests.request_id, validator_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| assignment_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| validator_id | INTEGER | No |  | users.user_id |  |  |
| is_primary | BOOLEAN | No |  |  | False |  |
| is_reviewer | BOOLEAN | No |  |  | False |  |
| assignment_date | DATE | No |  |  | <function date.today at 0x10753e8e0> |  |
| estimated_hours | FLOAT | Yes |  |  |  |  |
| actual_hours | FLOAT | Yes |  |  | 0.0 |  |
| independence_attestation | BOOLEAN | No |  |  | False |  |
| reviewer_signed_off | BOOLEAN | No |  |  | False |  |
| reviewer_signed_off_at | DATETIME | Yes |  |  |  |  |
| reviewer_sign_off_comments | TEXT | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10753ec00> |  |

### `validation_component_definitions`

- **Primary Key:** component_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| component_id | INTEGER | No | Yes |  |  |  |
| section_number | VARCHAR(10) | No |  |  |  |  |
| section_title | VARCHAR(200) | No |  |  |  |  |
| component_code | VARCHAR(20) | No |  |  |  | Stable identifier like '1.1', '3.4' |
| component_title | VARCHAR(200) | No |  |  |  |  |
| is_test_or_analysis | BOOLEAN | No |  |  | False | True if test/analysis, False if report section |
| expectation_high | VARCHAR(20) | No |  |  | Required |  |
| expectation_medium | VARCHAR(20) | No |  |  | Required |  |
| expectation_low | VARCHAR(20) | No |  |  | Required |  |
| expectation_very_low | VARCHAR(20) | No |  |  | Required |  |
| sort_order | INTEGER | No |  |  | 0 |  |
| is_active | BOOLEAN | No |  |  | True |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1075834c0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107583560> |  |

### `validation_findings`

- **Primary Key:** finding_id
- **Foreign Keys:** identified_by_id → users.user_id, request_id → validation_requests.request_id, resolved_by_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| finding_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| finding_type | VARCHAR(50) | No |  |  |  | Category of finding: DATA_QUALITY, METHODOLOGY, IMPLEMENTATION, etc. |
| severity | VARCHAR(20) | No |  |  |  | Severity level: HIGH, MEDIUM, LOW |
| title | VARCHAR(500) | No |  |  |  |  |
| description | TEXT | No |  |  |  |  |
| status | VARCHAR(20) | No |  |  | OPEN | Finding status: OPEN or RESOLVED |
| identified_by_id | INTEGER | No |  | users.user_id |  |  |
| resolved_at | DATETIME | Yes |  |  |  |  |
| resolved_by_id | INTEGER | Yes |  | users.user_id |  |  |
| resolution_notes | TEXT | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1075defc0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1075df420> |  |

### `validation_grouping_memory`

- **Primary Key:** model_id
- **Foreign Keys:** last_validation_request_id → validation_requests.request_id, model_id → models.model_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| model_id | INTEGER | No | Yes | models.model_id |  |  |
| last_validation_request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| grouped_model_ids | TEXT | No |  |  |  |  |
| is_regular_validation | BOOLEAN | No |  |  | True |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107604f40> |  |

### `validation_outcomes`

- **Primary Key:** outcome_id
- **Foreign Keys:** overall_rating_id → taxonomy_values.value_id, request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| outcome_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| overall_rating_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| executive_summary | TEXT | No |  |  |  |  |
| effective_date | DATE | No |  |  |  |  |
| expiration_date | DATE | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10755d800> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10755db20> |  |

### `validation_plan_components`

- **Primary Key:** plan_component_id
- **Foreign Keys:** component_id → validation_component_definitions.component_id, monitoring_plan_version_id → monitoring_plan_versions.version_id, plan_id → validation_plans.plan_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| plan_component_id | INTEGER | No | Yes |  |  |  |
| plan_id | INTEGER | No |  | validation_plans.plan_id |  |  |
| component_id | INTEGER | No |  | validation_component_definitions.component_id |  |  |
| default_expectation | VARCHAR(20) | No |  |  |  | Required, IfApplicable, or NotExpected |
| planned_treatment | VARCHAR(20) | No |  |  | Planned | Planned, NotPlanned, or NotApplicable |
| is_deviation | BOOLEAN | No |  |  | False |  |
| rationale | TEXT | Yes |  |  |  |  |
| additional_notes | TEXT | Yes |  |  |  |  |
| monitoring_plan_version_id | INTEGER | Yes |  | monitoring_plan_versions.version_id |  | For component 9b: which monitoring plan version was reviewed |
| monitoring_review_notes | TEXT | Yes |  |  |  | For component 9b: notes about the monitoring plan review |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1075bea20> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1075bec00> |  |

### `validation_plans`

- **Primary Key:** plan_id
- **Foreign Keys:** config_id → component_definition_configurations.config_id, locked_by_user_id → users.user_id, request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| plan_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| overall_scope_summary | TEXT | Yes |  |  |  |  |
| material_deviation_from_standard | BOOLEAN | No |  |  | False |  |
| overall_deviation_rationale | TEXT | Yes |  |  |  |  |
| config_id | INTEGER | Yes |  | component_definition_configurations.config_id |  | Configuration version this plan is linked to (locked when plan submitted for review) |
| locked_at | DATETIME | Yes |  |  |  | When plan was locked (moved to Review/Pending Approval) |
| locked_by_user_id | INTEGER | Yes |  | users.user_id |  | User who triggered the lock (via status transition) |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1075bccc0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1075bcfe0> |  |

### `validation_policies`

- **Primary Key:** policy_id
- **Foreign Keys:** risk_tier_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| policy_id | INTEGER | No | Yes |  |  |  |
| risk_tier_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| frequency_months | INTEGER | No |  |  | 12 |  |
| grace_period_months | INTEGER | No |  |  | 3 | Grace period in months after submission due date before item is considered overdue |
| model_change_lead_time_days | INTEGER | No |  |  | 90 | Lead time in days before model change implementation date to trigger interim validation |
| monitoring_plan_review_required | BOOLEAN | No |  |  | False | If true, component 9b (Performance Monitoring Plan Review) requires Planned or comment |
| monitoring_plan_review_description | TEXT | Yes |  |  |  |  |
| description | TEXT | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1074ed6c0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1074ed760> |  |

### `validation_request_models`

- **Primary Key:** request_id, model_id
- **Foreign Keys:** model_id → models.model_id, request_id → validation_requests.request_id, version_id → model_versions.version_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| request_id | INTEGER | No | Yes | validation_requests.request_id |  |  |
| model_id | INTEGER | No | Yes | models.model_id |  |  |
| version_id | INTEGER | Yes |  | model_versions.version_id |  |  |

### `validation_request_regions`

- **Primary Key:** request_id, region_id
- **Foreign Keys:** region_id → regions.region_id, request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| request_id | INTEGER | No | Yes | validation_requests.request_id |  |  |
| region_id | INTEGER | No | Yes | regions.region_id |  |  |

### `validation_requests`

- **Primary Key:** request_id
- **Foreign Keys:** confirmed_model_version_id → model_versions.version_id, current_status_id → taxonomy_values.value_id, declined_by_id → users.user_id, prior_full_validation_request_id → validation_requests.request_id, prior_validation_request_id → validation_requests.request_id, priority_id → taxonomy_values.value_id, requestor_id → users.user_id, validated_risk_tier_id → taxonomy_values.value_id, validation_type_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| request_id | INTEGER | No | Yes |  |  |  |
| request_date | DATE | No |  |  | <function date.today at 0x1074ef740> |  |
| requestor_id | INTEGER | No |  | users.user_id |  |  |
| validation_type_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| priority_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| target_completion_date | DATE | No |  |  |  |  |
| trigger_reason | TEXT | Yes |  |  |  |  |
| current_status_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| declined_by_id | INTEGER | Yes |  | users.user_id |  |  |
| decline_reason | TEXT | Yes |  |  |  |  |
| declined_at | DATETIME | Yes |  |  |  |  |
| prior_validation_request_id | INTEGER | Yes |  | validation_requests.request_id |  | Link to the previous validation that this revalidation follows |
| prior_full_validation_request_id | INTEGER | Yes |  | validation_requests.request_id |  | Link to the most recent INITIAL or COMPREHENSIVE validation |
| submission_due_date | DATE | Yes |  |  |  | Date by which model owner must submit documentation (locked at request creation) |
| submission_received_date | DATE | Yes |  |  |  | Date model owner actually submitted documentation |
| confirmed_model_version_id | INTEGER | Yes |  | model_versions.version_id |  | Confirmed model version at time of submission (may differ from originally associated version) |
| model_documentation_version | VARCHAR(100) | Yes |  |  |  | Version identifier for the model documentation submitted |
| model_submission_version | VARCHAR(100) | Yes |  |  |  | Version identifier for the model code/artifacts submitted |
| model_documentation_id | VARCHAR(255) | Yes |  |  |  | External ID or reference for the model documentation (e.g., document management system ID) |
| version_source | VARCHAR(20) | Yes |  |  | explicit | How version was linked: 'explicit' (user selected) or 'inferred' (system auto-suggested) |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1074ef7e0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x107510400> |  |
| completion_date | DATETIME | Yes |  |  |  | Date when validation was completed (latest approval date) |
| validated_risk_tier_id | INTEGER | Yes |  | taxonomy_values.value_id |  | Snapshot of model's risk tier at the moment of validation approval |

### `validation_review_outcomes`

- **Primary Key:** review_outcome_id
- **Foreign Keys:** request_id → validation_requests.request_id, reviewer_id → users.user_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| review_outcome_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| reviewer_id | INTEGER | No |  | users.user_id |  |  |
| decision | VARCHAR(50) | No |  |  |  |  |
| comments | TEXT | Yes |  |  |  |  |
| agrees_with_rating | BOOLEAN | Yes |  |  |  |  |
| review_date | DATETIME | No |  |  | <function utc_now at 0x10755ed40> |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10755f1a0> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10755f240> |  |

### `validation_scorecard_ratings`

- **Primary Key:** rating_id
- **Foreign Keys:** request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| rating_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  | FK to validation request |
| criterion_code | VARCHAR(20) | No |  |  |  | Criterion code (e.g., '1.1') - keyed by code for resilience |
| rating | VARCHAR(20) | Yes |  |  |  | Rating: Green, Green-, Yellow+, Yellow, Yellow-, Red, N/A, or NULL |
| description | TEXT | Yes |  |  |  | Validator's description response |
| comments | TEXT | Yes |  |  |  | Validator's comments |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10785e160> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10785e340> |  |

### `validation_scorecard_results`

- **Primary Key:** result_id
- **Foreign Keys:** config_version_id → scorecard_config_versions.version_id, request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| result_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  | FK to validation request (ONE result per request) |
| overall_numeric_score | INTEGER | Yes |  |  |  | Overall numeric score (0-6) |
| overall_rating | VARCHAR(20) | Yes |  |  |  | Overall rating string (Green, Green-, etc.) |
| overall_assessment_narrative | TEXT | Yes |  |  |  | Free-text narrative for overall scorecard assessment |
| section_summaries | JSON | Yes |  |  |  | JSON object with per-section summaries |
| config_snapshot | JSON | Yes |  |  |  | Snapshot of scorecard configuration at computation time |
| computed_at | DATETIME | No |  |  | <function utc_now at 0x10785f420> | When the scorecard was computed |
| config_version_id | INTEGER | Yes |  | scorecard_config_versions.version_id |  | FK to scorecard config version used for this scorecard |

### `validation_status_history`

- **Primary Key:** history_id
- **Foreign Keys:** changed_by_id → users.user_id, new_status_id → taxonomy_values.value_id, old_status_id → taxonomy_values.value_id, request_id → validation_requests.request_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| history_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| old_status_id | INTEGER | Yes |  | taxonomy_values.value_id |  |  |
| new_status_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| changed_by_id | INTEGER | No |  | users.user_id |  |  |
| change_reason | TEXT | Yes |  |  |  |  |
| additional_context | TEXT | Yes |  |  |  | JSON storing action-specific details (e.g., revision snapshots for send-back) |
| changed_at | DATETIME | No |  |  | <function utc_now at 0x10753ca40> |  |

### `validation_work_components`

- **Primary Key:** component_id
- **Foreign Keys:** component_type_id → taxonomy_values.value_id, request_id → validation_requests.request_id, status_id → taxonomy_values.value_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| component_id | INTEGER | No | Yes |  |  |  |
| request_id | INTEGER | No |  | validation_requests.request_id |  |  |
| component_type_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| status_id | INTEGER | No |  | taxonomy_values.value_id |  |  |
| start_date | DATE | Yes |  |  |  |  |
| end_date | DATE | Yes |  |  |  |  |
| notes | TEXT | Yes |  |  |  |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x10755c0e0> |  |

### `validation_workflow_slas`

- **Primary Key:** sla_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| sla_id | INTEGER | No | Yes |  |  |  |
| workflow_type | VARCHAR(100) | No |  |  | Validation |  |
| assignment_days | INTEGER | No |  |  | 10 |  |
| begin_work_days | INTEGER | No |  |  | 5 |  |
| approval_days | INTEGER | No |  |  | 10 |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x1074ee980> |  |
| updated_at | DATETIME | No |  |  | <function utc_now at 0x1074eea20> |  |

### `vendors`

- **Primary Key:** vendor_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| vendor_id | INTEGER | No | Yes |  |  |  |
| name | VARCHAR(255) | No |  |  |  |  |
| contact_info | TEXT | Yes |  |  |  |  |
| created_at | DATETIME | No |  |  | <function utc_now at 0x10730d8a0> |  |

### `version_deployment_tasks`

- **Primary Key:** task_id
- **Foreign Keys:** assigned_to_id → users.user_id, confirmed_by_id → users.user_id, model_id → models.model_id, region_id → regions.region_id, version_id → model_versions.version_id

| Column | Type | Nullable | PK | FK | Default | Comment |
|---|---|---:|---:|---|---|---|
| task_id | INTEGER | No | Yes |  |  |  |
| version_id | INTEGER | No |  | model_versions.version_id |  |  |
| model_id | INTEGER | No |  | models.model_id |  |  |
| region_id | INTEGER | Yes |  | regions.region_id |  | NULL for global deployment |
| planned_production_date | DATE | No |  |  |  |  |
| actual_production_date | DATE | Yes |  |  |  |  |
| assigned_to_id | INTEGER | No |  | users.user_id |  | Model Owner or delegate |
| status | VARCHAR(20) | No |  |  | PENDING |  |
| confirmation_notes | TEXT | Yes |  |  |  |  |
| confirmed_at | DATETIME | Yes |  |  |  |  |
| confirmed_by_id | INTEGER | Yes |  | users.user_id |  |  |
| deployed_before_validation_approved | BOOLEAN | No |  |  | False | True if deployed before validation was approved |
| validation_override_reason | TEXT | Yes |  |  |  | Justification for deploying before validation approval |
| created_at | DATETIME | No |  |  | <function utc_now at 0x107607ce0> |  |

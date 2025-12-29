# Schema Comment Gaps (Candidates)

This report lists database columns that have **no ORM `comment`** and may be difficult to interpret without additional context.
Source of truth: SQLAlchemy models under `api/app/models`.

## Summary

- Total columns without comments: **813**
- High priority (score ≥ 6): **15**
- Medium priority (score 3–5): **219**
- Low priority (score < 3): **579**

## Tables With Most Uncommented Columns

- `decommissioning_requests`: 20
- `models`: 18
- `recommendations`: 18
- `lob_units`: 16
- `monitoring_cycles`: 16
- `validation_approvals`: 16
- `attestation_records`: 15
- `model_exceptions`: 15
- `monitoring_plan_metric_snapshots`: 15
- `attestation_scheduling_rules`: 14
- `component_definition_config_items`: 14
- `monitoring_cycle_approvals`: 14
- `attestation_cycles`: 13
- `validation_assignments`: 13
- `validation_requests`: 13
- `attestation_bulk_submissions`: 12
- `entra_users`: 12
- `monitoring_results`: 12
- `validation_component_definitions`: 12
- `model_versions`: 11
- `action_plan_tasks`: 10
- `model_pending_edits`: 10
- `monitoring_plan_versions`: 10
- `recommendation_approvals`: 10
- `recommendation_rebuttals`: 10

## High Priority (Add Comments First)

| Table | Column | Type | Nullable | FK | Why this is hard to interpret |
|---|---|---|---:|---|---|
| `models` | `status_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Workflow/status semantics not self-evident |
| `recommendation_status_history` | `new_status_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Workflow/status semantics not self-evident |
| `recommendation_status_history` | `old_status_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Workflow/status semantics not self-evident |
| `recommendations` | `current_status_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Workflow/status semantics not self-evident |
| `validation_requests` | `current_status_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Workflow/status semantics not self-evident |
| `validation_status_history` | `new_status_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Workflow/status semantics not self-evident |
| `validation_status_history` | `old_status_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Workflow/status semantics not self-evident |
| `validation_work_components` | `status_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Workflow/status semantics not self-evident |
| `decommissioning_requests` | `reason_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Domain-specific meaning |
| `model_dependency_metadata` | `feed_frequency_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Domain-specific meaning |
| `models` | `usage_frequency_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Domain-specific meaning |
| `monitoring_cycle_approvals` | `approval_status` | VARCHAR(50) | No |  | Workflow/status semantics not self-evident |
| `monitoring_results` | `outcome_value_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Domain-specific meaning |
| `validation_approvals` | `approval_status` | VARCHAR(50) | No |  | Workflow/status semantics not self-evident |
| `validation_requests` | `priority_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity); Domain-specific meaning |

## Medium Priority

| Table | Column | Type | Nullable | FK | Why this is hard to interpret |
|---|---|---|---:|---|---|
| `action_plan_tasks` | `owner_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `action_plan_tasks` | `recommendation_id` | INTEGER | No | recommendations.recommendation_id | Identifier (meaning depends on referenced entity) |
| `attestation_bulk_submissions` | `cycle_id` | INTEGER | No | attestation_cycles.cycle_id | Identifier (meaning depends on referenced entity) |
| `attestation_bulk_submissions` | `status` | VARCHAR(20) | No |  | Workflow/status semantics not self-evident |
| `attestation_bulk_submissions` | `user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `attestation_change_links` | `attestation_id` | INTEGER | No | attestation_records.attestation_id | Identifier (meaning depends on referenced entity) |
| `attestation_change_links` | `decommissioning_request_id` | INTEGER | Yes | decommissioning_requests.request_id | Identifier (meaning depends on referenced entity) |
| `attestation_change_links` | `model_id` | INTEGER | Yes | models.model_id | Identifier (meaning depends on referenced entity) |
| `attestation_change_links` | `pending_edit_id` | INTEGER | Yes | model_pending_edits.pending_edit_id | Identifier (meaning depends on referenced entity) |
| `attestation_coverage_targets` | `created_by_user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `attestation_coverage_targets` | `risk_tier_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `attestation_cycles` | `closed_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `attestation_cycles` | `opened_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `attestation_cycles` | `status` | VARCHAR(20) | No |  | Workflow/status semantics not self-evident |
| `attestation_evidence` | `added_by_user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `attestation_evidence` | `attestation_id` | INTEGER | No | attestation_records.attestation_id | Identifier (meaning depends on referenced entity) |
| `attestation_question_configs` | `question_value_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `attestation_records` | `attesting_user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `attestation_records` | `bulk_submission_id` | INTEGER | Yes | attestation_bulk_submissions.bulk_submission_id | Identifier (meaning depends on referenced entity) |
| `attestation_records` | `cycle_id` | INTEGER | No | attestation_cycles.cycle_id | Identifier (meaning depends on referenced entity) |
| `attestation_records` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `attestation_records` | `reviewed_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `attestation_records` | `status` | VARCHAR(20) | No |  | Workflow/status semantics not self-evident |
| `attestation_responses` | `attestation_id` | INTEGER | No | attestation_records.attestation_id | Identifier (meaning depends on referenced entity) |
| `attestation_responses` | `question_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `attestation_scheduling_rules` | `created_by_user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `attestation_scheduling_rules` | `model_id` | INTEGER | Yes | models.model_id | Identifier (meaning depends on referenced entity) |
| `attestation_scheduling_rules` | `region_id` | INTEGER | Yes | regions.region_id | Identifier (meaning depends on referenced entity) |
| `attestation_scheduling_rules` | `updated_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `audit_logs` | `user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `closure_evidence` | `recommendation_id` | INTEGER | No | recommendations.recommendation_id | Identifier (meaning depends on referenced entity) |
| `closure_evidence` | `uploaded_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `component_definition_config_items` | `component_id` | INTEGER | No | validation_component_definitions.component_id | Identifier (meaning depends on referenced entity) |
| `component_definition_config_items` | `config_id` | INTEGER | No | component_definition_configurations.config_id | Identifier (meaning depends on referenced entity) |
| `component_definition_configurations` | `created_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_approvals` | `approved_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_approvals` | `region_id` | INTEGER | Yes | regions.region_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_approvals` | `request_id` | INTEGER | No | decommissioning_requests.request_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_requests` | `created_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_requests` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_requests` | `owner_approval_required` | BOOLEAN | No |  | Boolean meaning/behavior unclear |
| `decommissioning_requests` | `owner_reviewed_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_requests` | `replacement_model_id` | INTEGER | Yes | models.model_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_requests` | `status` | VARCHAR(30) | No |  | Workflow/status semantics not self-evident |
| `decommissioning_requests` | `validator_reviewed_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_status_history` | `changed_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `decommissioning_status_history` | `new_status` | VARCHAR(30) | No |  | Workflow/status semantics not self-evident |
| `decommissioning_status_history` | `old_status` | VARCHAR(30) | Yes |  | Workflow/status semantics not self-evident |
| `decommissioning_status_history` | `request_id` | INTEGER | No | decommissioning_requests.request_id | Identifier (meaning depends on referenced entity) |
| `export_views` | `user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `fry_line_items` | `metric_group_id` | INTEGER | No | fry_metric_groups.metric_group_id | Identifier (meaning depends on referenced entity) |
| `fry_metric_groups` | `schedule_id` | INTEGER | No | fry_schedules.schedule_id | Identifier (meaning depends on referenced entity) |
| `fry_schedules` | `report_id` | INTEGER | No | fry_reports.report_id | Identifier (meaning depends on referenced entity) |
| `kpm_categories` | `code` | VARCHAR(100) | No |  | No comment; may be ambiguous to analysts |
| `kpms` | `category_id` | INTEGER | No | kpm_categories.category_id | Identifier (meaning depends on referenced entity) |
| `lob_units` | `code` | VARCHAR(50) | No |  | No comment; may be ambiguous to analysts |
| `lob_units` | `parent_id` | INTEGER | Yes | lob_units.lob_id | Identifier (meaning depends on referenced entity) |
| `methodologies` | `category_id` | INTEGER | No | methodology_categories.category_id | Identifier (meaning depends on referenced entity) |
| `methodology_categories` | `code` | VARCHAR(50) | No |  | No comment; may be ambiguous to analysts |
| `model_applications` | `created_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_approval_status_history` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_change_categories` | `code` | VARCHAR(10) | No |  | No comment; may be ambiguous to analysts |
| `model_change_types` | `category_id` | INTEGER | No | model_change_categories.category_id | Identifier (meaning depends on referenced entity) |
| `model_change_types` | `code` | INTEGER | No |  | No comment; may be ambiguous to analysts |
| `model_change_types` | `requires_mv_approval` | BOOLEAN | No |  | Boolean meaning/behavior unclear |
| `model_delegates` | `delegated_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_delegates` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_delegates` | `revoked_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_delegates` | `user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_dependency_metadata` | `criticality_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `model_dependency_metadata` | `dependency_id` | INTEGER | No | model_feed_dependencies.id | Identifier (meaning depends on referenced entity) |
| `model_dependency_metadata` | `interface_type_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `model_exception_status_history` | `exception_id` | INTEGER | No | model_exceptions.exception_id | Identifier (meaning depends on referenced entity) |
| `model_exception_status_history` | `new_status` | VARCHAR(20) | No |  | Workflow/status semantics not self-evident |
| `model_exceptions` | `acknowledged_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_exceptions` | `attestation_response_id` | INTEGER | Yes | attestation_responses.response_id | Identifier (meaning depends on referenced entity) |
| `model_exceptions` | `deployment_task_id` | INTEGER | Yes | version_deployment_tasks.task_id | Identifier (meaning depends on referenced entity) |
| `model_exceptions` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_exceptions` | `monitoring_result_id` | INTEGER | Yes | monitoring_results.result_id | Identifier (meaning depends on referenced entity) |
| `model_exceptions` | `status` | VARCHAR(20) | No |  | Workflow/status semantics not self-evident |
| `model_feed_dependencies` | `consumer_model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_feed_dependencies` | `dependency_type_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `model_feed_dependencies` | `feeder_model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_hierarchy` | `child_model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_hierarchy` | `parent_model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_hierarchy` | `relation_type_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `model_limitations` | `created_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_limitations` | `retired_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_name_history` | `changed_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_name_history` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_pending_edits` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_pending_edits` | `requested_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_pending_edits` | `reviewed_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_pending_edits` | `status` | VARCHAR(20) | No |  | Workflow/status semantics not self-evident |
| `model_regions` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_regions` | `region_id` | INTEGER | No | regions.region_id | Identifier (meaning depends on referenced entity) |
| `model_regions` | `shared_model_owner_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_submission_comments` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_submission_comments` | `user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_types` | `category_id` | INTEGER | No | model_type_categories.category_id | Identifier (meaning depends on referenced entity) |
| `model_version_regions` | `region_id` | INTEGER | No | regions.region_id | Identifier (meaning depends on referenced entity) |
| `model_version_regions` | `version_id` | INTEGER | No | model_versions.version_id | Identifier (meaning depends on referenced entity) |
| `model_versions` | `change_type_id` | INTEGER | Yes | model_change_types.change_type_id | Identifier (meaning depends on referenced entity) |
| `model_versions` | `created_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `model_versions` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `model_versions` | `scope` | VARCHAR(20) | No |  | Domain-specific meaning |
| `model_versions` | `status` | VARCHAR(20) | No |  | Workflow/status semantics not self-evident |
| `model_versions` | `validation_request_id` | INTEGER | Yes | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `models` | `developer_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `models` | `methodology_id` | INTEGER | Yes | methodologies.methodology_id | Identifier (meaning depends on referenced entity) |
| `models` | `model_type_id` | INTEGER | Yes | model_types.type_id | Identifier (meaning depends on referenced entity) |
| `models` | `owner_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `models` | `ownership_type_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `models` | `risk_tier_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `models` | `status` | VARCHAR(50) | No |  | Workflow/status semantics not self-evident |
| `models` | `validation_type_id` | INTEGER | Yes | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `models` | `vendor_id` | INTEGER | Yes | vendors.vendor_id | Identifier (meaning depends on referenced entity) |
| `models` | `wholly_owned_region_id` | INTEGER | Yes | regions.region_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycle_approvals` | `approver_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycle_approvals` | `cycle_id` | INTEGER | No | monitoring_cycles.cycle_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycle_approvals` | `region_id` | INTEGER | Yes | regions.region_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycle_approvals` | `represented_region_id` | INTEGER | Yes | regions.region_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycle_approvals` | `voided_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycles` | `assigned_to_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycles` | `completed_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycles` | `plan_id` | INTEGER | No | monitoring_plans.plan_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycles` | `status` | VARCHAR(50) | No |  | Workflow/status semantics not self-evident |
| `monitoring_cycles` | `submitted_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `monitoring_cycles` | `version_locked_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plan_metric_snapshots` | `kpm_id` | INTEGER | No | kpms.kpm_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plan_metric_snapshots` | `version_id` | INTEGER | No | monitoring_plan_versions.version_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plan_metrics` | `kpm_id` | INTEGER | No | kpms.kpm_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plan_metrics` | `plan_id` | INTEGER | No | monitoring_plans.plan_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plan_model_snapshots` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plan_model_snapshots` | `version_id` | INTEGER | No | monitoring_plan_versions.version_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plan_versions` | `plan_id` | INTEGER | No | monitoring_plans.plan_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plan_versions` | `published_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plans` | `data_provider_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `monitoring_plans` | `monitoring_team_id` | INTEGER | Yes | monitoring_teams.team_id | Identifier (meaning depends on referenced entity) |
| `monitoring_results` | `cycle_id` | INTEGER | No | monitoring_cycles.cycle_id | Identifier (meaning depends on referenced entity) |
| `monitoring_results` | `entered_by_user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `monitoring_results` | `model_id` | INTEGER | Yes | models.model_id | Identifier (meaning depends on referenced entity) |
| `monitoring_results` | `plan_metric_id` | INTEGER | No | monitoring_plan_metrics.metric_id | Identifier (meaning depends on referenced entity) |
| `overdue_revalidation_comments` | `created_by_user_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `overdue_revalidation_comments` | `superseded_by_comment_id` | INTEGER | Yes | overdue_revalidation_comments.comment_id | Identifier (meaning depends on referenced entity) |
| `overdue_revalidation_comments` | `validation_request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `recommendation_approvals` | `approver_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `recommendation_approvals` | `recommendation_id` | INTEGER | No | recommendations.recommendation_id | Identifier (meaning depends on referenced entity) |
| `recommendation_approvals` | `voided_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `recommendation_rebuttals` | `recommendation_id` | INTEGER | No | recommendations.recommendation_id | Identifier (meaning depends on referenced entity) |
| `recommendation_rebuttals` | `reviewed_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `recommendation_rebuttals` | `submitted_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `recommendation_status_history` | `changed_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `recommendation_status_history` | `recommendation_id` | INTEGER | No | recommendations.recommendation_id | Identifier (meaning depends on referenced entity) |
| `recommendations` | `acknowledged_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `recommendations` | `closed_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `recommendations` | `finalized_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `recommendations` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `regions` | `code` | VARCHAR(10) | No |  | No comment; may be ambiguous to analysts |
| `regions` | `requires_regional_approval` | BOOLEAN | No |  | Boolean meaning/behavior unclear |
| `residual_risk_map_configs` | `created_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `rule_required_approvers` | `approver_role_id` | INTEGER | No | approver_roles.role_id | Identifier (meaning depends on referenced entity) |
| `rule_required_approvers` | `rule_id` | INTEGER | No | conditional_approval_rules.rule_id | Identifier (meaning depends on referenced entity) |
| `scorecard_config_versions` | `published_by_user_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `scorecard_criterion_snapshots` | `version_id` | INTEGER | No | scorecard_config_versions.version_id | Identifier (meaning depends on referenced entity) |
| `scorecard_section_snapshots` | `version_id` | INTEGER | No | scorecard_config_versions.version_id | Identifier (meaning depends on referenced entity) |
| `taxonomy_values` | `code` | VARCHAR(50) | No |  | No comment; may be ambiguous to analysts |
| `taxonomy_values` | `taxonomy_id` | INTEGER | No | taxonomies.taxonomy_id | Identifier (meaning depends on referenced entity) |
| `users` | `role` | VARCHAR(50) | No |  | No comment; may be ambiguous to analysts |
| `validation_approvals` | `approver_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_approvals` | `region_id` | INTEGER | Yes | regions.region_id | Identifier (meaning depends on referenced entity) |
| `validation_approvals` | `request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `validation_approvals` | `unlinked_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_approvals` | `voided_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_assignments` | `request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `validation_assignments` | `validator_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_findings` | `identified_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_findings` | `request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `validation_findings` | `resolved_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_grouping_memory` | `last_validation_request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `validation_outcomes` | `overall_rating_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `validation_outcomes` | `request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `validation_plan_components` | `component_id` | INTEGER | No | validation_component_definitions.component_id | Identifier (meaning depends on referenced entity) |
| `validation_plan_components` | `plan_id` | INTEGER | No | validation_plans.plan_id | Identifier (meaning depends on referenced entity) |
| `validation_plans` | `request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `validation_policies` | `risk_tier_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `validation_request_models` | `version_id` | INTEGER | Yes | model_versions.version_id | Identifier (meaning depends on referenced entity) |
| `validation_requests` | `declined_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_requests` | `requestor_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_requests` | `validation_type_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `validation_review_outcomes` | `request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `validation_review_outcomes` | `reviewer_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_status_history` | `changed_by_id` | INTEGER | No | users.user_id | Identifier (meaning depends on referenced entity) |
| `validation_status_history` | `request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `validation_work_components` | `component_type_id` | INTEGER | No | taxonomy_values.value_id | Identifier (meaning depends on referenced entity) |
| `validation_work_components` | `request_id` | INTEGER | No | validation_requests.request_id | Identifier (meaning depends on referenced entity) |
| `version_deployment_tasks` | `confirmed_by_id` | INTEGER | Yes | users.user_id | Identifier (meaning depends on referenced entity) |
| `version_deployment_tasks` | `model_id` | INTEGER | No | models.model_id | Identifier (meaning depends on referenced entity) |
| `version_deployment_tasks` | `status` | VARCHAR(20) | No |  | Workflow/status semantics not self-evident |
| `version_deployment_tasks` | `version_id` | INTEGER | No | model_versions.version_id | Identifier (meaning depends on referenced entity) |

## Notes / Recommendations

- Prefer adding ORM `comment=` on columns that are workflow states, legacy/back-compat fields, date deadlines, and JSON blobs.
- For taxonomy-driven foreign keys, consider comments that identify the expected taxonomy name (e.g., “FK to `taxonomy_values`; taxonomy=`Validation Status`”).
- For booleans, comments should state default behavior and what “true” triggers in the app.
- For JSON columns, document keys and schema (even a short bullet list) and whether the structure is stable.
# Security Test Warnings Report

## 1. Pydantic Deprecated Class-based Config Warnings
**Warning:** `PydanticDeprecatedSince20: Support for class-based config is deprecated, use ConfigDict instead.`
**Count:** 193 warnings
**Details:** Deprecated in Pydantic V2.0 to be removed in V3.0.
**Location:** `pydantic/_internal/_config.py:271`

## 2. Pydantic Protected Namespace "model_" Warnings
**Warning:** `UserWarning: Field "..." has conflict with protected namespace "model_".`
**Details:** Pydantic V2 reserves the `model_` prefix for internal methods. Fields starting with `model_` trigger this warning.
**Affected Fields:**
- `model_id`
- `model_types`
- `model_count`
- `model_name`
- `model_type_id`
- `model_last_updated`
- `model_type`
- `model_owner`
- `model_ids`
- `model_code`
- `model_change_lead_time_days`
- `model_versions`
- `model_documentation_version`
- `model_submission_version`
- `model_documentation_id`
- `model_validation_due_date`
- `model_compliance_status`
- `model_names`
- `model_details`
- `model_driven`
- `model_owner_id`
- `model_owner_name`
- `model_owner_email`
- `model_developer_name`
- `model_snapshots`
- `model_version_id`
- `model_version`
- `model_risk_tier`
- `model_status`

**Suggested Fix:** Set `model_config['protected_namespaces'] = ()` in the Pydantic model configuration.

## 3. Matplotlib Deprecations
**Warnings:**
- `DeprecationWarning: 'parseString' deprecated - use 'parse_string'`
- `DeprecationWarning: 'resetCache' deprecated - use 'reset_cache'`
- `DeprecationWarning: 'enablePackrat' deprecated - use 'enable_packrat'`
**Location:** `matplotlib/_fontconfig_pattern.py` and `matplotlib/_mathtext.py`

## 4. SQLAlchemy Drop All FK Cycle Warning
**Warning:** `SAWarning: Can't sort tables for DROP; an unresolvable foreign key dependency exists between tables: model_versions, validation_requests; and backend does not support ALTER.`
**Location:** `api/tests/conftest.py:50`
**Details:** There is a circular dependency between `model_versions` and `validation_requests` tables that prevents SQLAlchemy from determining the correct drop order.
**Suggested Fix:** Apply `use_alter=True` to ForeignKey and ForeignKeyConstraint objects involved in the cycle.

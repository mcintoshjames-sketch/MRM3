# Remediation Plan: Security Test Warnings

This plan outlines the steps to resolve the warnings identified during the security test suite execution. The goal is to implement clean, safe fixes that modernize the codebase and suppress upstream noise.

## 1. SQLAlchemy Circular Dependency Warning

**Issue:** `SAWarning: Can't sort tables for DROP; an unresolvable foreign key dependency exists between tables: model_versions, validation_requests`

**Root Cause:**
- `ModelVersion` has a foreign key to `ValidationRequest` (`validation_request_id`).
- `ValidationRequest` has a foreign key to `ModelVersion` (`confirmed_model_version_id`).
- This creates a cycle that prevents SQLAlchemy from determining the correct drop order during tests.

**Remediation (safe refactor):**
Prefer a test-only mitigation to avoid changing production DDL or Alembic behavior. Two safe options:
- Add a targeted warning filter in `api/pytest.ini` for this specific SAWarning, or
- Update `api/tests/conftest.py` to drop tables in a manual order (skip dependency sort).

**Optional (higher-risk) alternative:**
If you still want a schema-level fix, apply `use_alter=True` to **one** of the two FKs (not both), give the constraint an explicit name, and confirm Alembic does not require a migration. Avoid this unless the warning is blocking.

**Files to Edit:**
- `api/app/models/model_version.py`
- `api/app/models/validation.py`

**Changes (optional / higher-risk path):**
```python
# api/app/models/model_version.py
validation_request_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("validation_requests.request_id", ondelete="SET NULL", use_alter=True), nullable=True
)

# api/app/models/validation.py
confirmed_model_version_id: Mapped[Optional[int]] = mapped_column(
    Integer,
    ForeignKey("model_versions.version_id", ondelete="SET NULL", use_alter=True),
    nullable=True,
    comment="..."
)
```

## 2. Pydantic Warnings

**Issues:**
1.  `PydanticDeprecatedSince20: Support for class-based config is deprecated`
2.  `UserWarning: Field "..." has conflict with protected namespace "model_"`

**Remediation (safe refactor):**
Replace legacy `class Config` blocks with `model_config = ConfigDict(...)` to eliminate deprecation warnings, and ensure any schema defining `model_*` fields sets `protected_namespaces=()` to prevent namespace conflicts. This is a mechanical, low‑risk change that preserves behavior while removing noise.

**Files to Edit:**
- `api/app/schemas/**/*.py` (replace `class Config` with `model_config`)
- Any schema or inline API model with `model_*` fields lacking `protected_namespaces=()` (including `api/app/api/*.py`)

**Changes:**
Use `ConfigDict` in place of `class Config`, and add `protected_namespaces=()` to `model_config` where `model_*` fields are present (including inline API schemas).

## 3. Matplotlib Deprecation Warnings

**Issue:** `DeprecationWarning` from `matplotlib` internals (via `pyparsing`).

**Root Cause:** Upstream library issue in `matplotlib` or its dependencies.

**Remediation:**
Suppress these warnings in the test configuration, but scope the filters to `matplotlib` to avoid hiding unrelated deprecations.

**Files to Edit:**
- `api/pytest.ini`

**Changes:**
Add to `filterwarnings`:
```ini
filterwarnings =
    # ... existing warnings ...
    ignore:.*parseString.*deprecated:DeprecationWarning:matplotlib.*
    ignore:.*resetCache.*deprecated:DeprecationWarning:matplotlib.*
    ignore:.*enablePackrat.*deprecated:DeprecationWarning:matplotlib.*
```

## Implementation Order
1.  Add targeted test-only warning filters (SQLAlchemy + matplotlib).
2.  Replace `class Config` with `model_config = ConfigDict(...)` across schemas.
3.  Ensure `protected_namespaces=()` is set anywhere `model_*` fields are defined (including inline API schemas).
4.  Re-run security tests to verify clean output.

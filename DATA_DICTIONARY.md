# Data Dictionary (Curated)

This document is the *curated* data dictionary for the application. It focuses on business meaning, governance notes, and how the application uses key entities.

For an **authoritative column-by-column schema listing** generated directly from the SQLAlchemy ORM models, see:

- `DATA_DICTIONARY_SCHEMA.md` (generated)

## Status, Source of Truth, and Regeneration

- **Primary source of truth:** SQLAlchemy models under `api/app/models`.
- **Schema appendix generation:** `scripts/generate_data_dictionary_schema.py` writes `DATA_DICTIONARY_SCHEMA.md`.
- **Why two files:** the schema appendix avoids drift (types/nullability/FKs/defaults/comments come straight from code), while this file stays readable and governance-focused.

To regenerate the appendix:

```bash
python scripts/generate_data_dictionary_schema.py
```

## Conventions and Cross-Cutting Rules

### Identifiers and Keys
- Tables generally use integer surrogate primary keys (e.g., `model_id`, `user_id`).
- Many-to-many relationships are implemented via association tables (e.g., `model_users`, `user_regions`, `monitoring_team_members`).

### Time and Dates
- Most timestamp columns are created/updated using application-side UTC helpers (see `app.core.time.utc_now`).
- Some workflow dates are `Date` (no time component) vs `DateTime` (time-of-day). Treat these as semantically different (deadlines vs event timestamps).

### Reference Data and Taxonomies
- Many “dropdown” classifications are driven by `taxonomies` + `taxonomy_values`.
- Multiple domains use taxonomy values as foreign keys (risk tier, validation type, priority, statuses, etc.).
- Some taxonomies are range-based (“bucket” type) using `min_days`/`max_days`.

### Derived / Computed Values
The API may expose derived fields that are not stored as columns. Example:
- **Model business line / LOB name** is derived from the model owner’s `lob_id` and the LOB hierarchy; the `models` table itself does **not** store a `lob_id`.

## Domain Glossary (Business Meaning)

### Inventory
- **Model**: the inventory record for a model or non-model tool (see `models.is_model`).
- **Model Version**: a submitted change/version of a model (see `model_versions`).
- **Change Taxonomy**: standardized change classification (`model_change_categories`/`model_change_types`).

### Governance and Workflow
- **Validation Request**: a workflow entity representing a validation engagement and its status progression.
- **Monitoring Plan**: ongoing monitoring configuration (scope, frequency, team, due dates).
- **Attestation Cycle**: scheduled attestation period; cycles can be concurrently open.

### Organization
- **LOB Unit**: hierarchical line-of-business structure (`lob_units`), used to roll up ownership views.
- **Region**: geographic/regulatory region used for approvals, scoping, and regional governance.

## Key Entities (Curated Notes)

### `users`
Represents application users (owners, developers, validators, approvers, admins).

Governance notes:
- Contains sensitive data (`email`, `password_hash`). Treat as **confidential**.
- `role` is an application enum concept; authorization logic uses this heavily.
- Regional approver scoping is modeled via the `user_regions` association to `regions`.

### `lob_units`
Represents the organization hierarchy (SBU → LOB1 → LOB2 → ...).

How the app uses it:
- Users are assigned to a required `lob_id`.
- Model “business line” is derived from the owner’s LOB and may roll up to a configured level.

### `models`
The central inventory record representing a model or a non-model tool/application.

Important semantics and implementation details:
- Ownership is modeled through foreign keys to `users` (`owner_id`, `developer_id`, optional shared roles).
- Classification fields are largely taxonomy-driven (e.g., `risk_tier_id`, `validation_type_id`, `usage_frequency_id`).
- Some classifications are multi-valued (e.g., regulatory categories) via many-to-many association tables.
- `status` (string enum) and `status_id` (taxonomy value) can both exist; treat `status_id` as the configurable/status-taxonomy representation.
- “Model vs non-model” is explicitly represented via `is_model`. MRSA classification uses `is_mrsa` and related fields.

### `regions`
Geographic/regulatory regions used for scoping and approvals.

Important semantics and implementation details:
- `requires_regional_approval` and related flags drive region-specific governance behaviors.

### `model_versions`
Tracks version submissions/changes over time.

Important semantics and implementation details:
- `change_type` is a legacy string; `change_type_id` normalizes change classification to `model_change_types`.
- Regional scoping is represented via `scope` plus the association table `model_version_regions`.
- Production dates include planned vs actual (and a legacy `production_date` field).
- Workflow coupling: versions can link to `validation_requests`.

### Validation (selected)
Validation is a multi-entity workflow domain. Use the schema appendix for the full table list/columns.

Key concepts:
- `validation_requests` is the hub record.
- Risk-tier-driven policies live in `validation_policies`.
- Assignment/approval/history tables record workflow progression and accountability.

### Monitoring (selected)
Monitoring supports ongoing performance monitoring plans and teams.

Key concepts:
- `monitoring_teams` group users.
- `monitoring_plans` define frequency, due dates, and who provides data.
- Plan scope can attach to models via `monitoring_plan_models`.

### Attestation (selected)
Attestation supports periodic owner attestations and admin review.

Key concepts:
- `attestation_cycles` define the schedule window and status.
- Associated scheduling rules and record tables drive “who must attest, when, and why”.

## How to Use This Data Dictionary

- For **reporting/BI**: start with the schema appendix to understand join keys and constraints, then refer here for business meaning.
- For **data governance**: treat taxonomy tables as the controlled vocabulary; changes should follow change management.
- For **API development**: remember the API may expose computed properties that do not exist as stored columns.


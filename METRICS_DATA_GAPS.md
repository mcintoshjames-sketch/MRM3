# Metrics Data Readiness Audit

- **4.1 Total Active Models** — Ready. Use `models.status='Active'` with `row_approval_status IS NULL`.
- **4.2 % by Inherent Risk Tier** — Ready. `models.risk_tier_id` → `taxonomy_values`.
- **4.3 % by Business Line/Region** — Region ready (`model_regions` / `wholly_owned_region_id`). Business line can be proxied via the owner’s LOB hierarchy (roll up as needed). If a dedicated model-level business line is desired, add `business_line_id` (taxonomy) and capture it explicitly.
- **4.4 % Vendor/Third-Party Models** — Ready. `development_type='Third-Party'` or `vendor_id IS NOT NULL`.
- **4.5 % AI/ML Models** — Ready. `methodology.category.is_aiml` is seeded and exposed; `Model.is_aiml` computed (see `api/app/models/model.py` and `api/app/api/methodology.py`).
- **4.6 % Validated Within Required Cycle** — Ready. `validation_requests` dates + `validation_policies` frequency/grace/lead time allow on-time calculation per model.
- **4.7 % Overdue for Validation** — Ready. Same inputs as 4.6; compare due/validation_due to today.
- **4.8 Avg Time to Complete Model Validation** — Ready. `submission_received_date` → `completion_date` (or approval timestamp) on `validation_requests`.
- **4.9 Number of Models with Interim Approval** — Gap. No explicit interim approval flag/status; interim validations exist, but there isn’t a durable “interim approved” marker per model to count.
- **4.10 % Timely Performance Monitoring Submission** — Ready. `monitoring_cycles` now track `submission_due_date` and `submitted_at` (`api/app/models/monitoring.py`).
- **4.11 % Breaching Performance Thresholds** — Ready. `monitoring_results` table captures per-cycle outcomes with `calculated_outcome` (R/Y/G) and links to plan metrics (`api/app/models/monitoring.py`).
- **4.12 % with Open Performance Issues** — Gap. No dedicated performance issue/alert table; breaches are recorded as results, but “open issue” state isn’t modeled.
- **4.13 Avg Time to Remediate Performance Breaches** — Gap. Needs breach open/close timestamps or issue lifecycle (not present).
- **4.14 % with Critical Limitations** — Ready. `model_limitations.significance='Critical'` per model.
- **4.15 % with Usage Restrictions/Conditions** — Gap. No explicit usage restriction flag/details on models or related table.
- **4.18 Total Number of Open Recommendations** — Ready. `recommendations` with `closed_at IS NULL` / non-terminal status.
- **4.19 % Recommendations Past Due** — Ready. `current_target_date` vs today, `closed_at IS NULL`.
- **4.20 Avg Time to Close Recommendations** — Ready. `created_at` → `closed_at`.
- **4.21 % Models with Open High-Priority Recommendations** — Ready. `priority_id` (High) + `closed_at IS NULL`, grouped by model.
- **4.22 % Required Attestations Received On Time** — Ready. `attestation_records.due_date` and `attested_at`/status.
- **4.23 Number of Models Flagged for Decommissioning** — Likely ready via `decommissioning_requests` status or a “Decommission Pending” model status; ensure status/date captured.
- **4.24 Number of Models Decommissioned in Last 12 Months** — Ready if decommission completion date is stored (e.g., on request or model status change); add a timestamp if missing.
- **4.26 % Models with Residual Risk Downgraded for Overdue Validation/Poor Performance** — Gap. No residual-risk history or downgrade reason codes to attribute changes.
- **4.27 KRI: % Models with High Residual Risk** — Gap. Current residual risk is not stored on models; needs a field or latest-assessment linkage.
- **4.28 KRI: % Models Past Due for Validation** — Ready. Same inputs as 4.7.

## Data-Leverage Notes / Proposed Approaches
- 4.9 Interim approval: derive counts from existing interim validation requests/outcomes (latest per model) before adding a new flag; only persist a denorm flag if consumers need it.
- 4.12 Open performance issues: compute “open” from monitoring results (latest RED/YELLOW without a subsequent GREEN) and cycle status; add a table only if you need workflow (assignment/comments/SLA).
- 4.13 Breach remediation time: can be computed from monitoring_results by measuring time from first breach to the first subsequent GREEN for the same plan_metric/model; formal history only if needed for audit/perf.
- 4.15 Usage restrictions: no proxy data; requires new model fields (boolean + notes) and API/UX capture.
- 4.26 Residual risk history/downgrade reasons: if needed, add a history table; lighter option is to log deltas when validations complete by comparing prior vs new residual risk.
- 4.27 Current residual risk: can be derived from latest validation outcome + residual risk map; add a persistent `current_residual_risk_id` only if derivation is ambiguous or too costly to compute on read.

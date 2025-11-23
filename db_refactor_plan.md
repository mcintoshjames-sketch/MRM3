## Incremental Data Model Hardening Plan (In-Progress)

Scope: Approval role normalization (taxonomy-backed), regional approval consistency, change-type/production date cleanup strategy, deployment task consistency. Lifecycle ordering checks are **out of scope** per request.

### Tasks & Rollback
- [x] Add approval role taxonomy seeded with current role variants; document rollback (remove taxonomy values) if needed.
- [x] Enforce approval role validation against taxonomy (prefix-friendly for regional variants) on creation/auto-assignment; rollback by disabling validation helper.
- [x] Require regional approvals to carry `region_id` and default `represented_region_id`; rollback by relaxing the checks.
- [x] Prefer `change_type_id` over legacy `change_type` (code-level preference, no schema change); rollback by reverting to legacy string reads.
- [x] Clarify production date usage (planned/actual) and mark legacy field for deprecation in code comments; rollback by keeping existing accesses untouched.
- [x] Ensure deployment tasks align `model_id` with the model of `version_id` during operations; rollback by removing the consistency check.
- [ ] (Optional) Add FK index notes/plan for future migration; no action now.

### Notes
- No database schema migrations in this pass; changes are code/data-seed level with clear rollback paths.
- Approval roles kept short and sourced from existing data: Global Approver, Regional Approver (prefix for region-coded strings), Regional Validator, Model Owner, Model Risk Committee, Senior Management, Committee.

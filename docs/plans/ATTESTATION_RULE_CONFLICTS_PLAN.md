# Attestation Rule Conflict Guardrails Plan

## Goals
- Prevent ambiguous or conflicting scheduling rules from producing non-deterministic frequencies.
- Freeze the rule/frequency applied at cycle open so submissions stay consistent even if rules change mid-cycle.
- Align UI and docs with the actual evaluation order and validation rules.

## Plan
1. **Persist applied rule/frequency on records**
   - Add `applied_rule_id` and `applied_frequency` columns to `attestation_records` with an Alembic migration.
   - Update the `AttestationRecord` model and `AttestationRecordResponse` to expose these fields.
2. **Deterministic rule evaluation**
   - Resolve rules in a fixed order: rule-type precedence (`MODEL_OVERRIDE > REGIONAL_OVERRIDE > OWNER_THRESHOLD > GLOBAL_DEFAULT`), then `priority DESC`, then `effective_date DESC`, then `rule_id DESC`.
   - Return both frequency and rule ID from resolution helper to store on records.
3. **Rule validation guardrails**
   - Enforce required/forbidden fields per rule type (e.g., `MODEL_OVERRIDE` requires `model_id` and no region/owner criteria).
   - Validate `end_date >= effective_date` and `owner_model_count_min >= 1` when provided.
   - Block overlapping active `MODEL_OVERRIDE` rules for the same model and overlapping active `REGIONAL_OVERRIDE` rules for the same region.
   - Only enforce the “one active GLOBAL_DEFAULT” rule when the incoming rule is active.
4. **Use stored frequency downstream**
   - On cycle open, set `applied_rule_id` and `applied_frequency` on each new record.
   - On submission, use the stored frequency (fallback to current rules for legacy records).
   - In the attestation detail UI, fetch questions using the record’s stored frequency to keep question sets aligned.
5. **Docs + tests**
   - Update UI helper text and `USER_GUIDE_ATTESTATION.md` to describe type precedence and priority within a type.
   - Add tests for overlap validation and applied frequency storage.

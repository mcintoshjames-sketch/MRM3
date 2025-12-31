# Monitoring Report Threshold Consistency Remediation Plan

Goal
- Eliminate mismatches between reported thresholds and stored outcomes in monitoring cycle PDFs.
- Ensure quantitative outcomes are calculated against the locked plan version used by the cycle.
- Backfill historical outcomes so past PDFs and analytics align with the cycle version in effect at the time.
- Provide strong automated coverage for the fix and the backfill.

Problem Summary
- The PDF report currently uses live plan metric thresholds when rendering breach details and charts.
- Outcomes stored in MonitoringResult are calculated using live thresholds for manual entry/update, but cycles are locked to plan versions with snapshot thresholds.
- Result: PDFs can show a YELLOW outcome with thresholds that would imply RED (or GREEN), and narratives can cite mismatched threshold values.

Scope
- Backend PDF generation for monitoring cycles.
- Outcome calculation for manual result entry/update.
- Historical backfill of MonitoringResult.calculated_outcome and outcome_value_id.
- Exception detection alignment with backfilled outcomes.
- Tests (unit + integration + migration/backfill validation).

Decisions
- Thresholds shown in PDFs should come from the cycle's locked plan version (MonitoringPlanMetricSnapshot).
- Outcome calculation for quantitative metrics should use snapshot thresholds when cycle.plan_version_id is present.
- Backfill recalculates outcomes only for quantitative results with numeric_value.
- Narratives are not altered; they remain historical user input.
- Legacy cycles with plan_version_id = NULL use live plan metrics as the threshold source.
- Deleted metrics do not require backfill because cascades remove their results.

Investigation Checklist (before coding)
1) For cycle 6, confirm plan_version_id on monitoring_cycles.
2) Compare live thresholds vs snapshot thresholds for the affected metric_id.
3) Compare MonitoringResult.calculated_outcome vs snapshot-based outcome.
4) Check if any results lack a snapshot for their plan_version_id (missing or removed metrics).

Implementation Plan
1) Snapshot-aware thresholds in PDF generation
   - In generate_cycle_report_pdf:
     - Load MonitoringPlanMetricSnapshot for cycle.plan_version_id.
     - Map by original_metric_id to get thresholds + kpm_name + kpm_category_name + evaluation_type.
     - Populate results_data yellow/red thresholds from snapshot when available.
     - Use snapshot metric name/category for consistency with the cycle's version.
   - In breach analysis:
     - Ensure "Recorded Value / Threshold" reflects snapshot values.
   - In trend charts:
     - Use snapshot thresholds from the current cycle version (same source as breach table).
     - Add a short note in breach analysis: "Thresholds reflect plan version vX (effective YYYY-MM-DD)."

2) Snapshot-aware outcome calculation for manual entry/update
   - Create helper: resolve_threshold_source(cycle, plan_metric_id) -> snapshot or live metric.
   - In POST /monitoring/cycles/{cycle_id}/results:
     - If cycle.plan_version_id and snapshot exists, compute outcome against snapshot thresholds.
     - If plan_version_id is NULL or snapshot missing, fall back to live plan metric thresholds and log warning.
   - In PATCH /monitoring/results/{result_id}:
     - Use the same logic when numeric_value is updated.
   - Keep outcome_value_id in sync with calculated_outcome for quantitative metrics.
   - Confirm CSV import already uses snapshots; align helper so all three paths behave consistently.

3) Backfill historical outcomes (quantitative only)
   - Target set:
     - MonitoringResult with numeric_value IS NOT NULL.
     - Cycle has plan_version_id.
     - Snapshot exists for (plan_version_id, original_metric_id = plan_metric_id).
   - Recalculate calculated_outcome from snapshot thresholds.
   - Update outcome_value_id to match the recalculated outcome.
   - Only write rows when outcome changes (diff-based update).
   - Record audit logs:
     - Per-cycle summary entry with counts, plus optional per-result entries when changed.
   - For results with missing snapshots:
     - Skip and collect counts for review.

4) Exception alignment after backfill
   - Do not reuse autoclose_type1_on_improved_result (it is model-level, not result-specific).
   - Implement backfill-specific exception handling:
     - If outcome changes from RED to YELLOW/GREEN:
       - Close exceptions where monitoring_result_id == result_id using NO_LONGER_EXCEPTION.
     - If outcome changes to RED from YELLOW/GREEN:
       - Create new exception linked to the same monitoring_result_id.
   - Preserve existing detection behavior for normal flows outside of backfill.
   - Produce a summary report of exceptions closed/created.
   - No automatic recommendation changes; flag for manual review if needed.

Testing Plan
Backend Unit Tests
- calculate_outcome uses snapshot thresholds when cycle.plan_version_id is set.
- calculate_outcome falls back to live metric when plan_version_id is NULL or snapshot missing.
- PDF report uses snapshot thresholds (not live) for breach sections and charts.
- Trend chart uses current cycle snapshot thresholds and uses outcome colors from stored results.

Integration Tests
- Create plan -> publish version -> start cycle (locks version) -> change live thresholds -> enter result -> PDF shows snapshot thresholds and stored outcome matches snapshot.
- PATCH numeric_value on a locked cycle recalculates outcome from snapshot.
- CSV import remains consistent with manual entry outcomes.

Backfill Tests
- Seed results with changed thresholds across versions.
- Run backfill in dry-run mode:
  - Verify counts of updated outcomes.
  - Verify skipped count for missing snapshots.
- Run backfill in apply mode:
  - Verify calculated_outcome + outcome_value_id changes.
  - Verify exception close/create behavior using result-linked exceptions.
  - Verify audit log entries.

Regression Tests
- Existing monitoring result creation/update flows for unversioned cycles.
- PDF generation for cycles without plan_version_id.

Rollout Plan
1) Ship backend changes (snapshot-aware PDF + outcome calculation).
2) Run backfill in staging with dry-run; validate sample PDF outputs for known cycles.
3) Run backfill apply in staging; validate exceptions report and dashboards.
4) Deploy to production; run backfill with logging + summary report.
5) Spot-check PDFs for previously inconsistent cycles (including cycle 6).

Risks and Mitigations
- Narrative may reference old thresholds: keep narrative unchanged but add PDF note about versioned thresholds.
- Missing snapshots for older cycles: skip and log; consider manual remediation if volume is high.
- Exception churn: handle via targeted close/create and include audit evidence.


Deliverables
- Code changes in monitoring PDF generation and result calculation.
- Backfill script (dry-run + apply) with audit logging.
- Test suite updates (unit + integration).
- Summary report of backfill impact (outcomes + exceptions).

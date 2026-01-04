# Phase 2 Risk Register Closeout Report

## Current Status Snapshot
- Verified in production: SEC-01, SEC-02, SEC-03, SEC-04 (config checks + negative fail-fast)
- Verified via automated tests: DATA-01, PERF-01..04, REL-01..03
- Postgres concurrency validation: completed (advisory lock test passed)
- Performance benchmarks: completed (bench harness output captured)

## Targeted Prod Smoke Check (SEC-02/03/04)
- SEC-02: Registration forces `USER` role and ignores `region_ids` (role_code=USER, regions=0).
- SEC-03: Non-admin blocked from list/get/update/delete user endpoints (403).
- SEC-04: Production config checks passed (SECRET_KEY set and non-default, length >= 32; DATABASE_URL not localhost or dev default; ANALYTICS_DB_ROLE set). Negative fail-fast exercised in a controlled environment (see evidence).

## Remaining Work to Close Out the Register
- None. All Phase 2 risks have verification evidence captured.

## ARCHITECTURE.md Reconciliation
- Updated Runtime & Deployment to reflect:
  - fail-fast config requirements and `.env.example` reference
  - production migration gate in `scripts/deploy.sh`
  - analytics read-only role bootstrap via `scripts/db_init/001_create_analytics_readonly.sql`
- No additional architectural updates required at this time.

## Evidence (Automated Tests)
- `DATABASE_URL=sqlite:///./test.db SECRET_KEY=test-secret PYTHONPATH=. pytest tests/test_security_hardening.py tests/test_monitoring.py tests/test_deployment_tasks.py tests/test_lob.py tests/test_risk_assessment_api.py tests/test_report_query_counts.py` → **230 passed, 18 warnings** (2025-01-04).
- `DATABASE_URL=sqlite:///./test.db SECRET_KEY=test-secret PYTHONPATH=. TEST_DATABASE_URL=postgresql://mrm_test_user:***@localhost:5434/mrm_test pytest -m postgres tests/test_postgres_concurrency.py` → **1 passed** (2025-01-04).
- `BENCH_DATABASE_URL=postgresql://mrm_bench_user:***@localhost:5434/mrm_bench python3 scripts/bench_reports.py --database-url "$BENCH_DATABASE_URL" --reset` → **benchmarks captured** (2025-01-04).

## Evidence (Negative Validation)
- `api/audit_artifacts/sec04_negative_validation.txt` → missing/short `SECRET_KEY` and default `DATABASE_URL` fail-fast cases captured (2026-01-04).

## Evidence (Benchmarks)
Dataset: 10,000 models; 5 regions; 2,000 attestation cycles; 10 records/cycle.

| Report | p50 (ms) | p95 (ms) | Query Count |
| --- | --- | --- | --- |
| KPI Report (uncached) | 0.49 | 0.67 | 1–23 |
| KPI Report (cached) | 0.40 | 0.40 | 1 |
| Regional Compliance Report | 115.51 | 116.29 | 4 |
| Attestation Cycles List | 8.31 | 9.57 | 2 |

## Operational Cleanup (Optional)
- Remove temporary admin account created for prod verification once you confirm no further live checks are needed.

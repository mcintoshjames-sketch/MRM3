# Adversarial Gap Analysis (Retrospective + Remediation Status)

**Date**: 2026-01-03  
**Last updated**: 2026-01-04 (RLS audit + doc hygiene complete)

This document captures the original adversarial review (“Effective Challenge”) findings from the Phase C/D review, and tracks what has been remediated since.

---

## Scope & Method (Original)

**Goal**: Identify high-impact failure modes that could survive a superficial “module inventory” review, with emphasis on correctness under edge cases, operational safety, and security assumptions.

**Method**:
- **Blind scan**: pick the highest-risk modules without relying on prior findings.
- **Critique**: identify “false comforts” (things that look safe but aren’t).
- **Undisclosed risks**: enumerate latent risks and how they would manifest in production.
- **Kill list deep dive**: focus on one subsystem (Model Exceptions automation) to produce actionable pre-prod breakpoints.

---

## Blind Scan: Top 3 High-Risk Modules

1. **Validation workflow**: large, stateful router with governance implications.
2. **Monitoring workflow**: large router plus status transitions and approval logic.
3. **Model Exceptions automation**: cross-domain detection, idempotency, and operational safety.

---

## Critique of the Early (Superficial) Review

The early PHASE 1 review focused on “does the module exist” alignment and documentation drift. That approach can miss production-critical risks, including:
- **Semantic mismatches**: taxonomy codes/status values inconsistent across modules.
- **Authorization gaps**: app-layer “RLS” filters must be applied everywhere, and omissions are silent.
- **Operational footguns**: batch endpoints that are safe at small scale but dangerous at inventory scale.
- **Security assumptions**: JWT validation and prod-hardening checks that are easy to bypass.

Original “rigorousness” score assigned: **3/10** (heavy on inventory, light on correctness + failure modes).

---

## Undisclosed Risks Table (Original) + Status

| Risk | Where it manifests | Why it’s dangerous | Current status | Evidence / Notes |
|---|---|---|---|---|
| Recommendation terminal-status mismatch suppresses Type 1 exceptions | Exception detection Type 1 active-rec logic | Can create **false negatives**: RED results appear “covered” by terminal recommendations | **Remediated** | Central terminal status constant used across Monitoring/Recommendations/Exception detection. See [api/app/core/exception_detection.py](api/app/core/exception_detection.py) and [api/app/core/recommendation_status.py](api/app/core/recommendation_status.py). |
| `exception_code` generation race | Exception creation uses `max(code)+1` | Concurrent batch runs can violate uniqueness, cause 500s or partial failures | **Remediated** | Bounded retry on collision implemented; regression test added. See [api/app/core/exception_detection.py](api/app/core/exception_detection.py) and [api/tests/test_exceptions.py](api/tests/test_exceptions.py). |
| `/exceptions/detect-all` operational risk (timeouts, big transactions) | Batch detection endpoint | Can time out, lock tables, or fail mid-run without clear trace | **Remediated** (guardrails) | Added `limit/offset`, per-model commit, and audit log on success/failure. See [api/app/api/exceptions.py](api/app/api/exceptions.py). |
| Closure taxonomy missing causes silent “no-close” behavior | Auto-close/manual close paths | Exceptions remain open indefinitely in partially-seeded envs | **Remediated** | Readiness fails if required closure-reason codes are missing, preventing traffic until seeded. See [api/app/core/exception_detection.py](api/app/core/exception_detection.py) and readiness checks in [api/app/main.py](api/app/main.py). |
| JWT validation minimal (issuer/audience hardening) | Auth dependency stack | Token acceptance may be overly permissive depending on deployment expectations | **Remediated** | Issuer/audience enforced when configured; production requires JWT_ISSUER/JWT_AUDIENCE. Tests added. See [api/app/core/security.py](api/app/core/security.py), [api/app/core/config.py](api/app/core/config.py), [api/tests/test_jwt_security.py](api/tests/test_jwt_security.py). |
| Prod-hardening checks brittle/bypassable | Settings validation | Safety checks only run under specific ENV and only reject one exact placeholder | **Remediated** | Production enforces SECRET_KEY length, issuer/audience, and UAT break-glass requirements. See [api/app/core/config.py](api/app/core/config.py). |
| App-layer “RLS” is easy to omit | Query-filter-based access control | Missing filter application can leak data silently | **Remediated** | Inventory completed with regression tests; residual risk is future drift. See [RLS_AUDIT.md](RLS_AUDIT.md) and [api/tests/test_rls_endpoints.py](api/tests/test_rls_endpoints.py). |

---

## What Has Been Remediated So Far (High Confidence)

### 1) Terminal recommendation statuses standardized
- Canonical terminal status codes are now shared via [api/app/core/recommendation_status.py](api/app/core/recommendation_status.py).
- Monitoring, Recommendations, and Exception detection import and use the shared constant.

### 2) Type 1 exception detection correctness improved
- Active recommendation status filtering now excludes terminal statuses using the shared constant.
- Both Type 1 creation paths (`detect_type1_unmitigated_performance` and `ensure_type1_exception_for_result`) use the same helper.

### 3) Exception code collisions handled
- Exception creation now retries on collision with bounded attempts.
- Regression test exists to prove collision retry behavior.

### 4) `/exceptions/detect-all` hardened
- Added `limit/offset` and bounded `limit`.
- Commits per model reduce transaction size.
- Audit logs written on both success and failure.
- Operational runbook documented in [EXCEPTIONS_REMEDIATION.md](EXCEPTIONS_REMEDIATION.md).

### 5) JWT trust-model hardening
- `JWT_ISSUER`/`JWT_AUDIENCE` supported in tokens and enforced during decode.
- Production startup now requires issuer/audience configuration.
- Tests added for issuer/audience/algorithm rejection.

### 6) Operational probes
- Added `/health` + `/healthz` liveness and `/ready` + `/readyz` readiness endpoints.
- Readiness uses a lightweight DB connectivity check.

### 7) Production safety checks
- Production now enforces strong SECRET_KEY length, issuer/audience presence, and UAT tools require explicit break-glass approval.

### 8) RLS enforcement audit (complete)
- Monitoring plan/cycle/results + report/approvals endpoints now use cycle/plan view gates (includes eligible approvers).
- Decommissioning list/detail and team model listing are RLS-filtered.
- Overdue revalidation report confirmed admin-only.
- IRP list/detail/coverage/review-status endpoints filtered by MRSA access.
- Regression coverage added in [api/tests/test_rls_endpoints.py](api/tests/test_rls_endpoints.py).
- Full inventory tracked in [RLS_AUDIT.md](RLS_AUDIT.md).

### 9) Documentation hygiene (REC_* status conventions)
- Updated recommendation status references to align with `REC_*` taxonomy conventions.
- Added operational runbook details for `/exceptions/detect-all`.

### 10) Closure taxonomy readiness guard
- Readiness now fails if required exception closure reason codes are missing, preventing silent no-close behavior.

---

## Critical Open Risks (Remaining)

### A) App-layer RLS enforcement regression risk
**Why it matters**: Central helpers are good, but future endpoints can still miss filters if not reviewed.

**Evidence**:
- RLS helpers: [api/app/core/rls.py](api/app/core/rls.py)
- Audit tracker: [RLS_AUDIT.md](RLS_AUDIT.md) (inventory complete as of this update)

---

## Next Remediation Focus (Recommended)

**None (monitor for drift)** — revisit if new endpoints, roles, or workflow states are introduced.

---

## Proposed Next Steps (Prioritized)

### P3: Ongoing maintenance
- Periodic doc drift checks after major feature work or schema changes.

---

## Appendix: Remediation Evidence Pointers

- Exception detection hardening: [api/app/core/exception_detection.py](api/app/core/exception_detection.py)
- Shared terminal status codes: [api/app/core/recommendation_status.py](api/app/core/recommendation_status.py)
- Detect-all guardrails & auditing: [api/app/api/exceptions.py](api/app/api/exceptions.py)
- Regression tests: [api/tests/test_exceptions.py](api/tests/test_exceptions.py)

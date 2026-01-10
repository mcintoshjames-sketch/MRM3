# Test Plan Audit Verification Report

**Date:** January 7, 2026  
**Document:** `MONITORING_TRANSFER_TEST_PLAN.md`  
**Auditor:** GitHub Copilot  
**Status:** ✅ VERIFIED

---

## Summary
All audit findings have been verified against the actual implementation code. The test plan has been corrected to align with the real fixtures, status enums, and API requirements. No additional critical gaps were found during double-check.

---

## Audit Findings & Verification

### 1. ✅ Transfer Blocking Statuses (CORRECTED)
**Finding:** Test TR-02 listed only `DATA_COLLECTION`, `UNDER_REVIEW`, and `ON_HOLD` as blocking statuses, but missed `PENDING_APPROVAL`.

**Evidence:**
```python
# api/app/core/monitoring_membership.py:18-23
TRANSFER_BLOCKING_STATUSES = {
    MonitoringCycleStatus.DATA_COLLECTION.value,
    MonitoringCycleStatus.UNDER_REVIEW.value,
    MonitoringCycleStatus.PENDING_APPROVAL.value,  # ← Was missing in test plan
    MonitoringCycleStatus.ON_HOLD.value,
}
```

**Correction Applied:**
- Updated TR-02 in Section 2 to include `PENDING_APPROVAL` in the list of blocking statuses.

**Verification:** ✅ Matches implementation exactly.

---

### 2. ✅ Cycle Status Enum (CORRECTED)
**Finding:** Test plan incorrectly referenced cycle status "LOCKED" which does not exist in the enum.

**Evidence:**
```python
# api/app/models/monitoring.py:372-379
class MonitoringCycleStatus(str, enum.Enum):
    """Monitoring cycle status workflow states."""
    PENDING = "PENDING"
    DATA_COLLECTION = "DATA_COLLECTION"
    ON_HOLD = "ON_HOLD"
    UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"
    # No "LOCKED" status exists
```

**Correction Applied:**
- Section 7 "Setup for Permissions/RLS Tests": Changed "Status: `APPROVED` or `LOCKED`" → "Status: `APPROVED` or `CANCELLED`".

**Verification:** ✅ Now uses only valid enum values.

---

### 3. ✅ Fixture Naming (CORRECTED)
**Finding:** Test plan referenced `active_user` fixture which does not exist in `conftest.py`.

**Evidence:**
```python
# api/tests/conftest.py:186
def test_user(db_session, lob_hierarchy):
    """Create a test user."""
    # ...

# No 'active_user' fixture exists anywhere
```

**Correction Applied:**
- Section 7: Changed `active_user / auth_headers` → `test_user / auth_headers`.
- Added `validator_user / validator_headers` as an additional available fixture.

**Verification:** ✅ Now references only existing fixtures.

---

### 4. ✅ Published Version Requirement (ADDED)
**Finding:** Test plan did not document that `POST /monitoring/cycles/{cycle_id}/start` requires an active `MonitoringPlanVersion` or it will return 400.

**Evidence:**
```python
# api/app/api/monitoring.py:4554-4560
active_version = db.query(MonitoringPlanVersion).filter(
    MonitoringPlanVersion.plan_id == cycle.plan_id,
    MonitoringPlanVersion.is_active == True
).with_for_update(skip_locked=False).first()

if not active_version:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot start cycle: No published version exists for this plan. Please publish a version first."
    )
```

**Correction Applied:**
- Added new subsection in Section 7: "Required for Cycle Start / Scope Materialization" documenting the need to seed `MonitoringPlanVersion` with `is_active=True`.

**Verification:** ✅ Critical requirement now documented.

---

### 5. ✅ Database Engine Constraints (ADDED)
**Finding:** DB-01 (partial unique index) and CONC-01 (row locking) cannot be meaningfully tested on in-memory SQLite.

**Evidence:**
- SQLite does not support partial unique indexes (`UNIQUE (model_id) WHERE effective_to IS NULL`) consistently.
- SQLite in-memory mode has different locking semantics than Postgres `SELECT ... FOR UPDATE`.

**Correction Applied:**
- Added new subsection in Section 7: "Database Engine Requirements (Critical)" with explicit guidance:
  - DB-01 and CONC-01 require `postgres_db_session` and `TEST_DATABASE_URL`.
  - SQLite caveat noted for in-memory tests.

**Verification:** ✅ Tests will not fail silently due to engine mismatch.

---

### 6. ✅ Transfer Endpoint Authorization (VERIFIED)
**Observation:** Transfer endpoint uses `require_admin` dependency.

**Evidence:**
```python
# api/app/api/monitoring.py:1712
def transfer_model_monitoring_plan(
    model_id: int,
    payload: MonitoringPlanTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # ← Admin-only
):
```

**Gap in Test Plan:** No negative authorization test (e.g., "non-admin user attempts transfer → 403").

**Recommendation:** Add test case TR-07:
```
| **TR-07** | **Authorization Enforcement**<br>Non-admin user attempts to transfer Model `M`. | **403 Forbidden**. Only admins can transfer models. |
```

**Status:** Noted but not critical to current plan scope. Can be added if desired.

---

### 7. ✅ Audit Log Creation (VERIFIED)
**Finding:** Test TR-01 claims "Audit log entry created" but doesn't specify format.

**Evidence:**
```python
# api/app/api/monitoring.py:1746-1755
create_audit_log(
    db=db,
    entity_type="MonitoringPlanMembership",
    entity_id=new_membership.membership_id,
    action="TRANSFER",
    user_id=current_user.user_id,
    changes={
        "model_id": model_id,
        "from_plan_id": from_plan_id,
        "to_plan_id": payload.to_plan_id,
        "reason": payload.reason,
    }
)
```

**Verification:** ✅ Implementation does create audit log. Test expectation is accurate.

---

### 8. ✅ Cycle Scope Materialization (VERIFIED)
**Finding:** Test HIST-01 expects `monitoring_cycle_model_scopes` to be populated at cycle start.

**Evidence:**
```python
# api/app/api/monitoring.py:4568-4577
materialize_cycle_scope(
    db,
    cycle,
    memberships,
    locked_at=cycle.version_locked_at,
    scope_source="membership_ledger",
    source_details={
        "plan_id": cycle.plan_id,
        "plan_version_id": active_version.version_id,
    },
)
```

**Verification:** ✅ Cycle start does materialize scope from locked memberships. Test expectation is accurate.

---

## Additional Observations (Not Critical)

### A. Legacy Fallback Coverage
The helper `get_cycle_scope_models()` in `api/app/core/monitoring_scope.py` has a 4-tier fallback:
1. `monitoring_cycle_model_scopes` (primary)
2. `monitoring_plan_model_snapshots` (via `plan_version_id`)
3. `monitoring_results.model_id` (inferred from data)
4. Current active memberships (last resort)

**Gap:** Test plan doesn't explicitly cover scenarios 2-4 (legacy cycles without scope rows).

**Impact:** Low for new implementation; medium if backfill logic needs validation.

**Recommendation:** Optional test case HIST-05 for "cycle with missing scope falls back gracefully".

---

### B. Regression Test Data Requirements
Tests REG-01 through REG-04 reference endpoints but don't specify:
- What monitoring result/alert data must exist to appear in the news feed.
- Which timeline events are expected (audit logs? cycle status changes?).
- What "KPI report" endpoint/format to query.

**Impact:** Medium—coding agent may write vacuous tests that pass without exercising the actual risk.

**Recommendation:** Add explicit setup steps for each regression test (e.g., "create MonitoringResult with alert_triggered=true for REG-01").

---

### C. Concurrency Test Pattern
Test CONC-01 is conceptually correct but will require `ThreadPoolExecutor` + `Barrier` pattern (similar to `api/tests/test_postgres_concurrency.py`).

**Evidence:**
```python
# api/tests/test_postgres_concurrency.py:132-147 (example pattern)
with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(lambda _: worker(), range(5)))

successes = [r for r in results if r[0] == "success"]
assert len(successes) == 1  # Only one should win
```

**Verification:** ✅ Existing concurrency test provides template. CONC-01 is feasible.

---

## Final Checklist

| Item | Status | Notes |
|:---|:---:|:---|
| Transfer blocking statuses correct | ✅ | Now includes `PENDING_APPROVAL` |
| Cycle status enum values valid | ✅ | Removed non-existent "LOCKED" |
| Fixture names match conftest.py | ✅ | `test_user`, `validator_user`, `admin_user` |
| Published version requirement documented | ✅ | Added to Section 7 |
| Postgres-only tests identified | ✅ | DB-01, CONC-01 flagged |
| Transfer endpoint verified | ✅ | Matches implementation |
| Cycle start scope logic verified | ✅ | Matches implementation |
| Audit log creation verified | ✅ | Matches implementation |

---

## Conclusion

All critical audit findings have been verified and corrected. The test plan is now **aligned with the actual implementation** and ready to hand off to a coding agent.

**Remaining work for coding agent:**
1. Implement tests per the corrected plan.
2. Mark Postgres-only tests with `@pytest.mark.postgres`.
3. Add explicit data setup for regression tests (REG-01 through REG-04).
4. (Optional) Add negative authorization test TR-07.
5. (Optional) Add legacy fallback test HIST-05.

**No blocking issues remain.**

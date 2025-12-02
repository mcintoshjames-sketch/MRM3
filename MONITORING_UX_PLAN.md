# Monitoring Plan Discoverability - Implementation Plan

## Overview

This document outlines the TDD implementation plan to improve monitoring plan discoverability in the MRM application.

**Problem**: UAT users cannot find where to create performance monitoring plans for models.

**Root Causes**:
1. "Monitoring Plans" link buried at position 21 in sidebar (Admin section)
2. No contextual entry point from Model details page
3. Confusing terminology ("My Monitoring" vs "Monitoring Plans")
4. No visual indicators for unmonitored models

---

## Implementation Phases

### Phase 1: Backend API Enhancement
**Goal**: Add endpoint to fetch monitoring plans for a specific model

| Step | Type | Description |
|------|------|-------------|
| 1.1 | TEST | Write test for `GET /models/{id}/monitoring-plans` endpoint |
| 1.2 | IMPL | Implement endpoint to return monitoring plans containing the model |
| 1.3 | TEST | Write test for monitoring status in model list response |
| 1.4 | IMPL | Add `monitoring_plan_count` field to model list/detail responses |

**Files**:
- `api/tests/test_monitoring.py` (new tests)
- `api/app/api/models.py` (enhance endpoints)
- `api/app/api/monitoring.py` (new endpoint)

---

### Phase 2: Frontend - Model Monitoring Tab Component
**Goal**: Create reusable component showing monitoring status for a model

| Step | Type | Description |
|------|------|-------------|
| 2.1 | TEST | Write component tests for `ModelMonitoringTab` |
| 2.2 | IMPL | Create `ModelMonitoringTab.tsx` component |
| 2.3 | TEST | Test empty state rendering (no plans) |
| 2.4 | IMPL | Implement empty state with "Create Plan" CTA |
| 2.5 | TEST | Test plans list rendering |
| 2.6 | IMPL | Implement plans list with cycle status |

**Files**:
- `web/src/components/ModelMonitoringTab.tsx` (new)
- `web/src/components/ModelMonitoringTab.test.tsx` (new)
- `web/src/api/monitoring.ts` (add new API function)

---

### Phase 3: Integrate Monitoring Tab into Model Details
**Goal**: Add Monitoring tab to ModelDetailsPage

| Step | Type | Description |
|------|------|-------------|
| 3.1 | TEST | Update ModelDetailsPage tests for new tab |
| 3.2 | IMPL | Add "Monitoring" tab to ModelDetailsPage |
| 3.3 | IMPL | Wire up tab to ModelMonitoringTab component |

**Files**:
- `web/src/pages/ModelDetailsPage.tsx`
- `web/src/pages/ModelDetailsPage.test.tsx`

---

### Phase 4: URL Parameter Support for Pre-population
**Goal**: Support `?model={id}` parameter on MonitoringPlansPage

| Step | Type | Description |
|------|------|-------------|
| 4.1 | TEST | Write test for URL parameter handling |
| 4.2 | IMPL | Parse `model` query param and pre-populate form |
| 4.3 | IMPL | Auto-open "Add Plan" modal when param present |

**Files**:
- `web/src/pages/MonitoringPlansPage.tsx`

---

### Phase 5: Sidebar Navigation Reorganization
**Goal**: Improve navigation structure for monitoring features

| Step | Type | Description |
|------|------|-------------|
| 5.1 | IMPL | Rename "My Monitoring" to "My Monitoring Tasks" |
| 5.2 | IMPL | Move "Monitoring Plans" adjacent to "My Monitoring Tasks" |
| 5.3 | IMPL | Add section headers for visual grouping |

**Files**:
- `web/src/components/Layout.tsx`

---

### Phase 6: Monitoring Status Column on Models List (Optional)
**Goal**: Show monitoring coverage on models list page

| Step | Type | Description |
|------|------|-------------|
| 6.1 | TEST | Test monitoring status badge rendering |
| 6.2 | IMPL | Add "Monitoring" column to ModelsPage |
| 6.3 | IMPL | Add click handler to navigate to create plan |

**Files**:
- `web/src/pages/ModelsPage.tsx`

---

## Test Strategy

### Backend Tests (pytest)
```python
# test_monitoring.py

def test_get_model_monitoring_plans_returns_plans():
    """GET /models/{id}/monitoring-plans returns plans containing this model"""

def test_get_model_monitoring_plans_empty():
    """GET /models/{id}/monitoring-plans returns empty list when no plans"""

def test_model_detail_includes_monitoring_count():
    """Model detail response includes monitoring_plan_count field"""
```

### Frontend Tests (vitest)
```typescript
// ModelMonitoringTab.test.tsx

describe('ModelMonitoringTab', () => {
    it('renders empty state when no monitoring plans exist');
    it('shows "Create Monitoring Plan" button for admin users');
    it('hides "Create Monitoring Plan" button for non-admin users');
    it('renders list of monitoring plans when they exist');
    it('displays current cycle status for each plan');
    it('links to monitoring plan detail page');
});
```

---

## Acceptance Criteria

### Must Have (P1)
- [x] Model details page has "Monitoring" tab
- [x] Tab shows list of monitoring plans containing this model
- [x] Empty state shows helpful message and "Create Plan" button (Admin)
- [x] "Create Plan" button links to `/monitoring-plans?model={id}`
- [x] MonitoringPlansPage pre-populates model when `?model=` param present
- [x] Sidebar has "Monitoring Plans" moved closer to "My Monitoring"

### Should Have (P2)
- [x] "My Monitoring" renamed to "My Monitoring Tasks"
- [ ] Section headers in sidebar for visual grouping (deferred)
- [x] Monitoring tab shows current cycle status (due date, last results)

### Nice to Have (P3)
- [ ] Models list page shows monitoring coverage column
- [ ] Warning badge for Tier 1/2 models without monitoring plans

---

## Rollback Plan

All changes are additive and non-breaking:
- New API endpoint doesn't affect existing endpoints
- New tab is purely additive to Model details
- Sidebar changes are visual only, all routes unchanged

If issues arise, revert commits in order:
1. Sidebar changes (Phase 5)
2. URL parameter support (Phase 4)
3. Tab integration (Phase 3)
4. Component (Phase 2)
5. API (Phase 1)

---

## Progress Tracking

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Backend API | COMPLETE | Already existed at `/monitoring/models/{id}/monitoring-plans` |
| Phase 2: Monitoring Tab Component | COMPLETE | Created `ModelMonitoringTab.tsx` |
| Phase 3: Tab Integration | COMPLETE | Added to `ModelDetailsPage.tsx` |
| Phase 4: URL Parameter Support | COMPLETE | Added `?model=` param handling to `MonitoringPlansPage.tsx` |
| Phase 5: Sidebar Reorganization | COMPLETE | Moved "Monitoring Plans" near "My Monitoring Tasks" in `Layout.tsx` |
| Phase 6: Models List Column | Not Started | Optional - deferred |

---

## Related Files Reference

### Backend
- `api/app/api/monitoring.py` - Existing monitoring endpoints
- `api/app/models/monitoring.py` - MonitoringPlan, MonitoringPlanModel models
- `api/tests/test_monitoring.py` - Existing monitoring tests

### Frontend
- `web/src/pages/ModelDetailsPage.tsx` - Model detail with tabs
- `web/src/pages/MonitoringPlansPage.tsx` - Admin plan management
- `web/src/pages/MyMonitoringPage.tsx` - User task view
- `web/src/components/Layout.tsx` - Sidebar navigation
- `web/src/api/monitoring.ts` - Monitoring API client (if exists)

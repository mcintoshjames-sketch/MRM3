# Admin Monitoring Overview Implementation Plan

## Problem Statement

The Admin user sees an empty "My Monitoring Tasks" page because the endpoint returns tasks where the user is personally assigned (data_provider, team_member, assignee). Admins have governance oversight responsibilities, not direct task assignments.

## Solution: Admin Monitoring Overview

Redesign the "My Monitoring Tasks" page to show a **Monitoring Program Overview** for Admin users that provides governance oversight of all monitoring activities.

---

## Implementation Status

### Completed Tasks

#### 1. Backend Schema Definitions
**File**: `api/app/schemas/monitoring.py`

Added three new schema classes:
- `AdminMonitoringCycleSummary` - Individual cycle summary with priority, approval progress, and result counts
- `AdminMonitoringOverviewSummary` - Summary counts (overdue, pending approval, in progress, completed)
- `AdminMonitoringOverviewResponse` - Complete response with summary + cycle list

#### 2. Backend API Endpoint
**File**: `api/app/api/monitoring.py`

Added endpoint `GET /monitoring/admin-overview`:
- Requires Admin role (uses `require_admin` dependency)
- Returns summary counts and priority-sorted cycle list
- Calculates priority based on: overdue > pending_approval > approaching (14 days) > normal
- Includes approval progress (e.g., "1/2 approved") for PENDING_APPROVAL cycles
- Includes result counts with GREEN/YELLOW/RED breakdown

Also added helper function `_generate_period_label()` to format periods as "Q3 2025", "Sep 2025", "H1 2025", etc.

#### 3. Frontend Component
**File**: `web/src/components/AdminMonitoringOverview.tsx`

Created comprehensive admin overview component with:
- **Summary Cards**: Clickable cards for Overdue (red), Pending Approval (yellow), In Progress (blue), Completed 30d (green)
- **Priority Table**: Sorted by urgency with visual indicators
- **Filtering**: Click summary cards to filter table
- **CSV Export**: Export filtered data
- **Visual Indicators**:
  - Priority emojis (🔴🟡🟠⚪)
  - Status badges
  - Days overdue/remaining
  - Result outcome dots (green/yellow/red)
- **Legend**: Explains priority indicators

---

### Completed

#### 4. Update MyMonitoringPage for Conditional Rendering
**File**: `web/src/pages/MyMonitoringPage.tsx`

Done:
- Import `AdminMonitoringOverview` component
- Import `useAuth` hook to get current user role
- Conditionally render `AdminMonitoringOverview` for Admin users, existing content for non-admins

#### 5. Testing - Completed

**API Test Results (2025-11-29)**:
```
GET /monitoring/admin-overview
HTTP Status: 200

Response:
{
  "summary": {
    "overdue_count": 0,
    "pending_approval_count": 0,
    "in_progress_count": 1,
    "completed_last_30_days": 2
  },
  "cycles": [
    {
      "cycle_id": 19,
      "plan_id": 1,
      "plan_name": "Credit Risk Model Monitoring - Q1 2025",
      "period_label": "Q1 2028",
      "status": "UNDER_REVIEW",
      "days_overdue": -882,
      "priority": "normal",
      "team_name": "Credit Risk Monitoring Team",
      "data_provider_name": "John Smith",
      "result_count": 3,
      "green_count": 0,
      "yellow_count": 2,
      "red_count": 1
    }
  ]
}
```

**Verified:**
- ✅ Admin-only endpoint (requires Admin role)
- ✅ Summary counts calculated correctly
- ✅ Priority sorting works (overdue > pending_approval > approaching > normal)
- ✅ Period label generation (Q1 2028 format)
- ✅ Result outcome breakdown (green/yellow/red counts)
- ✅ TypeScript compilation passes

---

## API Response Structure

```typescript
// GET /monitoring/admin-overview
{
  "summary": {
    "overdue_count": 3,
    "pending_approval_count": 5,
    "in_progress_count": 12,
    "completed_last_30_days": 8
  },
  "cycles": [
    {
      "cycle_id": 15,
      "plan_id": 1,
      "plan_name": "Credit Risk Model Monitoring",
      "period_label": "Q3 2025",
      "period_start_date": "2025-07-01",
      "period_end_date": "2025-09-30",
      "due_date": "2025-10-15",
      "status": "PENDING_APPROVAL",
      "days_overdue": 5,
      "priority": "overdue",
      "team_name": "Credit Risk Monitoring Team",
      "data_provider_name": "John Smith",
      "approval_progress": "1/2",
      "report_url": "https://...",
      "result_count": 10,
      "green_count": 7,
      "yellow_count": 2,
      "red_count": 1
    }
  ]
}
```

---

## Priority Sort Logic

Cycles are sorted by priority in this order:
1. **Overdue** (most days overdue first) - days_overdue > 0
2. **Pending Approval** (longest waiting first) - status = PENDING_APPROVAL, not overdue
3. **Approaching** (soonest due first) - due within 14 days
4. **Normal** - everything else

Within each priority level, sorted by urgency (days_overdue descending, so most urgent first).

---

## Files Modified/Created

| File | Action | Description |
|------|--------|-------------|
| `api/app/schemas/monitoring.py` | Modified | Added 3 new schema classes |
| `api/app/api/monitoring.py` | Modified | Added endpoint + helper function |
| `web/src/components/AdminMonitoringOverview.tsx` | Created | New admin overview component |
| `web/src/pages/MyMonitoringPage.tsx` | Modified | Conditional rendering for admin |

---

## Implementation Complete

All tasks completed:
1. ✅ Backend schema definitions
2. ✅ Backend API endpoint
3. ✅ Frontend AdminMonitoringOverview component
4. ✅ MyMonitoringPage conditional rendering
5. ✅ API testing verified
6. ✅ Design refinements for consistency with Admin Dashboard

### Design Refinements (2025-11-29)
Updated the AdminMonitoringOverview component to match the cleaner visual style of the main Admin Dashboard:
- **Summary Cards**: Changed from emoji-based clickable buttons to simple white cards with `bg-white p-4 rounded-lg shadow-md` styling
- **Priority Indicators**: Replaced emoji icons (🔴🟡🟠⚪) with colored dots using `rounded-full` spans matching the result indicator style
- **Legend**: Updated to use same colored dot visual language with `bg-white border shadow-sm` styling and uppercase label header
- **Color Consistency**: Red (#ef4444), Orange (#fb923c), Yellow (#facc15), Gray (#d1d5db) for priority states

The Admin user now sees a comprehensive "Monitoring Program Overview" with consistent visual design throughout the application.

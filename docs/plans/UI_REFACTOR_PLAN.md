# UI Refactoring Plan: Interactive Statistic Filters

## Goal
Align key list pages with the "Interactive Statistic Cards" design pattern found in `MyAttestationsPage.tsx`. This pattern improves usability by combining high-level metrics with quick filtering capabilities.

## Design Pattern Reference
**Example:** `web/src/pages/MyAttestationsPage.tsx`

**Key Elements:**
1.  **Interactive Statistic Cards:** Top banner containing key metrics (e.g., "Total Items", "Overdue").
2.  **Mutually Exclusive:** Only one card filter can be active at a time.
3.  **Visual Feedback:** Active cards are highlighted (e.g., `ring-2 ring-blue-500`, `aria-pressed="true"`).
4.  **Filtered List:** The list below updates immediately to show records matching the selected metric.
5.  **Clear Filters:** A clear option to reset filters when one is active.
6.  **Scoped Counts:** Card counts reflect the current scope (e.g., if "My Models" is checked, the "Overdue" count reflects only *my* overdue models).

---

## Target Pages for Refactoring

### 1. Recommendations Page
**File:** `web/src/pages/RecommendationsPage.tsx`

**Current State:**
- Contains a list of recommendations.
- Has sidebar/top filters for Status, Priority, Category.
- Has "My Tasks Only" and "Overdue Only" checkboxes.
- Displays a simple "Showing X of Y" text.

**Proposed Changes:**
- **State Management:**
    - Introduce `filterMode` state: `'all' | 'my_tasks' | 'overdue' | 'high_priority'`.
    - Initialize based on URL params (e.g., `?my_tasks=true` sets mode to `'my_tasks'`).
- **Add Statistic Cards:**
    1.  **Total Open:** Count of all open recommendations (excludes `REC_DROPPED`, `REC_CLOSED`). Clicking sets mode to `'all'`.
    2.  **My Tasks:** Count of recommendations in `myTaskIds` set. Clicking sets mode to `'my_tasks'`.
    3.  **Overdue:** Count of overdue recommendations. Clicking sets mode to `'overdue'`.
    4.  **High Priority:** Count of High priority items. Clicking sets mode to `'high_priority'`.
- **Interaction:**
    - Cards are mutually exclusive.
    - Secondary filters (Search, Category dropdowns) *stack* on top of the active card filter.
    - "Clear Filters" button resets `filterMode` to `'all'` and clears secondary filters.

### 2. Monitoring Plans Page (Admin Overview)
**File:** `web/src/pages/MonitoringPlansPage.tsx` & `web/src/components/AdminMonitoringOverview.tsx`

**Current State:**
- `AdminMonitoringOverview` component displays summary cards ("Overdue Cycles", "Pending Approval", etc.).
- These cards are currently static `div`s.
- "Completed (30d)" card exists but has no direct filter target in the current list logic.

**Proposed Changes:**
- **Refactor `AdminMonitoringOverview`:**
    - Convert summary cards to `button` elements.
    - **Overdue Cycles Card:** On click, set `statusFilter` to `'overdue'`.
    - **Pending Approval Card:** On click, set `statusFilter` to `'pending_approval'`.
    - **Active/In Progress Card:** On click, set `statusFilter` to `'in_progress'`.
    - **Total/All Card:** Add a new card for "Total Active Cycles" to allow resetting the view (sets `statusFilter` to `'all'`).
    - **Completed (30d) Card:** Keep as informational (non-clickable) or link to a history report, as it doesn't map to the current "Active Cycles" list.
- **Visuals:** Add active state styling (borders/rings) matching the reference design.

### 3. Attestation Cycles Page (All Records Tab)
**File:** `web/src/pages/AttestationCyclesPage.tsx`

**Current State:**
- The "All Records" tab displays a table of all attestations.
- Has a dropdown filter for `allRecordsStatusFilter`.
- Already has a set of buttons that look like cards but might need styling/behavior refinement to match the pattern exactly.

**Proposed Changes:**
- **Refine Statistic Cards (All Records Tab):**
    - Ensure the existing buttons for "Total Records", "Pending", "Submitted", etc., follow the strict "Interactive Card" styling (ring, aria-pressed).
    - **Scoped Counts:** Ensure the counts displayed on these cards respect the `allRecordsCycleFilter`. If a specific cycle is selected, the "Pending" count should only show pending items *for that cycle*.
    - **Mutually Exclusive:** Ensure clicking one clears the others (already seems to be the case with `toggleAllRecordsStatusFilter`).
    - **Dropdown:** Remove the redundant status dropdown if the cards cover all statuses, or keep it as a fallback for mobile.

### 4. Ready to Deploy Page
**File:** `web/src/pages/ReadyToDeployPage.tsx`

**Current State:**
- Displays list of models ready for deployment.
- Calculates `uniqueVersionsCount`, `uniqueModelsCount`, `pendingTasksCount`.
- Shows these as simple text stats.

**Proposed Changes:**
- **Interactive Cards:**
    1.  **Ready to Deploy:** Count of models with `has_pending_task = false`.
    2.  **Pending Tasks:** Count of models with `has_pending_task = true`.
    3.  **Total Candidates:** Count of all items in the list.
- **Interaction:**
    - Client-side filtering.
    - **Scoped Counts:** If "My Models Only" is checked, these card counts must update to reflect only the user's models.
    - Clicking a card filters the table below.

### 5. Overdue Revalidation Report Page
**File:** `web/src/pages/OverdueRevalidationReportPage.tsx`

**Current State:**
- Displays a report of overdue items.
- Has `EnhancedSummary` with `pre_submission_overdue`, `validation_overdue`, `missing_commentary`.
- Has filters for `overdue_type` and `comment_status`.

**Proposed Changes:**
- **Add Statistic Cards:**
    1.  **Pre-Submission Overdue:** Filter `overdue_type` to `'PRE_SUBMISSION'`.
    2.  **Validation Overdue:** Filter `overdue_type` to `'VALIDATION_IN_PROGRESS'`.
    3.  **Missing Commentary:** Filter `comment_status` to `'MISSING'`.
    4.  **Stale Commentary:** Filter `comment_status` to `'STALE'`.
- **Interaction:**
    - **Quick Filters:** These cards act as quick filters.
    - **Mutually Exclusive:** Clicking "Missing Commentary" clears "Pre-Submission Overdue" filter.
    - **Stacking:** These filters *stack* with "Region" or "Risk Tier" filters.
    - **Clear:** "Clear Filters" button resets these specific quick filters.

## General UX Requirements

1.  **Component Consistency:**
    - Use a consistent card design: `bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md`.
    - Active state: `ring-2 ring-[color]-500`.
    - Accessibility: Use `button` elements with `type="button"` and `aria-pressed={isActive}`.
2.  **Clear Filters:**
    - Place a "Clear Filters" button clearly visible when a filter is active (e.g., "Showing: **Overdue** items (Clear)").
3.  **Responsiveness:**
    - Use `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` (or similar) to ensure cards stack gracefully on mobile.


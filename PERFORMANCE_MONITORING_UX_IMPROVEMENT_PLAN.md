# Performance Monitoring UX/Architecture Improvement Plan

## Executive Summary

The current Performance Monitoring module is functionally robust but suffers from **"Monolithic UI" anti-patterns** and **high cognitive friction** in the data entry workflow. While the backend architecture is sound (using a versioned plan approach), the frontend implementation concentrates too much responsibility into a single view (`MonitoringPlanDetailPage.tsx`), creating a dense, overwhelming experience.

The critical friction point is the **Result Entry Workflow**. Currently, users must navigate deep into a configuration page to perform a routine operational task (entering data), and the "Publish" requirement for plan changes creates a hidden mode error where users wonder why their threshold updates aren't reflected in active cycles.

---

## 1. Workflow Analysis

### Current Workflow (High Friction)
1.  **Navigation**: User clicks "Monitoring Plans" (Admin menu) $\rightarrow$ Selects Plan.
2.  **Context Switching**: User lands on a "Configuration" page (Metrics/Models tabs) but wants to do "Operations" (Cycles).
3.  **Drill Down**: User clicks "Cycles" tab $\rightarrow$ Finds active cycle $\rightarrow$ Clicks "Enter Results".
4.  **Data Entry**: A **Modal** opens. User manually inputs values for 10+ models $\times$ 5+ metrics.
    *   *Friction*: Modals prevent referencing other tabs/pages. No bulk paste.
5.  **Validation**: User saves. If a threshold is breached, the status updates, but there is no immediate prompt to explain/annotate the breach.

### Proposed Workflow (Streamlined)
1.  **Navigation**: User clicks "My Monitoring Tasks" (Top-level menu).
2.  **Direct Access**: User sees a card: *"Q3 2025 Cycle - Due in 3 days"*. Clicks "Enter Data".
3.  **Dedicated View**: User lands on a **Full-Page Grid** (Excel-like interface).
4.  **Data Entry**: User pastes column of data from their local Excel file.
5.  **Immediate Feedback**: Cells turn Red/Green instantly based on thresholds.
6.  **Annotation**: User clicks a Red cell $\rightarrow$ Side panel opens to "Add Breach Justification".

---

## 2. Friction & Cognitive Load Analysis

| Category | Issue | Impact |
| :--- | :--- | :--- |
| **Latency** | **On-the-fly Diffing**: `compute_has_unpublished_changes` runs every time a plan is loaded, comparing sets of metrics vs. snapshots. | As plans grow (50+ models), the "Plan Details" page load time will degrade linearly. |
| **Info Density** | **The "Everything" Page**: `MonitoringPlanDetailPage.tsx` (~4700 lines) handles Config, Versioning, Cycles, and Results. | Users are bombarded with "Configuration" data (Thresholds, Methodologies) when they just want to see "Status". |
| **Workflow Gap** | **The "Publish" Trap**: Users change a threshold, go to the cycle, and see old thresholds. They don't realize they must "Publish" a new version. | High support ticket volume ("Why is my threshold not working?"). |
| **Visual Hierarchy** | **Table Blindness**: Results are shown in standard tables. A "Critical Breach" looks 90% similar to a "Stable" result. | Risk Managers miss urgent signals amidst the noise of "Green" data. |

---

## 3. Enhancement Plan

### A. Refactoring: Decouple "Config" from "Ops"
Split the monolithic `MonitoringPlanDetailPage` into distinct routes.
*   `/monitoring/plans/{id}/config`: For Admins to set metrics/thresholds.
*   `/monitoring/cycles/{id}`: For Validators/Owners to view status and enter data.

**Backend Optimization**:
Stop computing diffs on read. Use a `dirty` flag pattern.

```python
# api/app/models/monitoring.py

class MonitoringPlan(Base):
    # ... existing fields ...
    
    # New field to track state
    is_dirty = Column(Boolean, default=False, index=True)

# api/app/api/monitoring.py

def add_metric_to_plan(plan_id, metric_data):
    # ... add metric logic ...
    plan.is_dirty = True  # Set flag on write
    db.commit()

def get_plan(plan_id):
    # No need to run heavy set comparison logic
    return {
        "id": plan.id,
        "has_unpublished_changes": plan.is_dirty, 
        # ...
    }
```

### B. UI/UX Pattern: The "Data Grid"
Replace the "Enter Results" modal with a dedicated **Data Grid View**.

*   **Pattern**: Spreadsheet-style editable table.
*   **Interaction**: Keyboard navigation (Tab/Enter), Copy/Paste support.
*   **Visuals**: Conditional formatting (Background color saturation based on value).

### C. Visual Hierarchy: "Exception-Based" Dashboard
On the "My Monitoring" page, separate "Action Required" from "Information".

*   **Top Section (Urgent)**: "Breaches Requiring Explanation", "Overdue Cycles".
*   **Bottom Section (Stable)**: "Completed Cycles", "Upcoming Cycles".

---

## 4. Feature Recommendations

### 1. "Smart" Threshold Wizard
**Problem**: Users struggle to mentally map "Lower is Better" vs "Range" logic.
**Solution**: A visual configurator.
*   *UI*: A slider bar with draggable handles for "Green", "Yellow", "Red" zones.
*   *Benefit*: Eliminates configuration errors (e.g., setting Red Min > Red Max).

### 2. Bulk Ingestion API & UI
**Problem**: Manual entry is slow and error-prone.
**Solution**: Drag-and-drop CSV upload on the Cycle page.
*   *Workflow*: User uploads `results_q3.csv`. System matches rows by `Model ID` and `Metric Code`.
*   *Benefit*: Reduces data entry time from 30 mins to 30 seconds.

### 3. Automated "Breach Protocol"
**Problem**: A breach is just a red dot. It requires no specific action.
**Solution**: State machine enforcement.
*   *Logic*: If `Result == Red`, prevent Cycle transition to `COMPLETED` until `BreachJustification` is filled.
*   *UI*: "Resolve Breaches" wizard that walks the user through each red metric to add a comment.

# Model Details Ribbon Refactor Plan

## 1. Problem Statement
The horizontal navigation ribbon on the Model Details page has grown to **12 items**, causing layout issues on standard screens. 
Current items:
1. Model Details
2. Risk Assessment
3. Versions
4. Validations (Dynamic: "X active")
5. Relationships
6. Activity
7. Recommendations (Dynamic Badge)
8. Limitations
9. Overlays
10. Monitoring
11. Decommissioning (Dynamic Badge)
12. Exceptions (Dynamic Badge)

## 2. Proposed Solution: Priority + "More" Menu
We will refactor the hardcoded list into a data-driven component using a **fixed array order**. The first 7 items will be visible, and the remaining items will be grouped into a "More" dropdown.

### The "Visible" List (Top 7)
These are hardcoded as the primary views in this specific order:
1.  **Model Details**
2.  **Versions**
3.  **Risk Assessment**
4.  **Validations**
5.  **Monitoring**
6.  **Recommendations**
7.  **Limitations**

### The "More" Menu (Overflow)
These will be tucked away but accessible:
8.  **Relationships**
9.  **Activity**
10. **Overlays**
11. **Decommissioning**
12. **Exceptions**

### Key Features
*   **Priority Display:** The most accessed tabs remain one click away.
*   **Dynamic "More" Indicator:** If any hidden tab (like Exceptions or Recommendations) has an active badge/notification, the "More" dropdown trigger will show a visual indicator (e.g., a dot) to ensure critical alerts aren't missed.
*   **Seamless UX:** Selecting an item from the "More" menu will mark the "More" tab as active while displaying the selected content.

## 3. Technical Implementation Details

### A. Data Structure
We will define a `TabConfig` interface to separate the data from the rendering logic.

```typescript
type TabId = 'details' | 'risk-assessment' | 'versions' | 'validations' | 
             'relationships' | 'activity' | 'recommendations' | 'limitations' | 
             'overlays' | 'monitoring' | 'decommissioning' | 'exceptions';

interface TabConfig {
    id: TabId;
    label: string;
    // Optional: Render function for complex labels (like "Validations (3 active)")
    renderLabel?: () => React.ReactNode; 
    // Optional: Badge count/status for the "More" bubble logic
    badgeCount?: number;
    hasWarning?: boolean;
}
```

### B. Logic Changes (`ModelDetailsPage.tsx`)
1.  **Extract Tab Logic:** Move the badge calculation logic (currently inline in JSX) into a helper function or `useMemo` hook that returns the `tabs` array.
2.  **Split Arrays:** Slice the `tabs` array into `visibleTabs` (0-6) and `overflowTabs` (6+).
3.  **Render Loop:**
    *   Map over `visibleTabs` to render standard buttons.
    *   Render a new `Dropdown` component for `overflowTabs`.

### C. New Component: `TabDropdown`
Since Headless UI is not available, we will implement a lightweight, accessible dropdown using standard React state and Tailwind CSS.

**Behavior:**
*   **Trigger:** A "More" button.
*   **State:** Open/Closed toggle.
*   **Active State:** Highlights blue if the current `activeTab` is inside the overflow list.
*   **Notification:** Shows a small red dot if any item in `overflowTabs` has `badgeCount > 0`.

## 4. Work Breakdown
1.  **Refactor Preparation:** Extract the complex inline badge logic for Validations, Recommendations, Decommissioning, and Exceptions into variables at the top of the render function.
2.  **Component Creation:** Create the `tabs` configuration array.
3.  **UI Implementation:** Replace the hardcoded `<nav>` block with the new dynamic rendering logic.
4.  **Testing:** Verify that clicking overflow items works and that badges correctly bubble up to the "More" menu.

## 5. Visual Mockup (Text)
```
[Model Details] [Risk Assessment] [Versions] [Validations (2)] [Relationships] [Activity] [ More ▾ ]
                                                                                         |
                                                                                         | Recommendations (1)
                                                                                         | Limitations
                                                                                         | Overlays
                                                                                         | Monitoring
                                                                                         | Decommissioning
                                                                                         | Exceptions (3)
```

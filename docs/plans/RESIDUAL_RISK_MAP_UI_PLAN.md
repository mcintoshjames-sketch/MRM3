# Residual Risk Map UI Implementation Plan

## Overview

Add UI components to display and configure the Residual Risk Map, which computes Residual (Final) Risk from the combination of Inherent Risk Tier and Validation Scorecard Outcome.

## Backend Status (Complete)

- ✅ Database model: `ResidualRiskMapConfig`
- ✅ API endpoints: `/residual-risk-map/`
- ✅ Computed properties on `ValidationRequest`: `scorecard_overall_rating`, `residual_risk`
- ✅ Seeding from `RESIDUAL_RISK_MAP.json`

---

## UI Implementation Tasks

### Task 1: Admin Configuration Page in Taxonomy Section

**Location**: Add to existing Taxonomy page as a new tab/section

**File**: `web/src/pages/TaxonomyPage.tsx`

**Existing Tabs** (for context):
- General Taxonomies
- Change Types
- Model Types
- Scorecard Criteria
- Qualitative Factors

**New Tab**: "Residual Risk Map"

**Implementation**:
- Add "Residual Risk Map" tab alongside existing tabs
- Display the matrix as a read-only colored table by default
- Admin can click "Edit" to modify cell values
- Show version history with ability to view past configurations
- Follow same patterns used by Scorecard and Qualitative Factors tabs

**Matrix Display**:
```
                    Scorecard Outcome
                 ┌───────┬───────┬───────┬───────┬───────┬───────┐
                 │  Red  │Yellow-│Yellow │Yellow+│Green- │Green  │
┌────────────────┼───────┼───────┼───────┼───────┼───────┼───────┤
│ High           │ High  │ High  │ High  │Medium │Medium │ Low   │
│ Medium         │ High  │ High  │Medium │Medium │ Low   │ Low   │
│ Low            │ High  │Medium │Medium │ Low   │ Low   │ Low   │
│ Very Low       │Medium │Medium │ Low   │ Low   │ Low   │ Low   │
└────────────────┴───────┴───────┴───────┴───────┴───────┴───────┘
  Inherent Risk
```

**Color Coding**:
- High: `bg-red-100 text-red-800 border-red-200`
- Medium: `bg-amber-100 text-amber-800 border-amber-200`
- Low: `bg-green-100 text-green-800 border-green-200`

**API Client**: Create `web/src/api/residualRiskMap.ts`

---

### Task 2: Display Residual Risk on Model Details Page

**Location**: `web/src/pages/ModelDetailsPage.tsx`

**Implementation**:
- Add a "Risk Summary" card/section showing:
  - Current Inherent Risk Tier (from model)
  - Latest Validation Scorecard Outcome (from most recent approved validation)
  - Computed Residual Risk (color-coded badge)
- Only show when model has an approved validation with scorecard

**Data Source**:
- Need to fetch latest approved validation for the model
- Use existing `/validation-workflow/requests/?model_id={id}&status=APPROVED&limit=1` or similar

**Display Example**:
```
┌─────────────────────────────────────────────────────┐
│ Risk Assessment Summary                              │
├─────────────────────────────────────────────────────┤
│ Inherent Risk Tier:    [Medium]                     │
│ Scorecard Outcome:     [Yellow+]                    │
│ Residual Risk:         [Medium] (computed)          │
│                                                     │
│ Based on validation approved 2025-01-15             │
└─────────────────────────────────────────────────────┘
```

---

### Task 3: Add Residual Risk to Overdue Revalidation Report

**Location**: `web/src/pages/OverdueRevalidationReportPage.tsx`

**Implementation**:
- Add "Residual Risk" column to the report table
- Show the residual risk from the most recent approved validation
- Color-coded badge for visual scanning
- Include in CSV export

**Backend Update** (if needed):
- Check if `/overdue-revalidation-report/` endpoint includes `residual_risk`
- May need to add computed field to report response

---

## File Changes Summary

### New Files
1. `web/src/api/residualRiskMap.ts` - API client for residual risk map endpoints

### Modified Files
1. `web/src/pages/TaxonomyPage.tsx` - Add Residual Risk Map configuration tab
2. `web/src/pages/ModelDetailsPage.tsx` - Add Risk Summary section
3. `web/src/pages/OverdueRevalidationReportPage.tsx` - Add Residual Risk column

### Backend Changes Required
1. `api/app/api/overdue_revalidation_report.py` - Add `residual_risk` field to `OverdueRevalidationRecord` schema and populate from validation request's computed property

---

## Implementation Order

1. **API Client** - Create the residual risk map API client
2. **Taxonomy Page** - Add configuration UI (largest change)
3. **Model Details** - Add risk summary display
4. **Overdue Report** - Add residual risk column

---

## Component Structure for Matrix Editor

```
ResidualRiskMapTab/
├── ResidualRiskMapTab.tsx        # Main tab component
├── RiskMatrixTable.tsx           # Matrix display/edit component
├── RiskMatrixCell.tsx            # Individual cell with dropdown
├── VersionHistoryPanel.tsx       # List of previous versions
└── types.ts                      # TypeScript interfaces
```

---

## Acceptance Criteria

### Configuration Page
- [ ] Matrix displays correctly with color coding
- [ ] Admin can edit cells and save new version
- [ ] Version history shows all previous configurations
- [ ] Non-admin users see read-only view

### Model Details
- [ ] Risk summary shows when approved validation exists
- [ ] All three values display with appropriate styling
- [ ] Handles missing data gracefully (shows "N/A" or hides section)

### Overdue Report
- [ ] Residual Risk column displays with color badges
- [ ] Column is sortable
- [ ] Included in CSV export

# Past Due Level Bucket Taxonomy - Fix Plan

This document outlines the plan to complete the bucket taxonomy implementation based on the audit findings.

## Requirements Summary

Based on clarification:
- **Usage**: Display Past Due Level on Overdue Revalidation Report AND Models list/detail pages
- **Frontend UI**: Edit-only (modify existing bucket ranges, not create new bucket taxonomies)
- **Role Restrictions**: Admin-only for bucket taxonomy modifications
- **Test Coverage**: Unit tests + API integration tests

---

## Phase 1: Backend Tests

### 1.1 Unit Tests for Validation Function

Create `api/tests/test_bucket_validation.py` with tests for `validate_bucket_taxonomy_values()`:

**Happy Path Tests:**
- [ ] Empty bucket list returns valid
- [ ] Single unbounded bucket (null, null) returns valid
- [ ] Complete contiguous range (6 buckets like Past Due Level) returns valid
- [ ] Two buckets: (null, 0) and (1, null) returns valid

**Gap Detection Tests:**
- [ ] Gap between buckets detected (e.g., (null, 10) and (15, null) - missing 11-14)
- [ ] Multiple gaps detected

**Overlap Detection Tests:**
- [ ] Overlapping buckets detected (e.g., (null, 10) and (5, null))
- [ ] Exact overlap detected (same min/max)

**Boundary Validation Tests:**
- [ ] First bucket without min_days=null fails
- [ ] Last bucket without max_days=null fails
- [ ] Middle bucket with min_days=null fails
- [ ] Middle bucket with max_days=null fails
- [ ] Single bucket with only min_days=null fails
- [ ] Single bucket with only max_days=null fails

**Edge Cases:**
- [ ] Single-day bucket (min=5, max=5) in middle of range
- [ ] Negative day values (for "days before due date" scenarios)
- [ ] Very large day values

### 1.2 API Integration Tests for Bucket Taxonomies

Create `api/tests/test_taxonomy_buckets.py`:

**CRUD Operations:**
- [ ] Create bucket taxonomy with valid values
- [ ] Create bucket taxonomy value - validation applied
- [ ] Update bucket taxonomy value - validation applied
- [ ] Delete bucket taxonomy value - validation prevents gaps
- [ ] Get bucket taxonomy returns min_days/max_days

**Role Restrictions:**
- [ ] Non-admin cannot modify bucket taxonomy values
- [ ] Non-admin cannot modify bucket taxonomy type
- [ ] Admin can modify bucket taxonomy values
- [ ] Non-admin CAN view bucket taxonomies (read-only)

**Error Handling:**
- [ ] Creating value that causes gap returns 400
- [ ] Creating value that causes overlap returns 400
- [ ] Deleting value that causes gap returns 400

---

## Phase 2: Backend Fixes

### 2.1 Add Admin Role Restriction

File: `api/app/api/taxonomies.py`

**Changes:**
- [ ] Add helper function `require_admin_for_bucket_taxonomy()`
- [ ] In `create_taxonomy_value()`: If taxonomy is bucket type, require admin role
- [ ] In `update_taxonomy_value()`: If taxonomy is bucket type and updating min_days/max_days, require admin role
- [ ] In `delete_taxonomy_value()`: If taxonomy is bucket type, require admin role
- [ ] In `update_taxonomy()`: If changing taxonomy_type to/from bucket, require admin role

### 2.2 Fix CSV Export

File: `api/app/api/taxonomies.py`

**Changes:**
- [ ] Add "Taxonomy Type" column to header
- [ ] Add "Min Days" and "Max Days" columns to header
- [ ] Include taxonomy_type in data rows
- [ ] Include min_days and max_days in data rows (empty string if null)

### 2.3 Fix Audit Log for Delete

File: `api/app/api/taxonomies.py`

**Changes:**
- [ ] In `delete_taxonomy_value()`: Add min_days and max_days to changes dict for bucket values

### 2.4 Add Past Due Level Calculation Endpoint

File: `api/app/api/models.py` (or new file `api/app/api/past_due.py`)

**New Endpoint:**
```python
GET /models/{model_id}/past-due-level
```

**Response:**
```json
{
  "model_id": 1,
  "days_past_due": 45,
  "past_due_level": {
    "value_id": 123,
    "code": "MINIMAL",
    "label": "Minimal",
    "description": "Model is 1-365 days past due"
  }
}
```

**Logic:**
- [ ] Calculate days since revalidation due date (use existing logic from overdue report)
- [ ] Query Past Due Level taxonomy values
- [ ] Find matching bucket based on days_past_due
- [ ] Return the matching taxonomy value

### 2.5 Add Past Due Level to Model List/Detail Responses

File: `api/app/api/models.py`, `api/app/schemas/model.py`

**Changes:**
- [ ] Add `past_due_level` field to ModelResponse schema (optional)
- [ ] Add `days_past_due` field to ModelResponse schema (optional, nullable)
- [ ] Calculate and include in model list endpoint (with query param to enable?)
- [ ] Calculate and include in model detail endpoint

### 2.6 Enhance Overdue Revalidation Report

File: `api/app/api/overdue_revalidation_report.py`

**Changes:**
- [ ] Add `past_due_level_code` and `past_due_level_label` to response items
- [ ] Add summary statistics by past due level (count per bucket)
- [ ] Add filter parameter `?past_due_level=CRITICAL,OBSOLETE`

---

## Phase 3: Frontend Updates

### 3.1 Add TypeScript Types

File: `web/src/types/taxonomy.ts` (new file)

```typescript
export interface TaxonomyValue {
  value_id: number;
  taxonomy_id: number;
  code: string;
  label: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  min_days: number | null;
  max_days: number | null;
  created_at: string;
}

export interface Taxonomy {
  taxonomy_id: number;
  name: string;
  description: string | null;
  is_system: boolean;
  taxonomy_type: 'standard' | 'bucket';
  created_at: string;
  values: TaxonomyValue[];
}
```

### 3.2 Update TaxonomyPage for Bucket Display/Edit

File: `web/src/pages/TaxonomyPage.tsx`

**Display Changes:**
- [ ] Show "Type" badge next to taxonomy name (Standard/Bucket)
- [ ] For bucket taxonomies, show "Range" column in values table
- [ ] Format range display: "≤ 0 days", "1 - 365 days", "≥ 1826 days"

**Edit Changes (Admin Only):**
- [ ] Add min_days and max_days fields to value edit form (only for bucket taxonomies)
- [ ] Show validation errors from API (gap/overlap messages)
- [ ] Disable bucket field editing for non-admin users
- [ ] Show info message: "Bucket ranges must be contiguous with no gaps or overlaps"

**UI Mockup for Bucket Values Table:**
```
| Code      | Label       | Range           | Active | Actions |
|-----------|-------------|-----------------|--------|---------|
| CURRENT   | Current     | ≤ 0 days        | Yes    | Edit    |
| MINIMAL   | Minimal     | 1 - 365 days    | Yes    | Edit    |
| MODERATE  | Moderate    | 366 - 730 days  | Yes    | Edit    |
| SIGNIFICANT| Significant| 731 - 1095 days | Yes    | Edit    |
| CRITICAL  | Critical    | 1096 - 1825 days| Yes    | Edit    |
| OBSOLETE  | Obsolete    | ≥ 1826 days     | Yes    | Edit    |
```

### 3.3 Update Overdue Revalidation Report Page

File: `web/src/pages/OverdueRevalidationReportPage.tsx`

**Changes:**
- [ ] Add "Past Due Level" column to the table
- [ ] Color-code rows by past due level (green=Current, yellow=Minimal, orange=Moderate, red=Significant, dark red=Critical, black=Obsolete)
- [ ] Add filter dropdown for Past Due Level
- [ ] Add summary cards showing count by past due level
- [ ] Include past_due_level in CSV export

### 3.4 Update Models List Page

File: `web/src/pages/ModelsPage.tsx`

**Changes:**
- [ ] Add "Past Due Level" column (optional, maybe behind a toggle or only for overdue models)
- [ ] Color-code the past due level badge
- [ ] Add filter for Past Due Level
- [ ] Include in CSV export

### 3.5 Update Model Details Page

File: `web/src/pages/ModelDetailsPage.tsx`

**Changes:**
- [ ] Show Past Due Level in the validation/compliance section
- [ ] Display as colored badge with label
- [ ] Show days past due number

---

## Phase 4: Cleanup

### 4.1 Fix Duplicate JSON File

File: `PAST_DUE_CAT.json`

- [ ] Remove duplicate content (lines 37-73)
- [ ] Or delete file if no longer needed

### 4.2 Update CLAUDE.md

- [ ] Document bucket taxonomy feature
- [ ] Add to Taxonomy System section

### 4.3 Update ARCHITECTURE.md

- [ ] Add bucket taxonomy to data model documentation

---

## Implementation Order

1. **Phase 1.1**: Unit tests for validation function
2. **Phase 1.2**: API integration tests
3. **Phase 2.1**: Admin role restrictions
4. **Phase 2.2-2.3**: CSV export and audit log fixes
5. **Phase 3.1**: TypeScript types
6. **Phase 3.2**: TaxonomyPage bucket UI
7. **Phase 2.4-2.6**: Past due level calculation and API enhancements
8. **Phase 3.3-3.5**: Frontend integration (Report, Models pages)
9. **Phase 4**: Cleanup

---

## Estimated File Changes

| File | Type | Changes |
|------|------|---------|
| `api/tests/test_bucket_validation.py` | New | Unit tests for validation |
| `api/tests/test_taxonomy_buckets.py` | New | API integration tests |
| `api/app/api/taxonomies.py` | Modify | Role checks, CSV, audit log |
| `api/app/api/models.py` | Modify | Past due level in responses |
| `api/app/api/overdue_revalidation_report.py` | Modify | Past due level integration |
| `api/app/schemas/model.py` | Modify | Add past_due_level field |
| `web/src/types/taxonomy.ts` | New | TypeScript interfaces |
| `web/src/pages/TaxonomyPage.tsx` | Modify | Bucket UI |
| `web/src/pages/OverdueRevalidationReportPage.tsx` | Modify | Past due level column |
| `web/src/pages/ModelsPage.tsx` | Modify | Past due level column |
| `web/src/pages/ModelDetailsPage.tsx` | Modify | Past due level display |
| `PAST_DUE_CAT.json` | Delete/Fix | Remove duplicates |
| `CLAUDE.md` | Modify | Documentation |
| `ARCHITECTURE.md` | Modify | Documentation |

---

## Success Criteria

- [ ] All new tests pass
- [ ] Existing tests still pass (regression)
- [ ] Admin can edit bucket ranges in TaxonomyPage
- [ ] Non-admin can view but not edit bucket taxonomies
- [ ] Overdue Revalidation Report shows Past Due Level for each model
- [ ] Models list/detail shows Past Due Level
- [ ] CSV exports include new fields
- [ ] TypeScript compiles without errors

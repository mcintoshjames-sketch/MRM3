# Demo Data Guide - Overdue Validation Dashboard

This document explains the demo models created to illustrate the overdue validation logic.

## Overview

The seed script creates 5 demo models that demonstrate different stages of the validation lifecycle for **Tier 2 models** (18-month re-validation frequency, 90-day validation lead time).

## Business Rules Reference

For Tier 2 models:
- **Re-Validation Frequency:** 18 months
- **Grace Period:** 3 months (for submission)
- **Validation Lead Time:** 90 days
- **Total Overdue Threshold:** 18 months + 3 months + 90 days = **~21.5 months**

## Demo Models

### 1. Demo: Overdue Model ⚠️ CRITICAL
- **Last Validated:** 24 months ago (~Nov 2023)
- **Risk Tier:** Tier 2 (Medium)
- **Status:** **OVERDUE** - Past all deadlines
- **Timeline:**
  - Submission due: 6 months ago
  - Submission overdue: 3 months ago
  - Validation overdue: Now (overdue by ~2.5 months)
- **Action Required:** Immediate validation needed

### 2. Demo: Submission Overdue ⚠️ URGENT
- **Last Validated:** 20 months ago (~Mar 2024)
- **Risk Tier:** Tier 2 (Medium)
- **Status:** **NOT YET OVERDUE** (but will be soon)
- **Timeline:**
  - Submission due: 2 months ago
  - Submission overdue: 1 month from now (still within grace)
  - Validation overdue: ~4 months from now
- **Action Required:** Submit validation request within 1 month

### 3. Demo: Due Soon 📅 APPROACHING
- **Last Validated:** 17 months ago (~Jun 2024)
- **Risk Tier:** Tier 2 (Medium)
- **Status:** **NOT OVERDUE** - Within normal cycle
- **Timeline:**
  - Submission due: 1 month from now
  - Submission overdue: 4 months from now
  - Validation overdue: ~7 months from now
- **Action Required:** Plan validation submission for next month

### 4. Demo: Never Validated ❌ CRITICAL
- **Last Validated:** Never
- **Risk Tier:** Tier 3 (Low)
- **Status:** **NEVER VALIDATED**
- **Action Required:** Initial validation required

### 5. Demo: Compliant Model ✅ OK
- **Last Validated:** 6 months ago (~May 2025)
- **Risk Tier:** Tier 2 (Medium)
- **Status:** **COMPLIANT** - Well within compliance
- **Timeline:**
  - Submission due: 12 months from now
  - Submission overdue: 15 months from now
  - Validation overdue: ~18.5 months from now
- **Action Required:** None - operating normally

## Testing the Dashboard

1. **Login as Admin:**
   ```bash
   Email: admin@example.com
   Password: admin123
   ```

2. **Navigate to Admin Dashboard:**
   - The "Overdue Validations" section should show 2 models:
     - **Demo: Overdue Model** (24 months old - OVERDUE)
     - **Demo: Never Validated** (no validation history)

3. **Expected Results:**
   - "Demo: Submission Overdue" should **NOT** appear (still within lead time window)
   - "Demo: Due Soon" should **NOT** appear (not yet due)
   - "Demo: Compliant Model" should **NOT** appear (recently validated)

## Calculation Examples

### Model A (Overdue Model - 24 months ago)
```
Last Validation:     Nov 30, 2023
Submission Due:      May 30, 2025  (+ 18 months)
Submission Overdue:  Aug 30, 2025  (+ 3 months grace)
Validation Overdue:  Nov 28, 2025  (+ 90 days)
Today:              Nov 19, 2025   → OVERDUE by ~9 days
```

### Model B (Submission Overdue - 20 months ago)
```
Last Validation:     Mar 29, 2024
Submission Due:      Sep 29, 2025  (+ 18 months)
Submission Overdue:  Dec 29, 2025  (+ 3 months grace)
Validation Overdue:  Mar 29, 2026  (+ 90 days)
Today:              Nov 19, 2025   → Still within lead time window
```

## Updating Demo Data

The demo models are created automatically by the seed script. To refresh them:

```bash
# Delete existing demo models
docker compose exec db psql -U mrm_user -d mrm_db -c "DELETE FROM models WHERE model_name LIKE 'Demo:%';"

# Re-run seed script
docker compose exec api python -m app.seed
```

## Notes

- Demo models are created with `status='Active'` to appear in overdue checks
- All demo models are owned by the admin user
- Validations are marked as "PASS" with generic findings summaries
- The seed script is idempotent - running it multiple times won't create duplicates

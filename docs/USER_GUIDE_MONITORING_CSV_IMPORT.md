# Model Performance Monitoring: CSV Import Guide

This guide explains how to bulk import monitoring results using CSV files.

## Overview

The CSV import feature allows you to efficiently enter monitoring results for multiple models and metrics at once, rather than entering them one by one through the UI. This is particularly useful when:

- You have results from external monitoring systems
- You need to enter data for many models in a monitoring plan
- You want to transfer results from spreadsheets

## CSV Format Requirements

### Required Columns

Your CSV file must include the following columns:

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `model_id` | Integer | Yes | The model ID from the monitoring plan |
| `metric_id` | Integer | Yes | The metric ID from the monitoring plan |
| `value` | Decimal | Conditional | Numeric value (required for quantitative metrics) |
| `outcome` | Text | Optional | Outcome code: GREEN, YELLOW, or RED |
| `narrative` | Text | Optional | Commentary or explanation |

### Example CSV

```csv
model_id,metric_id,value,outcome,narrative
1,101,0.85,,Model performing well
1,102,0.92,,Above target
2,101,0.67,,Below threshold - under review
2,102,0.78,,Acceptable performance
3,101,,,Qualitative assessment
3,102,,GREEN,Manual override for qualitative metric
```

## Important Rules

### Quantitative vs Qualitative Metrics

The system handles metrics differently based on their type:

**Quantitative Metrics (numeric-based)**
- **Must provide a numeric `value`** - the `outcome` column is ignored
- Outcome (GREEN/YELLOW/RED) is automatically calculated from configured thresholds
- If you provide an outcome value, it will be silently ignored

**Qualitative Metrics (judgment-based)**
- Numeric `value` is optional
- You may provide an explicit `outcome` (GREEN, YELLOW, or RED)
- Outcome is not calculated from thresholds

### Validation Rules

The import will reject rows with:
- Invalid or missing `model_id`
- Invalid or missing `metric_id`
- Model not included in the monitoring plan
- Metric not included in the monitoring plan
- Invalid numeric value (non-numeric text in value column)
- Invalid outcome code (must be GREEN, YELLOW, RED, or empty)
- Quantitative metric without a numeric value

### Cycle Status Requirements

CSV import is only available when the monitoring cycle is in one of these statuses:
- **Data Collection** - Primary data entry phase
- **Under Review** - Review phase where corrections can still be made

Import is blocked when the cycle is in:
- Pending
- Pending Approval
- Approved
- Rejected

## Import Process

### Step 1: Download Template

From the Monitoring Cycle page, click **"Import CSV"** to open the import panel. Use the **"Download Template"** button to get a pre-populated CSV with:
- All valid model IDs and names for the plan
- All valid metric IDs and names for the plan
- Empty columns for value, outcome, and narrative

### Step 2: Prepare Your Data

Fill in your CSV file following these guidelines:

1. Keep the header row unchanged
2. Enter one result per row (model + metric combination)
3. For quantitative metrics, always provide a numeric value
4. For qualitative metrics, provide an outcome code if known
5. Add narrative comments as needed

### Step 3: Preview (Dry Run)

Upload your CSV file with **"Preview"** mode enabled (default). This shows:

- **Valid Rows**: Rows that will be processed, showing whether each is a new entry ("create") or updating an existing entry ("update")
- **Error Rows**: Rows that will be skipped, with specific error messages
- **Summary**: Total counts of creates, updates, and errors

**Review the preview carefully before proceeding!**

### Step 4: Execute Import

Once satisfied with the preview:

1. Click **"Execute Import"** to process the data
2. The system will create new results and update existing ones
3. A summary shows the final counts

## Outcome Calculation

### How Thresholds Work

For quantitative metrics, outcomes are calculated using configured thresholds:

| Zone | Condition |
|------|-----------|
| **RED** | Value < red_min OR value > red_max |
| **YELLOW** | Value < yellow_min OR value > yellow_max (but not in RED zone) |
| **GREEN** | All other values (within acceptable range) |
| **UNCONFIGURED** | No thresholds configured for this metric |

### Example

If a metric has:
- `red_max = 0.95` (values > 95% are RED)
- `yellow_max = 0.90` (values > 90% are YELLOW)

Then:
- Value 0.97 → RED
- Value 0.92 → YELLOW
- Value 0.85 → GREEN

## Common Issues and Solutions

### "Model X is not in this monitoring plan"

The model ID in your CSV doesn't match any model in the current monitoring plan. Check:
- You're importing to the correct monitoring cycle
- The model hasn't been removed from the plan
- You're using the correct model ID (from the template)

### "Metric X is not in this monitoring plan"

The metric ID doesn't match any active metric in the plan. Check:
- The metric is still active in the plan configuration
- You're using the correct metric ID (from the template)

### "Quantitative metrics require a numeric value"

You tried to import a row for a quantitative metric without a value. For quantitative metrics, you must always provide a numeric value - the outcome cannot be set directly.

### "Invalid numeric value"

The value column contains non-numeric text. Ensure values are:
- Plain numbers (e.g., `0.85`, `95`, `1.23`)
- No currency symbols, percentages, or other characters
- Use period (.) as decimal separator

### "Invalid outcome"

The outcome column contains an unrecognized value. Valid options are:
- `GREEN`
- `YELLOW`
- `RED`
- Empty (blank)

Case doesn't matter (green, Green, GREEN all work).

## Permissions

To import CSV results, you must have one of:
- **Plan Owner**: You created or own the monitoring plan
- **Team Member**: You're a member of the plan's monitoring team
- **Admin**: System administrator role

## API Reference

For programmatic access, the import endpoint is:

```
POST /monitoring/cycles/{cycle_id}/results/import
```

Parameters:
- `file`: CSV file (multipart/form-data)
- `dry_run`: Boolean (default: true) - Preview without saving

Response includes:
- `valid_rows`: Array of processable rows with actions
- `error_rows`: Array of rejected rows with error messages
- `summary`: Counts of total, created, updated, skipped, and errors

## Best Practices

1. **Always preview first** - Use dry run mode to catch errors before importing
2. **Use the template** - Download the template to ensure correct IDs
3. **Import in batches** - For very large datasets, consider splitting into multiple files
4. **Review thresholds** - Ensure metric thresholds are configured before importing quantitative data
5. **Document changes** - Use the narrative column to explain notable values
6. **Verify after import** - Review the imported results in the UI to confirm accuracy

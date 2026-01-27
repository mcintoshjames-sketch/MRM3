# Point-in-Time Compliance Snapshot for Model Versions

## Overview

The system captures a **point-in-time snapshot** of whether each model change required MV (Model Validation) approval at the time the change was submitted. This enables accurate compliance reporting even if taxonomy rules change over time.

## Feature Details

### Database Field

**Table**: `model_versions`
**Column**: `change_requires_mv_approval` (Boolean, nullable)

```sql
change_requires_mv_approval BOOLEAN NULL
COMMENT 'Point-in-time snapshot: Did this change require MV approval at submission time?'
```

### Capture Logic

When a model version is created (`POST /models/{model_id}/versions`):

1. **If `change_type_id` is provided**:
   - Lookup the `ModelChangeType` in the taxonomy
   - Capture its `requires_mv_approval` value at write time
   - Store in `change_requires_mv_approval` field

2. **If only legacy `change_type` ("MAJOR"/"MINOR") is provided**:
   - MAJOR → `change_requires_mv_approval = True`
   - MINOR → `change_requires_mv_approval = False`

3. **Snapshot is immutable**: Once captured, it never changes, preserving historical compliance state

## Use Cases

### 1. Non-Compliance Detection

Find all changes that required approval but lack validation:

```sql
SELECT
    version_id,
    version_number,
    change_description,
    created_at,
    created_by_id
FROM model_versions
WHERE change_requires_mv_approval = true
  AND validation_request_id IS NULL
ORDER BY created_at DESC;
```

### 2. Compliance Rate Reporting

Calculate annual compliance rates:

```sql
SELECT
    EXTRACT(YEAR FROM created_at) as year,
    COUNT(*) FILTER (
        WHERE change_requires_mv_approval AND validation_request_id IS NOT NULL
    ) as compliant_changes,
    COUNT(*) FILTER (
        WHERE change_requires_mv_approval AND validation_request_id IS NULL
    ) as non_compliant_changes,
    COUNT(*) FILTER (
        WHERE change_requires_mv_approval
    ) as total_requiring_approval,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE change_requires_mv_approval AND validation_request_id IS NOT NULL
        ) / NULLIF(COUNT(*) FILTER (WHERE change_requires_mv_approval), 0),
        2
    ) as compliance_rate_pct
FROM model_versions
WHERE change_requires_mv_approval IS NOT NULL
GROUP BY year
ORDER BY year DESC;
```

### 3. Model-Specific Compliance History

Track compliance for a specific model:

```sql
SELECT
    mv.version_number,
    mv.change_description,
    mv.change_requires_mv_approval as required_approval,
    mv.validation_request_id IS NOT NULL as has_validation,
    vr.current_status_id as validation_status,
    mv.created_at
FROM model_versions mv
LEFT JOIN validation_requests vr ON mv.validation_request_id = vr.request_id
WHERE mv.model_id = 1
  AND mv.change_requires_mv_approval IS NOT NULL
ORDER BY mv.created_at DESC;
```

### 4. Taxonomy Change Impact Analysis

Identify how many historical versions would be affected if taxonomy rules changed:

```sql
-- Example: How many versions would be affected if we changed
-- "Bug Fixes" (change_type_id=7) to NOT require approval?
SELECT
    COUNT(*) as affected_versions,
    COUNT(*) FILTER (WHERE validation_request_id IS NULL) as without_validation
FROM model_versions
WHERE change_type_id = 7
  AND change_requires_mv_approval = true;
```

## Benefits

| Benefit | Description |
|---------|-------------|
| **Historical Accuracy** | Compliance audits can reference exact requirements at time of change |
| **Regulatory Reporting** | Generate accurate historical compliance reports for regulators |
| **Taxonomy Evolution** | Admin can safely modify taxonomy rules without losing historical context |
| **Audit Trail** | Complete record of whether each change followed approval requirements in effect |
| **Non-Compliance Detection** | Quickly identify changes that bypassed required validation |

## API Response

The `change_requires_mv_approval` field is included in all model version API responses:

```json
{
  "version_id": 68,
  "version_number": "10.0",
  "change_type": "MAJOR",
  "change_type_id": 1,
  "change_description": "New Model Development",
  "change_requires_mv_approval": true,
  "validation_request_id": 50,
  "status": "DRAFT",
  "created_at": "2025-11-23T15:24:16.485128",
  "created_by_id": 1
}
```

## Migration and Backfill

### Migration: `4b1d659c419b_add_mv_approval_snapshot_to_versions`

1. **Add column** as nullable
2. **Backfill existing data** from current taxonomy state:
   - For versions with `change_type_id`: Use current `requires_mv_approval` from taxonomy
   - For legacy versions without `change_type_id`: Use MAJOR=True, MINOR=False
3. **Leave nullable** for future flexibility

### Backfill Accuracy

The backfill uses the **current state** of the taxonomy as the best approximation of historical requirements. This is acceptable because:
- The taxonomy was just established (no historical changes yet)
- The seeded data represents the organization's long-standing policies
- For any discrepancies, the `validation_request_id` field provides ground truth

## Testing

Run the compliance snapshot test:

```bash
./test_compliance_snapshot.sh
```

Expected results:
- Creates a version with change type that requires MV approval
- Verifies snapshot is captured correctly
- Confirms snapshot persists in database and API responses
- Demonstrates compliance query patterns

## Audit Trail for Taxonomy Changes

**In addition to point-in-time snapshots**, the system maintains a **complete audit trail** of when approval requirements are changed in the taxonomy.

### Tracking Taxonomy Changes

All changes to change types are automatically logged in the audit_logs table:

```sql
-- Find all historical changes to approval requirements
SELECT
    al.timestamp,
    al.action,
    u.email as changed_by,
    al.changes->>'requires_mv_approval' as approval_change
FROM audit_logs al
JOIN users u ON al.user_id = u.user_id
WHERE al.entity_type = 'ModelChangeType'
  AND al.changes ? 'requires_mv_approval'
ORDER BY al.timestamp DESC;
```

### Example Audit Log Entry

```json
{
  "log_id": 190,
  "entity_type": "ModelChangeType",
  "entity_id": 13,
  "action": "UPDATE",
  "user_id": 1,
  "changes": {
    "requires_mv_approval": {
      "old": false,
      "new": true
    }
  },
  "timestamp": "2025-11-23T15:52:56.755750",
  "user": {
    "email": "admin@example.com",
    "full_name": "Admin User"
  }
}
```

### Complete Compliance Coverage

The system provides **two complementary audit mechanisms**:

| Mechanism | Purpose | Query Target |
|-----------|---------|--------------|
| **Point-in-Time Snapshot** | What were the approval requirements when THIS change was submitted? | `model_versions.change_requires_mv_approval` |
| **Taxonomy Audit Trail** | When did we change the approval requirements for THIS change type? | `audit_logs` (entity_type='ModelChangeType') |

**Combined Query Example** - Prove compliance for a specific version:
```sql
-- Show the approval requirement at submission time AND the history of taxonomy changes
SELECT
    mv.version_id,
    mv.version_number,
    mv.change_requires_mv_approval as required_approval_at_submission,
    mv.created_at as submitted_at,
    (
        SELECT json_agg(
            json_build_object(
                'timestamp', al.timestamp,
                'changed_by', u.email,
                'old_value', (al.changes->'requires_mv_approval'->>'old')::boolean,
                'new_value', (al.changes->'requires_mv_approval'->>'new')::boolean
            )
        )
        FROM audit_logs al
        JOIN users u ON al.user_id = u.user_id
        WHERE al.entity_type = 'ModelChangeType'
          AND al.entity_id = mv.change_type_id
          AND al.changes ? 'requires_mv_approval'
          AND al.timestamp < mv.created_at
        ORDER BY al.timestamp DESC
    ) as taxonomy_change_history
FROM model_versions mv
WHERE mv.version_id = 68;
```

This query proves:
1. What the requirement was when the version was submitted (snapshot)
2. Complete history of how that requirement evolved over time (audit trail)

## Related Files

- **Model**: [api/app/models/model_version.py](api/app/models/model_version.py)
- **Schema**: [api/app/schemas/model_version.py](api/app/schemas/model_version.py)
- **Endpoint**: [api/app/api/model_versions.py](api/app/api/model_versions.py) - `create_model_version()`
- **Taxonomy API**: [api/app/api/model_change_taxonomy.py](api/app/api/model_change_taxonomy.py) - Audit logging on CREATE/UPDATE/DELETE
- **Migration**: [api/alembic/versions/4b1d659c419b_add_mv_approval_snapshot_to_versions.py](api/alembic/versions/4b1d659c419b_add_mv_approval_snapshot_to_versions.py)
- **Test Scripts**:
  - [test_compliance_snapshot.sh](test_compliance_snapshot.sh) - Point-in-time snapshot test
  - [test_taxonomy_audit_trail.py](/tmp/test_taxonomy_audit_trail.py) - Taxonomy change audit trail test

## Future Enhancements

1. **Dashboard Widget**: Show compliance rate trends over time
2. **Automated Alerts**: Notify admins when non-compliant changes are detected
3. **Compliance Report**: Generate PDF reports for regulatory submissions
4. **Grace Period Tracking**: Track if validation was completed within required timeframe

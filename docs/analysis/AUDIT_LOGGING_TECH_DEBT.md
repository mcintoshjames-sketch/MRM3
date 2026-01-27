# Audit Logging Technical Debt

**Created**: 2025-11-23
**Status**: Documented for future implementation

## Overview

This document tracks audit logging gaps identified during the compliance audit logging review. All **High Priority** items have been implemented. This document covers **Medium** and **Low Priority** items for future consideration.

---

## ✅ Implemented (Complete Audit Trail Coverage)

The following have been **completed** and have full audit trail coverage:

| Entity | Operations | File | Status |
|--------|-----------|------|--------|
| **Validation Policies** | CREATE, UPDATE, DELETE | [validation_policies.py](api/app/api/validation_policies.py) | ✅ Complete |
| **Users** | CREATE, UPDATE, DELETE, PROVISION | [auth.py](api/app/api/auth.py) | ✅ Complete |
| **Workflow SLA Configuration** | UPDATE | [workflow_sla.py](api/app/api/workflow_sla.py) | ✅ Complete |
| **Regions** | CREATE, UPDATE, DELETE | [regions.py](api/app/api/regions.py) | ✅ Complete |
| **Taxonomies** | CREATE, UPDATE, DELETE | [taxonomies.py](api/app/api/taxonomies.py) | ✅ Complete |
| **Taxonomy Values** | CREATE, UPDATE, DELETE | [taxonomies.py](api/app/api/taxonomies.py) | ✅ Complete |
| **Models** | CREATE, UPDATE, DELETE, APPROVE, SEND_BACK, RESUBMIT | [models.py](api/app/api/models.py) | ✅ Already Complete |
| **Model Versions** | CREATE, UPDATE | [model_versions.py](api/app/api/model_versions.py) | ✅ Already Complete |
| **Model Change Taxonomy** | CREATE, UPDATE, DELETE | [model_change_taxonomy.py](api/app/api/model_change_taxonomy.py) | ✅ Complete |
| **Model Delegates** | ADD, REVOKE | [model_delegates.py](api/app/api/model_delegates.py) | ✅ Already Complete |
| **Validation Workflow** | 29+ operations | [validation_workflow.py](api/app/api/validation_workflow.py) | ✅ Already Complete |

---

## 🚫 Explicitly Excluded (By Request)

### Vendors ([vendors.py](api/app/api/vendors.py))

**Operations**: CREATE, UPDATE, DELETE

**Status**: ❌ **Excluded by user request**

**Business Context**:
- Third-party vendor management is part of model governance
- Changes affect which vendors are available for third-party model selection
- Less critical than policy/taxonomy changes

**Decision**: User explicitly requested to omit audit logging for vendor operations. If this decision changes in the future, implementation would be straightforward (1-2 hours) following the established pattern.

---

## 🟢 Low Priority - Operational (Not Yet Implemented)

### Version Deployment Tasks ([version_deployment_tasks.py](api/app/api/version_deployment_tasks.py))

**Missing Operations**: CONFIRM, ADJUST, CANCEL

**Business Justification**:
- Deployment task actions are operational rather than compliance-critical
- Already tracked indirectly through:
  - Model versions (actual_production_date changes)
  - Model regions (deployment confirmations)
  - Validation workflow (approval before deployment)

**Example Use Cases**:
- Tracking deployment date adjustments
- Recording deployment cancellations
- Audit trail of who confirmed deployments

**Implementation Effort**: Low (1-2 hours)

**Recommendation**: Defer indefinitely unless:
1. Specific regulatory requirement emerges
2. Disputes occur about deployment actions
3. Operational reporting needs arise

**Alternative**: Current indirect tracking through related entities is sufficient for compliance purposes.

---

## Implementation Patterns

If implementing any of these in the future, follow this established pattern:

### 1. Add Audit Log Import and Helper
```python
from app.models.audit_log import AuditLog

def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)
```

### 2. CREATE Operations
```python
db.add(entity)
db.flush()  # Get entity_id before audit log

create_audit_log(
    db=db,
    entity_type="EntityName",
    entity_id=entity.id,
    action="CREATE",
    user_id=current_user.user_id,
    changes={"field1": value1, "field2": value2}
)

db.commit()
```

### 3. UPDATE Operations
```python
# Track changes
changes = {}

if update_data.field != entity.field:
    changes["field"] = {
        "old": entity.field,
        "new": update_data.field
    }
    entity.field = update_data.field

# Create audit log if changes made
if changes:
    create_audit_log(
        db=db,
        entity_type="EntityName",
        entity_id=entity_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes=changes
    )

db.commit()
```

### 4. DELETE Operations
```python
# Audit log BEFORE deletion
create_audit_log(
    db=db,
    entity_type="EntityName",
    entity_id=entity_id,
    action="DELETE",
    user_id=current_user.user_id,
    changes={"name": entity.name, "other_key_fields": entity.value}
)

db.delete(entity)
db.commit()
```

---

## Query Patterns for Audit Logs

### Find All Changes to a Specific Entity
```sql
SELECT al.*, u.email as changed_by
FROM audit_logs al
JOIN users u ON al.user_id = u.user_id
WHERE al.entity_type = 'EntityName'
  AND al.entity_id = 123
ORDER BY al.timestamp DESC;
```

### Find All Changes by a Specific User
```sql
SELECT al.*, u.email
FROM audit_logs al
JOIN users u ON al.user_id = u.user_id
WHERE u.email = 'admin@example.com'
ORDER BY al.timestamp DESC;
```

### Find Specific Field Changes
```sql
SELECT
    al.entity_id,
    al.timestamp,
    u.email,
    al.changes->>'field_name' as field_change
FROM audit_logs al
JOIN users u ON al.user_id = u.user_id
WHERE al.entity_type = 'EntityName'
  AND al.changes ? 'field_name'
ORDER BY al.timestamp DESC;
```

---

## Prioritization Rationale

### Why High Priority Items Were Implemented First:

1. **Validation Policies**: Direct impact on compliance schedules and validation requirements
2. **Users**: Security-critical access control and role management
3. **Workflow SLA Configuration**: Defines compliance timelines and violation triggers
4. **Regions**: Geographic/regulatory scope affects compliance reporting
5. **Model Change Taxonomy**: Determines if changes require approval (compliance-critical)
6. **Taxonomies**: Classification system changes affect reporting and categorization

### Why Vendors Were Excluded:

- **Vendors**: Less frequently changed, not directly tied to regulatory schedules
- **User Decision**: Explicitly requested to omit vendor audit logging
- **Rationale**: Less critical than policy/taxonomy changes

### Why Low Priority Items Are Optional:

- **Deployment Tasks**: Already captured indirectly through version and validation tracking
- Operational rather than compliance-focused

---

## Review Schedule

**Next Review**: When any of the following occur:
1. Regulatory audit identifies gaps
2. Taxonomy or vendor changes become frequent
3. Disputes arise about historical changes
4. New compliance requirements emerge

**Last Updated**: 2025-11-23 (Updated after implementing Taxonomies)
**Reviewed By**: System Implementation

---

## Related Documentation

- [COMPLIANCE_SNAPSHOT.md](COMPLIANCE_SNAPSHOT.md) - Point-in-time compliance tracking
- [api/app/api/audit_logs.py](api/app/api/audit_logs.py) - Audit log query API
- [api/app/models/audit_log.py](api/app/models/audit_log.py) - Audit log data model

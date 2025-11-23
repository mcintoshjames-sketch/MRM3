# Change Type Orphan Handling

## Summary

The system implements **multi-layered orphan protection** to prevent data loss when change types are deleted or modified.

## Protection Layers

### 1. Database Level - SET NULL Constraint
```sql
FOREIGN KEY (change_type_id)
REFERENCES model_change_types(change_type_id)
ON DELETE SET NULL
```

**Behavior**: If a change type is deleted, `model_version.change_type_id` is set to NULL rather than:
- ❌ Deleting the version (CASCADE)
- ❌ Blocking the delete (RESTRICT)
- ❌ Causing an error (NO ACTION)

**Purpose**: Last-resort safety net if application-level checks fail.

### 2. Application Level - Reference Check Before Delete

**Backend** (`api/app/api/model_change_taxonomy.py:356-394`):
```python
@router.delete("/change-taxonomy/types/{change_type_id}")
def delete_change_type(change_type_id: int, force: bool = False):
    # Check for references in model_versions
    version_count = db.query(ModelVersion).filter(
        ModelVersion.change_type_id == change_type_id
    ).count()

    if version_count > 0 and not force:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {version_count} model version(s) reference this change type. "
                   f"Consider deactivating instead or use force=true."
        )
```

**Behavior**:
- ✅ Prevents deletion if ANY model versions reference the change type
- ✅ Returns HTTP 409 Conflict with helpful message
- ✅ Suggests deactivation as alternative
- ✅ Allows `force=true` override for admin emergencies

### 3. Frontend - Guided User Experience

**Frontend** (`web/src/pages/TaxonomyPage.tsx:307-340`):
```typescript
const handleDeleteChangeType = async (changeTypeId: number) => {
    try {
        await api.delete(`/change-taxonomy/types/${changeTypeId}`);
        fetchChangeCategories();
    } catch (error: any) {
        if (error.response?.status === 409) {
            const deactivate = confirm(
                `${errorMessage}\n\n` +
                `Would you like to deactivate this change type instead? ` +
                `This will hide it from dropdowns while preserving historical data.`
            );

            if (deactivate) {
                await api.patch(`/change-taxonomy/types/${changeTypeId}`, {
                    is_active: false
                });
            }
        }
    }
};
```

**User Flow**:
1. Admin clicks "Delete" on a change type
2. If referenced by versions: Shows error with count
3. Offers to **deactivate instead** via confirm dialog
4. If user accepts: Deactivates type automatically
5. Result: Historical data preserved, future use prevented

### 4. Active/Inactive Filtering

**API Endpoint** (`/change-taxonomy/categories`):
- **Default**: `active_only=true` - Returns only active types (for user dropdowns)
- **Admin UI**: `active_only=false` - Returns all types (to manage inactive ones)

**SubmitChangeModal** (user-facing):
```typescript
// Uses default endpoint (active_only=true)
const categoryData = await changeTaxonomyApi.getCategories();
// Result: Only active types shown in dropdown
```

**TaxonomyPage** (admin-facing):
```typescript
// Explicitly requests all types
const response = await api.get('/change-taxonomy/categories?active_only=false');
// Result: Admin can see and manage inactive types
```

## Recommended Workflow

### ❌ **DO NOT** Delete Change Types That Are In Use

### ✅ **DO** Deactivate Instead

**Steps**:
1. Go to **Taxonomy Management** → **Change Type Taxonomy** tab
2. Select the category containing the change type
3. Click **Edit** on the change type
4. Uncheck **"Active"** checkbox
5. Click **Update**

**Result**:
- ✅ Historical model versions retain their change type reference
- ✅ Change type hidden from "Submit Model Change" dropdown
- ✅ Change type visible in admin UI with "Inactive" badge
- ✅ Can be reactivated later if needed
- ✅ Audit trail preserved

### Emergency Force Delete

If you absolutely must delete a change type with references:

```bash
curl -X DELETE "http://localhost:8001/change-taxonomy/types/2?force=true" \
  -H "Authorization: Bearer $TOKEN"
```

**Warning**: This will set `change_type_id = NULL` on all referencing model versions. Use only in exceptional circumstances.

## Benefits

| Approach | Data Preservation | User Experience | Reversible |
|----------|-------------------|-----------------|------------|
| **Deactivate** (Recommended) | ✅ Full | ✅ Clean | ✅ Yes |
| **Delete with Protection** | ✅ Full | ⚠️ Error message | ❌ No |
| **Force Delete** | ❌ Partial loss | ⚠️ Silent data loss | ❌ No |

## Testing

Run the orphan protection test:
```bash
./test_orphan_protection.sh
```

Expected behavior:
- If change type has references: HTTP 409 Conflict
- If no references: HTTP 204 No Content (deletion succeeds)
- Frontend automatically offers deactivation on conflict

## Related Files

- Backend API: `api/app/api/model_change_taxonomy.py`
- Database Model: `api/app/models/model_change_taxonomy.py`
- Database Migration: `api/alembic/versions/026d874c626f_add_model_change_taxonomy.py`
- Frontend Admin UI: `web/src/pages/TaxonomyPage.tsx`
- Frontend User Modal: `web/src/components/SubmitChangeModal.tsx`

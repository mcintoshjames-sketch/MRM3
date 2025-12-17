# Regional Deployment UX Implementation Plan

## Overview

Implement the Deploy Modal and My Tasks enhancements as specified in `DEPLOY_PLAN.md`, with the critical business rule:

**Lock Icon 🔒 Logic**: Regional approval is required ONLY for regions not covered by the validation scope:
```
requires_regional_approval = region.requires_regional_approval AND region.region_id NOT IN validation_request.regions
```

---

## Phase 1: Core Deploy Modal (Backend)

### 1.1 New Schemas (`api/app/schemas/deploy_modal.py`)

```python
class RegionDeploymentStatus(BaseModel):
    region_id: int
    region_code: str
    region_name: str
    current_version_id: Optional[int]
    current_version_number: Optional[str]
    deployed_at: Optional[datetime]
    requires_regional_approval: bool  # Computed: region flag AND NOT in validation scope
    in_validation_scope: bool
    has_pending_task: bool
    pending_task_id: Optional[int]

class DeployModalDataResponse(BaseModel):
    version_id: int
    version_number: str
    model_id: int
    model_name: str
    validation_request_id: Optional[int]
    validation_status: Optional[str]
    validation_approved: bool
    regions: List[RegionDeploymentStatus]
    can_deploy: bool

class RegionDeploymentSpec(BaseModel):
    region_id: int
    production_date: date
    notes: Optional[str]

class DeploymentCreateRequest(BaseModel):
    deployments: List[RegionDeploymentSpec]
    deploy_now: bool = False
    validation_override_reason: Optional[str]
    shared_notes: Optional[str]
```

### 1.2 New Endpoints (`api/app/api/version_deployment_tasks.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/deployment-tasks/version/{version_id}/deploy-modal` | GET | Get modal data with lock icon computation |
| `/deployment-tasks/version/{version_id}/deploy` | POST | Create deployment(s) - Deploy Now or Schedule |

### 1.3 Lock Icon Computation (Critical Business Logic)

```python
def compute_requires_regional_approval(
    region: Region,
    validation_region_ids: Set[int]
) -> bool:
    """
    Lock icon shows when:
    - Region has requires_regional_approval = True, AND
    - Region is NOT in the validation request's scope
    """
    if not region.requires_regional_approval:
        return False
    return region.region_id not in validation_region_ids
```

### 1.4 Key Files to Modify
- `api/app/api/version_deployment_tasks.py` - Add new endpoints
- `api/app/schemas/deploy_modal.py` - New file for schemas
- `api/app/main.py` - Register new schemas if needed

---

## Phase 2: Core Deploy Modal (Frontend)

### 2.1 New Component: `web/src/components/DeployModal.tsx`

**Features:**
- Radio toggle: "Deploy Now" vs "Schedule for Later"
- Region checklist with current deployment status (version, deployed date)
- Lock icon 🔒 for regions requiring approval (not in validation scope)
- Single date field for Deploy Now
- Per-region dates for Schedule for Later
- **"Apply same date to all"** button for convenience
- "Select All" / "Clear" buttons
- **Smart button text** showing count: "Deploy to 3 Regions"
- Footer note explaining lock icon meaning

**State:**
```typescript
const [deployMode, setDeployMode] = useState<'now' | 'later'>('now');
const [selectedRegions, setSelectedRegions] = useState<Map<number, boolean>>(new Map());
const [regionDates, setRegionDates] = useState<Map<number, string>>(new Map());
const [deployDate, setDeployDate] = useState(todayISO);
const [validationRegionIds, setValidationRegionIds] = useState<Set<number>>(new Set());
```

**Lock Icon Display Logic:**
```typescript
// In region list mapping
{region.requires_regional_approval && !validationRegionIds.has(region.region_id) && (
    <LockIcon className="h-5 w-5 text-yellow-500" title="Regional approval required" />
)}
```

### 2.2 New API Client (`web/src/api/deployments.ts`)

```typescript
export const deploymentsApi = {
    getDeployModalData: (versionId: number) =>
        api.get(`/deployment-tasks/version/${versionId}/deploy-modal`),

    deployVersion: (versionId: number, data: DeployRequest) =>
        api.post(`/deployment-tasks/version/${versionId}/deploy`, data),
};
```

### 2.3 Modify `web/src/components/VersionsList.tsx`

Add "Deploy" button to actions column for APPROVED/ACTIVE versions:
```typescript
{(version.status === 'APPROVED' || version.status === 'ACTIVE') && (
    <button onClick={() => setDeployModalVersion(version)}>
        Deploy
    </button>
)}
```

### 2.4 Entry Point: Validation Approval Success

Add "Deploy Approved Version" link to validation request detail page when status transitions to APPROVED:
- Location: `web/src/pages/ValidationRequestDetailPage.tsx`
- Show prominent CTA when validation is approved
- Links directly to Deploy Modal for the associated version

### 2.5 Version Deployment Status Section (Model Details)

Add regional deployment status display on Model Details → Versions tab:

| Region | Status | Deployed | Validation |
|--------|--------|----------|------------|
| US | 🟢 Deployed | Jan 15, 2025 | ✓ Approved |
| UK | 🟡 Pending | Planned: Jan 20 | ✓ Approved 🔒 |
| EU | ⚪ Not Started | — | ✓ Approved |
| APAC | 🔴 Overdue | Planned: Jan 10 | ✓ Approved |

Status legend:
- 🟢 Deployed - Live in production
- 🟡 Pending - Scheduled, awaiting confirmation
- 🔴 Overdue - Past planned date
- ⚪ Not Started - No deployment scheduled
- 🔒 Requires Approval - Regional approval needed (not in validation scope)

### 2.6 Key Files to Create/Modify
- `web/src/components/DeployModal.tsx` - New file
- `web/src/components/VersionDeploymentStatus.tsx` - New file for status section
- `web/src/api/deployments.ts` - New file
- `web/src/components/VersionsList.tsx` - Add Deploy button and status section
- `web/src/pages/ValidationRequestDetailPage.tsx` - Add "Deploy Approved Version" link

---

## Phase 3: Scheduled Deployments & My Tasks

### 3.1 Backend Bulk Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/deployment-tasks/bulk/confirm` | POST | Confirm multiple tasks |
| `/deployment-tasks/bulk/adjust` | POST | Adjust dates for multiple tasks |
| `/deployment-tasks/bulk/cancel` | POST | Cancel multiple tasks |

### 3.2 Frontend: Enhance `MyDeploymentTasksPage.tsx`

**Add:**
- **Filters**: Status dropdown [All, Due Today, This Week, Overdue], Date range picker, Search box
- Checkbox column for bulk selection
- "Select All" header checkbox
- Bulk action buttons: "Confirm Selected", "Adjust Dates", "Cancel Selected"
- Status color indicators: 🟡 Due/Overdue, ⚪ Scheduled, 🟢 Confirmed

### 3.3 New Modals

**`web/src/components/BulkConfirmationModal.tsx`**
- List of selected deployments with model/version/region
- Lock icon indicator for regions requiring approval
- **Actual Deployment Date** field (single date for all)
- **Confirmation Notes** text area
- Footer note about regional approvals that will be requested

**`web/src/components/AdjustDatesModal.tsx`**
- List of selected deployments
- New planned date picker
- Option: "Apply to all selected" or per-task dates

---

## Phase 4: Regional Approval Integration & Post-Deployment Actions

### 4.1 Auto-Create Regional Approval on Deploy

When deploying to a region that requires approval (lock icon shown):

```python
# In deploy endpoint
if requires_regional_approval:
    create_regional_approval_request(
        validation_request_id=version.validation_request_id,
        region_id=region_id,
        approval_type="Regional",
        approval_status="Pending"
    )
```

### 4.2 Post-Deployment Auto-Actions

On deployment confirmation, the system must:

```python
# In confirm deployment endpoint
def on_deployment_confirmed(task: VersionDeploymentTask, actual_date: date, notes: str):
    # 1. Update ModelRegion
    model_region.version_id = task.version_id
    model_region.deployed_at = actual_date

    # 2. Create regional approval if needed (lock icon region)
    if compute_requires_regional_approval(region, validation_region_ids):
        create_regional_approval_request(...)

    # 3. Log audit event
    create_audit_log(
        entity_type="VersionDeploymentTask",
        entity_id=task.id,
        action="DEPLOYMENT_CONFIRMED",
        changes={"status": "CONFIRMED", "actual_date": actual_date}
    )

    # 4. Update version.actual_production_date (if all regions done)
    if all_regions_deployed(version):
        version.actual_production_date = max(region_deployed_dates)

    # 5. Check for Type 3 exception (deployed before validation approved)
    if not version.validation_request or version.validation_request.status != "APPROVED":
        create_type3_exception(
            model_id=version.model_id,
            version_id=version.id,
            reason="Deployed before validation approved"
        )
```

### 4.3 Display Approval Status in Modals

Show pending regional approvals in:
- Deploy Modal (footer note)
- Bulk Confirmation Modal (per-task indicator)

---

## Phase 5: Automation (Future)

- Auto-create tasks on validation approval (when version has `planned_production_date`)
- Overdue notifications (daily job)
- Smart date suggestions based on deployment history

---

## Implementation Order

1. **Backend Phase 1**: Create schemas and GET deploy-modal endpoint
2. **Frontend Phase 1**: Create DeployModal component
3. **Backend Phase 2**: Add POST deploy endpoint
4. **Frontend Phase 2**: Add Deploy button to VersionsList, integrate modal
5. **Backend Phase 3**: Add bulk endpoints (confirm, adjust, cancel)
6. **Frontend Phase 3**: Add bulk operations to MyDeploymentTasksPage
7. **Frontend Phase 4**: Create BulkConfirmationModal and AdjustDatesModal
8. **Integration**: Test regional approval triggering

---

## Critical Files Summary

### Backend (api/)
| File | Action |
|------|--------|
| `app/schemas/deploy_modal.py` | CREATE - New schemas |
| `app/api/version_deployment_tasks.py` | MODIFY - Add 5 new endpoints (deploy-modal, deploy, bulk confirm/adjust/cancel) |
| `app/models/validation.py` | REFERENCE - ValidationRequest.regions (lines 217-218) |
| `app/models/region.py` | REFERENCE - requires_regional_approval flag (line 20) |
| `app/models/model_version.py` | MODIFY - Ensure actual_production_date field exists |

### Frontend (web/src/)
| File | Action |
|------|--------|
| `components/DeployModal.tsx` | CREATE - Main deploy modal with region selection |
| `components/VersionDeploymentStatus.tsx` | CREATE - Regional status display section |
| `components/BulkConfirmationModal.tsx` | CREATE - Bulk confirmation with notes |
| `components/AdjustDatesModal.tsx` | CREATE - Bulk date adjustment |
| `api/deployments.ts` | CREATE - Deployment API client |
| `components/VersionsList.tsx` | MODIFY - Add Deploy button + status section |
| `pages/MyDeploymentTasksPage.tsx` | MODIFY - Add bulk operations + filters |
| `pages/ValidationRequestDetailPage.tsx` | MODIFY - Add "Deploy Approved Version" link |

---

## Testing Checklist

### Lock Icon Logic (Critical)
- [ ] Lock icon appears ONLY when `region.requires_regional_approval=true` AND `region.id NOT IN validation_request.regions`
- [ ] Lock icon does NOT appear when region is in validation scope (even if requires_regional_approval=true)
- [ ] Lock icon does NOT appear when region has requires_regional_approval=false

### Deploy Modal
- [ ] Deploy Now creates CONFIRMED task and updates ModelRegion
- [ ] Schedule for Later creates PENDING task(s)
- [ ] "Apply same date to all" works in Schedule mode
- [ ] "Select All" / "Clear" buttons work correctly
- [ ] Smart button text shows correct region count ("Deploy to 3 Regions")
- [ ] Footer note shows which regions will require approval

### Entry Points
- [ ] Deploy button appears on Versions tab for APPROVED/ACTIVE versions
- [ ] "Deploy Approved Version" link appears on validation detail page after approval

### Status Display
- [ ] Version Deployment Status section shows correct status icons (🟢🟡🔴⚪)
- [ ] Overdue status (🔴) displays for tasks past planned date

### Bulk Operations
- [ ] Bulk confirmation works for multiple tasks
- [ ] Bulk date adjustment works for multiple tasks
- [ ] Bulk cancellation works for multiple tasks

### Post-Deployment Actions
- [ ] Regional approval request created when deploying to lock icon region
- [ ] Audit log entry created on deployment confirmation
- [ ] `version.actual_production_date` updated when all regions deployed
- [ ] Type 3 exception created if deployed before validation approved

### General
- [ ] Validation override flow works when validation not approved
- [ ] Dates display in ISO format (YYYY-MM-DD)

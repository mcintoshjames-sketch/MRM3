Phase 5: Real-Time "Ready to Deploy" Surfacing
5.1 Overview & Design Decisions
Goal: Surface approved model versions that haven't been fully deployed to all their target regions, using real-time calculation instead of email notifications. Key Requirement: Every approved validation → model version/region combination should surface as "Ready to Deploy" regardless of whether planned_production_date was set. Alert Fatigue Mitigation:
❌ Do NOT show separate alerts for "versions without planned production dates"
❌ Do NOT duplicate deployment prompts across multiple UI locations
✅ Single consolidated "Ready to Deploy" section in My Deployment Tasks page
✅ Each item links directly to Deploy Modal for immediate action
5.2 Data Model for Detection
To identify approved-but-not-deployed versions, query must check:
ValidationRequest → status = 'APPROVED'
ValidationRequest → ValidationRequestModelVersion → ModelVersion
For each ModelVersion:
GLOBAL scope: Check if any ModelRegion for that model lacks deployed_at for this version
REGIONAL scope: Check ModelVersionRegion target regions; compare against ModelRegion deployment status

# Pseudocode for detection
def get_ready_to_deploy_items(db: Session, user_id: int) -> List[ReadyToDeployItem]:
    """
    Find approved versions not fully deployed to all target regions.
    Filter to models where user has deployment permissions (owner/admin).
    """

    # 1. Get all approved validation requests
    approved_requests = db.query(ValidationRequest).filter(
        ValidationRequest.status_id == APPROVED_STATUS_ID
    ).all()

    ready_items = []

    for request in approved_requests:
        for version in request.versions:
            model = version.model

            # Check user has deployment access (owner or admin)
            if not user_can_deploy(user, model):
                continue

            # Determine target regions
            if version.scope == 'GLOBAL':
                target_regions = get_all_regions_for_model(model)
            else:  # REGIONAL
                target_regions = version.affected_regions

            # Check deployment status for each target region
            for region in target_regions:
                model_region = get_model_region(model.model_id, region.region_id)

                # Not deployed, or deployed with different version
                if not model_region or model_region.version_id != version.version_id:
                    ready_items.append(ReadyToDeployItem(
                        model_id=model.model_id,
                        model_name=model.model_name,
                        version_id=version.version_id,
                        version_number=version.version_number,
                        region_id=region.region_id,
                        region_code=region.code,
                        region_name=region.name,
                        validation_request_id=request.request_id,
                        validation_approved_date=request.completion_date,
                        days_since_approval=calculate_days(request.completion_date),
                        requires_regional_approval=compute_requires_regional_approval(
                            region, request.regions
                        ),
                        current_deployed_version=model_region.version.version_number if model_region else None
                    ))

    return ready_items
5.3 New Backend Endpoint
File: api/app/api/version_deployment_tasks.py
Endpoint	Method	Purpose
/deployment-tasks/ready-to-deploy	GET	Get versions awaiting deployment (real-time calculation)
Request Parameters:
model_id (optional): Filter to specific model
region_id (optional): Filter to specific region
limit (optional): Pagination, default 50
Response Schema (api/app/schemas/version_deployment_task.py):

class ReadyToDeployItem(BaseModel):
    """Item representing an approved version not yet deployed to a region."""
    model_id: int
    model_name: str
    version_id: int
    version_number: str
    region_id: int
    region_code: str
    region_name: str
    validation_request_id: int
    validation_approved_date: date
    days_since_approval: int
    requires_regional_approval: bool  # 🔒 Lock icon
    current_deployed_version: Optional[str]  # What's currently deployed (if any)

class ReadyToDeployResponse(BaseModel):
    """Response for ready-to-deploy endpoint."""
    items: List[ReadyToDeployItem]
    total_count: int
    models_affected: int
    regions_affected: int
5.4 Frontend Integration
Location: web/src/pages/MyDeploymentTasksPage.tsx UI Design:

┌─────────────────────────────────────────────────────────────┐
│ 📋 My Deployment Tasks                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🚀 Ready to Deploy (4 items)                      [▼]  │ │
│ │                                                         │ │
│ │  Model             Version   Region    Days    Action   │ │
│ │  ─────────────────────────────────────────────────────  │ │
│ │  Credit Risk v2.1  v2.1.0    US        15d     [Deploy] │ │
│ │  Credit Risk v2.1  v2.1.0    UK 🔒     15d     [Deploy] │ │
│ │  ALM Model         v3.0.0    EU        8d      [Deploy] │ │
│ │  Fraud Detection   v1.2.0    APAC      3d      [Deploy] │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📅 Scheduled Deployments                                │ │
│ │                                                         │ │
│ │  [Filters: All ▼] [Search: _______] [Date: __ to __]   │ │
│ │                                                         │ │
│ │  ☐ Model           Version  Region  Planned     Status  │ │
│ │  ─────────────────────────────────────────────────────  │ │
│ │  ☐ Market Risk     v1.0.0   US      2025-02-01  Pending │ │
│ │  ☐ Market Risk     v1.0.0   UK 🔒   2025-02-05  Pending │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [Confirm Selected] [Adjust Dates] [Cancel Selected]         │
└─────────────────────────────────────────────────────────────┘
Key UI Elements:
"Ready to Deploy" section - Collapsible, shown at top of page
Days since approval - Helps prioritize (e.g., "15d" = 15 days)
Lock icon 🔒 - Same logic as Deploy Modal (requires regional approval)
[Deploy] button - Opens Deploy Modal pre-filtered to that version/region
Collapsed by default if empty, expanded if items exist
Badge count in sidebar navigation: "My Tasks (4)" showing total across both sections
5.5 API Client Update
File: web/src/api/deployments.ts

export interface ReadyToDeployItem {
    model_id: number;
    model_name: string;
    version_id: number;
    version_number: string;
    region_id: number;
    region_code: string;
    region_name: string;
    validation_request_id: number;
    validation_approved_date: string;
    days_since_approval: number;
    requires_regional_approval: boolean;
    current_deployed_version: string | null;
}

export interface ReadyToDeployResponse {
    items: ReadyToDeployItem[];
    total_count: number;
    models_affected: number;
    regions_affected: number;
}

export const deploymentsApi = {
    // ... existing methods ...

    /**
     * Get approved versions awaiting deployment (real-time calculation).
     * Returns items for models where current user has deployment permissions.
     */
    getReadyToDeploy: (params?: { model_id?: number; region_id?: number; limit?: number }) =>
        client.get<ReadyToDeployResponse>('/deployment-tasks/ready-to-deploy', { params }),
};
5.6 Dashboard Integration (Optional Summary Widget)
File: web/src/pages/AdminDashboard.tsx (if exists) or DashboardPage.tsx Add a summary card linking to My Tasks:

<SummaryCard
    title="Awaiting Deployment"
    value={readyToDeployCount}
    icon="🚀"
    linkTo="/deployment-tasks"
    description="Approved versions ready to deploy"
/>
5.7 Implementation Files
File	Action
api/app/api/version_deployment_tasks.py	ADD /ready-to-deploy endpoint
api/app/schemas/version_deployment_task.py	ADD ReadyToDeployItem, ReadyToDeployResponse schemas
web/src/api/deployments.ts	ADD getReadyToDeploy method and types
web/src/pages/MyDeploymentTasksPage.tsx	ADD "Ready to Deploy" section at top
web/src/pages/DashboardPage.tsx	ADD summary widget (optional)
5.8 Testing Checklist
 Ready to Deploy shows ALL approved versions not fully deployed
 Items appear regardless of whether planned_production_date was set
 Days since approval calculated correctly
 Lock icon 🔒 shows for regions requiring approval (not in validation scope)
 [Deploy] button opens Deploy Modal for correct version
 List updates in real-time after deployment (item disappears)
 Empty state shows "All approved versions have been deployed" message
 Badge count in sidebar reflects total tasks (scheduled + ready)
 Filtering by model/region works
 User only sees models they have deployment permissions for
5.9 Alert Fatigue Prevention
Removed/Consolidated:
❌ No separate "versions missing planned_production_date" alert
❌ No separate dashboard widget duplicating My Tasks content
❌ No email notifications (replaced by real-time surfacing)
Single Source of Truth:
✅ My Deployment Tasks page is THE place for all deployment actions
✅ Dashboard widget shows count only, links to My Tasks
✅ Ready to Deploy + Scheduled Deployments in one unified view
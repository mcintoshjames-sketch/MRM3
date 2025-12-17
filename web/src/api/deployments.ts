/**
 * API client for version deployment operations.
 */
import client from './client';

// Types for deploy modal
export interface RegionDeploymentStatus {
    region_id: number;
    region_code: string;
    region_name: string;
    current_version_id: number | null;
    current_version_number: string | null;
    deployed_at: string | null;
    requires_regional_approval: boolean;
    in_validation_scope: boolean;
    has_pending_task: boolean;
    pending_task_id: number | null;
    pending_task_planned_date: string | null;
}

export interface DeployModalData {
    version_id: number;
    version_number: string;
    change_description: string | null;
    model_id: number;
    model_name: string;
    validation_request_id: number | null;
    validation_status: string | null;
    validation_approved: boolean;
    regions: RegionDeploymentStatus[];
    can_deploy: boolean;
}

export interface RegionDeploymentSpec {
    region_id: number;
    production_date: string; // ISO date string YYYY-MM-DD
    notes?: string;
}

export interface DeploymentCreateRequest {
    deployments: RegionDeploymentSpec[];
    deploy_now: boolean;
    validation_override_reason?: string;
    shared_notes?: string;
}

export interface DeploymentCreateResponse {
    created_tasks: number[];
    regions_requiring_approval: string[];
    message: string;
}

export interface BulkConfirmRequest {
    task_ids: number[];
    actual_production_date: string; // ISO date string YYYY-MM-DD
    confirmation_notes?: string;
    validation_override_reason?: string;
}

export interface BulkAdjustRequest {
    task_ids: number[];
    new_planned_date: string; // ISO date string YYYY-MM-DD
    adjustment_reason?: string;
}

export interface BulkCancelRequest {
    task_ids: number[];
    cancellation_reason?: string;
}

export interface BulkOperationResult {
    succeeded: number[];
    failed: Array<{ task_id: number; error: string }>;
    message: string;
}

export const deploymentsApi = {
    /**
     * Get deploy modal data for a version.
     * Returns region deployment status with lock icon computation.
     */
    getDeployModalData: (versionId: number) =>
        client.get<DeployModalData>(`/deployment-tasks/version/${versionId}/deploy-modal`),

    /**
     * Deploy a version to selected regions.
     * - deploy_now=true: Creates CONFIRMED tasks and updates ModelRegion immediately
     * - deploy_now=false: Creates PENDING tasks for later confirmation
     */
    deployVersion: (versionId: number, data: DeploymentCreateRequest) =>
        client.post<DeploymentCreateResponse>(`/deployment-tasks/version/${versionId}/deploy`, data),

    /**
     * Bulk confirm multiple deployment tasks.
     */
    bulkConfirm: (data: BulkConfirmRequest) =>
        client.post<BulkOperationResult>('/deployment-tasks/bulk/confirm', data),

    /**
     * Bulk adjust dates for multiple deployment tasks.
     */
    bulkAdjust: (data: BulkAdjustRequest) =>
        client.post<BulkOperationResult>('/deployment-tasks/bulk/adjust', data),

    /**
     * Bulk cancel multiple deployment tasks.
     */
    bulkCancel: (data: BulkCancelRequest) =>
        client.post<BulkOperationResult>('/deployment-tasks/bulk/cancel', data),
};

export default deploymentsApi;

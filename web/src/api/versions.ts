import api from './client';

export type ChangeType = 'MINOR' | 'MAJOR';
export type VersionStatus = 'DRAFT' | 'IN_VALIDATION' | 'APPROVED' | 'ACTIVE' | 'SUPERSEDED';
export type VersionScope = 'GLOBAL' | 'REGIONAL';

export interface ModelVersion {
    version_id: number;
    model_id: number;
    version_number: string;
    change_type: ChangeType;
    change_type_id: number | null;
    change_description: string;
    status: VersionStatus;
    created_by_id: number;
    created_at: string;
    // Production dates
    planned_production_date: string | null;
    actual_production_date: string | null;
    production_date: string | null;  // Legacy field
    // Regional scope
    scope: VersionScope;
    affected_region_ids: number[] | null;
    // Validation
    validation_request_id: number | null;
    created_by_name: string | null;
    change_type_name: string | null;
    change_category_name: string | null;
    // Validation project info (populated when auto-created)
    validation_request_created?: boolean;
    validation_type?: string;  // "TARGETED" or "INTERIM"
    validation_warning?: string;
    // Validation workflow status (for edit permission checks)
    validation_request_status?: string;  // e.g., "INTAKE", "PLANNING", "IN_PROGRESS", "REVIEW", "PENDING_APPROVAL", "APPROVED"
}

export interface ModelVersionCreate {
    version_number?: string | null;
    change_type: ChangeType;
    change_type_id?: number | null;
    change_description: string;
    production_date?: string | null;
    // Regional scope
    scope?: VersionScope;
    affected_region_ids?: number[] | null;
}

export interface NextVersionPreview {
    next_version: string;
    change_type: string;
}

export const versionsApi = {
    // Preview next auto-generated version number
    getNextVersionPreview: async (modelId: number, changeType: ChangeType): Promise<NextVersionPreview> => {
        const response = await api.get(`/models/${modelId}/versions/next-version?change_type=${changeType}`);
        return response.data;
    },

    // Create a new version
    createVersion: async (modelId: number, data: ModelVersionCreate): Promise<ModelVersion> => {
        const response = await api.post(`/models/${modelId}/versions`, data);
        return response.data;
    },

    // List all versions for a model
    listVersions: async (modelId: number): Promise<ModelVersion[]> => {
        const response = await api.get(`/models/${modelId}/versions`);
        return response.data;
    },

    // Get current active version
    getCurrentVersion: async (modelId: number): Promise<ModelVersion> => {
        const response = await api.get(`/models/${modelId}/versions/current`);
        return response.data;
    },

    // Approve version (Validator/Admin only)
    approveVersion: async (versionId: number): Promise<ModelVersion> => {
        const response = await api.patch(`/versions/${versionId}/approve`);
        return response.data;
    },

    // Activate version
    activateVersion: async (versionId: number): Promise<ModelVersion> => {
        const response = await api.patch(`/versions/${versionId}/activate`);
        return response.data;
    },

    // Set production date
    setProductionDate: async (versionId: number, productionDate: string): Promise<ModelVersion> => {
        const response = await api.patch(`/versions/${versionId}/production?production_date=${productionDate}`);
        return response.data;
    },

    // Delete draft version
    deleteVersion: async (versionId: number): Promise<void> => {
        await api.delete(`/versions/${versionId}`);
    },

    // Get version details
    getVersion: async (versionId: number): Promise<ModelVersion> => {
        const response = await api.get(`/versions/${versionId}`);
        return response.data;
    },

    // Update version
    updateVersion: async (versionId: number, data: Partial<ModelVersionCreate>): Promise<ModelVersion> => {
        const response = await api.patch(`/versions/${versionId}`, data);
        return response.data;
    },

    // Export versions to CSV
    exportCSV: async (modelId: number): Promise<void> => {
        const response = await api.get(`/models/${modelId}/versions/export/csv`, {
            responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `model_${modelId}_versions_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
    },

    // Export versions to PDF
    exportPDF: async (modelId: number): Promise<void> => {
        const response = await api.get(`/models/${modelId}/versions/export/pdf`, {
            responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `model_${modelId}_changelog_${new Date().toISOString().split('T')[0]}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
    },
};

// Ready to Deploy types and API - Per-Region Granularity
export type VersionSource = 'explicit' | 'inferred';

export interface ReadyToDeployItem {
    // Version identification
    version_id: number;
    version_number: string;
    model_id: number;
    model_name: string;

    // Region details (per-region granularity)
    region_id: number;
    region_code: string;
    region_name: string;

    // Version source tracking
    version_source: VersionSource;

    // Validation info
    validation_request_id: number | null;
    validation_status: string;
    validation_approved_date: string | null;

    // Timing
    days_since_approval: number;

    // Owner info
    owner_id: number;
    owner_name: string;

    // Deployment task tracking (for this specific region)
    has_pending_task: boolean;
    pending_task_id: number | null;
}

export interface ReadyToDeployFilters {
    model_id?: number;
    my_models_only?: boolean;
}

// Legacy types for backwards compatibility
export interface ReadyToDeployVersion {
    version_id: number;
    version_number: string;
    model_id: number;
    model_name: string;
    validation_status: string;
    validation_approved_date: string | null;
    total_regions_count: number;
    deployed_regions_count: number;
    pending_regions: string[];
    pending_tasks_count: number;
    has_pending_tasks: boolean;
    owner_name: string;
    days_since_approval: number;
}

export interface ReadyToDeploySummary {
    ready_count: number;
    partially_deployed_count: number;
    with_pending_tasks_count: number;
}

export const readyToDeployApi = {
    // Get list of versions ready to deploy (per-region granularity)
    getReadyToDeploy: async (filters?: ReadyToDeployFilters): Promise<ReadyToDeployItem[]> => {
        const params = new URLSearchParams();
        if (filters?.model_id) params.append('model_id', filters.model_id.toString());
        if (filters?.my_models_only) params.append('my_models_only', 'true');
        const queryString = params.toString();
        const url = queryString ? `/deployment-tasks/ready-to-deploy?${queryString}` : '/deployment-tasks/ready-to-deploy';
        const response = await api.get(url);
        return response.data;
    },

    // Compute summary from items (no separate endpoint needed)
    computeSummary: (items: ReadyToDeployItem[]): ReadyToDeploySummary => {
        const uniqueVersions = new Set(items.map(i => i.version_id));
        const versionsWithPendingTasks = new Set(
            items.filter(i => i.has_pending_task).map(i => i.version_id)
        );
        return {
            ready_count: uniqueVersions.size,
            partially_deployed_count: 0, // Can be computed if needed
            with_pending_tasks_count: versionsWithPendingTasks.size,
        };
    },
};

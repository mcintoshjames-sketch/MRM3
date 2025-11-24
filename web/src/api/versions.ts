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

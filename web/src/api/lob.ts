import api from './client';

export interface LOBUnit {
    lob_id: number;
    parent_id: number | null;
    code: string;
    name: string;
    org_unit: string;  // 5-char external identifier (e.g., "12345" or "S0001")
    level: number;
    sort_order: number;
    is_active: boolean;
    full_path: string;
    user_count: number;
    // Optional metadata (typically on leaf nodes)
    description?: string | null;
    contact_name?: string | null;
    org_description?: string | null;
    legal_entity_id?: string | null;
    legal_entity_name?: string | null;
    short_name?: string | null;
    status_code?: string | null;
    tier?: string | null;
    created_at: string;
    updated_at: string;
}

export interface LOBUnitTreeNode extends LOBUnit {
    children: LOBUnitTreeNode[];
}

export interface LOBUnitCreate {
    code: string;
    name: string;
    org_unit: string;  // Required: 5-char external identifier
    parent_id?: number | null;
    sort_order?: number;
    description?: string | null;
    // Metadata fields (typically on leaf nodes)
    contact_name?: string | null;
    org_description?: string | null;
    legal_entity_id?: string | null;
    legal_entity_name?: string | null;
    short_name?: string | null;
    status_code?: string | null;
    tier?: string | null;
}

export interface LOBUnitUpdate {
    code?: string;
    name?: string;
    org_unit?: string;  // 5-char external identifier
    sort_order?: number;
    is_active?: boolean;
    description?: string | null;
    // Metadata fields
    contact_name?: string | null;
    org_description?: string | null;
    legal_entity_id?: string | null;
    legal_entity_name?: string | null;
    short_name?: string | null;
    status_code?: string | null;
    tier?: string | null;
}

export interface LOBImportPreview {
    to_create: Record<string, unknown>[];
    to_update: Record<string, unknown>[];
    to_skip: Record<string, unknown>[];
    errors: string[];
    detected_columns: string[];
    max_depth: number;
}

export interface LOBImportResult {
    created_count: number;
    updated_count: number;
    skipped_count: number;
    errors: string[];
}

export interface LOBUser {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
    role_code?: string | null;
}

export const lobApi = {
    // Get all LOB units (flat list)
    getLOBUnits: async (activeOnly: boolean = true): Promise<LOBUnit[]> => {
        const response = await api.get('/lob-units/', {
            params: { include_inactive: !activeOnly }
        });
        return response.data;
    },

    // Get LOB units as tree structure
    getLOBTree: async (activeOnly: boolean = true): Promise<LOBUnitTreeNode[]> => {
        const response = await api.get('/lob-units/tree', {
            params: { include_inactive: !activeOnly }
        });
        return response.data;
    },

    // Get a specific LOB unit
    getLOBUnit: async (lobId: number): Promise<LOBUnit> => {
        const response = await api.get(`/lob-units/${lobId}`);
        return response.data;
    },

    // Create a new LOB unit
    createLOBUnit: async (data: LOBUnitCreate): Promise<LOBUnit> => {
        const response = await api.post('/lob-units/', data);
        return response.data;
    },

    // Update an LOB unit
    updateLOBUnit: async (lobId: number, data: LOBUnitUpdate): Promise<LOBUnit> => {
        const response = await api.patch(`/lob-units/${lobId}`, data);
        return response.data;
    },

    // Deactivate an LOB unit (soft delete)
    deactivateLOBUnit: async (lobId: number): Promise<{ message: string }> => {
        const response = await api.delete(`/lob-units/${lobId}`);
        return response.data;
    },

    // Get users assigned to an LOB unit
    getLOBUsers: async (lobId: number): Promise<LOBUser[]> => {
        const response = await api.get(`/lob-units/${lobId}/users`);
        return response.data;
    },

    // Preview CSV import (dry run)
    previewImport: async (file: File): Promise<LOBImportPreview> => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post('/lob-units/import-csv', formData, {
            params: { dry_run: true },
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    },

    // Execute CSV import
    importCSV: async (file: File): Promise<LOBImportResult> => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post('/lob-units/import-csv', formData, {
            params: { dry_run: false },
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    },

    // Export LOB hierarchy as CSV
    exportCSV: async (): Promise<Blob> => {
        const response = await api.get('/lob-units/export-csv', {
            responseType: 'blob'
        });
        return response.data;
    },
};

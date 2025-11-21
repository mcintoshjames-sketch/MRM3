/**
 * Export Views API
 * Manages saved CSV export configurations
 */
import api from './client';

export interface ExportView {
    view_id: number;
    user_id: number;
    entity_type: string;
    view_name: string;
    is_public: boolean;
    columns: string[];
    description?: string;
    created_at: string;
    updated_at: string;
}

export interface ExportViewCreate {
    entity_type: string;
    view_name: string;
    columns: string[];
    is_public: boolean;
    description?: string;
}

export interface ExportViewUpdate {
    view_name?: string;
    columns?: string[];
    is_public?: boolean;
    description?: string;
}

export const exportViewsApi = {
    /**
     * Get all export views for the current user and entity type
     */
    async list(entityType: string): Promise<ExportView[]> {
        const response = await api.get(`/export-views/?entity_type=${entityType}`);
        return response.data;
    },

    /**
     * Get a specific export view by ID
     */
    async get(viewId: number): Promise<ExportView> {
        const response = await api.get(`/export-views/${viewId}`);
        return response.data;
    },

    /**
     * Create a new export view
     */
    async create(viewData: ExportViewCreate): Promise<ExportView> {
        const response = await api.post('/export-views/', viewData);
        return response.data;
    },

    /**
     * Update an existing export view
     */
    async update(viewId: number, viewData: ExportViewUpdate): Promise<ExportView> {
        const response = await api.patch(`/export-views/${viewId}`, viewData);
        return response.data;
    },

    /**
     * Delete an export view
     */
    async delete(viewId: number): Promise<void> {
        await api.delete(`/export-views/${viewId}`);
    },
};

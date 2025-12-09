import api from './client';

export interface Region {
    region_id: number;
    code: string;
    name: string;
    requires_regional_approval?: boolean; // Optional for backward compatibility
    enforce_validation_plan?: boolean;
    requires_standalone_rating?: boolean; // When true, models in this region require regional risk assessments
    created_at: string;
}

export interface ModelRegion {
    id: number;
    model_id: number;
    region_id: number;
    shared_model_owner_id?: number | null;
    regional_risk_level?: string | null;
    notes?: string | null;
    created_at: string;
    updated_at: string;
}

export interface ModelRegionCreate {
    region_id: number;
    shared_model_owner_id?: number | null;
    regional_risk_level?: string | null;
    notes?: string | null;
}

export const regionsApi = {
    // Get all regions
    getRegions: async (): Promise<Region[]> => {
        const response = await api.get('/regions/');
        return response.data;
    },

    // Get a specific region
    getRegion: async (regionId: number): Promise<Region> => {
        const response = await api.get(`/regions/${regionId}`);
        return response.data;
    },

    // Get model-region links for a model
    getModelRegions: async (modelId: number): Promise<ModelRegion[]> => {
        const response = await api.get(`/models/${modelId}/regions`);
        return response.data;
    },

    // Create model-region link
    createModelRegion: async (modelId: number, data: ModelRegionCreate): Promise<ModelRegion> => {
        const response = await api.post(`/models/${modelId}/regions`, data);
        return response.data;
    },

    // Update model-region link
    updateModelRegion: async (id: number, data: Partial<ModelRegionCreate>): Promise<ModelRegion> => {
        const response = await api.put(`/model-regions/${id}`, data);
        return response.data;
    },

    // Delete model-region link
    deleteModelRegion: async (id: number): Promise<void> => {
        await api.delete(`/model-regions/${id}`);
    },
};

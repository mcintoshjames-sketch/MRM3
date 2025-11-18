import api from './client';

export interface ModelChangeType {
    change_type_id: number;
    category_id: number;
    code: number;
    name: string;
    description: string | null;
    mv_activity: string | null;
    requires_mv_approval: boolean;
    sort_order: number;
    is_active: boolean;
}

export interface ModelChangeCategory {
    category_id: number;
    code: string;
    name: string;
    sort_order: number;
    change_types: ModelChangeType[];
}

export const changeTaxonomyApi = {
    // Get all categories with their types
    getCategories: async (): Promise<ModelChangeCategory[]> => {
        const response = await api.get('/change-taxonomy/categories');
        return response.data;
    },

    // Get all types (optionally filtered to active only)
    getTypes: async (activeOnly: boolean = true): Promise<ModelChangeType[]> => {
        const response = await api.get('/change-taxonomy/types', {
            params: { active_only: activeOnly }
        });
        return response.data;
    },

    // Get a specific type by ID
    getType: async (changeTypeId: number): Promise<ModelChangeType> => {
        const response = await api.get(`/change-taxonomy/types/${changeTypeId}`);
        return response.data;
    },
};

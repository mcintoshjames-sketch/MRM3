import api from './client';

export interface RegionalModelImplementation {
    regional_model_impl_id: number;
    model_id: number;
    region_id: number;
    shared_model_owner_id: number | null;
    local_identifier: string | null;
    status: string;
    effective_date: string | null;
    decommission_date: string | null;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface CreateRegionalImplementation {
    model_id: number;
    region_id: number;
    shared_model_owner_id?: number | null;
    local_identifier?: string | null;
    status?: string;
    effective_date?: string | null;
    decommission_date?: string | null;
    notes?: string | null;
}

export const regionalImplementationsApi = {
    getByModel: (modelId: number) =>
        api.get<RegionalImplementation[]>(`/models/${modelId}/regional-implementations`),

    create: (modelId: number, data: CreateRegionalImplementation) =>
        api.post<RegionalModelImplementation>(`/models/${modelId}/regional-implementations`, data),

    getById: (id: number) =>
        api.get<RegionalModelImplementation>(`/regional-implementations/${id}`),

    update: (id: number, data: Partial<CreateRegionalImplementation>) =>
        api.put<RegionalModelImplementation>(`/regional-implementations/${id}`, data),

    delete: (id: number) => api.delete(`/regional-implementations/${id}`)
};

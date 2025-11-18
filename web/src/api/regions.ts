import api from './client';

export interface Region {
    region_id: number;
    code: string;
    name: string;
    created_at: string;
}

export const regionsApi = {
    getAll: () => api.get<Region[]>('/regions/'),

    getById: (id: number) => api.get<Region>(`/regions/${id}`),

    create: (data: { code: string; name: string }) =>
        api.post<Region>('/regions/', data),

    update: (id: number, data: Partial<{ code: string; name: string }>) =>
        api.put<Region>(`/regions/${id}`, data),

    delete: (id: number) => api.delete(`/regions/${id}`)
};

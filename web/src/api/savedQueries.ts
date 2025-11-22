/**
 * Saved Queries API
 * Manages saved SQL queries for analytics
 */
import api from './client';

export interface SavedQuery {
    query_id: number;
    user_id: number;
    query_name: string;
    query_text: string;
    description?: string;
    is_public: boolean;
    created_at: string;
    updated_at: string;
}

export interface SavedQueryCreate {
    query_name: string;
    query_text: string;
    description?: string;
    is_public: boolean;
}

export interface SavedQueryUpdate {
    query_name?: string;
    query_text?: string;
    description?: string;
    is_public?: boolean;
}

export const savedQueriesApi = {
    /**
     * Get all saved queries for the current user
     */
    async list(): Promise<SavedQuery[]> {
        const response = await api.get('/saved-queries/');
        return response.data;
    },

    /**
     * Get a specific saved query by ID
     */
    async get(queryId: number): Promise<SavedQuery> {
        const response = await api.get(`/saved-queries/${queryId}`);
        return response.data;
    },

    /**
     * Create a new saved query
     */
    async create(queryData: SavedQueryCreate): Promise<SavedQuery> {
        const response = await api.post('/saved-queries/', queryData);
        return response.data;
    },

    /**
     * Update an existing saved query
     */
    async update(queryId: number, queryData: SavedQueryUpdate): Promise<SavedQuery> {
        const response = await api.patch(`/saved-queries/${queryId}`, queryData);
        return response.data;
    },

    /**
     * Delete a saved query
     */
    async delete(queryId: number): Promise<void> {
        await api.delete(`/saved-queries/${queryId}`);
    },
};

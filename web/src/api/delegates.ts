import api from './client';

export interface ModelDelegate {
    delegate_id: number;
    model_id: number;
    user_id: number;
    can_submit_changes: boolean;
    can_manage_regional: boolean;
    delegated_by_id: number;
    delegated_at: string;
    revoked_at: string | null;
    revoked_by_id: number | null;
    user_name: string | null;
    user_email: string | null;
    delegated_by_name: string | null;
    revoked_by_name: string | null;
}

export interface ModelDelegateCreate {
    user_id: number;
    can_submit_changes: boolean;
    can_manage_regional: boolean;
}

export interface ModelDelegateUpdate {
    can_submit_changes?: boolean;
    can_manage_regional?: boolean;
}

export interface BatchDelegateRequest {
    target_user_id: number;
    role: 'owner' | 'developer';
    delegate_user_id: number;
    can_submit_changes: boolean;
    can_manage_regional: boolean;
    replace_existing: boolean;
}

export interface ModelDelegateDetail {
    model_id: number;
    model_name: string;
    action: 'created' | 'updated' | 'replaced';
}

export interface BatchDelegateResponse {
    models_affected: number;
    model_details: ModelDelegateDetail[];
    delegations_created: number;
    delegations_updated: number;
    delegations_revoked: number;
}

export const delegatesApi = {
    // Create delegation
    createDelegate: async (modelId: number, data: ModelDelegateCreate): Promise<ModelDelegate> => {
        const response = await api.post(`/models/${modelId}/delegates`, data);
        return response.data;
    },

    // List delegates
    listDelegates: async (modelId: number, includeRevoked: boolean = false): Promise<ModelDelegate[]> => {
        const response = await api.get(`/models/${modelId}/delegates?include_revoked=${includeRevoked}`);
        return response.data;
    },

    // Update delegate permissions
    updateDelegate: async (delegateId: number, data: ModelDelegateUpdate): Promise<ModelDelegate> => {
        const response = await api.patch(`/delegates/${delegateId}`, data);
        return response.data;
    },

    // Revoke delegation
    revokeDelegate: async (delegateId: number): Promise<ModelDelegate> => {
        const response = await api.patch(`/delegates/${delegateId}/revoke`);
        return response.data;
    },

    // Delete delegation (Admin only)
    deleteDelegate: async (delegateId: number): Promise<void> => {
        await api.delete(`/delegates/${delegateId}`);
    },

    // Batch add/update delegates (Admin only)
    batchAddDelegates: async (data: BatchDelegateRequest): Promise<BatchDelegateResponse> => {
        const response = await api.post('/delegates/batch', data);
        return response.data;
    },
};

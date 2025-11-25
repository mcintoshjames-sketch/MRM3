/**
 * Overdue Commentary API
 */
import api from './client';

export interface UserResponse {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
}

export interface OverdueComment {
    comment_id: number;
    validation_request_id: number;
    overdue_type: 'PRE_SUBMISSION' | 'VALIDATION_IN_PROGRESS';
    reason_comment: string;
    target_date: string;
    created_by_user_id: number;
    created_by_user: UserResponse;
    created_at: string;
    is_current: boolean;
    superseded_at: string | null;
    superseded_by_comment_id: number | null;
}

export interface CurrentOverdueCommentaryResponse {
    validation_request_id: number;
    model_id: number;
    model_name: string;
    overdue_type: 'PRE_SUBMISSION' | 'VALIDATION_IN_PROGRESS' | null;
    has_current_comment: boolean;
    current_comment: OverdueComment | null;
    is_stale: boolean;
    stale_reason: string | null;
    computed_completion_date: string | null;
}

export interface OverdueCommentaryHistoryResponse {
    validation_request_id: number;
    model_id: number;
    model_name: string;
    current_comment: OverdueComment | null;
    comment_history: OverdueComment[];
}

export interface CreateOverdueCommentaryRequest {
    overdue_type: 'PRE_SUBMISSION' | 'VALIDATION_IN_PROGRESS';
    reason_comment: string;
    target_date: string;
}

export interface MyOverdueItem {
    overdue_type: 'PRE_SUBMISSION' | 'VALIDATION_IN_PROGRESS';
    request_id: number;
    model_id: number;
    model_name: string;
    risk_tier: string | null;
    days_overdue: number;
    due_date: string | null;
    user_role: 'owner' | 'developer' | 'delegate' | 'validator';
    current_status: string;
    comment_status: 'CURRENT' | 'STALE' | 'MISSING';
    latest_comment: string | null;
    latest_comment_date: string | null;
    target_date: string | null;
    needs_comment_update: boolean;
}

export const overdueCommentaryApi = {
    /**
     * Get overdue commentary for a validation request
     */
    getForRequest: async (requestId: number): Promise<CurrentOverdueCommentaryResponse> => {
        const response = await api.get(`/validation-workflow/requests/${requestId}/overdue-commentary`);
        return response.data;
    },

    /**
     * Create or update overdue commentary for a validation request
     */
    createForRequest: async (requestId: number, data: CreateOverdueCommentaryRequest): Promise<OverdueComment> => {
        const response = await api.post(`/validation-workflow/requests/${requestId}/overdue-commentary`, data);
        return response.data;
    },

    /**
     * Get overdue commentary history for a validation request
     */
    getHistoryForRequest: async (requestId: number): Promise<OverdueCommentaryHistoryResponse> => {
        const response = await api.get(`/validation-workflow/requests/${requestId}/overdue-commentary/history`);
        return response.data;
    },

    /**
     * Get overdue commentary for a model (convenience endpoint)
     */
    getForModel: async (modelId: number): Promise<CurrentOverdueCommentaryResponse> => {
        const response = await api.get(`/models/${modelId}/overdue-commentary`);
        return response.data;
    },

    /**
     * Get current user's overdue items
     */
    getMyOverdueItems: async (): Promise<MyOverdueItem[]> => {
        const response = await api.get('/validation-workflow/dashboard/my-overdue-items');
        return response.data;
    }
};

export default overdueCommentaryApi;

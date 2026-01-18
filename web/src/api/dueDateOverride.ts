/**
 * Due Date Override API
 *
 * Allows admins to override a model's validation submission due date
 * to an earlier date (accelerate validation schedule).
 */
import api from './client';

export interface UserResponse {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
}

export interface DueDateOverride {
    override_id: number;
    model_id: number;
    validation_request_id: number | null;
    override_type: 'ONE_TIME' | 'PERMANENT';
    target_scope: 'CURRENT_REQUEST' | 'NEXT_CYCLE';
    override_date: string;
    original_calculated_date: string;
    reason: string;
    created_by_user_id: number;
    created_by_user: UserResponse;
    created_at: string;
    is_active: boolean;
    cleared_at: string | null;
    cleared_by_user_id: number | null;
    cleared_by_user: UserResponse | null;
    cleared_reason: string | null;
    cleared_type: 'MANUAL' | 'AUTO_VALIDATION_COMPLETE' | 'AUTO_ROLL_FORWARD' | 'AUTO_REQUEST_CANCELLED' | 'SUPERSEDED' | null;
    superseded_by_override_id: number | null;
    rolled_from_override_id: number | null;
}

export interface CurrentDueDateOverrideResponse {
    model_id: number;
    model_name: string;
    has_active_override: boolean;
    active_override: DueDateOverride | null;
    policy_calculated_date: string | null;
    effective_due_date: string | null;
    current_validation_request_id: number | null;
    current_validation_status: string | null;
}

export interface DueDateOverrideHistoryResponse {
    model_id: number;
    model_name: string;
    active_override: DueDateOverride | null;
    override_history: DueDateOverride[];
}

export interface CreateDueDateOverrideRequest {
    override_type: 'ONE_TIME' | 'PERMANENT';
    target_scope: 'CURRENT_REQUEST' | 'NEXT_CYCLE';
    override_date: string;
    reason: string;
}

export interface ClearDueDateOverrideRequest {
    reason: string;
}

export const dueDateOverrideApi = {
    /**
     * Get current due date override status for a model
     */
    getForModel: async (modelId: number): Promise<CurrentDueDateOverrideResponse> => {
        const response = await api.get(`/models/${modelId}/due-date-override`);
        return response.data;
    },

    /**
     * Create a due date override (Admin only)
     */
    create: async (modelId: number, data: CreateDueDateOverrideRequest): Promise<DueDateOverride> => {
        const response = await api.post(`/models/${modelId}/due-date-override`, data);
        return response.data;
    },

    /**
     * Clear an active due date override (Admin only)
     */
    clear: async (modelId: number, data: ClearDueDateOverrideRequest): Promise<DueDateOverride> => {
        const response = await api.delete(`/models/${modelId}/due-date-override`, { data });
        return response.data;
    },

    /**
     * Get full history of due date overrides for a model
     */
    getHistory: async (modelId: number): Promise<DueDateOverrideHistoryResponse> => {
        const response = await api.get(`/models/${modelId}/due-date-override/history`);
        return response.data;
    }
};

export default dueDateOverrideApi;

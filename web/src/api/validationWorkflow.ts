import api from './client';

// ==================== INTERFACES ====================

export interface PreTransitionWarning {
    warning_type: 'PENDING_RECOMMENDATIONS' | 'UNADDRESSED_ATTESTATIONS';
    severity: 'ERROR' | 'WARNING' | 'INFO';
    message: string;
    model_id: number;
    model_name: string;
    details: Record<string, unknown> | null;
}

export interface PreTransitionWarningsResponse {
    request_id: number;
    target_status: string;
    warnings: PreTransitionWarning[];
    can_proceed: boolean;
    checked_at: string;
}

export interface ValidationWarning {
    warning_type: string;
    severity: 'ERROR' | 'WARNING' | 'INFO';
    message: string;
    model_id: number;
    model_name: string;
    version_number?: string | null;
    details?: Record<string, unknown> | null;
}

export interface ModelVersionEntry {
    model_id: number;
    version_id?: number | null;
}

export interface ValidationRequestModelUpdatePayload {
    add_models?: ModelVersionEntry[];
    remove_model_ids?: number[];
    allow_unassign_conflicts?: boolean;
}

export interface ValidationRequestModelUpdateResponse {
    success: boolean;
    models_added: number[];
    models_removed: number[];
    lead_time_changed: boolean;
    old_lead_time_days?: number | null;
    new_lead_time_days?: number | null;
    warnings: ValidationWarning[];
    plan_deviations_flagged: number;
    approvals_added: number;
    approvals_voided: number;
    conditional_approvals_added: number;
    conditional_approvals_voided: number;
    validators_unassigned: string[];
}

// ==================== API CLIENT ====================

export const validationWorkflowApi = {
    /**
     * Get pre-transition warnings for a validation request.
     * These warnings alert validators about potential issues before advancing
     * to the Pending Approval stage.
     *
     * Warning types:
     * - PENDING_RECOMMENDATIONS: Model has open recommendations not yet Closed/Superseded/Rejected
     * - UNADDRESSED_ATTESTATIONS: Owner attestations still pending for this validation
     *
     * @param requestId - The validation request ID
     * @param targetStatus - The target status to transition to (default: PENDING_APPROVAL)
     * @returns PreTransitionWarningsResponse with warnings and can_proceed flag
     */
    getPreTransitionWarnings: async (
        requestId: number,
        targetStatus: string = 'PENDING_APPROVAL'
    ): Promise<PreTransitionWarningsResponse> => {
        const response = await api.get(
            `/validation-workflow/requests/${requestId}/pre-transition-warnings`,
            { params: { target_status: targetStatus } }
        );
        return response.data;
    },

    updateRequestModels: async (
        requestId: number,
        payload: ValidationRequestModelUpdatePayload
    ): Promise<ValidationRequestModelUpdateResponse> => {
        const response = await api.patch(
            `/validation-workflow/requests/${requestId}/models`,
            payload
        );
        return response.data;
    },
};

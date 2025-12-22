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
};

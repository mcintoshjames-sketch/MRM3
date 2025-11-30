import api from './client';

// ==================== INTERFACES ====================

export interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
    description?: string;
}

export interface UserSummary {
    user_id: number;
    email: string;
    full_name: string;
}

export interface ModelSummary {
    model_id: number;
    model_name: string;
}

export interface ValidationRequestSummary {
    request_id: number;
    validation_code: string;
    validation_type?: string;
}

export interface MonitoringCycleSummary {
    cycle_id: number;
    period_start: string;
    period_end: string;
    plan_name?: string;
}

export interface Recommendation {
    recommendation_id: number;
    recommendation_code: string;
    model_id: number;
    // Source linkage (optional - at least one should be set)
    validation_request_id: number | null;
    validation_request?: ValidationRequestSummary | null;
    monitoring_cycle_id: number | null;
    monitoring_cycle?: MonitoringCycleSummary | null;
    title: string;
    description: string;
    root_cause_analysis: string | null;
    priority_id: number;
    category_id: number | null;
    current_status_id: number;
    created_by_id: number;
    assigned_to_id: number;
    original_target_date: string;
    current_target_date: string;
    closed_at: string | null;
    closed_by_id: number | null;
    closure_summary: string | null;
    finalized_at: string | null;
    finalized_by_id: number | null;
    acknowledged_at: string | null;
    acknowledged_by_id: number | null;
    created_at: string;
    updated_at: string;
    // Expanded relationships
    model?: ModelSummary;
    priority?: TaxonomyValue;
    category?: TaxonomyValue;
    current_status?: TaxonomyValue;
    created_by?: UserSummary;
    assigned_to?: UserSummary;
    closed_by?: UserSummary;
    finalized_by?: UserSummary;
    acknowledged_by?: UserSummary;
    action_plan_tasks?: ActionPlanTask[];
    rebuttals?: Rebuttal[];
    closure_evidence?: ClosureEvidence[];
    status_history?: StatusHistory[];
    approvals?: Approval[];
}

export interface RecommendationListItem {
    recommendation_id: number;
    recommendation_code: string;
    model_id: number;
    // Source linkage info
    validation_request_id: number | null;
    monitoring_cycle_id: number | null;
    source_type?: 'validation' | 'monitoring' | null;
    title: string;
    priority_id: number;
    category_id: number | null;
    current_status_id: number;
    assigned_to_id: number;
    original_target_date: string;
    current_target_date: string;
    created_at: string;
    updated_at: string;
    model?: ModelSummary;
    priority?: TaxonomyValue;
    category?: TaxonomyValue;
    current_status?: TaxonomyValue;
    assigned_to?: UserSummary;
}

export interface RecommendationCreate {
    model_id: number;
    validation_request_id?: number | null;
    monitoring_cycle_id?: number | null;
    title: string;
    description: string;
    priority_id: number;
    category_id?: number | null;
    assigned_to_id: number;
    original_target_date: string;
}

export interface RecommendationUpdate {
    title?: string;
    description?: string;
    root_cause_analysis?: string;
    priority_id?: number;
    category_id?: number | null;
    assigned_to_id?: number;
    current_target_date?: string;
}

// Action Plan Tasks
export interface ActionPlanTask {
    task_id: number;
    recommendation_id: number;
    task_order: number;
    description: string;
    owner_id: number;
    target_date: string;
    completed_date: string | null;
    completion_status_id: number;
    completion_notes: string | null;
    created_at: string;
    updated_at: string;
    owner?: UserSummary;
    completion_status?: TaxonomyValue;
}

export interface ActionPlanTaskCreate {
    description: string;
    owner_id: number;
    target_date: string;
    task_order?: number;
}

export interface ActionPlanTaskUpdate {
    description?: string;
    owner_id?: number;
    target_date?: string;
    completed_date?: string;
    completion_status_id?: number;
    completion_notes?: string;
}

// Rebuttals
export interface Rebuttal {
    rebuttal_id: number;
    recommendation_id: number;
    submitted_by_id: number;
    rationale: string;
    supporting_evidence: string | null;
    submitted_at: string;
    reviewed_by_id: number | null;
    reviewed_at: string | null;
    review_decision: string | null;
    review_comments: string | null;
    is_current: boolean;
    submitted_by?: UserSummary;
    reviewed_by?: UserSummary;
}

export interface RebuttalCreate {
    rationale: string;
    supporting_evidence?: string;
}

export interface RebuttalReview {
    decision: 'ACCEPT' | 'OVERRIDE';
    comments?: string;
    review_comments?: string;  // Alias for compatibility
}

// Closure Evidence
export interface ClosureEvidence {
    evidence_id: number;
    recommendation_id: number;
    description: string;
    evidence_url: string | null;
    uploaded_by_id: number;
    uploaded_at: string;
    uploaded_by?: UserSummary;
}

export interface ClosureEvidenceCreate {
    description: string;
    evidence_url?: string;
}

// Status History
export interface StatusHistory {
    history_id: number;
    recommendation_id: number;
    old_status_id: number | null;
    new_status_id: number;
    changed_by_id: number;
    changed_at: string;
    change_reason: string | null;
    additional_context: string | null;
    old_status?: TaxonomyValue;
    new_status?: TaxonomyValue;
    status?: TaxonomyValue;  // Alias for new_status used in timeline
    changed_by?: UserSummary;
}

// Approvals
export interface Approval {
    approval_id: number;
    recommendation_id: number;
    approval_type: 'GLOBAL' | 'REGIONAL';
    region_id: number | null;
    represented_region_id: number | null;
    approver_id: number | null;
    approved_at: string | null;
    is_required: boolean;
    approval_status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'VOIDED';
    decision: 'APPROVE' | 'REJECT' | null;  // For UI compatibility
    decided_at: string | null;  // For UI compatibility
    comments: string | null;
    approval_evidence: string | null;
    voided_by_id: number | null;
    void_reason: string | null;
    voided_at: string | null;
    created_at: string;
    approver?: UserSummary;
    approver_role?: TaxonomyValue;
    voided_by?: UserSummary;
    region?: { region_id: number; code: string; name: string };
}

export interface ApprovalRequest {
    decision: 'APPROVE' | 'REJECT';
    comments?: string;
    approval_evidence?: string;
}

export interface ApprovalReject {
    rejection_reason: string;
}

// Priority Config
export interface PriorityConfig {
    config_id: number;
    priority_id: number;
    requires_final_approval: boolean;
    description: string | null;
    created_at: string;
    updated_at: string;
    priority?: TaxonomyValue;
}

// Dashboard types
export interface MyTaskItem {
    task_type: 'ACTION_REQUIRED' | 'REVIEW_PENDING' | 'APPROVAL_PENDING';
    recommendation_id: number;
    recommendation_code: string;
    title: string;
    model: ModelSummary;
    priority: TaxonomyValue;
    current_status: TaxonomyValue;
    current_target_date: string;
    action_description: string;
    days_until_due: number | null;
    is_overdue: boolean;
}

export interface MyTasksResponse {
    total_tasks: number;
    overdue_count: number;
    tasks: MyTaskItem[];
}

export interface StatusSummary {
    status_code: string;
    status_label: string;
    count: number;
}

export interface PrioritySummary {
    priority_code: string;
    priority_label: string;
    count: number;
}

export interface OpenRecommendationsSummary {
    total_open: number;
    by_status: StatusSummary[];
    by_priority: PrioritySummary[];
}

export interface OverdueRecommendation {
    recommendation_id: number;
    recommendation_code: string;
    title: string;
    model: ModelSummary;
    priority: TaxonomyValue;
    current_status: TaxonomyValue;
    assigned_to: UserSummary;
    current_target_date: string;
    days_overdue: number;
}

export interface OverdueRecommendationsReport {
    total_overdue: number;
    by_priority: PrioritySummary[];
    recommendations: OverdueRecommendation[];
}

// ==================== API CLIENT ====================

export const recommendationsApi = {
    // List recommendations with filters
    list: async (params?: {
        model_id?: number;
        status_id?: number;
        priority_id?: number;
        assigned_to_id?: number;
        offset?: number;
        limit?: number;
    }): Promise<RecommendationListItem[]> => {
        const response = await api.get('/recommendations/', { params });
        return response.data;
    },

    // Get a single recommendation with all details
    get: async (id: number): Promise<Recommendation> => {
        const response = await api.get(`/recommendations/${id}`);
        return response.data;
    },

    // Create a new recommendation (Validator/Admin only)
    create: async (data: RecommendationCreate): Promise<Recommendation> => {
        const response = await api.post('/recommendations/', data);
        return response.data;
    },

    // Update a recommendation
    update: async (id: number, data: RecommendationUpdate): Promise<Recommendation> => {
        const response = await api.patch(`/recommendations/${id}`, data);
        return response.data;
    },

    // ==================== WORKFLOW ACTIONS ====================

    // Finalize recommendation (transition from DRAFT to PENDING_RESPONSE)
    finalize: async (id: number): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/finalize`);
        return response.data;
    },

    // Acknowledge recommendation (Developer)
    acknowledge: async (id: number): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/acknowledge`);
        return response.data;
    },

    // Decline acknowledgement (Developer) - redirects to rebuttal
    declineAcknowledgement: async (id: number, reason: string): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/decline-acknowledgement`, { reason });
        return response.data;
    },

    // Submit for closure review
    submitForClosureReview: async (id: number, closureSummary: string): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/submit-closure`, { closure_summary: closureSummary });
        return response.data;
    },

    // Validator approves closure
    approveClosureReview: async (id: number, comments?: string): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/approve-closure-review`, { comments });
        return response.data;
    },

    // Validator rejects closure (request rework)
    rejectClosureReview: async (id: number, feedback: string): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/reject-closure-review`, { feedback });
        return response.data;
    },

    // ==================== ACTION PLAN ====================

    submitActionPlan: async (id: number, tasks: ActionPlanTaskCreate[]): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/action-plan`, { tasks });
        return response.data;
    },

    approveActionPlan: async (id: number, comments?: string): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/action-plan/approve`, { comments });
        return response.data;
    },

    rejectActionPlan: async (id: number, feedback: string): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/action-plan/reject`, { feedback });
        return response.data;
    },

    updateTask: async (recommendationId: number, taskId: number, data: ActionPlanTaskUpdate): Promise<ActionPlanTask> => {
        const response = await api.patch(`/recommendations/${recommendationId}/tasks/${taskId}`, data);
        return response.data;
    },

    // ==================== REBUTTAL ====================

    submitRebuttal: async (id: number, data: RebuttalCreate): Promise<{ rebuttal_id: number; recommendation: Recommendation }> => {
        const response = await api.post(`/recommendations/${id}/rebuttals`, data);
        return response.data;
    },

    reviewRebuttal: async (recommendationId: number, rebuttalId: number, data: RebuttalReview): Promise<Rebuttal> => {
        const response = await api.post(`/recommendations/${recommendationId}/rebuttals/${rebuttalId}/review`, data);
        return response.data;
    },

    // ==================== CLOSURE EVIDENCE ====================

    addClosureEvidence: async (id: number, data: ClosureEvidenceCreate): Promise<ClosureEvidence> => {
        const response = await api.post(`/recommendations/${id}/evidence`, data);
        return response.data;
    },

    deleteClosureEvidence: async (recommendationId: number, evidenceId: number): Promise<void> => {
        await api.delete(`/recommendations/${recommendationId}/evidence/${evidenceId}`);
    },

    // ==================== APPROVALS ====================

    getApprovals: async (id: number): Promise<Approval[]> => {
        const response = await api.get(`/recommendations/${id}/approvals`);
        return response.data;
    },

    submitApproval: async (recommendationId: number, approvalId: number, data: ApprovalRequest): Promise<Approval> => {
        const response = await api.post(`/recommendations/${recommendationId}/approvals/${approvalId}/approve`, data);
        return response.data;
    },

    rejectApproval: async (recommendationId: number, approvalId: number, data: ApprovalReject): Promise<Approval> => {
        const response = await api.post(`/recommendations/${recommendationId}/approvals/${approvalId}/reject`, data);
        return response.data;
    },

    voidApproval: async (recommendationId: number, approvalId: number, reason: string): Promise<Approval> => {
        const response = await api.post(`/recommendations/${recommendationId}/approvals/${approvalId}/void`, { rejection_reason: reason });
        return response.data;
    },

    // ==================== PRIORITY CONFIG (Admin) ====================

    getPriorityConfigs: async (): Promise<PriorityConfig[]> => {
        const response = await api.get('/recommendations/priority-config/');
        return response.data;
    },

    updatePriorityConfig: async (configId: number, data: { requires_final_approval?: boolean; description?: string }): Promise<PriorityConfig> => {
        const response = await api.patch(`/recommendations/priority-config/${configId}`, data);
        return response.data;
    },

    // ==================== DASHBOARD & REPORTS ====================

    getMyTasks: async (): Promise<MyTasksResponse> => {
        const response = await api.get('/recommendations/my-tasks');
        return response.data;
    },

    getOpenSummary: async (): Promise<OpenRecommendationsSummary> => {
        const response = await api.get('/recommendations/dashboard/open');
        return response.data;
    },

    getOverdueReport: async (): Promise<OverdueRecommendationsReport> => {
        const response = await api.get('/recommendations/dashboard/overdue');
        return response.data;
    },

    getByModel: async (modelId: number, includeClosed?: boolean): Promise<RecommendationListItem[]> => {
        const response = await api.get(`/recommendations/dashboard/by-model/${modelId}`, {
            params: { include_closed: includeClosed }
        });
        return response.data;
    },

    // ==================== CONVENIENCE METHODS ====================

    // Review action plan (approve or request changes)
    reviewActionPlan: async (id: number, data: { decision: 'APPROVE' | 'REQUEST_CHANGES'; comments?: string }): Promise<Recommendation> => {
        if (data.decision === 'APPROVE') {
            const response = await api.post(`/recommendations/${id}/action-plan/approve`, { comments: data.comments });
            return response.data;
        } else {
            const response = await api.post(`/recommendations/${id}/action-plan/reject`, { feedback: data.comments || '' });
            return response.data;
        }
    },

    // Review closure (approve or request rework)
    reviewClosure: async (id: number, data: { decision: 'APPROVE' | 'REQUEST_REWORK'; review_comments?: string }): Promise<Recommendation> => {
        if (data.decision === 'APPROVE') {
            const response = await api.post(`/recommendations/${id}/approve-closure-review`, { comments: data.review_comments });
            return response.data;
        } else {
            const response = await api.post(`/recommendations/${id}/reject-closure-review`, { feedback: data.review_comments || '' });
            return response.data;
        }
    },

    // Submit for closure (alias)
    submitForClosure: async (id: number, data: { closure_summary: string }): Promise<Recommendation> => {
        const response = await api.post(`/recommendations/${id}/submit-closure`, data);
        return response.data;
    },

    // Upload evidence (convenience method)
    uploadEvidence: async (id: number, data: { description: string; evidence_url?: string }): Promise<ClosureEvidence> => {
        const response = await api.post(`/recommendations/${id}/evidence`, data);
        return response.data;
    },

    // Delete evidence (alias)
    deleteEvidence: async (recommendationId: number, evidenceId: number): Promise<void> => {
        await api.delete(`/recommendations/${recommendationId}/evidence/${evidenceId}`);
    },
};

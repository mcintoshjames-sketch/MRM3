import api from './client';

// ==================== INTERFACES ====================

export interface UserBrief {
    user_id: number;
    email: string;
    full_name: string | null;
}

export interface ModelBrief {
    model_id: number;
    model_name: string;
    model_code: string | null;
}

export interface TaxonomyValueBrief {
    value_id: number;
    code: string;
    label: string;
}

export interface ModelExceptionStatusHistory {
    history_id: number;
    exception_id: number;
    old_status: string | null;
    new_status: string;
    changed_by_id: number | null;
    changed_by: UserBrief | null;
    changed_at: string;
    notes: string | null;
}

export interface ModelExceptionListItem {
    exception_id: number;
    exception_code: string;
    model_id: number;
    model: ModelBrief;
    exception_type: string;
    status: string;
    description: string;
    detected_at: string;
    auto_closed: boolean;
    acknowledged_at: string | null;
    closed_at: string | null;
    created_at: string;
    updated_at: string;
}

export interface ModelExceptionDetail {
    exception_id: number;
    exception_code: string;
    model_id: number;
    model: ModelBrief;
    exception_type: string;
    status: string;
    description: string;
    detected_at: string;
    auto_closed: boolean;
    // Source entity IDs (only one will be populated)
    monitoring_result_id: number | null;
    attestation_response_id: number | null;
    deployment_task_id: number | null;
    // Acknowledgment
    acknowledged_by_id: number | null;
    acknowledged_by: UserBrief | null;
    acknowledged_at: string | null;
    acknowledgment_notes: string | null;
    // Closure
    closed_at: string | null;
    closed_by_id: number | null;
    closed_by: UserBrief | null;
    closure_narrative: string | null;
    closure_reason_id: number | null;
    closure_reason: TaxonomyValueBrief | null;
    // Timestamps
    created_at: string;
    updated_at: string;
    // Status history
    status_history: ModelExceptionStatusHistory[];
}

export interface PaginatedExceptionResponse {
    items: ModelExceptionListItem[];
    total: number;
    skip: number;
    limit: number;
}

export interface ExceptionSummary {
    total_open: number;
    total_acknowledged: number;
    total_closed: number;
    by_type: Record<string, number>;
}

export interface DetectionResponse {
    type1_count: number;
    type2_count: number;
    type3_count: number;
    total_created: number;
    exceptions: ModelExceptionListItem[];
}

export interface AcknowledgeRequest {
    notes?: string;
}

export interface CloseRequest {
    closure_narrative: string;
    closure_reason_id: number;
}

export interface CreateExceptionRequest {
    model_id: number;
    exception_type: string;
    description: string;
    acknowledgment_notes?: string;
    initial_status?: 'OPEN' | 'ACKNOWLEDGED';
}

// Exception type labels for display
export const EXCEPTION_TYPE_LABELS: Record<string, string> = {
    'UNMITIGATED_PERFORMANCE': 'Unmitigated Performance Problem',
    'OUTSIDE_INTENDED_PURPOSE': 'Model Used Outside Intended Purpose',
    'USE_PRIOR_TO_VALIDATION': 'Model In Use Prior to Full Validation',
};

// Exception status labels and colors for display
export const EXCEPTION_STATUS_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
    'OPEN': { label: 'Open', color: 'text-red-800', bgColor: 'bg-red-100' },
    'ACKNOWLEDGED': { label: 'Acknowledged', color: 'text-yellow-800', bgColor: 'bg-yellow-100' },
    'CLOSED': { label: 'Closed', color: 'text-green-800', bgColor: 'bg-green-100' },
};

// ==================== API CLIENT ====================

export const exceptionsApi = {
    // Create a new exception (Admin only)
    create: async (data: CreateExceptionRequest): Promise<ModelExceptionDetail> => {
        const response = await api.post('/exceptions/', data);
        return response.data;
    },

    // List exceptions with filters
    list: async (params?: {
        model_id?: number;
        exception_type?: string;
        status?: string;
        region_id?: number;
        skip?: number;
        limit?: number;
    }): Promise<PaginatedExceptionResponse> => {
        const response = await api.get('/exceptions/', { params });
        return response.data;
    },

    // Get summary statistics
    getSummary: async (model_id?: number): Promise<ExceptionSummary> => {
        const response = await api.get('/exceptions/summary', { params: { model_id } });
        return response.data;
    },

    // Get a single exception with full details
    get: async (id: number): Promise<ModelExceptionDetail> => {
        const response = await api.get(`/exceptions/${id}`);
        return response.data;
    },

    // Acknowledge an exception (Admin only)
    acknowledge: async (id: number, data?: AcknowledgeRequest): Promise<ModelExceptionDetail> => {
        const response = await api.post(`/exceptions/${id}/acknowledge`, data || {});
        return response.data;
    },

    // Close an exception (Admin only)
    close: async (id: number, data: CloseRequest): Promise<ModelExceptionDetail> => {
        const response = await api.post(`/exceptions/${id}/close`, data);
        return response.data;
    },

    // Detect exceptions for a specific model (Admin only)
    detectForModel: async (modelId: number): Promise<DetectionResponse> => {
        const response = await api.post(`/exceptions/detect/${modelId}`);
        return response.data;
    },

    // Detect exceptions for all models (Admin only)
    detectAll: async (): Promise<DetectionResponse> => {
        const response = await api.post('/exceptions/detect-all');
        return response.data;
    },

    // Get exceptions for a specific model
    getByModel: async (modelId: number, status?: string): Promise<ModelExceptionListItem[]> => {
        const response = await api.get(`/exceptions/model/${modelId}`, { params: { status } });
        return response.data;
    },

    // Get closure reason options
    getClosureReasons: async (): Promise<TaxonomyValueBrief[]> => {
        const response = await api.get('/exceptions/closure-reasons');
        return response.data;
    },
};

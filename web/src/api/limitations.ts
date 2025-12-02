/**
 * API client for Model Limitations endpoints.
 */
import client from './client';

// Types
export interface LimitationCategory {
    value_id: number;
    code: string;
    label: string;
    description?: string;
}

export interface LimitationListItem {
    limitation_id: number;
    model_id: number;
    significance: 'Critical' | 'Non-Critical';
    category_id: number;
    category_label?: string;
    description: string;
    conclusion: 'Mitigate' | 'Accept';
    is_retired: boolean;
    created_at: string;
}

export interface LimitationDetail {
    limitation_id: number;
    model_id: number;
    validation_request_id?: number;
    model_version_id?: number;
    recommendation_id?: number;
    significance: 'Critical' | 'Non-Critical';
    category_id: number;
    description: string;
    impact_assessment: string;
    conclusion: 'Mitigate' | 'Accept';
    conclusion_rationale: string;
    user_awareness_description?: string;
    is_retired: boolean;
    retirement_date?: string;
    retirement_reason?: string;
    retired_by_id?: number;
    created_by_id: number;
    created_at: string;
    updated_at: string;
    // Expanded relationships
    model?: {
        model_id: number;
        model_name: string;
    };
    validation_request?: {
        request_id: number;
    };
    model_version?: {
        version_id: number;
        version_name: string;
    };
    recommendation?: {
        recommendation_id: number;
        title: string;
    };
    category?: LimitationCategory;
    created_by?: {
        user_id: number;
        full_name: string;
    };
    retired_by?: {
        user_id: number;
        full_name: string;
    };
}

export interface LimitationCreate {
    validation_request_id?: number;
    model_version_id?: number;
    recommendation_id?: number;
    significance: 'Critical' | 'Non-Critical';
    category_id: number;
    description: string;
    impact_assessment: string;
    conclusion: 'Mitigate' | 'Accept';
    conclusion_rationale: string;
    user_awareness_description?: string;
}

export interface LimitationUpdate {
    validation_request_id?: number | null;
    model_version_id?: number | null;
    recommendation_id?: number | null;
    significance?: 'Critical' | 'Non-Critical';
    category_id?: number;
    description?: string;
    impact_assessment?: string;
    conclusion?: 'Mitigate' | 'Accept';
    conclusion_rationale?: string;
    user_awareness_description?: string | null;
}

export interface LimitationRetire {
    retirement_reason: string;
}

export interface CriticalLimitationReportItem {
    limitation_id: number;
    model_id: number;
    model_name: string;
    region_name?: string;
    category_label: string;
    description: string;
    impact_assessment: string;
    conclusion: 'Mitigate' | 'Accept';
    conclusion_rationale: string;
    user_awareness_description: string;
    originating_validation?: string;
    created_at: string;
}

export interface CriticalLimitationsReportResponse {
    filters_applied: Record<string, unknown>;
    total_count: number;
    items: CriticalLimitationReportItem[];
}

// API functions

/**
 * List limitations for a model.
 */
export async function listModelLimitations(
    modelId: number,
    params?: {
        include_retired?: boolean;
        significance?: 'Critical' | 'Non-Critical';
        conclusion?: 'Mitigate' | 'Accept';
        category_id?: number;
    }
): Promise<LimitationListItem[]> {
    const response = await client.get(`/models/${modelId}/limitations`, { params });
    return response.data;
}

/**
 * Create a new limitation for a model.
 */
export async function createLimitation(
    modelId: number,
    data: LimitationCreate
): Promise<LimitationDetail> {
    const response = await client.post(`/models/${modelId}/limitations`, data);
    return response.data;
}

/**
 * Get limitation details.
 */
export async function getLimitation(limitationId: number): Promise<LimitationDetail> {
    const response = await client.get(`/limitations/${limitationId}`);
    return response.data;
}

/**
 * Update a limitation.
 */
export async function updateLimitation(
    limitationId: number,
    data: LimitationUpdate
): Promise<LimitationDetail> {
    const response = await client.patch(`/limitations/${limitationId}`, data);
    return response.data;
}

/**
 * Retire a limitation.
 */
export async function retireLimitation(
    limitationId: number,
    data: LimitationRetire
): Promise<LimitationDetail> {
    const response = await client.post(`/limitations/${limitationId}/retire`, data);
    return response.data;
}

/**
 * Get critical limitations report.
 */
export async function getCriticalLimitationsReport(
    regionId?: number
): Promise<CriticalLimitationsReportResponse> {
    const params = regionId ? { region_id: regionId } : {};
    const response = await client.get('/reports/critical-limitations', { params });
    return response.data;
}

/**
 * List limitations for a validation request.
 * Returns limitations that were documented during this validation.
 */
export async function listValidationRequestLimitations(
    requestId: number,
    params?: {
        include_retired?: boolean;
    }
): Promise<LimitationListItem[]> {
    const response = await client.get(`/validation-requests/${requestId}/limitations`, { params });
    return response.data;
}

/**
 * List limitations linked to a recommendation.
 * Returns limitations that have this recommendation set as their mitigation recommendation.
 */
export async function listRecommendationLimitations(
    recommendationId: number,
    params?: {
        include_retired?: boolean;
    }
): Promise<LimitationListItem[]> {
    const response = await client.get(`/recommendations/${recommendationId}/limitations`, { params });
    return response.data;
}

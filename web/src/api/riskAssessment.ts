/**
 * API client for Model Risk Assessment endpoints.
 */
import client from './client';

// ============================================================================
// Types
// ============================================================================

export interface FactorRatingInput {
    factor_id: number;
    rating: 'HIGH' | 'MEDIUM' | 'LOW' | null;
    comment?: string;
}

export interface RiskAssessmentCreate {
    region_id: number | null;
    quantitative_rating?: 'HIGH' | 'MEDIUM' | 'LOW';
    quantitative_comment?: string;
    quantitative_override?: 'HIGH' | 'MEDIUM' | 'LOW';
    quantitative_override_comment?: string;
    qualitative_override?: 'HIGH' | 'MEDIUM' | 'LOW';
    qualitative_override_comment?: string;
    derived_risk_tier_override?: 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW';
    derived_risk_tier_override_comment?: string;
    factor_ratings: FactorRatingInput[];
}

export interface RiskAssessmentUpdate {
    quantitative_rating?: 'HIGH' | 'MEDIUM' | 'LOW';
    quantitative_comment?: string;
    quantitative_override?: 'HIGH' | 'MEDIUM' | 'LOW';
    quantitative_override_comment?: string;
    qualitative_override?: 'HIGH' | 'MEDIUM' | 'LOW';
    qualitative_override_comment?: string;
    derived_risk_tier_override?: 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW';
    derived_risk_tier_override_comment?: string;
    factor_ratings: FactorRatingInput[];
}

export interface QualitativeFactorResponse {
    factor_assessment_id: number;
    factor_id: number;
    factor_code: string;
    factor_name: string;
    rating: 'HIGH' | 'MEDIUM' | 'LOW' | null;
    comment: string | null;
    weight: number;
    score: number | null;
}

export interface RegionBrief {
    region_id: number;
    code: string;
    name: string;
}

export interface UserBrief {
    user_id: number;
    email: string;
    full_name: string;
}

export interface TaxonomyValueBrief {
    value_id: number;
    code: string;
    label: string;
}

export interface RiskAssessmentResponse {
    assessment_id: number;
    model_id: number;
    region: RegionBrief | null;
    qualitative_factors: QualitativeFactorResponse[];
    qualitative_calculated_score: number | null;
    qualitative_calculated_level: 'HIGH' | 'MEDIUM' | 'LOW' | null;
    qualitative_override: 'HIGH' | 'MEDIUM' | 'LOW' | null;
    qualitative_override_comment: string | null;
    qualitative_effective_level: 'HIGH' | 'MEDIUM' | 'LOW' | null;
    quantitative_rating: 'HIGH' | 'MEDIUM' | 'LOW' | null;
    quantitative_comment: string | null;
    quantitative_override: 'HIGH' | 'MEDIUM' | 'LOW' | null;
    quantitative_override_comment: string | null;
    quantitative_effective_rating: 'HIGH' | 'MEDIUM' | 'LOW' | null;
    derived_risk_tier: 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW' | null;
    derived_risk_tier_override: 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW' | null;
    derived_risk_tier_override_comment: string | null;
    derived_risk_tier_effective: 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW' | null;
    final_tier: TaxonomyValueBrief | null;
    assessed_by: UserBrief | null;
    assessed_at: string | null;
    is_complete: boolean;
    created_at: string;
    updated_at: string;
}

export interface RiskAssessmentHistoryItem {
    log_id: number;
    action: string;
    timestamp: string;
    user_id: number | null;
    user_name: string | null;
    region_id: number | null;
    region_name: string | null;
    old_tier: string | null;
    new_tier: string | null;
    old_quantitative: string | null;
    new_quantitative: string | null;
    old_qualitative: string | null;
    new_qualitative: string | null;
    changes_summary: string;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * List all risk assessments for a model.
 */
export async function listAssessments(modelId: number): Promise<RiskAssessmentResponse[]> {
    const response = await client.get(`/models/${modelId}/risk-assessments/`);
    return response.data;
}

/**
 * Get a specific risk assessment.
 */
export async function getAssessment(
    modelId: number,
    assessmentId: number
): Promise<RiskAssessmentResponse> {
    const response = await client.get(`/models/${modelId}/risk-assessments/${assessmentId}`);
    return response.data;
}

/**
 * Create a new risk assessment for a model.
 */
export async function createAssessment(
    modelId: number,
    data: RiskAssessmentCreate
): Promise<RiskAssessmentResponse> {
    const response = await client.post(`/models/${modelId}/risk-assessments/`, data);
    return response.data;
}

/**
 * Update an existing risk assessment.
 */
export async function updateAssessment(
    modelId: number,
    assessmentId: number,
    data: RiskAssessmentUpdate
): Promise<RiskAssessmentResponse> {
    const response = await client.put(`/models/${modelId}/risk-assessments/${assessmentId}`, data);
    return response.data;
}

/**
 * Delete a risk assessment.
 */
export async function deleteAssessment(modelId: number, assessmentId: number): Promise<void> {
    await client.delete(`/models/${modelId}/risk-assessments/${assessmentId}`);
}

/**
 * Get risk assessment history for a model.
 */
export async function getAssessmentHistory(modelId: number): Promise<RiskAssessmentHistoryItem[]> {
    const response = await client.get(`/models/${modelId}/risk-assessments/history`);
    return response.data;
}

// ============================================================================
// Risk Calculation Helpers
// ============================================================================

export const RATING_SCORES: Record<string, number> = {
    HIGH: 3,
    MEDIUM: 2,
    LOW: 1,
};

export const RATING_COLORS: Record<string, { bg: string; text: string; border: string }> = {
    HIGH: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300' },
    MEDIUM: { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300' },
    LOW: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300' },
    VERY_LOW: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-300' },
};

export const TIER_MAP: Record<string, string> = {
    HIGH: 'TIER_1',
    MEDIUM: 'TIER_2',
    LOW: 'TIER_3',
    VERY_LOW: 'TIER_4',
};

export const TIER_LABELS: Record<string, string> = {
    TIER_1: 'Tier 1 (High)',
    TIER_2: 'Tier 2 (Medium)',
    TIER_3: 'Tier 3 (Low)',
    TIER_4: 'Tier 4 (Very Low)',
};

/**
 * Inherent risk matrix lookup.
 */
export function lookupInherentRisk(
    quantitative: 'HIGH' | 'MEDIUM' | 'LOW',
    qualitative: 'HIGH' | 'MEDIUM' | 'LOW'
): 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW' {
    const matrix: Record<string, Record<string, 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW'>> = {
        HIGH: { HIGH: 'HIGH', MEDIUM: 'MEDIUM', LOW: 'LOW' },
        MEDIUM: { HIGH: 'MEDIUM', MEDIUM: 'MEDIUM', LOW: 'LOW' },
        LOW: { HIGH: 'LOW', MEDIUM: 'LOW', LOW: 'VERY_LOW' },
    };
    return matrix[quantitative][qualitative];
}

// ============================================================================
// Risk Tier Change Impact Check
// ============================================================================

export interface OpenValidationSummary {
    request_id: number;
    current_status: string;
    validation_type: string;
    has_plan: boolean;
    pending_approvals_count: number;
    primary_validator: string | null;
}

export interface OpenValidationsCheckResponse {
    model_id: number;
    model_name: string;
    current_risk_tier: string | null;
    proposed_risk_tier: string | null;
    has_open_validations: boolean;
    open_validation_count: number;
    open_validations: OpenValidationSummary[];
    warning_message: string | null;
    requires_confirmation: boolean;
}

/**
 * Check if a model has open validation requests that will be affected by a risk tier change.
 * @param modelId - The model ID to check
 * @param proposedTierCode - The proposed new tier code (e.g., 'TIER_2') for change detection
 */
export async function checkOpenValidationsForModel(
    modelId: number,
    proposedTierCode?: string
): Promise<OpenValidationsCheckResponse> {
    const params = new URLSearchParams();
    if (proposedTierCode) {
        params.append('proposed_tier_code', proposedTierCode);
    }
    const queryString = params.toString();
    const url = `/validation-workflow/risk-tier-impact/check/${modelId}${queryString ? `?${queryString}` : ''}`;
    const response = await client.get<OpenValidationsCheckResponse>(url);
    return response.data;
}

export const downloadAssessmentPdf = async (modelId: number, assessmentId: number): Promise<void> => {
    const response = await client.get(`/models/${modelId}/risk-assessments/${assessmentId}/pdf`, {
        responseType: 'blob',
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;

    const contentDisposition = response.headers['content-disposition'];
    let filename = `Risk_Assessment_${modelId}.pdf`;
    if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch && filenameMatch.length === 2)
            filename = filenameMatch[1];
    }

    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
};

export default {
    listAssessments,
    getAssessment,
    createAssessment,
    updateAssessment,
    deleteAssessment,
    getAssessmentHistory,
    lookupInherentRisk,
    checkOpenValidationsForModel,
    downloadAssessmentPdf,
    RATING_SCORES,
    RATING_COLORS,
    TIER_MAP,
    TIER_LABELS,
};

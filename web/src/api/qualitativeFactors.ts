/**
 * API client for Qualitative Risk Factor Configuration endpoints.
 */
import client from './client';

// ============================================================================
// Types
// ============================================================================

export interface GuidanceCreate {
    rating: 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_HIGH' | 'VERY_LOW';
    points: number;
    description: string;
    sort_order?: number;
}

export interface GuidanceUpdate {
    rating?: 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_HIGH' | 'VERY_LOW';
    points?: number;
    description?: string;
    sort_order?: number;
}

export interface GuidanceResponse {
    guidance_id: number;
    factor_id: number;
    rating: string;
    points: number;
    description: string;
    sort_order: number;
}

export interface FactorCreate {
    code: string;
    name: string;
    description?: string;
    weight: number;
    sort_order?: number;
    guidance?: GuidanceCreate[];
}

export interface FactorUpdate {
    code?: string;
    name?: string;
    description?: string;
    weight?: number;
    sort_order?: number;
    is_active?: boolean;
}

export interface WeightUpdate {
    weight: number;
}

export interface FactorResponse {
    factor_id: number;
    code: string;
    name: string;
    description: string | null;
    weight: number;
    sort_order: number;
    is_active: boolean;
    guidance: GuidanceResponse[];
    created_at: string;
    updated_at: string;
}

export interface WeightValidationResponse {
    valid: boolean;
    total: number;
    message: string | null;
}

export interface ReorderRequest {
    factor_ids: number[];
}

// ============================================================================
// API Functions
// ============================================================================

const BASE_URL = '/risk-assessment/factors';

/**
 * List all qualitative risk factors.
 */
export async function listFactors(includeInactive = false): Promise<FactorResponse[]> {
    const response = await client.get(`${BASE_URL}/`, {
        params: { include_inactive: includeInactive }
    });
    return response.data;
}

/**
 * Get a specific factor.
 */
export async function getFactor(factorId: number): Promise<FactorResponse> {
    const response = await client.get(`${BASE_URL}/${factorId}`);
    return response.data;
}

/**
 * Create a new factor.
 */
export async function createFactor(data: FactorCreate): Promise<FactorResponse> {
    const response = await client.post(`${BASE_URL}/`, data);
    return response.data;
}

/**
 * Update a factor.
 */
export async function updateFactor(factorId: number, data: FactorUpdate): Promise<FactorResponse> {
    const response = await client.put(`${BASE_URL}/${factorId}`, data);
    return response.data;
}

/**
 * Update only the weight of a factor.
 */
export async function updateFactorWeight(factorId: number, weight: number): Promise<FactorResponse> {
    const response = await client.patch(`${BASE_URL}/${factorId}/weight`, { weight });
    return response.data;
}

/**
 * Soft-delete a factor (set is_active=false).
 */
export async function deleteFactor(factorId: number): Promise<FactorResponse> {
    const response = await client.delete(`${BASE_URL}/${factorId}`);
    return response.data;
}

/**
 * Validate that active factor weights sum to 1.0.
 */
export async function validateWeights(): Promise<WeightValidationResponse> {
    const response = await client.post(`${BASE_URL}/validate-weights`);
    return response.data;
}

/**
 * Reorder factors by providing new order of IDs.
 */
export async function reorderFactors(factorIds: number[]): Promise<FactorResponse[]> {
    const response = await client.post(`${BASE_URL}/reorder`, { factor_ids: factorIds });
    return response.data;
}

/**
 * Add guidance to a factor.
 */
export async function addGuidance(factorId: number, data: GuidanceCreate): Promise<GuidanceResponse> {
    const response = await client.post(`${BASE_URL}/${factorId}/guidance`, data);
    return response.data;
}

/**
 * Update guidance.
 */
export async function updateGuidance(guidanceId: number, data: GuidanceUpdate): Promise<GuidanceResponse> {
    const response = await client.put(`${BASE_URL}/guidance/${guidanceId}`, data);
    return response.data;
}

/**
 * Delete guidance.
 */
export async function deleteGuidance(guidanceId: number): Promise<void> {
    await client.delete(`${BASE_URL}/guidance/${guidanceId}`);
}

export default {
    listFactors,
    getFactor,
    createFactor,
    updateFactor,
    updateFactorWeight,
    deleteFactor,
    validateWeights,
    reorderFactors,
    addGuidance,
    updateGuidance,
    deleteGuidance,
};

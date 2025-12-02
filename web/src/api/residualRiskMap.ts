/**
 * Residual Risk Map API Client
 *
 * Provides functions to interact with the residual risk map configuration API.
 * The residual risk map defines how Inherent Risk Tier + Scorecard Outcome
 * combine to produce a Residual (Final) Risk rating.
 */

import client from './client';

// ============================================================================
// Types
// ============================================================================

export interface ResidualRiskMatrixConfig {
    row_axis_label: string;
    column_axis_label: string;
    row_values?: string[];
    column_values?: string[];
    result_values?: string[];
    matrix: Record<string, Record<string, string>>;
}

export interface ResidualRiskMapResponse {
    config_id: number;
    version_number: number;
    version_name: string | null;
    matrix_config: ResidualRiskMatrixConfig;
    description: string | null;
    is_active: boolean;
    created_by_user_id: number | null;
    created_at: string;
    updated_at: string;
}

export interface ResidualRiskMapUpdate {
    matrix_config?: ResidualRiskMatrixConfig;
    version_name?: string;
    description?: string;
}

export interface ResidualRiskCalculateRequest {
    inherent_risk_tier: string;
    scorecard_outcome: string;
}

export interface ResidualRiskCalculateResponse {
    inherent_risk_tier: string;
    scorecard_outcome: string;
    residual_risk: string | null;
    config_version: number;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get the active residual risk map configuration.
 */
export async function getActiveConfig(): Promise<ResidualRiskMapResponse> {
    const response = await client.get<ResidualRiskMapResponse>('/residual-risk-map/');
    return response.data;
}

/**
 * Get all residual risk map versions.
 */
export async function listVersions(): Promise<ResidualRiskMapResponse[]> {
    const response = await client.get<ResidualRiskMapResponse[]>('/residual-risk-map/versions');
    return response.data;
}

/**
 * Get a specific version by ID.
 */
export async function getVersion(versionId: number): Promise<ResidualRiskMapResponse> {
    const response = await client.get<ResidualRiskMapResponse>(`/residual-risk-map/versions/${versionId}`);
    return response.data;
}

/**
 * Update the residual risk map configuration.
 * This creates a new version and sets it as active.
 */
export async function updateConfig(data: ResidualRiskMapUpdate): Promise<ResidualRiskMapResponse> {
    const response = await client.patch<ResidualRiskMapResponse>('/residual-risk-map/', data);
    return response.data;
}

/**
 * Calculate residual risk for given inputs.
 */
export async function calculateResidualRisk(
    inherentRiskTier: string,
    scorecardOutcome: string
): Promise<ResidualRiskCalculateResponse> {
    const response = await client.post<ResidualRiskCalculateResponse>('/residual-risk-map/calculate', {
        inherent_risk_tier: inherentRiskTier,
        scorecard_outcome: scorecardOutcome,
    });
    return response.data;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get background color class for a residual risk value.
 */
export function getResidualRiskColorClass(risk: string | null | undefined): string {
    if (!risk) return 'bg-gray-100 text-gray-600';

    switch (risk.toLowerCase()) {
        case 'high':
            return 'bg-red-100 text-red-800 border-red-200';
        case 'medium':
            return 'bg-amber-100 text-amber-800 border-amber-200';
        case 'low':
            return 'bg-green-100 text-green-800 border-green-200';
        default:
            return 'bg-gray-100 text-gray-600';
    }
}

/**
 * Get badge class for inline display of residual risk.
 */
export function getResidualRiskBadgeClass(risk: string | null | undefined): string {
    if (!risk) return 'px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-600';

    const baseClass = 'px-2 py-1 text-xs font-medium rounded';
    switch (risk.toLowerCase()) {
        case 'high':
            return `${baseClass} bg-red-100 text-red-800`;
        case 'medium':
            return `${baseClass} bg-amber-100 text-amber-800`;
        case 'low':
            return `${baseClass} bg-green-100 text-green-800`;
        default:
            return `${baseClass} bg-gray-100 text-gray-600`;
    }
}

/**
 * Default row values (Inherent Risk Tiers) in display order.
 */
export const DEFAULT_ROW_VALUES = ['High', 'Medium', 'Low', 'Very Low'];

/**
 * Default column values (Scorecard Outcomes) in display order.
 */
export const DEFAULT_COLUMN_VALUES = ['Red', 'Yellow-', 'Yellow', 'Yellow+', 'Green-', 'Green'];

/**
 * Default result values (Residual Risk levels).
 */
export const DEFAULT_RESULT_VALUES = ['High', 'Medium', 'Low'];

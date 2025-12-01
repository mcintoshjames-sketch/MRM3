/**
 * API client for Validation Scorecard endpoints.
 */
import client from './client';

// ============================================================================
// Types
// ============================================================================

/**
 * Valid rating values for scorecard criteria.
 */
export type ScorecardRating = 'Green' | 'Green-' | 'Yellow+' | 'Yellow' | 'Yellow-' | 'Red' | 'N/A' | null;

/**
 * Rating options for dropdowns with display labels.
 */
export const RATING_OPTIONS: { value: ScorecardRating; label: string; color: string }[] = [
    { value: null, label: 'Select Rating...', color: 'gray' },
    { value: 'Green', label: 'Green (6)', color: 'green' },
    { value: 'Green-', label: 'Green- (5)', color: 'green' },
    { value: 'Yellow+', label: 'Yellow+ (4)', color: 'yellow' },
    { value: 'Yellow', label: 'Yellow (3)', color: 'yellow' },
    { value: 'Yellow-', label: 'Yellow- (2)', color: 'yellow' },
    { value: 'Red', label: 'Red (1)', color: 'red' },
    { value: 'N/A', label: 'N/A (0)', color: 'gray' },
];

/**
 * Scorecard criterion from configuration.
 */
export interface ScorecardCriterion {
    criterion_id: number;
    code: string;
    section_id: number;
    name: string;
    description_prompt: string | null;
    comments_prompt: string | null;
    include_in_summary: boolean;
    allow_zero: boolean;
    weight: number;
    sort_order: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

/**
 * Scorecard section with nested criteria.
 */
export interface ScorecardSection {
    section_id: number;
    code: string;
    name: string;
    description: string | null;
    sort_order: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    criteria: ScorecardCriterion[];
}

/**
 * Scorecard configuration response.
 */
export interface ScorecardConfigResponse {
    sections: ScorecardSection[];
}

/**
 * Input for a single criterion rating.
 */
export interface CriterionRatingInput {
    criterion_code: string;
    rating: ScorecardRating;
    description?: string | null;
    comments?: string | null;
}

/**
 * Input for updating a single criterion rating.
 */
export interface CriterionRatingUpdate {
    rating?: ScorecardRating;
    description?: string | null;
    comments?: string | null;
}

/**
 * Request body for creating/updating all ratings.
 */
export interface ScorecardRatingsCreate {
    ratings: CriterionRatingInput[];
}

/**
 * Criterion detail in scorecard response.
 */
export interface CriterionDetailResponse {
    criterion_code: string;
    criterion_name: string;
    section_code: string;
    rating: ScorecardRating;
    numeric_score: number;
    description: string | null;
    comments: string | null;
}

/**
 * Section summary in scorecard response.
 */
export interface SectionSummaryResponse {
    section_code: string;
    section_name: string;
    criteria_count: number;
    rated_count: number;
    unrated_count: number;
    numeric_score: number;
    rating: string | null;
}

/**
 * Overall assessment in scorecard response.
 */
export interface OverallAssessmentResponse {
    numeric_score: number;
    rating: string | null;
    sections_count: number;
    rated_sections_count: number;
}

/**
 * Full scorecard response with all details.
 */
export interface ScorecardFullResponse {
    request_id: number;
    criteria_details: CriterionDetailResponse[];
    section_summaries: SectionSummaryResponse[];
    overall_assessment: OverallAssessmentResponse;
    computed_at: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Convert a rating to its display color class.
 */
export function getRatingColorClass(rating: string | null): string {
    if (!rating) return 'bg-gray-100 text-gray-600';

    switch (rating) {
        case 'Green':
        case 'Green-':
            return 'bg-green-100 text-green-800';
        case 'Yellow+':
        case 'Yellow':
        case 'Yellow-':
            return 'bg-yellow-100 text-yellow-800';
        case 'Red':
            return 'bg-red-100 text-red-800';
        case 'N/A':
            return 'bg-gray-100 text-gray-600';
        default:
            return 'bg-gray-100 text-gray-600';
    }
}

/**
 * Convert a numeric score to its display color class.
 */
export function getScoreColorClass(score: number): string {
    if (score >= 5) return 'text-green-600';
    if (score >= 3) return 'text-yellow-600';
    if (score >= 1) return 'text-red-600';
    return 'text-gray-400';
}

// ============================================================================
// API Functions
// ============================================================================

const BASE_URL = '/scorecard';

/**
 * Get the scorecard configuration (sections and criteria).
 */
export async function getScorecardConfig(): Promise<ScorecardConfigResponse> {
    const response = await client.get(`${BASE_URL}/config`);
    return response.data;
}

/**
 * Get the scorecard for a validation request.
 */
export async function getScorecard(requestId: number): Promise<ScorecardFullResponse> {
    const response = await client.get(`${BASE_URL}/validation/${requestId}`);
    return response.data;
}

/**
 * Create or update all scorecard ratings for a validation request.
 */
export async function saveScorecard(
    requestId: number,
    ratings: CriterionRatingInput[]
): Promise<ScorecardFullResponse> {
    const response = await client.post(`${BASE_URL}/validation/${requestId}`, {
        ratings
    });
    return response.data;
}

/**
 * Update a single criterion rating.
 */
export async function updateSingleRating(
    requestId: number,
    criterionCode: string,
    data: CriterionRatingUpdate
): Promise<ScorecardFullResponse> {
    const response = await client.patch(
        `${BASE_URL}/validation/${requestId}/ratings/${criterionCode}`,
        data
    );
    return response.data;
}

export default {
    getScorecardConfig,
    getScorecard,
    saveScorecard,
    updateSingleRating,
    getRatingColorClass,
    getScoreColorClass,
    RATING_OPTIONS,
};

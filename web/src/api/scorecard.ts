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
    overall_assessment_narrative: string | null;
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

/**
 * Update the overall assessment narrative.
 */
export async function updateOverallNarrative(
    requestId: number,
    narrative: string | null
): Promise<ScorecardFullResponse> {
    const response = await client.patch(
        `${BASE_URL}/validation/${requestId}/overall-narrative`,
        { overall_assessment_narrative: narrative }
    );
    return response.data;
}

/**
 * Export the validation scorecard as a PDF.
 * Returns a Blob that can be downloaded by the browser.
 */
export async function exportScorecardPDF(requestId: number): Promise<Blob> {
    const response = await client.get(
        `${BASE_URL}/validation/${requestId}/export-pdf`,
        { responseType: 'blob' }
    );
    return response.data;
}

// ============================================================================
// Admin: Section CRUD Functions
// ============================================================================

/**
 * Input for creating a new section.
 */
export interface ScorecardSectionCreate {
    code: string;
    name: string;
    description?: string | null;
    sort_order?: number;
    is_active?: boolean;
}

/**
 * Input for updating a section.
 */
export interface ScorecardSectionUpdate {
    name?: string;
    description?: string | null;
    sort_order?: number;
    is_active?: boolean;
}

/**
 * List all scorecard sections.
 */
export async function listSections(includeInactive = false): Promise<ScorecardSection[]> {
    const response = await client.get(`${BASE_URL}/sections`, {
        params: { include_inactive: includeInactive }
    });
    return response.data;
}

/**
 * Get a single section with its criteria.
 */
export async function getSection(sectionId: number): Promise<ScorecardSection> {
    const response = await client.get(`${BASE_URL}/sections/${sectionId}`);
    return response.data;
}

/**
 * Create a new section.
 */
export async function createSection(data: ScorecardSectionCreate): Promise<ScorecardSection> {
    const response = await client.post(`${BASE_URL}/sections`, data);
    return response.data;
}

/**
 * Update a section.
 */
export async function updateSection(sectionId: number, data: ScorecardSectionUpdate): Promise<ScorecardSection> {
    const response = await client.patch(`${BASE_URL}/sections/${sectionId}`, data);
    return response.data;
}

/**
 * Delete a section.
 */
export async function deleteSection(sectionId: number): Promise<void> {
    await client.delete(`${BASE_URL}/sections/${sectionId}`);
}

// ============================================================================
// Admin: Criterion CRUD Functions
// ============================================================================

/**
 * Input for creating a new criterion.
 */
export interface ScorecardCriterionCreate {
    code: string;
    section_id: number;
    name: string;
    description_prompt?: string | null;
    comments_prompt?: string | null;
    include_in_summary?: boolean;
    allow_zero?: boolean;
    weight?: number;
    sort_order?: number;
    is_active?: boolean;
}

/**
 * Input for updating a criterion.
 */
export interface ScorecardCriterionUpdate {
    name?: string;
    description_prompt?: string | null;
    comments_prompt?: string | null;
    include_in_summary?: boolean;
    allow_zero?: boolean;
    weight?: number;
    sort_order?: number;
    is_active?: boolean;
}

/**
 * List all scorecard criteria.
 */
export async function listCriteria(sectionId?: number, includeInactive = false): Promise<ScorecardCriterion[]> {
    const response = await client.get(`${BASE_URL}/criteria`, {
        params: {
            section_id: sectionId,
            include_inactive: includeInactive
        }
    });
    return response.data;
}

/**
 * Get a single criterion.
 */
export async function getCriterion(criterionId: number): Promise<ScorecardCriterion> {
    const response = await client.get(`${BASE_URL}/criteria/${criterionId}`);
    return response.data;
}

/**
 * Create a new criterion.
 */
export async function createCriterion(data: ScorecardCriterionCreate): Promise<ScorecardCriterion> {
    const response = await client.post(`${BASE_URL}/criteria`, data);
    return response.data;
}

/**
 * Update a criterion.
 */
export async function updateCriterion(criterionId: number, data: ScorecardCriterionUpdate): Promise<ScorecardCriterion> {
    const response = await client.patch(`${BASE_URL}/criteria/${criterionId}`, data);
    return response.data;
}

/**
 * Delete a criterion.
 */
export async function deleteCriterion(criterionId: number): Promise<void> {
    await client.delete(`${BASE_URL}/criteria/${criterionId}`);
}

// ============================================================================
// Configuration Versioning Types
// ============================================================================

/**
 * Section snapshot in a config version.
 */
export interface ScorecardSectionSnapshot {
    snapshot_id: number;
    code: string;
    name: string;
    description: string | null;
    sort_order: number;
    is_active: boolean;
}

/**
 * Criterion snapshot in a config version.
 */
export interface ScorecardCriterionSnapshot {
    snapshot_id: number;
    section_code: string;
    code: string;
    name: string;
    description_prompt: string | null;
    comments_prompt: string | null;
    include_in_summary: boolean;
    allow_zero: boolean;
    weight: number;
    sort_order: number;
    is_active: boolean;
}

/**
 * Scorecard configuration version summary.
 */
export interface ScorecardConfigVersion {
    version_id: number;
    version_number: number;
    version_name: string | null;
    description: string | null;
    published_by_name: string | null;
    published_at: string;
    is_active: boolean;
    sections_count: number;
    criteria_count: number;
    scorecards_count: number;
    created_at: string;
    has_unpublished_changes: boolean;
}

/**
 * Scorecard configuration version with full snapshots.
 */
export interface ScorecardConfigVersionDetail extends ScorecardConfigVersion {
    section_snapshots: ScorecardSectionSnapshot[];
    criterion_snapshots: ScorecardCriterionSnapshot[];
}

/**
 * Input for publishing a new version.
 */
export interface PublishScorecardVersionRequest {
    version_name?: string | null;
    description?: string | null;
}

// ============================================================================
// Configuration Versioning API Functions
// ============================================================================

/**
 * List all scorecard configuration versions.
 */
export async function listConfigVersions(): Promise<ScorecardConfigVersion[]> {
    const response = await client.get(`${BASE_URL}/versions`);
    return response.data;
}

/**
 * Get the currently active scorecard configuration version with full details.
 */
export async function getActiveConfigVersion(): Promise<ScorecardConfigVersionDetail | null> {
    const response = await client.get(`${BASE_URL}/versions/active`);
    return response.data;
}

/**
 * Get a specific scorecard configuration version with full details.
 */
export async function getConfigVersion(versionId: number): Promise<ScorecardConfigVersionDetail> {
    const response = await client.get(`${BASE_URL}/versions/${versionId}`);
    return response.data;
}

/**
 * Publish a new scorecard configuration version. Admin only.
 */
export async function publishConfigVersion(data: PublishScorecardVersionRequest): Promise<ScorecardConfigVersion> {
    const response = await client.post(`${BASE_URL}/versions/publish`, data);
    return response.data;
}

export default {
    getScorecardConfig,
    getScorecard,
    saveScorecard,
    updateSingleRating,
    updateOverallNarrative,
    exportScorecardPDF,
    getRatingColorClass,
    getScoreColorClass,
    RATING_OPTIONS,
    // Admin functions
    listSections,
    getSection,
    createSection,
    updateSection,
    deleteSection,
    listCriteria,
    getCriterion,
    createCriterion,
    updateCriterion,
    deleteCriterion,
    // Config versioning
    listConfigVersions,
    getActiveConfigVersion,
    getConfigVersion,
    publishConfigVersion,
};

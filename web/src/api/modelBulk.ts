/**
 * API functions for bulk model operations.
 */
import client from './client';

export interface BulkUpdateFieldsRequest {
    model_ids: number[];

    // People pickers (single-select)
    owner_id?: number | null;
    developer_id?: number | null;
    shared_owner_id?: number | null;
    shared_developer_id?: number | null;
    monitoring_manager_id?: number | null;

    // Text field
    products_covered?: string | null;

    // Multi-select with mode
    user_ids?: number[];
    user_ids_mode?: 'add' | 'replace';

    regulatory_category_ids?: number[];
    regulatory_category_ids_mode?: 'add' | 'replace';
}

export interface BulkUpdateResultItem {
    model_id: number;
    model_name: string | null;
    success: boolean;
    error: string | null;
}

export interface BulkUpdateFieldsResponse {
    total_requested: number;
    total_modified: number;
    total_skipped: number;
    total_failed: number;
    results: BulkUpdateResultItem[];
}

/**
 * Bulk update fields on multiple models.
 *
 * @param request - The bulk update request containing model IDs and field values
 * @returns Response with counts and per-model results
 */
export async function bulkUpdateFields(
    request: BulkUpdateFieldsRequest
): Promise<BulkUpdateFieldsResponse> {
    const response = await client.post<BulkUpdateFieldsResponse>(
        '/models/bulk-update-fields',
        request
    );
    return response.data;
}

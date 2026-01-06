/**
 * API client for Model Overlays endpoints.
 */
import client from './client';

export type OverlayKind = 'OVERLAY' | 'MANAGEMENT_JUDGEMENT';

export interface RegionSummary {
    region_id: number;
    code: string;
    name: string;
}

export interface ModelOverlayListItem {
    overlay_id: number;
    model_id: number;
    overlay_kind: OverlayKind;
    is_underperformance_related: boolean;
    description: string;
    rationale: string;
    effective_from: string;
    effective_to?: string | null;
    region_id?: number | null;
    region?: RegionSummary | null;
    trigger_monitoring_result_id?: number | null;
    trigger_monitoring_cycle_id?: number | null;
    related_recommendation_id?: number | null;
    related_limitation_id?: number | null;
    evidence_description?: string | null;
    is_retired: boolean;
    created_at: string;
}

export interface ModelOverlayDetail extends ModelOverlayListItem {
    retirement_date?: string | null;
    retirement_reason?: string | null;
    retired_by?: {
        user_id: number;
        full_name: string;
        email: string;
    } | null;
    created_by: {
        user_id: number;
        full_name: string;
        email: string;
    };
    updated_at: string;
}

export interface ModelOverlayCreate {
    overlay_kind: OverlayKind;
    is_underperformance_related: boolean;
    description: string;
    rationale: string;
    effective_from: string;
    effective_to?: string | null;
    region_id?: number | null;
    trigger_monitoring_result_id?: number | null;
    trigger_monitoring_cycle_id?: number | null;
    related_recommendation_id?: number | null;
    related_limitation_id?: number | null;
    evidence_description?: string | null;
}

export interface ModelOverlayUpdate {
    evidence_description?: string | null;
    trigger_monitoring_result_id?: number | null;
    trigger_monitoring_cycle_id?: number | null;
    related_recommendation_id?: number | null;
    related_limitation_id?: number | null;
}

export interface ModelOverlayRetire {
    retirement_reason: string;
}

export interface ModelOverlayReportItem {
    overlay_id: number;
    model_id: number;
    model_name: string;
    model_status: string;
    risk_tier?: string | null;
    risk_tier_code?: string | null;
    team_name?: string | null;
    overlay_kind: OverlayKind;
    is_underperformance_related: boolean;
    description: string;
    rationale: string;
    effective_from: string;
    effective_to?: string | null;
    region_name?: string | null;
    region_code?: string | null;
    evidence_description?: string | null;
    trigger_monitoring_result_id?: number | null;
    trigger_monitoring_cycle_id?: number | null;
    related_recommendation_id?: number | null;
    related_limitation_id?: number | null;
    has_monitoring_traceability: boolean;
    created_at: string;
}

export interface ModelOverlaysReportResponse {
    filters_applied: Record<string, unknown>;
    total_count: number;
    items: ModelOverlayReportItem[];
}

export async function listModelOverlays(
    modelId: number,
    params?: {
        include_retired?: boolean;
        overlay_kind?: OverlayKind;
        region_id?: number;
        is_underperformance_related?: boolean;
    }
): Promise<ModelOverlayListItem[]> {
    const response = await client.get(`/models/${modelId}/overlays`, { params });
    return response.data;
}

export async function getModelOverlay(overlayId: number): Promise<ModelOverlayDetail> {
    const response = await client.get(`/overlays/${overlayId}`);
    return response.data;
}

export async function createModelOverlay(
    modelId: number,
    data: ModelOverlayCreate
): Promise<ModelOverlayDetail> {
    const response = await client.post(`/models/${modelId}/overlays`, data);
    return response.data;
}

export async function updateModelOverlay(
    overlayId: number,
    data: ModelOverlayUpdate
): Promise<ModelOverlayDetail> {
    const response = await client.patch(`/overlays/${overlayId}`, data);
    return response.data;
}

export async function retireModelOverlay(
    overlayId: number,
    data: ModelOverlayRetire
): Promise<ModelOverlayDetail> {
    const response = await client.post(`/overlays/${overlayId}/retire`, data);
    return response.data;
}

export async function getModelOverlaysReport(params?: {
    region_id?: number;
    team_id?: number;
    risk_tier?: string;
    overlay_kind?: OverlayKind;
    include_pending_decommission?: boolean;
}): Promise<ModelOverlaysReportResponse> {
    const response = await client.get('/reports/model-overlays', { params });
    return response.data;
}

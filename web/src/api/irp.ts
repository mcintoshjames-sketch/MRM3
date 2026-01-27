import api from './client';

// ==================== INTERFACES ====================

export interface UserSummary {
    user_id: number;
    email: string;
    full_name: string;
}

export interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
    description?: string;
    is_active?: boolean;
}

// MRSA Summary (lightweight model info for IRP views)
export interface MRSASummary {
    model_id: number;
    model_name: string;
    description?: string;
    mrsa_risk_level_id?: number;
    mrsa_risk_level_label?: string;
    mrsa_risk_rationale?: string;
    is_mrsa: boolean;
    owner_id: number;
    owner_name?: string;
}

// IRP Review
export interface IRPReview {
    review_id: number;
    irp_id: number;
    review_date: string;
    outcome_id: number;
    outcome?: TaxonomyValue;
    notes?: string;
    reviewed_by_user_id: number;
    reviewed_by?: UserSummary;
    created_at: string;
}

export interface IRPReviewCreate {
    review_date: string;
    outcome_id: number;
    notes?: string;
    reviewed_by_user_id?: number;  // Defaults to IRP contact if not provided
}

// IRP Certification
export interface IRPCertification {
    certification_id: number;
    irp_id: number;
    certification_date: string;
    certified_by_user_id: number;
    certified_by_user?: UserSummary;
    certified_by_email: string;
    conclusion_summary: string;
    created_at: string;
}

export interface IRPCertificationCreate {
    certification_date: string;
    certified_by_email: string;
    conclusion_summary: string;
}

// IRP (list view)
export interface IRP {
    irp_id: number;
    process_name: string;
    description?: string;
    is_active: boolean;
    contact_user_id: number;
    contact_user?: UserSummary;
    created_at: string;
    updated_at: string;
    covered_mrsa_count: number;
    latest_review_date?: string;
    latest_review_outcome?: string;
    latest_certification_date?: string;
}

// IRP Detail (with relationships)
export interface IRPDetail {
    irp_id: number;
    process_name: string;
    description?: string;
    is_active: boolean;
    contact_user_id: number;
    contact_user?: UserSummary;
    created_at: string;
    updated_at: string;
    // Covered MRSAs
    covered_mrsas: MRSASummary[];
    covered_mrsa_count: number;
    // Review history
    reviews: IRPReview[];
    latest_review?: IRPReview;
    // Certification history
    certifications: IRPCertification[];
    latest_certification?: IRPCertification;
}

export interface IRPCreate {
    process_name: string;
    description?: string;
    is_active?: boolean;
    contact_user_id: number;
    mrsa_ids?: number[];
}

export interface IRPUpdate {
    process_name?: string;
    description?: string;
    contact_user_id?: number;
    is_active?: boolean;
    mrsa_ids?: number[];
}

// IRP Coverage Check
export interface IRPCoverageStatus {
    model_id: number;
    model_name: string;
    is_mrsa: boolean;
    mrsa_risk_level_id?: number;
    mrsa_risk_level_label?: string;
    requires_irp: boolean;
    has_irp_coverage: boolean;
    is_compliant: boolean;
    irp_ids: number[];
    irp_names: string[];
}

// ==================== API CLIENT ====================

export const irpApi = {
    // ==================== IRP CRUD ====================

    // List IRPs with optional filter
    list: async (params?: { is_active?: boolean }): Promise<IRP[]> => {
        const response = await api.get('/irps/', { params });
        return response.data;
    },

    // Get IRP detail with relationships
    get: async (irpId: number): Promise<IRPDetail> => {
        const response = await api.get(`/irps/${irpId}`);
        return response.data;
    },

    // Create IRP (Admin only)
    create: async (data: IRPCreate): Promise<IRP> => {
        const response = await api.post('/irps/', data);
        return response.data;
    },

    // Update IRP (Admin only)
    update: async (irpId: number, data: IRPUpdate): Promise<IRP> => {
        const response = await api.patch(`/irps/${irpId}`, data);
        return response.data;
    },

    // Delete IRP (Admin only)
    delete: async (irpId: number): Promise<void> => {
        await api.delete(`/irps/${irpId}`);
    },

    // ==================== IRP REVIEWS ====================

    // List reviews for an IRP
    listReviews: async (irpId: number): Promise<IRPReview[]> => {
        const response = await api.get(`/irps/${irpId}/reviews`);
        return response.data;
    },

    // Create a review for an IRP
    createReview: async (irpId: number, data: IRPReviewCreate): Promise<IRPReview> => {
        const response = await api.post(`/irps/${irpId}/reviews`, data);
        return response.data;
    },

    // ==================== IRP CERTIFICATIONS ====================

    // List certifications for an IRP
    listCertifications: async (irpId: number): Promise<IRPCertification[]> => {
        const response = await api.get(`/irps/${irpId}/certifications`);
        return response.data;
    },

    // Create a certification for an IRP (Admin only)
    createCertification: async (irpId: number, data: IRPCertificationCreate): Promise<IRPCertification> => {
        const response = await api.post(`/irps/${irpId}/certifications`, data);
        return response.data;
    },

    // ==================== COVERAGE CHECK ====================

    // Check IRP coverage for MRSAs
    checkCoverage: async (params?: {
        mrsa_ids?: number[];
        require_irp_only?: boolean;
    }): Promise<IRPCoverageStatus[]> => {
        const searchParams: Record<string, string> = {};
        if (params?.mrsa_ids) {
            searchParams.mrsa_ids = params.mrsa_ids.join(',');
        }
        if (params?.require_irp_only !== undefined) {
            searchParams.require_irp_only = String(params.require_irp_only);
        }
        const response = await api.get('/irps/coverage/check', { params: searchParams });
        return response.data;
    },

    // Get coverage for a specific MRSA
    getMRSACoverage: async (mrsaId: number): Promise<IRPCoverageStatus | undefined> => {
        const response = await api.get('/irps/coverage/check', {
            params: { mrsa_ids: String(mrsaId) }
        });
        return response.data[0];
    },
};

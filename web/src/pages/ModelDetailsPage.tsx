import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';
import ModelRegionsSection from '../components/ModelRegionsSection';
import SubmitChangeModal from '../components/SubmitChangeModal';
import VersionsList from '../components/VersionsList';
import VersionDetailModal from '../components/VersionDetailModal';
import DelegatesSection from '../components/DelegatesSection';
import RegionalVersionsTable from '../components/RegionalVersionsTable';
import ModelHierarchySection from '../components/ModelHierarchySection';
import ModelDependenciesSection from '../components/ModelDependenciesSection';
import ModelApplicationsSection from '../components/ModelApplicationsSection';
import LineageViewer from '../components/LineageViewer';
import ModelRiskAssessmentTab from '../components/ModelRiskAssessmentTab';
import ModelMonitoringTab from '../components/ModelMonitoringTab';
import ModelLimitationsTab from '../components/ModelLimitationsTab';
import ModelExceptionsTab from '../components/ModelExceptionsTab';
import OverdueCommentaryModal, { OverdueType } from '../components/OverdueCommentaryModal';
import { useAuth } from '../contexts/AuthContext';
import {
    canApproveModel,
    canManageIrps,
    canManageModels,
    canManageRecommendations
} from '../utils/roleUtils';
import { ModelVersion } from '../api/versions';
import { overdueCommentaryApi, CurrentOverdueCommentaryResponse } from '../api/overdueCommentary';
import { getResidualRiskBadgeClass } from '../api/residualRiskMap';
import { linkChangeToAttestationIfPresent } from '../api/attestation';
import { irpApi, IRP, IRPCoverageStatus } from '../api/irp';

interface User {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
}

interface Vendor {
    vendor_id: number;
    name: string;
    contact_info: string;
}

interface ModelType {
    type_id: number;
    category_id: number;
    name: string;
    description: string | null;
    sort_order: number;
    is_active: boolean;
}

interface ModelTypeCategory {
    category_id: number;
    name: string;
    description: string | null;
    sort_order: number;
    model_types: ModelType[];
}

interface Methodology {
    methodology_id: number;
    category_id: number;
    name: string;
    description: string | null;
    variants: string | null;
    sort_order: number;
    is_active: boolean;
}

interface MethodologyCategory {
    category_id: number;
    code: string;
    name: string;
    sort_order: number;
    methodologies: Methodology[];
}

interface TaxonomyValue {
    value_id: number;
    taxonomy_id: number;
    code: string;
    label: string;
    description: string | null;
    sort_order: number;
    is_active: boolean;
    requires_irp?: boolean;
}

interface Taxonomy {
    taxonomy_id: number;
    name: string;
    description: string | null;
    is_system: boolean;
    values: TaxonomyValue[];
}

interface Region {
    region_id: number;
    code: string;
    name: string;
    requires_regional_approval: boolean;
}

interface SubmissionComment {
    comment_id: number;
    model_id: number;
    user_id: number;
    comment_text: string;
    action_taken: string | null;
    created_at: string;
    user: User;
}

interface Model {
    model_id: number;
    model_name: string;
    description: string;
    products_covered: string | null;
    development_type: string;
    owner_id: number;
    developer_id: number | null;
    shared_owner_id: number | null;
    shared_developer_id: number | null;
    monitoring_manager_id: number | null;
    vendor_id: number | null;
    risk_tier_id: number | null;
    validation_type_id: number | null;
    model_type_id: number | null;
    methodology_id: number | null;
    usage_frequency_id: number | null;
    wholly_owned_region_id: number | null;
    status: string;
    status_id: number | null;
    created_at: string;
    updated_at: string;
    row_approval_status: string | null;
    submitted_by_user_id: number | null;
    submitted_at: string | null;
    is_model: boolean;
    is_aiml: boolean | null;
    is_mrsa: boolean | null;
    mrsa_risk_level_id: number | null;
    mrsa_risk_rationale: string | null;
    mrsa_risk_level: TaxonomyValue | null;
    business_line_name: string | null;
    team?: {
        team_id: number;
        name: string;
    } | null;
    // Computed approval status fields
    approval_status: string | null;
    approval_status_label: string | null;
    // Computed exception count for UI badge
    open_exception_count: number;
    owner: User;
    developer: User | null;
    shared_owner: User | null;
    shared_developer: User | null;
    monitoring_manager: User | null;
    vendor: Vendor | null;
    risk_tier: TaxonomyValue | null;
    validation_type: TaxonomyValue | null;
    model_type: ModelType | null;
    methodology: Methodology | null;
    usage_frequency: TaxonomyValue | null;
    status_value: TaxonomyValue | null;
    wholly_owned_region: Region | null;
    users: User[];
    regulatory_categories: TaxonomyValue[];
    submitted_by_user: User | null;
    submission_comments: SubmissionComment[];
}

interface UserWithLOBRollup {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
    lob_id: number;
    lob_name: string | null;
    lob_rollup_name: string | null;
}

interface ModelRolesWithLOB {
    owner: UserWithLOBRollup;
    shared_owner: UserWithLOBRollup | null;
    developer: UserWithLOBRollup | null;
    shared_developer: UserWithLOBRollup | null;
    monitoring_manager: UserWithLOBRollup | null;
}

interface ValidationRequest {
    request_id: number;
    model_id: number;
    model_name: string;
    request_date: string;
    requestor_name: string;
    validation_type: string;
    priority: string;
    target_completion_date: string;
    current_status: string;
    days_in_status: number;
    primary_validator: string | null;
    created_at: string;
    completion_date: string | null;
    scorecard_overall_rating: string | null;
    residual_risk: string | null;
    validated_risk_tier: string | null;
}

interface DecommissioningRequestListItem {
    request_id: number;
    model_id: number;
    model_name: string;
    status: string;
    reason: string;
    last_production_date: string;
    created_at: string;
    created_by_name: string;
}

interface ValidationSummary {
    request_id: number;
    approval_date: string;
    validation_type: string;
}

interface RevalidationStatus {
    model_id: number;
    model_name: string;
    model_owner: string;
    risk_tier: string | null;
    status: string;
    last_validation_date: string | null;
    next_submission_due: string | null;
    grace_period_end: string | null;
    next_validation_due: string | null;
    days_until_submission_due: number | null;
    days_until_validation_due: number | null;
    active_request_id: number | null;
    submission_received: string | null;
    submission_status: string | null;
    model_compliance_status: string | null;
    validation_team_sla_status: string | null;
    validation_team_sla_due_date: string | null;
    interim_expiration: string | null;
    most_recent_validation: ValidationSummary | null;
    previous_validation: ValidationSummary | null;
}

interface ActivityTimelineItem {
    timestamp: string;
    activity_type: string;
    title: string;
    description: string | null;
    user_name: string | null;
    user_id: number | null;
    entity_type: string | null;
    entity_id: number | null;
    icon: string;
}

interface NameHistoryItem {
    history_id: number;
    model_id: number;
    old_name: string;
    new_name: string;
    changed_by_id: number | null;
    changed_by_name: string | null;
    changed_at: string;
    change_reason: string | null;
}

interface PendingEdit {
    pending_edit_id: number;
    model_id: number;
    requested_by: { user_id: number; full_name: string; email: string };
    requested_at: string;
    proposed_changes: Record<string, unknown>;
    original_values: Record<string, unknown>;
    status: string;
    reviewed_by: { user_id: number; full_name: string; email: string } | null;
    reviewed_at: string | null;
    review_comment: string | null;
}

interface FinalRiskRanking {
    original_scorecard: string;
    days_overdue: number;
    past_due_level: string;
    past_due_level_code: string;
    downgrade_notches: number;
    adjusted_scorecard: string;
    inherent_risk_tier: string;
    inherent_risk_tier_label: string | null;
    final_rating: string | null;
    residual_risk_without_penalty: string | null;
}

interface RecommendationListItem {
    recommendation_id: number;
    recommendation_code: string;
    title: string;
    priority: { code: string; label: string } | null;
    current_status: { code: string; label: string } | null;
    assigned_to: { full_name: string } | null;
    current_target_date: string;
    created_at: string;
}

export default function ModelDetailsPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const { user } = useAuth();
    const canApproveModelFlag = canApproveModel(user);
    const canManageIrpsFlag = canManageIrps(user);
    const canManageModelsFlag = canManageModels(user);
    const canManageRecommendationsFlag = canManageRecommendations(user);
    const [model, setModel] = useState<Model | null>(null);
    const [users, setUsers] = useState<User[]>([]);
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [taxonomies, setTaxonomies] = useState<Taxonomy[]>([]);
    const [modelTypes, setModelTypes] = useState<ModelTypeCategory[]>([]);
    const [methodologyCategories, setMethodologyCategories] = useState<MethodologyCategory[]>([]);
    const [validationRequests, setValidationRequests] = useState<ValidationRequest[]>([]);
    const [versions, setVersions] = useState<ModelVersion[]>([]);
    const [revalidationStatus, setRevalidationStatus] = useState<RevalidationStatus | null>(null);
    const [rolesWithLOB, setRolesWithLOB] = useState<ModelRolesWithLOB | null>(null);
    const [decommissioningRequests, setDecommissioningRequests] = useState<DecommissioningRequestListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(false);
    const [activeTab, setActiveTab] = useState<'details' | 'versions' | 'validations' | 'relationships' | 'activity' | 'recommendations' | 'limitations' | 'monitoring' | 'decommissioning' | 'risk-assessment' | 'exceptions'>('details');
    const [relationshipSubTab, setRelationshipSubTab] = useState<'hierarchy' | 'dependencies' | 'applications' | 'lineage'>('hierarchy');
    const [showDelegates, setShowDelegates] = useState(false);
    const [showSubmitChangeModal, setShowSubmitChangeModal] = useState(false);
    const [selectedVersion, setSelectedVersion] = useState<ModelVersion | null>(null);
    const [versionsRefreshTrigger, setVersionsRefreshTrigger] = useState(0);
    const [userSearchTerm, setUserSearchTerm] = useState('');
    const [showUserDropdown, setShowUserDropdown] = useState(false);
    const [showCancelledValidations, setShowCancelledValidations] = useState(false);
    const [showApprovalActions, setShowApprovalActions] = useState(false);
    const [showResubmitForm, setShowResubmitForm] = useState(false);
    const [approvalComment, setApprovalComment] = useState('');
    const [sendBackComment, setSendBackComment] = useState('');
    const [resubmitComment, setResubmitComment] = useState('');
    const [submittingApproval, setSubmittingApproval] = useState(false);
    const [activities, setActivities] = useState<ActivityTimelineItem[]>([]);
    const [activitiesLoading, setActivitiesLoading] = useState(false);
    const [editError, setEditError] = useState<string | null>(null);
    const [pendingEditSuccess, setPendingEditSuccess] = useState<string | null>(null);
    const [overdueCommentary, setOverdueCommentary] = useState<CurrentOverdueCommentaryResponse | null>(null);
    const [showCommentaryModal, setShowCommentaryModal] = useState(false);
    const [commentaryModalType, setCommentaryModalType] = useState<OverdueType>('PRE_SUBMISSION');
    const [nameHistory, setNameHistory] = useState<NameHistoryItem[]>([]);
    const [showNameHistory, setShowNameHistory] = useState(false);
    const [pendingEdits, setPendingEdits] = useState<PendingEdit[]>([]);
    const [selectedPendingEditId, setSelectedPendingEditId] = useState<number | null>(null);
    const [showPendingEditReview, setShowPendingEditReview] = useState(false);
    const [pendingEditComment, setPendingEditComment] = useState('');
    const [submittingPendingEdit, setSubmittingPendingEdit] = useState(false);
    const [recommendations, setRecommendations] = useState<RecommendationListItem[]>([]);
    const [recommendationsLoading, setRecommendationsLoading] = useState(false);
    // IRP state for MRSAs
    const [allIrps, setAllIrps] = useState<IRP[]>([]);
    const [irpCoverage, setIrpCoverage] = useState<IRPCoverageStatus | null>(null);
    const [showIrpLinkModal, setShowIrpLinkModal] = useState(false);
    const [selectedIrpId, setSelectedIrpId] = useState<number | null>(null);
    const [linkingIrp, setLinkingIrp] = useState(false);
    const [irpSearchTerm, setIrpSearchTerm] = useState('');
    const [finalRiskRanking, setFinalRiskRanking] = useState<FinalRiskRanking | null>(null);
    // Track whether the model has a global risk assessment (disables direct risk tier editing)
    const [hasGlobalAssessment, setHasGlobalAssessment] = useState(false);
    // Store original form values to compute diff when saving
    const [originalFormData, setOriginalFormData] = useState<typeof formData | null>(null);
    const [formData, setFormData] = useState({
        model_name: '',
        description: '',
        products_covered: '',
        development_type: 'In-House',
        owner_id: 0,
        developer_id: null as number | null,
        shared_owner_id: null as number | null,
        shared_developer_id: null as number | null,
        monitoring_manager_id: null as number | null,
        vendor_id: null as number | null,
        risk_tier_id: null as number | null,
        model_type_id: null as number | null,
        methodology_id: null as number | null,
        usage_frequency_id: null as number | null,
        wholly_owned_region_id: null as number | null,
        status: 'In Development',
        status_id: null as number | null,
        user_ids: [] as number[],
        regulatory_category_ids: [] as number[],
        is_model: true,
        is_mrsa: false,
        mrsa_risk_level_id: null as number | null,
        mrsa_risk_rationale: ''
    });
    const [mrsaRiskLevels, setMrsaRiskLevels] = useState<TaxonomyValue[]>([]);

    useEffect(() => {
        fetchData();
    }, [id]);

    // Handle ?edit=true query param to auto-open edit mode
    useEffect(() => {
        if (searchParams.get('edit') === 'true' && model) {
            setEditing(true);
            // Clear the query param so it doesn't persist on refresh
            setSearchParams({}, { replace: true });
        }
    }, [searchParams, setSearchParams, model]);

    // Poll activities when Activity tab is active
    useEffect(() => {
        if (activeTab === 'activity') {
            fetchActivities();
            const interval = setInterval(fetchActivities, 30000); // Poll every 30 seconds
            return () => clearInterval(interval);
        }
        if (activeTab === 'recommendations') {
            fetchRecommendations();
        }
    }, [activeTab, id]);

    // Fetch overdue commentary when there's an active overdue validation request
    useEffect(() => {
        const fetchOverdueCommentary = async () => {
            if (revalidationStatus?.active_request_id &&
                (revalidationStatus.status.includes('Overdue') ||
                 (revalidationStatus.days_until_validation_due !== null && revalidationStatus.days_until_validation_due < 0) ||
                 (revalidationStatus.days_until_submission_due !== null && revalidationStatus.days_until_submission_due < 0))) {
                try {
                    const response = await overdueCommentaryApi.getForRequest(revalidationStatus.active_request_id);
                    setOverdueCommentary(response);
                } catch (error) {
                    console.error('Failed to fetch overdue commentary:', error);
                }
            }
        };
        fetchOverdueCommentary();
    }, [revalidationStatus]);

    // Fetch pending edits and check URL parameter
    useEffect(() => {
        const fetchPendingEdits = async () => {
            if (!id || !user) return;
            try {
                const response = await api.get(`/models/${id}/pending-edits`);
                setPendingEdits(response.data);

                // Check if URL has reviewEdit parameter
                const reviewEditId = searchParams.get('reviewEdit');
                if (reviewEditId && canApproveModelFlag) {
                    const editId = parseInt(reviewEditId, 10);
                    const editExists = response.data.some((e: PendingEdit) => e.pending_edit_id === editId);
                    if (editExists) {
                        setSelectedPendingEditId(editId);
                        setShowPendingEditReview(true);
                    }
                    // Clear the URL parameter
                    setSearchParams({});
                }
            } catch (error) {
                console.error('Failed to fetch pending edits:', error);
            }
        };
        fetchPendingEdits();
    }, [id, user, searchParams, setSearchParams]);

    const handleOpenCommentaryModal = (type: OverdueType) => {
        setCommentaryModalType(type);
        setShowCommentaryModal(true);
    };

    const handleCommentarySuccess = async () => {
        // Refresh commentary data
        if (revalidationStatus?.active_request_id) {
            try {
                const response = await overdueCommentaryApi.getForRequest(revalidationStatus.active_request_id);
                setOverdueCommentary(response);
            } catch (error) {
                console.error('Failed to refresh commentary:', error);
            }
        }
    };

    const fetchData = async () => {
        try {
            // Fetch critical model data first - these are required
            const [modelRes, usersRes, vendorsRes, regionsRes, taxonomiesRes, modelTypesRes, methodologyCategoriesRes] = await Promise.all([
                api.get(`/models/${id}`),
                api.get('/auth/users'),
                api.get('/vendors/'),
                api.get('/regions/'),
                api.get('/taxonomies/'),
                api.get('/model-types/categories'),
                api.get('/methodology-library/categories')
            ]);
            const modelData = modelRes.data;
            setModel(modelData);
            setUsers(usersRes.data);
            setVendors(vendorsRes.data);
            setRegions(regionsRes.data);
            setModelTypes(modelTypesRes.data);
            setMethodologyCategories(methodologyCategoriesRes.data);

            // Fetch full taxonomy details for dropdowns
            const taxDetails = await Promise.all(
                taxonomiesRes.data.map((t: Taxonomy) => api.get(`/taxonomies/${t.taxonomy_id}`))
            );
            const allTaxonomies = taxDetails.map((r) => r.data);
            setTaxonomies(allTaxonomies);

            // Extract MRSA Risk Level taxonomy values
            const mrsaTax = allTaxonomies.find((t: Taxonomy) => t.name === 'MRSA Risk Level');
            if (mrsaTax) {
                setMrsaRiskLevels(mrsaTax.values.filter((v: TaxonomyValue) => v.is_active));
            }

            const initialFormData = {
                model_name: modelData.model_name,
                description: modelData.description || '',
                products_covered: modelData.products_covered || '',
                development_type: modelData.development_type,
                owner_id: modelData.owner_id,
                developer_id: modelData.developer_id,
                shared_owner_id: modelData.shared_owner_id,
                shared_developer_id: modelData.shared_developer_id,
                monitoring_manager_id: modelData.monitoring_manager_id,
                vendor_id: modelData.vendor_id,
                risk_tier_id: modelData.risk_tier_id,
                model_type_id: modelData.model_type_id,
                methodology_id: modelData.methodology_id,
                usage_frequency_id: modelData.usage_frequency_id,
                wholly_owned_region_id: modelData.wholly_owned_region_id,
                status: modelData.status,
                status_id: modelData.status_id,
                user_ids: modelData.users.map((u: User) => u.user_id),
                regulatory_category_ids: modelData.regulatory_categories.map((c: TaxonomyValue) => c.value_id),
                is_model: modelData.is_model ?? true,
                is_mrsa: modelData.is_mrsa ?? false,
                mrsa_risk_level_id: modelData.mrsa_risk_level_id,
                mrsa_risk_rationale: modelData.mrsa_risk_rationale || ''
            };
            setFormData(initialFormData);
            setOriginalFormData(initialFormData);

            // Fetch validation requests and versions separately - this is optional and shouldn't break the page
            try {
                const [validationRequestsRes, versionsRes, revalidationRes, decommissioningRes, nameHistoryRes, rolesWithLOBRes] = await Promise.all([
                    api.get(`/validation-workflow/requests/?model_id=${id}`),
                    api.get(`/models/${id}/versions`),
                    api.get(`/models/${id}/revalidation-status`),
                    api.get(`/decommissioning/?model_id=${id}`),
                    api.get(`/models/${id}/name-history`),
                    api.get(`/models/${id}/roles-with-lob`)
                ]);
                setValidationRequests(validationRequestsRes.data);
                setVersions(versionsRes.data);
                setRevalidationStatus(revalidationRes.data);
                setDecommissioningRequests(decommissioningRes.data);
                setNameHistory(nameHistoryRes.data.history || []);
                setRolesWithLOB(rolesWithLOBRes.data);
            } catch (validationError) {
                console.error('Failed to fetch validation data:', validationError);
                // Keep as empty arrays - don't break the page
                setValidationRequests([]);
                setVersions([]);
                setRevalidationStatus(null);
                setDecommissioningRequests([]);
                setNameHistory([]);
                setRolesWithLOB(null);
            }

            // Fetch final risk ranking (optional - may not exist for models without approved validations)
            try {
                const finalRankingRes = await api.get(`/models/${id}/final-risk-ranking`);
                setFinalRiskRanking(finalRankingRes.data);
            } catch (rankingError: any) {
                // 404 is expected when model has no approved validation with scorecard
                if (rankingError.response?.status !== 404) {
                    console.error('Failed to fetch final risk ranking:', rankingError);
                }
                setFinalRiskRanking(null);
            }

            // Check if model has a global risk assessment (disables direct risk tier editing)
            try {
                const assessmentStatusRes = await api.get(`/models/${id}/risk-assessments/status`);
                setHasGlobalAssessment(assessmentStatusRes.data.has_assessment);
            } catch (assessmentError) {
                console.error('Failed to fetch assessment status:', assessmentError);
                setHasGlobalAssessment(false);
            }
        } catch (error) {
            console.error('Failed to fetch model:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchActivities = async () => {
        if (!id) return;
        setActivitiesLoading(true);
        try {
            const response = await api.get(`/models/${id}/activity-timeline`);
            setActivities(response.data.activities);
        } catch (error) {
            console.error('Failed to fetch activities:', error);
        } finally {
            setActivitiesLoading(false);
        }
    };

    const fetchRecommendations = async () => {
        if (!id) return;
        setRecommendationsLoading(true);
        try {
            const response = await api.get(`/recommendations/`, { params: { model_id: parseInt(id) } });
            setRecommendations(response.data);
        } catch (error) {
            console.error('Failed to fetch recommendations:', error);
        } finally {
            setRecommendationsLoading(false);
        }
    };

    // Fetch IRP data when model is an MRSA
    const fetchIrpData = async () => {
        if (!model?.is_mrsa) return;
        try {
            // Fetch all active IRPs for linking
            const irps = await irpApi.list({ is_active: true });
            setAllIrps(irps);
            // Fetch coverage status for this MRSA
            const coverage = await irpApi.getMRSACoverage(model.model_id);
            setIrpCoverage(coverage || null);
        } catch (error) {
            console.error('Failed to fetch IRP data:', error);
        }
    };

    // Fetch IRP data when model loads and is an MRSA
    useEffect(() => {
        if (model?.is_mrsa) {
            fetchIrpData();
        }
    }, [model?.model_id, model?.is_mrsa]);

    // Handle linking MRSA to an IRP
    const handleLinkIrp = async () => {
        if (!selectedIrpId || !model) return;
        setLinkingIrp(true);
        try {
            // Get the current IRP details to get its current MRSA list
            const irpDetail = await irpApi.get(selectedIrpId);
            const currentMrsaIds = irpDetail.covered_mrsas.map(m => m.model_id);
            // Add this MRSA to the list
            if (!currentMrsaIds.includes(model.model_id)) {
                await irpApi.update(selectedIrpId, {
                    mrsa_ids: [...currentMrsaIds, model.model_id]
                });
            }
            // Refresh IRP data
            await fetchIrpData();
            setShowIrpLinkModal(false);
            setSelectedIrpId(null);
            setIrpSearchTerm('');
        } catch (error) {
            console.error('Failed to link IRP:', error);
            alert('Failed to link IRP. Please try again.');
        } finally {
            setLinkingIrp(false);
        }
    };

    // Handle unlinking MRSA from an IRP
    const handleUnlinkIrp = async (irpId: number) => {
        if (!model) return;
        if (!confirm('Are you sure you want to remove this MRSA from this IRP?')) return;
        try {
            // Get the current IRP details
            const irpDetail = await irpApi.get(irpId);
            const currentMrsaIds = irpDetail.covered_mrsas.map(m => m.model_id);
            // Remove this MRSA from the list
            const newMrsaIds = currentMrsaIds.filter(id => id !== model.model_id);
            await irpApi.update(irpId, { mrsa_ids: newMrsaIds });
            // Refresh IRP data
            await fetchIrpData();
        } catch (error) {
            console.error('Failed to unlink IRP:', error);
            alert('Failed to unlink IRP. Please try again.');
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setEditError(null);
        setPendingEditSuccess(null);
        try {
            if (originalFormData?.description?.trim() && !formData.description.trim()) {
                setEditError('Description cannot be cleared once set.');
                return;
            }
            if (originalFormData?.developer_id && !formData.developer_id) {
                setEditError('Developer cannot be cleared once set.');
                return;
            }
            if (originalFormData?.usage_frequency_id && !formData.usage_frequency_id) {
                setEditError('Usage frequency cannot be cleared once set.');
                return;
            }

            // Compute only the fields that actually changed (for proper pending edit tracking)
            const payload: Record<string, unknown> = {};

            // Helper to check if arrays are equal
            const arraysEqual = (a: number[], b: number[]) => {
                if (a.length !== b.length) return false;
                const sortedA = [...a].sort();
                const sortedB = [...b].sort();
                return sortedA.every((val, idx) => val === sortedB[idx]);
            };

            if (originalFormData) {
                // Only include fields that have actually changed
                if (formData.model_name !== originalFormData.model_name) {
                    payload.model_name = formData.model_name;
                }
                if (formData.description !== originalFormData.description) {
                    payload.description = formData.description;
                }
                if (formData.products_covered !== originalFormData.products_covered) {
                    payload.products_covered = formData.products_covered;
                }
                if (formData.development_type !== originalFormData.development_type) {
                    payload.development_type = formData.development_type;
                }
                if (formData.owner_id !== originalFormData.owner_id) {
                    payload.owner_id = formData.owner_id;
                }
                if (formData.developer_id !== originalFormData.developer_id) {
                    payload.developer_id = formData.developer_id || null;
                }
                if (formData.shared_owner_id !== originalFormData.shared_owner_id) {
                    payload.shared_owner_id = formData.shared_owner_id || null;
                }
                if (formData.shared_developer_id !== originalFormData.shared_developer_id) {
                    payload.shared_developer_id = formData.shared_developer_id || null;
                }
                if (formData.monitoring_manager_id !== originalFormData.monitoring_manager_id) {
                    payload.monitoring_manager_id = formData.monitoring_manager_id || null;
                }
                if (formData.vendor_id !== originalFormData.vendor_id) {
                    payload.vendor_id = formData.vendor_id || null;
                }
                if (formData.risk_tier_id !== originalFormData.risk_tier_id) {
                    payload.risk_tier_id = formData.risk_tier_id || null;
                }
                if (formData.model_type_id !== originalFormData.model_type_id) {
                    payload.model_type_id = formData.model_type_id || null;
                }
                if (formData.methodology_id !== originalFormData.methodology_id) {
                    payload.methodology_id = formData.methodology_id || null;
                }
                if (formData.usage_frequency_id !== originalFormData.usage_frequency_id) {
                    payload.usage_frequency_id = formData.usage_frequency_id;
                }
                if (formData.status_id !== originalFormData.status_id) {
                    payload.status_id = formData.status_id;
                }
                if (formData.wholly_owned_region_id !== originalFormData.wholly_owned_region_id) {
                    payload.wholly_owned_region_id = formData.wholly_owned_region_id || null;
                }
                if (!arraysEqual(formData.user_ids, originalFormData.user_ids)) {
                    payload.user_ids = formData.user_ids.length > 0 ? formData.user_ids : [];
                }
                if (!arraysEqual(formData.regulatory_category_ids, originalFormData.regulatory_category_ids)) {
                    payload.regulatory_category_ids = formData.regulatory_category_ids.length > 0 ? formData.regulatory_category_ids : [];
                }
                if (formData.is_model !== originalFormData.is_model) {
                    payload.is_model = formData.is_model;
                }
                if (formData.is_mrsa !== originalFormData.is_mrsa) {
                    payload.is_mrsa = formData.is_mrsa;
                }
                if (formData.mrsa_risk_level_id !== originalFormData.mrsa_risk_level_id) {
                    payload.mrsa_risk_level_id = formData.mrsa_risk_level_id || null;
                }
                if (formData.mrsa_risk_rationale !== originalFormData.mrsa_risk_rationale) {
                    payload.mrsa_risk_rationale = formData.mrsa_risk_rationale || null;
                }
            } else {
                // Fallback: send all fields if original data not available (shouldn't happen)
                const { status, ...formDataWithoutStatus } = formData;
                Object.assign(payload, formDataWithoutStatus, {
                    developer_id: formData.developer_id || null,
                    vendor_id: formData.vendor_id || null,
                    risk_tier_id: formData.risk_tier_id || null,
                    model_type_id: formData.model_type_id || null,
                    methodology_id: formData.methodology_id || null,
                    wholly_owned_region_id: formData.wholly_owned_region_id || null,
                    user_ids: formData.user_ids.length > 0 ? formData.user_ids : [],
                    regulatory_category_ids: formData.regulatory_category_ids.length > 0 ? formData.regulatory_category_ids : []
                });
            }

            // Validate MRSA fields if is_mrsa is true
            if (formData.is_mrsa && !formData.is_model) {
                if (!formData.mrsa_risk_level_id) {
                    setEditError('MRSA Risk Level is required when marking as MRSA.');
                    return;
                }
                if (!formData.mrsa_risk_rationale?.trim()) {
                    setEditError('MRSA Risk Rationale is required when marking as MRSA.');
                    return;
                }
            }

            // Check if there are any changes
            if (Object.keys(payload).length === 0) {
                setEditError('No changes to save.');
                return;
            }

            const response = await api.patch(`/models/${id}`, payload);
            setEditing(false);
            setEditError(null);

            // Check if changes were submitted for approval (202 Accepted)
            if (response.status === 202) {
                setPendingEditSuccess('Your changes have been submitted for admin approval. You will be notified when they are reviewed.');
                // Refresh pending edits list
                const pendingResponse = await api.get(`/models/${id}/pending-edits`);
                setPendingEdits(pendingResponse.data);

                // Link to attestation if navigated from attestation page
                const pendingEditId = response.data?.pending_edit_id;
                await linkChangeToAttestationIfPresent('MODEL_EDIT', {
                    model_id: Number(id),
                    pending_edit_id: pendingEditId,
                });
            } else {
                // Direct edit (admin) - still link to attestation if present
                await linkChangeToAttestationIfPresent('MODEL_EDIT', {
                    model_id: Number(id),
                });
            }

            fetchData();
        } catch (error: any) {
            const errorMessage = error.response?.status === 403
                ? 'You do not have permission to edit this model. Only the model owner or administrators can make changes.'
                : error.response?.data?.detail || 'Failed to update model. Please try again.';
            setEditError(errorMessage);
            console.error('Failed to update model:', error);
        }
    };

    const getRiskTierTaxonomy = () => taxonomies.find(t => t.name === 'Model Risk Tier');
    const getUsageFrequencyTaxonomy = () => taxonomies.find(t => t.name === 'Model Usage Frequency');
    const getRegulatoryCategoryTaxonomy = () => taxonomies.find(t => t.name === 'Regulatory Category');
    const getModelStatusTaxonomy = () => taxonomies.find(t => t.name === 'Model Status');

    // Check for out-of-order validation conditions
    const getOutOfOrderWarnings = () => {
        const warnings: string[] = [];
        const activeStatuses = ['Intake', 'Planning', 'In Progress', 'Review', 'Pending Approval'];

        // Find active validation projects
        const activeRequests = validationRequests.filter(req =>
            activeStatuses.includes(req.current_status) && req.target_completion_date
        );

        // Find versions with production dates
        const implementedVersions = versions.filter(v => v.production_date);

        // Check each active project against implemented versions
        activeRequests.forEach(request => {
            implementedVersions.forEach(version => {
                const targetDate = new Date(request.target_completion_date);
                const implDate = new Date(version.production_date!);

                if (implDate < targetDate) {
                    warnings.push(
                        `Active validation project (${request.validation_type}, target: ${request.target_completion_date.split('T')[0]}) has a target completion date after version ${version.version_number} implementation date (${version.production_date!.split('T')[0]}). Consider expediting validation or using Interim Review.`
                    );
                }
            });
        });

        return warnings;
    };

    const toggleRegulatoryCategory = (valueId: number) => {
        setFormData(prev => {
            const ids = prev.regulatory_category_ids;
            if (ids.includes(valueId)) {
                return { ...prev, regulatory_category_ids: ids.filter(id => id !== valueId) };
            } else {
                return { ...prev, regulatory_category_ids: [...ids, valueId] };
            }
        });
    };

    const addUserToModel = (userId: number) => {
        if (!formData.user_ids.includes(userId)) {
            setFormData(prev => ({
                ...prev,
                user_ids: [...prev.user_ids, userId]
            }));
        }
        setUserSearchTerm('');
        setShowUserDropdown(false);
    };

    const removeUserFromModel = (userId: number) => {
        setFormData(prev => ({
            ...prev,
            user_ids: prev.user_ids.filter(id => id !== userId)
        }));
    };

    const filteredUsersForSearch = users.filter(u =>
        !formData.user_ids.includes(u.user_id) &&
        (u.full_name.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
            u.email.toLowerCase().includes(userSearchTerm.toLowerCase()))
    );

    const selectedUsers = users.filter(u => formData.user_ids.includes(u.user_id));

    const handleDelete = async () => {
        if (!confirm('Are you sure you want to delete this model?')) return;
        try {
            await api.delete(`/models/${id}`);
            navigate('/models');
        } catch (error) {
            console.error('Failed to delete model:', error);
        }
    };

    const handleApprove = async () => {
        if (!model) return;
        setSubmittingApproval(true);
        try {
            await api.post(`/models/${model.model_id}/approve`, {
                comment: approvalComment || 'Record approved for inventory.'
            });
            // Refresh the model data
            await fetchData();
            setShowApprovalActions(false);
            setApprovalComment('');
        } catch (error: any) {
            console.error('Failed to approve record:', error);
            alert(error.response?.data?.detail || 'Failed to approve record');
        } finally {
            setSubmittingApproval(false);
        }
    };

    const handleSendBack = async () => {
        if (!model || !sendBackComment.trim()) {
            alert('Please provide feedback for the submitter.');
            return;
        }
        setSubmittingApproval(true);
        try {
            await api.post(`/models/${model.model_id}/send-back`, {
                comment: sendBackComment
            });
            // Refresh the model data
            await fetchData();
            setShowApprovalActions(false);
            setSendBackComment('');
        } catch (error: any) {
            console.error('Failed to send back record:', error);
            alert(error.response?.data?.detail || 'Failed to send back record');
        } finally {
            setSubmittingApproval(false);
        }
    };

    const handleResubmit = async () => {
        if (!model) return;
        setSubmittingApproval(true);
        try {
            await api.post(`/models/${model.model_id}/resubmit`, {
                comment: resubmitComment || 'Resubmitted for review.'
            });
            // Refresh the model data
            await fetchData();
            setShowResubmitForm(false);
            setResubmitComment('');
        } catch (error: any) {
            console.error('Failed to resubmit record:', error);
            alert(error.response?.data?.detail || 'Failed to resubmit record');
        } finally {
            setSubmittingApproval(false);
        }
    };

    const handleApprovePendingEdit = async (editId: number) => {
        if (!model) return;
        setSubmittingPendingEdit(true);
        try {
            await api.post(`/models/${model.model_id}/pending-edits/${editId}/approve`, {
                comment: pendingEditComment || 'Changes approved.'
            });
            // Refresh the data
            await fetchData();
            // Refresh pending edits
            const response = await api.get(`/models/${id}/pending-edits`);
            setPendingEdits(response.data);
            setShowPendingEditReview(false);
            setSelectedPendingEditId(null);
            setPendingEditComment('');
        } catch (error: any) {
            console.error('Failed to approve pending edit:', error);
            alert(error.response?.data?.detail || 'Failed to approve pending edit');
        } finally {
            setSubmittingPendingEdit(false);
        }
    };

    const handleRejectPendingEdit = async (editId: number) => {
        if (!model || !pendingEditComment.trim()) {
            alert('Please provide a reason for rejection.');
            return;
        }
        setSubmittingPendingEdit(true);
        try {
            await api.post(`/models/${model.model_id}/pending-edits/${editId}/reject`, {
                comment: pendingEditComment
            });
            // Refresh pending edits
            const response = await api.get(`/models/${id}/pending-edits`);
            setPendingEdits(response.data);
            setShowPendingEditReview(false);
            setSelectedPendingEditId(null);
            setPendingEditComment('');
        } catch (error: any) {
            console.error('Failed to reject pending edit:', error);
            alert(error.response?.data?.detail || 'Failed to reject pending edit');
        } finally {
            setSubmittingPendingEdit(false);
        }
    };

    const formatFieldName = (field: string): string => {
        return field
            .replace(/_ids$/, ' IDs')
            .replace(/_id$/, '')
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase())
            .replace(/\bIds\b/g, 'IDs'); // Ensure "IDs" is capitalized correctly
    };

    // Resolve lookup IDs to human-readable labels for pending edit review
    const resolveLookupValue = (field: string, value: unknown): string => {
        if (value == null) return '';

        // Handle array fields (regulatory_category_ids, user_ids)
        if (Array.isArray(value)) {
            if (value.length === 0) return '';

            switch (field) {
                case 'regulatory_category_ids': {
                    const regCatTax = taxonomies.find(t => t.name === 'Regulatory Category');
                    if (!regCatTax) return value.join(', ');
                    const labels = value.map(id => {
                        const catValue = regCatTax.values.find(v => v.value_id === id);
                        return catValue ? catValue.label : String(id);
                    });
                    return labels.join(', ');
                }
                case 'user_ids': {
                    const names = value.map(id => {
                        const user = users.find(u => u.user_id === id);
                        return user ? user.full_name : String(id);
                    });
                    return names.join(', ');
                }
                default:
                    return value.join(', ');
            }
        }

        const numValue = typeof value === 'number' ? value : parseInt(String(value), 10);
        if (isNaN(numValue)) return String(value);

        switch (field) {
            case 'owner_id':
            case 'developer_id': {
                const user = users.find(u => u.user_id === numValue);
                return user ? user.full_name : String(value);
            }
            case 'vendor_id': {
                const vendor = vendors.find(v => v.vendor_id === numValue);
                return vendor ? vendor.name : String(value);
            }
            case 'risk_tier_id': {
                const riskTierTax = taxonomies.find(t => t.name === 'Model Risk Tier');
                const tierValue = riskTierTax?.values.find(v => v.value_id === numValue);
                return tierValue ? tierValue.label : String(value);
            }
            case 'validation_type_id': {
                const valTypeTax = taxonomies.find(t => t.name === 'Validation Type');
                const typeValue = valTypeTax?.values.find(v => v.value_id === numValue);
                return typeValue ? typeValue.label : String(value);
            }
            case 'status_id': {
                const statusTax = taxonomies.find(t => t.name === 'Model Status');
                const statusValue = statusTax?.values.find(v => v.value_id === numValue);
                return statusValue ? statusValue.label : String(value);
            }
            case 'usage_frequency_id': {
                const usageFreqTax = taxonomies.find(t => t.name === 'Model Usage Frequency');
                const usageFreqValue = usageFreqTax?.values.find(v => v.value_id === numValue);
                return usageFreqValue ? usageFreqValue.label : String(value);
            }
            case 'model_type_id': {
                for (const category of modelTypes) {
                    const modelType = category.model_types.find(t => t.type_id === numValue);
                    if (modelType) return modelType.name;
                }
                return String(value);
            }
            case 'wholly_owned_region_id': {
                const region = regions.find(r => r.region_id === numValue);
                return region ? region.name : String(value);
            }
            default:
                return String(value);
        }
    };

    // Check if two values are different (for showing "Changed" badge)
    const valuesAreDifferent = (oldValue: unknown, newValue: unknown): boolean => {
        // Handle null/undefined
        if (oldValue == null && newValue == null) return false;
        if (oldValue == null || newValue == null) return true;

        // Handle arrays
        if (Array.isArray(oldValue) && Array.isArray(newValue)) {
            if (oldValue.length !== newValue.length) return true;
            const sortedOld = [...oldValue].sort();
            const sortedNew = [...newValue].sort();
            return sortedOld.some((v, i) => v !== sortedNew[i]);
        }

        // Simple comparison
        return oldValue !== newValue;
    };

    const getActivityIcon = (activityType: string) => {
        const iconClass = "w-6 h-6";

        switch (activityType) {
            case 'model_created':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
                    </svg>
                );
            case 'model_updated':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                    </svg>
                );
            case 'model_submitted':
            case 'model_resubmitted':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
                    </svg>
                );
            case 'model_approved':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                );
            case 'model_rejected':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                );
            case 'version_created':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V8z" clipRule="evenodd" />
                    </svg>
                );
            case 'validation_request_created':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                    </svg>
                );
            case 'validation_status_change':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                    </svg>
                );
            case 'validation_approval':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                );
            case 'validation_rejection':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 000 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
                    </svg>
                );
            case 'delegate_added':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path d="M8 9a3 3 0 100-6 3 3 0 000 6zM8 11a6 6 0 016 6H2a6 6 0 016-6zM16 7a1 1 0 10-2 0v1h-1a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V7z" />
                    </svg>
                );
            case 'delegate_removed':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path d="M11 6a3 3 0 11-6 0 3 3 0 016 0zM14 17a6 6 0 00-12 0h12zM13 8a1 1 0 100 2h4a1 1 0 100-2h-4z" />
                    </svg>
                );
            case 'comment_added':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
                    </svg>
                );
            case 'deployment_confirmed':
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11 4a1 1 0 10-2 0v4a1 1 0 102 0V7zm-3 1a1 1 0 10-2 0v3a1 1 0 102 0V8zM8 9a1 1 0 00-2 0v2a1 1 0 102 0V9z" clipRule="evenodd" />
                    </svg>
                );
            default:
                return (
                    <svg className={iconClass} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                );
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    if (!model) {
        return (
            <Layout>
                <div className="text-center">
                    <h2 className="text-2xl font-bold mb-4">Model Not Found</h2>
                    <button onClick={() => navigate('/models')} className="btn-primary">
                        Back to Models
                    </button>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <button
                        onClick={() => navigate('/models')}
                        className="text-blue-600 hover:text-blue-800 text-sm mb-2"
                    >
                        &larr; Back to Models
                    </button>
                    <div className="flex items-center gap-3">
                        <h2 className="text-2xl font-bold">{model.model_name}</h2>
                        {model.wholly_owned_region && (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800 border border-indigo-300">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                                </svg>
                                {model.wholly_owned_region.code}-Owned
                            </span>
                        )}
                    </div>
                </div>
                <div className="flex gap-2">
                    {!editing && (
                        <>
                            <button onClick={() => setShowSubmitChangeModal(true)} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                                Submit Change
                            </button>
                            <button onClick={() => { setEditError(null); setEditing(true); }} className="btn-primary">
                                Edit Model
                            </button>
                            {canManageModelsFlag && (
                                <button onClick={handleDelete} className="btn-secondary text-red-600">
                                    Delete
                                </button>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Approval Status Banner */}
            {model.row_approval_status && (model.row_approval_status === 'Draft' || model.row_approval_status === 'needs_revision') && (
                <div className={`mb-6 p-4 rounded-lg border-l-4 ${model.row_approval_status === 'needs_revision'
                    ? 'bg-orange-50 border-orange-500'
                    : 'bg-blue-50 border-blue-500'
                    }`}>
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3 flex-1">
                            <svg className={`w-6 h-6 flex-shrink-0 mt-0.5 ${model.row_approval_status === 'needs_revision'
                                ? 'text-orange-600'
                                : 'text-blue-600'
                                }`} fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            <div className="flex-1">
                                <h3 className={`text-sm font-semibold mb-1 ${model.row_approval_status === 'needs_revision'
                                    ? 'text-orange-900'
                                    : 'text-blue-900'
                                    }`}>
                                    {model.row_approval_status === 'Draft' && 'New Model Record Awaiting Approval'}
                                    {model.row_approval_status === 'needs_revision' && 'Revisions Requested'}
                                </h3>
                                <p className={`text-sm ${model.row_approval_status === 'needs_revision'
                                    ? 'text-orange-800'
                                    : 'text-blue-800'
                                    }`}>
                                    {model.row_approval_status === 'Draft' && 'This record is awaiting admin approval to be added to the inventory.'}
                                    {model.row_approval_status === 'needs_revision' && 'This record has been sent back for revisions. Please review the feedback below and resubmit when ready.'}
                                </p>
                                {model.submitted_by_user && (
                                    <p className="text-xs text-gray-600 mt-1">
                                        Submitted by {model.submitted_by_user.full_name} on {model.submitted_at!.split('T')[0]}
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* Admin Actions */}
                        {canApproveModelFlag && model.row_approval_status === 'Draft' && (
                            <div className="flex gap-2 flex-shrink-0">
                                <button
                                    onClick={() => setShowApprovalActions(!showApprovalActions)}
                                    className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded transition-colors"
                                >
                                    Review & Approve
                                </button>
                            </div>
                        )}

                        {/* Submitter Resubmit Action */}
                        {model.row_approval_status === 'needs_revision' && model.submitted_by_user_id === user?.user_id && (
                            <div className="flex gap-2 flex-shrink-0">
                                <button
                                    onClick={() => setShowResubmitForm(!showResubmitForm)}
                                    className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 rounded transition-colors"
                                >
                                    {showResubmitForm ? 'Cancel' : 'Resubmit for Review'}
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Approval Actions Panel */}
                    {showApprovalActions && canApproveModelFlag && (
                        <div className="mt-4 pt-4 border-t border-blue-200 space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Approve Section */}
                                <div className="space-y-2">
                                    <label className="block text-sm font-medium text-gray-700">
                                        Approve Record
                                    </label>
                                    <textarea
                                        value={approvalComment}
                                        onChange={(e) => setApprovalComment(e.target.value)}
                                        placeholder="Optional: Add approval comment..."
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                                        rows={3}
                                    />
                                    <button
                                        onClick={handleApprove}
                                        disabled={submittingApproval}
                                        className="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
                                    >
                                        {submittingApproval ? 'Approving...' : 'Approve & Add to Inventory'}
                                    </button>
                                </div>

                                {/* Send Back Section */}
                                <div className="space-y-2">
                                    <label className="block text-sm font-medium text-gray-700">
                                        Send Back for Revisions
                                    </label>
                                    <textarea
                                        value={sendBackComment}
                                        onChange={(e) => setSendBackComment(e.target.value)}
                                        placeholder="Provide feedback for the submitter... (required)"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                                        rows={3}
                                    />
                                    <button
                                        onClick={handleSendBack}
                                        disabled={submittingApproval || !sendBackComment.trim()}
                                        className="w-full bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 disabled:opacity-50 text-sm font-medium"
                                    >
                                        {submittingApproval ? 'Sending...' : 'Send Back for Revisions'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Resubmit Form Panel */}
                    {showResubmitForm && model.row_approval_status === 'needs_revision' && model.submitted_by_user_id === user?.user_id && (
                        <div className="mt-4 pt-4 border-t border-orange-200 space-y-3">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Resubmit for Review
                                </label>
                                <p className="text-sm text-gray-600 mb-3">
                                    Describe the changes you made to address the feedback above. This will help the reviewer understand what was updated.
                                </p>
                                <textarea
                                    value={resubmitComment}
                                    onChange={(e) => setResubmitComment(e.target.value)}
                                    placeholder="Optional: Describe what you changed in response to the feedback..."
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                                    rows={4}
                                />
                            </div>
                            <div className="flex gap-2 justify-end">
                                <button
                                    onClick={() => {
                                        setShowResubmitForm(false);
                                        setResubmitComment('');
                                    }}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleResubmit}
                                    disabled={submittingApproval}
                                    className="px-4 py-2 text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 rounded disabled:opacity-50"
                                >
                                    {submittingApproval ? 'Resubmitting...' : 'Submit for Review'}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Submission Comments Thread */}
                    {model.submission_comments && model.submission_comments.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                            <h4 className="text-sm font-semibold text-gray-700 mb-3">Review History</h4>
                            <div className="space-y-3">
                                {model.submission_comments.map((comment) => (
                                    <div key={comment.comment_id} className="bg-white p-3 rounded border border-gray-200">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-sm font-medium text-gray-900">
                                                {comment.user.full_name}
                                            </span>
                                            {comment.action_taken && (
                                                <span className={`px-2 py-0.5 text-xs rounded ${comment.action_taken === 'approved' ? 'bg-green-100 text-green-700' :
                                                    comment.action_taken === 'sent_back' ? 'bg-orange-100 text-orange-700' :
                                                        comment.action_taken === 'resubmitted' ? 'bg-blue-100 text-blue-700' :
                                                            'bg-gray-100 text-gray-700'
                                                    }`}>
                                                    {comment.action_taken === 'sent_back' ? 'Sent Back' :
                                                        comment.action_taken === 'resubmitted' ? 'Resubmitted' :
                                                            comment.action_taken === 'approved' ? 'Approved' :
                                                                comment.action_taken}
                                                </span>
                                            )}
                                            <span className="text-xs text-gray-500 ml-auto">
                                                {new Date(comment.created_at).toLocaleString()}
                                            </span>
                                        </div>
                                        <p className="text-sm text-gray-700">{comment.comment_text}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Success Banner for Pending Edit Submission */}
            {pendingEditSuccess && (
                <div className="mb-6 p-4 rounded-lg border-l-4 bg-green-50 border-green-500">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3 flex-1">
                            <svg className="w-6 h-6 flex-shrink-0 mt-0.5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            <div className="flex-1">
                                <h3 className="text-sm font-semibold text-green-900 mb-1">
                                    Changes Submitted for Approval
                                </h3>
                                <p className="text-sm text-green-800">
                                    {pendingEditSuccess}
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={() => setPendingEditSuccess(null)}
                            className="text-green-600 hover:text-green-800"
                            aria-label="Dismiss"
                        >
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                        </button>
                    </div>
                </div>
            )}

            {/* Pending Edits Banner (Admin only) */}
            {canApproveModelFlag && pendingEdits.length > 0 && (
                <div className="mb-6 p-4 rounded-lg border-l-4 bg-amber-50 border-amber-500">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3 flex-1">
                            <svg className="w-6 h-6 flex-shrink-0 mt-0.5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                            </svg>
                            <div className="flex-1">
                                <h3 className="text-sm font-semibold text-amber-900 mb-1">
                                    Pending Model Changes ({pendingEdits.length})
                                </h3>
                                <p className="text-sm text-amber-800">
                                    There are proposed changes to this model awaiting your review.
                                </p>
                            </div>
                        </div>
                        {!showPendingEditReview && (
                            <button
                                onClick={() => {
                                    setSelectedPendingEditId(pendingEdits[0].pending_edit_id);
                                    setShowPendingEditReview(true);
                                }}
                                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 rounded transition-colors flex-shrink-0"
                            >
                                Review Changes
                            </button>
                        )}
                    </div>

                    {/* Pending Edit Review Panel */}
                    {showPendingEditReview && selectedPendingEditId && (
                        <div className="mt-4 pt-4 border-t border-amber-200">
                            {pendingEdits.filter(e => e.pending_edit_id === selectedPendingEditId).map(edit => (
                                <div key={edit.pending_edit_id} className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <div className="text-sm text-gray-600">
                                            Submitted by <span className="font-medium">{edit.requested_by.full_name}</span> on {edit.requested_at.split('T')[0]}
                                        </div>
                                        {pendingEdits.length > 1 && (
                                            <select
                                                value={selectedPendingEditId}
                                                onChange={(e) => setSelectedPendingEditId(parseInt(e.target.value, 10))}
                                                className="text-sm border border-gray-300 rounded px-2 py-1"
                                            >
                                                {pendingEdits.map(pe => (
                                                    <option key={pe.pending_edit_id} value={pe.pending_edit_id}>
                                                        Edit #{pe.pending_edit_id} - {pe.requested_at.split('T')[0]}
                                                    </option>
                                                ))}
                                            </select>
                                        )}
                                    </div>

                                    {/* Proposed Changes Table */}
                                    <div className="bg-white rounded border border-gray-200 overflow-hidden">
                                        <table className="min-w-full divide-y divide-gray-200">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Field</th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Current Value</th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Proposed Value</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-200">
                                                {Object.entries(edit.proposed_changes).map(([field, newValue]) => {
                                                    const isChanged = valuesAreDifferent(edit.original_values[field], newValue);
                                                    return (
                                                        <tr key={field} className={isChanged ? 'bg-amber-50/50' : ''}>
                                                            <td className="px-4 py-2 text-sm font-medium text-gray-900">
                                                                <div className="flex items-center gap-2">
                                                                    {formatFieldName(field)}
                                                                    {isChanged && (
                                                                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
                                                                            Changed
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            </td>
                                                            <td className="px-4 py-2 text-sm text-gray-500">
                                                                {edit.original_values[field] != null
                                                                    ? resolveLookupValue(field, edit.original_values[field])
                                                                    : <span className="text-gray-400 italic">empty</span>}
                                                            </td>
                                                            <td className="px-4 py-2 text-sm text-green-700 font-medium">
                                                                {newValue != null
                                                                    ? resolveLookupValue(field, newValue)
                                                                    : <span className="text-gray-400 italic">empty</span>}
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>

                                    {/* Review Actions */}
                                    <div className="space-y-3">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Review Comment
                                            </label>
                                            <textarea
                                                value={pendingEditComment}
                                                onChange={(e) => setPendingEditComment(e.target.value)}
                                                placeholder="Optional for approval, required for rejection..."
                                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                                                rows={3}
                                            />
                                        </div>
                                        <div className="flex items-center gap-3 justify-end">
                                            {!pendingEditComment.trim() && (
                                                <span className="text-sm text-amber-600">
                                                    Comment required to reject
                                                </span>
                                            )}
                                            <button
                                                onClick={() => {
                                                    setShowPendingEditReview(false);
                                                    setSelectedPendingEditId(null);
                                                    setPendingEditComment('');
                                                }}
                                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={() => handleRejectPendingEdit(edit.pending_edit_id)}
                                                disabled={submittingPendingEdit || !pendingEditComment.trim()}
                                                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded disabled:opacity-50"
                                            >
                                                {submittingPendingEdit ? 'Rejecting...' : 'Reject Changes'}
                                            </button>
                                            <button
                                                onClick={() => handleApprovePendingEdit(edit.pending_edit_id)}
                                                disabled={submittingPendingEdit}
                                                className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded disabled:opacity-50"
                                            >
                                                {submittingPendingEdit ? 'Approving...' : 'Approve & Apply Changes'}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Out-of-Order Validation Warning */}
            {getOutOfOrderWarnings().length > 0 && (
                <div className="mb-6 p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
                    <div className="flex items-start gap-3">
                        <svg className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        <div className="flex-1">
                            <h3 className="text-sm font-semibold text-yellow-900 mb-2">Validation Timing Warning</h3>
                            <div className="space-y-1">
                                {getOutOfOrderWarnings().map((warning, index) => (
                                    <p key={index} className="text-sm text-yellow-800">
                                        {warning}
                                    </p>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Tabs */}
            {!editing && (
                <div className="mb-6">
                    {/* Main tabs row */}
                    <div className="border-b border-gray-200">
                        <nav className="-mb-px flex space-x-8">
                            <button
                                onClick={() => setActiveTab('details')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'details'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Model Details
                            </button>
                            <button
                                onClick={() => setActiveTab('risk-assessment')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'risk-assessment'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Risk Assessment
                            </button>
                            <button
                                onClick={() => setActiveTab('versions')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'versions'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Versions
                            </button>
                            <button
                                onClick={() => setActiveTab('validations')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'validations'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Validations ({validationRequests.filter(req => req.current_status !== 'Approved' && req.current_status !== 'Cancelled').length} active)
                            </button>
                            <button
                                onClick={() => setActiveTab('relationships')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'relationships'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Relationships
                            </button>
                            <button
                                onClick={() => setActiveTab('activity')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'activity'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Activity
                            </button>
                            <button
                                onClick={() => setActiveTab('recommendations')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'recommendations'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Recommendations
                                {recommendations.filter(r => !['REC_CLOSED', 'REC_DROPPED'].includes(r.current_status?.code || '')).length > 0 && (
                                    <span className="ml-1 px-1.5 py-0.5 text-xs bg-orange-100 text-orange-800 rounded-full">
                                        {recommendations.filter(r => !['REC_CLOSED', 'REC_DROPPED'].includes(r.current_status?.code || '')).length}
                                    </span>
                                )}
                            </button>
                            <button
                                onClick={() => setActiveTab('limitations')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'limitations'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Limitations
                            </button>
                            <button
                                onClick={() => setActiveTab('monitoring')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'monitoring'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Monitoring
                            </button>
                            <button
                                onClick={() => setActiveTab('decommissioning')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'decommissioning'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Decommissioning
                                {decommissioningRequests.length > 0 && decommissioningRequests[0].status !== 'APPROVED' && decommissioningRequests[0].status !== 'REJECTED' && decommissioningRequests[0].status !== 'WITHDRAWN' && (
                                    <span className="ml-1 px-1.5 py-0.5 text-xs bg-orange-100 text-orange-800 rounded-full">
                                        {decommissioningRequests[0].status}
                                    </span>
                                )}
                            </button>
                            <button
                                onClick={() => setActiveTab('exceptions')}
                                className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'exceptions'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                Exceptions
                                {model.open_exception_count > 0 && (
                                    <span className="ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-800">
                                        {model.open_exception_count}
                                    </span>
                                )}
                            </button>
                        </nav>
                    </div>

                    {/* Relationships sub-tabs */}
                    {activeTab === 'relationships' && (
                        <div className="bg-gray-50 border-b border-gray-200">
                            <nav className="flex space-x-6 px-4">
                                <button
                                    onClick={() => setRelationshipSubTab('hierarchy')}
                                    className={`py-2 px-1 text-sm font-medium ${relationshipSubTab === 'hierarchy'
                                        ? 'text-blue-600 border-b-2 border-blue-500'
                                        : 'text-gray-500 hover:text-gray-700'
                                        }`}
                                >
                                    Hierarchy
                                </button>
                                <button
                                    onClick={() => setRelationshipSubTab('dependencies')}
                                    className={`py-2 px-1 text-sm font-medium ${relationshipSubTab === 'dependencies'
                                        ? 'text-blue-600 border-b-2 border-blue-500'
                                        : 'text-gray-500 hover:text-gray-700'
                                        }`}
                                >
                                    Dependencies
                                </button>
                                <button
                                    onClick={() => setRelationshipSubTab('applications')}
                                    className={`py-2 px-1 text-sm font-medium ${relationshipSubTab === 'applications'
                                        ? 'text-blue-600 border-b-2 border-blue-500'
                                        : 'text-gray-500 hover:text-gray-700'
                                        }`}
                                >
                                    Applications
                                </button>
                                <button
                                    onClick={() => setRelationshipSubTab('lineage')}
                                    className={`py-2 px-1 text-sm font-medium ${relationshipSubTab === 'lineage'
                                        ? 'text-blue-600 border-b-2 border-blue-500'
                                        : 'text-gray-500 hover:text-gray-700'
                                        }`}
                                >
                                    Lineage
                                </button>
                            </nav>
                        </div>
                    )}
                </div>
            )}

            {/* Revalidation Alert Banner */}
            {!editing && revalidationStatus && (
                <>
                    {/* Critical: Validation Actually Overdue (days_until_validation_due < 0) */}
                    {revalidationStatus.days_until_validation_due !== null && revalidationStatus.days_until_validation_due < 0 && (
                        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
                            <div className="flex items-start">
                                <svg className="h-5 w-5 text-red-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                <div className="flex-1">
                                    <h3 className="text-sm font-bold text-red-800">Revalidation Overdue</h3>
                                    <p className="text-sm text-red-700 mt-1">
                                        This model is <strong>{Math.abs(revalidationStatus.days_until_validation_due)} days overdue</strong> for revalidation.
                                        {revalidationStatus.next_validation_due && ` Validation was due on ${revalidationStatus.next_validation_due}.`}
                                        {revalidationStatus.active_request_id && (
                                            <Link to={`/validation-workflow/${revalidationStatus.active_request_id}`} className="ml-2 underline font-medium hover:text-red-900">
                                                View active project →
                                            </Link>
                                        )}
                                    </p>
                                    {/* Commentary Status - Only ask validator for explanation if submission was received.
                                        If submission hasn't been received, the delay is due to the owner/developer not submitting,
                                        so we only need their PRE_SUBMISSION commentary (shown in yellow banner below). */}
                                    {revalidationStatus.active_request_id && revalidationStatus.submission_received && overdueCommentary && (
                                        <div className="mt-3 pt-3 border-t border-red-200">
                                            {overdueCommentary.has_current_comment && overdueCommentary.current_comment ? (
                                                <div className="text-sm">
                                                    <p className="text-red-800">
                                                        <span className="font-medium">Current explanation:</span>{' '}
                                                        <span className="italic">"{overdueCommentary.current_comment.reason_comment}"</span>
                                                    </p>
                                                    <p className="text-red-700 text-xs mt-1">
                                                        Target: {overdueCommentary.current_comment.target_date.split('T')[0]} •
                                                        By: {overdueCommentary.current_comment.created_by_user.full_name}
                                                        {overdueCommentary.is_stale && (
                                                            <span className="ml-2 text-red-900 font-medium">
                                                                ⚠ Update required: {overdueCommentary.stale_reason}
                                                            </span>
                                                        )}
                                                    </p>
                                                </div>
                                            ) : (
                                                <p className="text-sm text-red-800 font-medium">
                                                    ⚠ No explanation provided for this delay
                                                </p>
                                            )}
                                            <button
                                                onClick={() => handleOpenCommentaryModal('VALIDATION_IN_PROGRESS')}
                                                className="mt-2 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                                            >
                                                {overdueCommentary.has_current_comment ? 'Update Explanation' : 'Provide Explanation'}
                                            </button>
                                        </div>
                                    )}
                                    {/* If submission hasn't been received, show message directing to submission overdue explanation */}
                                    {revalidationStatus.active_request_id && !revalidationStatus.submission_received && (
                                        <div className="mt-3 pt-3 border-t border-red-200">
                                            <p className="text-sm text-red-800">
                                                <span className="font-medium">Cause:</span> Model documentation has not been submitted for validation.
                                                The model owner/developer must submit documentation before validation work can begin.
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Warning: Due soon (within 60 days but not overdue) */}
                    {!revalidationStatus.status.includes('Overdue') && revalidationStatus.days_until_validation_due !== null && revalidationStatus.days_until_validation_due >= 0 && revalidationStatus.days_until_validation_due < 60 && (
                        <div className="bg-orange-50 border-l-4 border-orange-500 p-4 mb-6">
                            <div className="flex items-start">
                                <svg className="h-5 w-5 text-orange-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                                <div className="flex-1">
                                    <h3 className="text-sm font-bold text-orange-800">Revalidation Due Soon</h3>
                                    <p className="text-sm text-orange-700 mt-1">
                                        This model is due for revalidation in <strong>{revalidationStatus.days_until_validation_due} days</strong>
                                        {revalidationStatus.next_validation_due && ` (${revalidationStatus.next_validation_due})`}.
                                        {revalidationStatus.days_until_submission_due !== null && revalidationStatus.days_until_submission_due > 0 && (
                                            <> Documentation submission due in {revalidationStatus.days_until_submission_due} days.</>
                                        )}
                                        {revalidationStatus.active_request_id && (
                                            <Link to={`/validation-workflow/${revalidationStatus.active_request_id}`} className="ml-2 underline font-medium hover:text-orange-900">
                                                View active project →
                                            </Link>
                                        )}
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Info: Submission overdue or in grace period
                        Show this banner when:
                        1. Submission is overdue but validation isn't yet overdue (normal case), OR
                        2. Validation IS overdue but submission hasn't been received (owner/developer caused the delay)
                        This ensures we only ask for ONE commentary explanation - from the responsible party. */}
                    {((revalidationStatus.days_until_submission_due !== null && revalidationStatus.days_until_submission_due < 0 && revalidationStatus.days_until_validation_due !== null && revalidationStatus.days_until_validation_due >= 0) ||
                      (revalidationStatus.days_until_validation_due !== null && revalidationStatus.days_until_validation_due < 0 && !revalidationStatus.submission_received)) && (
                        <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 mb-6">
                            <div className="flex items-start">
                                <svg className="h-5 w-5 text-yellow-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                </svg>
                                <div className="flex-1">
                                    <h3 className="text-sm font-bold text-yellow-800">
                                        {revalidationStatus.days_until_validation_due !== null && revalidationStatus.days_until_validation_due < 0
                                            ? 'Submission Required - Validation Overdue'
                                            : revalidationStatus.status.includes('Grace')
                                                ? 'Documentation Submission - In Grace Period'
                                                : 'Documentation Submission Overdue'}
                                    </h3>
                                    <p className="text-sm text-yellow-700 mt-1">
                                        {revalidationStatus.days_until_validation_due !== null && revalidationStatus.days_until_validation_due < 0 ? (
                                            <>
                                                Model documentation has not been submitted for validation.
                                                The model owner/developer must provide an explanation for this delay.
                                            </>
                                        ) : (
                                            <>
                                                Submission was due {revalidationStatus.next_submission_due && `on ${revalidationStatus.next_submission_due}`}.
                                                {revalidationStatus.grace_period_end && ` Grace period ends ${revalidationStatus.grace_period_end}.`}
                                            </>
                                        )}
                                        {revalidationStatus.active_request_id && (
                                            <Link to={`/validation-workflow/${revalidationStatus.active_request_id}`} className="ml-2 underline font-medium hover:text-yellow-900">
                                                {revalidationStatus.days_until_validation_due !== null && revalidationStatus.days_until_validation_due < 0
                                                    ? 'View validation request →'
                                                    : 'Submit documentation →'}
                                            </Link>
                                        )}
                                    </p>
                                    {/* Commentary Status for Pre-Submission */}
                                    {revalidationStatus.active_request_id && overdueCommentary && (
                                        <div className="mt-3 pt-3 border-t border-yellow-200">
                                            {overdueCommentary.has_current_comment && overdueCommentary.current_comment ? (
                                                <div className="text-sm">
                                                    <p className="text-yellow-800">
                                                        <span className="font-medium">Current explanation:</span>{' '}
                                                        <span className="italic">"{overdueCommentary.current_comment.reason_comment}"</span>
                                                    </p>
                                                    <p className="text-yellow-700 text-xs mt-1">
                                                        Target submission: {overdueCommentary.current_comment.target_date.split('T')[0]} •
                                                        By: {overdueCommentary.current_comment.created_by_user.full_name}
                                                        {overdueCommentary.is_stale && (
                                                            <span className="ml-2 text-yellow-900 font-medium">
                                                                ⚠ Update required: {overdueCommentary.stale_reason}
                                                            </span>
                                                        )}
                                                    </p>
                                                </div>
                                            ) : (
                                                <p className="text-sm text-yellow-800 font-medium">
                                                    ⚠ No explanation provided for this delay
                                                </p>
                                            )}
                                            <button
                                                onClick={() => handleOpenCommentaryModal('PRE_SUBMISSION')}
                                                className="mt-2 px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700"
                                            >
                                                {overdueCommentary.has_current_comment ? 'Update Explanation' : 'Provide Explanation'}
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Decommissioning Alert Banner */}
            {!editing && activeTab === 'details' && decommissioningRequests.length > 0 && decommissioningRequests[0].status !== 'APPROVED' && decommissioningRequests[0].status !== 'REJECTED' && decommissioningRequests[0].status !== 'WITHDRAWN' && (
                <div className="bg-purple-50 border-l-4 border-purple-500 p-4 mb-6">
                    <div className="flex items-start">
                        <svg className="h-5 w-5 text-purple-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        <div className="flex-1">
                            <h3 className="text-sm font-bold text-purple-800">Decommissioning In Progress</h3>
                            <p className="text-sm text-purple-700 mt-1">
                                This model has an active decommissioning request with status: <strong>{decommissioningRequests[0].status}</strong> ({decommissioningRequests[0].last_production_date}).
                                <button
                                    onClick={() => setActiveTab('decommissioning')}
                                    className="ml-2 underline font-medium hover:text-purple-900"
                                >
                                    View decommissioning details →
                                </button>
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {editing ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h3 className="text-lg font-bold mb-4">Edit Model</h3>
                    {editError && (
                        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
                            <div className="flex">
                                <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                <div className="ml-3">
                                    <p className="text-sm font-medium text-red-800">{editError}</p>
                                </div>
                            </div>
                        </div>
                    )}
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label htmlFor="model_name" className="block text-sm font-medium mb-2">
                                    Model Name
                                </label>
                                <input
                                    id="model_name"
                                    type="text"
                                    className="input-field"
                                    value={formData.model_name}
                                    onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                                    required
                                />
                            </div>

                            <div className="mb-4">
                                <label htmlFor="development_type" className="block text-sm font-medium mb-2">
                                    Development Type
                                </label>
                                <select
                                    id="development_type"
                                    className="input-field"
                                    value={formData.development_type}
                                    onChange={(e) => setFormData({
                                        ...formData,
                                        development_type: e.target.value,
                                        vendor_id: e.target.value === 'In-House' ? null : formData.vendor_id
                                    })}
                                >
                                    <option value="In-House">In-House</option>
                                    <option value="Third-Party">Third-Party</option>
                                </select>
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">Classification</label>
                                <div className="flex items-center gap-4">
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="radio"
                                            name="is_model"
                                            checked={formData.is_model === true}
                                            onChange={() => setFormData({ ...formData, is_model: true })}
                                            className="w-4 h-4 text-blue-600"
                                        />
                                        <span className="text-sm">Model</span>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="radio"
                                            name="is_model"
                                            checked={formData.is_model === false}
                                            onChange={() => setFormData({ ...formData, is_model: false })}
                                            className="w-4 h-4 text-blue-600"
                                        />
                                        <span className="text-sm">Non-Model</span>
                                    </label>
                                </div>
                                <p className="text-xs text-gray-500 mt-1">Non-models are tools/applications that use quantitative methods but don't meet the regulatory definition of a model</p>
                            </div>

                            {/* MRSA Classification - only shown when is_model=false */}
                            {formData.is_model === false && (
                                <div className="mb-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                                    <h4 className="text-sm font-medium text-purple-800 mb-3">MRSA Classification</h4>
                                    <div className="mb-3">
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={formData.is_mrsa}
                                                onChange={(e) => setFormData({
                                                    ...formData,
                                                    is_mrsa: e.target.checked,
                                                    mrsa_risk_level_id: e.target.checked ? formData.mrsa_risk_level_id : null,
                                                    mrsa_risk_rationale: e.target.checked ? formData.mrsa_risk_rationale : ''
                                                })}
                                                className="w-4 h-4 text-purple-600 rounded"
                                            />
                                            <span className="text-sm font-medium text-gray-700">Mark as MRSA (Model Risk-Sensitive Application)</span>
                                        </label>
                                        <p className="text-xs text-gray-500 mt-1 ml-6">MRSAs are non-model applications with characteristics similar to models that require oversight</p>
                                    </div>

                                    {formData.is_mrsa && (
                                        <>
                                            <div className="mb-3">
                                                <label htmlFor="mrsa_risk_level_id" className="block text-sm font-medium text-gray-700 mb-1">
                                                    MRSA Risk Level <span className="text-red-500">*</span>
                                                </label>
                                                <select
                                                    id="mrsa_risk_level_id"
                                                    className="input-field"
                                                    value={formData.mrsa_risk_level_id || ''}
                                                    onChange={(e) => setFormData({
                                                        ...formData,
                                                        mrsa_risk_level_id: e.target.value ? parseInt(e.target.value) : null
                                                    })}
                                                    required
                                                >
                                                    <option value="">Select Risk Level</option>
                                                    {mrsaRiskLevels
                                                        .sort((a, b) => a.sort_order - b.sort_order)
                                                        .map(v => (
                                                            <option key={v.value_id} value={v.value_id}>{v.label}</option>
                                                        ))}
                                                </select>
                                            </div>

                                            {/* Show IRP warning if High-Risk is selected */}
                                            {formData.mrsa_risk_level_id && mrsaRiskLevels.find(v => v.value_id === formData.mrsa_risk_level_id)?.requires_irp && (
                                                <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                                                    <p className="text-sm text-yellow-800">
                                                        <span className="font-medium">⚠️ High-Risk MRSA:</span> This MRSA will require IRP (Independent Review Process) coverage
                                                    </p>
                                                </div>
                                            )}

                                            <div className="mb-3">
                                                <label htmlFor="mrsa_risk_rationale" className="block text-sm font-medium text-gray-700 mb-1">
                                                    Risk Rationale <span className="text-red-500">*</span>
                                                </label>
                                                <textarea
                                                    id="mrsa_risk_rationale"
                                                    className="input-field"
                                                    rows={3}
                                                    value={formData.mrsa_risk_rationale}
                                                    onChange={(e) => setFormData({ ...formData, mrsa_risk_rationale: e.target.value })}
                                                    placeholder="Provide justification for MRSA classification and risk level..."
                                                    required
                                                />
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            <div className="mb-4">
                                <label htmlFor="owner_id" className="block text-sm font-medium mb-2">
                                    Owner
                                </label>
                                <select
                                    id="owner_id"
                                    className="input-field"
                                    value={formData.owner_id}
                                    onChange={(e) => setFormData({ ...formData, owner_id: parseInt(e.target.value) })}
                                    required
                                >
                                    <option value="">Select Owner</option>
                                    {users.map(u => (
                                        <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="developer_id" className="block text-sm font-medium mb-2">
                                    Developer
                                </label>
                                <select
                                    id="developer_id"
                                    className="input-field"
                                    value={formData.developer_id || ''}
                                    onChange={(e) => setFormData({
                                        ...formData,
                                        developer_id: e.target.value ? parseInt(e.target.value) : null
                                    })}
                                >
                                    <option value="">None</option>
                                    {users.map(u => (
                                        <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="shared_owner_id" className="block text-sm font-medium mb-2">
                                    Shared Owner (Co-Owner)
                                </label>
                                <select
                                    id="shared_owner_id"
                                    className="input-field"
                                    value={formData.shared_owner_id || ''}
                                    onChange={(e) => setFormData({
                                        ...formData,
                                        shared_owner_id: e.target.value ? parseInt(e.target.value) : null
                                    })}
                                >
                                    <option value="">None</option>
                                    {users
                                        .filter(u => u.user_id !== formData.owner_id)
                                        .map(u => (
                                            <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                                        ))}
                                </select>
                                <p className="text-xs text-gray-500 mt-1">Optional co-owner for shared ownership scenarios</p>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="shared_developer_id" className="block text-sm font-medium mb-2">
                                    Shared Developer (Co-Developer)
                                </label>
                                <select
                                    id="shared_developer_id"
                                    className="input-field"
                                    value={formData.shared_developer_id || ''}
                                    onChange={(e) => setFormData({
                                        ...formData,
                                        shared_developer_id: e.target.value ? parseInt(e.target.value) : null
                                    })}
                                >
                                    <option value="">None</option>
                                    {users
                                        .filter(u => u.user_id !== formData.developer_id)
                                        .map(u => (
                                            <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                                        ))}
                                </select>
                                <p className="text-xs text-gray-500 mt-1">Optional co-developer for shared development scenarios</p>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="monitoring_manager_id" className="block text-sm font-medium mb-2">
                                    Monitoring Manager
                                </label>
                                <select
                                    id="monitoring_manager_id"
                                    className="input-field"
                                    value={formData.monitoring_manager_id || ''}
                                    onChange={(e) => setFormData({
                                        ...formData,
                                        monitoring_manager_id: e.target.value ? parseInt(e.target.value) : null
                                    })}
                                >
                                    <option value="">None</option>
                                    {users.map(u => (
                                        <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                                    ))}
                                </select>
                                <p className="text-xs text-gray-500 mt-1">User responsible for ongoing model monitoring</p>
                            </div>

                            {formData.development_type === 'Third-Party' && (
                                <div className="mb-4">
                                    <label htmlFor="vendor_id" className="block text-sm font-medium mb-2">
                                        Vendor
                                    </label>
                                    <select
                                        id="vendor_id"
                                        className="input-field"
                                        value={formData.vendor_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            vendor_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                        required
                                    >
                                        <option value="">Select Vendor</option>
                                        {vendors.map(v => (
                                            <option key={v.vendor_id} value={v.vendor_id}>{v.name}</option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {getModelStatusTaxonomy() && (
                                <div className="mb-4">
                                    <label htmlFor="status_id" className="block text-sm font-medium mb-2">
                                        Status
                                    </label>
                                    <select
                                        id="status_id"
                                        className="input-field"
                                        value={formData.status_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            status_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">Select Status</option>
                                        {getModelStatusTaxonomy()?.values
                                            .filter(v => v.is_active)
                                            .sort((a, b) => a.sort_order - b.sort_order)
                                            .map(v => (
                                                <option key={v.value_id} value={v.value_id}>{v.label}</option>
                                            ))}
                                    </select>
                                </div>
                            )}

                            {getRiskTierTaxonomy() && (
                                <div className="mb-4">
                                    <label htmlFor="risk_tier_id" className="block text-sm font-medium mb-2">
                                        Risk Tier
                                        {hasGlobalAssessment && (
                                            <span className="ml-2 text-xs text-gray-500 font-normal">(Managed by Risk Assessment)</span>
                                        )}
                                    </label>
                                    <select
                                        id="risk_tier_id"
                                        className={`input-field ${hasGlobalAssessment ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                                        value={formData.risk_tier_id || ''}
                                        disabled={hasGlobalAssessment}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            risk_tier_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">Select Risk Tier</option>
                                        {getRiskTierTaxonomy()?.values
                                            .filter(v => v.is_active)
                                            .sort((a, b) => a.sort_order - b.sort_order)
                                            .map(v => (
                                                <option key={v.value_id} value={v.value_id}>{v.label}</option>
                                            ))}
                                    </select>
                                    {hasGlobalAssessment && (
                                        <p className="mt-1 text-xs text-gray-500">
                                            Risk tier is determined by the Risk Assessment. Go to the Risk Assessment tab to update.
                                        </p>
                                    )}
                                </div>
                            )}

                            {getUsageFrequencyTaxonomy() && (
                                <div className="mb-4">
                                    <label htmlFor="usage_frequency_id" className="block text-sm font-medium mb-2">
                                        Typical Usage Frequency <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        id="usage_frequency_id"
                                        className="input-field"
                                        required
                                        value={formData.usage_frequency_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            usage_frequency_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="" disabled>Select Usage Frequency</option>
                                        {getUsageFrequencyTaxonomy()?.values
                                            .filter(v => v.is_active)
                                            .sort((a, b) => a.sort_order - b.sort_order)
                                            .map(v => (
                                                <option key={v.value_id} value={v.value_id}>{v.label}</option>
                                            ))}
                                    </select>
                                </div>
                            )}

                            <div className="mb-4">
                                <label htmlFor="model_type_id" className="block text-sm font-medium mb-2">
                                    Model Type
                                </label>
                                <select
                                    id="model_type_id"
                                    className="input-field"
                                    value={formData.model_type_id || ''}
                                    onChange={(e) => setFormData({
                                        ...formData,
                                        model_type_id: e.target.value ? parseInt(e.target.value) : null
                                    })}
                                >
                                    <option value="">Select Model Type</option>
                                    {modelTypes.map(category => (
                                        <optgroup key={category.category_id} label={category.name}>
                                            {category.model_types.map(type => (
                                                <option key={type.type_id} value={type.type_id}>
                                                    {type.name}
                                                </option>
                                            ))}
                                        </optgroup>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="methodology_id" className="block text-sm font-medium mb-2">
                                    Methodology
                                </label>
                                <select
                                    id="methodology_id"
                                    className="input-field"
                                    value={formData.methodology_id || ''}
                                    onChange={(e) => setFormData({
                                        ...formData,
                                        methodology_id: e.target.value ? parseInt(e.target.value) : null
                                    })}
                                >
                                    <option value="">Select Methodology</option>
                                    {methodologyCategories.map(category => (
                                        <optgroup key={category.category_id} label={category.name}>
                                            {category.methodologies.map(methodology => (
                                                <option key={methodology.methodology_id} value={methodology.methodology_id}>
                                                    {methodology.name}
                                                </option>
                                            ))}
                                        </optgroup>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="wholly_owned_region_id" className="block text-sm font-medium mb-2">
                                    Wholly-Owned By Region
                                </label>
                                <select
                                    id="wholly_owned_region_id"
                                    className="input-field"
                                    value={formData.wholly_owned_region_id || ''}
                                    onChange={(e) => setFormData({
                                        ...formData,
                                        wholly_owned_region_id: e.target.value ? parseInt(e.target.value) : null
                                    })}
                                >
                                    <option value="">None (Global)</option>
                                    {regions.map(r => (
                                        <option key={r.region_id} value={r.region_id}>{r.name} ({r.code})</option>
                                    ))}
                                </select>
                                <p className="text-xs text-gray-500 mt-1">
                                    Select a region if this model is wholly-owned by that region's governance structure
                                </p>
                            </div>
                        </div>

                        <div className="mb-4">
                            <label htmlFor="description" className="block text-sm font-medium mb-2">
                                Description and Purpose
                            </label>
                            <textarea
                                id="description"
                                className="input-field"
                                rows={3}
                                placeholder="Describe what this model does and its business purpose..."
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            />
                        </div>
                        <div className="mb-4">
                            <label htmlFor="products_covered" className="block text-sm font-medium mb-2">
                                Products Covered
                            </label>
                            <textarea
                                id="products_covered"
                                className="input-field"
                                rows={2}
                                placeholder="List products, portfolios, or lines of business covered by this model..."
                                value={formData.products_covered}
                                onChange={(e) => setFormData({ ...formData, products_covered: e.target.value })}
                            />
                        </div>

                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Model Users</label>

                            {/* User search/lookup */}
                            <div className="relative mb-3">
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="Search users by name or email..."
                                    value={userSearchTerm}
                                    onChange={(e) => {
                                        setUserSearchTerm(e.target.value);
                                        setShowUserDropdown(e.target.value.length > 0);
                                    }}
                                    onFocus={() => userSearchTerm.length > 0 && setShowUserDropdown(true)}
                                    onBlur={() => setTimeout(() => setShowUserDropdown(false), 200)}
                                />
                                {showUserDropdown && filteredUsersForSearch.length > 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                                        {filteredUsersForSearch.map(u => (
                                            <button
                                                key={u.user_id}
                                                type="button"
                                                className="w-full text-left px-4 py-2 hover:bg-blue-50 focus:bg-blue-50"
                                                onClick={() => addUserToModel(u.user_id)}
                                            >
                                                <div className="font-medium">{u.full_name}</div>
                                                <div className="text-sm text-gray-500">{u.email}</div>
                                            </button>
                                        ))}
                                    </div>
                                )}
                                {showUserDropdown && userSearchTerm && filteredUsersForSearch.length === 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg p-3 text-gray-500 text-sm">
                                        No users found matching "{userSearchTerm}"
                                    </div>
                                )}
                            </div>

                            {/* Selected users subform */}
                            <div className="border rounded bg-gray-50 p-3">
                                <div className="text-sm font-medium text-gray-600 mb-2">
                                    Selected Users ({selectedUsers.length})
                                </div>
                                {selectedUsers.length === 0 ? (
                                    <div className="text-sm text-gray-500 italic">
                                        No users added. Use the search above to add users.
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {selectedUsers.map(u => (
                                            <div
                                                key={u.user_id}
                                                className="flex items-center justify-between bg-white p-2 rounded border"
                                            >
                                                <div>
                                                    <div className="font-medium text-sm">{u.full_name}</div>
                                                    <div className="text-xs text-gray-500">{u.email}</div>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => removeUserFromModel(u.user_id)}
                                                    className="text-red-500 hover:text-red-700 text-sm px-2"
                                                >
                                                    Remove
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {getRegulatoryCategoryTaxonomy() && (
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Regulatory Categories ({formData.regulatory_category_ids.length} selected)
                                </label>
                                <div className="border rounded bg-gray-50 p-3 max-h-48 overflow-y-auto">
                                    <div className="space-y-1">
                                        {getRegulatoryCategoryTaxonomy()?.values
                                            .filter(v => v.is_active)
                                            .sort((a, b) => a.sort_order - b.sort_order)
                                            .map(v => (
                                                <label key={v.value_id} className="flex items-start gap-2 cursor-pointer hover:bg-white p-1 rounded">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.regulatory_category_ids.includes(v.value_id)}
                                                        onChange={() => toggleRegulatoryCategory(v.value_id)}
                                                        className="mt-1"
                                                    />
                                                    <span className="text-sm">{v.label}</span>
                                                </label>
                                            ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">
                                Save Changes
                            </button>
                            <button type="button" onClick={() => setEditing(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            ) : activeTab === 'details' ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <div className="grid grid-cols-2 gap-6">
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Model ID</h4>
                            <p className="text-lg">{model.model_id}</p>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Status</h4>
                            <span className="px-2 py-1 text-sm rounded bg-blue-100 text-blue-800">
                                {model.status_value?.label || model.status}
                            </span>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Development Type</h4>
                            <span className={`px-2 py-1 text-sm rounded ${model.development_type === 'In-House'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-purple-100 text-purple-800'
                                }`}>
                                {model.development_type}
                            </span>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Classification</h4>
                            <span className={`px-2 py-1 text-sm rounded ${model.is_model
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-gray-200 text-gray-700'
                                }`}>
                                {model.is_model ? 'Model' : 'Non-Model'}
                            </span>
                        </div>
                        {!model.is_model && model.is_mrsa && (
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">MRSA Status</h4>
                                <span className={`px-2 py-1 text-sm rounded ${
                                    model.mrsa_risk_level?.code === 'HIGH_RISK'
                                        ? 'bg-red-100 text-red-800'
                                        : 'bg-purple-100 text-purple-800'
                                }`}>
                                    {model.mrsa_risk_level?.label || 'MRSA'}
                                </span>
                            </div>
                        )}
                        {/* IRP Coverage for MRSAs */}
                        {!model.is_model && model.is_mrsa && (
                            <div className="col-span-2">
                                <h4 className="text-sm font-medium text-gray-500 mb-2">IRP Coverage</h4>
                                {irpCoverage?.requires_irp && !irpCoverage?.has_irp_coverage ? (
                                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-2">
                                        <p className="text-sm text-red-700 font-medium">
                                            ⚠️ High-Risk MRSA requires IRP coverage
                                        </p>
                                    </div>
                                ) : irpCoverage?.has_irp_coverage ? (
                                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-2">
                                        <p className="text-sm text-green-700 font-medium">
                                            ✓ IRP coverage in place
                                        </p>
                                    </div>
                                ) : null}
                                {/* List of linked IRPs */}
                                {irpCoverage && irpCoverage.irp_ids.length > 0 ? (
                                    <div className="space-y-2">
                                        {irpCoverage.irp_ids.map((irpId, index) => (
                                            <div key={irpId} className="flex items-center justify-between bg-gray-50 rounded px-3 py-2">
                                                <Link
                                                    to={`/irps/${irpId}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline"
                                                >
                                                    {irpCoverage.irp_names[index] || `IRP #${irpId}`}
                                                </Link>
                                                {canManageIrpsFlag && (
                                                    <button
                                                        onClick={() => handleUnlinkIrp(irpId)}
                                                        className="text-red-600 hover:text-red-800 text-sm"
                                                        title="Remove from IRP"
                                                    >
                                                        ✕
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-gray-500 italic">No IRP coverage assigned</p>
                                )}
                                {/* Link to IRP button - Admin only */}
                                {canManageIrpsFlag && (
                                    <button
                                        onClick={() => {
                                            setShowIrpLinkModal(true);
                                            setSelectedIrpId(null);
                                            setIrpSearchTerm('');
                                        }}
                                        className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                                    >
                                        + Link to IRP
                                    </button>
                                )}
                            </div>
                        )}
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Vendor</h4>
                            {model.vendor ? (
                                <Link
                                    to={`/vendors/${model.vendor.vendor_id}`}
                                    className="text-lg text-blue-600 hover:text-blue-800 hover:underline"
                                >
                                    {model.vendor.name}
                                </Link>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Risk Tier</h4>
                            {model.risk_tier ? (
                                <span className="px-2 py-1 text-sm rounded bg-orange-100 text-orange-800">
                                    {model.risk_tier.label}
                                </span>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Usage Frequency</h4>
                            {model.usage_frequency ? (
                                <span className="px-2 py-1 text-sm rounded bg-blue-100 text-blue-800">
                                    {model.usage_frequency.label}
                                </span>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Model Type</h4>
                            {model.model_type ? (
                                <span className="px-2 py-1 text-sm rounded bg-teal-100 text-teal-800">
                                    {(() => {
                                        const category = modelTypes.find(c => c.category_id === model.model_type?.category_id);
                                        return category ? `${category.name} - ${model.model_type.name}` : model.model_type.name;
                                    })()}
                                </span>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Methodology</h4>
                            {model.methodology ? (
                                <span className="px-2 py-1 text-sm rounded bg-cyan-100 text-cyan-800">
                                    {(() => {
                                        const category = methodologyCategories.find(c => c.category_id === model.methodology?.category_id);
                                        return category ? `${category.name} - ${model.methodology.name}` : model.methodology.name;
                                    })()}
                                </span>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">AI/ML Classification</h4>
                            {model.is_aiml === true ? (
                                <span className="px-2 py-1 text-sm rounded bg-purple-100 text-purple-800 font-medium">
                                    AI/ML Model
                                </span>
                            ) : model.is_aiml === false ? (
                                <span className="px-2 py-1 text-sm rounded bg-gray-100 text-gray-700">
                                    Non-AI/ML Model
                                </span>
                            ) : (
                                <span className="px-2 py-1 text-sm rounded bg-gray-50 text-gray-500 italic">
                                    Undefined (No Methodology)
                                </span>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Wholly-Owned By Region</h4>
                            {model.wholly_owned_region ? (
                                <span className="inline-flex items-center gap-1.5 px-2 py-1 text-sm rounded bg-indigo-100 text-indigo-800 border border-indigo-300 font-medium">
                                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                                    </svg>
                                    {model.wholly_owned_region.name} ({model.wholly_owned_region.code})
                                </span>
                            ) : (
                                <p className="text-lg">Global</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Business Line</h4>
                            {model.business_line_name ? (
                                <span className="px-2 py-1 text-sm rounded bg-amber-100 text-amber-800">
                                    {model.business_line_name}
                                </span>
                            ) : (
                                <p className="text-lg text-gray-400">-</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Team</h4>
                            {model.team ? (
                                <span className="px-2 py-1 text-sm rounded bg-emerald-100 text-emerald-800">
                                    {model.team.name}
                                </span>
                            ) : (
                                <p className="text-lg text-gray-400">Unassigned</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Approval Status</h4>
                            {model.approval_status ? (
                                <span className={`px-2 py-1 text-sm rounded font-medium ${
                                    model.approval_status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                                    model.approval_status === 'INTERIM_APPROVED' ? 'bg-yellow-100 text-yellow-800' :
                                    model.approval_status === 'VALIDATION_IN_PROGRESS' ? 'bg-blue-100 text-blue-800' :
                                    model.approval_status === 'EXPIRED' ? 'bg-red-100 text-red-800' :
                                    model.approval_status === 'NEVER_VALIDATED' ? 'bg-gray-100 text-gray-800' :
                                    'bg-gray-100 text-gray-700'
                                }`}>
                                    {model.approval_status_label || model.approval_status}
                                </span>
                            ) : (
                                <p className="text-lg text-gray-400">-</p>
                            )}
                        </div>
                        {/* Model Roles Section */}
                        <div className="col-span-2">
                            <h4 className="text-sm font-medium text-gray-500 mb-3 flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                                </svg>
                                Model Roles
                            </h4>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                                {/* Owner */}
                                <div className="border-r border-gray-200 pr-4 last:border-r-0">
                                    <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Owner</p>
                                    <p className="text-sm font-medium text-gray-900">{model.owner.full_name}</p>
                                    <p className="text-xs text-gray-500">{model.owner.email}</p>
                                    {rolesWithLOB?.owner.lob_rollup_name && (
                                        <p className="text-xs text-blue-600 mt-1">{rolesWithLOB.owner.lob_rollup_name}</p>
                                    )}
                                </div>
                                {/* Shared Owner */}
                                <div className="border-r border-gray-200 pr-4 last:border-r-0">
                                    <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Shared Owner</p>
                                    {model.shared_owner ? (
                                        <>
                                            <p className="text-sm font-medium text-gray-900">{model.shared_owner.full_name}</p>
                                            <p className="text-xs text-gray-500">{model.shared_owner.email}</p>
                                            {rolesWithLOB?.shared_owner?.lob_rollup_name && (
                                                <p className="text-xs text-blue-600 mt-1">{rolesWithLOB.shared_owner.lob_rollup_name}</p>
                                            )}
                                        </>
                                    ) : (
                                        <p className="text-sm text-gray-400">-</p>
                                    )}
                                </div>
                                {/* Developer */}
                                <div className="border-r border-gray-200 pr-4 last:border-r-0">
                                    <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Developer</p>
                                    {model.developer ? (
                                        <>
                                            <p className="text-sm font-medium text-gray-900">{model.developer.full_name}</p>
                                            <p className="text-xs text-gray-500">{model.developer.email}</p>
                                            {rolesWithLOB?.developer?.lob_rollup_name && (
                                                <p className="text-xs text-blue-600 mt-1">{rolesWithLOB.developer.lob_rollup_name}</p>
                                            )}
                                        </>
                                    ) : (
                                        <p className="text-sm text-gray-400">-</p>
                                    )}
                                </div>
                                {/* Shared Developer */}
                                <div>
                                    <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Shared Developer</p>
                                    {model.shared_developer ? (
                                        <>
                                            <p className="text-sm font-medium text-gray-900">{model.shared_developer.full_name}</p>
                                            <p className="text-xs text-gray-500">{model.shared_developer.email}</p>
                                            {rolesWithLOB?.shared_developer?.lob_rollup_name && (
                                                <p className="text-xs text-blue-600 mt-1">{rolesWithLOB.shared_developer.lob_rollup_name}</p>
                                            )}
                                        </>
                                    ) : (
                                        <p className="text-sm text-gray-400">-</p>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Delegates Collapsible Section */}
                        <div className="col-span-2">
                            <button
                                onClick={() => setShowDelegates(!showDelegates)}
                                className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
                            >
                                <svg
                                    className={`w-4 h-4 transform transition-transform ${showDelegates ? 'rotate-90' : ''}`}
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                                <span className="flex items-center gap-1">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                                    </svg>
                                    Manage Delegates
                                </span>
                            </button>
                            {showDelegates && (
                                <div className="mt-3 border border-gray-200 rounded-lg bg-gray-50 p-4">
                                    <DelegatesSection
                                        modelId={model.model_id}
                                        modelOwnerId={model.owner_id}
                                        currentUserId={user?.user_id || 0}
                                    />
                                </div>
                            )}
                        </div>

                        <div className="col-span-2">
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Description and Purpose</h4>
                            <p className="text-lg">{model.description || 'No description provided'}</p>
                        </div>
                        <div className="col-span-2">
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Products Covered</h4>
                            <p className="text-lg">{model.products_covered || 'No products covered provided'}</p>
                        </div>
                        <div className="col-span-2">
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Model Users</h4>
                            {model.users.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {model.users.map(u => (
                                        <span key={u.user_id} className="px-3 py-1 bg-gray-100 rounded text-sm">
                                            {u.full_name}
                                        </span>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-gray-500">No users assigned</p>
                            )}
                        </div>
                        <div className="col-span-2">
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Regulatory Categories</h4>
                            {model.regulatory_categories.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {model.regulatory_categories.map(c => (
                                        <span key={c.value_id} className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded text-sm">
                                            {c.label}
                                        </span>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-gray-500">No regulatory categories assigned</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Created</h4>
                            <p className="text-sm">{new Date(model.created_at).toLocaleString()}</p>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Last Updated</h4>
                            <p className="text-sm">{new Date(model.updated_at).toLocaleString()}</p>
                        </div>
                    </div>

                    {/* Risk Assessment Summary Card */}
                    {(() => {
                        // Find the latest approved validation with scorecard data
                        const approvedValidations = validationRequests
                            .filter(v => v.current_status === 'APPROVED' && v.scorecard_overall_rating)
                            .sort((a, b) => new Date(b.completion_date || b.created_at).getTime() - new Date(a.completion_date || a.created_at).getTime());
                        const latestApproved = approvedValidations[0];

                        if (!latestApproved && !model.risk_tier && !finalRiskRanking) return null;

                        const hasPenalty = finalRiskRanking && finalRiskRanking.downgrade_notches > 0;

                        // Helper to get scorecard badge class
                        const getScorecardBadgeClass = (rating: string) => {
                            if (rating.includes('Green')) return 'bg-green-100 text-green-800';
                            if (rating.includes('Yellow')) return 'bg-yellow-100 text-yellow-800';
                            return 'bg-red-100 text-red-800';
                        };

                        return (
                            <div className="mt-6 bg-gradient-to-r from-gray-50 to-slate-50 p-5 rounded-lg border border-gray-200">
                                <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                                    <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                    </svg>
                                    Risk Assessment Summary
                                    {hasPenalty && (
                                        <span className="ml-2 px-2 py-0.5 text-xs rounded bg-amber-100 text-amber-800">
                                            Overdue Penalty Applied
                                        </span>
                                    )}
                                </h4>

                                {/* Row 1: Inherent Risk + Original Scorecard + Base Residual Risk */}
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="bg-white p-4 rounded border border-gray-200">
                                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Inherent Risk Tier</p>
                                        {model.risk_tier ? (
                                            <span className="px-2 py-1 text-sm rounded bg-orange-100 text-orange-800 font-medium">
                                                {model.risk_tier.label}
                                            </span>
                                        ) : (
                                            <span className="text-gray-400">Not assigned</span>
                                        )}
                                    </div>
                                    <div className="bg-white p-4 rounded border border-gray-200">
                                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
                                            {hasPenalty ? 'Original Scorecard' : 'Scorecard Outcome'}
                                        </p>
                                        {latestApproved?.scorecard_overall_rating ? (
                                            <span className={`px-2 py-1 text-sm rounded font-medium ${getScorecardBadgeClass(latestApproved.scorecard_overall_rating)}`}>
                                                {latestApproved.scorecard_overall_rating}
                                            </span>
                                        ) : finalRiskRanking?.original_scorecard ? (
                                            <span className={`px-2 py-1 text-sm rounded font-medium ${getScorecardBadgeClass(finalRiskRanking.original_scorecard)}`}>
                                                {finalRiskRanking.original_scorecard}
                                            </span>
                                        ) : (
                                            <span className="text-gray-400">No scorecard</span>
                                        )}
                                    </div>
                                    <div className="bg-white p-4 rounded border border-gray-200">
                                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
                                            {hasPenalty ? 'Base Residual Risk' : 'Residual Risk'}
                                        </p>
                                        {hasPenalty && finalRiskRanking?.residual_risk_without_penalty ? (
                                            <span className={getResidualRiskBadgeClass(finalRiskRanking.residual_risk_without_penalty)}>
                                                {finalRiskRanking.residual_risk_without_penalty}
                                            </span>
                                        ) : finalRiskRanking?.final_rating ? (
                                            <span className={getResidualRiskBadgeClass(finalRiskRanking.final_rating)}>
                                                {finalRiskRanking.final_rating}
                                            </span>
                                        ) : latestApproved?.residual_risk ? (
                                            <span className={getResidualRiskBadgeClass(latestApproved.residual_risk)}>
                                                {latestApproved.residual_risk}
                                            </span>
                                        ) : (
                                            <span className="text-gray-400">Not computed</span>
                                        )}
                                    </div>
                                </div>

                                {/* Row 2: Penalty Details (only shown when there's a penalty) */}
                                {hasPenalty && finalRiskRanking && (
                                    <div className="mt-4 grid grid-cols-3 gap-4">
                                        <div className="bg-amber-50 p-4 rounded border border-amber-200">
                                            <p className="text-xs text-amber-700 uppercase tracking-wide mb-1">Overdue Status</p>
                                            <div className="flex flex-col gap-1">
                                                <span className="px-2 py-1 text-sm rounded bg-amber-100 text-amber-800 font-medium inline-block w-fit">
                                                    {finalRiskRanking.past_due_level}
                                                </span>
                                                <span className="text-xs text-amber-600">
                                                    {finalRiskRanking.days_overdue} days overdue
                                                </span>
                                            </div>
                                        </div>
                                        <div className="bg-amber-50 p-4 rounded border border-amber-200">
                                            <p className="text-xs text-amber-700 uppercase tracking-wide mb-1">Adjusted Scorecard</p>
                                            <div className="flex flex-col gap-1">
                                                <span className={`px-2 py-1 text-sm rounded font-medium inline-block w-fit ${getScorecardBadgeClass(finalRiskRanking.adjusted_scorecard)}`}>
                                                    {finalRiskRanking.adjusted_scorecard}
                                                </span>
                                                <span className="text-xs text-amber-600">
                                                    -{finalRiskRanking.downgrade_notches} notch{finalRiskRanking.downgrade_notches !== 1 ? 'es' : ''} penalty
                                                </span>
                                            </div>
                                        </div>
                                        <div className="bg-gradient-to-r from-amber-50 to-red-50 p-4 rounded border border-amber-300">
                                            <p className="text-xs text-amber-800 uppercase tracking-wide mb-1 font-semibold">Final Risk Rating</p>
                                            {finalRiskRanking.final_rating ? (
                                                <span className={`px-2 py-1 text-sm rounded font-bold ${getResidualRiskBadgeClass(finalRiskRanking.final_rating)}`}>
                                                    {finalRiskRanking.final_rating}
                                                </span>
                                            ) : (
                                                <span className="text-gray-400">Not computed</span>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {latestApproved && (
                                    <p className="text-xs text-gray-500 mt-3">
                                        Based on validation approved {latestApproved.completion_date?.split('T')[0] || latestApproved.created_at.split('T')[0]}
                                        {latestApproved.validated_risk_tier && latestApproved.validated_risk_tier !== model.risk_tier?.label && (
                                            <span className="ml-2 text-amber-600">
                                                (Validated tier: {latestApproved.validated_risk_tier})
                                            </span>
                                        )}
                                    </p>
                                )}
                            </div>
                        );
                    })()}

                    {/* Model-Region Management Section */}
                    <div className="mt-6">
                        <ModelRegionsSection
                            modelId={model.model_id}
                            whollyOwnedRegionId={model.wholly_owned_region_id}
                            whollyOwnedRegion={model.wholly_owned_region}
                        />
                    </div>

                    {/* Name History Section */}
                    {nameHistory.length > 0 && (
                        <div className="mt-6 bg-gray-50 p-4 rounded-lg border border-gray-200">
                            <button
                                onClick={() => setShowNameHistory(!showNameHistory)}
                                className="flex items-center justify-between w-full text-left"
                            >
                                <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                                    <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    Name History ({nameHistory.length} change{nameHistory.length !== 1 ? 's' : ''})
                                </h4>
                                <svg
                                    className={`w-5 h-5 text-gray-500 transform transition-transform ${showNameHistory ? 'rotate-180' : ''}`}
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>
                            {showNameHistory && (
                                <div className="mt-3 space-y-2">
                                    {nameHistory.map((item) => (
                                        <div key={item.history_id} className="bg-white p-3 rounded border border-gray-200 text-sm">
                                            <div className="flex items-center gap-2 text-gray-600">
                                                <span className="font-medium text-gray-900">{item.old_name}</span>
                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                                                </svg>
                                                <span className="font-medium text-gray-900">{item.new_name}</span>
                                            </div>
                                            <div className="mt-1 text-xs text-gray-500">
                                                Changed by {item.changed_by_name || 'Unknown'} on {item.changed_at.split('T')[0]}
                                            </div>
                                            {item.change_reason && (
                                                <div className="mt-1 text-xs text-gray-500 italic">
                                                    Reason: {item.change_reason}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            ) : activeTab === 'risk-assessment' ? (
                <ModelRiskAssessmentTab
                    modelId={model.model_id}
                    regions={regions}
                />
            ) : activeTab === 'versions' ? (
                <div className="space-y-6">
                    {/* Regional Version Deployments */}
                    <RegionalVersionsTable modelId={model.model_id} refreshTrigger={versionsRefreshTrigger} />

                    {/* Model Versions List */}
                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h3 className="text-lg font-semibold mb-4">Model Versions</h3>
                        <VersionsList
                            modelId={model.model_id}
                            refreshTrigger={versionsRefreshTrigger}
                            onVersionClick={(version) => setSelectedVersion(version)}
                            onActivate={() => setVersionsRefreshTrigger(prev => prev + 1)}
                        />
                    </div>
                </div>
            ) : activeTab === 'validations' ? (
                <div className="space-y-6">
                    {/* Validation Key Dates Summary - Always shown */}
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-green-50">
                            <div className="flex justify-between items-start">
                                <div>
                                    <h3 className="text-lg font-bold text-green-900">Validation Key Dates</h3>
                                    <p className="text-sm text-green-700">Summary of model validation history and upcoming dates</p>
                                </div>
                                {revalidationStatus && (
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium text-gray-600">Status:</span>
                                        <span className={`px-3 py-1 text-sm font-semibold rounded-full ${
                                            revalidationStatus.status.includes('Overdue') || revalidationStatus.status.includes('Expired') ? 'bg-red-100 text-red-800' :
                                            revalidationStatus.status.includes('In Progress') || revalidationStatus.status.includes('Awaiting') ? 'bg-yellow-100 text-yellow-800' :
                                            revalidationStatus.status === 'Upcoming' ? 'bg-blue-100 text-blue-800' :
                                            revalidationStatus.status.includes('Pending') ? 'bg-purple-100 text-purple-800' :
                                            revalidationStatus.status === 'Never Validated' ? 'bg-gray-100 text-gray-800' :
                                            'bg-green-100 text-green-800'
                                        }`}>
                                            {revalidationStatus.status}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {/* Most Recent Validation */}
                                <div className="border rounded-lg p-4 bg-gray-50">
                                    <div className="text-xs font-medium text-gray-500 uppercase mb-1">
                                        Most Recent Validation
                                    </div>
                                    {revalidationStatus?.most_recent_validation ? (
                                        <>
                                            <div className="text-lg font-semibold text-gray-900">
                                                {revalidationStatus.most_recent_validation.approval_date}
                                            </div>
                                            <div className="text-sm text-gray-600">
                                                {revalidationStatus.most_recent_validation.validation_type}
                                            </div>
                                            <Link
                                                to={`/validation-workflow/${revalidationStatus.most_recent_validation.request_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm hover:underline"
                                            >
                                                Project #{revalidationStatus.most_recent_validation.request_id}
                                            </Link>
                                        </>
                                    ) : (
                                        <div className="text-gray-400 italic">Never validated</div>
                                    )}
                                </div>

                                {/* Previous Validation */}
                                <div className="border rounded-lg p-4 bg-gray-50">
                                    <div className="text-xs font-medium text-gray-500 uppercase mb-1">
                                        Previous Validation
                                    </div>
                                    {revalidationStatus?.previous_validation ? (
                                        <>
                                            <div className="text-lg font-semibold text-gray-900">
                                                {revalidationStatus.previous_validation.approval_date}
                                            </div>
                                            <div className="text-sm text-gray-600">
                                                {revalidationStatus.previous_validation.validation_type}
                                            </div>
                                            <Link
                                                to={`/validation-workflow/${revalidationStatus.previous_validation.request_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm hover:underline"
                                            >
                                                Project #{revalidationStatus.previous_validation.request_id}
                                            </Link>
                                        </>
                                    ) : (
                                        <div className="text-gray-400 italic">
                                            {revalidationStatus?.most_recent_validation ? 'No prior validation' : '-'}
                                        </div>
                                    )}
                                </div>

                                {/* Next Model Submission Due */}
                                <div className="border rounded-lg p-4 bg-gray-50">
                                    <div className="text-xs font-medium text-gray-500 uppercase mb-1">
                                        Next Submission Due
                                        {revalidationStatus?.interim_expiration && (
                                            <span className="ml-1 text-purple-600">(INTERIM)</span>
                                        )}
                                    </div>
                                    {revalidationStatus?.next_submission_due ? (
                                        <>
                                            <div className={`text-lg font-semibold ${
                                                revalidationStatus.days_until_submission_due !== null &&
                                                revalidationStatus.days_until_submission_due < 0
                                                    ? 'text-red-600'
                                                    : revalidationStatus.days_until_submission_due !== null &&
                                                      revalidationStatus.days_until_submission_due < 30
                                                        ? 'text-yellow-600'
                                                        : 'text-gray-900'
                                            }`}>
                                                {revalidationStatus.next_submission_due}
                                            </div>
                                            {revalidationStatus.days_until_submission_due !== null && (
                                                <div className={`text-sm ${
                                                    revalidationStatus.days_until_submission_due < 0
                                                        ? 'text-red-500'
                                                        : 'text-gray-600'
                                                }`}>
                                                    {revalidationStatus.days_until_submission_due < 0
                                                        ? `${Math.abs(revalidationStatus.days_until_submission_due)} days overdue`
                                                        : `${revalidationStatus.days_until_submission_due} days`}
                                                </div>
                                            )}
                                            {revalidationStatus.interim_expiration && (
                                                <div className="text-xs text-purple-600 mt-1">
                                                    INTERIM expires: {revalidationStatus.interim_expiration}
                                                </div>
                                            )}
                                        </>
                                    ) : (
                                        <div className="text-gray-400 italic">
                                            {revalidationStatus?.status === 'Never Validated'
                                                ? 'Pending initial validation'
                                                : revalidationStatus?.status === 'Pending Full Validation'
                                                    ? 'Pending full validation'
                                                    : revalidationStatus?.status === 'No Policy Configured'
                                                        ? 'No policy configured'
                                                        : '-'}
                                        </div>
                                    )}
                                </div>

                                {/* Next Validation Due */}
                                <div className="border rounded-lg p-4 bg-gray-50">
                                    <div className="text-xs font-medium text-gray-500 uppercase mb-1">
                                        {revalidationStatus?.interim_expiration
                                            ? 'INTERIM Expiration'
                                            : 'Next Validation Due'}
                                    </div>
                                    {revalidationStatus?.next_validation_due ? (
                                        <>
                                            <div className={`text-lg font-semibold ${
                                                revalidationStatus.days_until_validation_due !== null &&
                                                revalidationStatus.days_until_validation_due < 0
                                                    ? 'text-red-600'
                                                    : revalidationStatus.days_until_validation_due !== null &&
                                                      revalidationStatus.days_until_validation_due < 60
                                                        ? 'text-orange-600'
                                                        : 'text-gray-900'
                                            }`}>
                                                {revalidationStatus.next_validation_due}
                                            </div>
                                            {revalidationStatus.days_until_validation_due !== null && (
                                                <div className={`text-sm ${
                                                    revalidationStatus.days_until_validation_due < 0
                                                        ? 'text-red-500'
                                                        : 'text-gray-600'
                                                }`}>
                                                    {revalidationStatus.days_until_validation_due < 0
                                                        ? `${Math.abs(revalidationStatus.days_until_validation_due)} days overdue`
                                                        : `${revalidationStatus.days_until_validation_due} days`}
                                                </div>
                                            )}
                                            {revalidationStatus.interim_expiration && (
                                                <div className="text-xs text-purple-600 mt-1">
                                                    Full validation required before this date
                                                </div>
                                            )}
                                        </>
                                    ) : (
                                        <div className="text-gray-400 italic">
                                            {revalidationStatus?.status === 'Never Validated'
                                                ? 'Pending initial validation'
                                                : revalidationStatus?.status === 'Pending Full Validation'
                                                    ? 'Pending full validation'
                                                    : revalidationStatus?.status === 'No Policy Configured'
                                                        ? 'No policy configured'
                                                        : '-'}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Active Validation Projects */}
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-blue-50 flex justify-between items-center">
                            <div>
                                <h3 className="text-lg font-bold">Active Validation Projects</h3>
                                <p className="text-sm text-gray-600">Workflow-based validation projects in progress</p>
                            </div>
                            <Link
                                to={`/validation-workflow/new?model_id=${model.model_id}`}
                                className="btn-primary text-sm"
                            >
                                + New Validation Project
                            </Link>
                        </div>
                        {validationRequests.filter(req =>
                            req.current_status !== 'Approved' &&
                            req.current_status !== 'Cancelled'
                        ).length === 0 ? (
                            <div className="p-6 text-center text-gray-500">
                                No active validation projects for this model.
                            </div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Request ID
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Request Date
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Requestor
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Type
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Priority
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Status
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Primary Validator
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Target Date
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {validationRequests.filter(req =>
                                        req.current_status !== 'Approved' &&
                                        req.current_status !== 'Cancelled'
                                    ).map((request) => (
                                        <tr key={request.request_id} className="hover:bg-gray-50">
                                            <td className="px-4 py-2 whitespace-nowrap text-sm font-mono">
                                                #{request.request_id}
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                {request.request_date}
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                {request.requestor_name}
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap">
                                                <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                    {request.validation_type}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs rounded ${request.priority === 'Critical' ? 'bg-red-100 text-red-800' :
                                                    request.priority === 'High' ? 'bg-orange-100 text-orange-800' :
                                                        request.priority === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                                                            'bg-green-100 text-green-800'
                                                    }`}>
                                                    {request.priority}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs rounded ${request.current_status === 'Intake' ? 'bg-gray-100 text-gray-800' :
                                                    request.current_status === 'Planning' ? 'bg-blue-100 text-blue-800' :
                                                        request.current_status === 'In Progress' ? 'bg-yellow-100 text-yellow-800' :
                                                            request.current_status === 'Review' ? 'bg-purple-100 text-purple-800' :
                                                                request.current_status === 'Pending Approval' ? 'bg-orange-100 text-orange-800' :
                                                                    request.current_status === 'Approved' ? 'bg-green-100 text-green-800' :
                                                                        'bg-red-100 text-red-800'
                                                    }`}>
                                                    {request.current_status}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                {request.primary_validator || (
                                                    <span className="text-orange-600">Unassigned</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                {request.target_completion_date}
                                            </td>
                                            <td className="px-4 py-2 whitespace-nowrap">
                                                <Link
                                                    to={`/validation-workflow/${request.request_id}`}
                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                >
                                                    View Details
                                                </Link>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* Historical Validations */}
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
                            <div>
                                <h3 className="text-lg font-bold">Historical Validations</h3>
                                <p className="text-sm text-gray-600">Completed validation records (Approved {showCancelledValidations ? '& Cancelled' : ''})</p>
                            </div>
                            <label className="flex items-center gap-2 text-sm cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={showCancelledValidations}
                                    onChange={(e) => setShowCancelledValidations(e.target.checked)}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-gray-700">Show Cancelled</span>
                            </label>
                        </div>
                        {(() => {
                            const historicalRequests = validationRequests.filter(req =>
                                req.current_status === 'Approved' ||
                                (showCancelledValidations && req.current_status === 'Cancelled')
                            );

                            return historicalRequests.length === 0 ? (
                                <div className="p-6 text-center text-gray-500">
                                    No historical validation records found for this model.
                                </div>
                            ) : (
                                <div>
                                    {historicalRequests.length > 0 && (
                                        <div>
                                            <div className="px-4 py-2 bg-blue-50">
                                                <h4 className="text-sm font-semibold text-gray-700">Historical Validations</h4>
                                            </div>
                                            <table className="min-w-full divide-y divide-gray-200">
                                                <thead className="bg-gray-50">
                                                    <tr>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Request ID
                                                        </th>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Request Date
                                                        </th>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Requestor
                                                        </th>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Type
                                                        </th>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Status
                                                        </th>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Primary Validator
                                                        </th>
                                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Actions
                                                        </th>
                                                    </tr>
                                                </thead>
                                                <tbody className="bg-white divide-y divide-gray-200">
                                                    {historicalRequests.map((request) => (
                                                        <tr key={request.request_id} className="hover:bg-gray-50">
                                                            <td className="px-4 py-2 whitespace-nowrap text-sm font-mono">
                                                                #{request.request_id}
                                                            </td>
                                                            <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                                {request.request_date}
                                                            </td>
                                                            <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                                {request.requestor_name}
                                                            </td>
                                                            <td className="px-4 py-2 whitespace-nowrap">
                                                                <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                                    {request.validation_type}
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-2 whitespace-nowrap">
                                                                <span className={`px-2 py-1 text-xs rounded ${request.current_status === 'Approved' ? 'bg-green-100 text-green-800' : 'bg-gray-400 text-white'
                                                                    }`}>
                                                                    {request.current_status}
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                                {request.primary_validator || '-'}
                                                            </td>
                                                            <td className="px-4 py-2 whitespace-nowrap">
                                                                <Link
                                                                    to={`/validation-workflow/${request.request_id}`}
                                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                                >
                                                                    View Details
                                                                </Link>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            );
                        })()}
                    </div>
                </div>
            ) : activeTab === 'relationships' ? (
                <>
                    {relationshipSubTab === 'hierarchy' && (
                        <ModelHierarchySection modelId={model.model_id} modelName={model.model_name} />
                    )}
                    {relationshipSubTab === 'dependencies' && (
                        <ModelDependenciesSection modelId={model.model_id} modelName={model.model_name} />
                    )}
                    {relationshipSubTab === 'applications' && (
                        <ModelApplicationsSection
                            modelId={model.model_id}
                            canEdit={
                                canManageModelsFlag ||
                                user?.user_id === model.owner_id ||
                                user?.user_id === model.developer_id
                            }
                        />
                    )}
                    {relationshipSubTab === 'lineage' && (
                        <LineageViewer modelId={model.model_id} modelName={model.model_name} />
                    )}
                </>
            ) : activeTab === 'activity' ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-xl font-bold">Activity Timeline</h3>
                        <button
                            onClick={fetchActivities}
                            disabled={activitiesLoading}
                            className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
                        >
                            {activitiesLoading ? 'Refreshing...' : '🔄 Refresh'}
                        </button>
                    </div>

                    {activitiesLoading && activities.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            Loading activities...
                        </div>
                    ) : activities.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            No activity recorded for this model yet.
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {activities.map((activity, index) => (
                                <div key={index} className="flex gap-4 pb-4 border-b last:border-b-0">
                                    <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-blue-50 rounded-full text-blue-600">
                                        {getActivityIcon(activity.activity_type)}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1">
                                                <h4 className="font-semibold text-gray-900">
                                                    {activity.title}
                                                </h4>
                                                {activity.description && (
                                                    <p className="text-sm text-gray-600 mt-1">
                                                        {activity.description}
                                                    </p>
                                                )}
                                                <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                                                    <span>{new Date(activity.timestamp).toLocaleString()}</span>
                                                    {activity.user_name && (
                                                        <>
                                                            <span>•</span>
                                                            <span>{activity.user_name}</span>
                                                        </>
                                                    )}
                                                    {activity.entity_type && (
                                                        <>
                                                            <span>•</span>
                                                            <span className="px-2 py-0.5 bg-gray-100 rounded">
                                                                {activity.entity_type}
                                                                {activity.entity_id && ` #${activity.entity_id}`}
                                                            </span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ) : activeTab === 'recommendations' ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-xl font-bold">Recommendations</h3>
                        {canManageRecommendationsFlag && (
                            <Link
                                to={`/recommendations?model_id=${model.model_id}`}
                                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
                            >
                                Create Recommendation
                            </Link>
                        )}
                    </div>

                    {recommendationsLoading ? (
                        <div className="text-center py-8 text-gray-500">
                            Loading recommendations...
                        </div>
                    ) : recommendations.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                            </svg>
                            <p className="mt-4 text-lg">No recommendations</p>
                            <p className="mt-2 text-sm">
                                Recommendations track remediation actions from validation findings.
                            </p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assigned To</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {recommendations.map((rec) => {
                                        const isOverdue = !['REC_CLOSED', 'REC_DROPPED'].includes(rec.current_status?.code || '') &&
                                            new Date(rec.current_target_date) < new Date();
                                        return (
                                            <tr key={rec.recommendation_id} className="hover:bg-gray-50">
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <span className="font-mono text-sm text-blue-600">{rec.recommendation_code}</span>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className="text-sm">{rec.title}</span>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs rounded ${
                                                        rec.priority?.code === 'HIGH' ? 'bg-red-100 text-red-800' :
                                                        rec.priority?.code === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                                                        'bg-green-100 text-green-800'
                                                    }`}>
                                                        {rec.priority?.label || '-'}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs rounded ${
                                                        rec.current_status?.code === 'REC_CLOSED' ? 'bg-emerald-100 text-emerald-800' :
                                                        rec.current_status?.code === 'REC_DROPPED' ? 'bg-gray-400 text-white' :
                                                        rec.current_status?.code === 'REC_OPEN' ? 'bg-green-100 text-green-800' :
                                                        'bg-blue-100 text-blue-800'
                                                    }`}>
                                                        {rec.current_status?.label || '-'}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm">
                                                    {rec.assigned_to?.full_name || '-'}
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <span className={`text-sm ${isOverdue ? 'text-red-600 font-medium' : ''}`}>
                                                        {rec.current_target_date}
                                                        {isOverdue && ' (Overdue)'}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <Link
                                                        to={`/recommendations/${rec.recommendation_id}`}
                                                        className="text-blue-600 hover:text-blue-800 text-sm"
                                                    >
                                                        View Details
                                                    </Link>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            ) : activeTab === 'limitations' ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <ModelLimitationsTab modelId={model.model_id} />
                </div>
            ) : activeTab === 'monitoring' ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <ModelMonitoringTab
                        modelId={model.model_id}
                        modelName={model.model_name}
                        monitoringManager={rolesWithLOB?.monitoring_manager}
                    />
                </div>
            ) : activeTab === 'decommissioning' ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-xl font-bold">Decommissioning</h3>
                        {/* Show button if model is not retired AND there's no active decommissioning request */}
                        {model.status !== 'Retired' && model.status !== 'Decommissioned' && !model.status?.includes('Decommission') &&
                         !decommissioningRequests.some(r => r.status === 'PENDING' || r.status === 'VALIDATOR_APPROVED') && (
                            <Link
                                to={`/models/${model.model_id}/decommission`}
                                className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 text-sm"
                            >
                                Initiate Decommissioning
                            </Link>
                        )}
                    </div>

                    {decommissioningRequests.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                            <p className="mt-4 text-lg">No decommissioning requests</p>
                            <p className="mt-2 text-sm">
                                {model.status === 'Retired' || model.status === 'Decommissioned' || model.status?.includes('Decommission')
                                    ? 'This model has been retired.'
                                    : 'Click "Initiate Decommissioning" above to start the retirement process for this model.'}
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {decommissioningRequests.map((request) => (
                                <div key={request.request_id} className="border rounded-lg overflow-hidden">
                                    <div className={`px-4 py-3 ${
                                        request.status === 'APPROVED' ? 'bg-green-50 border-b border-green-200' :
                                        request.status === 'REJECTED' || request.status === 'WITHDRAWN' ? 'bg-gray-50 border-b border-gray-200' :
                                        'bg-purple-50 border-b border-purple-200'
                                    }`}>
                                        <div className="flex justify-between items-center">
                                            <div>
                                                <span className={`px-2 py-1 text-xs font-medium rounded ${
                                                    request.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                                                    request.status === 'REJECTED' ? 'bg-red-100 text-red-800' :
                                                    request.status === 'WITHDRAWN' ? 'bg-gray-100 text-gray-800' :
                                                    request.status === 'VALIDATOR_APPROVED' ? 'bg-blue-100 text-blue-800' :
                                                    'bg-orange-100 text-orange-800'
                                                }`}>
                                                    {request.status}
                                                </span>
                                                <span className="ml-3 text-sm text-gray-600">
                                                    Request #{request.request_id}
                                                </span>
                                            </div>
                                            <Link
                                                to={`/models/${model.model_id}/decommission`}
                                                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                View Details →
                                            </Link>
                                        </div>
                                    </div>
                                    <div className="px-4 py-4">
                                        <dl className="grid grid-cols-2 gap-4">
                                            <div>
                                                <dt className="text-sm font-medium text-gray-500">Reason</dt>
                                                <dd className="mt-1 text-sm text-gray-900">{request.reason}</dd>
                                            </div>
                                            <div>
                                                <dt className="text-sm font-medium text-gray-500">Requested By</dt>
                                                <dd className="mt-1 text-sm text-gray-900">{request.created_by_name}</dd>
                                            </div>
                                            <div>
                                                <dt className="text-sm font-medium text-gray-500">Requested On</dt>
                                                <dd className="mt-1 text-sm text-gray-900">{request.created_at.split('T')[0]}</dd>
                                            </div>
                                        </dl>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ) : activeTab === 'exceptions' ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <ModelExceptionsTab modelId={model.model_id} />
                </div>
            ) : null}

            {/* Submit Change Modal */}
            {showSubmitChangeModal && model && (
                <SubmitChangeModal
                    modelId={model.model_id}
                    onClose={() => setShowSubmitChangeModal(false)}
                    onSuccess={() => {
                        setVersionsRefreshTrigger(prev => prev + 1);
                        setActiveTab('versions');
                    }}
                />
            )}

            {selectedVersion && (
                <VersionDetailModal
                    version={selectedVersion}
                    onClose={() => setSelectedVersion(null)}
                    onSuccess={() => {
                        setVersionsRefreshTrigger(prev => prev + 1);
                        setSelectedVersion(null);
                    }}
                />
            )}

            {/* Overdue Commentary Modal */}
            {showCommentaryModal && revalidationStatus?.active_request_id && (
                <OverdueCommentaryModal
                    requestId={revalidationStatus.active_request_id}
                    overdueType={commentaryModalType}
                    modelName={model?.model_name}
                    currentComment={overdueCommentary?.current_comment}
                    onClose={() => setShowCommentaryModal(false)}
                    onSuccess={handleCommentarySuccess}
                />
            )}

            {/* IRP Link Modal */}
            {showIrpLinkModal && model?.is_mrsa && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
                        {(() => {
                            const linkedIrpIds = irpCoverage?.irp_ids ?? [];
                            const availableIrps = allIrps.filter((irp) => !linkedIrpIds.includes(irp.irp_id));
                            const normalizedSearch = irpSearchTerm.trim().toLowerCase();
                            const filteredIrps = normalizedSearch
                                ? availableIrps.filter((irp) => {
                                    const nameMatch = irp.process_name.toLowerCase().includes(normalizedSearch);
                                    const descriptionMatch = (irp.description || '').toLowerCase().includes(normalizedSearch);
                                    const contactMatch = (irp.contact_user?.full_name || '').toLowerCase().includes(normalizedSearch);
                                    return nameMatch || descriptionMatch || contactMatch;
                                })
                                : availableIrps;
                            const hasAvailableIrps = availableIrps.length > 0;

                            return (
                                <>
                        <div className="px-4 py-2 border-b border-gray-200">
                            <h3 className="text-lg font-semibold text-gray-900">Link MRSA to IRP</h3>
                            <p className="text-sm text-gray-500 mt-1">
                                Select an Independent Review Process to cover this MRSA
                            </p>
                        </div>
                        <div className="px-4 py-2">
                            {allIrps.length === 0 ? (
                                <div className="text-center py-4">
                                    <p className="text-gray-500">No active IRPs available.</p>
                                    <p className="text-sm text-gray-400 mt-2">
                                        Create an IRP first from the IRP management page.
                                    </p>
                                </div>
                            ) : (
                                <>
                                    <div className="mb-3">
                                        <label className="block text-sm font-medium text-gray-600 mb-1">
                                            Search IRPs
                                        </label>
                                        <input
                                            type="text"
                                            className="input-field"
                                            placeholder="Search by name, description, or contact..."
                                            value={irpSearchTerm}
                                            onChange={(event) => setIrpSearchTerm(event.target.value)}
                                        />
                                    </div>
                                    {!hasAvailableIrps ? (
                                        <p className="text-center text-gray-500 py-4">
                                            This MRSA is already linked to all available IRPs.
                                        </p>
                                    ) : (
                                        <div className="space-y-3 max-h-96 overflow-y-auto">
                                            {filteredIrps.map((irp) => (
                                                <label
                                                    key={irp.irp_id}
                                                    className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                                                        selectedIrpId === irp.irp_id
                                                            ? 'border-blue-500 bg-blue-50'
                                                            : 'border-gray-200 hover:border-gray-300'
                                                    }`}
                                                >
                                                    <input
                                                        type="radio"
                                                        name="irp"
                                                        value={irp.irp_id}
                                                        checked={selectedIrpId === irp.irp_id}
                                                        onChange={() => setSelectedIrpId(irp.irp_id)}
                                                        className="mt-1 mr-3"
                                                    />
                                                    <div className="flex-1">
                                                        <div className="font-medium text-gray-900">
                                                            {irp.process_name}
                                                        </div>
                                                        {irp.description && (
                                                            <p className="text-sm text-gray-500 mt-0.5">
                                                                {irp.description}
                                                            </p>
                                                        )}
                                                        <div className="text-xs text-gray-400 mt-1">
                                                            Contact: {irp.contact_user?.full_name || 'Unknown'} •
                                                            {irp.covered_mrsa_count} MRSA{irp.covered_mrsa_count !== 1 ? 's' : ''} covered
                                                        </div>
                                                    </div>
                                                </label>
                                            ))}
                                            {filteredIrps.length === 0 && (
                                                <p className="text-center text-gray-500 py-4">
                                                    No IRPs match your search.
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                        <div className="px-4 py-2 border-t border-gray-200 flex justify-end gap-3">
                            <button
                                onClick={() => {
                                    setShowIrpLinkModal(false);
                                    setSelectedIrpId(null);
                                    setIrpSearchTerm('');
                                }}
                                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleLinkIrp}
                                disabled={!selectedIrpId || linkingIrp}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {linkingIrp ? 'Linking...' : 'Link to IRP'}
                            </button>
                        </div>
                                </>
                            );
                        })()}
                    </div>
                </div>
            )}
        </Layout>
    );
}

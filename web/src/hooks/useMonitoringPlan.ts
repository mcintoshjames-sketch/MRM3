/**
 * useMonitoringPlan - Custom hook for monitoring plan configuration
 *
 * Manages plan config state including:
 * - Plan details fetching/editing
 * - Metrics configuration (add, edit, delete)
 * - Models management (add, remove)
 * - Version publishing
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import api from '../api/client';

// Types
interface UserRef {
    user_id: number;
    email: string;
    full_name: string;
}

interface TeamMember {
    user_id: number;
    email: string;
    full_name: string;
}

interface MonitoringTeam {
    team_id: number;
    name: string;
    description: string | null;
    is_active: boolean;
    member_count?: number;
    members?: TeamMember[];
}

interface UserPermissions {
    is_admin: boolean;
    is_team_member: boolean;
    is_data_provider: boolean;
    can_start_cycle: boolean;
    can_submit_cycle: boolean;
    can_request_approval: boolean;
    can_cancel_cycle: boolean;
}

interface Model {
    model_id: number;
    model_name: string;
}

interface KpmRef {
    kpm_id: number;
    name: string;
    category_id: number;
    category_name: string | null;
    evaluation_type: string;
}

export interface PlanMetric {
    metric_id: number;
    kpm_id: number;
    kpm: KpmRef;
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
    qualitative_guidance: string | null;
    sort_order: number;
    is_active: boolean;
}

interface Kpm {
    kpm_id: number;
    name: string;
    description: string | null;
    evaluation_type: 'Quantitative' | 'Qualitative' | 'Outcome Only';
}

interface KpmCategory {
    category_id: number;
    code: string;
    name: string;
    kpms: Kpm[];
}

export interface PlanVersion {
    version_id: number;
    version_number: number;
    version_name: string | null;
    effective_date: string;
    is_active: boolean;
    metrics_count?: number;
    models_count?: number;
}

interface MetricSnapshot {
    snapshot_id: number;
    original_metric_id: number | null;
    kpm_id: number;
    kpm_name: string;
    kpm_category_name: string | null;
    evaluation_type: string;
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
    qualitative_guidance: string | null;
    sort_order: number;
}

interface ModelSnapshot {
    snapshot_id: number;
    model_id: number;
    model_name: string;
}

export interface VersionDetail {
    version_id: number;
    plan_id: number;
    version_number: number;
    version_name: string | null;
    effective_date: string;
    published_at: string;
    is_active: boolean;
    metric_snapshots: MetricSnapshot[];
    model_snapshots: ModelSnapshot[];
}

export interface MonitoringPlan {
    plan_id: number;
    name: string;
    description: string | null;
    frequency: string;
    is_active: boolean;
    next_submission_due_date: string | null;
    next_report_due_date: string | null;
    reporting_lead_days: number;
    data_submission_lead_days: number;
    monitoring_team_id: number | null;
    data_provider_user_id: number | null;
    team?: MonitoringTeam | null;
    data_provider?: UserRef | null;
    models?: Model[];
    metrics?: PlanMetric[];
    active_version_number?: number | null;
    has_unpublished_changes?: boolean;
    version_count?: number;
    user_permissions?: UserPermissions;
}

interface UseMonitoringPlanReturn {
    // Plan state
    plan: MonitoringPlan | null;
    loading: boolean;
    error: string | null;
    fetchPlan: () => Promise<void>;

    // Versions
    versions: PlanVersion[];
    loadingVersions: boolean;
    selectedVersionDetail: VersionDetail | null;
    loadingVersionDetail: boolean;
    fetchVersions: () => Promise<void>;
    fetchVersionDetail: (versionId: number) => Promise<void>;

    // Publish
    showPublishModal: boolean;
    setShowPublishModal: (show: boolean) => void;
    publishForm: { version_name: string; description: string; effective_date: string };
    setPublishForm: React.Dispatch<React.SetStateAction<{ version_name: string; description: string; effective_date: string }>>;
    publishing: boolean;
    publishError: string | null;
    setPublishError: React.Dispatch<React.SetStateAction<string | null>>;
    handlePublishVersion: (e: React.FormEvent) => Promise<void>;

    // Metric editing
    editingMetric: PlanMetric | null;
    setEditingMetric: React.Dispatch<React.SetStateAction<PlanMetric | null>>;
    showMetricModal: boolean;
    setShowMetricModal: React.Dispatch<React.SetStateAction<boolean>>;
    metricForm: { yellow_min: string; yellow_max: string; red_min: string; red_max: string; qualitative_guidance: string };
    setMetricForm: React.Dispatch<React.SetStateAction<{ yellow_min: string; yellow_max: string; red_min: string; red_max: string; qualitative_guidance: string }>>;
    savingMetric: boolean;
    metricError: string | null;
    setMetricError: React.Dispatch<React.SetStateAction<string | null>>;
    openEditMetric: (metric: PlanMetric) => void;
    closeMetricModal: () => void;
    handleSaveMetric: (e: React.FormEvent) => Promise<void>;
    handleDeactivateMetric: (metricId: number) => Promise<void>;

    // Add metric
    showAddMetricModal: boolean;
    setShowAddMetricModal: (show: boolean) => void;
    kpmCategories: KpmCategory[];
    addMetricForm: { kpm_id: number; yellow_min: string; yellow_max: string; red_min: string; red_max: string; qualitative_guidance: string; sort_order: number };
    setAddMetricForm: React.Dispatch<React.SetStateAction<{ kpm_id: number; yellow_min: string; yellow_max: string; red_min: string; red_max: string; qualitative_guidance: string; sort_order: number }>>;
    addingMetric: boolean;
    addMetricError: string | null;
    setAddMetricError: React.Dispatch<React.SetStateAction<string | null>>;
    handleAddMetric: (e: React.FormEvent) => Promise<void>;

    // Models management
    showAddModelModal: boolean;
    setShowAddModelModal: (show: boolean) => void;
    allModels: Model[];
    loadingAllModels: boolean;
    addingModel: boolean;
    removingModelId: number | null;
    modelSearchTerm: string;
    setModelSearchTerm: (term: string) => void;
    availableModels: Model[];
    filteredAvailableModels: Model[];
    openAddModelModal: () => void;
    handleAddModel: (modelId: number) => Promise<void>;
    handleRemoveModel: (modelId: number) => Promise<void>;

    // Plan details editing
    editingPlanDetails: boolean;
    setEditingPlanDetails: React.Dispatch<React.SetStateAction<boolean>>;
    planDetailsForm: { data_provider_user_id: number | null; reporting_lead_days: number; data_submission_lead_days: number };
    setPlanDetailsForm: React.Dispatch<React.SetStateAction<{ data_provider_user_id: number | null; reporting_lead_days: number; data_submission_lead_days: number }>>;
    savingPlanDetails: boolean;
    setSavingPlanDetails: React.Dispatch<React.SetStateAction<boolean>>;
    availableUsers: { user_id: number; full_name: string }[];
    startEditingPlanDetails: () => void;
    cancelEditingPlanDetails: () => void;
    handleSavePlanDetails: (updateCycleAssignee?: boolean) => Promise<void>;

    // Cycle assignee update prompt
    showUpdateCycleAssigneePrompt: boolean;
    setShowUpdateCycleAssigneePrompt: React.Dispatch<React.SetStateAction<boolean>>;
    handleCycleAssigneePromptResponse: (updateAssignee: boolean) => void;
}

export function useMonitoringPlan(planId: string | undefined): UseMonitoringPlanReturn {
    // Plan state
    const [plan, setPlan] = useState<MonitoringPlan | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Versions state
    const [versions, setVersions] = useState<PlanVersion[]>([]);
    const [loadingVersions, setLoadingVersions] = useState(false);
    const [selectedVersionDetail, setSelectedVersionDetail] = useState<VersionDetail | null>(null);
    const [loadingVersionDetail, setLoadingVersionDetail] = useState(false);

    // Publish state
    const [showPublishModal, setShowPublishModal] = useState(false);
    const [publishForm, setPublishForm] = useState({
        version_name: '',
        description: '',
        effective_date: new Date().toISOString().split('T')[0]
    });
    const [publishing, setPublishing] = useState(false);
    const [publishError, setPublishError] = useState<string | null>(null);

    // Metric editing state
    const [editingMetric, setEditingMetric] = useState<PlanMetric | null>(null);
    const [showMetricModal, setShowMetricModal] = useState(false);
    const [metricForm, setMetricForm] = useState({
        yellow_min: '' as string,
        yellow_max: '' as string,
        red_min: '' as string,
        red_max: '' as string,
        qualitative_guidance: ''
    });
    const [savingMetric, setSavingMetric] = useState(false);
    const [metricError, setMetricError] = useState<string | null>(null);

    // Add metric state
    const [showAddMetricModal, setShowAddMetricModal] = useState(false);
    const [kpmCategories, setKpmCategories] = useState<KpmCategory[]>([]);
    const [addMetricForm, setAddMetricForm] = useState({
        kpm_id: 0,
        yellow_min: '' as string,
        yellow_max: '' as string,
        red_min: '' as string,
        red_max: '' as string,
        qualitative_guidance: '',
        sort_order: 0
    });
    const [addingMetric, setAddingMetric] = useState(false);
    const [addMetricError, setAddMetricError] = useState<string | null>(null);

    // Models state
    const [showAddModelModal, setShowAddModelModal] = useState(false);
    const [allModels, setAllModels] = useState<Model[]>([]);
    const [loadingAllModels, setLoadingAllModels] = useState(false);
    const [addingModel, setAddingModel] = useState(false);
    const [removingModelId, setRemovingModelId] = useState<number | null>(null);
    const [modelSearchTerm, setModelSearchTerm] = useState('');

    // Plan details editing state
    const [editingPlanDetails, setEditingPlanDetails] = useState(false);
    const [planDetailsForm, setPlanDetailsForm] = useState({
        data_provider_user_id: null as number | null,
        reporting_lead_days: 5,
        data_submission_lead_days: 15
    });
    const [savingPlanDetails, setSavingPlanDetails] = useState(false);
    const [availableUsers, setAvailableUsers] = useState<{ user_id: number; full_name: string }[]>([]);
    const [showUpdateCycleAssigneePrompt, setShowUpdateCycleAssigneePrompt] = useState(false);
    // Note: pendingDataProviderChange is for future integration with cycle hook
    const [, setPendingDataProviderChange] = useState<number | null>(null);

    // Fetch plan
    const fetchPlan = useCallback(async () => {
        if (!planId) return;
        setLoading(true);
        try {
            const response = await api.get(`/monitoring/plans/${planId}`);
            setPlan(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load plan');
        } finally {
            setLoading(false);
        }
    }, [planId]);

    // Fetch versions
    const fetchVersions = useCallback(async () => {
        if (!planId) return;
        setLoadingVersions(true);
        try {
            const response = await api.get(`/monitoring/plans/${planId}/versions`);
            setVersions(response.data);
        } catch (err) {
            console.error('Failed to load versions:', err);
        } finally {
            setLoadingVersions(false);
        }
    }, [planId]);

    // Fetch version detail
    const fetchVersionDetail = useCallback(async (versionId: number) => {
        if (!planId) return;
        setLoadingVersionDetail(true);
        try {
            const response = await api.get(`/monitoring/plans/${planId}/versions/${versionId}`);
            setSelectedVersionDetail(response.data);
        } catch (err) {
            console.error('Failed to load version detail:', err);
        } finally {
            setLoadingVersionDetail(false);
        }
    }, [planId]);

    // Publish version
    const handlePublishVersion = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!planId) return;
        setPublishing(true);
        setPublishError(null);

        try {
            await api.post(`/monitoring/plans/${planId}/versions/publish`, {
                version_name: publishForm.version_name || null,
                description: publishForm.description || null,
                effective_date: publishForm.effective_date
            });
            setShowPublishModal(false);
            setPublishForm({
                version_name: '',
                description: '',
                effective_date: new Date().toISOString().split('T')[0]
            });
            fetchVersions();
            fetchPlan();
        } catch (err: any) {
            setPublishError(err.response?.data?.detail || 'Failed to publish version');
        } finally {
            setPublishing(false);
        }
    }, [planId, publishForm, fetchVersions, fetchPlan]);

    // KPM categories fetch
    const fetchKpmCategories = useCallback(async () => {
        try {
            const response = await api.get('/kpm/categories?active_only=false');
            setKpmCategories(response.data);
        } catch (err) {
            console.error('Failed to load KPM categories:', err);
        }
    }, []);

    // Open edit metric modal
    const openEditMetric = useCallback((metric: PlanMetric) => {
        setEditingMetric(metric);
        setMetricForm({
            yellow_min: metric.yellow_min?.toString() || '',
            yellow_max: metric.yellow_max?.toString() || '',
            red_min: metric.red_min?.toString() || '',
            red_max: metric.red_max?.toString() || '',
            qualitative_guidance: metric.qualitative_guidance || ''
        });
        setMetricError(null);
        setShowMetricModal(true);
    }, []);

    const closeMetricModal = useCallback(() => {
        setShowMetricModal(false);
        setEditingMetric(null);
    }, []);

    // Save metric
    const handleSaveMetric = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingMetric || !planId) return;

        // Validate threshold consistency
        const yellowMin = metricForm.yellow_min ? parseFloat(metricForm.yellow_min) : null;
        const yellowMax = metricForm.yellow_max ? parseFloat(metricForm.yellow_max) : null;
        const redMin = metricForm.red_min ? parseFloat(metricForm.red_min) : null;
        const redMax = metricForm.red_max ? parseFloat(metricForm.red_max) : null;

        if (yellowMax !== null && redMax !== null && redMax <= yellowMax) {
            setMetricError(`Invalid threshold configuration: red_max (${redMax}) must be greater than yellow_max (${yellowMax}).`);
            return;
        }

        if (yellowMin !== null && redMin !== null && redMin >= yellowMin) {
            setMetricError(`Invalid threshold configuration: red_min (${redMin}) must be less than yellow_min (${yellowMin}).`);
            return;
        }

        setSavingMetric(true);
        setMetricError(null);

        try {
            await api.patch(`/monitoring/plans/${planId}/metrics/${editingMetric.metric_id}`, {
                yellow_min: yellowMin,
                yellow_max: yellowMax,
                red_min: redMin,
                red_max: redMax,
                qualitative_guidance: metricForm.qualitative_guidance || null
            });
            setShowMetricModal(false);
            setEditingMetric(null);
            fetchPlan();
        } catch (err: any) {
            setMetricError(err.response?.data?.detail || 'Failed to save metric');
        } finally {
            setSavingMetric(false);
        }
    }, [editingMetric, planId, metricForm, fetchPlan]);

    // Add metric
    const handleAddMetric = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!addMetricForm.kpm_id || !planId) {
            setAddMetricError('Please select a KPM');
            return;
        }

        setAddingMetric(true);
        setAddMetricError(null);

        try {
            await api.post(`/monitoring/plans/${planId}/metrics`, {
                kpm_id: addMetricForm.kpm_id,
                yellow_min: addMetricForm.yellow_min ? parseFloat(addMetricForm.yellow_min) : null,
                yellow_max: addMetricForm.yellow_max ? parseFloat(addMetricForm.yellow_max) : null,
                red_min: addMetricForm.red_min ? parseFloat(addMetricForm.red_min) : null,
                red_max: addMetricForm.red_max ? parseFloat(addMetricForm.red_max) : null,
                qualitative_guidance: addMetricForm.qualitative_guidance || null,
                sort_order: plan?.metrics?.length || 0,
                is_active: true
            });
            setShowAddMetricModal(false);
            setAddMetricForm({
                kpm_id: 0,
                yellow_min: '',
                yellow_max: '',
                red_min: '',
                red_max: '',
                qualitative_guidance: '',
                sort_order: 0
            });
            fetchPlan();
        } catch (err: any) {
            setAddMetricError(err.response?.data?.detail || 'Failed to add metric');
        } finally {
            setAddingMetric(false);
        }
    }, [addMetricForm, planId, plan?.metrics?.length, fetchPlan]);

    // Deactivate metric
    const handleDeactivateMetric = useCallback(async (metricId: number) => {
        if (!planId) return;
        if (!confirm('Deactivate this metric from the plan? It will be hidden but can be reactivated later.')) return;

        try {
            await api.patch(`/monitoring/plans/${planId}/metrics/${metricId}`, { is_active: false });
            fetchPlan();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to deactivate metric');
        }
    }, [planId, fetchPlan]);

    // Fetch all models
    const fetchAllModels = useCallback(async () => {
        setLoadingAllModels(true);
        try {
            const response = await api.get('/models/?limit=1000');
            setAllModels(response.data.items || response.data);
        } catch (err) {
            console.error('Failed to load models:', err);
        } finally {
            setLoadingAllModels(false);
        }
    }, []);

    // Open add model modal
    const openAddModelModal = useCallback(() => {
        setShowAddModelModal(true);
        setModelSearchTerm('');
        if (allModels.length === 0) {
            fetchAllModels();
        }
    }, [allModels.length, fetchAllModels]);

    // Add model to plan
    const handleAddModel = useCallback(async (modelId: number) => {
        if (!plan || !planId) return;
        setAddingModel(true);
        try {
            const currentModelIds = plan.models?.map(m => m.model_id) || [];
            const updatedModelIds = [...currentModelIds, modelId];
            await api.patch(`/monitoring/plans/${planId}`, {
                model_ids: updatedModelIds
            });
            await fetchPlan();
            setShowAddModelModal(false);
            setModelSearchTerm('');
        } catch (err: any) {
            console.error('Failed to add model:', err);
            alert(err.response?.data?.detail || 'Failed to add model');
        } finally {
            setAddingModel(false);
        }
    }, [plan, planId, fetchPlan]);

    // Remove model from plan
    const handleRemoveModel = useCallback(async (modelId: number) => {
        if (!plan || !planId) return;
        if (!window.confirm('Are you sure you want to remove this model from the plan?')) return;
        setRemovingModelId(modelId);
        try {
            const currentModelIds = plan.models?.map(m => m.model_id) || [];
            const updatedModelIds = currentModelIds.filter(id => id !== modelId);
            await api.patch(`/monitoring/plans/${planId}`, {
                model_ids: updatedModelIds
            });
            await fetchPlan();
        } catch (err: any) {
            console.error('Failed to remove model:', err);
            alert(err.response?.data?.detail || 'Failed to remove model');
        } finally {
            setRemovingModelId(null);
        }
    }, [plan, planId, fetchPlan]);

    // Available models (not already in plan)
    const availableModels = useMemo(() => {
        const planModelIds = new Set(plan?.models?.map(m => m.model_id) || []);
        return allModels.filter(m => !planModelIds.has(m.model_id));
    }, [allModels, plan?.models]);

    // Filtered available models
    const filteredAvailableModels = useMemo(() => {
        if (!modelSearchTerm.trim()) return availableModels;
        const term = modelSearchTerm.toLowerCase();
        return availableModels.filter(m =>
            m.model_name.toLowerCase().includes(term) ||
            m.model_id.toString().includes(term)
        );
    }, [availableModels, modelSearchTerm]);

    // Plan details editing
    const fetchAvailableUsers = useCallback(async () => {
        try {
            const response = await api.get('/auth/users');
            setAvailableUsers(response.data.map((u: any) => ({
                user_id: u.user_id,
                full_name: u.full_name
            })));
        } catch (err) {
            console.error('Failed to fetch users:', err);
        }
    }, []);

    const startEditingPlanDetails = useCallback(() => {
        if (plan) {
            setPlanDetailsForm({
                data_provider_user_id: plan.data_provider_user_id,
                reporting_lead_days: plan.reporting_lead_days,
                data_submission_lead_days: plan.data_submission_lead_days
            });
            fetchAvailableUsers();
            setEditingPlanDetails(true);
        }
    }, [plan, fetchAvailableUsers]);

    const cancelEditingPlanDetails = useCallback(() => {
        setEditingPlanDetails(false);
        setPlanDetailsForm({
            data_provider_user_id: null,
            reporting_lead_days: 5,
            data_submission_lead_days: 15
        });
    }, []);

    // This will need cycles from the cycle hook - for now, simplified version
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const handleSavePlanDetails = useCallback(async (_updateCycleAssignee: boolean = false) => {
        if (!plan || !planId) return;

        if (planDetailsForm.data_submission_lead_days >= planDetailsForm.reporting_lead_days) {
            alert('Data submission lead days must be less than reporting lead days.');
            return;
        }

        setSavingPlanDetails(true);

        try {
            await api.patch(`/monitoring/plans/${plan.plan_id}`, {
                data_provider_user_id: planDetailsForm.data_provider_user_id || 0,
                reporting_lead_days: planDetailsForm.reporting_lead_days,
                data_submission_lead_days: planDetailsForm.data_submission_lead_days
            });

            await fetchPlan();
            setEditingPlanDetails(false);
            setShowUpdateCycleAssigneePrompt(false);
            setPendingDataProviderChange(null);
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to update plan details');
        } finally {
            setSavingPlanDetails(false);
        }
    }, [plan, planId, planDetailsForm, fetchPlan]);

    const handleCycleAssigneePromptResponse = useCallback((updateAssignee: boolean) => {
        setShowUpdateCycleAssigneePrompt(false);
        handleSavePlanDetails(updateAssignee);
    }, [handleSavePlanDetails]);

    // Initial fetch
    useEffect(() => {
        if (planId) {
            fetchPlan();
        }
    }, [planId, fetchPlan]);

    // Fetch KPM categories when needed
    useEffect(() => {
        if (showAddMetricModal && kpmCategories.length === 0) {
            fetchKpmCategories();
        }
    }, [showAddMetricModal, kpmCategories.length, fetchKpmCategories]);

    return {
        // Plan
        plan,
        loading,
        error,
        fetchPlan,

        // Versions
        versions,
        loadingVersions,
        selectedVersionDetail,
        loadingVersionDetail,
        fetchVersions,
        fetchVersionDetail,

        // Publish
        showPublishModal,
        setShowPublishModal,
        publishForm,
        setPublishForm,
        publishing,
        publishError,
        handlePublishVersion,

        // Publish
        setPublishError,

        // Metric editing
        editingMetric,
        setEditingMetric,
        showMetricModal,
        setShowMetricModal,
        metricForm,
        setMetricForm,
        savingMetric,
        metricError,
        setMetricError,
        openEditMetric,
        closeMetricModal,
        handleSaveMetric,
        handleDeactivateMetric,

        // Add metric
        showAddMetricModal,
        setShowAddMetricModal,
        kpmCategories,
        addMetricForm,
        setAddMetricForm,
        addingMetric,
        addMetricError,
        setAddMetricError,
        handleAddMetric,

        // Models
        showAddModelModal,
        setShowAddModelModal,
        allModels,
        loadingAllModels,
        addingModel,
        removingModelId,
        modelSearchTerm,
        setModelSearchTerm,
        availableModels,
        filteredAvailableModels,
        openAddModelModal,
        handleAddModel,
        handleRemoveModel,

        // Plan details
        editingPlanDetails,
        setEditingPlanDetails,
        planDetailsForm,
        setPlanDetailsForm,
        savingPlanDetails,
        setSavingPlanDetails,
        availableUsers,
        startEditingPlanDetails,
        cancelEditingPlanDetails,
        handleSavePlanDetails,

        // Cycle assignee prompt
        showUpdateCycleAssigneePrompt,
        setShowUpdateCycleAssigneePrompt,
        handleCycleAssigneePromptResponse,
    };
}

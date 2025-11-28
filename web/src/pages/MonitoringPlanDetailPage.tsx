import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';

// Types
interface UserRef {
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
}

interface Model {
    model_id: number;
    model_name: string;
    model_id_str?: string;
}

interface PlanMetric {
    metric_id: number;
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
    is_active: boolean;
}

interface PlanVersion {
    version_id: number;
    version_number: number;
    version_name: string | null;
    effective_date: string;
    is_active: boolean;
}

interface MonitoringPlan {
    plan_id: number;
    name: string;
    description: string | null;
    frequency: string;
    is_active: boolean;
    next_submission_due_date: string | null;
    next_report_due_date: string | null;
    reporting_lead_days: number;
    monitoring_team_id: number | null;
    data_provider_user_id: number | null;
    team?: MonitoringTeam | null;
    data_provider?: UserRef | null;
    models?: Model[];
    metrics?: PlanMetric[];
    active_version_number?: number | null;
    version_count?: number;
}

interface MonitoringCycle {
    cycle_id: number;
    plan_id: number;
    period_start_date: string;
    period_end_date: string;
    submission_due_date: string;
    report_due_date: string;
    status: string;
    assigned_to_name?: string | null;
    plan_version_id?: number | null;
    version_number?: number | null;
    version_name?: string | null;
    version_locked_at?: string | null;
    result_count: number;
    green_count: number;
    yellow_count: number;
    red_count: number;
}

interface CycleApproval {
    approval_id: number;
    approval_type: string;
    region_id: number | null;
    region_name?: string | null;
    approval_status: string;
    approver_name?: string | null;
    approved_at?: string | null;
    comments?: string | null;
    is_required: boolean;
    voided_at?: string | null;
    void_reason?: string | null;
    can_approve: boolean;  // Server-calculated permission
}

interface CycleDetail extends MonitoringCycle {
    assigned_to?: UserRef | null;
    submitted_at?: string | null;
    submitted_by?: UserRef | null;
    completed_at?: string | null;
    completed_by?: UserRef | null;
    notes?: string | null;
    version_locked_at?: string | null;
    version_locked_by?: UserRef | null;
    approvals?: CycleApproval[];
    plan_version?: PlanVersion | null;
}

// Results Entry Types
interface MetricSnapshot {
    snapshot_id: number;
    original_metric_id: number | null;  // FK to MonitoringPlanMetric for result submission
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

interface VersionDetail {
    version_id: number;
    plan_id: number;
    version_number: number;
    version_name: string | null;
    effective_date: string;
    published_at: string;
    is_active: boolean;
    metric_snapshots: MetricSnapshot[];
}

interface OutcomeValue {
    value_id: number;
    code: string;
    label: string;
}

interface MonitoringResult {
    result_id: number;
    cycle_id: number;
    plan_metric_id: number;
    model_id: number | null;
    numeric_value: number | null;
    outcome_value: OutcomeValue | null;
    calculated_outcome: string | null;
    narrative: string | null;
    entered_by: UserRef;
    entered_at: string;
}

interface ResultFormData {
    metric_id: number;
    snapshot_id?: number;
    kpm_name: string;
    evaluation_type: string;
    numeric_value: string;
    outcome_value_id: number | null;
    narrative: string;
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
    qualitative_guidance: string | null;
    calculatedOutcome: string | null;
    existingResultId: number | null;
    dirty: boolean;
}

type TabType = 'overview' | 'models' | 'metrics' | 'cycles';

const MonitoringPlanDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const { user } = useAuth();
    const [loading, setLoading] = useState(true);
    const [plan, setPlan] = useState<MonitoringPlan | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<TabType>('cycles');

    // Cycles state
    const [cycles, setCycles] = useState<MonitoringCycle[]>([]);
    const [loadingCycles, setLoadingCycles] = useState(false);
    const [selectedCycle, setSelectedCycle] = useState<CycleDetail | null>(null);
    const [loadingCycleDetail, setLoadingCycleDetail] = useState(false);

    // Create cycle modal
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [creating, setCreating] = useState(false);
    const [createForm, setCreateForm] = useState({
        notes: ''
    });

    // Action state
    const [actionLoading, setActionLoading] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);

    // Results Entry state
    const [showResultsModal, setShowResultsModal] = useState(false);
    const [resultsEntryCycle, setResultsEntryCycle] = useState<MonitoringCycle | null>(null);
    const [versionDetail, setVersionDetail] = useState<VersionDetail | null>(null);
    const [outcomeValues, setOutcomeValues] = useState<OutcomeValue[]>([]);
    const [resultForms, setResultForms] = useState<ResultFormData[]>([]);
    const [loadingResults, setLoadingResults] = useState(false);
    const [savingResult, setSavingResult] = useState<number | null>(null);
    const [resultsError, setResultsError] = useState<string | null>(null);

    // Approval modal state
    const [approvalModalType, setApprovalModalType] = useState<'approve' | 'reject' | 'void' | null>(null);
    const [selectedApproval, setSelectedApproval] = useState<CycleApproval | null>(null);
    const [approvalComments, setApprovalComments] = useState('');
    const [approvalLoading, setApprovalLoading] = useState(false);
    const [approvalError, setApprovalError] = useState<string | null>(null);

    useEffect(() => {
        if (id) {
            fetchPlan();
            fetchCycles();
        }
    }, [id]);

    const fetchPlan = async () => {
        setLoading(true);
        try {
            const response = await api.get(`/monitoring/plans/${id}`);
            setPlan(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load plan');
        } finally {
            setLoading(false);
        }
    };

    const fetchCycles = async () => {
        setLoadingCycles(true);
        try {
            const response = await api.get(`/monitoring/plans/${id}/cycles`);
            setCycles(response.data);
        } catch (err) {
            console.error('Failed to load cycles:', err);
        } finally {
            setLoadingCycles(false);
        }
    };

    const fetchCycleDetail = async (cycleId: number) => {
        setLoadingCycleDetail(true);
        try {
            // Fetch cycle details and approvals in parallel
            const [cycleResponse, approvalsResponse] = await Promise.all([
                api.get(`/monitoring/cycles/${cycleId}`),
                api.get(`/monitoring/cycles/${cycleId}/approvals`)
            ]);

            // Map approvals to include region_name for display
            const approvals = approvalsResponse.data.map((a: any) => ({
                ...a,
                region_name: a.region?.region_name || null,
                approver_name: a.approver?.full_name || null
            }));

            // Merge cycle data with approvals
            setSelectedCycle({
                ...cycleResponse.data,
                approvals
            });
        } catch (err) {
            console.error('Failed to load cycle detail:', err);
        } finally {
            setLoadingCycleDetail(false);
        }
    };

    const handleCreateCycle = async (e: React.FormEvent) => {
        e.preventDefault();
        setCreating(true);
        setActionError(null);

        try {
            await api.post(`/monitoring/plans/${id}/cycles`, {
                notes: createForm.notes || null
            });
            setShowCreateModal(false);
            setCreateForm({ notes: '' });
            fetchCycles();
            fetchPlan(); // Refresh plan to get updated next_submission_due_date
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to create cycle');
        } finally {
            setCreating(false);
        }
    };

    const handleCycleAction = async (cycleId: number, action: string, payload?: object) => {
        setActionLoading(true);
        setActionError(null);

        try {
            await api.post(`/monitoring/cycles/${cycleId}/${action}`, payload || {});
            fetchCycles();
            if (selectedCycle?.cycle_id === cycleId) {
                fetchCycleDetail(cycleId);
            }
        } catch (err: any) {
            setActionError(err.response?.data?.detail || `Failed to ${action} cycle`);
        } finally {
            setActionLoading(false);
        }
    };

    // ========== Results Entry Functions ==========

    const openResultsEntry = async (cycle: MonitoringCycle) => {
        setResultsEntryCycle(cycle);
        setShowResultsModal(true);
        setLoadingResults(true);
        setResultsError(null);

        try {
            // Fetch outcome values for qualitative selection
            const outcomeResponse = await api.get('/taxonomies/');
            const taxonomies = outcomeResponse.data;
            const monitoringOutcomeTax = taxonomies.find((t: { code: string }) => t.code === 'MONITORING_OUTCOME');
            if (monitoringOutcomeTax) {
                const outcomeValResponse = await api.get(`/taxonomies/${monitoringOutcomeTax.taxonomy_id}/values`);
                setOutcomeValues(outcomeValResponse.data.filter((v: OutcomeValue & { is_active: boolean }) => v.is_active));
            }

            // Fetch existing results for this cycle
            const resultsResponse = await api.get(`/monitoring/cycles/${cycle.cycle_id}/results`);

            // Determine which metrics to show
            let metricsToShow: { metric_id: number; snapshot_id?: number; kpm_name: string; evaluation_type: string; yellow_min: number | null; yellow_max: number | null; red_min: number | null; red_max: number | null; qualitative_guidance: string | null }[] = [];

            // If cycle has a locked version, use the metric snapshots
            if (cycle.plan_version_id) {
                const versionResponse = await api.get(`/monitoring/plans/${id}/versions/${cycle.plan_version_id}`);
                setVersionDetail(versionResponse.data);
                metricsToShow = versionResponse.data.metric_snapshots.map((s: MetricSnapshot) => ({
                    metric_id: s.original_metric_id ?? s.snapshot_id,  // Use original_metric_id for result submission
                    snapshot_id: s.snapshot_id,
                    kpm_name: s.kpm_name,
                    evaluation_type: s.evaluation_type,
                    yellow_min: s.yellow_min,
                    yellow_max: s.yellow_max,
                    red_min: s.red_min,
                    red_max: s.red_max,
                    qualitative_guidance: s.qualitative_guidance
                }));
            } else if (plan?.metrics) {
                // Use live plan metrics (before version lock)
                setVersionDetail(null);
                metricsToShow = plan.metrics.filter(m => m.is_active).map(m => ({
                    metric_id: m.metric_id,
                    kpm_name: m.kpm_name,
                    evaluation_type: m.evaluation_type,
                    yellow_min: m.yellow_min,
                    yellow_max: m.yellow_max,
                    red_min: m.red_min,
                    red_max: m.red_max,
                    qualitative_guidance: m.qualitative_guidance
                }));
            }

            // Build form data for each metric
            const forms: ResultFormData[] = metricsToShow.map(m => {
                // Find existing result for this metric
                const existing = resultsResponse.data.find((r: MonitoringResult) =>
                    r.plan_metric_id === m.metric_id
                );

                return {
                    metric_id: m.metric_id,
                    snapshot_id: m.snapshot_id,
                    kpm_name: m.kpm_name,
                    evaluation_type: m.evaluation_type,
                    numeric_value: existing?.numeric_value?.toString() ?? '',
                    outcome_value_id: existing?.outcome_value?.value_id ?? null,
                    narrative: existing?.narrative ?? '',
                    yellow_min: m.yellow_min,
                    yellow_max: m.yellow_max,
                    red_min: m.red_min,
                    red_max: m.red_max,
                    qualitative_guidance: m.qualitative_guidance,
                    calculatedOutcome: existing?.calculated_outcome ?? null,
                    existingResultId: existing?.result_id ?? null,
                    dirty: false
                };
            });

            setResultForms(forms);
        } catch (err: any) {
            setResultsError(err.response?.data?.detail || 'Failed to load results data');
        } finally {
            setLoadingResults(false);
        }
    };

    const calculateOutcome = (value: number, metric: ResultFormData): string => {
        // Check red thresholds first (highest severity)
        if (metric.red_min !== null && value < metric.red_min) return 'RED';
        if (metric.red_max !== null && value > metric.red_max) return 'RED';
        // Check yellow thresholds
        if (metric.yellow_min !== null && value < metric.yellow_min) return 'YELLOW';
        if (metric.yellow_max !== null && value > metric.yellow_max) return 'YELLOW';
        // Passed all checks
        return 'GREEN';
    };

    const handleResultChange = (index: number, field: string, value: string | number | null) => {
        setResultForms(prev => {
            const updated = [...prev];
            const form = { ...updated[index], [field]: value, dirty: true };

            // Calculate outcome for quantitative metrics
            if (form.evaluation_type === 'Quantitative' && field === 'numeric_value' && value !== '') {
                const numValue = parseFloat(value as string);
                if (!isNaN(numValue)) {
                    form.calculatedOutcome = calculateOutcome(numValue, form);
                } else {
                    form.calculatedOutcome = null;
                }
            }

            // For qualitative/outcome-only, update calculated outcome from selected value
            if (field === 'outcome_value_id' && value !== null) {
                const selectedOutcome = outcomeValues.find(o => o.value_id === value);
                if (selectedOutcome) {
                    form.calculatedOutcome = selectedOutcome.code;
                }
            }

            updated[index] = form;
            return updated;
        });
    };

    const saveResult = async (index: number) => {
        const form = resultForms[index];
        if (!resultsEntryCycle) return;

        // Validate qualitative requires narrative
        if (form.evaluation_type === 'Qualitative' && !form.narrative.trim()) {
            setResultsError('Narrative is required for qualitative metrics');
            return;
        }

        setSavingResult(index);
        setResultsError(null);

        try {
            const payload: Record<string, unknown> = {
                plan_metric_id: form.metric_id,
                narrative: form.narrative || null
            };

            if (form.evaluation_type === 'Quantitative') {
                payload.numeric_value = form.numeric_value ? parseFloat(form.numeric_value) : null;
            } else {
                payload.outcome_value_id = form.outcome_value_id;
            }

            if (form.existingResultId) {
                // Update existing
                await api.patch(`/monitoring/results/${form.existingResultId}`, payload);
            } else {
                // Create new
                const response = await api.post(`/monitoring/cycles/${resultsEntryCycle.cycle_id}/results`, payload);
                // Update the form with the new result ID
                setResultForms(prev => {
                    const updated = [...prev];
                    updated[index] = { ...updated[index], existingResultId: response.data.result_id, dirty: false };
                    return updated;
                });
            }

            // Mark as saved
            setResultForms(prev => {
                const updated = [...prev];
                updated[index] = { ...updated[index], dirty: false };
                return updated;
            });

            // Refresh cycles to update counts
            fetchCycles();
        } catch (err: any) {
            setResultsError(err.response?.data?.detail || 'Failed to save result');
        } finally {
            setSavingResult(null);
        }
    };

    const getOutcomeColor = (outcome: string | null): string => {
        switch (outcome) {
            case 'GREEN': return 'bg-green-100 text-green-800 border-green-300';
            case 'YELLOW': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            case 'RED': return 'bg-red-100 text-red-800 border-red-300';
            default: return 'bg-gray-100 text-gray-600 border-gray-300';
        }
    };

    const getOutcomeIcon = (outcome: string | null): string => {
        switch (outcome) {
            case 'GREEN': return '●';
            case 'YELLOW': return '●';
            case 'RED': return '●';
            default: return '○';
        }
    };

    const canEnterResults = (cycle: MonitoringCycle): boolean => {
        return ['DATA_COLLECTION', 'UNDER_REVIEW'].includes(cycle.status);
    };

    const closeResultsModal = () => {
        setShowResultsModal(false);
        setResultsEntryCycle(null);
        setVersionDetail(null);
        setResultForms([]);
        setResultsError(null);
    };

    // ========== Approval Functions ==========

    const openApprovalModal = (approval: CycleApproval, type: 'approve' | 'reject' | 'void') => {
        setSelectedApproval(approval);
        setApprovalModalType(type);
        setApprovalComments('');
        setApprovalError(null);
    };

    const closeApprovalModal = () => {
        setApprovalModalType(null);
        setSelectedApproval(null);
        setApprovalComments('');
        setApprovalError(null);
    };

    const handleApprovalSubmit = async () => {
        if (!selectedApproval || !selectedCycle || !approvalModalType) return;

        // Validate rejection/void requires comments
        if ((approvalModalType === 'reject' || approvalModalType === 'void') && !approvalComments.trim()) {
            setApprovalError(`${approvalModalType === 'reject' ? 'Rejection reason' : 'Void reason'} is required`);
            return;
        }

        setApprovalLoading(true);
        setApprovalError(null);

        try {
            const endpoint = `/monitoring/cycles/${selectedCycle.cycle_id}/approvals/${selectedApproval.approval_id}/${approvalModalType}`;
            const payload = approvalModalType === 'void'
                ? { void_reason: approvalComments }
                : { comments: approvalComments || null };

            await api.post(endpoint, payload);

            // Refresh the cycle detail to get updated approvals
            await fetchCycleDetail(selectedCycle.cycle_id);

            // Also refresh the cycles list to update status if it changed
            fetchCycles();

            closeApprovalModal();
        } catch (err: any) {
            setApprovalError(err.response?.data?.detail || `Failed to ${approvalModalType} approval`);
        } finally {
            setApprovalLoading(false);
        }
    };

    const canApprove = (approval: CycleApproval): boolean => {
        // Use server-calculated permission which checks:
        // - Cycle is in PENDING_APPROVAL status
        // - Approval is pending and not voided
        // - User has permission (Admin, team member for Global, regional approver for Regional)
        return approval.can_approve;
    };

    const canVoid = (approval: CycleApproval): boolean => {
        // Admin only, and only for pending approvals
        if (user?.role !== 'Admin') return false;
        if (approval.approval_status === 'Approved') return false;
        if (approval.voided_at) return false;
        return true;
    };

    const getApprovalProgress = (approvals: CycleApproval[]): { completed: number; total: number } => {
        const required = approvals.filter(a => a.is_required && !a.voided_at);
        const completed = required.filter(a => a.approval_status === 'Approved');
        return { completed: completed.length, total: required.length };
    };

    const getStatusBadgeColor = (status: string) => {
        switch (status) {
            case 'PENDING':
                return 'bg-gray-100 text-gray-800';
            case 'DATA_COLLECTION':
                return 'bg-blue-100 text-blue-800';
            case 'UNDER_REVIEW':
                return 'bg-yellow-100 text-yellow-800';
            case 'PENDING_APPROVAL':
                return 'bg-purple-100 text-purple-800';
            case 'APPROVED':
                return 'bg-green-100 text-green-800';
            case 'CANCELLED':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const formatStatus = (status: string) => {
        return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    };

    const formatPeriod = (start: string, end: string) => {
        const startDate = new Date(start);
        const endDate = new Date(end);
        const startMonth = startDate.toLocaleString('default', { month: 'short' });
        const endMonth = endDate.toLocaleString('default', { month: 'short' });
        const year = endDate.getFullYear();
        return `${startMonth} - ${endMonth} ${year}`;
    };

    const canCreateCycle = user?.role === 'Admin' ||
        (plan?.team?.team_id && plan.data_provider?.user_id === user?.user_id);

    const getAvailableActions = (cycle: MonitoringCycle | CycleDetail) => {
        const actions: { label: string; action: string; variant: string; requiresConfirm?: boolean }[] = [];

        switch (cycle.status) {
            case 'PENDING':
                actions.push({ label: 'Start Data Collection', action: 'start', variant: 'primary' });
                break;
            case 'DATA_COLLECTION':
                actions.push({ label: 'Submit for Review', action: 'submit', variant: 'primary' });
                break;
            case 'UNDER_REVIEW':
                actions.push({ label: 'Request Approval', action: 'request-approval', variant: 'primary' });
                break;
        }

        if (cycle.status !== 'APPROVED' && cycle.status !== 'CANCELLED') {
            actions.push({ label: 'Cancel Cycle', action: 'cancel', variant: 'danger', requiresConfirm: true });
        }

        return actions;
    };

    if (loading) {
        return (
            <Layout>
                <div className="text-center py-12">Loading...</div>
            </Layout>
        );
    }

    if (error || !plan) {
        return (
            <Layout>
                <div className="text-center py-12">
                    <h2 className="text-2xl font-bold text-red-600">Error</h2>
                    <p className="text-gray-600 mt-2">{error || 'Plan not found'}</p>
                    <Link to="/monitoring-plans" className="text-blue-600 hover:underline mt-4 inline-block">
                        Back to Monitoring Plans
                    </Link>
                </div>
            </Layout>
        );
    }

    const currentCycle = cycles.find(c => c.status !== 'APPROVED' && c.status !== 'CANCELLED');
    const previousCycles = cycles.filter(c => c.status === 'APPROVED' || c.status === 'CANCELLED');

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex justify-between items-start">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <Link to="/monitoring-plans" className="text-blue-600 hover:underline text-sm">
                                Monitoring Plans
                            </Link>
                            <span className="text-gray-400">/</span>
                            <span className="text-gray-600">{plan.name}</span>
                        </div>
                        <h1 className="text-2xl font-bold">{plan.name}</h1>
                        {plan.description && (
                            <p className="text-gray-600 mt-1">{plan.description}</p>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        <span className={`px-3 py-1 rounded-full text-sm ${
                            plan.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                            {plan.is_active ? 'Active' : 'Inactive'}
                        </span>
                        {plan.active_version_number && (
                            <span className="px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800">
                                v{plan.active_version_number}
                            </span>
                        )}
                    </div>
                </div>

                {/* Plan Summary Cards */}
                <div className="grid grid-cols-4 gap-4">
                    <div className="bg-white rounded-lg border p-4">
                        <div className="text-sm text-gray-500">Frequency</div>
                        <div className="text-lg font-semibold">{plan.frequency}</div>
                    </div>
                    <div className="bg-white rounded-lg border p-4">
                        <div className="text-sm text-gray-500">Team</div>
                        <div className="text-lg font-semibold">{plan.team?.name || '-'}</div>
                    </div>
                    <div className="bg-white rounded-lg border p-4">
                        <div className="text-sm text-gray-500">Models</div>
                        <div className="text-lg font-semibold">{plan.models?.length || 0}</div>
                    </div>
                    <div className="bg-white rounded-lg border p-4">
                        <div className="text-sm text-gray-500">Metrics</div>
                        <div className="text-lg font-semibold">{plan.metrics?.length || 0}</div>
                    </div>
                </div>

                {/* Tabs */}
                <div className="border-b">
                    <nav className="flex gap-6">
                        {(['overview', 'models', 'metrics', 'cycles'] as TabType[]).map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`py-3 px-1 border-b-2 font-medium text-sm capitalize ${
                                    activeTab === tab
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                            >
                                {tab}
                            </button>
                        ))}
                    </nav>
                </div>

                {/* Tab Content */}
                <div className="bg-white rounded-lg border p-6">
                    {/* Overview Tab */}
                    {activeTab === 'overview' && (
                        <div className="space-y-6">
                            <h3 className="text-lg font-semibold">Plan Details</h3>
                            <div className="grid grid-cols-2 gap-6">
                                <div>
                                    <label className="text-sm text-gray-500">Data Provider</label>
                                    <p className="font-medium">{plan.data_provider?.full_name || '-'}</p>
                                </div>
                                <div>
                                    <label className="text-sm text-gray-500">Reporting Lead Days</label>
                                    <p className="font-medium">{plan.reporting_lead_days} days</p>
                                </div>
                                <div>
                                    <label className="text-sm text-gray-500">Next Submission Due</label>
                                    <p className="font-medium">{plan.next_submission_due_date || '-'}</p>
                                </div>
                                <div>
                                    <label className="text-sm text-gray-500">Next Report Due</label>
                                    <p className="font-medium">{plan.next_report_due_date || '-'}</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Models Tab */}
                    {activeTab === 'models' && (
                        <div>
                            <h3 className="text-lg font-semibold mb-4">Covered Models ({plan.models?.length || 0})</h3>
                            {!plan.models?.length ? (
                                <p className="text-gray-500">No models assigned to this plan.</p>
                            ) : (
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Model ID</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Model Name</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200">
                                        {plan.models.map((model) => (
                                            <tr key={model.model_id} className="hover:bg-gray-50">
                                                <td className="px-4 py-2 text-sm">{model.model_id_str || model.model_id}</td>
                                                <td className="px-4 py-2 text-sm">
                                                    <Link to={`/models/${model.model_id}`} className="text-blue-600 hover:underline">
                                                        {model.model_name}
                                                    </Link>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    )}

                    {/* Metrics Tab */}
                    {activeTab === 'metrics' && (
                        <div>
                            <h3 className="text-lg font-semibold mb-4">Configured Metrics ({plan.metrics?.length || 0})</h3>
                            {!plan.metrics?.length ? (
                                <p className="text-gray-500">No metrics configured for this plan.</p>
                            ) : (
                                <table className="min-w-full divide-y divide-gray-200 text-sm">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">KPM</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Thresholds</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200">
                                        {plan.metrics.map((metric) => (
                                            <tr key={metric.metric_id} className="hover:bg-gray-50">
                                                <td className="px-4 py-2">{metric.kpm_name}</td>
                                                <td className="px-4 py-2 text-gray-600">{metric.kpm_category_name || '-'}</td>
                                                <td className="px-4 py-2">
                                                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                                                        metric.evaluation_type === 'Quantitative' ? 'bg-blue-100 text-blue-800' :
                                                        metric.evaluation_type === 'Qualitative' ? 'bg-purple-100 text-purple-800' :
                                                        'bg-green-100 text-green-800'
                                                    }`}>
                                                        {metric.evaluation_type}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-2">
                                                    {metric.evaluation_type === 'Quantitative' ? (
                                                        <div className="flex gap-1">
                                                            <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs">
                                                                Y: {metric.yellow_min ?? '-'}/{metric.yellow_max ?? '-'}
                                                            </span>
                                                            <span className="px-1.5 py-0.5 bg-red-100 text-red-800 rounded text-xs">
                                                                R: {metric.red_min ?? '-'}/{metric.red_max ?? '-'}
                                                            </span>
                                                        </div>
                                                    ) : (
                                                        <span className="text-xs text-gray-500 italic">Judgment-based</span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    )}

                    {/* Cycles Tab */}
                    {activeTab === 'cycles' && (
                        <div className="space-y-6">
                            {/* Action Error */}
                            {actionError && (
                                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                                    {actionError}
                                </div>
                            )}

                            {/* Current Cycle */}
                            <div>
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="text-lg font-semibold">Current Cycle</h3>
                                    {canCreateCycle && !currentCycle && (
                                        <button
                                            onClick={() => setShowCreateModal(true)}
                                            className="btn-primary"
                                        >
                                            + New Cycle
                                        </button>
                                    )}
                                </div>

                                {loadingCycles ? (
                                    <div className="text-center py-8 text-gray-500">Loading cycles...</div>
                                ) : !currentCycle ? (
                                    <div className="bg-gray-50 rounded-lg p-6 text-center">
                                        <p className="text-gray-600">No active cycle.</p>
                                        {!plan.active_version_number && (
                                            <p className="text-amber-600 text-sm mt-2">
                                                Note: A published plan version is required before starting a cycle.
                                            </p>
                                        )}
                                    </div>
                                ) : (
                                    <div className="border rounded-lg p-6 bg-blue-50 border-blue-200">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <div className="flex items-center gap-3 mb-2">
                                                    <span className="text-xl font-bold">
                                                        {formatPeriod(currentCycle.period_start_date, currentCycle.period_end_date)}
                                                    </span>
                                                    <span className={`px-3 py-1 rounded-full text-sm ${getStatusBadgeColor(currentCycle.status)}`}>
                                                        {formatStatus(currentCycle.status)}
                                                    </span>
                                                </div>
                                                <div className="grid grid-cols-2 gap-4 text-sm">
                                                    <div>
                                                        <span className="text-gray-500">Submission Due:</span>{' '}
                                                        <span className="font-medium">{currentCycle.submission_due_date}</span>
                                                    </div>
                                                    <div>
                                                        <span className="text-gray-500">Report Due:</span>{' '}
                                                        <span className="font-medium">{currentCycle.report_due_date}</span>
                                                    </div>
                                                    {currentCycle.assigned_to_name && (
                                                        <div>
                                                            <span className="text-gray-500">Assigned to:</span>{' '}
                                                            <span className="font-medium">{currentCycle.assigned_to_name}</span>
                                                        </div>
                                                    )}
                                                    {currentCycle.version_number && (
                                                        <div>
                                                            <span className="text-gray-500">Using:</span>{' '}
                                                            <span className="font-medium">v{currentCycle.version_number} metrics</span>
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Results Summary */}
                                                {currentCycle.result_count > 0 && (
                                                    <div className="mt-4">
                                                        <span className="text-gray-500 text-sm">Results:</span>
                                                        <div className="flex items-center gap-2 mt-1">
                                                            <span className="text-sm">{currentCycle.result_count} / {plan.metrics?.length || 0} metrics</span>
                                                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-800 rounded text-sm">
                                                                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                                                {currentCycle.green_count}
                                                            </span>
                                                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded text-sm">
                                                                <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
                                                                {currentCycle.yellow_count}
                                                            </span>
                                                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-800 rounded text-sm">
                                                                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                                                {currentCycle.red_count}
                                                            </span>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Actions */}
                                            <div className="flex flex-col gap-2">
                                                {getAvailableActions(currentCycle).map((action) => (
                                                    <button
                                                        key={action.action}
                                                        onClick={() => {
                                                            if (action.requiresConfirm) {
                                                                if (window.confirm(`Are you sure you want to ${action.label.toLowerCase()}?`)) {
                                                                    handleCycleAction(currentCycle.cycle_id, action.action);
                                                                }
                                                            } else {
                                                                handleCycleAction(currentCycle.cycle_id, action.action);
                                                            }
                                                        }}
                                                        disabled={actionLoading}
                                                        className={`px-4 py-2 rounded text-sm font-medium ${
                                                            action.variant === 'primary' ? 'bg-blue-600 text-white hover:bg-blue-700' :
                                                            action.variant === 'danger' ? 'bg-red-600 text-white hover:bg-red-700' :
                                                            'bg-gray-200 text-gray-800 hover:bg-gray-300'
                                                        } disabled:opacity-50`}
                                                    >
                                                        {actionLoading ? 'Processing...' : action.label}
                                                    </button>
                                                ))}
                                                {canEnterResults(currentCycle) && (
                                                    <button
                                                        onClick={() => openResultsEntry(currentCycle)}
                                                        className="px-4 py-2 rounded text-sm font-medium bg-green-600 text-white hover:bg-green-700"
                                                    >
                                                        Enter Results
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => fetchCycleDetail(currentCycle.cycle_id)}
                                                    className="px-4 py-2 rounded text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
                                                >
                                                    View Details
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Previous Cycles */}
                            <div>
                                <h3 className="text-lg font-semibold mb-4">Previous Cycles</h3>
                                {previousCycles.length === 0 ? (
                                    <p className="text-gray-500">No completed cycles yet.</p>
                                ) : (
                                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Version</th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Results</th>
                                                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-200">
                                            {previousCycles.map((cycle) => (
                                                <tr key={cycle.cycle_id} className="hover:bg-gray-50">
                                                    <td className="px-4 py-3">
                                                        {formatPeriod(cycle.period_start_date, cycle.period_end_date)}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        {cycle.version_number ? `v${cycle.version_number}` : '-'}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className={`px-2 py-1 rounded-full text-xs ${getStatusBadgeColor(cycle.status)}`}>
                                                            {formatStatus(cycle.status)}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <div className="flex items-center gap-1">
                                                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-green-100 text-green-800 rounded text-xs">
                                                                <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                                                                {cycle.green_count}
                                                            </span>
                                                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs">
                                                                <span className="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>
                                                                {cycle.yellow_count}
                                                            </span>
                                                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-100 text-red-800 rounded text-xs">
                                                                <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                                                                {cycle.red_count}
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3 text-right">
                                                        <button
                                                            onClick={() => fetchCycleDetail(cycle.cycle_id)}
                                                            className="text-blue-600 hover:underline text-sm"
                                                        >
                                                            View
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Cycle Detail Modal */}
                {selectedCycle && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
                            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
                                <h3 className="text-lg font-bold">
                                    Cycle Details: {formatPeriod(selectedCycle.period_start_date, selectedCycle.period_end_date)}
                                </h3>
                                <button onClick={() => setSelectedCycle(null)} className="text-gray-500 hover:text-gray-700">
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>

                            <div className="p-6 overflow-y-auto max-h-[70vh]">
                                {loadingCycleDetail ? (
                                    <div className="text-center py-8">Loading...</div>
                                ) : (
                                    <div className="space-y-6">
                                        {/* Status & Version */}
                                        <div className="flex items-center gap-3">
                                            <span className={`px-3 py-1 rounded-full text-sm ${getStatusBadgeColor(selectedCycle.status)}`}>
                                                {formatStatus(selectedCycle.status)}
                                            </span>
                                            {selectedCycle.plan_version && (
                                                <span className="px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800">
                                                    v{selectedCycle.plan_version.version_number} metrics
                                                    {selectedCycle.version_locked_at && (
                                                        <span className="text-blue-600 ml-1">
                                                            (locked {selectedCycle.version_locked_at.split('T')[0]})
                                                        </span>
                                                    )}
                                                </span>
                                            )}
                                        </div>

                                        {/* Details Grid */}
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="text-sm text-gray-500">Period</label>
                                                <p className="font-medium">{selectedCycle.period_start_date} to {selectedCycle.period_end_date}</p>
                                            </div>
                                            <div>
                                                <label className="text-sm text-gray-500">Submission Due</label>
                                                <p className="font-medium">{selectedCycle.submission_due_date}</p>
                                            </div>
                                            <div>
                                                <label className="text-sm text-gray-500">Report Due</label>
                                                <p className="font-medium">{selectedCycle.report_due_date}</p>
                                            </div>
                                            <div>
                                                <label className="text-sm text-gray-500">Assigned To</label>
                                                <p className="font-medium">{selectedCycle.assigned_to?.full_name || '-'}</p>
                                            </div>
                                            {selectedCycle.submitted_at && (
                                                <div>
                                                    <label className="text-sm text-gray-500">Submitted</label>
                                                    <p className="font-medium">
                                                        {selectedCycle.submitted_at.split('T')[0]} by {selectedCycle.submitted_by?.full_name || 'Unknown'}
                                                    </p>
                                                </div>
                                            )}
                                            {selectedCycle.completed_at && (
                                                <div>
                                                    <label className="text-sm text-gray-500">Completed</label>
                                                    <p className="font-medium">
                                                        {selectedCycle.completed_at.split('T')[0]} by {selectedCycle.completed_by?.full_name || 'Unknown'}
                                                    </p>
                                                </div>
                                            )}
                                        </div>

                                        {/* Notes */}
                                        {selectedCycle.notes && (
                                            <div>
                                                <label className="text-sm text-gray-500">Notes</label>
                                                <p className="mt-1 text-gray-700">{selectedCycle.notes}</p>
                                            </div>
                                        )}

                                        {/* Approvals */}
                                        {selectedCycle.approvals && selectedCycle.approvals.length > 0 && (
                                            <div>
                                                <div className="flex items-center justify-between mb-3">
                                                    <h4 className="font-semibold">Approvals</h4>
                                                    {/* Progress Indicator */}
                                                    {(() => {
                                                        const progress = getApprovalProgress(selectedCycle.approvals);
                                                        return (
                                                            <div className="flex items-center gap-2">
                                                                <span className={`text-sm ${
                                                                    progress.completed === progress.total
                                                                        ? 'text-green-600 font-medium'
                                                                        : 'text-gray-600'
                                                                }`}>
                                                                    {progress.completed} / {progress.total} Complete
                                                                </span>
                                                                <div className="w-24 bg-gray-200 rounded-full h-2">
                                                                    <div
                                                                        className={`h-2 rounded-full transition-all ${
                                                                            progress.completed === progress.total
                                                                                ? 'bg-green-500'
                                                                                : 'bg-blue-500'
                                                                        }`}
                                                                        style={{ width: progress.total > 0 ? `${(progress.completed / progress.total) * 100}%` : '0%' }}
                                                                    />
                                                                </div>
                                                            </div>
                                                        );
                                                    })()}
                                                </div>
                                                <div className="space-y-2">
                                                    {selectedCycle.approvals.map((approval) => (
                                                        <div key={approval.approval_id} className={`p-3 rounded-lg border ${
                                                            approval.approval_status === 'Approved' ? 'bg-green-50 border-green-200' :
                                                            approval.approval_status === 'Rejected' ? 'bg-red-50 border-red-200' :
                                                            approval.voided_at ? 'bg-gray-50 border-gray-200' :
                                                            'bg-yellow-50 border-yellow-200'
                                                        }`}>
                                                            <div className="flex items-center justify-between">
                                                                <div className="flex-1">
                                                                    <div className="flex items-center gap-2">
                                                                        <span className="font-medium">
                                                                            {approval.approval_type === 'Global' ? 'Global Approval' : `${approval.region_name || 'Regional'} Approval`}
                                                                        </span>
                                                                        <span className={`px-2 py-0.5 rounded text-xs ${
                                                                            approval.approval_status === 'Approved' ? 'bg-green-100 text-green-800' :
                                                                            approval.approval_status === 'Rejected' ? 'bg-red-100 text-red-800' :
                                                                            approval.voided_at ? 'bg-gray-100 text-gray-600' :
                                                                            'bg-yellow-100 text-yellow-800'
                                                                        }`}>
                                                                            {approval.voided_at ? 'Voided' : approval.approval_status}
                                                                        </span>
                                                                    </div>
                                                                    {/* Approval details */}
                                                                    {approval.approver_name && (
                                                                        <p className="text-sm text-gray-600 mt-1">
                                                                            {approval.approval_status === 'Approved' ? 'Approved' : 'Processed'} by {approval.approver_name}
                                                                            {approval.approved_at && ` on ${approval.approved_at.split('T')[0]}`}
                                                                        </p>
                                                                    )}
                                                                    {approval.comments && (
                                                                        <p className="text-sm text-gray-700 mt-1 italic">"{approval.comments}"</p>
                                                                    )}
                                                                    {approval.voided_at && approval.void_reason && (
                                                                        <p className="text-sm text-gray-600 mt-1">
                                                                            <span className="font-medium">Void reason:</span> {approval.void_reason}
                                                                        </p>
                                                                    )}
                                                                </div>
                                                                {/* Action buttons */}
                                                                <div className="flex items-center gap-2 ml-4">
                                                                    {canApprove(approval) && (
                                                                        <>
                                                                            <button
                                                                                onClick={() => openApprovalModal(approval, 'approve')}
                                                                                className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                                                                            >
                                                                                Approve
                                                                            </button>
                                                                            <button
                                                                                onClick={() => openApprovalModal(approval, 'reject')}
                                                                                className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                                                                            >
                                                                                Reject
                                                                            </button>
                                                                        </>
                                                                    )}
                                                                    {canVoid(approval) && (
                                                                        <button
                                                                            onClick={() => openApprovalModal(approval, 'void')}
                                                                            className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                                                                        >
                                                                            Void
                                                                        </button>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            <div className="p-4 border-t bg-gray-50 flex justify-end">
                                <button onClick={() => setSelectedCycle(null)} className="btn-secondary">
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Create Cycle Modal */}
                {showCreateModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
                            <div className="p-4 border-b">
                                <h3 className="text-lg font-bold">Create New Cycle</h3>
                            </div>

                            <form onSubmit={handleCreateCycle}>
                                <div className="p-4 space-y-4">
                                    {actionError && (
                                        <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                                            {actionError}
                                        </div>
                                    )}

                                    {!plan.active_version_number && (
                                        <div className="bg-amber-50 border border-amber-300 rounded-lg p-3">
                                            <p className="text-amber-800 text-sm">
                                                <strong>Warning:</strong> No published plan version exists.
                                                You will not be able to start data collection until a version is published.
                                            </p>
                                        </div>
                                    )}

                                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                        <p className="text-sm text-blue-800">
                                            <strong>Next Period:</strong> Based on plan frequency ({plan.frequency}),
                                            the next cycle will be automatically calculated.
                                        </p>
                                        <p className="text-sm text-blue-700 mt-1">
                                            <strong>Submission Due:</strong> {plan.next_submission_due_date || 'TBD'}
                                        </p>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Notes (optional)
                                        </label>
                                        <textarea
                                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                            rows={3}
                                            value={createForm.notes}
                                            onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
                                            placeholder="Any notes for this cycle..."
                                        />
                                    </div>
                                </div>

                                <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowCreateModal(false);
                                            setActionError(null);
                                        }}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={creating}
                                        className="btn-primary disabled:opacity-50"
                                    >
                                        {creating ? 'Creating...' : 'Create Cycle'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* Results Entry Modal */}
                {showResultsModal && resultsEntryCycle && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
                            <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
                                <div>
                                    <h3 className="text-lg font-bold">Enter Results</h3>
                                    <p className="text-sm text-gray-600">
                                        {formatPeriod(resultsEntryCycle.period_start_date, resultsEntryCycle.period_end_date)}
                                    </p>
                                </div>
                                <button onClick={closeResultsModal} className="text-gray-500 hover:text-gray-700">
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>

                            {/* Version Info Banner */}
                            {versionDetail && (
                                <div className="px-4 py-3 bg-blue-50 border-b border-blue-200">
                                    <div className="flex items-center gap-2">
                                        <span className="text-blue-600 font-medium">
                                            Using v{versionDetail.version_number} metrics configuration
                                        </span>
                                        {resultsEntryCycle.version_locked_at && (
                                            <span className="text-blue-500 text-sm">
                                                (locked {resultsEntryCycle.version_locked_at.split('T')[0]})
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-sm text-blue-600">
                                        Effective: {versionDetail.effective_date} | {versionDetail.metric_snapshots.length} metrics
                                    </p>
                                </div>
                            )}

                            {!versionDetail && !loadingResults && (
                                <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
                                    <p className="text-amber-700 text-sm">
                                        Using live plan metrics (not yet locked to a version)
                                    </p>
                                </div>
                            )}

                            {/* Error display */}
                            {resultsError && (
                                <div className="px-4 py-3 bg-red-100 border-b border-red-300">
                                    <p className="text-red-700 text-sm">{resultsError}</p>
                                </div>
                            )}

                            {/* Metrics List */}
                            <div className="flex-1 overflow-y-auto p-4">
                                {loadingResults ? (
                                    <div className="text-center py-12 text-gray-500">Loading metrics...</div>
                                ) : resultForms.length === 0 ? (
                                    <div className="text-center py-12 text-gray-500">No metrics configured for this plan.</div>
                                ) : (
                                    <div className="space-y-6">
                                        {/* Progress indicator */}
                                        <div className="flex items-center gap-4 mb-4">
                                            <span className="text-sm text-gray-600">
                                                Progress: {resultForms.filter(f => f.existingResultId !== null).length} / {resultForms.length} entered
                                            </span>
                                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                                                <div
                                                    className="bg-green-500 h-2 rounded-full transition-all"
                                                    style={{ width: `${(resultForms.filter(f => f.existingResultId !== null).length / resultForms.length) * 100}%` }}
                                                />
                                            </div>
                                        </div>

                                        {resultForms.map((form, index) => (
                                            <div key={form.metric_id} className="border rounded-lg p-4 bg-white shadow-sm">
                                                <div className="flex justify-between items-start mb-4">
                                                    <div>
                                                        <h4 className="font-semibold text-lg">{form.kpm_name}</h4>
                                                        <span className={`inline-block mt-1 px-2 py-0.5 text-xs rounded-full ${
                                                            form.evaluation_type === 'Quantitative' ? 'bg-blue-100 text-blue-800' :
                                                            form.evaluation_type === 'Qualitative' ? 'bg-purple-100 text-purple-800' :
                                                            'bg-green-100 text-green-800'
                                                        }`}>
                                                            {form.evaluation_type}
                                                        </span>
                                                    </div>
                                                    <div className={`px-3 py-1.5 rounded-lg border text-sm font-medium ${getOutcomeColor(form.calculatedOutcome)}`}>
                                                        <span className="mr-1">{getOutcomeIcon(form.calculatedOutcome)}</span>
                                                        {form.calculatedOutcome || 'Not Set'}
                                                    </div>
                                                </div>

                                                {/* Quantitative Metric */}
                                                {form.evaluation_type === 'Quantitative' && (
                                                    <div className="space-y-3">
                                                        {/* Threshold Visualization */}
                                                        <div className="bg-gray-50 rounded-lg p-3">
                                                            <div className="text-sm text-gray-600 mb-2">Thresholds:</div>
                                                            <div className="flex flex-wrap gap-2">
                                                                <span className="inline-flex items-center px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                                                                    <span className="w-2 h-2 rounded-full bg-green-500 mr-1"></span>
                                                                    Green: {form.yellow_min !== null || form.yellow_max !== null ? (
                                                                        <>
                                                                            {form.yellow_min !== null ? `>${form.yellow_min}` : ''}
                                                                            {form.yellow_min !== null && form.yellow_max !== null ? ' and ' : ''}
                                                                            {form.yellow_max !== null ? `<${form.yellow_max}` : ''}
                                                                        </>
                                                                    ) : 'Default'}
                                                                </span>
                                                                {(form.yellow_min !== null || form.yellow_max !== null) && (
                                                                    <span className="inline-flex items-center px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
                                                                        <span className="w-2 h-2 rounded-full bg-yellow-500 mr-1"></span>
                                                                        Yellow: {form.yellow_min ?? '-'} to {form.yellow_max ?? '-'}
                                                                    </span>
                                                                )}
                                                                {(form.red_min !== null || form.red_max !== null) && (
                                                                    <span className="inline-flex items-center px-2 py-1 bg-red-100 text-red-800 rounded text-xs">
                                                                        <span className="w-2 h-2 rounded-full bg-red-500 mr-1"></span>
                                                                        Red: {form.red_min !== null ? `<${form.red_min}` : ''}{form.red_min !== null && form.red_max !== null ? ' or ' : ''}{form.red_max !== null ? `>${form.red_max}` : ''}
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>

                                                        {/* Value Input */}
                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">Value</label>
                                                            <input
                                                                type="number"
                                                                step="any"
                                                                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                                                                value={form.numeric_value}
                                                                onChange={(e) => handleResultChange(index, 'numeric_value', e.target.value)}
                                                                placeholder="Enter numeric value..."
                                                            />
                                                        </div>

                                                        {/* Notes */}
                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
                                                            <textarea
                                                                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                                rows={2}
                                                                value={form.narrative}
                                                                onChange={(e) => handleResultChange(index, 'narrative', e.target.value)}
                                                                placeholder="Any supporting notes..."
                                                            />
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Qualitative Metric */}
                                                {form.evaluation_type === 'Qualitative' && (
                                                    <div className="space-y-3">
                                                        {form.qualitative_guidance && (
                                                            <div className="bg-gray-50 rounded-lg p-3">
                                                                <div className="text-sm text-gray-600 mb-1">Guidance:</div>
                                                                <p className="text-sm">{form.qualitative_guidance}</p>
                                                            </div>
                                                        )}

                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">Outcome</label>
                                                            <select
                                                                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                                                                value={form.outcome_value_id || ''}
                                                                onChange={(e) => handleResultChange(index, 'outcome_value_id', e.target.value ? parseInt(e.target.value) : null)}
                                                            >
                                                                <option value="">Select outcome...</option>
                                                                {outcomeValues.map(o => (
                                                                    <option key={o.value_id} value={o.value_id}>{o.label}</option>
                                                                ))}
                                                            </select>
                                                        </div>

                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                Rationale <span className="text-red-500">*</span>
                                                            </label>
                                                            <textarea
                                                                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                                rows={3}
                                                                value={form.narrative}
                                                                onChange={(e) => handleResultChange(index, 'narrative', e.target.value)}
                                                                placeholder="Required: Explain the rationale for this outcome..."
                                                            />
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Outcome Only Metric */}
                                                {form.evaluation_type === 'Outcome Only' && (
                                                    <div className="space-y-3">
                                                        {form.qualitative_guidance && (
                                                            <div className="bg-gray-50 rounded-lg p-3">
                                                                <div className="text-sm text-gray-600 mb-1">Guidance:</div>
                                                                <p className="text-sm">{form.qualitative_guidance}</p>
                                                            </div>
                                                        )}

                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">Outcome</label>
                                                            <select
                                                                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                                                                value={form.outcome_value_id || ''}
                                                                onChange={(e) => handleResultChange(index, 'outcome_value_id', e.target.value ? parseInt(e.target.value) : null)}
                                                            >
                                                                <option value="">Select outcome...</option>
                                                                {outcomeValues.map(o => (
                                                                    <option key={o.value_id} value={o.value_id}>{o.label}</option>
                                                                ))}
                                                            </select>
                                                        </div>

                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
                                                            <textarea
                                                                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                                rows={2}
                                                                value={form.narrative}
                                                                onChange={(e) => handleResultChange(index, 'narrative', e.target.value)}
                                                                placeholder="Any supporting notes..."
                                                            />
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Save Button */}
                                                <div className="mt-4 flex justify-between items-center">
                                                    <div className="flex items-center gap-2">
                                                        {form.existingResultId && !form.dirty && (
                                                            <span className="text-green-600 text-sm flex items-center gap-1">
                                                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                                </svg>
                                                                Saved
                                                            </span>
                                                        )}
                                                        {form.dirty && (
                                                            <span className="text-amber-600 text-sm">Unsaved changes</span>
                                                        )}
                                                    </div>
                                                    <button
                                                        onClick={() => saveResult(index)}
                                                        disabled={savingResult === index || (!form.dirty && form.existingResultId !== null)}
                                                        className={`px-4 py-2 rounded text-sm font-medium ${
                                                            form.dirty
                                                                ? 'bg-blue-600 text-white hover:bg-blue-700'
                                                                : 'bg-gray-200 text-gray-600'
                                                        } disabled:opacity-50`}
                                                    >
                                                        {savingResult === index ? 'Saving...' : form.existingResultId ? 'Update' : 'Save'}
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Footer */}
                            <div className="p-4 border-t bg-gray-50 flex justify-between items-center">
                                <div className="text-sm text-gray-600">
                                    {resultForms.filter(f => f.dirty).length > 0 && (
                                        <span className="text-amber-600">
                                            {resultForms.filter(f => f.dirty).length} unsaved changes
                                        </span>
                                    )}
                                </div>
                                <button onClick={closeResultsModal} className="btn-secondary">
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Approval Action Modal */}
                {approvalModalType && selectedApproval && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
                            <div className={`p-4 border-b ${
                                approvalModalType === 'approve' ? 'bg-green-50' :
                                approvalModalType === 'reject' ? 'bg-red-50' :
                                'bg-gray-50'
                            }`}>
                                <h3 className="text-lg font-bold">
                                    {approvalModalType === 'approve' ? 'Approve' :
                                     approvalModalType === 'reject' ? 'Reject' :
                                     'Void'} {selectedApproval.approval_type === 'Global' ? 'Global Approval' : `${selectedApproval.region_name || 'Regional'} Approval`}
                                </h3>
                            </div>

                            <div className="p-4 space-y-4">
                                {approvalError && (
                                    <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                                        {approvalError}
                                    </div>
                                )}

                                {approvalModalType === 'approve' && (
                                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                                        <p className="text-green-800 text-sm">
                                            You are about to approve this monitoring cycle. This action confirms the results have been reviewed and are acceptable.
                                        </p>
                                    </div>
                                )}

                                {approvalModalType === 'reject' && (
                                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                        <p className="text-red-800 text-sm">
                                            Rejecting will return the cycle to <strong>Under Review</strong> status for the team to address concerns.
                                        </p>
                                    </div>
                                )}

                                {approvalModalType === 'void' && (
                                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                                        <p className="text-amber-800 text-sm">
                                            Voiding removes this approval requirement without completing it. Use this when the approval is no longer applicable.
                                        </p>
                                    </div>
                                )}

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        {approvalModalType === 'approve' ? 'Comments (optional)' :
                                         approvalModalType === 'reject' ? 'Rejection Reason *' :
                                         'Void Reason *'}
                                    </label>
                                    <textarea
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                        rows={3}
                                        value={approvalComments}
                                        onChange={(e) => setApprovalComments(e.target.value)}
                                        placeholder={
                                            approvalModalType === 'approve' ? 'Optional comments...' :
                                            approvalModalType === 'reject' ? 'Please explain why this is being rejected...' :
                                            'Please explain why this approval is being voided...'
                                        }
                                    />
                                </div>
                            </div>

                            <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                                <button
                                    onClick={closeApprovalModal}
                                    disabled={approvalLoading}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleApprovalSubmit}
                                    disabled={approvalLoading}
                                    className={`px-4 py-2 rounded text-white font-medium disabled:opacity-50 ${
                                        approvalModalType === 'approve' ? 'bg-green-600 hover:bg-green-700' :
                                        approvalModalType === 'reject' ? 'bg-red-600 hover:bg-red-700' :
                                        'bg-gray-600 hover:bg-gray-700'
                                    }`}
                                >
                                    {approvalLoading ? 'Processing...' :
                                     approvalModalType === 'approve' ? 'Confirm Approval' :
                                     approvalModalType === 'reject' ? 'Confirm Rejection' :
                                     'Confirm Void'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default MonitoringPlanDetailPage;

/**
 * useMonitoringCycle - Custom hook for monitoring cycle operations
 *
 * Manages cycle state including:
 * - Cycle listing and detail fetching
 * - Cycle actions (start, submit, cancel, request approval)
 * - Results entry and management
 * - Approval workflows
 * - Performance summaries and CSV export
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import api from '../api/client';
import { MonitoringPlan } from './useMonitoringPlan';

// Types
interface UserRef {
    user_id: number;
    email: string;
    full_name: string;
}

interface PlanVersion {
    version_id: number;
    version_number: number;
    version_name: string | null;
    effective_date: string;
    is_active: boolean;
}

export interface MonitoringCycle {
    cycle_id: number;
    plan_id: number;
    period_start_date: string;
    period_end_date: string;
    submission_due_date: string;
    report_due_date: string;
    hold_reason?: string | null;
    hold_start_date?: string | null;
    original_due_date?: string | null;
    postponed_due_date?: string | null;
    postponement_count?: number;
    status: string;
    assigned_to_name?: string | null;
    report_url?: string | null;
    plan_version_id?: number | null;
    version_number?: number | null;
    version_name?: string | null;
    version_locked_at?: string | null;
    result_count: number;
    green_count: number;
    yellow_count: number;
    red_count: number;
    approval_count: number;
    pending_approval_count: number;
    is_overdue: boolean;
    days_overdue: number;
}

export interface CycleApproval {
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
    can_approve: boolean;
}

export interface CycleDetail extends MonitoringCycle {
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

interface VersionDetail {
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

interface OutcomeValue {
    value_id: number;
    code: string;
    label: string;
}

export interface MonitoringResult {
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

export interface ResultFormData {
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
    skipped: boolean;
    previousValue: number | null;
    previousOutcome: string | null;
    previousPeriod: string | null;
    model_id: number | null;
}

interface MetricSummary {
    metric_id: number;
    metric_name: string;
    green_count: number;
    yellow_count: number;
    red_count: number;
    na_count: number;
    total: number;
}

interface PerformanceSummary {
    total_results: number;
    green_count: number;
    yellow_count: number;
    red_count: number;
    na_count: number;
    by_metric: MetricSummary[];
}

interface PostponeFormState {
    new_due_date: string;
    reason: string;
    justification: string;
    indefinite_hold: boolean;
}

// Helper function for formatting periods
function formatPeriod(startDate: string, endDate: string): string {
    const startParts = startDate.split('T')[0].split('-');
    const endParts = endDate.split('T')[0].split('-');
    if (startParts.length < 3 || endParts.length < 3) {
        return `${startDate} - ${endDate}`;
    }
    const [startYear, startMonth, startDay] = startParts;
    const [endYear, endMonth, endDay] = endParts;
    return `${startMonth}/${startDay}/${startYear} - ${endMonth}/${endDay}/${endYear}`;
}

interface UseMonitoringCycleReturn {
    // Cycles list
    cycles: MonitoringCycle[];
    loadingCycles: boolean;
    fetchCycles: () => Promise<void>;

    // Selected cycle detail
    selectedCycle: CycleDetail | null;
    setSelectedCycle: (cycle: CycleDetail | null) => void;
    loadingCycleDetail: boolean;
    fetchCycleDetail: (cycleId: number) => Promise<void>;

    // Create cycle
    showCreateModal: boolean;
    setShowCreateModal: (show: boolean) => void;
    creating: boolean;
    createForm: { notes: string };
    setCreateForm: React.Dispatch<React.SetStateAction<{ notes: string }>>;
    handleCreateCycle: (e: React.FormEvent) => Promise<void>;

    // Cycle actions
    actionLoading: boolean;
    actionError: string | null;
    setActionLoading: React.Dispatch<React.SetStateAction<boolean>>;
    setActionError: React.Dispatch<React.SetStateAction<string | null>>;
    handleCycleAction: (cycleId: number, action: string, payload?: object) => Promise<void>;

    // Start cycle modal
    showStartCycleModal: boolean;
    setShowStartCycleModal: React.Dispatch<React.SetStateAction<boolean>>;
    startCycleId: number | null;
    setStartCycleId: React.Dispatch<React.SetStateAction<number | null>>;
    openStartCycleModal: (cycleId: number) => void;
    closeStartCycleModal: () => void;
    handleStartCycle: () => Promise<void>;

    // Cancel cycle modal
    showCancelModal: boolean;
    setShowCancelModal: React.Dispatch<React.SetStateAction<boolean>>;
    cancelCycleId: number | null;
    setCancelCycleId: React.Dispatch<React.SetStateAction<number | null>>;
    cancelReason: string;
    setCancelReason: (reason: string) => void;
    deactivatePlanOnCancel: boolean;
    setDeactivatePlanOnCancel: React.Dispatch<React.SetStateAction<boolean>>;
    openCancelModal: (cycleId: number) => void;
    closeCancelModal: () => void;
    handleCancelCycle: () => Promise<void>;

    // Postpone/hold cycle modal
    showPostponeModal: boolean;
    setShowPostponeModal: React.Dispatch<React.SetStateAction<boolean>>;
    postponeCycleId: number | null;
    setPostponeCycleId: React.Dispatch<React.SetStateAction<number | null>>;
    postponeForm: PostponeFormState;
    setPostponeForm: React.Dispatch<React.SetStateAction<PostponeFormState>>;
    openPostponeModal: (cycleId: number) => void;
    closePostponeModal: () => void;
    handlePostponeCycle: () => Promise<void>;

    // Request approval modal
    showRequestApprovalModal: boolean;
    setShowRequestApprovalModal: React.Dispatch<React.SetStateAction<boolean>>;
    requestApprovalCycleId: number | null;
    setRequestApprovalCycleId: React.Dispatch<React.SetStateAction<number | null>>;
    reportUrl: string;
    setReportUrl: (url: string) => void;
    openRequestApprovalModal: (cycleId: number) => void;
    closeRequestApprovalModal: () => void;
    handleRequestApproval: () => Promise<void>;

    // Edit assignee
    editingAssignee: boolean;
    setEditingAssignee: React.Dispatch<React.SetStateAction<boolean>>;
    newAssigneeId: number | null;
    savingAssignee: boolean;
    startEditingAssignee: () => void;
    cancelEditingAssignee: () => void;
    setNewAssigneeId: (id: number | null) => void;
    handleSaveAssignee: () => Promise<void>;

    // Results entry
    showResultsModal: boolean;
    resultsEntryCycle: MonitoringCycle | null;
    versionDetail: VersionDetail | null;
    outcomeValues: OutcomeValue[];
    resultForms: ResultFormData[];
    loadingResults: boolean;
    savingResult: number | null;
    deletingResult: number | null;
    resultsError: string | null;
    selectedResultsModel: number | null;
    allCycleResults: MonitoringResult[];
    existingResultsMode: 'none' | 'plan-level' | 'model-specific';
    openResultsEntry: (cycle: MonitoringCycle) => Promise<void>;
    closeResultsModal: () => void;
    handleResultChange: (index: number, field: string, value: string | number | null) => void;
    handleSkipToggle: (index: number, isSkipped: boolean) => void;
    handleResultsModelChange: (modelId: number | null) => void;
    saveResult: (index: number) => Promise<void>;
    deleteResult: (index: number) => Promise<void>;

    // Approvals
    approvalModalType: 'approve' | 'reject' | 'void' | null;
    selectedApproval: CycleApproval | null;
    approvalComments: string;
    approvalLoading: boolean;
    approvalError: string | null;
    setApprovalComments: (comments: string) => void;
    openApprovalModal: (approval: CycleApproval, type: 'approve' | 'reject' | 'void') => void;
    closeApprovalModal: () => void;
    handleApprovalAction: () => Promise<void>;

    // Performance summary
    performanceSummary: PerformanceSummary | null;
    loadingPerformance: boolean;
    exportingCycle: number | null;
    fetchPerformanceSummary: () => Promise<void>;
    exportCycleCSV: (cycleId: number) => Promise<void>;

    // Helper functions
    getOutcomeColor: (outcome: string | null) => string;
    getOutcomeIcon: (outcome: string | null) => string;
    formatPeriod: (startDate: string, endDate: string) => string;
}

export function useMonitoringCycle(
    planId: string | undefined,
    plan: MonitoringPlan | null,
    fetchPlan: () => Promise<void>
): UseMonitoringCycleReturn {
    // Cycles state
    const [cycles, setCycles] = useState<MonitoringCycle[]>([]);
    const [loadingCycles, setLoadingCycles] = useState(false);
    const [selectedCycle, setSelectedCycle] = useState<CycleDetail | null>(null);
    const [loadingCycleDetail, setLoadingCycleDetail] = useState(false);

    // Create cycle modal
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [creating, setCreating] = useState(false);
    const [createForm, setCreateForm] = useState({ notes: '' });

    // Action state
    const [actionLoading, setActionLoading] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);

    // Start cycle modal
    const [showStartCycleModal, setShowStartCycleModal] = useState(false);
    const [startCycleId, setStartCycleId] = useState<number | null>(null);

    // Cancel cycle modal
    const [showCancelModal, setShowCancelModal] = useState(false);
    const [cancelCycleId, setCancelCycleId] = useState<number | null>(null);
    const [cancelReason, setCancelReason] = useState('');
    const [deactivatePlanOnCancel, setDeactivatePlanOnCancel] = useState(false);

    const [showPostponeModal, setShowPostponeModal] = useState(false);
    const [postponeCycleId, setPostponeCycleId] = useState<number | null>(null);
    const [postponeForm, setPostponeForm] = useState<PostponeFormState>({
        new_due_date: '',
        reason: '',
        justification: '',
        indefinite_hold: false
    });

    // Request approval modal
    const [showRequestApprovalModal, setShowRequestApprovalModal] = useState(false);
    const [requestApprovalCycleId, setRequestApprovalCycleId] = useState<number | null>(null);
    const [reportUrl, setReportUrl] = useState('');

    // Edit assignee
    const [editingAssignee, setEditingAssignee] = useState(false);
    const [newAssigneeId, setNewAssigneeId] = useState<number | null>(null);
    const [savingAssignee, setSavingAssignee] = useState(false);

    // Results entry state
    const [showResultsModal, setShowResultsModal] = useState(false);
    const [resultsEntryCycle, setResultsEntryCycle] = useState<MonitoringCycle | null>(null);
    const [versionDetail, setVersionDetail] = useState<VersionDetail | null>(null);
    const [outcomeValues, setOutcomeValues] = useState<OutcomeValue[]>([]);
    const [resultForms, setResultForms] = useState<ResultFormData[]>([]);
    const [loadingResults, setLoadingResults] = useState(false);
    const [savingResult, setSavingResult] = useState<number | null>(null);
    const [deletingResult, setDeletingResult] = useState<number | null>(null);
    const [resultsError, setResultsError] = useState<string | null>(null);
    const [selectedResultsModel, setSelectedResultsModel] = useState<number | null>(null);
    const [allCycleResults, setAllCycleResults] = useState<MonitoringResult[]>([]);

    // Stored metrics context for model switching
    const [metricsContext, setMetricsContext] = useState<{
        metricsToShow: any[];
        previousResults: MonitoringResult[];
        previousPeriodLabel: string | null;
    } | null>(null);

    // Approval modal state
    const [approvalModalType, setApprovalModalType] = useState<'approve' | 'reject' | 'void' | null>(null);
    const [selectedApproval, setSelectedApproval] = useState<CycleApproval | null>(null);
    const [approvalComments, setApprovalComments] = useState('');
    const [approvalLoading, setApprovalLoading] = useState(false);
    const [approvalError, setApprovalError] = useState<string | null>(null);

    // Performance summary
    const [performanceSummary, setPerformanceSummary] = useState<PerformanceSummary | null>(null);
    const [loadingPerformance, setLoadingPerformance] = useState(false);
    const [exportingCycle, setExportingCycle] = useState<number | null>(null);

    // Computed: existing results mode
    const existingResultsMode = useMemo<'none' | 'plan-level' | 'model-specific'>(() => {
        if (allCycleResults.length === 0) return 'none';
        const hasPlanLevel = allCycleResults.some(r => r.model_id === null);
        const hasModelSpecific = allCycleResults.some(r => r.model_id !== null);
        if (hasPlanLevel && !hasModelSpecific) return 'plan-level';
        if (hasModelSpecific && !hasPlanLevel) return 'model-specific';
        return hasModelSpecific ? 'model-specific' : 'plan-level';
    }, [allCycleResults]);

    // Fetch cycles
    const fetchCycles = useCallback(async () => {
        if (!planId) return;
        setLoadingCycles(true);
        try {
            const response = await api.get(`/monitoring/plans/${planId}/cycles`);
            setCycles(response.data);
        } catch (err) {
            console.error('Failed to load cycles:', err);
        } finally {
            setLoadingCycles(false);
        }
    }, [planId]);

    // Fetch cycle detail
    const fetchCycleDetail = useCallback(async (cycleId: number) => {
        setLoadingCycleDetail(true);
        try {
            const [cycleResponse, approvalsResponse] = await Promise.all([
                api.get(`/monitoring/cycles/${cycleId}`),
                api.get(`/monitoring/cycles/${cycleId}/approvals`)
            ]);

            const approvals = approvalsResponse.data.map((a: any) => ({
                ...a,
                region_name: a.region?.region_name || null,
                approver_name: a.approver?.full_name || null
            }));

            setSelectedCycle({
                ...cycleResponse.data,
                approvals
            });
        } catch (err) {
            console.error('Failed to load cycle detail:', err);
        } finally {
            setLoadingCycleDetail(false);
        }
    }, []);

    // Create cycle
    const handleCreateCycle = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!planId) return;
        setCreating(true);
        setActionError(null);

        try {
            await api.post(`/monitoring/plans/${planId}/cycles`, {
                notes: createForm.notes || null
            });
            setShowCreateModal(false);
            setCreateForm({ notes: '' });
            fetchCycles();
            fetchPlan();
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to create cycle');
        } finally {
            setCreating(false);
        }
    }, [planId, createForm, fetchCycles, fetchPlan]);

    // Generic cycle action
    const handleCycleAction = useCallback(async (cycleId: number, action: string, payload?: object) => {
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
    }, [selectedCycle?.cycle_id, fetchCycles, fetchCycleDetail]);

    // Start cycle modal
    const openStartCycleModal = useCallback((cycleId: number) => {
        setStartCycleId(cycleId);
        setActionError(null);
        setShowStartCycleModal(true);
    }, []);

    const closeStartCycleModal = useCallback(() => {
        setShowStartCycleModal(false);
        setStartCycleId(null);
    }, []);

    const handleStartCycle = useCallback(async () => {
        if (!startCycleId) return;
        setActionLoading(true);
        setActionError(null);

        try {
            await api.post(`/monitoring/cycles/${startCycleId}/start`);
            setShowStartCycleModal(false);
            setStartCycleId(null);
            fetchCycles();
            fetchPlan();
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to start cycle');
        } finally {
            setActionLoading(false);
        }
    }, [startCycleId, fetchCycles, fetchPlan]);

    // Cancel cycle modal
    const openCancelModal = useCallback((cycleId: number) => {
        setCancelCycleId(cycleId);
        setCancelReason('');
        setDeactivatePlanOnCancel(false);
        setActionError(null);
        setShowCancelModal(true);
    }, []);

    const closeCancelModal = useCallback(() => {
        setShowCancelModal(false);
        setCancelCycleId(null);
        setCancelReason('');
        setDeactivatePlanOnCancel(false);
    }, []);

    const handleCancelCycle = useCallback(async () => {
        if (!cancelCycleId || !cancelReason.trim()) return;
        setActionLoading(true);
        setActionError(null);

        try {
            await api.post(`/monitoring/cycles/${cancelCycleId}/cancel`, {
                cancel_reason: cancelReason.trim(),
                deactivate_plan: deactivatePlanOnCancel
            });
            setShowCancelModal(false);
            setCancelCycleId(null);
            setCancelReason('');
            setDeactivatePlanOnCancel(false);
            fetchCycles();
            fetchPlan();
            if (selectedCycle?.cycle_id === cancelCycleId) {
                setSelectedCycle(null);
            }
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to cancel cycle');
        } finally {
            setActionLoading(false);
        }
    }, [cancelCycleId, cancelReason, deactivatePlanOnCancel, fetchCycles, fetchPlan, selectedCycle?.cycle_id]);

    // Postpone/hold cycle modal
    const openPostponeModal = useCallback((cycleId: number) => {
        setPostponeCycleId(cycleId);
        setPostponeForm({
            new_due_date: '',
            reason: '',
            justification: '',
            indefinite_hold: false
        });
        setActionError(null);
        setShowPostponeModal(true);
    }, []);

    const closePostponeModal = useCallback(() => {
        setShowPostponeModal(false);
        setPostponeCycleId(null);
        setPostponeForm({
            new_due_date: '',
            reason: '',
            justification: '',
            indefinite_hold: false
        });
    }, []);

    const handlePostponeCycle = useCallback(async () => {
        if (!postponeCycleId) return;
        if (!postponeForm.reason.trim() || !postponeForm.justification.trim()) {
            setActionError('Reason and justification are required.');
            return;
        }
        if (!postponeForm.indefinite_hold && !postponeForm.new_due_date) {
            setActionError('New due date is required to extend a cycle.');
            return;
        }

        setActionLoading(true);
        setActionError(null);

        try {
            await api.post(`/monitoring/cycles/${postponeCycleId}/postpone`, {
                new_due_date: postponeForm.new_due_date || null,
                reason: postponeForm.reason.trim(),
                justification: postponeForm.justification.trim(),
                indefinite_hold: postponeForm.indefinite_hold
            });
            setShowPostponeModal(false);
            setPostponeCycleId(null);
            setPostponeForm({
                new_due_date: '',
                reason: '',
                justification: '',
                indefinite_hold: false
            });
            fetchCycles();
            fetchPlan();
            if (selectedCycle?.cycle_id === postponeCycleId) {
                fetchCycleDetail(postponeCycleId);
            }
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to postpone cycle');
        } finally {
            setActionLoading(false);
        }
    }, [postponeCycleId, postponeForm, fetchCycles, fetchPlan, selectedCycle?.cycle_id, fetchCycleDetail]);

    // Request approval modal
    const openRequestApprovalModal = useCallback((cycleId: number) => {
        setRequestApprovalCycleId(cycleId);
        setReportUrl('');
        setActionError(null);
        setShowRequestApprovalModal(true);
    }, []);

    const closeRequestApprovalModal = useCallback(() => {
        setShowRequestApprovalModal(false);
        setRequestApprovalCycleId(null);
        setReportUrl('');
    }, []);

    const handleRequestApproval = useCallback(async () => {
        if (!requestApprovalCycleId || !reportUrl.trim()) return;
        setActionLoading(true);
        setActionError(null);

        try {
            await api.post(`/monitoring/cycles/${requestApprovalCycleId}/request-approval`, {
                report_url: reportUrl.trim()
            });
            setShowRequestApprovalModal(false);
            setRequestApprovalCycleId(null);
            setReportUrl('');
            fetchCycles();
            if (selectedCycle?.cycle_id === requestApprovalCycleId) {
                fetchCycleDetail(requestApprovalCycleId);
            }
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to request approval');
        } finally {
            setActionLoading(false);
        }
    }, [requestApprovalCycleId, reportUrl, fetchCycles, selectedCycle?.cycle_id, fetchCycleDetail]);

    // Edit assignee
    const startEditingAssignee = useCallback(() => {
        if (selectedCycle) {
            setNewAssigneeId(selectedCycle.assigned_to?.user_id || null);
            setEditingAssignee(true);
        }
    }, [selectedCycle]);

    const cancelEditingAssignee = useCallback(() => {
        setEditingAssignee(false);
        setNewAssigneeId(null);
    }, []);

    const handleSaveAssignee = useCallback(async () => {
        if (!selectedCycle) return;
        setSavingAssignee(true);
        setActionError(null);

        try {
            await api.patch(`/monitoring/cycles/${selectedCycle.cycle_id}`, {
                assigned_to_user_id: newAssigneeId || 0
            });
            await fetchCycleDetail(selectedCycle.cycle_id);
            fetchCycles();
            setEditingAssignee(false);
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to update assignee');
        } finally {
            setSavingAssignee(false);
        }
    }, [selectedCycle, newAssigneeId, fetchCycleDetail, fetchCycles]);

    // Helper to build result forms
    const buildResultForms = useCallback((
        metricsToShow: any[],
        currentResults: MonitoringResult[],
        previousResults: MonitoringResult[],
        previousPeriodLabel: string | null,
        modelId: number | null
    ): ResultFormData[] => {
        return metricsToShow.map(m => {
            const existing = currentResults.find((r: MonitoringResult) =>
                r.plan_metric_id === m.metric_id && r.model_id === modelId
            );
            const previousResult = previousResults.find((r: MonitoringResult) =>
                r.plan_metric_id === m.metric_id && r.model_id === modelId
            );
            const wasSkipped = existing &&
                existing.numeric_value === null &&
                existing.outcome_value === null &&
                existing.narrative;

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
                dirty: false,
                skipped: !!wasSkipped,
                previousValue: previousResult?.numeric_value ?? null,
                previousOutcome: previousResult?.calculated_outcome ?? null,
                previousPeriod: previousPeriodLabel,
                model_id: modelId
            };
        });
    }, []);

    // Open results entry
    const openResultsEntry = useCallback(async (cycle: MonitoringCycle) => {
        setResultsEntryCycle(cycle);
        setShowResultsModal(true);
        setLoadingResults(true);
        setResultsError(null);

        try {
            // Fetch outcome values
            const outcomeResponse = await api.get('/taxonomies/');
            const taxonomies = outcomeResponse.data;
            const qualitativeOutcomeTax = taxonomies.find((t: { name: string }) => t.name === 'Qualitative Outcome');
            if (qualitativeOutcomeTax) {
                const taxDetailResponse = await api.get(`/taxonomies/${qualitativeOutcomeTax.taxonomy_id}`);
                const values = taxDetailResponse.data.values || [];
                setOutcomeValues(values.filter((v: OutcomeValue & { is_active: boolean }) => v.is_active));
            }

            // Fetch existing results
            const resultsResponse = await api.get(`/monitoring/cycles/${cycle.cycle_id}/results`);
            const allResults: MonitoringResult[] = resultsResponse.data;
            setAllCycleResults(allResults);

            // Determine metrics to show
            let metricsToShow: any[] = [];
            if (cycle.plan_version_id && planId) {
                const versionResponse = await api.get(`/monitoring/plans/${planId}/versions/${cycle.plan_version_id}`);
                setVersionDetail(versionResponse.data);
                metricsToShow = versionResponse.data.metric_snapshots.map((s: MetricSnapshot) => ({
                    metric_id: s.original_metric_id ?? s.snapshot_id,
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
                setVersionDetail(null);
                metricsToShow = plan.metrics.filter(m => m.is_active).map(m => ({
                    metric_id: m.metric_id,
                    kpm_name: m.kpm?.name || 'Unknown',
                    evaluation_type: m.kpm?.evaluation_type || 'Quantitative',
                    yellow_min: m.yellow_min,
                    yellow_max: m.yellow_max,
                    red_min: m.red_min,
                    red_max: m.red_max,
                    qualitative_guidance: m.qualitative_guidance
                }));
            }

            // Find previous cycle for trends
            const previousApprovedCycle = cycles.find(c =>
                c.status === 'APPROVED' && c.period_end_date < cycle.period_end_date
            );
            let previousResults: MonitoringResult[] = [];
            let previousPeriodLabel: string | null = null;

            if (previousApprovedCycle) {
                try {
                    const prevResultsResponse = await api.get(`/monitoring/cycles/${previousApprovedCycle.cycle_id}/results`);
                    previousResults = prevResultsResponse.data;
                    previousPeriodLabel = formatPeriod(previousApprovedCycle.period_start_date, previousApprovedCycle.period_end_date);
                } catch {
                    // Silently fail
                }
            }

            // Store context for model switching
            setMetricsContext({ metricsToShow, previousResults, previousPeriodLabel });

            // Initial model selection
            const planModels = plan?.models || [];
            const initialModelId = planModels.length === 1 ? planModels[0].model_id : null;
            setSelectedResultsModel(initialModelId);

            // Build forms
            const forms = buildResultForms(metricsToShow, allResults, previousResults, previousPeriodLabel, initialModelId);
            setResultForms(forms);
        } catch (err: any) {
            setResultsError(err.response?.data?.detail || 'Failed to load results data');
        } finally {
            setLoadingResults(false);
        }
    }, [planId, plan, cycles, buildResultForms]);

    const closeResultsModal = useCallback(() => {
        setShowResultsModal(false);
        setResultsEntryCycle(null);
        setVersionDetail(null);
        setResultForms([]);
        setResultsError(null);
        setAllCycleResults([]);
        setMetricsContext(null);
    }, []);

    // Handle model change in results entry
    const handleResultsModelChange = useCallback((modelId: number | null) => {
        setSelectedResultsModel(modelId);
        if (metricsContext) {
            const forms = buildResultForms(
                metricsContext.metricsToShow,
                allCycleResults,
                metricsContext.previousResults,
                metricsContext.previousPeriodLabel,
                modelId
            );
            setResultForms(forms);
        }
    }, [metricsContext, allCycleResults, buildResultForms]);

    // Calculate outcome for quantitative metrics
    const calculateOutcome = useCallback((value: number, metric: ResultFormData): string => {
        if (metric.red_min !== null && value < metric.red_min) return 'RED';
        if (metric.red_max !== null && value > metric.red_max) return 'RED';
        if (metric.yellow_min !== null && value < metric.yellow_min) return 'YELLOW';
        if (metric.yellow_max !== null && value > metric.yellow_max) return 'YELLOW';
        return 'GREEN';
    }, []);

    // Handle result change
    const handleResultChange = useCallback((index: number, field: string, value: string | number | null) => {
        setResultForms(prev => {
            const updated = [...prev];
            const form = { ...updated[index], [field]: value, dirty: true };

            if (form.evaluation_type === 'Quantitative' && field === 'numeric_value') {
                if (value !== '' && value !== null) {
                    const numValue = parseFloat(value as string);
                    if (!isNaN(numValue)) {
                        form.calculatedOutcome = calculateOutcome(numValue, form);
                    } else {
                        form.calculatedOutcome = null;
                    }
                } else {
                    form.calculatedOutcome = null;
                }
            }

            if (field === 'outcome_value_id') {
                if (value !== null) {
                    const selectedOutcome = outcomeValues.find(o => o.value_id === value);
                    if (selectedOutcome) {
                        form.calculatedOutcome = selectedOutcome.code;
                    }
                } else {
                    form.calculatedOutcome = null;
                }
            }

            updated[index] = form;
            return updated;
        });
    }, [calculateOutcome, outcomeValues]);

    // Handle skip toggle
    const handleSkipToggle = useCallback((index: number, isSkipped: boolean) => {
        setResultForms(prev => {
            const updated = [...prev];
            const form = { ...updated[index], skipped: isSkipped, dirty: true };
            if (isSkipped) {
                form.numeric_value = '';
                form.outcome_value_id = null;
                form.calculatedOutcome = null;
            }
            updated[index] = form;
            return updated;
        });
    }, []);

    // Save result
    const saveResult = useCallback(async (index: number) => {
        const form = resultForms[index];
        if (!resultsEntryCycle) return;

        if (form.skipped && !form.narrative.trim()) {
            setResultsError('An explanation is required when skipping a metric');
            return;
        }

        if (form.evaluation_type === 'Qualitative' && !form.narrative.trim()) {
            setResultsError('Narrative is required for qualitative metrics');
            return;
        }

        setSavingResult(index);
        setResultsError(null);

        try {
            const payload: Record<string, unknown> = {
                plan_metric_id: form.metric_id,
                model_id: form.model_id,
                narrative: form.narrative || null
            };

            if (form.evaluation_type === 'Quantitative') {
                payload.numeric_value = form.numeric_value ? parseFloat(form.numeric_value) : null;
            } else {
                payload.outcome_value_id = form.outcome_value_id;
            }

            let savedResultId = form.existingResultId;
            if (form.existingResultId) {
                await api.patch(`/monitoring/results/${form.existingResultId}`, payload);
            } else {
                const response = await api.post(`/monitoring/cycles/${resultsEntryCycle.cycle_id}/results`, payload);
                savedResultId = response.data.result_id;
                setResultForms(prev => {
                    const updated = [...prev];
                    updated[index] = { ...updated[index], existingResultId: response.data.result_id, dirty: false };
                    return updated;
                });
            }

            setResultForms(prev => {
                const updated = [...prev];
                updated[index] = { ...updated[index], dirty: false };
                return updated;
            });

            // Update allCycleResults
            setAllCycleResults(prev => {
                const filtered = prev.filter((r: MonitoringResult) =>
                    !(r.plan_metric_id === form.metric_id && r.model_id === form.model_id)
                );
                const newResult: MonitoringResult = {
                    result_id: savedResultId!,
                    cycle_id: resultsEntryCycle.cycle_id,
                    plan_metric_id: form.metric_id,
                    model_id: form.model_id,
                    numeric_value: form.evaluation_type === 'Quantitative' && form.numeric_value ? parseFloat(form.numeric_value) : null,
                    outcome_value: form.outcome_value_id ? { value_id: form.outcome_value_id, code: '', label: '' } : null,
                    narrative: form.narrative || null,
                    calculated_outcome: form.calculatedOutcome,
                    entered_by: { user_id: 0, email: '', full_name: '' },
                    entered_at: new Date().toISOString()
                };
                return [...filtered, newResult];
            });

            fetchCycles();
        } catch (err: any) {
            setResultsError(err.response?.data?.detail || 'Failed to save result');
        } finally {
            setSavingResult(null);
        }
    }, [resultForms, resultsEntryCycle, fetchCycles]);

    // Delete result
    const deleteResult = useCallback(async (index: number) => {
        const form = resultForms[index];
        if (!form.existingResultId) return;
        if (!window.confirm('Are you sure you want to delete this result? This cannot be undone.')) return;

        setDeletingResult(index);
        setResultsError(null);

        try {
            await api.delete(`/monitoring/results/${form.existingResultId}`);

            setResultForms(prev => {
                const updated = [...prev];
                updated[index] = {
                    ...updated[index],
                    existingResultId: null,
                    numeric_value: '',
                    outcome_value_id: null,
                    narrative: '',
                    calculatedOutcome: null,
                    skipped: false,
                    dirty: false
                };
                return updated;
            });

            fetchCycles();
        } catch (err: any) {
            setResultsError(err.response?.data?.detail || 'Failed to delete result');
        } finally {
            setDeletingResult(null);
        }
    }, [resultForms, fetchCycles]);

    // Approval actions
    const openApprovalModal = useCallback((approval: CycleApproval, type: 'approve' | 'reject' | 'void') => {
        setSelectedApproval(approval);
        setApprovalModalType(type);
        setApprovalComments('');
        setApprovalError(null);
    }, []);

    const closeApprovalModal = useCallback(() => {
        setApprovalModalType(null);
        setSelectedApproval(null);
        setApprovalComments('');
    }, []);

    const handleApprovalAction = useCallback(async () => {
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
    }, [selectedApproval, selectedCycle, approvalModalType, approvalComments, closeApprovalModal, fetchCycleDetail, fetchCycles]);

    // Performance summary
    const fetchPerformanceSummary = useCallback(async () => {
        if (!planId) return;
        setLoadingPerformance(true);
        try {
            const response = await api.get(`/monitoring/plans/${planId}/performance-summary?cycles=10`);
            setPerformanceSummary(response.data);
        } catch (err) {
            console.error('Failed to load performance summary:', err);
        } finally {
            setLoadingPerformance(false);
        }
    }, [planId]);

    // Export cycle CSV
    const exportCycleCSV = useCallback(async (cycleId: number) => {
        if (!planId) return;
        setExportingCycle(cycleId);
        try {
            const response = await api.get(`/monitoring/plans/${planId}/cycles/${cycleId}/export`, {
                responseType: 'blob'
            });

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;

            const contentDisposition = response.headers['content-disposition'];
            let filename = `cycle_${cycleId}_results.csv`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to export cycle:', err);
        } finally {
            setExportingCycle(null);
        }
    }, [planId]);

    // Helper functions
    const getOutcomeColor = useCallback((outcome: string | null): string => {
        switch (outcome) {
            case 'GREEN': return 'bg-green-100 text-green-800 border-green-300';
            case 'YELLOW': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            case 'RED': return 'bg-red-100 text-red-800 border-red-300';
            default: return 'bg-gray-100 text-gray-600 border-gray-300';
        }
    }, []);

    const getOutcomeIcon = useCallback((outcome: string | null): string => {
        switch (outcome) {
            case 'GREEN': return '●';
            case 'YELLOW': return '●';
            case 'RED': return '●';
            default: return '○';
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        if (planId) {
            fetchCycles();
        }
    }, [planId, fetchCycles]);

    return {
        // Cycles list
        cycles,
        loadingCycles,
        fetchCycles,

        // Selected cycle
        selectedCycle,
        setSelectedCycle,
        loadingCycleDetail,
        fetchCycleDetail,

        // Create cycle
        showCreateModal,
        setShowCreateModal,
        creating,
        createForm,
        setCreateForm,
        handleCreateCycle,

        // Actions
        actionLoading,
        actionError,
        setActionLoading,
        setActionError,
        handleCycleAction,

        // Start cycle
        showStartCycleModal,
        setShowStartCycleModal,
        startCycleId,
        setStartCycleId,
        openStartCycleModal,
        closeStartCycleModal,
        handleStartCycle,

        // Cancel cycle
        showCancelModal,
        setShowCancelModal,
        cancelCycleId,
        setCancelCycleId,
        cancelReason,
        setCancelReason,
        deactivatePlanOnCancel,
        setDeactivatePlanOnCancel,
        openCancelModal,
        closeCancelModal,
        handleCancelCycle,

        // Postpone/hold cycle
        showPostponeModal,
        setShowPostponeModal,
        postponeCycleId,
        setPostponeCycleId,
        postponeForm,
        setPostponeForm,
        openPostponeModal,
        closePostponeModal,
        handlePostponeCycle,

        // Request approval
        showRequestApprovalModal,
        setShowRequestApprovalModal,
        requestApprovalCycleId,
        setRequestApprovalCycleId,
        reportUrl,
        setReportUrl,
        openRequestApprovalModal,
        closeRequestApprovalModal,
        handleRequestApproval,

        // Edit assignee
        editingAssignee,
        setEditingAssignee,
        newAssigneeId,
        savingAssignee,
        startEditingAssignee,
        cancelEditingAssignee,
        setNewAssigneeId,
        handleSaveAssignee,

        // Results entry
        showResultsModal,
        resultsEntryCycle,
        versionDetail,
        outcomeValues,
        resultForms,
        loadingResults,
        savingResult,
        deletingResult,
        resultsError,
        selectedResultsModel,
        allCycleResults,
        existingResultsMode,
        openResultsEntry,
        closeResultsModal,
        handleResultChange,
        handleSkipToggle,
        handleResultsModelChange,
        saveResult,
        deleteResult,

        // Approvals
        approvalModalType,
        selectedApproval,
        approvalComments,
        approvalLoading,
        approvalError,
        setApprovalComments,
        openApprovalModal,
        closeApprovalModal,
        handleApprovalAction,

        // Performance
        performanceSummary,
        loadingPerformance,
        exportingCycle,
        fetchPerformanceSummary,
        exportCycleCSV,

        // Helpers
        getOutcomeColor,
        getOutcomeIcon,
        formatPeriod,
    };
}

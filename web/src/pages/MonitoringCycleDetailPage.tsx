import React, { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import CycleResultsPanel from '../components/monitoring/CycleResultsPanel';
import CycleApprovalPanel, { CycleApproval } from '../components/monitoring/CycleApprovalPanel';
import { formatPeriod } from '../components/monitoring/CycleResultsPanel';
import BreachResolutionWizard, { BreachItem, BreachResolution } from '../components/BreachResolutionWizard';
import MonitoringDataGrid, {
    ResultSavePayload,
    CellPosition,
    MonitoringResult as GridMonitoringResult,
} from '../components/MonitoringDataGrid';
import BreachAnnotationPanel from '../components/BreachAnnotationPanel';
import MonitoringCSVImport from '../components/MonitoringCSVImport';
import RecommendationCreateModal from '../components/RecommendationCreateModal';
import { isAdmin, isAdminOrValidator } from '../utils/roleUtils';

// Types
interface UserRef {
    user_id: number;
    email: string;
    full_name: string;
}

interface Model {
    model_id: number;
    model_name: string;
}

interface MonitoringPlan {
    plan_id: number;
    name: string;
    models?: Model[];
    user_permissions?: {
        is_admin: boolean;
        is_team_member: boolean;
        is_data_provider: boolean;
        can_start_cycle: boolean;
        can_submit_cycle: boolean;
        can_request_approval: boolean;
        can_cancel_cycle: boolean;
    };
}

interface PlanVersion {
    version_id: number;
    version_number: number;
    version_name: string | null;
    effective_date: string;
}

interface CycleDetail {
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
    assigned_to?: UserRef | null;
    assigned_to_name?: string | null;
    report_url?: string | null;
    plan_version_id?: number | null;
    version_number?: number | null;
    version_name?: string | null;
    version_locked_at?: string | null;
    version_locked_by?: UserRef | null;
    notes?: string | null;
    submitted_at?: string | null;
    submitted_by?: UserRef | null;
    completed_at?: string | null;
    completed_by?: UserRef | null;
    result_count: number;
    green_count: number;
    yellow_count: number;
    red_count: number;
    approval_count: number;
    pending_approval_count: number;
    is_overdue: boolean;
    days_overdue: number;
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

interface LinkedRecommendation {
    recommendation_id: number;
    recommendation_code: string;
    title: string;
    plan_metric_id: number | null;
    current_status: { code: string; label: string };
    priority: { code: string; label: string };
    current_target_date: string;
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
    skipped: boolean;
    previousValue: number | null;
    previousOutcome: string | null;
    previousPeriod: string | null;
    model_id: number | null;
}

type TabType = 'results' | 'approvals';

const MonitoringCycleDetailPage: React.FC = () => {
    const { cycleId } = useParams<{ cycleId: string }>();
    const { user } = useAuth();
    const isAdminUser = isAdmin(user);
    const isAdminOrValidatorUser = isAdminOrValidator(user);
    const monitoringHomePath = isAdminUser ? '/monitoring-plans?tab=plans' : '/my-monitoring-tasks';
    const monitoringHomeLabel = isAdminUser ? 'Monitoring Plans' : 'My Monitoring Tasks';

    // Basic state
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [cycle, setCycle] = useState<CycleDetail | null>(null);
    const [plan, setPlan] = useState<MonitoringPlan | null>(null);
    const [activeTab, setActiveTab] = useState<TabType>('results');

    // Results state
    const [versionDetail, setVersionDetail] = useState<VersionDetail | null>(null);
    const [outcomeValues, setOutcomeValues] = useState<OutcomeValue[]>([]);
    const [resultForms, setResultForms] = useState<ResultFormData[]>([]);
    const [loadingResults, setLoadingResults] = useState(false);
    const [savingResult, setSavingResult] = useState<number | null>(null);
    const [deletingResult, setDeletingResult] = useState<number | null>(null);
    const [resultsError, setResultsError] = useState<string | null>(null);
    const [selectedResultsModel, setSelectedResultsModel] = useState<number | null>(null);
    const [allCycleResults, setAllCycleResults] = useState<MonitoringResult[]>([]);

    // Approval state
    const [approvalModalType, setApprovalModalType] = useState<'approve' | 'reject' | 'void' | null>(null);
    const [selectedApproval, setSelectedApproval] = useState<CycleApproval | null>(null);
    const [approvalComments, setApprovalComments] = useState('');
    const [approvalEvidence, setApprovalEvidence] = useState('');
    const [approvalLoading, setApprovalLoading] = useState(false);
    const [approvalError, setApprovalError] = useState<string | null>(null);

    // Breach wizard state
    const [showBreachWizard, setShowBreachWizard] = useState(false);
    const [pendingBreaches, setPendingBreaches] = useState<BreachItem[]>([]);
    const [breachResolutionLoading, setBreachResolutionLoading] = useState(false);

    // Request approval modal state
    const [showRequestApprovalModal, setShowRequestApprovalModal] = useState(false);
    const [reportUrl, setReportUrl] = useState('');
    const [requestingApproval, setRequestingApproval] = useState(false);
    const [requestApprovalError, setRequestApprovalError] = useState<string | null>(null);

    // Submit cycle state
    const [submittingCycle, setSubmittingCycle] = useState(false);
    const [submitCycleError, setSubmitCycleError] = useState<string | null>(null);

    // Report download state
    const [downloadingReport, setDownloadingReport] = useState(false);

    // View mode and data grid state
    const [viewMode, setViewMode] = useState<'grid' | 'card'>('card');
    const [showCSVImport, setShowCSVImport] = useState(false);

    // Breach annotation panel state
    const [breachPanelOpen, setBreachPanelOpen] = useState(false);
    const [breachPanelResultId, setBreachPanelResultId] = useState<number | null>(null);
    const [breachPanelMetricInfo, setBreachPanelMetricInfo] = useState<{
        metricName: string;
        modelName: string;
        numericValue: number | null;
        outcome: string | null;
        thresholds: {
            yellow_min: number | null;
            yellow_max: number | null;
            red_min: number | null;
            red_max: number | null;
        };
    } | null>(null);
    const [breachPanelNarrative, setBreachPanelNarrative] = useState('');
    const [breachPanelCellIds, setBreachPanelCellIds] = useState<{ modelId: number; metricId: number } | null>(null);
    const [breachPanelRecommendations, setBreachPanelRecommendations] = useState<LinkedRecommendation[]>([]);
    const [breachPanelRecommendationsLoading, setBreachPanelRecommendationsLoading] = useState(false);
    const [breachPanelRecommendationsError, setBreachPanelRecommendationsError] = useState<string | null>(null);

    // Recommendation create modal state (triggered from breach panel)
    const [showRecModal, setShowRecModal] = useState(false);
    const [recModalData, setRecModalData] = useState<{
        users: { user_id: number; email: string; full_name: string }[];
        priorities: { value_id: number; code: string; label: string }[];
        categories: { value_id: number; code: string; label: string }[];
    } | null>(null);

    // Computed values
    const existingResultsMode = useMemo<'none' | 'plan-level' | 'model-specific'>(() => {
        if (allCycleResults.length === 0) return 'none';
        const hasPlanLevel = allCycleResults.some(r => r.model_id === null);
        const hasModelSpecific = allCycleResults.some(r => r.model_id !== null);
        if (hasPlanLevel && !hasModelSpecific) return 'plan-level';
        if (hasModelSpecific && !hasPlanLevel) return 'model-specific';
        return hasModelSpecific ? 'model-specific' : 'plan-level';
    }, [allCycleResults]);
    const monitoringCategoryId = recModalData?.categories.find(
        (category) => category.code === 'MONITORING' || category.label === 'Monitoring'
    )?.value_id ?? null;
    const canCreateRecommendation = useMemo(() => {
        if (isAdminOrValidatorUser) {
            return true;
        }
        return !!plan?.user_permissions?.is_team_member;
    }, [isAdminOrValidatorUser, plan?.user_permissions?.is_team_member]);
    const canDownloadReport = useMemo(() => {
        if (isAdminOrValidatorUser) {
            return true;
        }
        if (plan?.user_permissions?.is_team_member) {
            return true;
        }
        return cycle?.approvals?.some(
            (approval) => approval.approver?.user_id === user?.user_id
        ) ?? false;
    }, [isAdminOrValidatorUser, user?.user_id, plan?.user_permissions?.is_team_member, cycle?.approvals]);
    const resultsReadOnly = cycle ? !['DATA_COLLECTION', 'UNDER_REVIEW'].includes(cycle.status) : true;

    // Fetch cycle and plan details
    useEffect(() => {
        const fetchData = async () => {
            if (!cycleId) return;

            setLoading(true);
            setError(null);

            try {
                // Fetch cycle detail
                const cycleResp = await api.get(`/monitoring/cycles/${cycleId}`);
                setCycle(cycleResp.data);

                // Fetch plan for breadcrumb and models
                const planResp = await api.get(`/monitoring/plans/${cycleResp.data.plan_id}`);
                setPlan(planResp.data);

                // If cycle has results capability, load results data
                if (['DATA_COLLECTION', 'ON_HOLD', 'UNDER_REVIEW', 'PENDING_APPROVAL', 'APPROVED'].includes(cycleResp.data.status)) {
                    loadResultsData(cycleResp.data);
                }
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to load cycle details');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [cycleId]);

    // Load results data
    const loadResultsData = async (cycleData: CycleDetail) => {
        setLoadingResults(true);
        setResultsError(null);

        try {
            // Load outcome values for qualitative metrics
            const taxonomyResp = await api.get('/taxonomies/');
            const qualTaxonomy = taxonomyResp.data.find((t: any) => t.name === 'Qualitative Outcome');
            if (qualTaxonomy) {
                const valuesResp = await api.get(`/taxonomies/${qualTaxonomy.taxonomy_id}`);
                const activeValues = valuesResp.data.values?.filter((v: any) => v.is_active) || [];
                setOutcomeValues(activeValues);
            }

            // Load existing results for this cycle
            const resultsResp = await api.get(`/monitoring/cycles/${cycleData.cycle_id}/results`);
            setAllCycleResults(resultsResp.data || []);

            // Determine metrics source
            let metrics: MetricSnapshot[] = [];
            if (cycleData.plan_version_id) {
                // Use locked version metrics
                const versionResp = await api.get(`/monitoring/plans/${cycleData.plan_id}/versions/${cycleData.plan_version_id}`);
                setVersionDetail(versionResp.data);
                metrics = versionResp.data.metric_snapshots || [];
            }

            // Initialize forms from metrics
            const activeMetrics = metrics.filter(m => {
                return m.original_metric_id !== null;
            });

            const forms: ResultFormData[] = activeMetrics.map(metric => {
                const existingResult = resultsResp.data?.find(
                    (r: MonitoringResult) => r.plan_metric_id === metric.original_metric_id && r.model_id === null
                );

                return {
                    metric_id: metric.original_metric_id!,
                    snapshot_id: metric.snapshot_id,
                    kpm_name: metric.kpm_name,
                    evaluation_type: metric.evaluation_type,
                    numeric_value: existingResult?.numeric_value?.toString() ?? '',
                    outcome_value_id: existingResult?.outcome_value?.value_id ?? null,
                    narrative: existingResult?.narrative ?? '',
                    yellow_min: metric.yellow_min,
                    yellow_max: metric.yellow_max,
                    red_min: metric.red_min,
                    red_max: metric.red_max,
                    qualitative_guidance: metric.qualitative_guidance,
                    calculatedOutcome: existingResult?.calculated_outcome ?? null,
                    existingResultId: existingResult?.result_id ?? null,
                    dirty: false,
                    skipped: existingResult?.numeric_value === null && existingResult?.outcome_value === null && existingResult?.narrative !== null,
                    previousValue: null,
                    previousOutcome: null,
                    previousPeriod: null,
                    model_id: null,
                };
            });

            setResultForms(forms);
        } catch (err: any) {
            setResultsError(err.response?.data?.detail || 'Failed to load results data');
        } finally {
            setLoadingResults(false);
        }
    };

    // Calculate outcome from value
    const calculateOutcome = (value: string, form: ResultFormData): string | null => {
        if (!value || form.skipped) return null;

        const numValue = parseFloat(value);
        if (isNaN(numValue)) return null;

        // Check RED thresholds first
        if (form.red_min !== null && numValue < form.red_min) return 'RED';
        if (form.red_max !== null && numValue > form.red_max) return 'RED';

        // Check YELLOW thresholds
        if (form.yellow_min !== null && numValue < form.yellow_min) return 'YELLOW';
        if (form.yellow_max !== null && numValue > form.yellow_max) return 'YELLOW';

        return 'GREEN';
    };

    // Handle result change
    const handleResultChange = (index: number, field: string, value: string | number | null) => {
        setResultForms(prev => {
            const updated = [...prev];
            const form = { ...updated[index], [field]: value, dirty: true };

            // Auto-calculate outcome for quantitative metrics
            if (field === 'numeric_value' && form.evaluation_type === 'Quantitative') {
                form.calculatedOutcome = calculateOutcome(value as string, form);
            }

            // For qualitative metrics, map outcome_value_id to outcome
            if (field === 'outcome_value_id' && form.evaluation_type !== 'Quantitative') {
                const outcomeVal = outcomeValues.find(o => o.value_id === value);
                if (outcomeVal) {
                    form.calculatedOutcome = outcomeVal.code.toUpperCase();
                }
            }

            updated[index] = form;
            return updated;
        });
    };

    // Handle skip toggle
    const handleSkipToggle = (index: number, isSkipped: boolean) => {
        setResultForms(prev => {
            const updated = [...prev];
            updated[index] = {
                ...updated[index],
                skipped: isSkipped,
                dirty: true,
                calculatedOutcome: isSkipped ? 'SKIPPED' : null,
                numeric_value: isSkipped ? '' : updated[index].numeric_value,
                outcome_value_id: isSkipped ? null : updated[index].outcome_value_id,
            };
            return updated;
        });
    };

    // Handle model change for results
    const handleResultsModelChange = React.useCallback((modelId: number | null) => {
        setSelectedResultsModel(modelId);
        // Reload forms for the selected model
        if (cycle) {
            const filteredResults = allCycleResults.filter(r => r.model_id === modelId);
            setResultForms(prev => prev.map(form => {
                const existingResult = filteredResults.find(r => r.plan_metric_id === form.metric_id);
                return {
                    ...form,
                    numeric_value: existingResult?.numeric_value?.toString() ?? '',
                    outcome_value_id: existingResult?.outcome_value?.value_id ?? null,
                    narrative: existingResult?.narrative ?? '',
                    calculatedOutcome: existingResult?.calculated_outcome ?? null,
                    existingResultId: existingResult?.result_id ?? null,
                    dirty: false,
                    model_id: modelId,
                };
            }));
        }
    }, [allCycleResults, cycle]);

    useEffect(() => {
        if (!plan?.models || resultForms.length === 0) return;

        if (existingResultsMode === 'model-specific') {
            const modelIds = plan.models.map(model => model.model_id);
            const hasValidSelection = selectedResultsModel !== null && modelIds.includes(selectedResultsModel);
            if (!hasValidSelection) {
                handleResultsModelChange(modelIds[0]);
            }
            return;
        }

        if (existingResultsMode === 'plan-level' && selectedResultsModel !== null) {
            handleResultsModelChange(null);
        }
    }, [existingResultsMode, plan?.models, resultForms.length, selectedResultsModel, handleResultsModelChange]);

    // Save result
    const saveResult = async (index: number) => {
        if (!cycle) return;

        const form = resultForms[index];
        setSavingResult(index);
        setResultsError(null);

        try {
            const payload: any = {
                plan_metric_id: form.metric_id,
                model_id: selectedResultsModel,
            };

            if (form.skipped) {
                payload.narrative = form.narrative;
            } else if (form.evaluation_type === 'Quantitative') {
                payload.numeric_value = form.numeric_value ? parseFloat(form.numeric_value) : null;
                payload.narrative = form.narrative || null;
            } else {
                payload.outcome_value_id = form.outcome_value_id;
                payload.narrative = form.narrative;
            }

            let response;
            if (form.existingResultId) {
                response = await api.patch(`/monitoring/results/${form.existingResultId}`, payload);
            } else {
                response = await api.post(`/monitoring/cycles/${cycle.cycle_id}/results`, payload);
            }

            // Update form with saved data
            setResultForms(prev => {
                const updated = [...prev];
                updated[index] = {
                    ...updated[index],
                    existingResultId: response.data.result_id,
                    calculatedOutcome: response.data.calculated_outcome,
                    dirty: false,
                };
                return updated;
            });

            // Refresh all results
            const resultsResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}/results`);
            setAllCycleResults(resultsResp.data || []);

            // Refresh cycle detail
            const cycleResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}`);
            setCycle(cycleResp.data);
        } catch (err: any) {
            setResultsError(err.response?.data?.detail || 'Failed to save result');
        } finally {
            setSavingResult(null);
        }
    };

    // Delete result
    const deleteResult = async (index: number) => {
        if (!cycle) return;

        const form = resultForms[index];
        if (!form.existingResultId) return;

        setDeletingResult(index);
        setResultsError(null);

        try {
            await api.delete(`/monitoring/results/${form.existingResultId}`);

            // Reset form
            setResultForms(prev => {
                const updated = [...prev];
                updated[index] = {
                    ...updated[index],
                    existingResultId: null,
                    numeric_value: '',
                    outcome_value_id: null,
                    narrative: '',
                    calculatedOutcome: null,
                    dirty: false,
                    skipped: false,
                };
                return updated;
            });

            // Refresh results
            const resultsResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}/results`);
            setAllCycleResults(resultsResp.data || []);

            // Refresh cycle
            const cycleResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}`);
            setCycle(cycleResp.data);
        } catch (err: any) {
            setResultsError(err.response?.data?.detail || 'Failed to delete result');
        } finally {
            setDeletingResult(null);
        }
    };

    // Auto-select grid view for large datasets
    useEffect(() => {
        if (plan?.models && versionDetail?.metric_snapshots) {
            const models = plan.models.length;
            const metrics = versionDetail.metric_snapshots.filter(m => m.original_metric_id !== null).length;
            const totalCells = models * metrics;
            // Auto-switch to grid for 10+ cells
            if (totalCells >= 10) {
                setViewMode('grid');
            }
        }
    }, [plan, versionDetail]);

    // Grid view handlers
    const handleGridSaveResult = async (payload: ResultSavePayload) => {
        if (!cycle) return;

        // Find if we have an existing result
        const existingResult = allCycleResults.find(
            r => r.model_id === payload.model_id && r.plan_metric_id === payload.plan_metric_id
        );

        const apiPayload: any = {
            plan_metric_id: payload.plan_metric_id,
            model_id: payload.model_id,
        };

        if (payload.numeric_value !== undefined && payload.numeric_value !== null) {
            apiPayload.numeric_value = payload.numeric_value;
        }
        if (payload.outcome_value_id !== undefined && payload.outcome_value_id !== null) {
            apiPayload.outcome_value_id = payload.outcome_value_id;
        }
        if (payload.narrative) {
            apiPayload.narrative = payload.narrative;
        }

        if (existingResult) {
            // PATCH uses /monitoring/results/{result_id} without cycle_id
            await api.patch(`/monitoring/results/${existingResult.result_id}`, apiPayload);
        } else {
            await api.post(`/monitoring/cycles/${cycle.cycle_id}/results`, apiPayload);
        }

        // Refresh results
        const resultsResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}/results`);
        setAllCycleResults(resultsResp.data || []);

        // Refresh cycle counts
        const cycleResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}`);
        setCycle(cycleResp.data);
    };

    const handleOpenBreachAnnotation = (cell: CellPosition, result: GridMonitoringResult | null) => {
        // Find the metric info
        const metric = versionDetail?.metric_snapshots.find(
            m => m.original_metric_id === cell.metricId
        );
        const model = plan?.models?.find(m => m.model_id === cell.modelId);

        setBreachPanelResultId(result?.result_id ?? null);
        setBreachPanelCellIds({ modelId: cell.modelId, metricId: cell.metricId });
        setBreachPanelMetricInfo({
            metricName: metric?.kpm_name || 'Unknown Metric',
            modelName: model?.model_name || 'Unknown Model',
            numericValue: result?.numeric_value ?? null,
            outcome: result?.calculated_outcome ?? null,
            thresholds: {
                yellow_min: metric?.yellow_min ?? null,
                yellow_max: metric?.yellow_max ?? null,
                red_min: metric?.red_min ?? null,
                red_max: metric?.red_max ?? null,
            },
        });
        setBreachPanelNarrative(result?.narrative ?? '');
        if (cycle) {
            loadBreachRecommendations(cycle.cycle_id, cell.modelId, cell.metricId);
        } else {
            setBreachPanelRecommendations([]);
        }
        setBreachPanelOpen(true);
    };

    const handleBreachAnnotationSave = async (narrative: string) => {
        if (!cycle) return;

        // The breach panel might not have a result yet - we need to find or create one
        // For now, assume a result exists if the panel was opened
        if (breachPanelResultId) {
            await api.patch(`/monitoring/results/${breachPanelResultId}`, {
                narrative,
            });

            // Refresh results
            const resultsResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}/results`);
            setAllCycleResults(resultsResp.data || []);
        }
    };

    const handleBreachValueChange = async (newValue: number | null) => {
        if (!cycle || !breachPanelResultId) return;

        // Update the result with the new value
        const response = await api.patch(`/monitoring/results/${breachPanelResultId}`, {
            numeric_value: newValue,
        });

        // Refresh results
        const resultsResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}/results`);
        setAllCycleResults(resultsResp.data || []);

        // Refresh cycle counts (in case outcome color changed)
        const cycleResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}`);
        setCycle(cycleResp.data);

        // Update the breach panel with new value and outcome
        if (breachPanelMetricInfo) {
            setBreachPanelMetricInfo({
                ...breachPanelMetricInfo,
                numericValue: newValue,
                outcome: response.data.calculated_outcome || null,
            });
        }
    };

    // Handler for creating recommendation from breach panel
    const handleCreateRecommendation = async () => {
        if (!canCreateRecommendation) {
            return;
        }
        // Close the breach panel first
        setBreachPanelOpen(false);

        try {
            // Fetch required data for the modal in parallel
            const [usersResp, taxonomiesResp] = await Promise.all([
                api.get('/auth/users'),
                api.get('/taxonomies/')
            ]);

            // Find priority and category taxonomies
            const priorityTaxonomy = taxonomiesResp.data.find((t: any) => t.name === 'Recommendation Priority');
            const categoryTaxonomy = taxonomiesResp.data.find((t: any) => t.name === 'Recommendation Category');

            // Fetch values for each taxonomy
            const [prioritiesResp, categoriesResp] = await Promise.all([
                priorityTaxonomy ? api.get(`/taxonomies/${priorityTaxonomy.taxonomy_id}`) : Promise.resolve({ data: { values: [] } }),
                categoryTaxonomy ? api.get(`/taxonomies/${categoryTaxonomy.taxonomy_id}`) : Promise.resolve({ data: { values: [] } })
            ]);

            setRecModalData({
                users: usersResp.data.filter((u: any) => u.is_active !== false),
                priorities: (prioritiesResp.data.values || []).filter((v: any) => v.is_active),
                categories: (categoriesResp.data.values || []).filter((v: any) => v.is_active)
            });
            setShowRecModal(true);
        } catch (err) {
            console.error('Failed to load recommendation modal data:', err);
        }
    };

    // Handler for recommendation modal close
    const handleRecModalClose = () => {
        setShowRecModal(false);
        setRecModalData(null);
    };

    // Handler for successful recommendation creation
    const handleRecCreated = () => {
        setShowRecModal(false);
        setRecModalData(null);
        // Optionally refresh cycle data to reflect any changes
    };

    const handleCSVImportComplete = async () => {
        if (!cycle) return;

        // Refresh all data after CSV import
        const resultsResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}/results`);
        setAllCycleResults(resultsResp.data || []);

        const cycleResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}`);
        setCycle(cycleResp.data);

        setShowCSVImport(false);
    };

    const loadBreachRecommendations = async (cycleIdValue: number, modelId: number, metricId: number) => {
        setBreachPanelRecommendations([]);
        setBreachPanelRecommendationsLoading(true);
        setBreachPanelRecommendationsError(null);

        try {
            const response = await api.get('/recommendations/', {
                params: {
                    monitoring_cycle_id: cycleIdValue,
                    model_id: modelId,
                    limit: 200
                }
            });
            const recommendations = (response.data || []).filter(
                (rec: LinkedRecommendation) => rec.plan_metric_id === metricId
            );
            setBreachPanelRecommendations(recommendations);
        } catch (err: any) {
            setBreachPanelRecommendationsError(
                err.response?.data?.detail || 'Failed to load linked recommendations'
            );
        } finally {
            setBreachPanelRecommendationsLoading(false);
        }
    };

    // Approval handlers
    const canApprove = (approval: CycleApproval): boolean => {
        return approval.can_approve;
    };

    const canVoid = (approval: CycleApproval): boolean => {
        if (!isAdminUser) return false;
        if (approval.approval_status === 'Approved') return false;
        if (approval.voided_at) return false;
        return true;
    };

    const openApprovalModal = (approval: CycleApproval, type: 'approve' | 'reject' | 'void') => {
        setSelectedApproval(approval);
        setApprovalModalType(type);
        setApprovalComments('');
        setApprovalEvidence('');
        setApprovalError(null);
    };

    const closeApprovalModal = () => {
        setApprovalModalType(null);
        setSelectedApproval(null);
        setApprovalComments('');
        setApprovalEvidence('');
        setApprovalError(null);
    };

    const handleApprovalSubmit = async () => {
        if (!selectedApproval || !cycle || !approvalModalType) return;

        if ((approvalModalType === 'reject' || approvalModalType === 'void') && !approvalComments.trim()) {
            setApprovalError(`${approvalModalType === 'reject' ? 'Rejection reason' : 'Void reason'} is required`);
            return;
        }

        setApprovalLoading(true);
        setApprovalError(null);

        try {
            const endpoint = `/monitoring/cycles/${cycle.cycle_id}/approvals/${selectedApproval.approval_id}/${approvalModalType}`;
            const payload = approvalModalType === 'void'
                ? { void_reason: approvalComments }
                : {
                    comments: approvalComments || null,
                    approval_evidence: approvalEvidence || null
                };

            await api.post(endpoint, payload);

            // Refresh cycle
            const cycleResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}`);
            setCycle(cycleResp.data);

            closeApprovalModal();
        } catch (err: any) {
            setApprovalError(err.response?.data?.detail || `Failed to ${approvalModalType} approval`);
        } finally {
            setApprovalLoading(false);
        }
    };

    // Submit cycle handler (DATA_COLLECTION -> UNDER_REVIEW)
    const handleSubmitCycle = async () => {
        if (!cycle) return;

        setSubmittingCycle(true);
        setSubmitCycleError(null);

        try {
            await api.post(`/monitoring/cycles/${cycle.cycle_id}/submit`);

            // Refresh cycle
            const cycleResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}`);
            setCycle(cycleResp.data);
        } catch (err: any) {
            setSubmitCycleError(err.response?.data?.detail || 'Failed to submit cycle');
        } finally {
            setSubmittingCycle(false);
        }
    };

    // Request approval handler
    const handleRequestApproval = async () => {
        if (!cycle) return;

        setRequestingApproval(true);
        setRequestApprovalError(null);

        try {
            await api.post(`/monitoring/cycles/${cycle.cycle_id}/request-approval`, {
                report_url: reportUrl || null,
            });

            // Success - refresh cycle and close modal
            const cycleResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}`);
            setCycle(cycleResp.data);
            setShowRequestApprovalModal(false);
            setReportUrl('');
        } catch (err: any) {
            const errorData = err.response?.data?.detail;

            // Check for breach protocol error
            if (typeof errorData === 'object' && errorData.error === 'breach_justification_required') {
                // Transform to BreachItem format
                const breaches: BreachItem[] = errorData.missing_justifications.map((item: any) => ({
                    result_id: item.result_id,
                    metric_name: item.metric_name,
                    model_name: item.model_name || 'Plan-level',
                    numeric_value: item.numeric_value,
                }));
                setPendingBreaches(breaches);
                setShowBreachWizard(true);
                setShowRequestApprovalModal(false);
            } else {
                setRequestApprovalError(typeof errorData === 'string' ? errorData : 'Failed to request approval');
            }
        } finally {
            setRequestingApproval(false);
        }
    };

    // Breach resolution handlers
    const handleBreachResolutionComplete = async (resolutions: BreachResolution[]) => {
        if (!cycle) return;

        setBreachResolutionLoading(true);

        try {
            // Save each narrative
            for (const resolution of resolutions) {
                await api.patch(`/monitoring/results/${resolution.result_id}`, {
                    narrative: resolution.narrative,
                });
            }

            // Refresh results
            const resultsResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}/results`);
            setAllCycleResults(resultsResp.data || []);

            // Close breach wizard
            setShowBreachWizard(false);
            setPendingBreaches([]);

            // Re-attempt request approval
            await api.post(`/monitoring/cycles/${cycle.cycle_id}/request-approval`, {
                report_url: reportUrl || null,
            });

            // Refresh cycle
            const cycleResp = await api.get(`/monitoring/cycles/${cycle.cycle_id}`);
            setCycle(cycleResp.data);
        } catch (err: any) {
            console.error('Error during breach resolution:', err);
            // Still close the wizard and show the request approval modal with error
            setShowBreachWizard(false);
            setPendingBreaches([]);
            setShowRequestApprovalModal(true);
            setRequestApprovalError(err.response?.data?.detail || 'Failed to complete approval request');
        } finally {
            setBreachResolutionLoading(false);
        }
    };

    const handleBreachResolutionCancel = () => {
        setShowBreachWizard(false);
        setPendingBreaches([]);
    };

    // Status badge styling
    const getStatusBadgeColor = (status: string) => {
        switch (status) {
            case 'PENDING': return 'bg-gray-100 text-gray-800';
            case 'DATA_COLLECTION': return 'bg-blue-100 text-blue-800';
            case 'ON_HOLD': return 'bg-orange-100 text-orange-800';
            case 'UNDER_REVIEW': return 'bg-yellow-100 text-yellow-800';
            case 'PENDING_APPROVAL': return 'bg-purple-100 text-purple-800';
            case 'APPROVED': return 'bg-green-100 text-green-800';
            case 'CANCELLED': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getFilenameFromDisposition = (disposition?: string) => {
        if (!disposition) return null;
        const match = disposition.match(/filename="?([^"]+)"?/i);
        return match ? match[1] : null;
    };

    const handleDownloadReport = async () => {
        if (!cycle) return;

        try {
            setDownloadingReport(true);
            const response = await api.get(
                `/monitoring/cycles/${cycle.cycle_id}/report/pdf`,
                { responseType: 'blob' }
            );
            const filename =
                getFilenameFromDisposition(response.headers?.['content-disposition']) ||
                `monitoring_cycle_${cycle.cycle_id}.pdf`;
            const url = URL.createObjectURL(response.data);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
        } catch (err: any) {
            console.error('Failed to download monitoring report:', err);
            alert(err.response?.data?.detail || 'Failed to download monitoring report.');
        } finally {
            setDownloadingReport(false);
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            </Layout>
        );
    }

    if (error || !cycle) {
        return (
            <Layout>
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                    {error || 'Cycle not found'}
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            {/* Breadcrumb */}
            <nav className="flex items-center gap-2 text-sm text-gray-600 mb-6">
                <Link to={monitoringHomePath} className="hover:text-blue-600">{monitoringHomeLabel}</Link>
                <span>/</span>
                <Link to={`/monitoring/${cycle.plan_id}`} className="hover:text-blue-600">
                    {plan?.name || `Plan ${cycle.plan_id}`}
                </Link>
                <span>/</span>
                <span className="text-gray-900 font-medium">
                    Cycle {formatPeriod(cycle.period_start_date, cycle.period_end_date)}
                </span>
            </nav>

            {/* Header */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">
                            {formatPeriod(cycle.period_start_date, cycle.period_end_date)}
                        </h1>
                        <div className="flex items-center gap-4 mt-2">
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadgeColor(cycle.status)}`}>
                                {cycle.status.replace(/_/g, ' ')}
                            </span>
                            {cycle.is_overdue && (
                                <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-sm">
                                    {cycle.days_overdue} days overdue
                                </span>
                            )}
                            {cycle.version_number && (
                                <span className="text-sm text-gray-600">
                                    v{cycle.version_number}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Results summary and actions */}
                    <div className="flex items-center gap-6">
                        {['PENDING_APPROVAL', 'APPROVED'].includes(cycle.status) && canDownloadReport && (
                            <button
                                onClick={handleDownloadReport}
                                disabled={downloadingReport}
                                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                            >
                                {downloadingReport ? 'Downloading...' : 'Report PDF'}
                            </button>
                        )}

                        {/* Submit Cycle Button - only when DATA_COLLECTION */}
                        {cycle.status === 'DATA_COLLECTION' && (
                            <button
                                onClick={handleSubmitCycle}
                                disabled={submittingCycle}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                            >
                                {submittingCycle ? (
                                    <>
                                        <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Submitting...
                                    </>
                                ) : (
                                    <>
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        Submit Cycle
                                    </>
                                )}
                            </button>
                        )}

                        {/* Request Approval Button - only when UNDER_REVIEW */}
                        {cycle.status === 'UNDER_REVIEW' && (
                            <button
                                onClick={() => setShowRequestApprovalModal(true)}
                                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center gap-2"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Request Approval
                            </button>
                        )}
                    </div>
                </div>

                {/* Submit Cycle Error Display */}
                {submitCycleError && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                        {submitCycleError}
                    </div>
                )}

                {/* Key dates */}
                <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t">
                    <div>
                        <span className="text-xs text-gray-500">Period</span>
                        <p className="font-medium">{cycle.period_start_date} to {cycle.period_end_date}</p>
                    </div>
                    <div>
                        <span className="text-xs text-gray-500">
                            {cycle.status === 'ON_HOLD' ? 'Hold Until' : 'Submission Due'}
                        </span>
                        <p className="font-medium">
                            {cycle.postponed_due_date || cycle.submission_due_date}
                        </p>
                    </div>
                    <div>
                        <span className="text-xs text-gray-500">Report Due</span>
                        <p className="font-medium">{cycle.report_due_date}</p>
                    </div>
                    <div>
                        <span className="text-xs text-gray-500">Assigned To</span>
                        <p className="font-medium">{cycle.assigned_to_name || '-'}</p>
                    </div>
                    {cycle.original_due_date && cycle.postponed_due_date && (
                        <div>
                            <span className="text-xs text-gray-500">Original Due</span>
                            <p className="font-medium">{cycle.original_due_date}</p>
                        </div>
                    )}
                    {typeof cycle.postponement_count === 'number' && (
                        <div>
                            <span className="text-xs text-gray-500">Postponements</span>
                            <p className="font-medium">{cycle.postponement_count}</p>
                        </div>
                    )}
                    {cycle.status === 'ON_HOLD' && cycle.hold_reason && (
                        <div>
                            <span className="text-xs text-gray-500">Hold Reason</span>
                            <p className="font-medium">{cycle.hold_reason}</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="flex gap-4">
                    <button
                        onClick={() => setActiveTab('results')}
                        className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                            activeTab === 'results'
                                ? 'border-blue-600 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                    >
                        Results ({cycle.result_count})
                    </button>
                    <button
                        onClick={() => setActiveTab('approvals')}
                        className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                            activeTab === 'approvals'
                                ? 'border-blue-600 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                    >
                        Approvals ({cycle.approval_count})
                        {cycle.pending_approval_count > 0 && (
                            <span className="ml-2 px-2 py-0.5 bg-amber-100 text-amber-800 rounded-full text-xs">
                                {cycle.pending_approval_count} pending
                            </span>
                        )}
                    </button>
                </nav>
            </div>

            {/* Tab Content */}
            {activeTab === 'results' && (
                <div className="space-y-4">
                    {/* Results toolbar */}
                    <div className="bg-white rounded-lg shadow px-4 py-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            {/* View toggle */}
                            <span className="text-sm text-gray-600 mr-2">View:</span>
                            <div className="inline-flex rounded-md shadow-sm">
                                <button
                                    onClick={() => setViewMode('card')}
                                    className={`px-3 py-1.5 text-sm font-medium rounded-l-md border ${
                                        viewMode === 'card'
                                            ? 'bg-blue-600 text-white border-blue-600'
                                            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                                    }`}
                                >
                                    <span className="flex items-center gap-1">
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                                        </svg>
                                        Card
                                    </span>
                                </button>
                                <button
                                    onClick={() => setViewMode('grid')}
                                    className={`px-3 py-1.5 text-sm font-medium rounded-r-md border border-l-0 ${
                                        viewMode === 'grid'
                                            ? 'bg-blue-600 text-white border-blue-600'
                                            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                                    }`}
                                >
                                    <span className="flex items-center gap-1">
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                                        </svg>
                                        Grid
                                    </span>
                                </button>
                            </div>
                        </div>

                        {/* Import CSV button - only show when cycle can be edited */}
                        {['DATA_COLLECTION', 'UNDER_REVIEW'].includes(cycle.status) && (
                            <button
                                onClick={() => setShowCSVImport(true)}
                                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-1"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                                </svg>
                                Import CSV
                            </button>
                        )}
                    </div>

                    {/* Results content */}
                    <div className="bg-white rounded-lg shadow">
                        {viewMode === 'grid' && versionDetail ? (
                            <MonitoringDataGrid
                                cycleId={cycle.cycle_id}
                                metrics={versionDetail.metric_snapshots.filter(m => m.original_metric_id !== null)}
                                models={plan?.models || []}
                                existingResults={allCycleResults}
                                outcomeValues={outcomeValues}
                                onSaveResult={handleGridSaveResult}
                                onOpenBreachAnnotation={handleOpenBreachAnnotation}
                                readOnly={!['DATA_COLLECTION', 'UNDER_REVIEW'].includes(cycle.status)}
                            />
                        ) : (
                            <CycleResultsPanel
                                cycle={cycle}
                                versionDetail={versionDetail}
                                resultForms={resultForms}
                                models={plan?.models || []}
                                outcomeValues={outcomeValues}
                                selectedModel={selectedResultsModel}
                                existingResultsMode={existingResultsMode}
                                loadingResults={loadingResults}
                                savingResult={savingResult}
                                deletingResult={deletingResult}
                                resultsError={resultsError}
                                onResultChange={handleResultChange}
                                onSkipToggle={handleSkipToggle}
                                onSaveResult={saveResult}
                                onDeleteResult={deleteResult}
                                onModelChange={handleResultsModelChange}
                                onClose={() => {}}
                            />
                        )}
                    </div>
                </div>
            )}

            {activeTab === 'approvals' && (
                <div className="bg-white rounded-lg shadow p-6">
                    <CycleApprovalPanel
                        approvals={cycle.approvals || []}
                        reportUrl={cycle.report_url}
                        canApprove={canApprove}
                        canVoid={canVoid}
                        onApprove={(approval) => openApprovalModal(approval, 'approve')}
                        onReject={(approval) => openApprovalModal(approval, 'reject')}
                        onVoid={(approval) => openApprovalModal(approval, 'void')}
                    />
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
                                 'Void'} {selectedApproval.approval_type === 'Global' ? 'Global Approval' : `${selectedApproval.region?.region_name || 'Regional'} Approval`}
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
                                        You are about to approve this monitoring cycle.
                                    </p>
                                </div>
                            )}

                            {approvalModalType === 'reject' && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                    <p className="text-red-800 text-sm">
                                        Rejecting will return the cycle to Under Review status.
                                    </p>
                                </div>
                            )}

                            {approvalModalType === 'void' && (
                                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                                    <p className="text-amber-800 text-sm">
                                        Voiding removes this approval requirement.
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
                                        approvalModalType === 'reject' ? 'Please explain why...' :
                                        'Please explain why...'
                                    }
                                />
                            </div>

                            {/* Approval Evidence - Required for Admin proxy approvals */}
                            {approvalModalType === 'approve' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Approval Evidence *
                                    </label>
                                    <textarea
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                        rows={2}
                                        value={approvalEvidence}
                                        onChange={(e) => setApprovalEvidence(e.target.value)}
                                        placeholder="e.g., Meeting minutes from 2025-03-15, email confirmation from approver..."
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        Required when approving on behalf of designated approvers (e.g., meeting minutes, email confirmation)
                                    </p>
                                </div>
                            )}
                        </div>

                        <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                            <button
                                onClick={closeApprovalModal}
                                disabled={approvalLoading}
                                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleApprovalSubmit}
                                disabled={approvalLoading || ((approvalModalType === 'reject' || approvalModalType === 'void') && !approvalComments.trim())}
                                className={`px-4 py-2 rounded-lg text-white ${
                                    approvalModalType === 'approve' ? 'bg-green-600 hover:bg-green-700' :
                                    approvalModalType === 'reject' ? 'bg-red-600 hover:bg-red-700' :
                                    'bg-gray-600 hover:bg-gray-700'
                                } disabled:opacity-50`}
                            >
                                {approvalLoading ? 'Processing...' :
                                    approvalModalType === 'approve' ? 'Approve' :
                                    approvalModalType === 'reject' ? 'Reject' : 'Void'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Request Approval Modal */}
            {showRequestApprovalModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
                        <div className="p-4 border-b bg-purple-50">
                            <h3 className="text-lg font-bold text-purple-900">Request Approval</h3>
                        </div>

                        <div className="p-4 space-y-4">
                            {requestApprovalError && (
                                <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                                    {requestApprovalError}
                                </div>
                            )}

                            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                                <p className="text-purple-800 text-sm">
                                    Submitting this cycle for approval will create approval requirements for all applicable approvers.
                                </p>
                            </div>

                            {cycle?.red_count ? (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                    <p className="text-red-800 text-sm font-medium">
                                        This cycle has {cycle.red_count} RED result(s).
                                    </p>
                                    <p className="text-red-700 text-sm mt-1">
                                        Breach justification narratives must be provided for all RED metrics before approval can be requested.
                                    </p>
                                </div>
                            ) : null}

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Report URL (optional)
                                </label>
                                <input
                                    type="url"
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                    value={reportUrl}
                                    onChange={(e) => setReportUrl(e.target.value)}
                                    placeholder="https://sharepoint.com/..."
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Link to the monitoring report document (SharePoint, etc.)
                                </p>
                            </div>
                        </div>

                        <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                            <button
                                onClick={() => {
                                    setShowRequestApprovalModal(false);
                                    setReportUrl('');
                                    setRequestApprovalError(null);
                                }}
                                disabled={requestingApproval}
                                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleRequestApproval}
                                disabled={requestingApproval}
                                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                            >
                                {requestingApproval ? 'Requesting...' : 'Request Approval'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Breach Resolution Wizard */}
            {showBreachWizard && (
                <BreachResolutionWizard
                    breaches={pendingBreaches}
                    onComplete={handleBreachResolutionComplete}
                    onCancel={handleBreachResolutionCancel}
                    isLoading={breachResolutionLoading}
                />
            )}

            {/* Breach Annotation Panel */}
            <BreachAnnotationPanel
                isOpen={breachPanelOpen}
                resultId={breachPanelResultId}
                metricInfo={breachPanelMetricInfo}
                existingNarrative={breachPanelNarrative}
                readOnly={resultsReadOnly}
                linkedRecommendations={breachPanelRecommendations}
                linkedRecommendationsLoading={breachPanelRecommendationsLoading}
                linkedRecommendationsError={breachPanelRecommendationsError}
                onSave={handleBreachAnnotationSave}
                onValueChange={resultsReadOnly ? undefined : handleBreachValueChange}
                onCreateRecommendation={canCreateRecommendation ? handleCreateRecommendation : undefined}
                onClose={() => setBreachPanelOpen(false)}
            />

            {/* Recommendation Create Modal (from breach panel) */}
            {showRecModal && breachPanelCellIds && cycle && recModalData && plan?.models && (
                <RecommendationCreateModal
                    onClose={handleRecModalClose}
                    onCreated={handleRecCreated}
                    models={plan.models}
                    users={recModalData.users}
                    priorities={recModalData.priorities}
                    categories={recModalData.categories}
                    preselectedModelId={breachPanelCellIds.modelId}
                    preselectedMonitoringCycleId={cycle.cycle_id}
                    preselectedPlanMetricId={breachPanelCellIds.metricId}
                    preselectedCategoryId={monitoringCategoryId || undefined}
                    preselectedTitle={`Address RED monitoring result for ${breachPanelMetricInfo?.metricName || 'metric'}`}
                    preselectedDescription={
                        `This recommendation was created to track remediation of a RED monitoring result.\n\n` +
                        `Model: ${breachPanelMetricInfo?.modelName || 'Unknown'}\n` +
                        `Metric: ${breachPanelMetricInfo?.metricName || 'Unknown'}\n` +
                        `Value: ${breachPanelMetricInfo?.numericValue?.toFixed(4) || 'N/A'}\n` +
                        `Period: ${formatPeriod(cycle.period_start_date, cycle.period_end_date)}`
                    }
                />
            )}

            {/* CSV Import Modal */}
            {showCSVImport && versionDetail && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
                        <MonitoringCSVImport
                            cycleId={cycle.cycle_id}
                            metrics={versionDetail.metric_snapshots.filter(m => m.original_metric_id !== null)}
                            models={plan?.models || []}
                            onImportComplete={handleCSVImportComplete}
                            onClose={() => setShowCSVImport(false)}
                        />
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default MonitoringCycleDetailPage;

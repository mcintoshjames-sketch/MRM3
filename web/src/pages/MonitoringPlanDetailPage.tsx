import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import Layout from '../components/Layout';
import TrendChartModal from '../components/TrendChartModal';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';

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
    model_id_str?: string;
}

interface KpmRef {
    kpm_id: number;
    name: string;
    category_id: number;
    category_name: string | null;
    evaluation_type: string;
}

interface PlanMetric {
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
    user_permissions?: UserPermissions;
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
    approval_count: number;
    pending_approval_count: number;
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
    skipped: boolean;  // Whether this metric is being skipped (requires explanation)
    // Inline trend context
    previousValue: number | null;
    previousOutcome: string | null;
    previousPeriod: string | null;
}

// Phase 7: Reporting & Trends
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

type TabType = 'dashboard' | 'models' | 'metrics' | 'versions' | 'cycles';

// Bullet Chart Component for threshold visualization
const BulletChart: React.FC<{
    value: number | null;
    yellowMin: number | null;
    yellowMax: number | null;
    redMin: number | null;
    redMax: number | null;
    width?: number;
    height?: number;
}> = ({ value, yellowMin, yellowMax, redMin, redMax, width = 200, height = 24 }) => {
    // Determine the metric type and calculate range
    // Type 1: Lower is better (yellowMax and redMax set) - G < yellowMax < Y < redMax < R
    // Type 2: Higher is better (yellowMin and redMin set) - R < redMin < Y < yellowMin < G
    // Type 3: Range-based (yellowMin AND yellowMax set) - Green is within the range
    const isLowerBetter = yellowMax !== null && redMax !== null;
    const isHigherBetter = yellowMin !== null && redMin !== null;
    const isRangeBased = yellowMin !== null && yellowMax !== null && !isLowerBetter && !isHigherBetter;

    // Check if any thresholds are configured
    const hasAnyThreshold = yellowMin !== null || yellowMax !== null || redMin !== null || redMax !== null;

    if (!hasAnyThreshold) {
        return <span className="text-xs text-gray-400 italic">No thresholds</span>;
    }

    // Calculate min/max for the chart
    let minVal: number, maxVal: number;
    if (isLowerBetter) {
        minVal = 0;
        maxVal = (redMax || 0) * 1.3; // Add 30% padding
    } else if (isHigherBetter) {
        minVal = (redMin || 0) * 0.7; // 30% padding below
        maxVal = (yellowMin || 0) * 1.3; // 30% padding above
    } else if (isRangeBased) {
        // Range-based: show yellowMin to yellowMax with padding
        minVal = (yellowMin || 0) * 0.7;
        maxVal = (yellowMax || 0) * 1.3;
    } else {
        // Partial thresholds - just show what we have
        const allVals = [yellowMin, yellowMax, redMin, redMax].filter(v => v !== null) as number[];
        minVal = Math.min(...allVals) * 0.7;
        maxVal = Math.max(...allVals) * 1.3;
    }
    const range = maxVal - minVal || 1; // Avoid division by zero

    const getPosition = (val: number) => Math.max(0, Math.min(100, ((val - minVal) / range) * 100));

    return (
        <div className="relative" style={{ width, height }}>
            {/* Background segments */}
            <div className="absolute inset-0 flex rounded-sm overflow-hidden">
                {isLowerBetter ? (
                    <>
                        <div
                            className="bg-green-200 h-full"
                            style={{ width: `${getPosition(yellowMax || 0)}%` }}
                        />
                        <div
                            className="bg-yellow-200 h-full"
                            style={{ width: `${getPosition(redMax || 0) - getPosition(yellowMax || 0)}%` }}
                        />
                        <div
                            className="bg-red-200 h-full flex-1"
                        />
                    </>
                ) : isHigherBetter ? (
                    <>
                        <div
                            className="bg-red-200 h-full"
                            style={{ width: `${getPosition(redMin || 0)}%` }}
                        />
                        <div
                            className="bg-yellow-200 h-full"
                            style={{ width: `${getPosition(yellowMin || 0) - getPosition(redMin || 0)}%` }}
                        />
                        <div
                            className="bg-green-200 h-full flex-1"
                        />
                    </>
                ) : isRangeBased ? (
                    // Range-based: Yellow on both edges, Green in the middle
                    <>
                        <div
                            className="bg-yellow-200 h-full"
                            style={{ width: `${getPosition(yellowMin || 0)}%` }}
                        />
                        <div
                            className="bg-green-200 h-full"
                            style={{ width: `${getPosition(yellowMax || 0) - getPosition(yellowMin || 0)}%` }}
                        />
                        <div
                            className="bg-yellow-200 h-full flex-1"
                        />
                    </>
                ) : (
                    // Partial thresholds - show gray with threshold markers
                    <div className="bg-gray-200 h-full flex-1" />
                )}
            </div>
            {/* Value marker */}
            {value !== null && (
                <div
                    className="absolute top-0 bottom-0 w-0.5 bg-gray-800"
                    style={{ left: `${Math.min(100, Math.max(0, getPosition(value)))}%` }}
                >
                    <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-gray-800 rotate-45" />
                </div>
            )}
            {/* Threshold lines */}
            {isLowerBetter && yellowMax !== null && (
                <div
                    className="absolute top-0 bottom-0 w-px bg-yellow-600"
                    style={{ left: `${getPosition(yellowMax)}%` }}
                />
            )}
            {isLowerBetter && redMax !== null && (
                <div
                    className="absolute top-0 bottom-0 w-px bg-red-600"
                    style={{ left: `${getPosition(redMax)}%` }}
                />
            )}
            {isHigherBetter && yellowMin !== null && (
                <div
                    className="absolute top-0 bottom-0 w-px bg-yellow-600"
                    style={{ left: `${getPosition(yellowMin)}%` }}
                />
            )}
            {isHigherBetter && redMin !== null && (
                <div
                    className="absolute top-0 bottom-0 w-px bg-red-600"
                    style={{ left: `${getPosition(redMin)}%` }}
                />
            )}
        </div>
    );
};

// Mini Sparkline for cycle outcomes
const CycleSparkline: React.FC<{ cycles: MonitoringCycle[] }> = ({ cycles }) => {
    const recentCycles = cycles
        .filter(c => c.status === 'APPROVED')
        .slice(0, 4)
        .reverse();

    if (recentCycles.length === 0) {
        return <span className="text-xs text-gray-400">No completed cycles</span>;
    }

    return (
        <div className="flex items-center gap-1">
            {recentCycles.map((cycle) => {
                const total = cycle.green_count + cycle.yellow_count + cycle.red_count;
                if (total === 0) {
                    return (
                        <div key={cycle.cycle_id} className="w-3 h-8 bg-gray-200 rounded-sm" title="No results" />
                    );
                }
                const greenPct = (cycle.green_count / total) * 100;
                const yellowPct = (cycle.yellow_count / total) * 100;
                const redPct = (cycle.red_count / total) * 100;
                const periodLabel = `${cycle.period_start_date.split('-').slice(1).join('/')} - ${cycle.period_end_date.split('-').slice(1).join('/')}`;
                return (
                    <div
                        key={cycle.cycle_id}
                        className="w-3 h-8 rounded-sm overflow-hidden flex flex-col"
                        title={`${periodLabel}: ${cycle.green_count}G ${cycle.yellow_count}Y ${cycle.red_count}R`}
                    >
                        {redPct > 0 && <div className="bg-red-500" style={{ height: `${redPct}%` }} />}
                        {yellowPct > 0 && <div className="bg-yellow-400" style={{ height: `${yellowPct}%` }} />}
                        {greenPct > 0 && <div className="bg-green-500" style={{ height: `${greenPct}%` }} />}
                    </div>
                );
            })}
            <span className="text-xs text-gray-500 ml-1">Last {recentCycles.length}</span>
        </div>
    );
};

const MonitoringPlanDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const { user } = useAuth();
    const [loading, setLoading] = useState(true);
    const [plan, setPlan] = useState<MonitoringPlan | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<TabType>('dashboard');

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
    const [deletingResult, setDeletingResult] = useState<number | null>(null);
    const [resultsError, setResultsError] = useState<string | null>(null);

    // Approval modal state
    const [approvalModalType, setApprovalModalType] = useState<'approve' | 'reject' | 'void' | null>(null);
    const [selectedApproval, setSelectedApproval] = useState<CycleApproval | null>(null);
    const [approvalComments, setApprovalComments] = useState('');
    const [approvalLoading, setApprovalLoading] = useState(false);
    const [approvalError, setApprovalError] = useState<string | null>(null);

    // Cancel cycle modal state
    const [showCancelModal, setShowCancelModal] = useState(false);
    const [cancelCycleId, setCancelCycleId] = useState<number | null>(null);
    const [cancelReason, setCancelReason] = useState('');

    // Phase 7: Performance summary state
    const [performanceSummary, setPerformanceSummary] = useState<PerformanceSummary | null>(null);
    const [loadingPerformance, setLoadingPerformance] = useState(false);
    const [exportingCycle, setExportingCycle] = useState<number | null>(null);

    // Trend chart modal state
    const [trendModalMetric, setTrendModalMetric] = useState<{
        metric_id: number;
        metric_name: string;
        thresholds: {
            yellow_min: number | null;
            yellow_max: number | null;
            red_min: number | null;
            red_max: number | null;
        };
    } | null>(null);

    // Version management state
    const [versions, setVersions] = useState<PlanVersion[]>([]);
    const [loadingVersions, setLoadingVersions] = useState(false);
    const [selectedVersionDetail, setSelectedVersionDetail] = useState<VersionDetail | null>(null);
    const [loadingVersionDetail, setLoadingVersionDetail] = useState(false);
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

    useEffect(() => {
        if (id) {
            fetchPlan();
            fetchCycles();
        }
    }, [id]);

    // Phase 7: Fetch performance summary when dashboard or cycles tab is selected
    useEffect(() => {
        if (id && (activeTab === 'dashboard' || activeTab === 'cycles')) {
            fetchPerformanceSummary();
        }
    }, [id, activeTab]);

    // Fetch versions when versions tab is selected
    useEffect(() => {
        if (id && activeTab === 'versions') {
            fetchVersions();
        }
    }, [id, activeTab]);

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

    // Phase 7: Fetch performance summary for History tab
    const fetchPerformanceSummary = async () => {
        setLoadingPerformance(true);
        try {
            const response = await api.get(`/monitoring/plans/${id}/performance-summary?cycles=10`);
            setPerformanceSummary(response.data);
        } catch (err) {
            console.error('Failed to load performance summary:', err);
        } finally {
            setLoadingPerformance(false);
        }
    };

    // Phase 7: Export cycle results as CSV
    const exportCycleCSV = async (cycleId: number) => {
        setExportingCycle(cycleId);
        try {
            const response = await api.get(`/monitoring/plans/${id}/cycles/${cycleId}/export`, {
                responseType: 'blob'
            });

            // Create blob link to download
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;

            // Get filename from content-disposition header or use default
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
    };

    // Version management functions
    const fetchVersions = async () => {
        setLoadingVersions(true);
        try {
            const response = await api.get(`/monitoring/plans/${id}/versions`);
            setVersions(response.data);
        } catch (err) {
            console.error('Failed to load versions:', err);
        } finally {
            setLoadingVersions(false);
        }
    };

    const fetchVersionDetail = async (versionId: number) => {
        setLoadingVersionDetail(true);
        try {
            const response = await api.get(`/monitoring/plans/${id}/versions/${versionId}`);
            setSelectedVersionDetail(response.data);
        } catch (err) {
            console.error('Failed to load version detail:', err);
        } finally {
            setLoadingVersionDetail(false);
        }
    };

    const handlePublishVersion = async (e: React.FormEvent) => {
        e.preventDefault();
        setPublishing(true);
        setPublishError(null);

        try {
            await api.post(`/monitoring/plans/${id}/versions/publish`, {
                version_name: publishForm.version_name || null,
                description: publishForm.description || null,
                effective_date: publishForm.effective_date || null
            });
            setShowPublishModal(false);
            setPublishForm({
                version_name: '',
                description: '',
                effective_date: new Date().toISOString().split('T')[0]
            });
            fetchVersions();
            fetchPlan(); // Refresh plan to get updated version count
        } catch (err: any) {
            setPublishError(err.response?.data?.detail || 'Failed to publish version');
        } finally {
            setPublishing(false);
        }
    };

    const exportVersionCSV = (version: VersionDetail) => {
        const headers = ['KPM Name', 'Category', 'Type', 'Yellow Min', 'Yellow Max', 'Red Min', 'Red Max', 'Guidance'];
        const rows = version.metric_snapshots.map(s => [
            s.kpm_name,
            s.kpm_category_name || '',
            s.evaluation_type,
            s.yellow_min?.toString() || '',
            s.yellow_max?.toString() || '',
            s.red_min?.toString() || '',
            s.red_max?.toString() || '',
            (s.qualitative_guidance || '').replace(/"/g, '""')
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${plan?.name || 'plan'}_v${version.version_number}_metrics_${version.effective_date}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    // Metric editing functions
    const openEditMetric = (metric: PlanMetric) => {
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
    };

    const handleSaveMetric = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingMetric) return;

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
            await api.patch(`/monitoring/plans/${id}/metrics/${editingMetric.metric_id}`, {
                yellow_min: metricForm.yellow_min ? parseFloat(metricForm.yellow_min) : null,
                yellow_max: metricForm.yellow_max ? parseFloat(metricForm.yellow_max) : null,
                red_min: metricForm.red_min ? parseFloat(metricForm.red_min) : null,
                red_max: metricForm.red_max ? parseFloat(metricForm.red_max) : null,
                qualitative_guidance: metricForm.qualitative_guidance || null
            });
            setShowMetricModal(false);
            setEditingMetric(null);
            fetchPlan(); // Refresh to show updated thresholds
        } catch (err: any) {
            setMetricError(err.response?.data?.detail || 'Failed to save metric');
        } finally {
            setSavingMetric(false);
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

    // Cancel cycle functions
    const openCancelModal = (cycleId: number) => {
        setCancelCycleId(cycleId);
        setCancelReason('');
        setActionError(null);
        setShowCancelModal(true);
    };

    const handleCancelCycle = async () => {
        if (!cancelCycleId || !cancelReason.trim()) return;

        setActionLoading(true);
        setActionError(null);

        try {
            await api.post(`/monitoring/cycles/${cancelCycleId}/cancel`, {
                cancel_reason: cancelReason.trim()
            });
            setShowCancelModal(false);
            setCancelCycleId(null);
            setCancelReason('');
            fetchCycles();
            if (selectedCycle?.cycle_id === cancelCycleId) {
                setSelectedCycle(null);
            }
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to cancel cycle');
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
            const qualitativeOutcomeTax = taxonomies.find((t: { name: string }) => t.name === 'Qualitative Outcome');
            if (qualitativeOutcomeTax) {
                // GET /taxonomies/{id} returns the taxonomy with values included
                const taxDetailResponse = await api.get(`/taxonomies/${qualitativeOutcomeTax.taxonomy_id}`);
                const values = taxDetailResponse.data.values || [];
                setOutcomeValues(values.filter((v: OutcomeValue & { is_active: boolean }) => v.is_active));
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
                    kpm_name: m.kpm?.name || 'Unknown',
                    evaluation_type: m.kpm?.evaluation_type || 'Quantitative',
                    yellow_min: m.yellow_min,
                    yellow_max: m.yellow_max,
                    red_min: m.red_min,
                    red_max: m.red_max,
                    qualitative_guidance: m.qualitative_guidance
                }));
            }

            // Find previous approved cycle for trend context
            const previousApprovedCycle = cycles.find(c =>
                c.status === 'APPROVED' &&
                c.period_end_date < cycle.period_end_date
            );
            let previousResults: MonitoringResult[] = [];
            let previousPeriodLabel: string | null = null;

            if (previousApprovedCycle) {
                try {
                    const prevResultsResponse = await api.get(`/monitoring/cycles/${previousApprovedCycle.cycle_id}/results`);
                    previousResults = prevResultsResponse.data;
                    previousPeriodLabel = formatPeriod(previousApprovedCycle.period_start_date, previousApprovedCycle.period_end_date);
                } catch {
                    // Silently fail - previous context is optional
                }
            }

            // Build form data for each metric
            const forms: ResultFormData[] = metricsToShow.map(m => {
                // Find existing result for this metric
                const existing = resultsResponse.data.find((r: MonitoringResult) =>
                    r.plan_metric_id === m.metric_id
                );

                // Find previous cycle's result for this metric
                const previousResult = previousResults.find((r: MonitoringResult) =>
                    r.plan_metric_id === m.metric_id
                );

                // Determine if this was a skipped metric (has narrative but no value)
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
                    skipped: wasSkipped ?? false,
                    // Inline trend context
                    previousValue: previousResult?.numeric_value ?? null,
                    previousOutcome: previousResult?.calculated_outcome ?? null,
                    previousPeriod: previousPeriodLabel
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
            if (form.evaluation_type === 'Quantitative' && field === 'numeric_value') {
                if (value !== '' && value !== null) {
                    const numValue = parseFloat(value as string);
                    if (!isNaN(numValue)) {
                        form.calculatedOutcome = calculateOutcome(numValue, form);
                    } else {
                        form.calculatedOutcome = null;
                    }
                } else {
                    // Value cleared - also clear the outcome
                    form.calculatedOutcome = null;
                }
            }

            // For qualitative/outcome-only, update calculated outcome from selected value
            if (field === 'outcome_value_id') {
                if (value !== null) {
                    const selectedOutcome = outcomeValues.find(o => o.value_id === value);
                    if (selectedOutcome) {
                        form.calculatedOutcome = selectedOutcome.code;
                    }
                } else {
                    // Outcome cleared
                    form.calculatedOutcome = null;
                }
            }

            updated[index] = form;
            return updated;
        });
    };

    const handleSkipToggle = (index: number, isSkipped: boolean) => {
        setResultForms(prev => {
            const updated = [...prev];
            const form = { ...updated[index], skipped: isSkipped, dirty: true };

            if (isSkipped) {
                // Clear value when skip is checked
                form.numeric_value = '';
                form.outcome_value_id = null;
                form.calculatedOutcome = null;
            }

            updated[index] = form;
            return updated;
        });
    };

    const saveResult = async (index: number) => {
        const form = resultForms[index];
        if (!resultsEntryCycle) return;

        // Validate skipped metrics require explanation
        if (form.skipped && !form.narrative.trim()) {
            setResultsError('An explanation is required when skipping a metric');
            return;
        }

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

    const deleteResult = async (index: number) => {
        const form = resultForms[index];
        if (!form.existingResultId) return;

        if (!window.confirm('Are you sure you want to delete this result? This cannot be undone.')) {
            return;
        }

        setDeletingResult(index);
        setResultsError(null);

        try {
            await api.delete(`/monitoring/results/${form.existingResultId}`);

            // Reset the form to empty state
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

            // Refresh cycles to update counts
            fetchCycles();
        } catch (err: any) {
            setResultsError(err.response?.data?.detail || 'Failed to delete result');
        } finally {
            setDeletingResult(null);
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

    // Permission checks based on user_permissions from API
    const permissions = plan?.user_permissions;
    const canCreateCycle = permissions?.can_start_cycle ?? user?.role === 'Admin';

    const getAvailableActions = (cycle: MonitoringCycle | CycleDetail) => {
        const actions: { label: string; action: string; variant: string; requiresConfirm?: boolean }[] = [];

        switch (cycle.status) {
            case 'PENDING':
                // Only Admin or team members (risk function) can start a cycle
                if (permissions?.can_start_cycle) {
                    actions.push({ label: 'Start Data Collection', action: 'start', variant: 'primary' });
                }
                break;
            case 'DATA_COLLECTION':
                // Data providers, team members, and admins can submit
                if (permissions?.can_submit_cycle) {
                    actions.push({ label: 'Submit for Review', action: 'submit', variant: 'primary' });
                }
                break;
            case 'UNDER_REVIEW':
                // Only Admin or team members (risk function) can request approval
                if (permissions?.can_request_approval) {
                    actions.push({ label: 'Request Approval', action: 'request-approval', variant: 'primary' });
                }
                break;
        }

        // Only Admin or team members (risk function) can cancel
        if (cycle.status !== 'APPROVED' && cycle.status !== 'CANCELLED' && permissions?.can_cancel_cycle) {
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
                        {([
                            { key: 'dashboard', label: 'Dashboard' },
                            { key: 'models', label: 'Models' },
                            { key: 'metrics', label: 'Metrics' },
                            { key: 'versions', label: 'Versions' },
                            { key: 'cycles', label: 'Cycles & Results' }
                        ] as { key: TabType; label: string }[]).map((tab) => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`py-3 px-1 border-b-2 font-medium text-sm ${
                                    activeTab === tab.key
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                            >
                                {tab.label}
                                {tab.key === 'versions' && plan?.version_count !== undefined && plan.version_count > 0 && (
                                    <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                                        {plan.version_count}
                                    </span>
                                )}
                                {tab.key === 'cycles' && currentCycle && (
                                    <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                                        currentCycle.status === 'DATA_COLLECTION' ? 'bg-blue-100 text-blue-700' :
                                        currentCycle.status === 'PENDING_APPROVAL' ? 'bg-purple-100 text-purple-700' :
                                        'bg-gray-100 text-gray-600'
                                    }`}>
                                        {currentCycle.status === 'DATA_COLLECTION' ? 'Active' :
                                         currentCycle.status === 'PENDING_APPROVAL' ? 'Awaiting' :
                                         currentCycle.status.replace(/_/g, ' ')}
                                    </span>
                                )}
                            </button>
                        ))}
                    </nav>
                </div>

                {/* Tab Content */}
                <div className="bg-white rounded-lg border p-6">
                    {/* Dashboard Tab */}
                    {activeTab === 'dashboard' && (
                        <div className="space-y-6">
                            {/* Action Error */}
                            {actionError && (
                                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                                    <p className="font-medium">{actionError}</p>
                                    {actionError.includes('Missing results') && (
                                        <p className="mt-2 text-sm">
                                            Click <strong>"Enter Results"</strong> to provide values or explanations for each metric.
                                        </p>
                                    )}
                                </div>
                            )}

                            {/* Action Card - Current Cycle Status */}
                            {currentCycle ? (
                                <div className={`rounded-lg p-5 ${
                                    currentCycle.status === 'DATA_COLLECTION' ? 'bg-blue-50 border-2 border-blue-300' :
                                    currentCycle.status === 'PENDING_APPROVAL' ? 'bg-purple-50 border-2 border-purple-300' :
                                    currentCycle.status === 'UNDER_REVIEW' ? 'bg-yellow-50 border-2 border-yellow-300' :
                                    'bg-gray-50 border border-gray-200'
                                }`}>
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <div className="flex items-center gap-3">
                                                <span className={`text-lg font-bold ${
                                                    currentCycle.status === 'DATA_COLLECTION' ? 'text-blue-800' :
                                                    currentCycle.status === 'PENDING_APPROVAL' ? 'text-purple-800' :
                                                    currentCycle.status === 'UNDER_REVIEW' ? 'text-yellow-800' :
                                                    'text-gray-800'
                                                }`}>
                                                    {formatPeriod(currentCycle.period_start_date, currentCycle.period_end_date)} Cycle
                                                </span>
                                                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadgeColor(currentCycle.status)}`}>
                                                    {formatStatus(currentCycle.status)}
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-600 mt-2">
                                                {currentCycle.status === 'DATA_COLLECTION' && (
                                                    <>Data collection in progress. {currentCycle.result_count} / {plan.metrics?.length || 0} metrics entered.</>
                                                )}
                                                {currentCycle.status === 'PENDING_APPROVAL' && (
                                                    <>Awaiting approvals before cycle can be completed.</>
                                                )}
                                                {currentCycle.status === 'UNDER_REVIEW' && (
                                                    <>Results under review before requesting approval.</>
                                                )}
                                                {currentCycle.status === 'PENDING' && (
                                                    <>Cycle created. Start data collection when ready.</>
                                                )}
                                            </p>
                                            <div className="flex items-center gap-4 mt-3 text-sm text-gray-600">
                                                <span>Due: <strong>{currentCycle.submission_due_date}</strong></span>
                                                {currentCycle.version_number && (
                                                    <span>Version: <strong>v{currentCycle.version_number}</strong></span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex flex-col gap-2">
                                            {canEnterResults(currentCycle) && (
                                                <button
                                                    onClick={() => openResultsEntry(currentCycle)}
                                                    className="px-4 py-2 rounded text-sm font-medium bg-green-600 text-white hover:bg-green-700"
                                                >
                                                    Enter Results
                                                </button>
                                            )}
                                            {currentCycle.status === 'PENDING_APPROVAL' && (
                                                <button
                                                    onClick={() => fetchCycleDetail(currentCycle.cycle_id)}
                                                    className="px-4 py-2 rounded text-sm font-medium bg-purple-600 text-white hover:bg-purple-700"
                                                >
                                                    View Approvals
                                                </button>
                                            )}
                                            {getAvailableActions(currentCycle).slice(0, 1).map((action) => (
                                                <button
                                                    key={action.action}
                                                    onClick={() => {
                                                        if (action.action === 'cancel') {
                                                            openCancelModal(currentCycle.cycle_id);
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
                                        </div>
                                    </div>
                                    {/* Results Summary Bar */}
                                    {currentCycle.result_count > 0 && (
                                        <div className="mt-4 pt-4 border-t border-gray-200">
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm text-gray-600">Current Results:</span>
                                                <div className="flex items-center gap-3">
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 rounded text-sm">
                                                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                                        {currentCycle.green_count} Green
                                                    </span>
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-sm">
                                                        <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
                                                        {currentCycle.yellow_count} Yellow
                                                    </span>
                                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-800 rounded text-sm">
                                                        <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                                        {currentCycle.red_count} Red
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                    {/* Approval Status Bar */}
                                    {currentCycle.status === 'PENDING_APPROVAL' && currentCycle.approval_count > 0 && (
                                        <div className="mt-4 pt-4 border-t border-gray-200">
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm text-gray-600">Approval Status:</span>
                                                <div className="flex items-center gap-3">
                                                    {currentCycle.pending_approval_count > 0 ? (
                                                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-800 rounded text-sm">
                                                            <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse"></span>
                                                            {currentCycle.pending_approval_count} of {currentCycle.approval_count} pending
                                                        </span>
                                                    ) : (
                                                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 rounded text-sm">
                                                            <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                                            All {currentCycle.approval_count} approved
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="bg-gray-50 rounded-lg p-5 border border-gray-200">
                                    <div className="flex justify-between items-center">
                                        <div>
                                            <h3 className="text-lg font-semibold text-gray-700">No Active Cycle</h3>
                                            <p className="text-sm text-gray-500 mt-1">
                                                {!plan.active_version_number
                                                    ? 'Publish a plan version before creating cycles.'
                                                    : 'Create a new cycle to start monitoring.'}
                                            </p>
                                        </div>
                                        {canCreateCycle && plan.active_version_number && (
                                            <button
                                                onClick={() => setShowCreateModal(true)}
                                                className="px-4 py-2 rounded text-sm font-medium bg-blue-600 text-white hover:bg-blue-700"
                                            >
                                                + New Cycle
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Performance Overview */}
                            <div className="grid grid-cols-2 gap-6">
                                {/* Left Column: Last Cycle Status + Sparkline */}
                                <div className="space-y-4">
                                    <div className="bg-white rounded-lg border p-4">
                                        <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Recent Performance</h4>
                                        <CycleSparkline cycles={cycles} />
                                        {cycles.filter(c => c.status === 'APPROVED').length > 0 && (
                                            <div className="mt-3 pt-3 border-t">
                                                <div className="text-sm text-gray-600">
                                                    Last Completed: <strong>{formatPeriod(
                                                        cycles.filter(c => c.status === 'APPROVED')[0]?.period_start_date || '',
                                                        cycles.filter(c => c.status === 'APPROVED')[0]?.period_end_date || ''
                                                    )}</strong>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                    {/* Plan Details */}
                                    <div className="bg-white rounded-lg border p-4">
                                        <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Plan Details</h4>
                                        <div className="grid grid-cols-2 gap-3 text-sm">
                                            <div>
                                                <span className="text-gray-500">Data Provider</span>
                                                <p className="font-medium">{plan.data_provider?.full_name || '-'}</p>
                                            </div>
                                            <div>
                                                <span className="text-gray-500">Lead Time</span>
                                                <p className="font-medium">{plan.reporting_lead_days} days</p>
                                            </div>
                                            <div>
                                                <span className="text-gray-500">Next Due</span>
                                                <p className="font-medium">{plan.next_submission_due_date || '-'}</p>
                                            </div>
                                            <div>
                                                <span className="text-gray-500">Report Due</span>
                                                <p className="font-medium">{plan.next_report_due_date || '-'}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Right Column: Performance Summary */}
                                <div className="bg-white rounded-lg border p-4">
                                    <h4 className="text-sm font-semibold text-gray-500 uppercase mb-3">Overall Performance (Last 10 Cycles)</h4>
                                    {loadingPerformance ? (
                                        <div className="text-center py-8 text-gray-500">Loading...</div>
                                    ) : performanceSummary && performanceSummary.total_results > 0 ? (
                                        <div className="space-y-4">
                                            <div className="grid grid-cols-4 gap-2 text-center">
                                                <div className="bg-green-50 rounded p-2">
                                                    <div className="text-xl font-bold text-green-700">{performanceSummary.green_count}</div>
                                                    <div className="text-xs text-green-600">Green</div>
                                                </div>
                                                <div className="bg-yellow-50 rounded p-2">
                                                    <div className="text-xl font-bold text-yellow-700">{performanceSummary.yellow_count}</div>
                                                    <div className="text-xs text-yellow-600">Yellow</div>
                                                </div>
                                                <div className="bg-red-50 rounded p-2">
                                                    <div className="text-xl font-bold text-red-700">{performanceSummary.red_count}</div>
                                                    <div className="text-xs text-red-600">Red</div>
                                                </div>
                                                <div className="bg-gray-50 rounded p-2">
                                                    <div className="text-xl font-bold text-gray-500">{performanceSummary.na_count}</div>
                                                    <div className="text-xs text-gray-500">N/A</div>
                                                </div>
                                            </div>
                                            {/* Distribution Bar */}
                                            <div className="flex h-4 rounded-full overflow-hidden bg-gray-200">
                                                {performanceSummary.green_count > 0 && (
                                                    <div className="bg-green-500" style={{ width: `${(performanceSummary.green_count / performanceSummary.total_results) * 100}%` }} />
                                                )}
                                                {performanceSummary.yellow_count > 0 && (
                                                    <div className="bg-yellow-400" style={{ width: `${(performanceSummary.yellow_count / performanceSummary.total_results) * 100}%` }} />
                                                )}
                                                {performanceSummary.red_count > 0 && (
                                                    <div className="bg-red-500" style={{ width: `${(performanceSummary.red_count / performanceSummary.total_results) * 100}%` }} />
                                                )}
                                                {performanceSummary.na_count > 0 && (
                                                    <div className="bg-gray-400" style={{ width: `${(performanceSummary.na_count / performanceSummary.total_results) * 100}%` }} />
                                                )}
                                            </div>
                                            <div className="text-xs text-gray-500 text-center">
                                                {performanceSummary.total_results} total results across {cycles.filter(c => c.status === 'APPROVED').length} cycles
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="text-center py-8 text-gray-500 text-sm">
                                            No performance data yet. Complete monitoring cycles to see summary.
                                        </div>
                                    )}
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
                            <div className="flex justify-between items-center mb-4">
                                <div>
                                    <h3 className="text-lg font-semibold">Configured Metrics ({plan.metrics?.length || 0})</h3>
                                    {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                        <p className="text-sm text-gray-500 mt-1">
                                            Edit thresholds below and publish a new version when ready
                                        </p>
                                    )}
                                </div>
                                {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                    <button
                                        onClick={() => setShowPublishModal(true)}
                                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                        </svg>
                                        Publish Version
                                    </button>
                                )}
                            </div>
                            {!plan.metrics?.length ? (
                                <p className="text-gray-500">No metrics configured for this plan.</p>
                            ) : (
                                <div className="space-y-4">
                                    {plan.metrics.map((metric) => (
                                        <div key={metric.metric_id} className="border rounded-lg p-4 hover:bg-gray-50">
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-3">
                                                        <span className="font-medium text-gray-900">{metric.kpm?.name || '-'}</span>
                                                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                                                            metric.kpm?.evaluation_type === 'Quantitative' ? 'bg-blue-100 text-blue-800' :
                                                            metric.kpm?.evaluation_type === 'Qualitative' ? 'bg-purple-100 text-purple-800' :
                                                            'bg-green-100 text-green-800'
                                                        }`}>
                                                            {metric.kpm?.evaluation_type || '-'}
                                                        </span>
                                                    </div>
                                                    <div className="text-sm text-gray-500 mt-1">{metric.kpm?.category_name || '-'}</div>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                                        <button
                                                            onClick={() => openEditMetric(metric)}
                                                            className="text-gray-600 hover:text-gray-800 text-sm flex items-center gap-1"
                                                            title="Edit thresholds"
                                                        >
                                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                            </svg>
                                                            Edit
                                                        </button>
                                                    )}
                                                    {metric.kpm?.evaluation_type === 'Quantitative' && (
                                                        <button
                                                            onClick={() => setTrendModalMetric({
                                                                metric_id: metric.metric_id,
                                                                metric_name: metric.kpm?.name || '',
                                                                thresholds: {
                                                                    yellow_min: metric.yellow_min,
                                                                    yellow_max: metric.yellow_max,
                                                                    red_min: metric.red_min,
                                                                    red_max: metric.red_max,
                                                                }
                                                            })}
                                                            className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1"
                                                            title="View trend chart"
                                                        >
                                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                                                            </svg>
                                                            Trend
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                            {metric.kpm?.evaluation_type === 'Quantitative' && (
                                                <div className="mt-3 pt-3 border-t">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs text-gray-500 uppercase">Thresholds</span>
                                                        <div className="flex flex-wrap items-center gap-2 text-xs">
                                                            {metric.yellow_min !== null || metric.yellow_max !== null || metric.red_min !== null || metric.red_max !== null ? (
                                                                <>
                                                                    <span className="inline-flex items-center px-2 py-0.5 bg-green-100 text-green-800 rounded">
                                                                        G: {metric.yellow_min !== null || metric.yellow_max !== null ? (
                                                                            <>
                                                                                {metric.yellow_min !== null ? `>${metric.yellow_min}` : ''}
                                                                                {metric.yellow_min !== null && metric.yellow_max !== null ? ' and ' : ''}
                                                                                {metric.yellow_max !== null ? `<${metric.yellow_max}` : ''}
                                                                            </>
                                                                        ) : 'Default'}
                                                                    </span>
                                                                    {(metric.yellow_min !== null || metric.yellow_max !== null) && (
                                                                        <span className="inline-flex items-center px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded">
                                                                            Y: {metric.yellow_min ?? '-'} to {metric.yellow_max ?? '-'}
                                                                        </span>
                                                                    )}
                                                                    {(metric.red_min !== null || metric.red_max !== null) && (
                                                                        <span className="inline-flex items-center px-2 py-0.5 bg-red-100 text-red-800 rounded">
                                                                            R: {metric.red_min !== null ? `<${metric.red_min}` : ''}{metric.red_min !== null && metric.red_max !== null ? ' or ' : ''}{metric.red_max !== null ? `>${metric.red_max}` : ''}
                                                                        </span>
                                                                    )}
                                                                </>
                                                            ) : (
                                                                <span className="text-gray-400 italic">No thresholds configured</span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <div className="mt-2">
                                                        <BulletChart
                                                            value={null}
                                                            yellowMin={metric.yellow_min}
                                                            yellowMax={metric.yellow_max}
                                                            redMin={metric.red_min}
                                                            redMax={metric.red_max}
                                                            width={300}
                                                            height={20}
                                                        />
                                                    </div>
                                                </div>
                                            )}
                                            {metric.kpm?.evaluation_type !== 'Quantitative' && (
                                                <div className="mt-3 pt-3 border-t">
                                                    <span className="text-xs text-gray-500">Judgment-based evaluation</span>
                                                    {metric.qualitative_guidance && (
                                                        <p className="text-sm text-gray-600 mt-1">{metric.qualitative_guidance}</p>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Versions Tab */}
                    {activeTab === 'versions' && (
                        <div className="space-y-6">
                            {/* Header */}
                            <div>
                                <h3 className="text-lg font-semibold">Plan Versions</h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    Each version captures a snapshot of metric configurations for immutable audit trail.
                                    To publish a new version, go to the <button onClick={() => setActiveTab('metrics')} className="text-blue-600 hover:underline">Metrics tab</button>.
                                </p>
                            </div>

                            {loadingVersions ? (
                                <div className="text-center py-8 text-gray-500">Loading versions...</div>
                            ) : versions.length === 0 ? (
                                <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 text-center">
                                    <svg className="w-12 h-12 mx-auto text-amber-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                    </svg>
                                    <h4 className="text-lg font-medium text-amber-800">No Published Versions</h4>
                                    <p className="text-amber-600 mt-1">
                                        Publish a version to lock in the current metric configurations before starting a cycle.
                                    </p>
                                    {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                        <button
                                            onClick={() => setActiveTab('metrics')}
                                            className="mt-4 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700"
                                        >
                                            Go to Metrics Tab
                                        </button>
                                    )}
                                </div>
                            ) : (
                                <div className="grid grid-cols-3 gap-6">
                                    {/* Version List */}
                                    <div className="col-span-1 border rounded-lg overflow-hidden">
                                        <div className="bg-gray-50 px-4 py-3 border-b">
                                            <h4 className="font-medium">All Versions</h4>
                                        </div>
                                        <div className="divide-y max-h-96 overflow-y-auto">
                                            {versions.map((version) => (
                                                <button
                                                    key={version.version_id}
                                                    onClick={() => fetchVersionDetail(version.version_id)}
                                                    className={`w-full text-left px-4 py-3 hover:bg-gray-50 ${
                                                        selectedVersionDetail?.version_id === version.version_id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                                                    }`}
                                                >
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-medium">v{version.version_number}</span>
                                                        {version.is_active && (
                                                            <span className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded">Active</span>
                                                        )}
                                                    </div>
                                                    {version.version_name && (
                                                        <div className="text-sm text-gray-600 truncate">{version.version_name}</div>
                                                    )}
                                                    <div className="text-xs text-gray-400 mt-1">
                                                        Effective: {version.effective_date}
                                                    </div>
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Version Detail */}
                                    <div className="col-span-2 border rounded-lg">
                                        {loadingVersionDetail ? (
                                            <div className="p-8 text-center text-gray-500">Loading version details...</div>
                                        ) : selectedVersionDetail ? (
                                            <div>
                                                <div className="bg-gray-50 px-4 py-3 border-b flex justify-between items-center">
                                                    <div>
                                                        <h4 className="font-medium">
                                                            Version {selectedVersionDetail.version_number}
                                                            {selectedVersionDetail.version_name && ` - ${selectedVersionDetail.version_name}`}
                                                        </h4>
                                                        <div className="text-xs text-gray-500">
                                                            Published: {selectedVersionDetail.published_at?.split('T')[0]} • Effective: {selectedVersionDetail.effective_date}
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={() => exportVersionCSV(selectedVersionDetail)}
                                                        className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1"
                                                    >
                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                        </svg>
                                                        Export CSV
                                                    </button>
                                                </div>
                                                <div className="p-4">
                                                    <h5 className="text-sm font-medium text-gray-700 mb-3">
                                                        Metric Snapshots ({selectedVersionDetail.metric_snapshots.length})
                                                    </h5>
                                                    <div className="space-y-3 max-h-80 overflow-y-auto">
                                                        {selectedVersionDetail.metric_snapshots.map((snapshot) => (
                                                            <div key={snapshot.snapshot_id} className="border rounded p-3 text-sm">
                                                                <div className="flex items-center justify-between">
                                                                    <span className="font-medium">{snapshot.kpm_name}</span>
                                                                    <span className={`px-2 py-0.5 text-xs rounded ${
                                                                        snapshot.evaluation_type === 'Quantitative' ? 'bg-blue-100 text-blue-800' :
                                                                        snapshot.evaluation_type === 'Qualitative' ? 'bg-purple-100 text-purple-800' :
                                                                        'bg-green-100 text-green-800'
                                                                    }`}>
                                                                        {snapshot.evaluation_type}
                                                                    </span>
                                                                </div>
                                                                <div className="text-xs text-gray-500 mt-1">{snapshot.kpm_category_name}</div>
                                                                {snapshot.evaluation_type === 'Quantitative' && (
                                                                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                                                                        {(snapshot.yellow_min !== null || snapshot.yellow_max !== null || snapshot.red_min !== null || snapshot.red_max !== null) ? (
                                                                            <>
                                                                                {snapshot.yellow_max !== null && (
                                                                                    <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded">
                                                                                        Y ≤ {snapshot.yellow_max}
                                                                                    </span>
                                                                                )}
                                                                                {snapshot.red_max !== null && (
                                                                                    <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded">
                                                                                        R &gt; {snapshot.red_max}
                                                                                    </span>
                                                                                )}
                                                                                {snapshot.yellow_min !== null && (
                                                                                    <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded">
                                                                                        Y ≥ {snapshot.yellow_min}
                                                                                    </span>
                                                                                )}
                                                                                {snapshot.red_min !== null && (
                                                                                    <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded">
                                                                                        R &lt; {snapshot.red_min}
                                                                                    </span>
                                                                                )}
                                                                            </>
                                                                        ) : (
                                                                            <span className="text-gray-400 italic">No thresholds</span>
                                                                        )}
                                                                    </div>
                                                                )}
                                                                {snapshot.qualitative_guidance && (
                                                                    <div className="mt-2 text-xs text-gray-600 italic">
                                                                        "{snapshot.qualitative_guidance}"
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="p-8 text-center text-gray-400">
                                                <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                </svg>
                                                <p>Select a version to view its metric snapshots</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Cycles Tab */}
                    {activeTab === 'cycles' && (
                        <div className="space-y-6">
                            {/* Action Error */}
                            {actionError && (
                                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                                    <p className="font-medium">{actionError}</p>
                                    {actionError.includes('Missing results') && (
                                        <p className="mt-2 text-sm">
                                            Click <strong>"Enter Results"</strong> to provide values or explanations for each metric.
                                        </p>
                                    )}
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
                                                            if (action.action === 'cancel') {
                                                                openCancelModal(currentCycle.cycle_id);
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

                            {/* Cycle History */}
                            <div>
                                <h3 className="text-lg font-semibold mb-4">Cycle History</h3>
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
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Approvals</th>
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
                                                    <td className="px-4 py-3">
                                                        {cycle.approval_count > 0 ? (
                                                            cycle.pending_approval_count > 0 ? (
                                                                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-purple-100 text-purple-800 rounded text-xs">
                                                                    <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
                                                                    {cycle.approval_count - cycle.pending_approval_count}/{cycle.approval_count}
                                                                </span>
                                                            ) : (
                                                                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-green-100 text-green-800 rounded text-xs">
                                                                    <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                                                                    {cycle.approval_count}/{cycle.approval_count}
                                                                </span>
                                                            )
                                                        ) : (
                                                            <span className="text-gray-400 text-xs">-</span>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3 text-right space-x-2">
                                                        <button
                                                            onClick={() => fetchCycleDetail(cycle.cycle_id)}
                                                            className="text-blue-600 hover:underline text-sm"
                                                        >
                                                            View
                                                        </button>
                                                        <button
                                                            onClick={() => exportCycleCSV(cycle.cycle_id)}
                                                            disabled={exportingCycle === cycle.cycle_id}
                                                            className="text-gray-600 hover:underline text-sm disabled:text-gray-400"
                                                        >
                                                            {exportingCycle === cycle.cycle_id ? '...' : 'CSV'}
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>

                            {/* Results by Metric Summary (collapsible) */}
                            {performanceSummary && performanceSummary.by_metric.length > 0 && (
                                <div className="border rounded-lg p-4 bg-gray-50">
                                    <h4 className="text-md font-semibold mb-3">Results by Metric (Last 10 Cycles)</h4>
                                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                                        <thead className="bg-white">
                                            <tr>
                                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Metric</th>
                                                <th className="px-3 py-2 text-center text-xs font-medium text-green-600 uppercase">G</th>
                                                <th className="px-3 py-2 text-center text-xs font-medium text-yellow-600 uppercase">Y</th>
                                                <th className="px-3 py-2 text-center text-xs font-medium text-red-600 uppercase">R</th>
                                                <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Trend</th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {performanceSummary.by_metric.map((metric) => {
                                                const planMetric = plan?.metrics?.find(m => m.metric_id === metric.metric_id);
                                                return (
                                                    <tr key={metric.metric_id}>
                                                        <td className="px-3 py-2 text-sm">{metric.metric_name}</td>
                                                        <td className="px-3 py-2 text-center text-sm text-green-600">{metric.green_count}</td>
                                                        <td className="px-3 py-2 text-center text-sm text-yellow-600">{metric.yellow_count}</td>
                                                        <td className="px-3 py-2 text-center text-sm text-red-600">{metric.red_count}</td>
                                                        <td className="px-3 py-2 text-center">
                                                            <button
                                                                onClick={() => setTrendModalMetric({
                                                                    metric_id: metric.metric_id,
                                                                    metric_name: metric.metric_name,
                                                                    thresholds: {
                                                                        yellow_min: planMetric?.yellow_min ?? null,
                                                                        yellow_max: planMetric?.yellow_max ?? null,
                                                                        red_min: planMetric?.red_min ?? null,
                                                                        red_max: planMetric?.red_max ?? null,
                                                                    }
                                                                })}
                                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                                                title="View trend chart"
                                                            >
                                                                <svg className="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                                                                </svg>
                                                            </button>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            )}
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

                                                        {/* Previous Value Context */}
                                                        {form.previousValue !== null && (
                                                            <div className="bg-blue-50 rounded-lg p-3 flex items-center justify-between">
                                                                <div>
                                                                    <span className="text-xs text-blue-600 font-medium">Previous Cycle</span>
                                                                    {form.previousPeriod && (
                                                                        <span className="text-xs text-blue-500 ml-1">({form.previousPeriod})</span>
                                                                    )}
                                                                </div>
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-sm font-medium text-blue-900">{form.previousValue.toFixed(4)}</span>
                                                                    {form.previousOutcome && (
                                                                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                                                            form.previousOutcome === 'GREEN' ? 'bg-green-100 text-green-800' :
                                                                            form.previousOutcome === 'YELLOW' ? 'bg-yellow-100 text-yellow-800' :
                                                                            form.previousOutcome === 'RED' ? 'bg-red-100 text-red-800' :
                                                                            'bg-gray-100 text-gray-800'
                                                                        }`}>
                                                                            {form.previousOutcome}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Value Input with Skip checkbox */}
                                                        <div>
                                                            <div className="flex items-center justify-between mb-1">
                                                                <label className="block text-sm font-medium text-gray-700">Value</label>
                                                                <label className="flex items-center gap-2 text-sm cursor-pointer">
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={form.skipped}
                                                                        onChange={(e) => handleSkipToggle(index, e.target.checked)}
                                                                        className="rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                                                                    />
                                                                    <span className="text-gray-600">Skip this metric</span>
                                                                </label>
                                                            </div>
                                                            <input
                                                                type="number"
                                                                step="any"
                                                                className={`w-full border border-gray-300 rounded-lg px-3 py-2 ${
                                                                    form.skipped ? 'bg-gray-100 text-gray-400' : ''
                                                                }`}
                                                                value={form.numeric_value}
                                                                onChange={(e) => handleResultChange(index, 'numeric_value', e.target.value)}
                                                                placeholder={form.skipped ? "Skipped" : "Enter numeric value..."}
                                                                disabled={form.skipped}
                                                            />
                                                        </div>

                                                        {/* Skip Explanation (only shown when skipped) */}
                                                        {form.skipped && (
                                                            <div>
                                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                    Skip Explanation <span className="text-red-500">*</span>
                                                                </label>
                                                                <textarea
                                                                    className={`w-full border rounded-lg px-3 py-2 text-sm ${
                                                                        !form.narrative.trim()
                                                                            ? 'border-amber-300 bg-amber-50'
                                                                            : 'border-gray-300'
                                                                    }`}
                                                                    rows={2}
                                                                    value={form.narrative}
                                                                    onChange={(e) => handleResultChange(index, 'narrative', e.target.value)}
                                                                    placeholder="Required: Explain why this metric was not measured..."
                                                                />
                                                                {!form.narrative.trim() && (
                                                                    <p className="text-xs text-amber-600 mt-1">
                                                                        ⚠️ An explanation is required when skipping a metric.
                                                                    </p>
                                                                )}
                                                            </div>
                                                        )}

                                                        {/* Notes (only shown when not skipped) */}
                                                        {!form.skipped && (
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
                                                        )}
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

                                                        {/* Outcome Input with Skip checkbox */}
                                                        <div>
                                                            <div className="flex items-center justify-between mb-1">
                                                                <label className="block text-sm font-medium text-gray-700">Outcome</label>
                                                                <label className="flex items-center gap-2 text-sm cursor-pointer">
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={form.skipped}
                                                                        onChange={(e) => handleSkipToggle(index, e.target.checked)}
                                                                        className="rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                                                                    />
                                                                    <span className="text-gray-600">Skip this metric</span>
                                                                </label>
                                                            </div>
                                                            <select
                                                                className={`w-full border border-gray-300 rounded-lg px-3 py-2 ${
                                                                    form.skipped ? 'bg-gray-100 text-gray-400' : ''
                                                                }`}
                                                                value={form.outcome_value_id || ''}
                                                                onChange={(e) => handleResultChange(index, 'outcome_value_id', e.target.value ? parseInt(e.target.value) : null)}
                                                                disabled={form.skipped}
                                                            >
                                                                <option value="">{form.skipped ? "Skipped" : "Select outcome..."}</option>
                                                                {outcomeValues.map(o => (
                                                                    <option key={o.value_id} value={o.value_id}>{o.label}</option>
                                                                ))}
                                                            </select>
                                                        </div>

                                                        {/* Skip Explanation (only shown when skipped) */}
                                                        {form.skipped && (
                                                            <div>
                                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                    Skip Explanation <span className="text-red-500">*</span>
                                                                </label>
                                                                <textarea
                                                                    className={`w-full border rounded-lg px-3 py-2 text-sm ${
                                                                        !form.narrative.trim()
                                                                            ? 'border-amber-300 bg-amber-50'
                                                                            : 'border-gray-300'
                                                                    }`}
                                                                    rows={2}
                                                                    value={form.narrative}
                                                                    onChange={(e) => handleResultChange(index, 'narrative', e.target.value)}
                                                                    placeholder="Required: Explain why this metric was not measured..."
                                                                />
                                                                {!form.narrative.trim() && (
                                                                    <p className="text-xs text-amber-600 mt-1">
                                                                        ⚠️ An explanation is required when skipping a metric.
                                                                    </p>
                                                                )}
                                                            </div>
                                                        )}

                                                        {/* Rationale (only shown when not skipped) */}
                                                        {!form.skipped && (
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
                                                        )}
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

                                                        {/* Outcome Input with Skip checkbox */}
                                                        <div>
                                                            <div className="flex items-center justify-between mb-1">
                                                                <label className="block text-sm font-medium text-gray-700">Outcome</label>
                                                                <label className="flex items-center gap-2 text-sm cursor-pointer">
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={form.skipped}
                                                                        onChange={(e) => handleSkipToggle(index, e.target.checked)}
                                                                        className="rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                                                                    />
                                                                    <span className="text-gray-600">Skip this metric</span>
                                                                </label>
                                                            </div>
                                                            <select
                                                                className={`w-full border border-gray-300 rounded-lg px-3 py-2 ${
                                                                    form.skipped ? 'bg-gray-100 text-gray-400' : ''
                                                                }`}
                                                                value={form.outcome_value_id || ''}
                                                                onChange={(e) => handleResultChange(index, 'outcome_value_id', e.target.value ? parseInt(e.target.value) : null)}
                                                                disabled={form.skipped}
                                                            >
                                                                <option value="">{form.skipped ? "Skipped" : "Select outcome..."}</option>
                                                                {outcomeValues.map(o => (
                                                                    <option key={o.value_id} value={o.value_id}>{o.label}</option>
                                                                ))}
                                                            </select>
                                                        </div>

                                                        {/* Skip Explanation (only shown when skipped) */}
                                                        {form.skipped && (
                                                            <div>
                                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                    Skip Explanation <span className="text-red-500">*</span>
                                                                </label>
                                                                <textarea
                                                                    className={`w-full border rounded-lg px-3 py-2 text-sm ${
                                                                        !form.narrative.trim()
                                                                            ? 'border-amber-300 bg-amber-50'
                                                                            : 'border-gray-300'
                                                                    }`}
                                                                    rows={2}
                                                                    value={form.narrative}
                                                                    onChange={(e) => handleResultChange(index, 'narrative', e.target.value)}
                                                                    placeholder="Required: Explain why this metric was not measured..."
                                                                />
                                                                {!form.narrative.trim() && (
                                                                    <p className="text-xs text-amber-600 mt-1">
                                                                        ⚠️ An explanation is required when skipping a metric.
                                                                    </p>
                                                                )}
                                                            </div>
                                                        )}

                                                        {/* Notes (only shown when not skipped) */}
                                                        {!form.skipped && (
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
                                                        )}
                                                    </div>
                                                )}

                                                {/* Save/Delete Buttons */}
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
                                                    <div className="flex items-center gap-2">
                                                        {form.existingResultId && (
                                                            <button
                                                                onClick={() => deleteResult(index)}
                                                                disabled={deletingResult === index || savingResult === index}
                                                                className="px-3 py-2 rounded text-sm font-medium text-red-600 hover:bg-red-50 border border-red-300 disabled:opacity-50"
                                                            >
                                                                {deletingResult === index ? 'Deleting...' : 'Delete'}
                                                            </button>
                                                        )}
                                                        <button
                                                            onClick={() => saveResult(index)}
                                                            disabled={savingResult === index || deletingResult === index || (!form.dirty && form.existingResultId !== null)}
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

                {/* Cancel Cycle Modal */}
                {showCancelModal && cancelCycleId && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
                            <div className="p-4 border-b bg-red-50">
                                <h3 className="text-lg font-bold text-red-800">Cancel Monitoring Cycle</h3>
                            </div>

                            <div className="p-4 space-y-4">
                                {actionError && (
                                    <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                                        {actionError}
                                    </div>
                                )}

                                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                    <p className="text-red-800 text-sm">
                                        Cancelling this cycle will permanently stop all work on it. This action cannot be undone.
                                    </p>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Cancellation Reason *
                                    </label>
                                    <textarea
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                        rows={3}
                                        value={cancelReason}
                                        onChange={(e) => setCancelReason(e.target.value)}
                                        placeholder="Please explain why this cycle is being cancelled..."
                                    />
                                </div>
                            </div>

                            <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                                <button
                                    onClick={() => {
                                        setShowCancelModal(false);
                                        setCancelCycleId(null);
                                        setCancelReason('');
                                        setActionError(null);
                                    }}
                                    disabled={actionLoading}
                                    className="btn-secondary"
                                >
                                    Keep Cycle
                                </button>
                                <button
                                    onClick={handleCancelCycle}
                                    disabled={actionLoading || !cancelReason.trim()}
                                    className="px-4 py-2 rounded text-white font-medium bg-red-600 hover:bg-red-700 disabled:opacity-50"
                                >
                                    {actionLoading ? 'Cancelling...' : 'Confirm Cancel'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Publish Version Modal */}
                {showPublishModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
                            <div className="p-4 border-b bg-blue-50">
                                <h3 className="text-lg font-bold text-blue-800">Publish New Version</h3>
                            </div>

                            <form onSubmit={handlePublishVersion}>
                                <div className="p-4 space-y-4">
                                    {publishError && (
                                        <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                                            {publishError}
                                        </div>
                                    )}

                                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                        <p className="text-blue-800 text-sm">
                                            Publishing a version creates an immutable snapshot of the current metric configurations.
                                            This version will be used for all future cycles until a new version is published.
                                        </p>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Version Name (optional)
                                        </label>
                                        <input
                                            type="text"
                                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                            value={publishForm.version_name}
                                            onChange={(e) => setPublishForm(prev => ({ ...prev, version_name: e.target.value }))}
                                            placeholder="e.g., Q1 2025 Update, Enhanced Risk Thresholds"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Effective Date
                                        </label>
                                        <input
                                            type="date"
                                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                            value={publishForm.effective_date}
                                            onChange={(e) => setPublishForm(prev => ({ ...prev, effective_date: e.target.value }))}
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Description (optional)
                                        </label>
                                        <textarea
                                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                            rows={3}
                                            value={publishForm.description}
                                            onChange={(e) => setPublishForm(prev => ({ ...prev, description: e.target.value }))}
                                            placeholder="Describe the changes in this version..."
                                        />
                                    </div>

                                    <div className="bg-gray-50 rounded-lg p-3">
                                        <p className="text-sm text-gray-600">
                                            <strong>{plan.metrics?.length || 0}</strong> metrics will be captured in this version.
                                        </p>
                                    </div>
                                </div>

                                <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowPublishModal(false);
                                            setPublishError(null);
                                        }}
                                        disabled={publishing}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={publishing}
                                        className="px-4 py-2 rounded text-white font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        {publishing ? 'Publishing...' : 'Publish Version'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* Edit Metric Modal */}
                {showMetricModal && editingMetric && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-lg">
                            <div className="p-4 border-b">
                                <h3 className="text-lg font-bold">Edit Metric Thresholds</h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    {editingMetric.kpm?.name} ({editingMetric.kpm?.evaluation_type})
                                </p>
                            </div>

                            <form onSubmit={handleSaveMetric}>
                                <div className="p-4 space-y-4">
                                    {metricError && (
                                        <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                                            {metricError}
                                        </div>
                                    )}

                                    {editingMetric.kpm?.evaluation_type === 'Quantitative' ? (
                                        <>
                                            <div className="bg-gray-50 rounded-lg p-3">
                                                <p className="text-sm text-gray-600">
                                                    Configure threshold boundaries. Leave fields blank for no threshold.
                                                </p>
                                            </div>

                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-yellow-700 mb-1">
                                                        Yellow Min
                                                    </label>
                                                    <input
                                                        type="number"
                                                        step="any"
                                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                        value={metricForm.yellow_min}
                                                        onChange={(e) => setMetricForm(prev => ({ ...prev, yellow_min: e.target.value }))}
                                                        placeholder="No minimum"
                                                    />
                                                    <p className="text-xs text-gray-500 mt-1">Yellow zone starts above this</p>
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-yellow-700 mb-1">
                                                        Yellow Max
                                                    </label>
                                                    <input
                                                        type="number"
                                                        step="any"
                                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                        value={metricForm.yellow_max}
                                                        onChange={(e) => setMetricForm(prev => ({ ...prev, yellow_max: e.target.value }))}
                                                        placeholder="No maximum"
                                                    />
                                                    <p className="text-xs text-gray-500 mt-1">Yellow zone ends below this</p>
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-red-700 mb-1">
                                                        Red Min
                                                    </label>
                                                    <input
                                                        type="number"
                                                        step="any"
                                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                        value={metricForm.red_min}
                                                        onChange={(e) => setMetricForm(prev => ({ ...prev, red_min: e.target.value }))}
                                                        placeholder="No minimum"
                                                    />
                                                    <p className="text-xs text-gray-500 mt-1">Red zone starts below this</p>
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-red-700 mb-1">
                                                        Red Max
                                                    </label>
                                                    <input
                                                        type="number"
                                                        step="any"
                                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                        value={metricForm.red_max}
                                                        onChange={(e) => setMetricForm(prev => ({ ...prev, red_max: e.target.value }))}
                                                        placeholder="No maximum"
                                                    />
                                                    <p className="text-xs text-gray-500 mt-1">Red zone starts above this</p>
                                                </div>
                                            </div>

                                            <div className="bg-blue-50 rounded-lg p-3 text-sm">
                                                <p className="font-medium text-blue-800 mb-2">Common Threshold Patterns:</p>
                                                <ul className="list-disc list-inside text-blue-700 space-y-1">
                                                    <li><strong>Lower is better:</strong> Set Yellow Max and Red Max (e.g., error rate)</li>
                                                    <li><strong>Higher is better:</strong> Set Yellow Min and Red Min (e.g., accuracy)</li>
                                                    <li><strong>Range-based:</strong> Set Yellow Min and Yellow Max (e.g., p-value)</li>
                                                </ul>
                                            </div>
                                        </>
                                    ) : (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Qualitative Guidance
                                            </label>
                                            <textarea
                                                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                rows={4}
                                                value={metricForm.qualitative_guidance}
                                                onChange={(e) => setMetricForm(prev => ({ ...prev, qualitative_guidance: e.target.value }))}
                                                placeholder="Provide guidance for evaluating this qualitative metric..."
                                            />
                                            <p className="text-xs text-gray-500 mt-1">
                                                This guidance will be shown to evaluators when assessing the metric.
                                            </p>
                                        </div>
                                    )}
                                </div>

                                <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowMetricModal(false);
                                            setEditingMetric(null);
                                            setMetricError(null);
                                        }}
                                        disabled={savingMetric}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={savingMetric}
                                        className="px-4 py-2 rounded text-white font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        {savingMetric ? 'Saving...' : 'Save Changes'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* Trend Chart Modal */}
                <TrendChartModal
                    isOpen={trendModalMetric !== null}
                    onClose={() => setTrendModalMetric(null)}
                    planMetricId={trendModalMetric?.metric_id || 0}
                    metricName={trendModalMetric?.metric_name || ''}
                    thresholds={trendModalMetric?.thresholds || {
                        yellow_min: null,
                        yellow_max: null,
                        red_min: null,
                        red_max: null,
                    }}
                />
            </div>
        </Layout>
    );
};

export default MonitoringPlanDetailPage;

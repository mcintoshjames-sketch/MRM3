import React, { useEffect, useState } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import Layout from '../components/Layout';
import TrendChartModal from '../components/TrendChartModal';
import BreachResolutionWizard, { BreachItem, BreachResolution } from '../components/BreachResolutionWizard';
import ThresholdWizard, { ThresholdValues } from '../components/ThresholdWizard';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { useMonitoringPlan, VersionDetail as HookVersionDetail } from '../hooks/useMonitoringPlan';
import { useMonitoringCycle, MonitoringCycle, CycleDetail } from '../hooks/useMonitoringCycle';

// Types - only page-specific types needed here
// Most types are imported from hooks: MonitoringCycle, CycleDetail

// VersionDetail - use HookVersionDetail imported from hooks
type VersionDetail = HookVersionDetail;

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
const CycleSparkline: React.FC<{
    cycles: MonitoringCycle[];
    formatPeriod: (startDate: string, endDate: string) => string;
    frequency: string;
}> = ({ cycles, formatPeriod, frequency }) => {
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
                        <div key={cycle.cycle_id} className="w-3 h-[2.75rem] bg-gray-200 rounded-sm" title="No results" />
                    );
                }
                const greenPct = (cycle.green_count / total) * 100;
                const yellowPct = (cycle.yellow_count / total) * 100;
                const redPct = (cycle.red_count / total) * 100;
                const periodLabel = formatPeriod(cycle.period_start_date, cycle.period_end_date);
                return (
                    <div
                        key={cycle.cycle_id}
                        className="w-3 h-[2.75rem] rounded-sm overflow-hidden flex flex-col"
                        title={`${periodLabel}: ${cycle.green_count}G ${cycle.yellow_count}Y ${cycle.red_count}R`}
                    >
                        {redPct > 0 && <div className="bg-red-500" style={{ height: `${redPct}%` }} />}
                        {yellowPct > 0 && <div className="bg-yellow-400" style={{ height: `${yellowPct}%` }} />}
                        {greenPct > 0 && <div className="bg-green-500" style={{ height: `${greenPct}%` }} />}
                    </div>
                );
            })}
            <span className="text-xs text-gray-500 ml-1">
                Last {recentCycles.length} {getFrequencyLabel(frequency, recentCycles.length)}
            </span>
        </div>
    );
};

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const getFrequencyLabel = (frequency: string, count: number): string => {
    switch (frequency) {
        case 'Monthly':
            return count === 1 ? 'Month' : 'Months';
        case 'Quarterly':
            return count === 1 ? 'Quarter' : 'Quarters';
        case 'Semi-Annual':
            return count === 1 ? 'Semi-Annual Period' : 'Semi-Annual Periods';
        case 'Annual':
            return count === 1 ? 'Year' : 'Years';
        default:
            return count === 1 ? 'Cycle' : 'Cycles';
    }
};

const formatMonthYearRange = (startDate: string, endDate: string): string => {
    const startParts = startDate.split('T')[0].split('-');
    const endParts = endDate.split('T')[0].split('-');
    if (startParts.length < 2 || endParts.length < 2) {
        return `${startDate} - ${endDate}`;
    }
    const [startYear, startMonth] = startParts;
    const [endYear, endMonth] = endParts;
    const startLabel = `${MONTH_NAMES[Math.max(0, parseInt(startMonth, 10) - 1)]} ${startYear}`;
    const endLabel = `${MONTH_NAMES[Math.max(0, parseInt(endMonth, 10) - 1)]} ${endYear}`;
    return `${startLabel} - ${endLabel}`;
};

const MonitoringPlanDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const [searchParams] = useSearchParams();
    const { user } = useAuth();
    const planId = id ? parseInt(id, 10) : null;

    // Read initial tab from URL query param if valid
    const validTabs: TabType[] = ['dashboard', 'models', 'metrics', 'versions', 'cycles'];
    const initialTab = searchParams.get('tab') as TabType | null;
    const defaultTab: TabType = initialTab && validTabs.includes(initialTab) ? initialTab : 'dashboard';

    // Page-specific state (not in hooks)
    const [activeTab, setActiveTab] = useState<TabType>(defaultTab);
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
    const [showBreachWizard, setShowBreachWizard] = useState(false);
    const [pendingBreaches, setPendingBreaches] = useState<BreachItem[]>([]);
    const [breachResolutionLoading, setBreachResolutionLoading] = useState(false);
    const [pendingDataProviderChange, setPendingDataProviderChange] = useState<number | null>(null);

    // Use the plan configuration hook
    const {
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
        setPublishError,
        handlePublishVersion,
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
        // Plan details editing
        editingPlanDetails,
        setEditingPlanDetails,
        planDetailsForm,
        setPlanDetailsForm,
        savingPlanDetails,
        setSavingPlanDetails,
        availableUsers,
        startEditingPlanDetails,
        cancelEditingPlanDetails,
        // Note: handleSavePlanDetails is defined locally for cycle assignee update logic
        // Cycle assignee prompt
        showUpdateCycleAssigneePrompt,
        setShowUpdateCycleAssigneePrompt,
        // Note: handleCycleAssigneePromptResponse is defined locally to use local handleSavePlanDetails
    } = useMonitoringPlan(id);

    // Use the cycle management hook
    const {
        cycles,
        loadingCycles,
        selectedCycle,
        fetchCycles,
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
        handleCycleAction,
        // Start cycle
        showStartCycleModal,
        setShowStartCycleModal,
        startCycleId,
        setStartCycleId,
        openStartCycleModal,
        handleStartCycle,
        // Cancel cycle
        showCancelModal,
        setShowCancelModal,
        cancelCycleId,
        setCancelCycleId,
        cancelReason,
        setCancelReason,
        openCancelModal,
        handleCancelCycle,
        // Request approval
        showRequestApprovalModal,
        setShowRequestApprovalModal,
        requestApprovalCycleId,
        setRequestApprovalCycleId,
        reportUrl,
        setReportUrl,
        openRequestApprovalModal,
        // Note: handleRequestApproval is defined locally to handle breach wizard integration
        setActionLoading,
        setActionError,
        // Performance
        performanceSummary,
        loadingPerformance,
        exportingCycle,
        fetchPerformanceSummary,
        exportCycleCSV,
        // Helpers
        formatPeriod,
    } = useMonitoringCycle(id, plan, fetchPlan);

    // Fetch performance summary when dashboard or cycles tab is selected
    useEffect(() => {
        if (planId && (activeTab === 'dashboard' || activeTab === 'cycles')) {
            fetchPerformanceSummary();
        }
    }, [planId, activeTab, fetchPerformanceSummary]);

    // Fetch versions when versions tab is selected
    useEffect(() => {
        if (planId && activeTab === 'versions') {
            fetchVersions();
        }
    }, [planId, activeTab, fetchVersions]);

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

    // Get active cycle that could have assignee updated (PENDING or DATA_COLLECTION)
    const getActiveCycleForAssigneeUpdate = (): MonitoringCycle | null => {
        return cycles.find(c =>
            c.status === 'PENDING' || c.status === 'DATA_COLLECTION'
        ) || null;
    };

    const handleSavePlanDetails = async (updateCycleAssignee: boolean = false) => {
        if (!plan) return;

        // Check if data provider is changing and there's an active cycle
        const dataProviderChanged = planDetailsForm.data_provider_user_id !== plan.data_provider_user_id;
        const activeCycle = getActiveCycleForAssigneeUpdate();

        // If data provider changed and there's an active cycle, ask about updating assignee
        if (dataProviderChanged && activeCycle && !showUpdateCycleAssigneePrompt && planDetailsForm.data_provider_user_id) {
            setPendingDataProviderChange(planDetailsForm.data_provider_user_id);
            setShowUpdateCycleAssigneePrompt(true);
            return;
        }

        setSavingPlanDetails(true);
        setActionError(null);

        try {
            // Update plan details
            await api.patch(`/monitoring/plans/${plan.plan_id}`, {
                data_provider_user_id: planDetailsForm.data_provider_user_id || 0,
                reporting_lead_days: planDetailsForm.reporting_lead_days
            });

            // If user chose to update cycle assignee
            if (updateCycleAssignee && activeCycle && pendingDataProviderChange) {
                await api.patch(`/monitoring/cycles/${activeCycle.cycle_id}`, {
                    assigned_to_user_id: pendingDataProviderChange
                });
                fetchCycles();
            }

            // Refresh plan data
            await fetchPlan();
            setEditingPlanDetails(false);
            setShowUpdateCycleAssigneePrompt(false);
            setPendingDataProviderChange(null);
        } catch (err: any) {
            setActionError(err.response?.data?.detail || 'Failed to update plan details');
        } finally {
            setSavingPlanDetails(false);
        }
    };

    const handleCycleAssigneePromptResponse = (updateAssignee: boolean) => {
        setShowUpdateCycleAssigneePrompt(false);
        handleSavePlanDetails(updateAssignee);
    };

    // Request approval handler (local to integrate breach wizard)
    const handleRequestApproval = async () => {
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
            const errorDetail = err.response?.data?.detail;
            // Check for breach justification required error
            if (errorDetail?.error === 'breach_justification_required' && errorDetail?.missing_justifications) {
                // Close the request approval modal and show breach wizard
                setShowRequestApprovalModal(false);
                setPendingBreaches(errorDetail.missing_justifications);
                setShowBreachWizard(true);
            } else {
                setActionError(typeof errorDetail === 'string' ? errorDetail : errorDetail?.message || 'Failed to request approval');
            }
        } finally {
            setActionLoading(false);
        }
    };

    // Handle breach resolution completion
    const handleBreachResolutionComplete = async (resolutions: BreachResolution[]) => {
        if (!requestApprovalCycleId) return;

        setBreachResolutionLoading(true);

        try {
            // Save each breach narrative
            for (const resolution of resolutions) {
                await api.patch(`/monitoring/cycles/${requestApprovalCycleId}/results/${resolution.result_id}`, {
                    narrative: resolution.narrative
                });
            }

            // Close the breach wizard
            setShowBreachWizard(false);
            setPendingBreaches([]);

            // Retry request approval
            await api.post(`/monitoring/cycles/${requestApprovalCycleId}/request-approval`, {
                report_url: reportUrl.trim()
            });

            // Success - clear state and refresh
            setRequestApprovalCycleId(null);
            setReportUrl('');
            fetchCycles();
            if (selectedCycle?.cycle_id === requestApprovalCycleId) {
                fetchCycleDetail(requestApprovalCycleId);
            }
        } catch (err: any) {
            const errorDetail = err.response?.data?.detail;
            // If there are still more breaches (somehow), show them
            if (errorDetail?.error === 'breach_justification_required' && errorDetail?.missing_justifications) {
                setPendingBreaches(errorDetail.missing_justifications);
            } else {
                setShowBreachWizard(false);
                setPendingBreaches([]);
                setActionError(typeof errorDetail === 'string' ? errorDetail : errorDetail?.message || 'Failed to request approval');
            }
        } finally {
            setBreachResolutionLoading(false);
        }
    };

    const handleBreachResolutionCancel = () => {
        setShowBreachWizard(false);
        setPendingBreaches([]);
        // Re-open the request approval modal
        setShowRequestApprovalModal(true);
    };

    // ========== Page-specific Helper Functions ==========

    const canEnterResults = (cycle: MonitoringCycle): boolean => {
        return ['DATA_COLLECTION', 'UNDER_REVIEW'].includes(cycle.status);
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

                {/* Unpublished Changes Warning Banner - Above all tabs */}
                {plan?.has_unpublished_changes && (plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                    <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mt-4">
                        <div className="flex items-start gap-3">
                            <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            <div className="flex-1">
                                <h4 className="font-medium text-amber-800">Unpublished Changes</h4>
                                <p className="text-sm text-amber-700 mt-1">
                                    You have made changes to the plan configuration (models or metrics) that have not been published yet.
                                    Publish a new version to make these changes available for future cycles.
                                </p>
                            </div>
                            <button
                                onClick={() => setShowPublishModal(true)}
                                className="px-3 py-1.5 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm font-medium flex items-center gap-1.5"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                </svg>
                                Publish Now
                            </button>
                        </div>
                    </div>
                )}

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

                            {/* Overdue Alert Banner */}
                            {currentCycle && currentCycle.is_overdue && (
                                <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
                                    <div className="flex items-start">
                                        <div className="flex-shrink-0">
                                            <svg className="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                            </svg>
                                        </div>
                                        <div className="ml-3">
                                            <h3 className="text-sm font-bold text-red-800">
                                                Monitoring Cycle Overdue
                                            </h3>
                                            <p className="mt-1 text-sm text-red-700">
                                                This monitoring cycle is <strong>{currentCycle.days_overdue} days overdue</strong>.
                                                The report was due on {currentCycle.report_due_date}.
                                                Please complete data collection and submit for approval as soon as possible.
                                            </p>
                                        </div>
                                    </div>
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
                                                <Link
                                                    to={`/monitoring/cycles/${currentCycle.cycle_id}`}
                                                    className="px-4 py-2 rounded text-sm font-medium bg-green-600 text-white hover:bg-green-700"
                                                >
                                                    Enter Results
                                                </Link>
                                            )}
                                            {currentCycle.status === 'PENDING_APPROVAL' && (
                                                <Link
                                                    to={`/monitoring/cycles/${currentCycle.cycle_id}`}
                                                    className="px-4 py-2 rounded text-sm font-medium bg-purple-600 text-white hover:bg-purple-700"
                                                >
                                                    View Approvals
                                                </Link>
                                            )}
                                            {getAvailableActions(currentCycle).slice(0, 1).map((action) => (
                                                <button
                                                    key={action.action}
                                                    onClick={() => {
                                                        if (action.action === 'cancel') {
                                                            openCancelModal(currentCycle.cycle_id);
                                                        } else if (action.action === 'request-approval') {
                                                            openRequestApprovalModal(currentCycle.cycle_id);
                                                        } else if (action.action === 'start') {
                                                            openStartCycleModal(currentCycle.cycle_id);
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
                                    {/* Report URL (shown for PENDING_APPROVAL and APPROVED cycles) */}
                                    {(currentCycle.status === 'PENDING_APPROVAL' || currentCycle.status === 'APPROVED') && currentCycle.report_url && (
                                        <div className="mt-4 pt-4 border-t border-gray-200">
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm text-gray-600">📄 Final Report:</span>
                                                <a
                                                    href={currentCycle.report_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline truncate max-w-md"
                                                >
                                                    {currentCycle.report_url}
                                                </a>
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
                                        <CycleSparkline cycles={cycles} formatPeriod={formatPeriod} frequency={plan.frequency} />
                                        {cycles.filter(c => c.status === 'APPROVED').length > 0 && (
                                            <div className="mt-3 pt-3 border-t">
                                                <div className="text-sm text-gray-600">
                                                    Last Completed: <strong>{formatMonthYearRange(
                                                        cycles.filter(c => c.status === 'APPROVED')[0]?.period_start_date || '',
                                                        cycles.filter(c => c.status === 'APPROVED')[0]?.period_end_date || ''
                                                    )}</strong>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                    {/* Plan Details */}
                                    <div className="bg-white rounded-lg border p-4">
                                        <div className="flex items-center justify-between mb-3">
                                            <h4 className="text-sm font-semibold text-gray-500 uppercase">Plan Details</h4>
                                            {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && !editingPlanDetails && (
                                                <button
                                                    onClick={startEditingPlanDetails}
                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                    title="Edit plan details"
                                                >
                                                    ✏️ Edit
                                                </button>
                                            )}
                                        </div>
                                        {editingPlanDetails ? (
                                            <div className="space-y-3">
                                                <div>
                                                    <label className="block text-sm text-gray-500 mb-1">Data Provider</label>
                                                    <select
                                                        value={planDetailsForm.data_provider_user_id || ''}
                                                        onChange={(e) => setPlanDetailsForm({
                                                            ...planDetailsForm,
                                                            data_provider_user_id: e.target.value ? parseInt(e.target.value) : null
                                                        })}
                                                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                                                        disabled={savingPlanDetails}
                                                    >
                                                        <option value="">None</option>
                                                        {availableUsers.map(user => (
                                                            <option key={user.user_id} value={user.user_id}>
                                                                {user.full_name}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className="block text-sm text-gray-500 mb-1">Lead Time (days)</label>
                                                    <input
                                                        type="number"
                                                        min="0"
                                                        max="90"
                                                        value={planDetailsForm.reporting_lead_days}
                                                        onChange={(e) => setPlanDetailsForm({
                                                            ...planDetailsForm,
                                                            reporting_lead_days: parseInt(e.target.value) || 0
                                                        })}
                                                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                                                        disabled={savingPlanDetails}
                                                    />
                                                </div>
                                                <div className="flex items-center gap-2 pt-2">
                                                    <button
                                                        onClick={() => handleSavePlanDetails(false)}
                                                        disabled={savingPlanDetails}
                                                        className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                                    >
                                                        {savingPlanDetails ? 'Saving...' : 'Save'}
                                                    </button>
                                                    <button
                                                        onClick={cancelEditingPlanDetails}
                                                        disabled={savingPlanDetails}
                                                        className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                                                    >
                                                        Cancel
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
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
                                        )}
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
                            <div className="flex justify-between items-center mb-4">
                                <div>
                                    <h3 className="text-lg font-semibold">Covered Models ({plan.models?.length || 0})</h3>
                                    {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                        <p className="text-sm text-gray-500 mt-1">
                                            Add or remove models from this monitoring plan
                                        </p>
                                    )}
                                </div>
                                {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                    <button
                                        onClick={openAddModelModal}
                                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                        </svg>
                                        Add Model
                                    </button>
                                )}
                            </div>
                            {!plan.models?.length ? (
                                <div className="text-center py-8 text-gray-500">
                                    <svg className="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                    </svg>
                                    <p>No models assigned to this plan.</p>
                                    {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                        <button
                                            onClick={openAddModelModal}
                                            className="mt-3 text-blue-600 hover:text-blue-800 text-sm"
                                        >
                                            + Add your first model
                                        </button>
                                    )}
                                </div>
                            ) : (
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Model ID</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Model Name</th>
                                            {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                                            )}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200">
                                        {plan.models.map((model) => (
                                            <tr key={model.model_id} className="hover:bg-gray-50">
                                                <td className="px-4 py-2 text-sm">{model.model_id}</td>
                                                <td className="px-4 py-2 text-sm">
                                                    <Link to={`/models/${model.model_id}`} className="text-blue-600 hover:underline">
                                                        {model.model_name}
                                                    </Link>
                                                </td>
                                                {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                                    <td className="px-4 py-2 text-sm text-right">
                                                        <button
                                                            onClick={() => handleRemoveModel(model.model_id)}
                                                            disabled={removingModelId === model.model_id}
                                                            className="text-red-600 hover:text-red-800 disabled:opacity-50 flex items-center gap-1 ml-auto"
                                                        >
                                                            {removingModelId === model.model_id ? (
                                                                <span className="animate-spin h-4 w-4 border-2 border-red-500 border-t-transparent rounded-full" />
                                                            ) : (
                                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                </svg>
                                                            )}
                                                            Remove
                                                        </button>
                                                    </td>
                                                )}
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
                                            Add metrics, edit thresholds, and publish a new version when ready
                                        </p>
                                    )}
                                </div>
                                {(plan.user_permissions?.is_admin || plan.user_permissions?.is_team_member) && (
                                    <button
                                        onClick={() => setShowAddMetricModal(true)}
                                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                        </svg>
                                        Add Metric
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
                                                        <>
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
                                                            <button
                                                                onClick={() => handleDeactivateMetric(metric.metric_id)}
                                                                className="text-red-600 hover:text-red-800 text-sm flex items-center gap-1"
                                                                title="Deactivate metric"
                                                            >
                                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                                                                </svg>
                                                                Deactivate
                                                            </button>
                                                        </>
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

                                                    {/* Models in Scope Section */}
                                                    <h5 className="text-sm font-medium text-gray-700 mb-3 mt-6 pt-4 border-t">
                                                        Models in Scope ({selectedVersionDetail.model_snapshots?.length || 0})
                                                    </h5>
                                                    {selectedVersionDetail.model_snapshots && selectedVersionDetail.model_snapshots.length > 0 ? (
                                                        <div className="grid grid-cols-2 gap-2">
                                                            {selectedVersionDetail.model_snapshots.map((model) => (
                                                                <div key={model.snapshot_id} className="border rounded p-2 text-sm flex items-center gap-2">
                                                                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                                                                    </svg>
                                                                    <div>
                                                                        <div className="font-medium">{model.model_name}</div>
                                                                        <div className="text-xs text-gray-500">ID: {model.model_id}</div>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        <div className="text-sm text-gray-400 italic">No models were in scope for this version</div>
                                                    )}
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="p-8 text-center text-gray-400">
                                                <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                </svg>
                                                <p>Select a version to view its snapshots</p>
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
                                                            } else if (action.action === 'request-approval') {
                                                                openRequestApprovalModal(currentCycle.cycle_id);
                                                            } else if (action.action === 'start') {
                                                                openStartCycleModal(currentCycle.cycle_id);
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
                                                <Link
                                                    to={`/monitoring/cycles/${currentCycle.cycle_id}`}
                                                    className={`px-4 py-2 rounded text-sm font-medium ${canEnterResults(currentCycle) ? 'bg-green-600 text-white hover:bg-green-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                                                >
                                                    {canEnterResults(currentCycle) ? 'Enter Results' : 'View Details'}
                                                </Link>
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
                                                        <Link
                                                            to={`/monitoring/cycles/${cycle.cycle_id}`}
                                                            className="text-blue-600 hover:underline text-sm"
                                                        >
                                                            View
                                                        </Link>
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

                {/* Start Cycle Modal */}
                {showStartCycleModal && startCycleId && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
                            <div className="p-4 border-b bg-blue-50">
                                <h3 className="text-lg font-bold text-blue-800">Start Cycle</h3>
                            </div>

                            <div className="p-4 space-y-4">
                                {actionError && (
                                    <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                                        {actionError}
                                    </div>
                                )}

                                {!plan?.active_version_number ? (
                                    <div className="bg-red-50 border border-red-300 rounded-lg p-3">
                                        <p className="text-red-800 text-sm">
                                            <strong>Cannot Start:</strong> No published plan version exists.
                                            You must publish a version before starting data collection.
                                        </p>
                                    </div>
                                ) : (
                                    <>
                                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                            <p className="text-blue-800 text-sm">
                                                Starting this cycle will lock it to <strong>Version {plan.active_version_number}</strong> (current active version).
                                                Once started, the cycle will use the metrics defined in that version.
                                            </p>
                                        </div>

                                        {plan.has_unpublished_changes && (
                                            <div className="bg-amber-50 border border-amber-300 rounded-lg p-3">
                                                <p className="text-amber-800 text-sm">
                                                    <strong>Note:</strong> You have unpublished metric changes.
                                                    This cycle will use the metrics from Version {plan.active_version_number},
                                                    not your pending changes. Consider publishing a new version first if you want the updated metrics.
                                                </p>
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>

                            <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                                <button
                                    onClick={() => {
                                        setShowStartCycleModal(false);
                                        setStartCycleId(null);
                                        setActionError(null);
                                    }}
                                    disabled={actionLoading}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleStartCycle}
                                    disabled={actionLoading || !plan?.active_version_number}
                                    className="px-4 py-2 rounded text-white font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {actionLoading ? 'Starting...' : 'Start Data Collection'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Update Cycle Assignee Prompt Modal */}
                {showUpdateCycleAssigneePrompt && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
                            <div className="p-4 border-b bg-blue-50">
                                <h3 className="text-lg font-bold text-blue-800">Update Current Cycle?</h3>
                            </div>

                            <div className="p-4 space-y-4">
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                    <p className="text-blue-800 text-sm">
                                        You're changing the Data Provider for this plan. There is an active cycle
                                        ({getActiveCycleForAssigneeUpdate()?.status === 'PENDING' ? 'Pending' : 'Data Collection in progress'})
                                        that hasn't been submitted for review yet.
                                    </p>
                                </div>
                                <p className="text-sm text-gray-700">
                                    Would you like to also update the assignee for the current cycle to the new Data Provider?
                                </p>
                            </div>

                            <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                                <button
                                    onClick={() => handleCycleAssigneePromptResponse(false)}
                                    disabled={savingPlanDetails}
                                    className="px-4 py-2 rounded text-gray-700 font-medium bg-gray-200 hover:bg-gray-300 disabled:opacity-50"
                                >
                                    No, Keep Current Assignee
                                </button>
                                <button
                                    onClick={() => handleCycleAssigneePromptResponse(true)}
                                    disabled={savingPlanDetails}
                                    className="px-4 py-2 rounded text-white font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {savingPlanDetails ? 'Updating...' : 'Yes, Update Assignee'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Request Approval Modal */}
                {showRequestApprovalModal && requestApprovalCycleId && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
                            <div className="p-4 border-b bg-blue-50">
                                <h3 className="text-lg font-bold text-blue-800">Request Approval</h3>
                            </div>

                            <div className="p-4 space-y-4">
                                {actionError && (
                                    <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                                        {actionError}
                                    </div>
                                )}

                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                    <p className="text-blue-800 text-sm">
                                        Please provide the URL to the final monitoring report document. Approvers will review this report before providing their approval.
                                    </p>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Report Document URL *
                                    </label>
                                    <input
                                        type="url"
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                        value={reportUrl}
                                        onChange={(e) => setReportUrl(e.target.value)}
                                        placeholder="https://sharepoint.example.com/reports/..."
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        Enter the full URL to the monitoring report (e.g., SharePoint, OneDrive, Google Drive)
                                    </p>
                                </div>
                            </div>

                            <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                                <button
                                    onClick={() => {
                                        setShowRequestApprovalModal(false);
                                        setRequestApprovalCycleId(null);
                                        setReportUrl('');
                                        setActionError(null);
                                    }}
                                    disabled={actionLoading}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleRequestApproval}
                                    disabled={actionLoading || !reportUrl.trim()}
                                    className="px-4 py-2 rounded text-white font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {actionLoading ? 'Submitting...' : 'Request Approval'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Breach Resolution Wizard */}
                {showBreachWizard && pendingBreaches.length > 0 && (
                    <BreachResolutionWizard
                        breaches={pendingBreaches}
                        onComplete={handleBreachResolutionComplete}
                        onCancel={handleBreachResolutionCancel}
                        isLoading={breachResolutionLoading}
                    />
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
                                        <ThresholdWizard
                                            values={{
                                                yellow_min: metricForm.yellow_min ? parseFloat(metricForm.yellow_min) : null,
                                                yellow_max: metricForm.yellow_max ? parseFloat(metricForm.yellow_max) : null,
                                                red_min: metricForm.red_min ? parseFloat(metricForm.red_min) : null,
                                                red_max: metricForm.red_max ? parseFloat(metricForm.red_max) : null,
                                            }}
                                            onChange={(values: ThresholdValues) => {
                                                setMetricForm(prev => ({
                                                    ...prev,
                                                    yellow_min: values.yellow_min?.toString() ?? '',
                                                    yellow_max: values.yellow_max?.toString() ?? '',
                                                    red_min: values.red_min?.toString() ?? '',
                                                    red_max: values.red_max?.toString() ?? '',
                                                }));
                                            }}
                                            suggestedMin={0}
                                            suggestedMax={1}
                                        />
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

                {/* Add Metric Modal */}
                {showAddMetricModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
                            <div className="p-4 border-b">
                                <h3 className="text-lg font-bold">Add Metric to Plan</h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    Select a KPM and configure thresholds
                                </p>
                            </div>

                            <form onSubmit={handleAddMetric}>
                                <div className="p-4 space-y-4">
                                    {addMetricError && (
                                        <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                                            {addMetricError}
                                        </div>
                                    )}

                                    {/* KPM Selection */}
                                    <div>
                                        <div className="flex items-center justify-between mb-1">
                                            <label className="block text-sm font-medium text-gray-700">
                                                Select KPM *
                                            </label>
                                            <a
                                                href="/taxonomy?tab=kpm"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-xs text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
                                            >
                                                + Create New KPM
                                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                                </svg>
                                            </a>
                                        </div>
                                        <select
                                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                            value={addMetricForm.kpm_id}
                                            onChange={(e) => setAddMetricForm(prev => ({ ...prev, kpm_id: parseInt(e.target.value) || 0 }))}
                                            required
                                        >
                                            <option value={0}>-- Select a KPM --</option>
                                            {kpmCategories.map(cat => (
                                                <optgroup key={cat.category_id} label={cat.name}>
                                                    {cat.kpms
                                                        .filter(kpm => !plan?.metrics?.some(m => m.kpm_id === kpm.kpm_id))
                                                        .map(kpm => (
                                                            <option key={kpm.kpm_id} value={kpm.kpm_id}>
                                                                {kpm.name} ({kpm.evaluation_type})
                                                            </option>
                                                        ))
                                                    }
                                                </optgroup>
                                            ))}
                                        </select>
                                    </div>

                                    {/* Threshold Configuration */}
                                    {addMetricForm.kpm_id > 0 && (() => {
                                        const selectedKpm = kpmCategories.flatMap(c => c.kpms).find(k => k.kpm_id === addMetricForm.kpm_id);
                                        const isQuantitative = selectedKpm?.evaluation_type === 'Quantitative';

                                        if (isQuantitative) {
                                            return (
                                                <>
                                                    <ThresholdWizard
                                                        values={{
                                                            yellow_min: addMetricForm.yellow_min ? parseFloat(addMetricForm.yellow_min) : null,
                                                            yellow_max: addMetricForm.yellow_max ? parseFloat(addMetricForm.yellow_max) : null,
                                                            red_min: addMetricForm.red_min ? parseFloat(addMetricForm.red_min) : null,
                                                            red_max: addMetricForm.red_max ? parseFloat(addMetricForm.red_max) : null,
                                                        }}
                                                        onChange={(values: ThresholdValues) => {
                                                            setAddMetricForm(prev => ({
                                                                ...prev,
                                                                yellow_min: values.yellow_min?.toString() ?? '',
                                                                yellow_max: values.yellow_max?.toString() ?? '',
                                                                red_min: values.red_min?.toString() ?? '',
                                                                red_max: values.red_max?.toString() ?? '',
                                                            }));
                                                        }}
                                                        suggestedMin={0}
                                                        suggestedMax={1}
                                                    />

                                                    {/* Additional Guidance for Quantitative */}
                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                                            Additional Guidance
                                                        </label>
                                                        <textarea
                                                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                            rows={2}
                                                            value={addMetricForm.qualitative_guidance}
                                                            onChange={(e) => setAddMetricForm(prev => ({ ...prev, qualitative_guidance: e.target.value }))}
                                                            placeholder="Additional guidance for interpreting this metric..."
                                                        />
                                                    </div>
                                                </>
                                            );
                                        } else {
                                            return (
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        Assessment Guidance *
                                                    </label>
                                                    <textarea
                                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                                        rows={4}
                                                        value={addMetricForm.qualitative_guidance}
                                                        onChange={(e) => setAddMetricForm(prev => ({ ...prev, qualitative_guidance: e.target.value }))}
                                                        placeholder="Describe the criteria for Green/Yellow/Red outcomes..."
                                                        required
                                                    />
                                                    <p className="text-xs text-gray-500 mt-1">
                                                        For qualitative metrics, guidance is required to define how outcomes should be assessed.
                                                    </p>
                                                </div>
                                            );
                                        }
                                    })()}
                                </div>

                                <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                                    <button
                                        type="button"
                                        onClick={() => {
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
                                            setAddMetricError(null);
                                        }}
                                        disabled={addingMetric}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={addingMetric || !addMetricForm.kpm_id}
                                        className="px-4 py-2 rounded text-white font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        {addingMetric ? 'Adding...' : 'Add Metric'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* Add Model Modal */}
                {showAddModelModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
                            <div className="p-4 border-b">
                                <h3 className="text-lg font-bold">Add Model to Plan</h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    Select a model to add to this monitoring plan
                                </p>
                            </div>

                            <div className="p-4 border-b">
                                <input
                                    type="text"
                                    placeholder="Search by model name or ID..."
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                                    value={modelSearchTerm}
                                    onChange={(e) => setModelSearchTerm(e.target.value)}
                                    autoFocus
                                />
                            </div>

                            <div className="flex-1 overflow-y-auto p-4" style={{ maxHeight: '400px' }}>
                                {loadingAllModels ? (
                                    <div className="flex items-center justify-center py-8">
                                        <span className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full mr-2" />
                                        Loading models...
                                    </div>
                                ) : filteredAvailableModels.length === 0 ? (
                                    <div className="text-center py-8 text-gray-500">
                                        {modelSearchTerm ? (
                                            <p>No models found matching "{modelSearchTerm}"</p>
                                        ) : availableModels.length === 0 ? (
                                            <p>All models are already added to this plan</p>
                                        ) : (
                                            <p>No available models</p>
                                        )}
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {filteredAvailableModels.map(model => (
                                            <div
                                                key={model.model_id}
                                                className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
                                            >
                                                <div>
                                                    <div className="font-medium text-gray-900">{model.model_name}</div>
                                                    <div className="text-sm text-gray-500">ID: {model.model_id}</div>
                                                </div>
                                                <button
                                                    onClick={() => handleAddModel(model.model_id)}
                                                    disabled={addingModel}
                                                    className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
                                                >
                                                    {addingModel ? (
                                                        <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                                                    ) : (
                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                                        </svg>
                                                    )}
                                                    Add
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="p-4 border-t bg-gray-50 flex justify-between items-center">
                                <span className="text-sm text-gray-500">
                                    {filteredAvailableModels.length} model{filteredAvailableModels.length !== 1 ? 's' : ''} available
                                </span>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowAddModelModal(false);
                                        setModelSearchTerm('');
                                    }}
                                    className="btn-secondary"
                                >
                                    Close
                                </button>
                            </div>
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

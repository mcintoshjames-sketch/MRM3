import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';
import { useTableSort } from '../hooks/useTableSort';

interface PendingApproval {
    approval_id: number;
    request_id: number;
    model_ids: number[];
    model_names: string[];
    validation_type: string;
    priority: string;
    current_status: string;
    requestor_name: string;
    primary_validator: string | null;
    target_completion_date: string | null;
    approval_type: string;
    approver_role: string;
    is_required: boolean;
    represented_region: string | null;
    days_pending: number;
    request_date: string;
}

interface RecommendationApprovalTask {
    task_type: 'ACTION_REQUIRED' | 'REVIEW_PENDING' | 'APPROVAL_PENDING';
    recommendation_id: number;
    recommendation_code: string;
    title: string;
    model: { model_id: number; model_name: string };
    priority: { code: string; label: string };
    current_status: { code: string; label: string };
    current_target_date: string | null;
    action_description: string;
    days_until_due: number | null;
    is_overdue: boolean;
}

interface MonitoringApprovalQueueItem {
    approval_id: number;
    cycle_id: number;
    plan_id: number;
    plan_name: string;
    period_start_date: string;
    period_end_date: string;
    submission_due_date: string;
    report_due_date: string;
    cycle_status: string;
    approval_type: string;
    region: { region_id: number; region_name: string; region_code: string } | null;
    is_required: boolean;
    approval_status: string;
    days_pending: number;
    created_at: string;
    can_approve: boolean;
}

type DashboardTab = 'validation' | 'recommendations' | 'monitoring';
type ValidationFilterMode = 'all' | 'overdue' | 'needs_attention' | 'new' | 'urgent';
type RecommendationFilterMode = 'all' | 'overdue' | 'due_soon' | 'on_track' | 'urgent';
type MonitoringFilterMode = 'all' | 'overdue' | 'needs_attention' | 'new' | 'global' | 'regional';
type ValidationRow = PendingApproval & { model_display: string };

type DashboardErrors = {
    validation: string | null;
    recommendations: string | null;
    monitoring: string | null;
};

export default function ApproverDashboardPage() {
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState<DashboardTab>('validation');
    const [validationApprovals, setValidationApprovals] = useState<PendingApproval[]>([]);
    const [recommendationApprovals, setRecommendationApprovals] = useState<RecommendationApprovalTask[]>([]);
    const [monitoringApprovals, setMonitoringApprovals] = useState<MonitoringApprovalQueueItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [errors, setErrors] = useState<DashboardErrors>({
        validation: null,
        recommendations: null,
        monitoring: null
    });
    const [validationFilterMode, setValidationFilterMode] = useState<ValidationFilterMode>('all');
    const [recommendationFilterMode, setRecommendationFilterMode] = useState<RecommendationFilterMode>('all');
    const [monitoringFilterMode, setMonitoringFilterMode] = useState<MonitoringFilterMode>('all');

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        setLoading(true);
        setErrors({ validation: null, recommendations: null, monitoring: null });

        const [validationResult, recommendationsResult, monitoringResult] = await Promise.allSettled([
            api.get('/validation-workflow/my-pending-approvals'),
            api.get('/recommendations/my-tasks'),
            api.get('/monitoring/approvals/my-pending')
        ]);

        if (validationResult.status === 'fulfilled') {
            setValidationApprovals(validationResult.value.data || []);
        } else {
            setValidationApprovals([]);
            setErrors((prev) => ({
                ...prev,
                validation: validationResult.reason?.response?.data?.detail || validationResult.reason?.message || 'Failed to load validation approvals'
            }));
        }

        if (recommendationsResult.status === 'fulfilled') {
            const tasks = recommendationsResult.value.data?.tasks || [];
            const approvalTasks = tasks.filter((task: RecommendationApprovalTask) => task.task_type === 'APPROVAL_PENDING');
            setRecommendationApprovals(approvalTasks);
        } else {
            setRecommendationApprovals([]);
            setErrors((prev) => ({
                ...prev,
                recommendations: recommendationsResult.reason?.response?.data?.detail || recommendationsResult.reason?.message || 'Failed to load recommendation approvals'
            }));
        }

        if (monitoringResult.status === 'fulfilled') {
            setMonitoringApprovals(monitoringResult.value.data || []);
        } else {
            setMonitoringApprovals([]);
            setErrors((prev) => ({
                ...prev,
                monitoring: monitoringResult.reason?.response?.data?.detail || monitoringResult.reason?.message || 'Failed to load monitoring approvals'
            }));
        }

        setLoading(false);
    };

    const formatDate = (value: string | null | undefined) => {
        if (!value) return '-';
        return value.split('T')[0];
    };

    const formatPeriod = (start: string, end: string) => {
        return `${formatDate(start)} - ${formatDate(end)}`;
    };

    const escapeCsvValue = (value: string | number | null | undefined) => {
        if (value === null || value === undefined) return '""';
        const stringValue = String(value).replace(/"/g, '""');
        return `"${stringValue}"`;
    };

    const downloadCsv = (headers: string[], rows: (string | number | null | undefined)[][], filename: string) => {
        const csvContent = [
            headers.map(escapeCsvValue).join(','),
            ...rows.map((row) => row.map(escapeCsvValue).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.setAttribute('download', filename);
        link.click();
        URL.revokeObjectURL(link.href);
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'Critical': return 'bg-red-100 text-red-800';
            case 'High': return 'bg-orange-100 text-orange-800';
            case 'Medium': return 'bg-yellow-100 text-yellow-800';
            case 'Low': return 'bg-green-100 text-green-800';
            case 'Urgent': return 'bg-red-100 text-red-800';
            case 'Standard': return 'bg-blue-100 text-blue-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getApprovalTypeColor = (approvalType: string) => {
        switch (approvalType) {
            case 'Global': return 'bg-blue-100 text-blue-800';
            case 'Regional': return 'bg-purple-100 text-purple-800';
            case 'Conditional': return 'bg-orange-100 text-orange-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getUrgencyColor = (daysPending: number) => {
        if (daysPending >= 7) return 'bg-red-100 text-red-800';
        if (daysPending >= 3) return 'bg-yellow-100 text-yellow-800';
        return 'bg-green-100 text-green-800';
    };

    const getDueStatusColor = (daysUntilDue: number | null) => {
        if (daysUntilDue === null || daysUntilDue === undefined) return 'bg-gray-100 text-gray-800';
        if (daysUntilDue < 0) return 'bg-red-100 text-red-800';
        if (daysUntilDue <= 7) return 'bg-yellow-100 text-yellow-800';
        return 'bg-green-100 text-green-800';
    };

    const getDueLabel = (daysUntilDue: number | null) => {
        if (daysUntilDue === null || daysUntilDue === undefined) return 'No target';
        if (daysUntilDue < 0) return `${Math.abs(daysUntilDue)} days overdue`;
        if (daysUntilDue === 0) return 'Due today';
        return `${daysUntilDue} days`;
    };

    const getRoleDisplay = () => {
        if (user?.role === 'Admin') return 'Administrator';
        if (user?.role === 'Global Approver') return 'Global Approver';
        if (user?.role === 'Regional Approver') return 'Regional Approver';
        return user?.role || 'User';
    };

    const isUrgentPriority = (priority?: { code: string; label: string }) => {
        if (!priority) return false;
        const label = priority.label || priority.code || '';
        return label.toLowerCase() === 'urgent';
    };

    // Validation filters
    const validationUrgentApprovals = validationApprovals.filter(a => a.priority === 'Urgent');
    const validationOverdue = validationApprovals.filter(a => a.days_pending >= 7);
    const validationNeedsAttention = validationApprovals.filter(a => a.days_pending >= 3 && a.days_pending < 7);
    const validationNew = validationApprovals.filter(a => a.days_pending < 3);

    const filteredValidationApprovals = validationApprovals.filter((approval) => {
        switch (validationFilterMode) {
            case 'overdue':
                return approval.days_pending >= 7;
            case 'needs_attention':
                return approval.days_pending >= 3 && approval.days_pending < 7;
            case 'new':
                return approval.days_pending < 3;
            case 'urgent':
                return approval.priority === 'Urgent';
            default:
                return true;
        }
    });

    const validationHasActiveFilter = validationFilterMode !== 'all';
    const validationFilterLabel = (() => {
        switch (validationFilterMode) {
            case 'overdue':
                return 'Overdue (7+ days)';
            case 'needs_attention':
                return 'Needs Attention (3-6 days)';
            case 'new':
                return 'New (<3 days)';
            case 'urgent':
                return 'Urgent Priority';
            default:
                return 'All Pending';
        }
    })();

    const validationRows = filteredValidationApprovals.map((approval) => ({
        ...approval,
        model_display: approval.model_names.join('; ')
    }));

    const {
        sortedData: sortedValidationRows,
        requestSort: requestValidationSort,
        getSortIcon: getValidationSortIcon
    } = useTableSort<ValidationRow>(validationRows, 'days_pending', 'desc');

    // Recommendation filters
    const recommendationUrgentApprovals = recommendationApprovals.filter((task) => isUrgentPriority(task.priority));
    const recommendationOverdue = recommendationApprovals.filter((task) => task.is_overdue || ((task.days_until_due ?? 0) < 0));
    const recommendationDueSoon = recommendationApprovals.filter((task) => {
        if (task.is_overdue || task.days_until_due === null || task.days_until_due === undefined) return false;
        return task.days_until_due >= 0 && task.days_until_due <= 7;
    });
    const recommendationOnTrack = recommendationApprovals.filter((task) => {
        if (task.is_overdue) return false;
        if (task.days_until_due === null || task.days_until_due === undefined) return true;
        return task.days_until_due > 7;
    });

    const filteredRecommendationApprovals = recommendationApprovals.filter((task) => {
        switch (recommendationFilterMode) {
            case 'overdue':
                return task.is_overdue || ((task.days_until_due ?? 0) < 0);
            case 'due_soon':
                return !task.is_overdue && task.days_until_due !== null && task.days_until_due <= 7 && task.days_until_due >= 0;
            case 'on_track':
                return !task.is_overdue && (task.days_until_due === null || task.days_until_due > 7);
            case 'urgent':
                return isUrgentPriority(task.priority);
            default:
                return true;
        }
    });

    const recommendationHasActiveFilter = recommendationFilterMode !== 'all';
    const recommendationFilterLabel = (() => {
        switch (recommendationFilterMode) {
            case 'overdue':
                return 'Overdue (past target date)';
            case 'due_soon':
                return 'Due Soon (0-7 days)';
            case 'on_track':
                return 'On Track (8+ days)';
            case 'urgent':
                return 'Urgent Priority';
            default:
                return 'All Pending';
        }
    })();

    const {
        sortedData: sortedRecommendationApprovals,
        requestSort: requestRecommendationSort,
        getSortIcon: getRecommendationSortIcon
    } = useTableSort<RecommendationApprovalTask>(filteredRecommendationApprovals, 'days_until_due', 'asc');

    // Monitoring filters
    const monitoringGlobalApprovals = monitoringApprovals.filter((approval) => approval.approval_type === 'Global');
    const monitoringRegionalApprovals = monitoringApprovals.filter((approval) => approval.approval_type === 'Regional');
    const monitoringOverdue = monitoringApprovals.filter((approval) => approval.days_pending >= 7);
    const monitoringNeedsAttention = monitoringApprovals.filter((approval) => approval.days_pending >= 3 && approval.days_pending < 7);
    const monitoringNew = monitoringApprovals.filter((approval) => approval.days_pending < 3);

    const filteredMonitoringApprovals = monitoringApprovals.filter((approval) => {
        switch (monitoringFilterMode) {
            case 'overdue':
                return approval.days_pending >= 7;
            case 'needs_attention':
                return approval.days_pending >= 3 && approval.days_pending < 7;
            case 'new':
                return approval.days_pending < 3;
            case 'global':
                return approval.approval_type === 'Global';
            case 'regional':
                return approval.approval_type === 'Regional';
            default:
                return true;
        }
    });

    const monitoringHasActiveFilter = monitoringFilterMode !== 'all';
    const monitoringFilterLabel = (() => {
        switch (monitoringFilterMode) {
            case 'overdue':
                return 'Overdue (7+ days)';
            case 'needs_attention':
                return 'Needs Attention (3-6 days)';
            case 'new':
                return 'New (<3 days)';
            case 'global':
                return 'Global approvals';
            case 'regional':
                return 'Regional approvals';
            default:
                return 'All Pending';
        }
    })();

    const {
        sortedData: sortedMonitoringApprovals,
        requestSort: requestMonitoringSort,
        getSortIcon: getMonitoringSortIcon
    } = useTableSort<MonitoringApprovalQueueItem>(filteredMonitoringApprovals, 'days_pending', 'desc');

    const errorMessages = [
        errors.validation ? `Validation approvals: ${errors.validation}` : null,
        errors.recommendations ? `Recommendation approvals: ${errors.recommendations}` : null,
        errors.monitoring ? `Monitoring approvals: ${errors.monitoring}` : null
    ].filter(Boolean) as string[];

    const tabs = [
        { id: 'validation', label: 'Validation', count: validationApprovals.length },
        { id: 'recommendations', label: 'Recommendations', count: recommendationApprovals.length },
        { id: 'monitoring', label: 'Monitoring', count: monitoringApprovals.length }
    ] as const;

    const exportValidationCsv = () => {
        const headers = ['Request ID', 'Models', 'Validation Type', 'Priority', 'Requestor', 'Validator', 'Approval Type', 'Region', 'Days Pending', 'Target Date'];
        const rows = sortedValidationRows.map((approval) => [
            `#${approval.request_id}`,
            approval.model_names.join('; '),
            approval.validation_type,
            approval.priority,
            approval.requestor_name,
            approval.primary_validator || '',
            approval.approval_type,
            approval.represented_region || '',
            approval.days_pending,
            formatDate(approval.target_completion_date)
        ]);

        const filename = `validation_approvals_${new Date().toISOString().split('T')[0]}.csv`;
        downloadCsv(headers, rows, filename);
    };

    const exportRecommendationCsv = () => {
        const headers = ['Recommendation', 'Title', 'Model', 'Priority', 'Status', 'Action Required', 'Target Date', 'Days Until Due'];
        const rows = sortedRecommendationApprovals.map((task) => [
            task.recommendation_code,
            task.title,
            task.model?.model_name || '',
            task.priority?.label || task.priority?.code || '',
            task.current_status?.label || task.current_status?.code || '',
            task.action_description,
            formatDate(task.current_target_date),
            task.days_until_due ?? ''
        ]);

        const filename = `recommendation_approvals_${new Date().toISOString().split('T')[0]}.csv`;
        downloadCsv(headers, rows, filename);
    };

    const exportMonitoringCsv = () => {
        const headers = ['Plan', 'Cycle Period', 'Approval Type', 'Region', 'Days Pending', 'Report Due Date', 'Cycle Status'];
        const rows = sortedMonitoringApprovals.map((approval) => [
            approval.plan_name,
            formatPeriod(approval.period_start_date, approval.period_end_date),
            approval.approval_type,
            approval.region?.region_name || '',
            approval.days_pending,
            formatDate(approval.report_due_date),
            approval.cycle_status
        ]);

        const filename = `monitoring_approvals_${new Date().toISOString().split('T')[0]}.csv`;
        downloadCsv(headers, rows, filename);
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="mb-6">
                <h2 className="text-2xl font-bold">Approver Dashboard</h2>
                <p className="text-gray-600 mt-1">
                    Welcome, {user?.full_name}. You are logged in as <span className="font-medium">{getRoleDisplay()}</span>.
                </p>
                <p className="text-sm text-gray-500 mt-2">
                    Review and finalize approvals across validation, recommendation, and monitoring workflows.
                </p>
            </div>

            {errorMessages.length > 0 && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    <p className="font-medium">Some data could not be loaded:</p>
                    <ul className="mt-1 text-sm list-disc list-inside space-y-1">
                        {errorMessages.map((message) => (
                            <li key={message}>{message}</li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="flex flex-wrap gap-3 mb-6">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        type="button"
                        aria-pressed={activeTab === tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-full border transition-colors ${
                            activeTab === tab.id
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                        }`}
                    >
                        <span className="font-medium">{tab.label}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                            activeTab === tab.id ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-700'
                        }`}>
                            {tab.count}
                        </span>
                    </button>
                ))}
            </div>

            {activeTab === 'validation' && (
                <>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
                        <button
                            type="button"
                            aria-pressed={validationFilterMode === 'all'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                                validationFilterMode === 'all' ? 'ring-2 ring-blue-500' : ''
                            }`}
                            onClick={() => setValidationFilterMode('all')}
                        >
                            <div className="text-sm text-gray-500">Awaiting Your Decision</div>
                            <div className="text-2xl font-bold text-blue-600">{validationApprovals.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={validationFilterMode === 'urgent'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 ${
                                validationFilterMode === 'urgent' ? 'ring-2 ring-red-500' : ''
                            }`}
                            onClick={() => setValidationFilterMode(validationFilterMode === 'urgent' ? 'all' : 'urgent')}
                        >
                            <div className="text-sm text-gray-500">Urgent Priority</div>
                            <div className="text-2xl font-bold text-red-600">{validationUrgentApprovals.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={validationFilterMode === 'overdue'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 ${
                                validationFilterMode === 'overdue' ? 'ring-2 ring-rose-500' : ''
                            }`}
                            onClick={() => setValidationFilterMode(validationFilterMode === 'overdue' ? 'all' : 'overdue')}
                        >
                            <div className="text-sm text-gray-500">Overdue (7+ days)</div>
                            <div className="text-2xl font-bold text-rose-600">{validationOverdue.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={validationFilterMode === 'needs_attention'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 ${
                                validationFilterMode === 'needs_attention' ? 'ring-2 ring-yellow-500' : ''
                            }`}
                            onClick={() => setValidationFilterMode(validationFilterMode === 'needs_attention' ? 'all' : 'needs_attention')}
                        >
                            <div className="text-sm text-gray-500">Needs Attention (3-6 days)</div>
                            <div className="text-2xl font-bold text-yellow-600">{validationNeedsAttention.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={validationFilterMode === 'new'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 ${
                                validationFilterMode === 'new' ? 'ring-2 ring-green-500' : ''
                            }`}
                            onClick={() => setValidationFilterMode(validationFilterMode === 'new' ? 'all' : 'new')}
                        >
                            <div className="text-sm text-gray-500">New (&lt;3 days)</div>
                            <div className="text-2xl font-bold text-green-600">{validationNew.length}</div>
                        </button>
                    </div>

                    {validationHasActiveFilter && (
                        <div className="mb-4 flex flex-wrap items-center gap-3">
                            <span className="text-sm text-gray-600">
                                Showing: <strong>{validationFilterLabel}</strong> approvals
                            </span>
                            <button
                                onClick={() => setValidationFilterMode('all')}
                                className="btn-secondary text-sm"
                            >
                                Clear filters
                            </button>
                        </div>
                    )}

                    <div id="approval-queue" className="bg-white rounded-lg shadow-md">
                        <div className="p-4 border-b bg-blue-50 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                            <div>
                                <h3 className="text-lg font-bold">Validation Approval Queue</h3>
                                <p className="text-sm text-gray-600">
                                    {filteredValidationApprovals.length} of {validationApprovals.length} approvals
                                    {validationHasActiveFilter ? ` • ${validationFilterLabel}` : ''}
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={exportValidationCsv}
                                className={`btn-secondary text-sm ${sortedValidationRows.length === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}
                                disabled={sortedValidationRows.length === 0}
                            >
                                Export CSV
                            </button>
                        </div>
                        {validationApprovals.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                <p className="text-lg font-medium">All caught up!</p>
                                <p className="text-sm">You have no pending validation approvals at this time.</p>
                            </div>
                        ) : filteredValidationApprovals.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                <p className="text-lg font-medium">No approvals found.</p>
                                <p className="text-sm">Try clearing the filter or select a different segment.</p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full min-w-[1400px] table-fixed divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th
                                                className="px-6 py-3 w-24 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestValidationSort('request_id')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    ID
                                                    {getValidationSortIcon('request_id')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-64 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestValidationSort('model_display')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Model(s)
                                                    {getValidationSortIcon('model_display')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-36 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestValidationSort('validation_type')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Validation Type
                                                    {getValidationSortIcon('validation_type')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-24 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestValidationSort('priority')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Priority
                                                    {getValidationSortIcon('priority')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-36 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestValidationSort('requestor_name')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Requestor
                                                    {getValidationSortIcon('requestor_name')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-36 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestValidationSort('primary_validator')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Validator
                                                    {getValidationSortIcon('primary_validator')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-36 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestValidationSort('approval_type')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Your Approval
                                                    {getValidationSortIcon('approval_type')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-28 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestValidationSort('days_pending')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Days Pending
                                                    {getValidationSortIcon('days_pending')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-32 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestValidationSort('target_completion_date')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Target Date
                                                    {getValidationSortIcon('target_completion_date')}
                                                </div>
                                            </th>
                                            <th className="px-6 py-3 w-32 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {sortedValidationRows.map((approval) => (
                                            <tr key={approval.approval_id} className="hover:bg-gray-50">
                                                <td className="px-6 py-4 w-24 whitespace-nowrap text-sm font-mono">
                                                    #{approval.request_id}
                                                </td>
                                                <td className="px-6 py-4 w-64 whitespace-normal break-words text-sm">
                                                    {approval.model_ids.length === 1 ? (
                                                        <Link
                                                            to={`/models/${approval.model_ids[0]}`}
                                                            className="font-medium text-blue-600 hover:text-blue-800"
                                                        >
                                                            {approval.model_names[0]}
                                                        </Link>
                                                    ) : (
                                                        <div className="space-y-1">
                                                            {approval.model_names.map((name, idx) => (
                                                                <div key={idx}>
                                                                    <Link
                                                                        to={`/models/${approval.model_ids[idx]}`}
                                                                        className="font-medium text-blue-600 hover:text-blue-800 text-sm"
                                                                    >
                                                                        {name}
                                                                    </Link>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 w-36 whitespace-nowrap text-sm">
                                                    {approval.validation_type}
                                                </td>
                                                <td className="px-6 py-4 w-24 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(approval.priority)}`}>
                                                        {approval.priority}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 w-36 whitespace-nowrap text-sm">
                                                    {approval.requestor_name}
                                                </td>
                                                <td className="px-6 py-4 w-36 whitespace-nowrap text-sm">
                                                    {approval.primary_validator || <span className="text-gray-400">Not assigned</span>}
                                                </td>
                                                <td className="px-6 py-4 w-36 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs rounded ${getApprovalTypeColor(approval.approval_type)}`}>
                                                        {approval.approval_type}
                                                    </span>
                                                    {approval.represented_region && (
                                                        <span className="ml-1 text-xs text-gray-500">
                                                            ({approval.represented_region})
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 w-28 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getUrgencyColor(approval.days_pending)}`}>
                                                        {approval.days_pending} days
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 w-32 whitespace-nowrap text-sm">
                                                    {formatDate(approval.target_completion_date)}
                                                </td>
                                                <td className="px-6 py-4 w-32 whitespace-nowrap">
                                                    <Link
                                                        to={`/validation-workflow/${approval.request_id}`}
                                                        className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                                    >
                                                        Review &amp; Approve
                                                    </Link>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </>
            )}

            {activeTab === 'recommendations' && (
                <>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
                        <button
                            type="button"
                            aria-pressed={recommendationFilterMode === 'all'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                                recommendationFilterMode === 'all' ? 'ring-2 ring-blue-500' : ''
                            }`}
                            onClick={() => setRecommendationFilterMode('all')}
                        >
                            <div className="text-sm text-gray-500">Awaiting Your Approval</div>
                            <div className="text-2xl font-bold text-blue-600">{recommendationApprovals.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={recommendationFilterMode === 'urgent'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 ${
                                recommendationFilterMode === 'urgent' ? 'ring-2 ring-red-500' : ''
                            }`}
                            onClick={() => setRecommendationFilterMode(recommendationFilterMode === 'urgent' ? 'all' : 'urgent')}
                        >
                            <div className="text-sm text-gray-500">Urgent Priority</div>
                            <div className="text-2xl font-bold text-red-600">{recommendationUrgentApprovals.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={recommendationFilterMode === 'overdue'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 ${
                                recommendationFilterMode === 'overdue' ? 'ring-2 ring-rose-500' : ''
                            }`}
                            onClick={() => setRecommendationFilterMode(recommendationFilterMode === 'overdue' ? 'all' : 'overdue')}
                        >
                            <div className="text-sm text-gray-500">Overdue</div>
                            <div className="text-2xl font-bold text-rose-600">{recommendationOverdue.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={recommendationFilterMode === 'due_soon'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 ${
                                recommendationFilterMode === 'due_soon' ? 'ring-2 ring-yellow-500' : ''
                            }`}
                            onClick={() => setRecommendationFilterMode(recommendationFilterMode === 'due_soon' ? 'all' : 'due_soon')}
                        >
                            <div className="text-sm text-gray-500">Due Soon (0-7 days)</div>
                            <div className="text-2xl font-bold text-yellow-600">{recommendationDueSoon.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={recommendationFilterMode === 'on_track'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 ${
                                recommendationFilterMode === 'on_track' ? 'ring-2 ring-green-500' : ''
                            }`}
                            onClick={() => setRecommendationFilterMode(recommendationFilterMode === 'on_track' ? 'all' : 'on_track')}
                        >
                            <div className="text-sm text-gray-500">On Track (8+ days)</div>
                            <div className="text-2xl font-bold text-green-600">{recommendationOnTrack.length}</div>
                        </button>
                    </div>

                    {recommendationHasActiveFilter && (
                        <div className="mb-4 flex flex-wrap items-center gap-3">
                            <span className="text-sm text-gray-600">
                                Showing: <strong>{recommendationFilterLabel}</strong> approvals
                            </span>
                            <button
                                onClick={() => setRecommendationFilterMode('all')}
                                className="btn-secondary text-sm"
                            >
                                Clear filters
                            </button>
                        </div>
                    )}

                    <div id="approval-queue" className="bg-white rounded-lg shadow-md">
                        <div className="p-4 border-b bg-blue-50 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                            <div>
                                <h3 className="text-lg font-bold">Recommendation Approval Queue</h3>
                                <p className="text-sm text-gray-600">
                                    {filteredRecommendationApprovals.length} of {recommendationApprovals.length} approvals
                                    {recommendationHasActiveFilter ? ` • ${recommendationFilterLabel}` : ''}
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={exportRecommendationCsv}
                                className={`btn-secondary text-sm ${sortedRecommendationApprovals.length === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}
                                disabled={sortedRecommendationApprovals.length === 0}
                            >
                                Export CSV
                            </button>
                        </div>
                        {recommendationApprovals.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                <p className="text-lg font-medium">All caught up!</p>
                                <p className="text-sm">You have no pending recommendation approvals at this time.</p>
                            </div>
                        ) : filteredRecommendationApprovals.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                <p className="text-lg font-medium">No approvals found.</p>
                                <p className="text-sm">Try clearing the filter or select a different segment.</p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full min-w-[1320px] table-fixed divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th
                                                className="px-6 py-3 w-32 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestRecommendationSort('recommendation_code')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Recommendation
                                                    {getRecommendationSortIcon('recommendation_code')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-56 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestRecommendationSort('title')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Title
                                                    {getRecommendationSortIcon('title')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-44 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestRecommendationSort('model.model_name')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Model
                                                    {getRecommendationSortIcon('model.model_name')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-24 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestRecommendationSort('priority.label')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Priority
                                                    {getRecommendationSortIcon('priority.label')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-36 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestRecommendationSort('current_status.label')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Status
                                                    {getRecommendationSortIcon('current_status.label')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-48 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestRecommendationSort('action_description')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Action Required
                                                    {getRecommendationSortIcon('action_description')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-28 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestRecommendationSort('current_target_date')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Target Date
                                                    {getRecommendationSortIcon('current_target_date')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-28 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestRecommendationSort('days_until_due')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Due In
                                                    {getRecommendationSortIcon('days_until_due')}
                                                </div>
                                            </th>
                                            <th className="px-6 py-3 w-32 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {sortedRecommendationApprovals.map((task) => (
                                            <tr key={task.recommendation_id} className="hover:bg-gray-50">
                                                <td className="px-6 py-4 w-32 whitespace-nowrap text-sm font-mono">
                                                    <Link
                                                        to={`/recommendations/${task.recommendation_id}`}
                                                        className="text-blue-600 hover:text-blue-800"
                                                    >
                                                        {task.recommendation_code}
                                                    </Link>
                                                </td>
                                                <td className="px-6 py-4 w-56 whitespace-normal break-words text-sm">
                                                    {task.title}
                                                </td>
                                                <td className="px-6 py-4 w-44 whitespace-nowrap">
                                                    <Link
                                                        to={`/models/${task.model.model_id}`}
                                                        className="font-medium text-blue-600 hover:text-blue-800 block truncate"
                                                    >
                                                        {task.model.model_name}
                                                    </Link>
                                                </td>
                                                <td className="px-6 py-4 w-24 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(task.priority?.label || task.priority?.code || '')}`}>
                                                        {task.priority?.label || task.priority?.code}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 w-36 whitespace-normal text-sm">
                                                    {task.current_status?.label || task.current_status?.code}
                                                </td>
                                                <td className="px-6 py-4 w-48 whitespace-normal break-words text-sm">
                                                    {task.action_description}
                                                </td>
                                                <td className="px-6 py-4 w-28 whitespace-nowrap text-sm">
                                                    {formatDate(task.current_target_date)}
                                                </td>
                                                <td className="px-6 py-4 w-28 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getDueStatusColor(task.days_until_due)}`}>
                                                        {getDueLabel(task.days_until_due)}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 w-32 whitespace-nowrap">
                                                    <Link
                                                        to={`/recommendations/${task.recommendation_id}`}
                                                        className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                                    >
                                                        Review &amp; Approve
                                                    </Link>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </>
            )}

            {activeTab === 'monitoring' && (
                <>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
                        <button
                            type="button"
                            aria-pressed={monitoringFilterMode === 'all'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                                monitoringFilterMode === 'all' ? 'ring-2 ring-blue-500' : ''
                            }`}
                            onClick={() => setMonitoringFilterMode('all')}
                        >
                            <div className="text-sm text-gray-500">Awaiting Your Approval</div>
                            <div className="text-2xl font-bold text-blue-600">{monitoringApprovals.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={monitoringFilterMode === 'global'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                                monitoringFilterMode === 'global' ? 'ring-2 ring-indigo-500' : ''
                            }`}
                            onClick={() => setMonitoringFilterMode(monitoringFilterMode === 'global' ? 'all' : 'global')}
                        >
                            <div className="text-sm text-gray-500">Global Approvals</div>
                            <div className="text-2xl font-bold text-indigo-600">{monitoringGlobalApprovals.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={monitoringFilterMode === 'regional'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 ${
                                monitoringFilterMode === 'regional' ? 'ring-2 ring-purple-500' : ''
                            }`}
                            onClick={() => setMonitoringFilterMode(monitoringFilterMode === 'regional' ? 'all' : 'regional')}
                        >
                            <div className="text-sm text-gray-500">Regional Approvals</div>
                            <div className="text-2xl font-bold text-purple-600">{monitoringRegionalApprovals.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={monitoringFilterMode === 'overdue'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 ${
                                monitoringFilterMode === 'overdue' ? 'ring-2 ring-rose-500' : ''
                            }`}
                            onClick={() => setMonitoringFilterMode(monitoringFilterMode === 'overdue' ? 'all' : 'overdue')}
                        >
                            <div className="text-sm text-gray-500">Overdue (7+ days)</div>
                            <div className="text-2xl font-bold text-rose-600">{monitoringOverdue.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={monitoringFilterMode === 'needs_attention'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 ${
                                monitoringFilterMode === 'needs_attention' ? 'ring-2 ring-yellow-500' : ''
                            }`}
                            onClick={() => setMonitoringFilterMode(monitoringFilterMode === 'needs_attention' ? 'all' : 'needs_attention')}
                        >
                            <div className="text-sm text-gray-500">Needs Attention (3-6 days)</div>
                            <div className="text-2xl font-bold text-yellow-600">{monitoringNeedsAttention.length}</div>
                        </button>
                        <button
                            type="button"
                            aria-pressed={monitoringFilterMode === 'new'}
                            className={`w-full text-left bg-white p-4 rounded-lg shadow cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 ${
                                monitoringFilterMode === 'new' ? 'ring-2 ring-green-500' : ''
                            }`}
                            onClick={() => setMonitoringFilterMode(monitoringFilterMode === 'new' ? 'all' : 'new')}
                        >
                            <div className="text-sm text-gray-500">New (&lt;3 days)</div>
                            <div className="text-2xl font-bold text-green-600">{monitoringNew.length}</div>
                        </button>
                    </div>

                    {monitoringHasActiveFilter && (
                        <div className="mb-4 flex flex-wrap items-center gap-3">
                            <span className="text-sm text-gray-600">
                                Showing: <strong>{monitoringFilterLabel}</strong> approvals
                            </span>
                            <button
                                onClick={() => setMonitoringFilterMode('all')}
                                className="btn-secondary text-sm"
                            >
                                Clear filters
                            </button>
                        </div>
                    )}

                    <div id="approval-queue" className="bg-white rounded-lg shadow-md">
                        <div className="p-4 border-b bg-blue-50 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                            <div>
                                <h3 className="text-lg font-bold">Monitoring Approval Queue</h3>
                                <p className="text-sm text-gray-600">
                                    {filteredMonitoringApprovals.length} of {monitoringApprovals.length} approvals
                                    {monitoringHasActiveFilter ? ` • ${monitoringFilterLabel}` : ''}
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={exportMonitoringCsv}
                                className={`btn-secondary text-sm ${sortedMonitoringApprovals.length === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}
                                disabled={sortedMonitoringApprovals.length === 0}
                            >
                                Export CSV
                            </button>
                        </div>
                        {monitoringApprovals.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                <p className="text-lg font-medium">All caught up!</p>
                                <p className="text-sm">You have no pending monitoring approvals at this time.</p>
                            </div>
                        ) : filteredMonitoringApprovals.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                <p className="text-lg font-medium">No approvals found.</p>
                                <p className="text-sm">Try clearing the filter or select a different segment.</p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full min-w-[1040px] table-fixed divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th
                                                className="px-6 py-3 w-52 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestMonitoringSort('plan_name')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Plan
                                                    {getMonitoringSortIcon('plan_name')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-48 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestMonitoringSort('period_start_date')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Cycle Period
                                                    {getMonitoringSortIcon('period_start_date')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-28 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestMonitoringSort('approval_type')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Approval Type
                                                    {getMonitoringSortIcon('approval_type')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-36 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestMonitoringSort('region.region_name')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Region
                                                    {getMonitoringSortIcon('region.region_name')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-28 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestMonitoringSort('days_pending')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Days Pending
                                                    {getMonitoringSortIcon('days_pending')}
                                                </div>
                                            </th>
                                            <th
                                                className="px-6 py-3 w-32 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => requestMonitoringSort('report_due_date')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Report Due Date
                                                    {getMonitoringSortIcon('report_due_date')}
                                                </div>
                                            </th>
                                            <th className="px-6 py-3 w-32 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {sortedMonitoringApprovals.map((approval) => (
                                            <tr key={approval.approval_id} className="hover:bg-gray-50">
                                                <td className="px-6 py-4 w-52 whitespace-normal break-words text-sm">
                                                    {approval.plan_name}
                                                </td>
                                                <td className="px-6 py-4 w-48 whitespace-nowrap text-sm">
                                                    {formatPeriod(approval.period_start_date, approval.period_end_date)}
                                                </td>
                                                <td className="px-6 py-4 w-28 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs rounded ${getApprovalTypeColor(approval.approval_type)}`}>
                                                        {approval.approval_type}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 w-36 whitespace-nowrap text-sm">
                                                    {approval.region?.region_name || '-'}
                                                </td>
                                                <td className="px-6 py-4 w-28 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getUrgencyColor(approval.days_pending)}`}>
                                                        {approval.days_pending} days
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 w-32 whitespace-nowrap text-sm">
                                                    {formatDate(approval.report_due_date)}
                                                </td>
                                                <td className="px-6 py-4 w-32 whitespace-nowrap">
                                                    <Link
                                                        to={`/monitoring/cycles/${approval.cycle_id}`}
                                                        className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                                    >
                                                        {approval.can_approve ? 'Review & Approve' : 'View Cycle'}
                                                    </Link>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </>
            )}

            <div className="mt-6 bg-white rounded-lg shadow-md p-4">
                <h3 className="text-lg font-bold mb-3">Quick Actions</h3>
                <div className="flex flex-wrap gap-4">
                    <button
                        onClick={() => {
                            document.getElementById('approval-queue')?.scrollIntoView({ behavior: 'smooth' });
                        }}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    >
                        Go to Approval Queue
                    </button>
                    {activeTab === 'validation' && (
                        <Link
                            to="/validation-workflow"
                            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                        >
                            Open Validation Workflow
                        </Link>
                    )}
                    {activeTab === 'recommendations' && (
                        <Link
                            to="/recommendations"
                            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                        >
                            Open Recommendations
                        </Link>
                    )}
                    {activeTab === 'monitoring' && (
                        <Link
                            to="/my-monitoring"
                            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                        >
                            Open Monitoring Tasks
                        </Link>
                    )}
                    <button
                        onClick={fetchDashboardData}
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                    >
                        Refresh
                    </button>
                </div>
            </div>
        </Layout>
    );
}

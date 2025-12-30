import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api/client';
import FilterStatusBar from './FilterStatusBar';
import StatFilterCard from './StatFilterCard';

interface CycleSummary {
    cycle_id: number;
    plan_id: number;
    plan_name: string;
    period_label: string;
    period_start_date: string;
    period_end_date: string;
    due_date: string;
    status: string;
    days_overdue: number;  // Positive if overdue, negative if days remaining
    priority: string;  // "overdue", "pending_approval", "approaching", "normal"
    team_name: string | null;
    data_provider_name: string | null;
    approval_progress: string | null;  // e.g., "1/2"
    report_url: string | null;
    result_count: number;
    green_count: number;
    yellow_count: number;
    red_count: number;
}

interface OverviewSummary {
    overdue_count: number;
    pending_approval_count: number;
    in_progress_count: number;
    completed_last_30_days: number;
}

interface AdminOverviewData {
    summary: OverviewSummary;
    cycles: CycleSummary[];
}

type StatusFilter = 'all' | 'overdue' | 'pending_approval' | 'in_progress';

export default function AdminMonitoringOverview() {
    const [data, setData] = useState<AdminOverviewData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
    const [downloadingReportId, setDownloadingReportId] = useState<number | null>(null);
    const [searchParams] = useSearchParams();

    useEffect(() => {
        fetchOverview();
    }, []);

    useEffect(() => {
        const statusParam = searchParams.get('status');
        if (statusParam === 'overdue' || statusParam === 'pending_approval' || statusParam === 'in_progress') {
            setStatusFilter(statusParam);
        }
    }, [searchParams]);

    const fetchOverview = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get('/monitoring/admin-overview');
            setData(response.data);
        } catch (err: any) {
            console.error('Failed to fetch admin overview:', err);
            setError(err.response?.data?.detail || 'Failed to load monitoring overview');
        } finally {
            setLoading(false);
        }
    };

    const getPriorityIndicator = (priority: string) => {
        switch (priority) {
            case 'overdue':
                return { color: 'bg-red-500', label: 'Overdue' };
            case 'pending_approval':
                return { color: 'bg-yellow-400', label: 'Pending Approval' };
            case 'approaching':
                return { color: 'bg-orange-400', label: 'Approaching' };
            default:
                return { color: 'bg-gray-300', label: 'Normal' };
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'PENDING':
                return 'bg-gray-100 text-gray-800';
            case 'DATA_COLLECTION':
                return 'bg-blue-100 text-blue-800';
            case 'ON_HOLD':
                return 'bg-orange-100 text-orange-800';
            case 'UNDER_REVIEW':
                return 'bg-yellow-100 text-yellow-800';
            case 'PENDING_APPROVAL':
                return 'bg-orange-100 text-orange-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'PENDING':
                return 'Pending';
            case 'DATA_COLLECTION':
                return 'Data Collection';
            case 'ON_HOLD':
                return 'On Hold';
            case 'UNDER_REVIEW':
                return 'Under Review';
            case 'PENDING_APPROVAL':
                return 'Pending Approval';
            default:
                return status;
        }
    };

    const getFilteredCycles = () => {
        if (!data) return [];

        switch (statusFilter) {
            case 'overdue':
                return data.cycles.filter(c => c.priority === 'overdue');
            case 'pending_approval':
                return data.cycles.filter(c => c.status === 'PENDING_APPROVAL');
            case 'in_progress':
                return data.cycles.filter(c =>
                    c.status === 'DATA_COLLECTION' || c.status === 'UNDER_REVIEW' || c.status === 'ON_HOLD'
                );
            default:
                return data.cycles;
        }
    };

    const filteredCycles = getFilteredCycles();
    const activeFilterLabel = statusFilter === 'overdue'
        ? 'Overdue'
        : statusFilter === 'pending_approval'
            ? 'Pending Approval'
            : statusFilter === 'in_progress'
                ? 'In Progress'
                : '';

    const exportCSV = () => {
        if (!data) return;

        const headers = [
            'Priority', 'Plan Name', 'Period', 'Status', 'Due Date',
            'Days Overdue', 'Team', 'Data Provider', 'Approval Progress',
            'Results', 'Green', 'Yellow', 'Red'
        ];

        const rows = filteredCycles.map(c => [
            c.priority,
            c.plan_name,
            c.period_label,
            c.status,
            c.due_date,
            c.days_overdue,
            c.team_name || '',
            c.data_provider_name || '',
            c.approval_progress || '',
            c.result_count,
            c.green_count,
            c.yellow_count,
            c.red_count,
        ]);

        const csvContent = [headers, ...rows]
            .map(row => row.map(cell => `"${cell}"`).join(','))
            .join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `monitoring_overview_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const getFilenameFromDisposition = (disposition?: string) => {
        if (!disposition) return null;
        const match = disposition.match(/filename="?([^"]+)"?/i);
        return match ? match[1] : null;
    };

    const handleDownloadReport = async (cycle: CycleSummary) => {
        try {
            setDownloadingReportId(cycle.cycle_id);
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
            setDownloadingReportId(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">Loading monitoring overview...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                <p className="text-red-800">{error}</p>
                <button
                    onClick={fetchOverview}
                    className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                >
                    Retry
                </button>
            </div>
        );
    }

    if (!data) return null;

    return (
        <div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
                <StatFilterCard
                    label="Total Active Cycles"
                    count={data.cycles.length}
                    isActive={statusFilter === 'all'}
                    onClick={() => setStatusFilter('all')}
                    colorScheme="blue"
                />
                <StatFilterCard
                    label="Overdue Cycles"
                    count={data.summary.overdue_count}
                    isActive={statusFilter === 'overdue'}
                    onClick={() => setStatusFilter(prev => (prev === 'overdue' ? 'all' : 'overdue'))}
                    colorScheme="red"
                />
                <StatFilterCard
                    label="Pending Approval"
                    count={data.summary.pending_approval_count}
                    isActive={statusFilter === 'pending_approval'}
                    onClick={() => setStatusFilter(prev => (prev === 'pending_approval' ? 'all' : 'pending_approval'))}
                    colorScheme="yellow"
                />
                <StatFilterCard
                    label="In Progress"
                    count={data.summary.in_progress_count}
                    isActive={statusFilter === 'in_progress'}
                    onClick={() => setStatusFilter(prev => (prev === 'in_progress' ? 'all' : 'in_progress'))}
                    colorScheme="green"
                />
                <StatFilterCard
                    label="Completed (30d)"
                    count={data.summary.completed_last_30_days}
                    isActive={false}
                    onClick={() => {}}
                    colorScheme="gray"
                    disabled
                />
            </div>

            {statusFilter !== 'all' && (
                <FilterStatusBar
                    activeFilterLabel={activeFilterLabel}
                    onClear={() => setStatusFilter('all')}
                    entityName="cycles"
                />
            )}

            {/* Filters and Export */}
            <div className="flex flex-wrap justify-end items-center gap-2 mb-4">
                <button
                    onClick={fetchOverview}
                    className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-700 hover:bg-gray-50"
                >
                    Refresh
                </button>
                <button
                    onClick={exportCSV}
                    className="px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                >
                    Export CSV
                </button>
            </div>

            {/* Cycles Table */}
            {filteredCycles.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md p-8 text-center">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="mt-2 text-lg font-medium text-gray-900">No Active Cycles</h3>
                    <p className="mt-1 text-sm text-gray-500">
                        {statusFilter === 'all'
                            ? 'There are no active monitoring cycles at this time.'
                            : `No cycles match the selected filter.`
                        }
                    </p>
                </div>
            ) : (
                <div className="bg-white rounded-lg shadow-md overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Priority
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Plan
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Period
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Status
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Due Date
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Team
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Results
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {filteredCycles.map((cycle) => {
                                const priorityIndicator = getPriorityIndicator(cycle.priority);
                                return (
                                    <tr
                                        key={cycle.cycle_id}
                                        className={`hover:bg-gray-50 ${
                                            cycle.priority === 'overdue' ? 'bg-red-50' : ''
                                        }`}
                                    >
                                        <td className="px-4 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-2">
                                                <span
                                                    className={`inline-block w-3 h-3 rounded-full ${priorityIndicator.color}`}
                                                    title={priorityIndicator.label}
                                                ></span>
                                                <span className="text-xs text-gray-500">{priorityIndicator.label}</span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-4">
                                            <Link
                                                to={`/monitoring/${cycle.plan_id}`}
                                                className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                            >
                                                {cycle.plan_name}
                                            </Link>
                                            {cycle.data_provider_name && (
                                                <div className="text-xs text-gray-500 mt-0.5">
                                                    Provider: {cycle.data_provider_name}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {cycle.period_label}
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${getStatusBadge(cycle.status)}`}>
                                                {getStatusLabel(cycle.status)}
                                            </span>
                                            {cycle.approval_progress && (
                                                <div className="text-xs text-gray-500 mt-1">
                                                    {cycle.approval_progress} approved
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap">
                                            <div className="text-sm text-gray-900">
                                                {cycle.due_date.split('T')[0]}
                                            </div>
                                            <div className={`text-xs font-medium ${
                                                cycle.days_overdue > 0 ? 'text-red-600' :
                                                cycle.days_overdue >= -7 ? 'text-orange-600' :
                                                cycle.days_overdue >= -14 ? 'text-yellow-600' :
                                                'text-gray-500'
                                            }`}>
                                                {cycle.days_overdue > 0
                                                    ? `${cycle.days_overdue}d overdue`
                                                    : `${Math.abs(cycle.days_overdue)}d remaining`
                                                }
                                            </div>
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-600">
                                            {cycle.team_name || '-'}
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap">
                                            {cycle.result_count > 0 ? (
                                                <div className="flex items-center gap-1">
                                                    <span className="text-sm text-gray-600">{cycle.result_count}</span>
                                                    {(cycle.green_count > 0 || cycle.yellow_count > 0 || cycle.red_count > 0) && (
                                                        <div className="flex gap-0.5 ml-1">
                                                            {cycle.green_count > 0 && (
                                                                <span className="inline-block w-3 h-3 bg-green-500 rounded-full" title={`${cycle.green_count} Green`}></span>
                                                            )}
                                                            {cycle.yellow_count > 0 && (
                                                                <span className="inline-block w-3 h-3 bg-yellow-400 rounded-full" title={`${cycle.yellow_count} Yellow`}></span>
                                                            )}
                                                            {cycle.red_count > 0 && (
                                                                <span className="inline-block w-3 h-3 bg-red-500 rounded-full" title={`${cycle.red_count} Red`}></span>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            ) : (
                                                <span className="text-sm text-gray-400">-</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/monitoring/${cycle.plan_id}?cycle=${cycle.cycle_id}`}
                                                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200"
                                            >
                                                View
                                            </Link>
                                            {(cycle.status === 'PENDING_APPROVAL' || cycle.status === 'APPROVED') && (
                                                <button
                                                    type="button"
                                                    onClick={() => handleDownloadReport(cycle)}
                                                    disabled={downloadingReportId === cycle.cycle_id}
                                                    className="ml-2 inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                                                    title="Download Report PDF"
                                                >
                                                    {downloadingReportId === cycle.cycle_id ? 'Downloading...' : 'Report'}
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>

                    {/* Summary Footer */}
                    <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
                        <div className="text-sm text-gray-600">
                            Showing <span className="font-medium">{filteredCycles.length}</span> of{' '}
                            <span className="font-medium">{data.cycles.length}</span> active cycles
                            {statusFilter !== 'all' && (
                                <button
                                    onClick={() => setStatusFilter('all')}
                                    className="ml-2 text-blue-600 hover:text-blue-800"
                                >
                                    (Clear filter)
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Legend */}
            <div className="mt-6 bg-white border border-gray-200 rounded-lg shadow-sm p-4">
                <h4 className="text-xs font-medium text-gray-500 uppercase mb-3">Priority Legend</h4>
                <div className="flex flex-wrap items-center gap-6 text-sm">
                    <div className="flex items-center gap-2">
                        <span className="inline-block w-3 h-3 rounded-full bg-red-500"></span>
                        <span className="text-gray-700"><span className="font-medium">Overdue</span> - Past due date</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="inline-block w-3 h-3 rounded-full bg-yellow-400"></span>
                        <span className="text-gray-700"><span className="font-medium">Pending Approval</span> - Awaiting sign-off</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="inline-block w-3 h-3 rounded-full bg-orange-400"></span>
                        <span className="text-gray-700"><span className="font-medium">Approaching</span> - Due within 14 days</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="inline-block w-3 h-3 rounded-full bg-gray-300"></span>
                        <span className="text-gray-700"><span className="font-medium">Normal</span> - On track</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

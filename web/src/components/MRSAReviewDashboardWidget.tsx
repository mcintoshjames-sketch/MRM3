import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import FilterStatusBar from './FilterStatusBar';
import { useTableSort } from '../hooks/useTableSort';
import MRSAReviewStatusBadge, { MRSAReviewStatusCode } from './MRSAReviewStatusBadge';
import StatFilterCard from './StatFilterCard';

interface MRSAReviewOwner {
    user_id: number;
    full_name: string;
    email: string;
}

interface MRSAReviewStatus {
    mrsa_id: number;
    mrsa_name: string;
    risk_level: string | null;
    last_review_date: string | null;
    next_due_date: string | null;
    status: MRSAReviewStatusCode;
    days_until_due: number | null;
    owner: MRSAReviewOwner | null;
    has_exception: boolean;
    exception_due_date: string | null;
}

type StatusFilter = 'attention' | 'upcoming' | 'current' | 'all';

interface MRSAReviewDashboardWidgetProps {
    title?: string;
    description?: string;
    ownerId?: number;
    showOwnerColumn?: boolean;
    showPolicyLink?: boolean;
    className?: string;
}

const ATTENTION_STATUSES: MRSAReviewStatusCode[] = [
    'OVERDUE',
    'NO_IRP',
    'NEVER_REVIEWED'
];

const formatDate = (value: string | null | undefined) => {
    if (!value) return '-';
    return value.split('T')[0];
};

const formatDays = (days: number | null) => {
    if (days === null || days === undefined) return '-';
    if (days < 0) return `${Math.abs(days)}d overdue`;
    if (days === 0) return 'Due today';
    return `${days}d remaining`;
};

export default function MRSAReviewDashboardWidget({
    title = 'MRSA Review Status',
    description = 'Track upcoming and overdue independent reviews for MRSAs.',
    ownerId,
    showOwnerColumn,
    showPolicyLink = false,
    className = ''
}: MRSAReviewDashboardWidgetProps) {
    const [data, setData] = useState<MRSAReviewStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

    const shouldShowOwnerColumn = showOwnerColumn ?? ownerId === undefined;

    const fetchStatuses = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get('/irps/mrsa-review-status');
            setData(response.data);
        } catch (err: any) {
            console.error('Failed to fetch MRSA review status:', err);
            setError(err.response?.data?.detail || 'Failed to load MRSA review status');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatuses();
    }, []);

    const scopedData = useMemo(() => {
        if (!ownerId) return data;
        return data.filter((item) => item.owner?.user_id === ownerId);
    }, [data, ownerId]);

    const summary = useMemo(() => {
        const counts = {
            current: 0,
            upcoming: 0,
            overdue: 0,
            noIrp: 0,
            neverReviewed: 0,
            noRequirement: 0
        };

        scopedData.forEach((item) => {
            switch (item.status) {
                case 'CURRENT':
                    counts.current += 1;
                    break;
                case 'UPCOMING':
                    counts.upcoming += 1;
                    break;
                case 'OVERDUE':
                    counts.overdue += 1;
                    break;
                case 'NO_IRP':
                    counts.noIrp += 1;
                    break;
                case 'NEVER_REVIEWED':
                    counts.neverReviewed += 1;
                    break;
                case 'NO_REQUIREMENT':
                    counts.noRequirement += 1;
                    break;
                default:
                    break;
            }
        });

        return counts;
    }, [scopedData]);

    const filteredData = useMemo(() => {
        if (statusFilter === 'all') return scopedData;
        if (statusFilter === 'upcoming') {
            return scopedData.filter((item) => item.status === 'UPCOMING');
        }
        if (statusFilter === 'current') {
            return scopedData.filter((item) => item.status === 'CURRENT');
        }
        return scopedData.filter((item) => ATTENTION_STATUSES.includes(item.status));
    }, [scopedData, statusFilter]);

    const { sortedData, requestSort, getSortIcon } = useTableSort<MRSAReviewStatus>(filteredData, 'days_until_due');

    const exportToCsv = () => {
        const headers = [
            'MRSA ID',
            'MRSA Name',
            'Risk Level',
            'Status',
            'Last Review',
            'Next Due',
            'Days Until Due'
        ];

        if (shouldShowOwnerColumn) {
            headers.push('Owner');
        }

        headers.push('Has Exception');

        const rows = sortedData.map((item) => {
            const base = [
                item.mrsa_id,
                item.mrsa_name,
                item.risk_level || '',
                item.status,
                formatDate(item.last_review_date),
                formatDate(item.next_due_date),
                item.days_until_due ?? ''
            ];

            if (shouldShowOwnerColumn) {
                base.push(item.owner?.full_name || '');
            }

            base.push(item.has_exception ? 'Yes' : 'No');
            return base;
        });

        const csvContent = [headers, ...rows]
            .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
            .join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `mrsa_review_status_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        link.parentNode?.removeChild(link);
        URL.revokeObjectURL(url);
    };

    if (loading) {
        return (
            <div className={`bg-gray-50 border border-gray-200 p-4 rounded-lg shadow-sm ${className}`}>
                <div className="flex items-center justify-center h-40">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span className="ml-3 text-gray-600">Loading MRSA review status...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className={`bg-gray-50 border border-gray-200 p-4 rounded-lg shadow-sm ${className}`}>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                    <p className="text-red-800">{error}</p>
                    <button
                        onClick={fetchStatuses}
                        className="mt-3 px-3 py-1.5 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className={`bg-gray-50 border border-gray-200 p-4 rounded-lg shadow-sm ${className}`}>
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3 mb-4">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
                    <p className="text-sm text-gray-600">{description}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    {showPolicyLink && (
                        <Link
                            to="/mrsa-review-policies"
                            className="px-3 py-1.5 text-xs border border-blue-200 text-blue-700 rounded hover:bg-blue-50"
                        >
                            Manage Policies
                        </Link>
                    )}
                    <Link
                        to="/models"
                        className="px-3 py-1.5 text-xs border border-gray-200 text-gray-700 rounded hover:bg-gray-50"
                    >
                        View Models
                    </Link>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                <StatFilterCard
                    label="Needs Attention"
                    count={summary.overdue + summary.noIrp + summary.neverReviewed}
                    isActive={statusFilter === 'attention'}
                    onClick={() => setStatusFilter(prev => (prev === 'attention' ? 'all' : 'attention'))}
                    colorScheme="red"
                />
                <StatFilterCard
                    label="Upcoming"
                    count={summary.upcoming}
                    isActive={statusFilter === 'upcoming'}
                    onClick={() => setStatusFilter(prev => (prev === 'upcoming' ? 'all' : 'upcoming'))}
                    colorScheme="yellow"
                />
                <StatFilterCard
                    label="Current"
                    count={summary.current}
                    isActive={statusFilter === 'current'}
                    onClick={() => setStatusFilter(prev => (prev === 'current' ? 'all' : 'current'))}
                    colorScheme="green"
                />
                <StatFilterCard
                    label="Total MRSAs"
                    count={scopedData.length}
                    isActive={statusFilter === 'all'}
                    onClick={() => setStatusFilter('all')}
                    colorScheme="blue"
                />
            </div>

            {statusFilter !== 'all' && (
                <FilterStatusBar
                    activeFilterLabel={statusFilter === 'attention'
                        ? 'Needs Attention'
                        : statusFilter === 'upcoming'
                            ? 'Upcoming'
                            : 'Current'}
                    onClear={() => setStatusFilter('all')}
                    entityName="MRSAs"
                />
            )}

            <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600 mb-4">
                <div>
                    <span className="font-semibold text-gray-800">{summary.overdue}</span> overdue
                </div>
                <div>
                    <span className="font-semibold text-gray-800">{summary.noIrp}</span> no IRP
                </div>
                <div>
                    <span className="font-semibold text-gray-800">{summary.neverReviewed}</span> never reviewed
                </div>
                <div>
                    <span className="font-semibold text-gray-800">{summary.noRequirement}</span> no requirement
                </div>
            </div>

            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-3">
                <div className="text-sm text-gray-500">
                    Showing {sortedData.length} of {scopedData.length} MRSAs
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={fetchStatuses}
                        className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-700 hover:bg-gray-50"
                    >
                        Refresh
                    </button>
                    <button
                        onClick={exportToCsv}
                        className="px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                    >
                        Export CSV
                    </button>
                </div>
            </div>

            {sortedData.length === 0 ? (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center text-sm text-gray-600">
                    No MRSAs match the selected filter.
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                    onClick={() => requestSort('mrsa_name')}
                                >
                                    <div className="flex items-center gap-2">
                                        MRSA
                                        {getSortIcon('mrsa_name')}
                                    </div>
                                </th>
                                <th
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                    onClick={() => requestSort('risk_level')}
                                >
                                    <div className="flex items-center gap-2">
                                        Risk Level
                                        {getSortIcon('risk_level')}
                                    </div>
                                </th>
                                <th
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                    onClick={() => requestSort('status')}
                                >
                                    <div className="flex items-center gap-2">
                                        Status
                                        {getSortIcon('status')}
                                    </div>
                                </th>
                                <th
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                    onClick={() => requestSort('last_review_date')}
                                >
                                    <div className="flex items-center gap-2">
                                        Last Review
                                        {getSortIcon('last_review_date')}
                                    </div>
                                </th>
                                <th
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                    onClick={() => requestSort('next_due_date')}
                                >
                                    <div className="flex items-center gap-2">
                                        Next Due
                                        {getSortIcon('next_due_date')}
                                    </div>
                                </th>
                                <th
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                    onClick={() => requestSort('days_until_due')}
                                >
                                    <div className="flex items-center gap-2">
                                        Days Until Due
                                        {getSortIcon('days_until_due')}
                                    </div>
                                </th>
                                {shouldShowOwnerColumn && (
                                    <th
                                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('owner.full_name')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Owner
                                            {getSortIcon('owner.full_name')}
                                        </div>
                                    </th>
                                )}
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {sortedData.map((item) => (
                                <tr key={item.mrsa_id} className="hover:bg-gray-50">
                                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                                        <Link
                                            to={`/models/${item.mrsa_id}`}
                                            className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                        >
                                            {item.mrsa_name}
                                        </Link>
                                        {item.has_exception && (
                                            <div className="text-xs text-purple-600 mt-1">Exception override</div>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                                        {item.risk_level || '-'}
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                                        <MRSAReviewStatusBadge status={item.status} />
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                                        {formatDate(item.last_review_date)}
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                                        {formatDate(item.next_due_date)}
                                        {item.has_exception && item.exception_due_date && (
                                            <div className="text-xs text-purple-600 mt-1">
                                                Exception: {formatDate(item.exception_due_date)}
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                                        {formatDays(item.days_until_due)}
                                    </td>
                                    {shouldShowOwnerColumn && (
                                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                                            {item.owner ? (
                                                <Link
                                                    to={`/users/${item.owner.user_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline"
                                                >
                                                    {item.owner.full_name}
                                                </Link>
                                            ) : (
                                                '-'
                                            )}
                                        </td>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

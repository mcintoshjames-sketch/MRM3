import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import client from '../api/client';
import OverdueCommentaryModal, { OverdueType } from '../components/OverdueCommentaryModal';

interface RegionInfo {
    region_id: number;
    region_code: string;
    region_name: string;
}

interface OverdueRevalidationRecord {
    overdue_type: 'PRE_SUBMISSION' | 'VALIDATION_IN_PROGRESS';
    request_id: number;
    validation_type: string | null;
    model_id: number;
    model_name: string;
    risk_tier: string | null;
    risk_tier_code: string | null;
    regions: RegionInfo[];
    model_owner_id: number | null;
    model_owner_name: string | null;
    model_owner_email: string | null;
    model_developer_name: string | null;
    primary_validator_id: number | null;
    primary_validator_name: string | null;
    primary_validator_email: string | null;
    due_date: string | null;
    grace_period_end: string | null;
    days_overdue: number;
    urgency: string;
    current_status: string;
    current_status_code: string | null;
    comment_status: 'CURRENT' | 'STALE' | 'MISSING';
    latest_comment: string | null;
    latest_comment_date: string | null;
    latest_comment_by: string | null;
    target_date_from_comment: string | null;
    stale_reason: string | null;
    needs_comment_update: boolean;
    computed_completion_date: string | null;
}

interface EnhancedSummary {
    total_overdue: number;
    pre_submission_overdue: number;
    validation_overdue: number;
    missing_commentary: number;
    stale_commentary: number;
    current_commentary: number;
    needs_attention: number;
    average_days_overdue: number;
    median_days_overdue: number;
    max_days_overdue: number;
    overdue_30_plus_days: number;
    overdue_60_plus_days: number;
    overdue_90_plus_days: number;
    by_risk_tier: Record<string, number>;
    by_region: Record<string, number>;
    risk_weighted_overdue_score: number;
}

interface DataLimitation {
    metric_name: string;
    reason: string;
    remediation: string;
}

interface OverdueRevalidationReportResponse {
    report_generated_at: string;
    filters_applied: {
        overdue_type: string | null;
        risk_tier: string | null;
        region_id: number | null;
        region_name: string | null;
        comment_status: string | null;
        owner_id: number | null;
        days_overdue_min: number | null;
        needs_update_only: boolean;
    };
    summary: EnhancedSummary;
    total_records: number;
    records: OverdueRevalidationRecord[];
    data_limitations: DataLimitation[];
}

const OverdueRevalidationReportPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [reportData, setReportData] = useState<OverdueRevalidationReportResponse | null>(null);
    const [regions, setRegions] = useState<RegionInfo[]>([]);

    // Filters
    const [overdueTypeFilter, setOverdueTypeFilter] = useState<string>('');
    const [regionFilter, setRegionFilter] = useState<string>('');
    const [commentStatusFilter, setCommentStatusFilter] = useState<string>('');
    const [needsUpdateOnly, setNeedsUpdateOnly] = useState(false);
    const [daysOverdueMin, setDaysOverdueMin] = useState<string>('');

    // UI State
    const [showDataLimitations, setShowDataLimitations] = useState(false);

    // Commentary modal
    const [showCommentaryModal, setShowCommentaryModal] = useState(false);
    const [commentaryModalRequestId, setCommentaryModalRequestId] = useState<number | null>(null);
    const [commentaryModalType, setCommentaryModalType] = useState<OverdueType>('PRE_SUBMISSION');
    const [commentaryModalModelName, setCommentaryModalModelName] = useState<string>('');

    useEffect(() => {
        fetchRegions();
    }, []);

    useEffect(() => {
        fetchReport();
    }, [overdueTypeFilter, regionFilter, commentStatusFilter, needsUpdateOnly, daysOverdueMin]);

    const fetchRegions = async () => {
        try {
            const response = await client.get('/overdue-revalidation-report/regions');
            setRegions(response.data);
        } catch (error) {
            console.error('Failed to fetch regions:', error);
        }
    };

    const fetchReport = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (overdueTypeFilter) params.append('overdue_type', overdueTypeFilter);
            if (regionFilter) params.append('region_id', regionFilter);
            if (commentStatusFilter) params.append('comment_status', commentStatusFilter);
            if (needsUpdateOnly) params.append('needs_update_only', 'true');
            if (daysOverdueMin) params.append('days_overdue_min', daysOverdueMin);

            const response = await client.get(`/overdue-revalidation-report/?${params.toString()}`);
            setReportData(response.data);
        } catch (error) {
            console.error('Failed to fetch report:', error);
        } finally {
            setLoading(false);
        }
    };

    const openCommentaryModal = (requestId: number, overdueType: OverdueType, modelName: string) => {
        setCommentaryModalRequestId(requestId);
        setCommentaryModalType(overdueType);
        setCommentaryModalModelName(modelName);
        setShowCommentaryModal(true);
    };

    const handleCommentarySuccess = () => {
        fetchReport();
    };

    const getCommentStatusBadge = (status: 'CURRENT' | 'STALE' | 'MISSING') => {
        switch (status) {
            case 'CURRENT':
                return 'bg-green-100 text-green-800';
            case 'STALE':
                return 'bg-yellow-100 text-yellow-800';
            case 'MISSING':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getOverdueTypeBadge = (type: string) => {
        if (type === 'PRE_SUBMISSION') {
            return 'bg-orange-100 text-orange-800';
        }
        return 'bg-red-100 text-red-800';
    };

    const getUrgencyBadge = (urgency: string, daysOverdue: number) => {
        if (urgency === 'in_grace_period') {
            return 'bg-yellow-100 text-yellow-800';
        }
        if (daysOverdue >= 90) {
            return 'bg-red-300 text-red-900';
        }
        if (daysOverdue >= 60) {
            return 'bg-red-200 text-red-900';
        }
        if (daysOverdue >= 30) {
            return 'bg-red-100 text-red-800';
        }
        return 'bg-orange-100 text-orange-800';
    };

    const exportToCsv = () => {
        if (!reportData || reportData.records.length === 0) return;

        const headers = [
            'Overdue Type',
            'Request ID',
            'Model ID',
            'Model Name',
            'Risk Tier',
            'Regions',
            'Owner Name',
            'Owner Email',
            'Primary Validator',
            'Due Date',
            'Days Overdue',
            'Urgency',
            'Current Status',
            'Commentary Status',
            'Latest Comment',
            'Comment Date',
            'Comment By',
            'Target Date',
            'Stale Reason',
            'Needs Update',
            'Computed Completion Date'
        ];

        const rows = reportData.records.map(record => [
            record.overdue_type === 'PRE_SUBMISSION' ? 'Submission' : 'Validation',
            record.request_id,
            record.model_id,
            record.model_name,
            record.risk_tier || 'N/A',
            record.regions.map(r => r.region_code).join('; ') || 'N/A',
            record.model_owner_name || 'N/A',
            record.model_owner_email || 'N/A',
            record.primary_validator_name || 'N/A',
            record.due_date || 'N/A',
            record.days_overdue,
            record.urgency === 'in_grace_period' ? 'In Grace Period' : 'Overdue',
            record.current_status,
            record.comment_status,
            record.latest_comment ? `"${record.latest_comment.replace(/"/g, '""')}"` : 'N/A',
            record.latest_comment_date ? record.latest_comment_date.split('T')[0] : 'N/A',
            record.latest_comment_by || 'N/A',
            record.target_date_from_comment || 'N/A',
            record.stale_reason || 'N/A',
            record.needs_comment_update ? 'Yes' : 'No',
            record.computed_completion_date || 'N/A'
        ]);

        const csvContent = [headers, ...rows]
            .map(row => row.join(','))
            .join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `overdue_revalidation_report_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <Layout>
            <div className="p-6">
                {/* Header */}
                <div className="mb-6">
                    <div className="flex items-center gap-2 mb-2">
                        <Link to="/reports" className="text-blue-600 hover:text-blue-800 text-sm">
                            ← Back to Reports
                        </Link>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900">Overdue Revalidation Report</h2>
                    <p className="mt-1 text-sm text-gray-600">
                        Comprehensive view of all overdue items with commentary status, regional breakdown, and responsible party tracking
                    </p>
                </div>

                {/* Primary Summary Cards */}
                {reportData && (
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-4">
                        <div className="bg-white p-4 rounded-lg shadow-sm border">
                            <div className="text-2xl font-bold text-gray-900">{reportData.summary.total_overdue}</div>
                            <div className="text-xs text-gray-500">Total Overdue</div>
                        </div>
                        <div className="bg-orange-50 p-4 rounded-lg shadow-sm border border-orange-200">
                            <div className="text-2xl font-bold text-orange-700">{reportData.summary.pre_submission_overdue}</div>
                            <div className="text-xs text-orange-600">Submissions</div>
                        </div>
                        <div className="bg-red-50 p-4 rounded-lg shadow-sm border border-red-200">
                            <div className="text-2xl font-bold text-red-700">{reportData.summary.validation_overdue}</div>
                            <div className="text-xs text-red-600">Validations</div>
                        </div>
                        <div className="bg-red-50 p-4 rounded-lg shadow-sm border border-red-200">
                            <div className="text-2xl font-bold text-red-700">{reportData.summary.missing_commentary}</div>
                            <div className="text-xs text-red-600">Missing Commentary</div>
                        </div>
                        <div className="bg-yellow-50 p-4 rounded-lg shadow-sm border border-yellow-200">
                            <div className="text-2xl font-bold text-yellow-700">{reportData.summary.stale_commentary}</div>
                            <div className="text-xs text-yellow-600">Stale Commentary</div>
                        </div>
                        <div className="bg-green-50 p-4 rounded-lg shadow-sm border border-green-200">
                            <div className="text-2xl font-bold text-green-700">{reportData.summary.current_commentary}</div>
                            <div className="text-xs text-green-600">Current Commentary</div>
                        </div>
                    </div>
                )}

                {/* Enhanced Metrics Panel */}
                {reportData && reportData.summary.total_overdue > 0 && (
                    <div className="bg-white p-4 rounded-lg shadow-sm border mb-4">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3">Enhanced Metrics</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                            {/* Severity Buckets */}
                            <div className="bg-gray-50 p-3 rounded">
                                <div className="text-lg font-bold text-gray-700">{reportData.summary.overdue_30_plus_days}</div>
                                <div className="text-xs text-gray-500">30+ Days Overdue</div>
                            </div>
                            <div className="bg-red-50 p-3 rounded">
                                <div className="text-lg font-bold text-red-700">{reportData.summary.overdue_60_plus_days}</div>
                                <div className="text-xs text-red-600">60+ Days Overdue</div>
                            </div>
                            <div className="bg-red-100 p-3 rounded">
                                <div className="text-lg font-bold text-red-800">{reportData.summary.overdue_90_plus_days}</div>
                                <div className="text-xs text-red-700">90+ Days Overdue</div>
                            </div>
                            {/* Statistics */}
                            <div className="bg-blue-50 p-3 rounded">
                                <div className="text-lg font-bold text-blue-700">{reportData.summary.average_days_overdue}</div>
                                <div className="text-xs text-blue-600">Avg Days Overdue</div>
                            </div>
                            <div className="bg-blue-50 p-3 rounded">
                                <div className="text-lg font-bold text-blue-700">{reportData.summary.median_days_overdue}</div>
                                <div className="text-xs text-blue-600">Median Days Overdue</div>
                            </div>
                            <div className="bg-purple-50 p-3 rounded" title="Risk-weighted score: Tier 1 models count 3x, Tier 2 = 2x, Tier 3 = 1x, multiplied by days overdue">
                                <div className="text-lg font-bold text-purple-700">{reportData.summary.risk_weighted_overdue_score.toLocaleString()}</div>
                                <div className="text-xs text-purple-600">Risk-Weighted Score</div>
                            </div>
                        </div>

                        {/* Breakdown by Risk Tier and Region */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            {/* Risk Tier Breakdown */}
                            {Object.keys(reportData.summary.by_risk_tier).length > 0 && (
                                <div>
                                    <h4 className="text-xs font-medium text-gray-500 mb-2">By Risk Tier</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(reportData.summary.by_risk_tier).map(([tier, count]) => (
                                            <span key={tier} className="px-2 py-1 bg-gray-100 rounded text-xs">
                                                {tier}: <strong>{count}</strong>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {/* Region Breakdown */}
                            {Object.keys(reportData.summary.by_region).length > 0 && (
                                <div>
                                    <h4 className="text-xs font-medium text-gray-500 mb-2">By Region</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(reportData.summary.by_region).map(([region, count]) => (
                                            <span key={region} className="px-2 py-1 bg-blue-100 rounded text-xs">
                                                {region}: <strong>{count}</strong>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Filters */}
                <div className="bg-white p-4 rounded-lg shadow-sm border mb-6">
                    <div className="flex flex-wrap items-center gap-4">
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">Overdue Type</label>
                            <select
                                value={overdueTypeFilter}
                                onChange={(e) => setOverdueTypeFilter(e.target.value)}
                                className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                            >
                                <option value="">All Types</option>
                                <option value="PRE_SUBMISSION">Submission Overdue</option>
                                <option value="VALIDATION_IN_PROGRESS">Validation Overdue</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">Region</label>
                            <select
                                value={regionFilter}
                                onChange={(e) => setRegionFilter(e.target.value)}
                                className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                            >
                                <option value="">All Regions</option>
                                {regions.map(region => (
                                    <option key={region.region_id} value={region.region_id}>
                                        {region.region_name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">Commentary Status</label>
                            <select
                                value={commentStatusFilter}
                                onChange={(e) => setCommentStatusFilter(e.target.value)}
                                className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                            >
                                <option value="">All Statuses</option>
                                <option value="MISSING">Missing</option>
                                <option value="STALE">Stale</option>
                                <option value="CURRENT">Current</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">Min Days Overdue</label>
                            <input
                                type="number"
                                value={daysOverdueMin}
                                onChange={(e) => setDaysOverdueMin(e.target.value)}
                                placeholder="0"
                                className="block w-24 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                            />
                        </div>
                        <div className="flex items-end pb-1">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={needsUpdateOnly}
                                    onChange={(e) => setNeedsUpdateOnly(e.target.checked)}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700">Needs Update Only</span>
                            </label>
                        </div>
                        <div className="ml-auto flex gap-2">
                            <button
                                onClick={fetchReport}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                            >
                                Refresh Report
                            </button>
                            <button
                                onClick={exportToCsv}
                                disabled={!reportData || reportData.records.length === 0}
                                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 text-sm"
                            >
                                Export CSV
                            </button>
                        </div>
                    </div>
                </div>

                {/* Results Table */}
                {loading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="text-gray-500">Loading report...</div>
                    </div>
                ) : reportData && reportData.records.length > 0 ? (
                    <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
                        <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
                            <span className="text-sm font-medium text-gray-700">
                                {reportData.total_records} records found
                                {reportData.filters_applied.region_name && (
                                    <span className="ml-2 text-blue-600">
                                        (filtered by: {reportData.filters_applied.region_name})
                                    </span>
                                )}
                            </span>
                            <span className="text-sm text-gray-500">
                                Avg: {reportData.summary.average_days_overdue} days |
                                Median: {reportData.summary.median_days_overdue} days |
                                Max: {reportData.summary.max_days_overdue} days
                            </span>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Regions</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Responsible</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Overdue</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Commentary</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {reportData.records.map((record) => (
                                        <tr
                                            key={`${record.request_id}-${record.overdue_type}`}
                                            className={`hover:bg-gray-50 ${record.needs_comment_update ? 'bg-red-50' : ''}`}
                                        >
                                            <td className="px-4 py-3 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs font-semibold rounded ${getOverdueTypeBadge(record.overdue_type)}`}>
                                                    {record.overdue_type === 'PRE_SUBMISSION' ? 'Submission' : 'Validation'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 whitespace-nowrap">
                                                <Link
                                                    to={`/models/${record.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                                                >
                                                    {record.model_name}
                                                </Link>
                                            </td>
                                            <td className="px-4 py-3 whitespace-nowrap text-sm">
                                                {record.risk_tier || <span className="text-gray-400">-</span>}
                                            </td>
                                            <td className="px-4 py-3 whitespace-nowrap text-sm">
                                                {record.regions.length > 0 ? (
                                                    <div className="flex flex-wrap gap-1">
                                                        {record.regions.map(r => (
                                                            <span key={r.region_id} className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">
                                                                {r.region_code}
                                                            </span>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <span className="text-gray-400">-</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 whitespace-nowrap text-sm">
                                                {record.overdue_type === 'PRE_SUBMISSION' ? (
                                                    <div>
                                                        <div className="font-medium">{record.model_owner_name || 'Unknown'}</div>
                                                        <div className="text-xs text-gray-500">Owner</div>
                                                    </div>
                                                ) : (
                                                    <div>
                                                        <div className="font-medium">{record.primary_validator_name || 'Unassigned'}</div>
                                                        <div className="text-xs text-gray-500">Validator</div>
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 whitespace-nowrap text-sm">
                                                {record.due_date || '-'}
                                            </td>
                                            <td className="px-4 py-3 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs font-semibold rounded ${getUrgencyBadge(record.urgency, record.days_overdue)}`}>
                                                    {record.days_overdue} days
                                                </span>
                                                {record.urgency === 'in_grace_period' && (
                                                    <span className="ml-1 text-xs text-gray-500">(grace)</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-3">
                                                <div className="flex flex-col gap-1">
                                                    {record.comment_status !== 'CURRENT' && (
                                                        <span className={`px-2 py-1 text-xs font-semibold rounded inline-block w-fit ${getCommentStatusBadge(record.comment_status)}`}>
                                                            {record.comment_status}
                                                        </span>
                                                    )}
                                                    {record.latest_comment && (
                                                        <span className="text-xs text-gray-600 max-w-48" title={record.latest_comment}>
                                                            {record.latest_comment.length > 50
                                                                ? `"${record.latest_comment.substring(0, 50)}..."`
                                                                : `"${record.latest_comment}"`}
                                                        </span>
                                                    )}
                                                    {record.stale_reason && (
                                                        <span className="text-xs text-yellow-600">{record.stale_reason}</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 whitespace-nowrap text-sm">
                                                {record.computed_completion_date ? (
                                                    <span className="text-amber-600 font-medium">{record.computed_completion_date}</span>
                                                ) : (
                                                    <span className="text-gray-400">-</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 whitespace-nowrap">
                                                <div className="flex gap-2">
                                                    <Link
                                                        to={`/validation-workflow/${record.request_id}`}
                                                        className="text-blue-600 hover:text-blue-800 text-sm"
                                                    >
                                                        View
                                                    </Link>
                                                    {record.needs_comment_update && (
                                                        <button
                                                            onClick={() => openCommentaryModal(
                                                                record.request_id,
                                                                record.overdue_type,
                                                                record.model_name
                                                            )}
                                                            className="px-2 py-1 text-xs font-medium text-white bg-orange-600 hover:bg-orange-700 rounded"
                                                        >
                                                            Add Commentary
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ) : (
                    <div className="bg-white rounded-lg shadow-sm border p-8 text-center">
                        <div className="text-gray-400 text-lg mb-2">No overdue items found</div>
                        <p className="text-sm text-gray-500">
                            All models are up to date with their revalidation schedules.
                        </p>
                    </div>
                )}

                {/* Data Limitations Section */}
                {reportData && reportData.data_limitations && reportData.data_limitations.length > 0 && (
                    <div className="mt-6">
                        <button
                            onClick={() => setShowDataLimitations(!showDataLimitations)}
                            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800"
                        >
                            <svg
                                className={`w-4 h-4 transform transition-transform ${showDataLimitations ? 'rotate-90' : ''}`}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                            Data Limitations & Recommended Improvements ({reportData.data_limitations.length})
                        </button>

                        {showDataLimitations && (
                            <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-4">
                                <p className="text-sm text-amber-800 mb-3">
                                    The following metrics would be valuable for regulatory reporting but cannot currently be calculated due to data limitations:
                                </p>
                                <div className="space-y-3">
                                    {reportData.data_limitations.map((limitation, index) => (
                                        <div key={index} className="bg-white p-3 rounded border border-amber-100">
                                            <h4 className="font-medium text-gray-900 text-sm">{limitation.metric_name}</h4>
                                            <p className="text-xs text-gray-600 mt-1">
                                                <strong>Current Limitation:</strong> {limitation.reason}
                                            </p>
                                            <p className="text-xs text-green-700 mt-1">
                                                <strong>Recommended Remediation:</strong> {limitation.remediation}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Report Generation Info */}
                {reportData && (
                    <div className="mt-4 text-xs text-gray-500 text-right">
                        Report generated at: {new Date(reportData.report_generated_at).toLocaleString()}
                    </div>
                )}

                {/* Commentary Modal */}
                {showCommentaryModal && commentaryModalRequestId && (
                    <OverdueCommentaryModal
                        requestId={commentaryModalRequestId}
                        overdueType={commentaryModalType}
                        modelName={commentaryModalModelName}
                        onClose={() => {
                            setShowCommentaryModal(false);
                            setCommentaryModalRequestId(null);
                        }}
                        onSuccess={handleCommentarySuccess}
                    />
                )}
            </div>
        </Layout>
    );
};

export default OverdueRevalidationReportPage;

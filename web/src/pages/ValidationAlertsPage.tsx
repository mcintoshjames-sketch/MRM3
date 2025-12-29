import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/client';
import FilterStatusBar from '../components/FilterStatusBar';
import StatFilterCard from '../components/StatFilterCard';

interface SLAViolation {
    request_id: number;
    model_name: string;
    violation_type: string;
    sla_days: number;
    actual_days: number;
    days_overdue: number;
    current_status: string;
    priority: string;
    severity: string;
    timestamp: string;
}

interface OutOfOrderValidation {
    request_id: number;
    model_name?: string;
    model_names?: string[];
    version_number: string;
    validation_type: string;
    target_completion_date: string;
    production_date: string;
    days_gap: number;
    current_status: string;
    priority: string;
    severity: string;
    is_interim: boolean;
}

const getOutOfOrderModelLabel = (item: OutOfOrderValidation) => {
    const primaryName = (item.model_name || '').trim();
    if (primaryName && primaryName !== '-') {
        return primaryName;
    }
    if (item.model_names && item.model_names.length > 0) {
        return item.model_names[0];
    }
    return `Request #${item.request_id}`;
};

type AlertFilter = 'all' | 'lead-time' | 'out-of-order';

const ValidationAlertsPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const tabParam = searchParams.get('tab');
    const initialAlertFilter: AlertFilter = tabParam === 'lead-time'
        ? 'lead-time'
        : tabParam === 'out-of-order'
            ? 'out-of-order'
            : 'all';
    const [slaViolations, setSlaViolations] = useState<SLAViolation[]>([]);
    const [outOfOrder, setOutOfOrder] = useState<OutOfOrderValidation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [alertFilter, setAlertFilter] = useState<AlertFilter>(initialAlertFilter);

    useEffect(() => {
        fetchAlerts();
    }, []);

    const fetchAlerts = async () => {
        try {
            setLoading(true);
            setError(null);
            const [slaRes, outOfOrderRes] = await Promise.all([
                api.get('/validation-workflow/dashboard/sla-violations'),
                api.get('/validation-workflow/dashboard/out-of-order'),
            ]);
            setSlaViolations(slaRes.data);
            const normalizedOutOfOrder = (outOfOrderRes.data || []).map((item: OutOfOrderValidation) => ({
                ...item,
                model_name: getOutOfOrderModelLabel(item),
            }));
            setOutOfOrder(normalizedOutOfOrder);
        } catch (err: any) {
            console.error('Failed to fetch validation alerts:', err);
            setError(err.response?.data?.detail || 'Failed to load validation alerts');
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (value: string | null | undefined) => {
        if (!value) return '-';
        return value.split('T')[0];
    };

    const getSeverityBadge = (severity: string) => {
        switch (severity) {
            case 'critical':
                return 'bg-red-100 text-red-700';
            case 'high':
                return 'bg-orange-100 text-orange-700';
            case 'medium':
                return 'bg-yellow-100 text-yellow-700';
            default:
                return 'bg-gray-100 text-gray-700';
        }
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const exportToCSV = (data: any[], filename: string, columns: { key: string; label: string }[]) => {
        if (data.length === 0) return;
        const headers = columns.map(col => col.label);
        const rows = data.map(item => {
            return columns.map(col => {
                const keys = col.key.split('.');
                let value: unknown = item;
                for (const k of keys) {
                    value = (value as Record<string, unknown>)?.[k];
                }
                const strValue = value != null ? String(value) : '';
                const escaped = strValue.replace(/"/g, '""');
                return escaped.includes(',') || escaped.includes('"') || escaped.includes('\n')
                    ? `"${escaped}"`
                    : escaped;
            }).join(',');
        });

        const csv = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const date = new Date().toISOString().split('T')[0];
        link.setAttribute('download', `${filename}_${date}.csv`);
        document.body.appendChild(link);
        link.click();
        link.parentNode?.removeChild(link);
        window.URL.revokeObjectURL(url);
    };

    const totalAlerts = useMemo(() => slaViolations.length + outOfOrder.length, [slaViolations, outOfOrder]);
    const activeFilterLabel = alertFilter === 'lead-time'
        ? 'Lead Time Violations'
        : alertFilter === 'out-of-order'
            ? 'Out-of-Order Validations'
            : '';

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-64">Loading validation alerts...</div>
            </Layout>
        );
    }

    if (error) {
        return (
            <Layout>
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                    <p className="text-red-800">{error}</p>
                    <button
                        onClick={fetchAlerts}
                        className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                    >
                        Retry
                    </button>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="p-6">
                <div className="mb-6">
                    <div className="flex items-center gap-2 mb-2">
                        <Link to="/dashboard" className="text-blue-600 hover:text-blue-800 text-sm">
                            &lt;- Back to Admin Dashboard
                        </Link>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900">Validation Alerts</h2>
                    <p className="mt-1 text-sm text-gray-600">
                        Track validation requests that miss lead-time policy requirements or occur after production.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <StatFilterCard
                        label="All Alerts"
                        count={totalAlerts}
                        isActive={alertFilter === 'all'}
                        onClick={() => setAlertFilter('all')}
                        colorScheme="blue"
                        disabled={totalAlerts === 0}
                    />
                    <StatFilterCard
                        label="Lead Time Violations"
                        count={slaViolations.length}
                        isActive={alertFilter === 'lead-time'}
                        onClick={() => setAlertFilter('lead-time')}
                        colorScheme="red"
                        disabled={slaViolations.length === 0}
                    />
                    <StatFilterCard
                        label="Out-of-Order Validations"
                        count={outOfOrder.length}
                        isActive={alertFilter === 'out-of-order'}
                        onClick={() => setAlertFilter('out-of-order')}
                        colorScheme="purple"
                        disabled={outOfOrder.length === 0}
                    />
                </div>

                {alertFilter !== 'all' && (
                    <FilterStatusBar
                        activeFilterLabel={activeFilterLabel}
                        onClear={() => setAlertFilter('all')}
                        entityName="alerts"
                    />
                )}

                {(alertFilter === 'all' || alertFilter === 'lead-time') && (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden mb-6">
                        <div className="p-4 border-b bg-red-50">
                            <div className="flex items-center">
                                <h3 className="text-lg font-bold text-red-900">
                                    Lead Time Violations ({slaViolations.length})
                                </h3>
                                <button
                                    onClick={() => exportToCSV(slaViolations, 'lead_time_violations', [
                                        { key: 'request_id', label: 'Request ID' },
                                        { key: 'model_name', label: 'Model Name' },
                                        { key: 'violation_type', label: 'Violation Type' },
                                        { key: 'sla_days', label: 'Lead Time (Days)' },
                                        { key: 'actual_days', label: 'Actual Days' },
                                        { key: 'days_overdue', label: 'Days Overdue' },
                                        { key: 'current_status', label: 'Status' },
                                        { key: 'priority', label: 'Priority' },
                                        { key: 'severity', label: 'Severity' },
                                        { key: 'timestamp', label: 'Detected At' },
                                    ])}
                                    className="ml-auto text-red-600 hover:text-red-800"
                                    title="Export to CSV"
                                    disabled={slaViolations.length === 0}
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </button>
                            </div>
                            <p className="text-sm text-red-700 mt-1">Requests submitted without required lead time before implementation.</p>
                        </div>
                        {slaViolations.length === 0 ? (
                            <div className="p-6 text-center text-sm text-gray-500">
                                No lead time violations found.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Violation</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lead Time</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Overdue</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Detected</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {slaViolations.map((violation, index) => (
                                            <tr key={`${violation.request_id}-${index}`} className="hover:bg-gray-50">
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <Link
                                                        to={`/validation-workflow/${violation.request_id}`}
                                                        className="text-blue-600 hover:text-blue-800 font-medium"
                                                    >
                                                        {violation.model_name}
                                                    </Link>
                                                    <div className="text-xs text-gray-500">Request #{violation.request_id}</div>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-gray-700">
                                                    {violation.violation_type}
                                                    <div className="mt-1">
                                                        <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getSeverityBadge(violation.severity)}`}>
                                                            {violation.severity}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                                    {violation.current_status}
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                                    {violation.priority}
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                                    {violation.sla_days}d required • {violation.actual_days}d actual
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <span className="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800">
                                                        {violation.days_overdue} days
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                                    {formatDate(violation.timestamp)}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {(alertFilter === 'all' || alertFilter === 'out-of-order') && (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-purple-50">
                            <div className="flex items-center">
                                <h3 className="text-lg font-bold text-purple-900">
                                    Out-of-Order Validations ({outOfOrder.length})
                                </h3>
                                <button
                                    onClick={() => exportToCSV(outOfOrder, 'out_of_order_validations', [
                                        { key: 'request_id', label: 'Request ID' },
                                        { key: 'model_name', label: 'Model Name' },
                                        { key: 'version_number', label: 'Version' },
                                        { key: 'validation_type', label: 'Validation Type' },
                                        { key: 'target_completion_date', label: 'Target Completion' },
                                        { key: 'production_date', label: 'Production Date' },
                                        { key: 'days_gap', label: 'Days Gap' },
                                        { key: 'current_status', label: 'Status' },
                                        { key: 'priority', label: 'Priority' },
                                        { key: 'severity', label: 'Severity' },
                                        { key: 'is_interim', label: 'Interim' },
                                    ])}
                                    className="ml-auto text-purple-600 hover:text-purple-800"
                                    title="Export to CSV"
                                    disabled={outOfOrder.length === 0}
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </button>
                            </div>
                            <p className="text-sm text-purple-700 mt-1">Validations started after the model version entered production.</p>
                        </div>
                        {outOfOrder.length === 0 ? (
                            <div className="p-6 text-center text-sm text-gray-500">
                                No out-of-order validations found.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation Type</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Production Date</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Completion</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Gap</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {outOfOrder.map((item, index) => (
                                            <tr key={`${item.request_id}-${index}`} className="hover:bg-gray-50">
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <Link
                                                        to={`/validation-workflow/${item.request_id}`}
                                                        className="text-blue-600 hover:text-blue-800 font-medium"
                                                    >
                                                        {getOutOfOrderModelLabel(item)}
                                                    </Link>
                                                    <div className="text-xs text-gray-500">
                                                        {(item.version_number || '').trim() ? `v${item.version_number}` : 'Version unavailable'}
                                                        {item.is_interim && (
                                                            <span className="ml-2 px-2 py-0.5 text-xs font-semibold rounded bg-yellow-100 text-yellow-800">
                                                                Interim
                                                            </span>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                                    {item.validation_type}
                                                    <div className="mt-1">
                                                        <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getSeverityBadge(item.severity)}`}>
                                                            {item.severity}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                                    {formatDate(item.production_date)}
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                                    {formatDate(item.target_completion_date)}
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <span className="px-2 py-1 text-xs font-semibold rounded bg-purple-100 text-purple-800">
                                                        {item.days_gap} days
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                                    {item.current_status}
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                                    {item.priority}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default ValidationAlertsPage;

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import client from '../api/client';

interface NameChangeRecord {
    history_id: number;
    model_id: number;
    old_name: string;
    new_name: string;
    changed_by_id: number | null;
    changed_by_name: string | null;
    changed_at: string;
    change_reason: string | null;
}

interface NameChangeStatistics {
    total_models_with_changes: number;
    models_changed_last_90_days: number;
    models_changed_last_30_days: number;
    total_name_changes: number;
    recent_changes: NameChangeRecord[];
}

// Helper to format date as YYYY-MM-DD
const formatDate = (date: Date): string => {
    return date.toISOString().split('T')[0];
};

// Get the most recent completed fiscal quarter (fiscal year ends Oct 31)
// Q1: Nov 1 - Jan 31, Q2: Feb 1 - Apr 30, Q3: May 1 - Jul 31, Q4: Aug 1 - Oct 31
const getMostRecentFiscalQuarter = (): { start: string; end: string; label: string } => {
    const today = new Date();
    const currentMonth = today.getMonth(); // 0-indexed
    const currentYear = today.getFullYear();

    // Determine which fiscal quarter we're in and get the previous one
    // Month mapping to fiscal quarters:
    // Nov (10), Dec (11), Jan (0) = Q1
    // Feb (1), Mar (2), Apr (3) = Q2
    // May (4), Jun (5), Jul (6) = Q3
    // Aug (7), Sep (8), Oct (9) = Q4

    let quarterStart: Date;
    let quarterEnd: Date;
    let fiscalYear: number;
    let quarterNum: number;

    if (currentMonth >= 10) {
        // Nov or Dec - we're in Q1 of next FY, return Q4 of FY ending this Oct
        quarterStart = new Date(currentYear, 7, 1); // Aug 1
        quarterEnd = new Date(currentYear, 9, 31); // Oct 31
        fiscalYear = currentYear; // FY2025 ends Oct 31, 2025
        quarterNum = 4;
    } else if (currentMonth >= 7) {
        // Aug, Sep, Oct - we're in Q4, return Q3 of same FY
        quarterStart = new Date(currentYear, 4, 1); // May 1
        quarterEnd = new Date(currentYear, 6, 31); // Jul 31
        fiscalYear = currentYear; // FY2025 ends Oct 31, 2025
        quarterNum = 3;
    } else if (currentMonth >= 4) {
        // May, Jun, Jul - we're in Q3, return Q2 of same FY
        quarterStart = new Date(currentYear, 1, 1); // Feb 1
        quarterEnd = new Date(currentYear, 3, 30); // Apr 30
        fiscalYear = currentYear;
        quarterNum = 2;
    } else if (currentMonth >= 1) {
        // Feb, Mar, Apr - we're in Q2, return Q1 of same FY
        quarterStart = new Date(currentYear - 1, 10, 1); // Nov 1 of previous year
        quarterEnd = new Date(currentYear, 0, 31); // Jan 31
        fiscalYear = currentYear;
        quarterNum = 1;
    } else {
        // Jan - we're in Q1, return Q4 of previous fiscal year
        quarterStart = new Date(currentYear - 1, 7, 1); // Aug 1 of previous year
        quarterEnd = new Date(currentYear - 1, 9, 31); // Oct 31 of previous year
        fiscalYear = currentYear - 1; // FY2024 ends Oct 31, 2024
        quarterNum = 4;
    }

    return {
        start: formatDate(quarterStart),
        end: formatDate(quarterEnd),
        label: `FY${fiscalYear} Q${quarterNum}`
    };
};

const NameChangesReportPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [statistics, setStatistics] = useState<NameChangeStatistics | null>(null);

    // Date range filters
    const [startDate, setStartDate] = useState<string>('');
    const [endDate, setEndDate] = useState<string>('');

    useEffect(() => {
        fetchStatistics();
    }, []);

    const fetchStatistics = async (startOverride?: string, endOverride?: string) => {
        try {
            setLoading(true);
            const start = startOverride ?? startDate;
            const end = endOverride ?? endDate;
            const params = new URLSearchParams();
            if (start) params.append('start_date', start);
            if (end) params.append('end_date', end);

            const url = params.toString()
                ? `/models/name-changes/stats?${params.toString()}`
                : '/models/name-changes/stats';
            const response = await client.get(url);
            setStatistics(response.data);
        } catch (error) {
            console.error('Failed to fetch name change statistics:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleApplyFilters = () => {
        fetchStatistics();
    };

    const handleClearFilters = () => {
        setStartDate('');
        setEndDate('');
        fetchStatistics('', '');
    };

    // Quick date range setters (auto-apply)
    const setLast30Days = () => {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 30);
        const startStr = formatDate(start);
        const endStr = formatDate(end);
        setStartDate(startStr);
        setEndDate(endStr);
        fetchStatistics(startStr, endStr);
    };

    const setLast90Days = () => {
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 90);
        const startStr = formatDate(start);
        const endStr = formatDate(end);
        setStartDate(startStr);
        setEndDate(endStr);
        fetchStatistics(startStr, endStr);
    };

    const setLastFiscalQuarter = () => {
        const quarter = getMostRecentFiscalQuarter();
        setStartDate(quarter.start);
        setEndDate(quarter.end);
        fetchStatistics(quarter.start, quarter.end);
    };

    const exportToCsv = () => {
        if (!statistics) return;

        const headers = ['Model ID', 'Old Name', 'New Name', 'Changed By', 'Changed At'];
        const rows = statistics.recent_changes.map(record => [
            record.model_id.toString(),
            record.old_name,
            record.new_name,
            record.changed_by_name || 'Unknown',
            record.changed_at.split('T')[0]
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `model_name_changes_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
    };

    const fiscalQuarter = getMostRecentFiscalQuarter();

    return (
        <Layout>
            <div className="p-6">
                {/* Header */}
                <div className="mb-6">
                    <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
                        <Link to="/reports" className="hover:text-blue-600">Reports</Link>
                        <span>/</span>
                        <span>Model Name Changes</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <div>
                            <h2 className="text-2xl font-bold text-gray-900">Model Name Changes Report</h2>
                            <p className="mt-1 text-sm text-gray-600">
                                Track all model name changes over time for audit and compliance purposes.
                            </p>
                        </div>
                        <div className="flex gap-3">
                            <button
                                onClick={exportToCsv}
                                disabled={!statistics || statistics.recent_changes.length === 0}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Export CSV
                            </button>
                        </div>
                    </div>
                </div>

                {/* Date Range Filters */}
                <div className="bg-white p-4 rounded-lg shadow-md mb-6">
                    <div className="flex flex-wrap items-end gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Start Date
                            </label>
                            <input
                                type="date"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                End Date
                            </label>
                            <input
                                type="date"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleApplyFilters}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                            >
                                Apply
                            </button>
                            {(startDate || endDate) && (
                                <button
                                    onClick={handleClearFilters}
                                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                                >
                                    Clear
                                </button>
                            )}
                        </div>
                        <div className="border-l border-gray-300 pl-4 flex gap-2">
                            <span className="text-sm text-gray-500 self-center mr-1">Quick:</span>
                            <button
                                onClick={() => { setLast30Days(); }}
                                className="px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                            >
                                Last 30 Days
                            </button>
                            <button
                                onClick={() => { setLast90Days(); }}
                                className="px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                            >
                                Last 90 Days
                            </button>
                            <button
                                onClick={() => { setLastFiscalQuarter(); }}
                                className="px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                                title={`${fiscalQuarter.start} to ${fiscalQuarter.end}`}
                            >
                                {fiscalQuarter.label}
                            </button>
                        </div>
                    </div>
                    {(startDate || endDate) && (
                        <p className="mt-2 text-sm text-gray-500">
                            Showing name changes
                            {startDate && ` from ${startDate}`}
                            {endDate && ` to ${endDate}`}
                        </p>
                    )}
                </div>

                {loading ? (
                    <div className="flex justify-center items-center h-64">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                ) : statistics ? (
                    <>
                        {/* Statistics Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                            <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-500">
                                <div className="text-sm font-medium text-gray-500 uppercase tracking-wider">
                                    Total Name Changes
                                </div>
                                <div className="mt-2 text-3xl font-bold text-gray-900">
                                    {statistics.total_name_changes}
                                </div>
                                <div className="mt-1 text-xs text-gray-500">All time</div>
                            </div>
                            <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-green-500">
                                <div className="text-sm font-medium text-gray-500 uppercase tracking-wider">
                                    Models with Changes
                                </div>
                                <div className="mt-2 text-3xl font-bold text-gray-900">
                                    {statistics.total_models_with_changes}
                                </div>
                                <div className="mt-1 text-xs text-gray-500">Unique models renamed</div>
                            </div>
                        </div>

                        {/* Recent Changes Table */}
                        <div className="bg-white rounded-lg shadow-md overflow-hidden">
                            <div className="px-6 py-4 border-b border-gray-200">
                                <h3 className="text-lg font-semibold text-gray-900">Name Changes</h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    {startDate || endDate
                                        ? `Showing ${statistics.recent_changes.length} name changes in selected date range`
                                        : `Showing the most recent ${statistics.recent_changes.length} name changes`
                                    }
                                </p>
                            </div>
                            {statistics.recent_changes.length === 0 ? (
                                <div className="p-8 text-center text-gray-500">
                                    <svg className="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <p>No name changes found{startDate || endDate ? ' in selected date range' : ''}.</p>
                                    <p className="text-sm mt-1">
                                        {startDate || endDate
                                            ? 'Try adjusting the date range or clearing filters.'
                                            : 'Name changes will appear here when models are renamed.'
                                        }
                                    </p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Model
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Old Name
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    New Name
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Changed By
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Changed At
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {statistics.recent_changes.map((record) => (
                                                <tr key={record.history_id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <Link
                                                            to={`/models/${record.model_id}`}
                                                            className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                                        >
                                                            #{record.model_id}
                                                        </Link>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className="text-gray-500 line-through">{record.old_name}</span>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className="text-gray-900 font-medium">{record.new_name}</span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                                        {record.changed_by_name || 'Unknown'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                                        {record.changed_at.split('T')[0]}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                        Failed to load report data. Please try again.
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default NameChangesReportPage;

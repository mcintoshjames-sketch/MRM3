import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import {
    getCriticalLimitationsReport,
    CriticalLimitationReportItem,
} from '../api/limitations';
import api from '../api/client';

interface Region {
    region_id: number;
    name: string;
}

const CriticalLimitationsReportPage: React.FC = () => {
    const [reportItems, setReportItems] = useState<CriticalLimitationReportItem[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedRegionId, setSelectedRegionId] = useState<number | undefined>(undefined);

    const fetchRegions = async () => {
        try {
            const response = await api.get('/regions/');
            setRegions(response.data);
        } catch (err) {
            console.error('Failed to fetch regions:', err);
        }
    };

    const fetchReport = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getCriticalLimitationsReport(selectedRegionId);
            setReportItems(data.items);
        } catch (err) {
            console.error('Failed to fetch report:', err);
            setError('Failed to load critical limitations report');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRegions();
    }, []);

    useEffect(() => {
        fetchReport();
    }, [selectedRegionId]);

    const exportToCSV = () => {
        if (reportItems.length === 0) return;

        const headers = [
            'Limitation ID',
            'Model ID',
            'Model Name',
            'Region',
            'Category',
            'Description',
            'Impact Assessment',
            'Conclusion',
            'Conclusion Rationale',
            'User Awareness',
            'Originating Validation',
            'Created At'
        ];

        const rows = reportItems.map(item => [
            item.limitation_id,
            item.model_id,
            `"${item.model_name.replace(/"/g, '""')}"`,
            item.region_name || '',
            item.category_label,
            `"${item.description.replace(/"/g, '""')}"`,
            `"${item.impact_assessment.replace(/"/g, '""')}"`,
            item.conclusion,
            `"${item.conclusion_rationale.replace(/"/g, '""')}"`,
            `"${item.user_awareness_description.replace(/"/g, '""')}"`,
            item.originating_validation || '',
            item.created_at.split('T')[0]
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `critical_limitations_report_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // Group by category for summary
    const categoryBreakdown = reportItems.reduce((acc, item) => {
        acc[item.category_label] = (acc[item.category_label] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    // Group by conclusion
    const conclusionBreakdown = reportItems.reduce((acc, item) => {
        acc[item.conclusion] = (acc[item.conclusion] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    return (
        <Layout>
            <div className="p-6">
                {/* Header */}
                <div className="mb-6 flex justify-between items-start">
                    <div>
                        <Link
                            to="/reports"
                            className="text-blue-600 hover:text-blue-800 text-sm mb-2 inline-block"
                        >
                            &larr; Back to Reports
                        </Link>
                        <h2 className="text-2xl font-bold text-gray-900">Critical Limitations Report</h2>
                        <p className="mt-1 text-sm text-gray-600">
                            Overview of all critical model limitations. These require documented user awareness.
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={fetchReport}
                            className="bg-gray-100 text-gray-700 px-4 py-2 rounded hover:bg-gray-200 text-sm"
                        >
                            Refresh
                        </button>
                        <button
                            onClick={exportToCSV}
                            disabled={reportItems.length === 0}
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm disabled:opacity-50"
                        >
                            Export CSV
                        </button>
                    </div>
                </div>

                {/* Filters */}
                <div className="bg-white rounded-lg shadow-md p-4 mb-6">
                    <div className="flex items-center gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Filter by Region
                            </label>
                            <select
                                value={selectedRegionId || ''}
                                onChange={(e) => setSelectedRegionId(e.target.value ? parseInt(e.target.value) : undefined)}
                                className="border border-gray-300 rounded px-3 py-2 text-sm"
                            >
                                <option value="">All Regions</option>
                                {regions.map((region) => (
                                    <option key={region.region_id} value={region.region_id}>
                                        {region.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-white rounded-lg shadow-md p-4">
                        <h4 className="text-sm font-medium text-gray-500">Total Critical Limitations</h4>
                        <p className="text-3xl font-bold text-red-600 mt-1">{reportItems.length}</p>
                    </div>
                    <div className="bg-white rounded-lg shadow-md p-4">
                        <h4 className="text-sm font-medium text-gray-500">To Mitigate</h4>
                        <p className="text-3xl font-bold text-yellow-600 mt-1">{conclusionBreakdown['Mitigate'] || 0}</p>
                    </div>
                    <div className="bg-white rounded-lg shadow-md p-4">
                        <h4 className="text-sm font-medium text-gray-500">Accepted</h4>
                        <p className="text-3xl font-bold text-green-600 mt-1">{conclusionBreakdown['Accept'] || 0}</p>
                    </div>
                    <div className="bg-white rounded-lg shadow-md p-4">
                        <h4 className="text-sm font-medium text-gray-500">Unique Models</h4>
                        <p className="text-3xl font-bold text-blue-600 mt-1">
                            {new Set(reportItems.map(i => i.model_id)).size}
                        </p>
                    </div>
                </div>

                {/* Category Breakdown */}
                {Object.keys(categoryBreakdown).length > 0 && (
                    <div className="bg-white rounded-lg shadow-md p-4 mb-6">
                        <h4 className="text-sm font-medium text-gray-700 mb-3">Breakdown by Category</h4>
                        <div className="flex flex-wrap gap-2">
                            {Object.entries(categoryBreakdown).map(([category, count]) => (
                                <span
                                    key={category}
                                    className="px-3 py-1 text-sm bg-gray-100 text-gray-800 rounded"
                                >
                                    {category}: <span className="font-medium">{count}</span>
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Error State */}
                {error && (
                    <div className="bg-red-100 text-red-800 p-4 rounded-lg mb-6">
                        {error}
                    </div>
                )}

                {/* Loading State */}
                {loading ? (
                    <div className="bg-white rounded-lg shadow-md p-12 text-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                        <p className="mt-4 text-gray-600">Loading report...</p>
                    </div>
                ) : reportItems.length === 0 ? (
                    <div className="bg-white rounded-lg shadow-md p-12 text-center">
                        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p className="mt-4 text-lg text-gray-600">No Critical Limitations Found</p>
                        <p className="mt-2 text-sm text-gray-500">
                            {selectedRegionId
                                ? 'No critical limitations found for the selected region.'
                                : 'There are currently no critical limitations recorded in the inventory.'}
                        </p>
                    </div>
                ) : (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Conclusion</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User Awareness</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {reportItems.map((item) => (
                                        <tr key={item.limitation_id} className="hover:bg-gray-50">
                                            <td className="px-4 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/models/${item.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 font-medium"
                                                >
                                                    {item.model_name}
                                                </Link>
                                                <div className="text-xs text-gray-500">ID: {item.model_id}</div>
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {item.region_name || <span className="text-gray-400">-</span>}
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap">
                                                <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-800">
                                                    {item.category_label}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4 text-sm text-gray-900 max-w-xs">
                                                <div className="truncate" title={item.description}>
                                                    {item.description.length > 80
                                                        ? `${item.description.slice(0, 80)}...`
                                                        : item.description}
                                                </div>
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap">
                                                {item.conclusion === 'Mitigate' ? (
                                                    <span className="px-2 py-1 text-xs font-medium rounded bg-yellow-100 text-yellow-800">
                                                        Mitigate
                                                    </span>
                                                ) : (
                                                    <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                                                        Accept
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-4 py-4 text-sm text-gray-900 max-w-xs">
                                                <div className="truncate" title={item.user_awareness_description}>
                                                    {item.user_awareness_description.length > 60
                                                        ? `${item.user_awareness_description.slice(0, 60)}...`
                                                        : item.user_awareness_description}
                                                </div>
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {item.created_at.split('T')[0]}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default CriticalLimitationsReportPage;

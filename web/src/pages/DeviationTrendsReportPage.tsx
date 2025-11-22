import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import client from '../api/client';

interface Summary {
    total_validation_plans: number;
    total_components_reviewed: number;
    total_deviations: number;
    plans_with_deviations: number;
    plans_with_material_deviations: number;
    deviation_rate_percentage: number;
    plan_deviation_rate_percentage: number;
}

interface ComponentDeviation {
    component_code: string;
    count: number;
}

interface SectionDeviation {
    section: string;
    count: number;
}

interface TimelinePoint {
    month: string;
    count: number;
}

interface DeviationRecord {
    plan_id: number;
    request_id: number;
    model_name: string;
    risk_tier: string;
    component_code: string;
    component_title: string;
    section_number: string;
    section_title: string;
    rationale: string | null;
    created_at: string | null;
}

interface ReportData {
    summary: Summary;
    deviation_by_component: ComponentDeviation[];
    deviation_by_risk_tier: { [key: string]: number };
    deviation_by_section: SectionDeviation[];
    deviations_timeline: TimelinePoint[];
    recent_deviations: DeviationRecord[];
}

const DeviationTrendsReportPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [reportData, setReportData] = useState<ReportData | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchReport();
    }, []);

    const fetchReport = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await client.get('/validation-workflow/compliance-report/deviation-trends');
            setReportData(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to fetch deviation trends report');
        } finally {
            setLoading(false);
        }
    };

    const handleExportCSV = () => {
        if (!reportData) return;

        const headers = ['Model', 'Risk Tier', 'Component Code', 'Component Title', 'Section', 'Rationale', 'Date'];
        const rows = reportData.recent_deviations.map(d => [
            d.model_name,
            d.risk_tier,
            d.component_code,
            `"${d.component_title.replace(/"/g, '""')}"`,
            `${d.section_number} - ${d.section_title}`,
            d.rationale ? `"${d.rationale.replace(/"/g, '""')}"` : '',
            d.created_at ? d.created_at.split('T')[0] : ''
        ].join(','));

        const csv = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `deviation_trends_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    };

    if (loading) {
        return (
            <Layout>
                <div className="text-center py-12">
                    <div className="text-gray-500">Loading deviation trends report...</div>
                </div>
            </Layout>
        );
    }

    if (error) {
        return (
            <Layout>
                <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
                    {error}
                </div>
            </Layout>
        );
    }

    if (!reportData) return null;

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Deviation Trends Report</h1>
                        <p className="text-gray-600 mt-2">
                            Track validation component deviations across all validation projects
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <button onClick={fetchReport} className="btn-secondary">
                            Refresh Report
                        </button>
                        {reportData.recent_deviations.length > 0 && (
                            <button onClick={handleExportCSV} className="btn-secondary">
                                Export CSV
                            </button>
                        )}
                    </div>
                </div>

                {/* Summary Cards */}
                <div className="grid grid-cols-4 gap-4">
                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="text-sm font-medium text-gray-500">Total Plans Reviewed</div>
                        <div className="text-3xl font-bold text-gray-900 mt-2">
                            {reportData.summary.total_validation_plans}
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="text-sm font-medium text-gray-500">Total Deviations</div>
                        <div className="text-3xl font-bold text-orange-600 mt-2">
                            {reportData.summary.total_deviations}
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="text-sm font-medium text-gray-500">Deviation Rate</div>
                        <div className="text-3xl font-bold text-blue-600 mt-2">
                            {reportData.summary.deviation_rate_percentage}%
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                            of components deviate
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="text-sm font-medium text-gray-500">Material Deviations</div>
                        <div className="text-3xl font-bold text-red-600 mt-2">
                            {reportData.summary.plans_with_material_deviations}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                            plans flagged as material
                        </div>
                    </div>
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-2 gap-6">
                    {/* Deviations by Risk Tier */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-bold mb-4">Deviations by Model Risk Tier</h3>
                        <div className="space-y-3">
                            {Object.entries(reportData.deviation_by_risk_tier).map(([tier, count]) => {
                                const total = Object.values(reportData.deviation_by_risk_tier).reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? (count / total * 100).toFixed(1) : 0;
                                const color = tier === 'High' ? 'bg-red-500' : tier === 'Medium' ? 'bg-orange-500' : tier === 'Low' ? 'bg-yellow-500' : 'bg-green-500';

                                return (
                                    <div key={tier}>
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="font-medium">{tier}</span>
                                            <span className="text-gray-600">{count} ({percentage}%)</span>
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-2">
                                            <div className={`${color} h-2 rounded-full`} style={{ width: `${percentage}%` }}></div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Top Deviation Components */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-bold mb-4">Top 10 Components with Deviations</h3>
                        <div className="space-y-2">
                            {reportData.deviation_by_component.slice(0, 10).map((item, index) => (
                                <div key={item.component_code} className="flex justify-between items-center">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-semibold text-gray-500">#{index + 1}</span>
                                        <span className="text-sm font-medium">{item.component_code}</span>
                                    </div>
                                    <span className="text-sm font-bold text-orange-600">{item.count}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Deviations Timeline */}
                {reportData.deviations_timeline.length > 0 && (
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-bold mb-4">Deviation Trend Over Time</h3>
                        <div className="flex items-end gap-2 h-48">
                            {reportData.deviations_timeline.map((point) => {
                                const maxCount = Math.max(...reportData.deviations_timeline.map(p => p.count));
                                const height = (point.count / maxCount * 100);
                                return (
                                    <div key={point.month} className="flex-1 flex flex-col items-center">
                                        <div className="text-xs font-semibold text-orange-600 mb-1">{point.count}</div>
                                        <div className="w-full bg-orange-500 rounded-t" style={{ height: `${height}%` }}></div>
                                        <div className="text-xs text-gray-500 mt-2 transform -rotate-45 origin-top-left whitespace-nowrap">
                                            {point.month}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Deviations by Section */}
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-bold mb-4">Deviations by Validation Section</h3>
                    <div className="grid grid-cols-3 gap-4">
                        {reportData.deviation_by_section.map((item) => (
                            <div key={item.section} className="border rounded p-3">
                                <div className="text-sm font-medium text-gray-700">Section {item.section}</div>
                                <div className="text-2xl font-bold text-orange-600 mt-1">{item.count}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Recent Deviations Table */}
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-bold mb-4">Recent Deviations (Last 50)</h3>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Component</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Section</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rationale</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {reportData.recent_deviations.map((deviation, index) => (
                                    <tr key={index} className="hover:bg-gray-50">
                                        <td className="px-4 py-3 text-sm text-gray-600">
                                            {deviation.created_at ? deviation.created_at.split('T')[0] : 'N/A'}
                                        </td>
                                        <td className="px-4 py-3 text-sm font-medium">{deviation.model_name}</td>
                                        <td className="px-4 py-3 text-sm">
                                            <span className={`px-2 py-1 text-xs rounded ${
                                                deviation.risk_tier.includes('High') || deviation.risk_tier.includes('Tier 1') ? 'bg-red-100 text-red-800' :
                                                deviation.risk_tier.includes('Medium') || deviation.risk_tier.includes('Tier 2') ? 'bg-orange-100 text-orange-800' :
                                                'bg-yellow-100 text-yellow-800'
                                            }`}>
                                                {deviation.risk_tier}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-sm">
                                            <div className="font-medium">{deviation.component_code}</div>
                                            <div className="text-xs text-gray-500">{deviation.component_title}</div>
                                        </td>
                                        <td className="px-4 py-3 text-sm text-gray-600">
                                            {deviation.section_number}
                                        </td>
                                        <td className="px-4 py-3 text-sm text-gray-600 max-w-md truncate">
                                            {deviation.rationale || <span className="text-gray-400 italic">No rationale provided</span>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default DeviationTrendsReportPage;

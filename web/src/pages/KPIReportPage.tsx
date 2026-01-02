/**
 * KPIReportPage - displays the KPI Report with all model risk management metrics.
 */
import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import KPIMetricCard from '../components/KPIMetricCard';
import KPIDefinitionModal from '../components/KPIDefinitionModal';
import {
    getKPIReport,
    groupMetricsByCategory,
    exportKPIReportToCSV,
    KPIReportResponse,
    KPIMetric,
} from '../api/kpiReport';
import { regionsApi, Region } from '../api/regions';
import { getTeams, Team as TeamOption } from '../api/teams';

const KPIReportPage: React.FC = () => {
    const [report, setReport] = useState<KPIReportResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedMetric, setSelectedMetric] = useState<KPIMetric | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [regions, setRegions] = useState<Region[]>([]);
    const [selectedRegion, setSelectedRegion] = useState<string>('');
    const [teams, setTeams] = useState<TeamOption[]>([]);
    const [selectedTeam, setSelectedTeam] = useState<string>('');

    const fetchReport = async () => {
        setLoading(true);
        setError(null);
        try {
            const regionId = selectedRegion ? parseInt(selectedRegion) : undefined;
            const teamId = selectedTeam === 'unassigned'
                ? 0
                : selectedTeam
                    ? parseInt(selectedTeam)
                    : undefined;
            const data = await getKPIReport(regionId, teamId);
            setReport(data);
        } catch (err) {
            console.error('Failed to fetch KPI report:', err);
            setError('Failed to load KPI report. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // Fetch regions on mount
    useEffect(() => {
        regionsApi.getRegions().then(setRegions).catch(console.error);
        getTeams().then((res) => setTeams(res.data)).catch(console.error);
    }, []);

    // Re-fetch report when region changes
    useEffect(() => {
        fetchReport();
    }, [selectedRegion, selectedTeam]);

    const handleInfoClick = (metric: KPIMetric) => {
        setSelectedMetric(metric);
        setIsModalOpen(true);
    };

    const handleExportCSV = () => {
        if (!report) return;

        const csvContent = exportKPIReportToCSV(report);
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        // Include region in filename if filtered
        const regionSuffix = report.region_name !== 'All Regions'
            ? `_${report.region_name.replace(/\s+/g, '_')}`
            : '';
        const teamSuffix = report.team_name !== 'All Teams'
            ? `_${report.team_name.replace(/\s+/g, '_')}`
            : '';
        link.download = `kpi_report${regionSuffix}${teamSuffix}_${report.as_of_date}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    // Get summary counts for the header cards
    const getSummaryStats = () => {
        if (!report) return { totalModels: 0, openRecs: 0, kriAlerts: 0 };

        const totalModels = report.total_active_models;
        const openRecsMetric = report.metrics.find(m => m.metric_id === '4.18');
        const openRecs = openRecsMetric?.count_value ?? 0;

        // Count KRI metrics with concerning values
        const kriMetrics = report.metrics.filter(m => m.is_kri);
        let kriAlerts = 0;
        for (const kri of kriMetrics) {
            if (kri.ratio_value && kri.ratio_value.percentage > 10) {
                kriAlerts++;
            }
        }

        return { totalModels, openRecs, kriAlerts };
    };

    const stats = getSummaryStats();
    const groupedMetrics = report ? groupMetricsByCategory(report.metrics) : {};

    // Define category order for display
    const categoryOrder = [
        'Model Inventory',
        'Validation',
        'Monitoring',
        'Model Risk',
        'Recommendations',
        'Governance',
        'Model Lifecycle',
        'Key Risk Indicators',
    ];

    // Sort categories by predefined order
    const sortedCategories = Object.keys(groupedMetrics).sort((a, b) => {
        const indexA = categoryOrder.indexOf(a);
        const indexB = categoryOrder.indexOf(b);
        if (indexA === -1 && indexB === -1) return a.localeCompare(b);
        if (indexA === -1) return 1;
        if (indexB === -1) return -1;
        return indexA - indexB;
    });

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-semibold text-gray-900">
                            KPI Report
                            {report && report.region_name !== 'All Regions' && (
                                <span className="ml-2 text-lg text-blue-600">
                                    ({report.region_name})
                                </span>
                            )}
                            {report && report.team_name !== 'All Teams' && (
                                <span className="ml-2 text-lg text-emerald-600">
                                    ({report.team_name})
                                </span>
                            )}
                        </h1>
                        {report && (
                            <p className="text-sm text-gray-500 mt-1">
                                As of {report.as_of_date} | Generated at {new Date(report.report_generated_at).toLocaleString()}
                            </p>
                        )}
                    </div>
                        <div className="flex items-center gap-3">
                            <div className="flex items-center gap-2">
                                <label htmlFor="region-filter" className="text-sm font-medium text-gray-700">
                                    Region:
                                </label>
                            <select
                                id="region-filter"
                                value={selectedRegion}
                                onChange={(e) => setSelectedRegion(e.target.value)}
                                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
                            >
                                <option value="">All Regions</option>
                                {regions.map((region) => (
                                    <option key={region.region_id} value={region.region_id}>
                                        {region.name}
                                    </option>
                                ))}
                                </select>
                            </div>
                            <div className="flex items-center gap-2">
                                <label htmlFor="team-filter" className="text-sm font-medium text-gray-700">
                                    Team:
                                </label>
                                <select
                                    id="team-filter"
                                    value={selectedTeam}
                                    onChange={(e) => setSelectedTeam(e.target.value)}
                                    className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
                                >
                                    <option value="">All Teams</option>
                                    <option value="unassigned">Unassigned</option>
                                    {teams.filter(team => team.is_active).map((team) => (
                                        <option key={team.team_id} value={team.team_id}>
                                            {team.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        <button
                            onClick={handleExportCSV}
                            disabled={loading || !report}
                            className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Export CSV
                        </button>
                        <button
                            onClick={fetchReport}
                            disabled={loading}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? 'Loading...' : 'Refresh Report'}
                        </button>
                    </div>
                </div>

                {/* Error state */}
                {error && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-4">
                        <p className="text-red-700">{error}</p>
                    </div>
                )}

                {/* Loading state */}
                {loading && (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <span className="ml-3 text-gray-600">Loading metrics...</span>
                    </div>
                )}

                {/* Content */}
                {!loading && report && (
                    <>
                        {/* Summary cards */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
                                <div className="text-3xl font-bold text-gray-900">
                                    {stats.totalModels.toLocaleString()}
                                </div>
                                <div className="text-sm text-gray-500 mt-1">Active Models</div>
                            </div>
                            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-yellow-500">
                                <div className="text-3xl font-bold text-gray-900">
                                    {stats.openRecs.toLocaleString()}
                                </div>
                                <div className="text-sm text-gray-500 mt-1">Open Recommendations</div>
                            </div>
                            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-red-500">
                                <div className="text-3xl font-bold text-gray-900">
                                    {stats.kriAlerts}
                                </div>
                                <div className="text-sm text-gray-500 mt-1">KRI Alerts</div>
                            </div>
                        </div>

                        {/* Metrics grouped by category */}
                        {sortedCategories.map(category => (
                            <div key={category} className="space-y-4">
                                <h2 className="text-lg font-semibold text-gray-800 border-b border-gray-200 pb-2">
                                    {category}
                                </h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                    {groupedMetrics[category].map(metric => (
                                        <KPIMetricCard
                                            key={metric.metric_id}
                                            metric={metric}
                                            onInfoClick={handleInfoClick}
                                        />
                                    ))}
                                </div>
                            </div>
                        ))}
                    </>
                )}

                {/* Definition Modal */}
                <KPIDefinitionModal
                    metric={selectedMetric}
                    isOpen={isModalOpen}
                    onClose={() => setIsModalOpen(false)}
                />
            </div>
        </Layout>
    );
};

export default KPIReportPage;

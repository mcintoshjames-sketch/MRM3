import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/client';
import {
    getModelOverlaysReport,
    ModelOverlayReportItem,
    OverlayKind,
} from '../api/modelOverlays';
import { useTableSort } from '../hooks/useTableSort';

interface Region {
    region_id: number;
    code: string;
    name: string;
}

interface Team {
    team_id: number;
    name: string;
}

interface RiskTier {
    value_id: number;
    code: string;
    label: string;
    is_active: boolean;
}

const formatDate = (value?: string | null) => (value ? value.split('T')[0] : '');

const ModelOverlaysReportPage: React.FC = () => {
    const [reportItems, setReportItems] = useState<ModelOverlayReportItem[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [teams, setTeams] = useState<Team[]>([]);
    const [riskTiers, setRiskTiers] = useState<RiskTier[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [selectedRegionId, setSelectedRegionId] = useState<string>('');
    const [selectedTeamId, setSelectedTeamId] = useState<string>('');
    const [selectedRiskTier, setSelectedRiskTier] = useState<string>('');
    const [selectedOverlayKind, setSelectedOverlayKind] = useState<string>('');
    const [includePendingDecommission, setIncludePendingDecommission] = useState(false);

    const { sortedData, requestSort, getSortIcon } = useTableSort<ModelOverlayReportItem>(
        reportItems,
        'model_name'
    );

    const fetchRegions = async () => {
        try {
            const response = await api.get('/regions/');
            setRegions(response.data);
        } catch (err) {
            console.error('Failed to fetch regions:', err);
        }
    };

    const fetchTeams = async () => {
        try {
            const response = await api.get('/teams/');
            setTeams(response.data);
        } catch (err) {
            console.error('Failed to fetch teams:', err);
        }
    };

    const fetchRiskTiers = async () => {
        try {
            const response = await api.get('/taxonomies/by-names/?names=Model%20Risk%20Tier');
            const taxonomies = response.data || [];
            const riskTierTax = taxonomies.find((tax: { name: string }) => tax.name === 'Model Risk Tier');
            const values = riskTierTax?.values || [];
            setRiskTiers(values.filter((v: RiskTier) => v.is_active));
        } catch (err) {
            console.error('Failed to fetch risk tiers:', err);
        }
    };

    const fetchReport = async () => {
        try {
            setLoading(true);
            setError(null);
            const params: {
                region_id?: number;
                team_id?: number;
                risk_tier?: string;
                overlay_kind?: OverlayKind;
                include_pending_decommission?: boolean;
            } = {};

            if (selectedRegionId) params.region_id = Number(selectedRegionId);
            if (selectedTeamId === 'unassigned') {
                params.team_id = 0;
            } else if (selectedTeamId) {
                params.team_id = Number(selectedTeamId);
            }
            if (selectedRiskTier) params.risk_tier = selectedRiskTier;
            if (selectedOverlayKind) params.overlay_kind = selectedOverlayKind as OverlayKind;
            if (includePendingDecommission) params.include_pending_decommission = true;

            const data = await getModelOverlaysReport(params);
            setReportItems(data.items);
        } catch (err) {
            console.error('Failed to fetch report:', err);
            setError('Failed to load model overlays report');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRegions();
        fetchTeams();
        fetchRiskTiers();
    }, []);

    useEffect(() => {
        fetchReport();
    }, [selectedRegionId, selectedTeamId, selectedRiskTier, selectedOverlayKind, includePendingDecommission]);

    const exportToCSV = () => {
        if (sortedData.length === 0) return;
        const headers = [
            'Overlay ID',
            'Model ID',
            'Model Name',
            'Model Status',
            'Risk Tier',
            'Team',
            'Kind',
            'Region',
            'Effective From',
            'Effective To',
            'Description',
            'Rationale',
            'Evidence',
            'Monitoring Traceability',
            'Monitoring Result ID',
            'Monitoring Cycle ID',
            'Recommendation ID',
            'Limitation ID',
        ];

        const rows = sortedData.map((item) => [
            item.overlay_id,
            item.model_id,
            `"${item.model_name.replace(/"/g, '""')}"`,
            item.model_status,
            item.risk_tier || '',
            item.team_name || '',
            item.overlay_kind === 'OVERLAY' ? 'Overlay' : 'Management Judgement',
            item.region_name || 'Global',
            formatDate(item.effective_from),
            formatDate(item.effective_to),
            `"${item.description.replace(/"/g, '""')}"`,
            `"${item.rationale.replace(/"/g, '""')}"`,
            `"${(item.evidence_description || '').replace(/"/g, '""')}"`,
            item.has_monitoring_traceability ? 'Yes' : 'No',
            item.trigger_monitoring_result_id || '',
            item.trigger_monitoring_cycle_id || '',
            item.related_recommendation_id || '',
            item.related_limitation_id || '',
        ]);

        const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `model_overlays_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const uniqueModels = useMemo(() => new Set(reportItems.map(i => i.model_id)).size, [reportItems]);
    const withTraceability = reportItems.filter(i => i.has_monitoring_traceability).length;
    const regionalCount = reportItems.filter(i => i.region_name).length;

    return (
        <Layout>
            <div className="p-6">
                <div className="mb-6 flex justify-between items-start">
                    <div>
                        <Link
                            to="/reports"
                            className="text-blue-600 hover:text-blue-800 text-sm mb-2 inline-block"
                        >
                            &larr; Back to Reports
                        </Link>
                        <h2 className="text-2xl font-bold text-gray-900">Model Overlays &amp; Judgements Report</h2>
                        <p className="mt-1 text-sm text-gray-600">
                            Current underperformance-related overlays and management judgements for active models.
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
                            disabled={sortedData.length === 0}
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm disabled:opacity-50"
                        >
                            Export CSV
                        </button>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-md p-4 mb-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                        <div>
                            <label htmlFor="overlay-report-region" className="block text-sm font-medium text-gray-700 mb-1">Region</label>
                            <select
                                id="overlay-report-region"
                                value={selectedRegionId}
                                onChange={(e) => setSelectedRegionId(e.target.value)}
                                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                            >
                                <option value="">All Regions</option>
                                {regions.map((region) => (
                                    <option key={region.region_id} value={region.region_id}>
                                        {region.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label htmlFor="overlay-report-team" className="block text-sm font-medium text-gray-700 mb-1">Team</label>
                            <select
                                id="overlay-report-team"
                                value={selectedTeamId}
                                onChange={(e) => setSelectedTeamId(e.target.value)}
                                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                            >
                                <option value="">All Teams</option>
                                <option value="unassigned">Unassigned</option>
                                {teams.map((team) => (
                                    <option key={team.team_id} value={team.team_id}>
                                        {team.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label htmlFor="overlay-report-risk-tier" className="block text-sm font-medium text-gray-700 mb-1">Risk Tier</label>
                            <select
                                id="overlay-report-risk-tier"
                                value={selectedRiskTier}
                                onChange={(e) => setSelectedRiskTier(e.target.value)}
                                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                            >
                                <option value="">All Tiers</option>
                                {riskTiers.map((tier) => (
                                    <option key={tier.value_id} value={tier.code}>
                                        {tier.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label htmlFor="overlay-report-kind" className="block text-sm font-medium text-gray-700 mb-1">Overlay Kind</label>
                            <select
                                id="overlay-report-kind"
                                value={selectedOverlayKind}
                                onChange={(e) => setSelectedOverlayKind(e.target.value)}
                                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                            >
                                <option value="">All Kinds</option>
                                <option value="OVERLAY">Overlay</option>
                                <option value="MANAGEMENT_JUDGEMENT">Management Judgement</option>
                            </select>
                        </div>
                        <div className="flex items-center gap-2 mt-6">
                            <input
                                type="checkbox"
                                checked={includePendingDecommission}
                                onChange={(e) => setIncludePendingDecommission(e.target.checked)}
                                className="rounded border-gray-300"
                            />
                            <span className="text-sm text-gray-700">Include Pending Decommission</span>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-white rounded-lg shadow-md p-4">
                        <h4 className="text-sm font-medium text-gray-500">Total Overlays</h4>
                        <p className="text-3xl font-bold text-blue-600 mt-1">{reportItems.length}</p>
                    </div>
                    <div className="bg-white rounded-lg shadow-md p-4">
                        <h4 className="text-sm font-medium text-gray-500">Unique Models</h4>
                        <p className="text-3xl font-bold text-gray-700 mt-1">{uniqueModels}</p>
                    </div>
                    <div className="bg-white rounded-lg shadow-md p-4">
                        <h4 className="text-sm font-medium text-gray-500">With Monitoring Traceability</h4>
                        <p className="text-3xl font-bold text-green-700 mt-1">{withTraceability}</p>
                    </div>
                    <div className="bg-white rounded-lg shadow-md p-4">
                        <h4 className="text-sm font-medium text-gray-500">Regional Overlays</h4>
                        <p className="text-3xl font-bold text-purple-700 mt-1">{regionalCount}</p>
                    </div>
                </div>

                {error && (
                    <div className="bg-red-100 text-red-800 p-4 rounded-lg mb-6">
                        {error}
                    </div>
                )}

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
                        <p className="mt-4 text-lg text-gray-600">No Overlays Found</p>
                        <p className="mt-2 text-sm text-gray-500">
                            Try adjusting your filters or confirm overlays have been recorded.
                        </p>
                    </div>
                ) : (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th
                                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('model_name')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Model
                                                {getSortIcon('model_name')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('model_status')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Status
                                                {getSortIcon('model_status')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('risk_tier')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Risk Tier
                                                {getSortIcon('risk_tier')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('team_name')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Team
                                                {getSortIcon('team_name')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('overlay_kind')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Kind
                                                {getSortIcon('overlay_kind')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('region_name')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Region
                                                {getSortIcon('region_name')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('effective_from')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Effective
                                                {getSortIcon('effective_from')}
                                            </div>
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Description
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Traceability
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {sortedData.map((item) => (
                                        <tr key={item.overlay_id}>
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                <Link
                                                    to={`/models/${item.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline"
                                                >
                                                    {item.model_name}
                                                </Link>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {item.model_status}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {item.risk_tier || 'Unassigned'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {item.team_name || 'Unassigned'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {item.overlay_kind === 'OVERLAY' ? 'Overlay' : 'Management Judgement'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {item.region_name || 'Global'}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {formatDate(item.effective_from)}
                                                <div className="text-xs text-gray-500">
                                                    to {item.effective_to ? formatDate(item.effective_to) : 'Open-ended'}
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                <div className="font-medium">{item.description}</div>
                                                <div className="text-xs text-gray-500 mt-1">Rationale: {item.rationale}</div>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-700">
                                                {item.has_monitoring_traceability ? 'Linked' : 'None'}
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

export default ModelOverlaysReportPage;

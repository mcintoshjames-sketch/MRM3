import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import client from '../api/client';
import { getTeams, Team as TeamOption } from '../api/teams';

interface RegionalDeploymentRecord {
    region_code: string;
    region_name: string;
    requires_regional_approval: boolean;
    model_id: number;
    model_name: string;
    deployed_version: string | null;
    deployment_date: string | null;
    deployment_notes: string | null;
    validation_request_id: number | null;
    validation_status: string | null;
    validation_status_code: string | null;
    validation_completion_date: string | null;
    has_regional_approval: boolean;
    regional_approver_name: string | null;
    regional_approver_role: string | null;
    regional_approval_status: string | null;
    regional_approval_date: string | null;
    is_deployed_without_validation: boolean;
    is_validation_pending: boolean;
    is_validation_approved: boolean;
}

interface RegionalComplianceReportResponse {
    report_generated_at: string;
    region_filter: string | null;
    team_filter?: string | null;
    total_records: number;
    records: RegionalDeploymentRecord[];
}

const RegionalComplianceReportPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [reportData, setReportData] = useState<RegionalComplianceReportResponse | null>(null);
    const [regionFilter, setRegionFilter] = useState<string>('');
    const [teamFilter, setTeamFilter] = useState<string>('');
    const [onlyDeployed, setOnlyDeployed] = useState(true);
    const [availableRegions, setAvailableRegions] = useState<{code: string, name: string}[]>([]);
    const [teams, setTeams] = useState<TeamOption[]>([]);

    useEffect(() => {
        fetchRegions();
        getTeams().then((res) => setTeams(res.data)).catch(console.error);
    }, []);

    useEffect(() => {
        fetchReport();
    }, [regionFilter, teamFilter, onlyDeployed]);

    const fetchRegions = async () => {
        try {
            const response = await client.get('/regions/');
            setAvailableRegions(response.data);
        } catch (error) {
            console.error('Failed to fetch regions:', error);
        }
    };

    const fetchReport = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (regionFilter) params.append('region_code', regionFilter);
            if (teamFilter === 'unassigned') {
                params.append('team_id', '0');
            } else if (teamFilter) {
                params.append('team_id', teamFilter);
            }
            params.append('only_deployed', String(onlyDeployed));

            const response = await client.get(
                `/regional-compliance-report/?${params.toString()}`
            );
            setReportData(response.data);
        } catch (error) {
            console.error('Failed to fetch report:', error);
        } finally {
            setLoading(false);
        }
    };

    const getStatusBadgeClass = (statusCode: string | null) => {
        if (!statusCode) return 'bg-gray-200 text-gray-800';
        switch (statusCode) {
            case 'APPROVED':
                return 'bg-green-100 text-green-800';
            case 'IN_PROGRESS':
                return 'bg-blue-100 text-blue-800';
            case 'PENDING_APPROVAL':
                return 'bg-yellow-100 text-yellow-800';
            case 'CANCELLED':
                return 'bg-gray-200 text-gray-800';
            default:
                return 'bg-gray-200 text-gray-800';
        }
    };

    const getComplianceStatusBadge = (record: RegionalDeploymentRecord) => {
        if (record.is_deployed_without_validation) {
            return (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    ⚠️ No Validation
                </span>
            );
        }
        if (record.is_validation_approved) {
            return (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    ✓ Validated
                </span>
            );
        }
        if (record.is_validation_pending) {
            return (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    ⏳ Pending
                </span>
            );
        }
        return (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                - Not Deployed
            </span>
        );
    };

    const exportToCsv = () => {
        if (!reportData || reportData.records.length === 0) return;

        const headers = [
            'Region Code',
            'Region Name',
            'Requires Regional Approval',
            'Model ID',
            'Model Name',
            'Deployed Version',
            'Deployment Date',
            'Validation Status',
            'Validation Completion Date',
            'Regional Approver',
            'Regional Approval Status',
            'Regional Approval Date',
            'Compliance Status'
        ];

        const rows = reportData.records.map(record => [
            record.region_code,
            record.region_name,
            record.requires_regional_approval ? 'Yes' : 'No',
            record.model_id,
            record.model_name,
            record.deployed_version || 'Not Deployed',
            record.deployment_date ? record.deployment_date.split('T')[0] : 'N/A',
            record.validation_status || 'N/A',
            record.validation_completion_date ? record.validation_completion_date.split('T')[0] : 'N/A',
            record.regional_approver_name || 'N/A',
            record.regional_approval_status || 'N/A',
            record.regional_approval_date ? record.regional_approval_date.split('T')[0] : 'N/A',
            record.is_deployed_without_validation ? 'No Validation' :
                record.is_validation_approved ? 'Validated' :
                    record.is_validation_pending ? 'Pending' : 'Not Deployed'
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `regional_compliance_report_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    if (loading && !reportData) {
        return (
            <Layout>
                <div className="flex justify-center items-center h-64">
                    <p className="text-gray-500">Loading report...</p>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex justify-between items-start">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">
                            Regional Deployment & Compliance Report
                        </h2>
                        <p className="text-sm text-gray-600 mt-1">
                            Regulatory report showing deployment status, validation, and approvals by region
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={exportToCsv}
                            className="btn-secondary"
                            disabled={!reportData || reportData.records.length === 0}
                        >
                            Export CSV
                        </button>
                        <button
                            onClick={fetchReport}
                            className="btn-primary"
                        >
                            Refresh Report
                        </button>
                    </div>
                </div>

                {/* Filters */}
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Filter by Region
                            </label>
                            <select
                                value={regionFilter}
                                onChange={(e) => setRegionFilter(e.target.value)}
                                className="input-field"
                            >
                                <option value="">All Regions</option>
                                {availableRegions.map((region) => (
                                    <option key={region.code} value={region.code}>
                                        {region.name} ({region.code})
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Filter by Team
                            </label>
                            <select
                                value={teamFilter}
                                onChange={(e) => setTeamFilter(e.target.value)}
                                className="input-field"
                            >
                                <option value="">All Teams</option>
                                <option value="unassigned">Unassigned</option>
                                {teams.filter(team => team.is_active).map((team) => (
                                    <option key={team.team_id} value={String(team.team_id)}>
                                        {team.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="flex items-end">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={onlyDeployed}
                                    onChange={(e) => setOnlyDeployed(e.target.checked)}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700">Show only deployed models</span>
                            </label>
                        </div>
                    </div>
                </div>

                {/* Report Summary */}
                {reportData && (
                    <div className="bg-white p-4 rounded-lg shadow-md">
                        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                            <div>
                                <p className="text-sm text-gray-600">Report Generated</p>
                                <p className="text-lg font-semibold">
                                    {new Date(reportData.report_generated_at).toLocaleString()}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">Total Records</p>
                                <p className="text-lg font-semibold">{reportData.total_records}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">Region Filter</p>
                                <p className="text-lg font-semibold">
                                    {reportData.region_filter || 'All Regions'}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">Team Filter</p>
                                <p className="text-lg font-semibold">
                                    {reportData.team_filter || 'All Teams'}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">Deployed Models</p>
                                <p className="text-lg font-semibold">
                                    {reportData.records.filter(r => r.deployed_version).length}
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Report Table */}
                <div className="bg-white rounded-lg shadow-md overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Region
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Model
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Deployed Version
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Deployment Date
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Validation Status
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Date Validated
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Regional Approval
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Compliance
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {reportData && reportData.records.length === 0 ? (
                                    <tr>
                                        <td colSpan={8} className="px-6 py-4 text-center text-gray-500">
                                            No records found. Try adjusting your filters.
                                        </td>
                                    </tr>
                                ) : (
                                    reportData?.records.map((record, index) => (
                                        <tr key={index} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-medium text-gray-900">
                                                        {record.region_code}
                                                    </span>
                                                    <span className="text-xs text-gray-500">
                                                        {record.region_name}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <a
                                                    href={`/models/${record.model_id}`}
                                                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                                                >
                                                    {record.model_name}
                                                </a>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="text-sm text-gray-900">
                                                    {record.deployed_version || (
                                                        <span className="text-gray-400">Not deployed</span>
                                                    )}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {record.deployment_date
                                                    ? record.deployment_date.split('T')[0]
                                                    : '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {record.validation_status ? (
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(record.validation_status_code)}`}>
                                                        {record.validation_status}
                                                    </span>
                                                ) : (
                                                    <span className="text-sm text-gray-400">No validation</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {record.validation_completion_date
                                                    ? record.validation_completion_date.split('T')[0]
                                                    : '-'}
                                            </td>
                                            <td className="px-6 py-4">
                                                {record.requires_regional_approval ? (
                                                    record.has_regional_approval ? (
                                                        <div className="space-y-1">
                                                            <div className={`text-xs font-medium px-2 py-1 rounded ${
                                                                record.regional_approval_status === 'Approved'
                                                                    ? 'text-green-800 bg-green-50'
                                                                    : record.regional_approval_status === 'Rejected'
                                                                    ? 'text-red-800 bg-red-50'
                                                                    : 'text-yellow-800 bg-yellow-50'
                                                            }`}>
                                                                {record.regional_approval_status}
                                                            </div>
                                                            <div className="text-xs text-gray-600">
                                                                {record.regional_approver_name}
                                                                {record.regional_approver_role && (
                                                                    <span className="text-gray-500"> ({record.regional_approver_role})</span>
                                                                )}
                                                            </div>
                                                            {record.regional_approval_date && (
                                                                <div className="text-xs text-gray-500">
                                                                    {record.regional_approval_date.split('T')[0]}
                                                                </div>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <span className="text-sm text-gray-400">No approval yet</span>
                                                    )
                                                ) : (
                                                    <span className="text-sm text-gray-400">Not required</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {getComplianceStatusBadge(record)}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default RegionalComplianceReportPage;

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface OverdueModel {
    model_id: number;
    model_name: string;
    risk_tier: string | null;
    owner_name: string;
    last_validation_date: string | null;
    next_due_date: string | null;
    days_overdue: number | null;
    status: string;
}

interface PassWithFindingsValidation {
    validation_id: number;
    model_id: number;
    model_name: string;
    validation_date: string;
    validator_name: string;
    findings_summary: string | null;
    has_recommendations: boolean;
}

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

export default function AdminDashboardPage() {
    const { user } = useAuth();
    const [overdueModels, setOverdueModels] = useState<OverdueModel[]>([]);
    const [passWithFindings, setPassWithFindings] = useState<PassWithFindingsValidation[]>([]);
    const [slaViolations, setSlaViolations] = useState<SLAViolation[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            const [overdueRes, findingsRes, violationsRes] = await Promise.all([
                api.get('/validations/dashboard/overdue'),
                api.get('/validations/dashboard/pass-with-findings'),
                api.get('/validation-workflow/dashboard/sla-violations')
            ]);
            setOverdueModels(overdueRes.data);
            setPassWithFindings(findingsRes.data);
            setSlaViolations(violationsRes.data);
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatTimeAgo = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
        return `${Math.floor(diffDays / 30)} months ago`;
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="mb-6">
                <h2 className="text-2xl font-bold">Admin Dashboard</h2>
                <p className="text-gray-600 mt-1">Welcome back, {user?.full_name}</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">SLA Violations</h3>
                    <p className="text-3xl font-bold text-red-600 mt-2">{slaViolations.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Active workflow delays</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Overdue Validations</h3>
                    <p className="text-3xl font-bold text-orange-600 mt-2">{overdueModels.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Models requiring validation</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Pass with Findings</h3>
                    <p className="text-3xl font-bold text-yellow-600 mt-2">
                        {passWithFindings.filter(v => !v.has_recommendations).length}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">Need recommendations</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Quick Actions</h3>
                    <div className="mt-2 space-y-1">
                        <Link to="/validation-workflow" className="block text-blue-600 hover:text-blue-800 text-xs">
                            View All Validations &rarr;
                        </Link>
                        <Link to="/workflow-config" className="block text-blue-600 hover:text-blue-800 text-xs">
                            Configure Workflow SLA &rarr;
                        </Link>
                    </div>
                </div>
            </div>

            {/* SLA Violations Feed */}
            {slaViolations.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">SLA Violation Alerts</h3>
                        <span className="text-xs text-gray-500 ml-auto">{slaViolations.length} active</span>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {slaViolations.slice(0, 5).map((violation, index) => (
                            <div
                                key={`${violation.request_id}-${index}`}
                                className="border-l-3 pl-3 py-2 hover:bg-gray-50 rounded-r"
                                style={{
                                    borderLeftWidth: '3px',
                                    borderLeftColor: violation.severity === 'critical' ? '#dc2626' :
                                                    violation.severity === 'high' ? '#ea580c' : '#ca8a04'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${
                                                violation.severity === 'critical' ? 'bg-red-100 text-red-700' :
                                                violation.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                                                'bg-yellow-100 text-yellow-700'
                                            }`}>
                                                {violation.severity}
                                            </span>
                                            <span className="text-xs text-gray-400">{formatTimeAgo(violation.timestamp)}</span>
                                        </div>
                                        <Link
                                            to={`/validation-workflow/${violation.request_id}`}
                                            className="text-sm font-medium text-gray-800 hover:text-blue-600 truncate block"
                                        >
                                            {violation.model_name}
                                        </Link>
                                        <p className="text-xs text-gray-600 mt-0.5">
                                            {violation.violation_type}: {violation.days_overdue}d overdue
                                            <span className="text-gray-400 ml-1">(SLA: {violation.sla_days}d)</span>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    {slaViolations.length > 5 && (
                        <div className="mt-3 pt-2 border-t text-center">
                            <Link
                                to="/validation-workflow"
                                className="text-xs text-blue-600 hover:text-blue-800"
                            >
                                View all {slaViolations.length} violations &rarr;
                            </Link>
                        </div>
                    )}
                </div>
            )}

            {/* Overdue Validations Table */}
            <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                <h3 className="text-lg font-bold mb-4">
                    Models Overdue for Validation ({overdueModels.length})
                </h3>
                {overdueModels.length === 0 ? (
                    <p className="text-gray-500">No models are currently overdue for validation.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Model Name
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Risk Tier
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Owner
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Last Validation
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Status
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {overdueModels.map((model) => (
                                    <tr key={model.model_id}>
                                        <td className="px-4 py-3 whitespace-nowrap font-medium">
                                            <Link
                                                to={`/models/${model.model_id}`}
                                                className="text-blue-600 hover:text-blue-800"
                                            >
                                                {model.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            {model.risk_tier ? (
                                                <span className="px-2 py-1 text-xs rounded bg-orange-100 text-orange-800">
                                                    {model.risk_tier}
                                                </span>
                                            ) : (
                                                <span className="text-gray-400">-</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {model.owner_name}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {model.last_validation_date || 'Never'}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${
                                                model.status === 'Never Validated'
                                                    ? 'bg-red-100 text-red-800'
                                                    : 'bg-orange-100 text-orange-800'
                                            }`}>
                                                {model.status}
                                                {model.days_overdue && ` (${model.days_overdue} days)`}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/validations/new?model_id=${model.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                Create Validation
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Pass with Findings Table */}
            <div className="bg-white p-6 rounded-lg shadow-md">
                <h3 className="text-lg font-bold mb-4">
                    Validations with Findings ({passWithFindings.length})
                </h3>
                {passWithFindings.length === 0 ? (
                    <p className="text-gray-500">No validations with findings requiring attention.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Model
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Validation Date
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Validator
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Findings Summary
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Recommendations
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {passWithFindings.map((validation) => (
                                    <tr key={validation.validation_id}>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/models/${validation.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                {validation.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {validation.validation_date}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {validation.validator_name}
                                        </td>
                                        <td className="px-4 py-3 text-sm max-w-md">
                                            <div className="truncate">
                                                {validation.findings_summary || 'No summary provided'}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            {validation.has_recommendations ? (
                                                <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">
                                                    Has Recommendations
                                                </span>
                                            ) : (
                                                <span className="px-2 py-1 text-xs rounded bg-red-100 text-red-800">
                                                    No Recommendations
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </Layout>
    );
}

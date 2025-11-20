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

interface OutOfOrderValidation {
    request_id: number;
    model_name: string;
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

interface PendingAssignment {
    request_id: number;
    model_id: number;
    model_name: string;
    requestor_name: string;
    validation_type: string;
    priority: string;
    region: string;
    request_date: string;
    target_completion_date: string | null;
    days_pending: number;
    severity: string;
}

interface OverdueSubmission {
    request_id: number;
    model_id: number;
    model_name: string;
    model_owner: string;
    submission_due_date: string;
    grace_period_end: string;
    days_overdue: number;
    validation_due_date: string;
    submission_status: string;
}

interface OverdueValidation {
    request_id: number;
    model_id: number;
    model_name: string;
    model_owner: string;
    submission_received_date: string | null;
    model_validation_due_date: string;
    days_overdue: number;
    current_status: string;
    model_compliance_status: string;
}

interface UpcomingRevalidation {
    model_id: number;
    model_name: string;
    model_owner: string;
    risk_tier: string | null;
    status: string;
    last_validation_date: string;
    next_submission_due: string;
    next_validation_due: string;
    days_until_submission_due: number;
    days_until_validation_due: number;
}

export default function AdminDashboardPage() {
    const { user } = useAuth();
    const [overdueModels, setOverdueModels] = useState<OverdueModel[]>([]);
    const [passWithFindings, setPassWithFindings] = useState<PassWithFindingsValidation[]>([]);
    const [slaViolations, setSlaViolations] = useState<SLAViolation[]>([]);
    const [outOfOrder, setOutOfOrder] = useState<OutOfOrderValidation[]>([]);
    const [pendingAssignments, setPendingAssignments] = useState<PendingAssignment[]>([]);
    const [overdueSubmissions, setOverdueSubmissions] = useState<OverdueSubmission[]>([]);
    const [overdueValidations, setOverdueValidations] = useState<OverdueValidation[]>([]);
    const [upcomingRevalidations, setUpcomingRevalidations] = useState<UpcomingRevalidation[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            const [
                overdueRes,
                findingsRes,
                violationsRes,
                outOfOrderRes,
                pendingRes,
                overdueSubmissionsRes,
                overdueValidationsRes,
                upcomingRevalidationsRes
            ] = await Promise.all([
                api.get('/validations/dashboard/overdue'),
                api.get('/validations/dashboard/pass-with-findings'),
                api.get('/validation-workflow/dashboard/sla-violations'),
                api.get('/validation-workflow/dashboard/out-of-order'),
                api.get('/validation-workflow/dashboard/pending-assignments'),
                api.get('/validation-workflow/dashboard/overdue-submissions'),
                api.get('/validation-workflow/dashboard/overdue-validations'),
                api.get('/validation-workflow/dashboard/upcoming-revalidations?days_ahead=90')
            ]);
            setOverdueModels(overdueRes.data);
            setPassWithFindings(findingsRes.data);
            setSlaViolations(violationsRes.data);
            setOutOfOrder(outOfOrderRes.data);
            setPendingAssignments(pendingRes.data);
            setOverdueSubmissions(overdueSubmissionsRes.data);
            setOverdueValidations(overdueValidationsRes.data);
            setUpcomingRevalidations(upcomingRevalidationsRes.data);
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
            <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-6">
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Pending Assignment</h3>
                    <p className="text-3xl font-bold text-blue-600 mt-2">{pendingAssignments.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Awaiting validator</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Lead Time Violations</h3>
                    <p className="text-3xl font-bold text-red-600 mt-2">{slaViolations.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Validation team SLA exceeded</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Out of Order</h3>
                    <p className="text-3xl font-bold text-purple-600 mt-2">{outOfOrder.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Validation after production</p>
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

            {/* Pending Validator Assignments Feed */}
            {pendingAssignments.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">Pending Validator Assignments</h3>
                        <span className="text-xs text-gray-500 ml-auto">{pendingAssignments.length} awaiting</span>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {pendingAssignments.slice(0, 5).map((item, index) => (
                            <div
                                key={`${item.request_id}-${index}`}
                                className="border-l-3 pl-3 py-2 hover:bg-gray-50 rounded-r"
                                style={{
                                    borderLeftWidth: '3px',
                                    borderLeftColor: item.severity === 'critical' ? '#2563eb' :
                                                    item.severity === 'high' ? '#3b82f6' : '#60a5fa'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${
                                                item.severity === 'critical' ? 'bg-blue-100 text-blue-700' :
                                                item.severity === 'high' ? 'bg-blue-50 text-blue-600' :
                                                'bg-blue-50 text-blue-500'
                                            }`}>
                                                {item.priority}
                                            </span>
                                            <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700">
                                                {item.region}
                                            </span>
                                            <span className="text-xs text-gray-400">
                                                {item.days_pending}d pending
                                            </span>
                                        </div>
                                        <Link
                                            to={`/validation-workflow/${item.request_id}`}
                                            className="text-sm font-medium text-gray-800 hover:text-blue-600 truncate block"
                                        >
                                            {item.model_name}
                                        </Link>
                                        <p className="text-xs text-gray-600 mt-0.5">
                                            {item.validation_type} • Requested by {item.requestor_name}
                                        </p>
                                        {item.target_completion_date && (
                                            <p className="text-xs text-gray-500">
                                                Target: {new Date(item.target_completion_date).toLocaleDateString()}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex-shrink-0">
                                        <Link
                                            to={`/validation-workflow/${item.request_id}?assignValidator=true`}
                                            className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors"
                                        >
                                            Assign Validator
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    {pendingAssignments.length > 5 && (
                        <div className="mt-3 pt-2 border-t text-center">
                            <Link
                                to="/validation-workflow?status=Intake"
                                className="text-xs text-blue-600 hover:text-blue-800"
                            >
                                View all {pendingAssignments.length} pending assignments &rarr;
                            </Link>
                        </div>
                    )}
                </div>
            )}

            {/* Validation Team SLA Violations Feed */}
            {slaViolations.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">Validation Team Lead Time Violations</h3>
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
                                            Submitted {formatTimeAgo(violation.timestamp)} • {violation.days_overdue}d past lead time
                                            <span className="text-gray-400 ml-1">(Lead time: {violation.sla_days}d)</span>
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

            {/* Out-of-Order Validations Feed */}
            {outOfOrder.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">Out-of-Order Validation Alerts</h3>
                        <span className="text-xs text-gray-500 ml-auto">{outOfOrder.length} active</span>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {outOfOrder.slice(0, 5).map((item, index) => (
                            <div
                                key={`${item.request_id}-${index}`}
                                className="border-l-3 pl-3 py-2 hover:bg-gray-50 rounded-r"
                                style={{
                                    borderLeftWidth: '3px',
                                    borderLeftColor: item.severity === 'critical' ? '#9333ea' :
                                                    item.severity === 'high' ? '#a855f7' : '#c084fc'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${
                                                item.severity === 'critical' ? 'bg-purple-100 text-purple-700' :
                                                item.severity === 'high' ? 'bg-purple-50 text-purple-600' :
                                                'bg-purple-50 text-purple-500'
                                            }`}>
                                                {item.severity}
                                            </span>
                                            {item.is_interim && (
                                                <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-yellow-100 text-yellow-800">
                                                    INTERIM
                                                </span>
                                            )}
                                        </div>
                                        <Link
                                            to={`/validation-workflow/${item.request_id}`}
                                            className="text-sm font-medium text-gray-800 hover:text-blue-600 truncate block"
                                        >
                                            {item.model_name} - v{item.version_number}
                                        </Link>
                                        <p className="text-xs text-gray-600 mt-0.5">
                                            Target completion: {new Date(item.target_completion_date).toLocaleDateString()}
                                            <span className="text-red-600 font-medium ml-1">
                                                ({item.days_gap}d after production)
                                            </span>
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            Production date: {new Date(item.production_date).toLocaleDateString()}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    {outOfOrder.length > 5 && (
                        <div className="mt-3 pt-2 border-t text-center">
                            <Link
                                to="/validation-workflow"
                                className="text-xs text-blue-600 hover:text-blue-800"
                            >
                                View all {outOfOrder.length} out-of-order validations &rarr;
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

            {/* Revalidation Lifecycle Widgets */}
            <div className="mt-8 space-y-6">
                {/* Overdue Submissions */}
                {overdueSubmissions.length > 0 && (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-red-50">
                            <div className="flex items-center">
                                <svg className="h-5 w-5 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                <h3 className="text-lg font-bold text-red-900">
                                    Overdue Revalidation Submissions ({overdueSubmissions.length})
                                </h3>
                            </div>
                            <p className="text-sm text-red-700 ml-7">Models with overdue documentation submissions (past grace period)</p>
                        </div>
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submission Due</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Grace Period End</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Overdue</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation Due</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {overdueSubmissions.map((submission) => (
                                    <tr key={submission.request_id} className="hover:bg-red-50">
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/models/${submission.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                {submission.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{submission.model_owner}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{submission.submission_due_date}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{submission.grace_period_end}</td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800">
                                                {submission.days_overdue} days
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{submission.validation_due_date}</td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/validation-workflow/${submission.request_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                View Request
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Overdue Validations */}
                {overdueValidations.length > 0 && (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-orange-50">
                            <div className="flex items-center">
                                <svg className="h-5 w-5 text-orange-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                                <h3 className="text-lg font-bold text-orange-900">
                                    Overdue Validations ({overdueValidations.length})
                                </h3>
                            </div>
                            <p className="text-sm text-orange-700 ml-7">Models with overdue validations (past model validation due date)</p>
                        </div>
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submission Received</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation Due</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Overdue</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {overdueValidations.map((validation) => (
                                    <tr key={validation.request_id} className="hover:bg-orange-50">
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/models/${validation.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                {validation.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{validation.model_owner}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {validation.submission_received_date || <span className="text-gray-400">Not received</span>}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{validation.model_validation_due_date}</td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className="px-2 py-1 text-xs font-semibold rounded bg-orange-100 text-orange-800">
                                                {validation.days_overdue} days
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{validation.current_status}</td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/validation-workflow/${validation.request_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                View Request
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Upcoming Revalidations */}
                {upcomingRevalidations.length > 0 && (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-blue-50">
                            <div className="flex items-center">
                                <svg className="h-5 w-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                                </svg>
                                <h3 className="text-lg font-bold text-blue-900">
                                    Upcoming Revalidations ({upcomingRevalidations.length})
                                </h3>
                            </div>
                            <p className="text-sm text-blue-700 ml-7">Models with revalidations due in the next 90 days</p>
                        </div>
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Validation</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submission Due</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation Due</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Until Due</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {upcomingRevalidations.slice(0, 10).map((revalidation) => (
                                    <tr key={revalidation.model_id} className="hover:bg-blue-50">
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/models/${revalidation.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                {revalidation.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{revalidation.model_owner}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{revalidation.risk_tier}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{revalidation.last_validation_date}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{revalidation.next_submission_due}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{revalidation.next_validation_due}</td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${
                                                revalidation.days_until_submission_due < 30 ? 'bg-yellow-100 text-yellow-800' :
                                                revalidation.days_until_submission_due < 60 ? 'bg-blue-100 text-blue-800' :
                                                'bg-gray-100 text-gray-800'
                                            }`}>
                                                {revalidation.days_until_submission_due} days
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {upcomingRevalidations.length > 10 && (
                            <div className="p-3 bg-gray-50 text-sm text-gray-600 text-center">
                                Showing first 10 of {upcomingRevalidations.length} upcoming revalidations
                            </div>
                        )}
                    </div>
                )}
            </div>
        </Layout>
    );
}

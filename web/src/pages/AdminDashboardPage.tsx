import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

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
    urgency: string;
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

interface PendingModelSubmission {
    model_id: number;
    model_name: string;
    description: string | null;
    development_type: string;
    owner: { full_name: string };
    submitted_by_user: { full_name: string };
    submitted_at: string;
    row_approval_status: string;
}

interface PendingConditionalApproval {
    request_id: number;
    model_id: number;
    model_name: string;
    validation_type: string;
    pending_approver_roles: Array<{
        approval_id: number;
        approver_role_id: number;
        approver_role_name: string;
        days_pending: number;
    }>;
    days_pending: number;
    created_at: string;
}

export default function AdminDashboardPage() {
    const { user } = useAuth();
    const [slaViolations, setSlaViolations] = useState<SLAViolation[]>([]);
    const [outOfOrder, setOutOfOrder] = useState<OutOfOrderValidation[]>([]);
    const [pendingAssignments, setPendingAssignments] = useState<PendingAssignment[]>([]);
    const [overdueSubmissions, setOverdueSubmissions] = useState<OverdueSubmission[]>([]);
    const [overdueValidations, setOverdueValidations] = useState<OverdueValidation[]>([]);
    const [upcomingRevalidations, setUpcomingRevalidations] = useState<UpcomingRevalidation[]>([]);
    const [pendingModelSubmissions, setPendingModelSubmissions] = useState<PendingModelSubmission[]>([]);
    const [pendingConditionalApprovals, setPendingConditionalApprovals] = useState<PendingConditionalApproval[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            const [
                violationsRes,
                outOfOrderRes,
                pendingRes,
                overdueSubmissionsRes,
                overdueValidationsRes,
                upcomingRevalidationsRes,
                pendingModelsRes,
                conditionalApprovalsRes
            ] = await Promise.all([
                api.get('/validation-workflow/dashboard/sla-violations'),
                api.get('/validation-workflow/dashboard/out-of-order'),
                api.get('/validation-workflow/dashboard/pending-assignments'),
                api.get('/validation-workflow/dashboard/overdue-submissions'),
                api.get('/validation-workflow/dashboard/overdue-validations'),
                api.get('/validation-workflow/dashboard/upcoming-revalidations?days_ahead=90'),
                api.get('/models/pending-submissions'),
                api.get('/validation-workflow/dashboard/pending-conditional-approvals')
            ]);
            setSlaViolations(violationsRes.data);
            setOutOfOrder(outOfOrderRes.data);
            setPendingAssignments(pendingRes.data);
            setOverdueSubmissions(overdueSubmissionsRes.data);
            setOverdueValidations(overdueValidationsRes.data);
            setUpcomingRevalidations(upcomingRevalidationsRes.data);
            setPendingModelSubmissions(pendingModelsRes.data);
            setPendingConditionalApprovals(conditionalApprovalsRes.data);
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

            {/* New Model Records Awaiting Approval Widget */}
            {pendingModelSubmissions.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">New Model Records Awaiting Approval</h3>
                        <span className="text-xs text-gray-500 ml-auto">{pendingModelSubmissions.length} pending</span>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {pendingModelSubmissions.slice(0, 5).map((submission) => (
                            <div
                                key={submission.model_id}
                                className="border-l-3 pl-3 py-2 hover:bg-gray-50 rounded-r"
                                style={{
                                    borderLeftWidth: '3px',
                                    borderLeftColor: submission.row_approval_status === 'needs_revision' ? '#f59e0b' : '#10b981'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${
                                                submission.row_approval_status === 'needs_revision'
                                                    ? 'bg-yellow-100 text-yellow-700'
                                                    : 'bg-green-100 text-green-700'
                                            }`}>
                                                {submission.row_approval_status === 'needs_revision' ? 'Needs Revision' : 'New Record'}
                                            </span>
                                            <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700">
                                                {submission.development_type}
                                            </span>
                                            <span className="text-xs text-gray-400">
                                                {formatTimeAgo(submission.submitted_at)}
                                            </span>
                                        </div>
                                        <Link
                                            to={`/models/${submission.model_id}`}
                                            className="text-sm font-medium text-gray-800 hover:text-blue-600 truncate block"
                                        >
                                            {submission.model_name}
                                        </Link>
                                        <p className="text-xs text-gray-600 mt-0.5">
                                            Owner: {submission.owner.full_name} • Submitted by: {submission.submitted_by_user.full_name}
                                        </p>
                                        {submission.description && (
                                            <p className="text-xs text-gray-500 truncate mt-0.5">
                                                {submission.description}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex-shrink-0">
                                        <Link
                                            to={`/models/${submission.model_id}?review=true`}
                                            className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded transition-colors"
                                        >
                                            Review
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    {pendingModelSubmissions.length > 5 && (
                        <div className="mt-3 pt-2 border-t text-center">
                            <Link
                                to="/models?approval_status=pending"
                                className="text-xs text-blue-600 hover:text-blue-800"
                            >
                                View all {pendingModelSubmissions.length} pending records &rarr;
                            </Link>
                        </div>
                    )}
                </div>
            )}

            {/* Pending Conditional Approvals Widget */}
            {pendingConditionalApprovals.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">Pending Conditional Approvals</h3>
                        <span className="text-xs text-gray-500 ml-auto">{pendingConditionalApprovals.length} awaiting</span>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {pendingConditionalApprovals.slice(0, 5).map((item) => (
                            <div
                                key={item.request_id}
                                className="border-l-3 pl-3 py-2 hover:bg-gray-50 rounded-r"
                                style={{
                                    borderLeftWidth: '3px',
                                    borderLeftColor: item.days_pending > 14 ? '#9333ea' : item.days_pending > 7 ? '#a855f7' : '#c084fc'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${
                                                item.days_pending > 14 ? 'bg-purple-100 text-purple-700' :
                                                item.days_pending > 7 ? 'bg-purple-50 text-purple-600' :
                                                'bg-purple-50 text-purple-500'
                                            }`}>
                                                {item.validation_type}
                                            </span>
                                            <Link
                                                to={`/models/${item.model_id}`}
                                                className="text-xs font-medium text-gray-900 hover:text-blue-600 hover:underline truncate"
                                            >
                                                {item.model_name}
                                            </Link>
                                        </div>
                                        <div className="text-xs text-gray-600 space-y-0.5">
                                            {item.pending_approver_roles.map((role) => (
                                                <div key={role.approval_id} className="flex items-center gap-1">
                                                    <span className="text-purple-600 font-medium">{role.approver_role_name}</span>
                                                    <span className="text-gray-400">•</span>
                                                    <span>{role.days_pending} {role.days_pending === 1 ? 'day' : 'days'} pending</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="flex-shrink-0">
                                        <Link
                                            to={`/validation-workflow/${item.request_id}?tab=approvals`}
                                            className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-purple-600 hover:bg-purple-700 rounded transition-colors"
                                        >
                                            Approve
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    {pendingConditionalApprovals.length > 5 && (
                        <div className="mt-3 pt-2 border-t text-center">
                            <span className="text-xs text-gray-500">
                                Showing 5 of {pendingConditionalApprovals.length} pending approvals
                            </span>
                        </div>
                    )}
                </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-7 gap-4 mb-6">
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
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Pending Submissions</h3>
                    <p className="text-3xl font-bold text-orange-600 mt-2">{overdueSubmissions.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Past due date</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Overdue Validations</h3>
                    <p className="text-3xl font-bold text-red-600 mt-2">{overdueValidations.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Past validation due</p>
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
                                                Target: {item.target_completion_date.split('T')[0]}
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
                                            Target completion: {item.target_completion_date.split('T')[0]}
                                            <span className="text-red-600 font-medium ml-1">
                                                ({item.days_gap}d after production)
                                            </span>
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            Production date: {item.production_date.split('T')[0]}
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

            {/* Revalidation Lifecycle Widgets */}
            <div className="mt-8 space-y-6">
                {/* Pending and Overdue Submissions */}
                {overdueSubmissions.length > 0 && (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-orange-50">
                            <div className="flex items-center">
                                <svg className="h-5 w-5 text-orange-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                                <h3 className="text-lg font-bold text-orange-900">
                                    Pending and Overdue Revalidation Submissions ({overdueSubmissions.length})
                                </h3>
                            </div>
                            <p className="text-sm text-orange-700 ml-7">Models past submission due date (includes those in grace period and fully overdue)</p>
                        </div>
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submission Due</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Grace Period End</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Late</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation Due</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {overdueSubmissions.map((submission) => (
                                    <tr
                                        key={submission.request_id}
                                        className="hover:bg-orange-50"
                                    >
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${
                                                submission.urgency === 'overdue'
                                                    ? 'bg-red-100 text-red-800'
                                                    : 'bg-yellow-100 text-yellow-800'
                                            }`}>
                                                {submission.urgency === 'overdue' ? 'Overdue' : 'In Grace Period'}
                                            </span>
                                        </td>
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
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${
                                                submission.urgency === 'overdue'
                                                    ? 'bg-orange-100 text-orange-800'
                                                    : 'bg-blue-100 text-blue-800'
                                            }`}>
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
                        <div className="p-4 border-b bg-red-50">
                            <div className="flex items-center">
                                <svg className="h-5 w-5 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                <h3 className="text-lg font-bold text-red-900">
                                    Overdue Validations ({overdueValidations.length})
                                </h3>
                            </div>
                            <p className="text-sm text-red-700 ml-7">Models past their final validation due date</p>
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
                                    <tr key={validation.request_id} className="hover:bg-red-50">
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
                                            <span className="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800">
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

                {/* Upcoming Submissions */}
                {upcomingRevalidations.length > 0 && (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-blue-50">
                            <div className="flex items-center">
                                <svg className="h-5 w-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                                </svg>
                                <h3 className="text-lg font-bold text-blue-900">
                                    Upcoming Submissions ({upcomingRevalidations.length})
                                </h3>
                            </div>
                            <p className="text-sm text-blue-700 ml-7">Models with submissions due in the next 90 days</p>
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
                                Showing first 10 of {upcomingRevalidations.length} upcoming submissions
                            </div>
                        )}
                    </div>
                )}
            </div>
        </Layout>
    );
}

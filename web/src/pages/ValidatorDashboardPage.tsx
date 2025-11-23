import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface ValidationRequest {
    request_id: number;
    model_ids: number[];
    model_names: string[];
    request_date: string;
    requestor_name: string;
    validation_type: string;
    priority: string;
    target_completion_date: string;
    current_status: string;
    days_in_status: number;
    primary_validator: string | null;
    created_at: string;
    updated_at: string;
}

interface WorkflowSLA {
    sla_id: number;
    workflow_type: string;
    assignment_days: number;
    begin_work_days: number;
    complete_work_days: number;
    approval_days: number;
    created_at: string;
    updated_at: string;
}

interface ActivityItem {
    type: 'sent_back_review' | 'sent_back_approval' | 'approaching_deadline' | 'newly_assigned';
    request: ValidationRequest;
    message: string;
    severity: 'critical' | 'high' | 'medium';
    daysUntil?: number;
}

interface Assignment {
    assignment_id: number;
    request_id: number;
    validator: {
        user_id: number;
        full_name: string;
    };
    is_primary: boolean;
    is_reviewer: boolean;
    estimated_hours: number | null;
    actual_hours: number | null;
}

interface ReviewModalData {
    request_id: number;
    assignment_id: number;
    model_names: string[];
}

export default function ValidatorDashboardPage() {
    const { user } = useAuth();
    const [myAssignments, setMyAssignments] = useState<ValidationRequest[]>([]);
    const [myReviews, setMyReviews] = useState<ValidationRequest[]>([]);
    const [myReviewAssignments, setMyReviewAssignments] = useState<Map<number, number>>(new Map());
    const [pendingRequests, setPendingRequests] = useState<ValidationRequest[]>([]);
    const [workflowSLA, setWorkflowSLA] = useState<WorkflowSLA | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [claimingId, setClaimingId] = useState<number | null>(null);

    // Review modal state
    const [reviewModal, setReviewModal] = useState<ReviewModalData | null>(null);
    const [reviewComments, setReviewComments] = useState('');
    const [reviewLoading, setReviewLoading] = useState(false);
    const [reviewModalError, setReviewModalError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch all validation projects, detailed assignments, and SLA configuration
            const [requestsRes, assignmentsRes, slaRes] = await Promise.all([
                api.get('/validation-workflow/requests/'),
                api.get('/validation-workflow/assignments/'),
                api.get('/workflow-sla/validation')
            ]);

            const allRequests: ValidationRequest[] = requestsRes.data;
            const allAssignments: Assignment[] = assignmentsRes.data;
            setWorkflowSLA(slaRes.data);

            // Filter for my primary assignments
            const myWork = allRequests.filter(
                req => req.primary_validator === user?.full_name
            );
            setMyAssignments(myWork);

            // Filter for validations where I'm assigned as reviewer and status is REVIEW
            const myReviewerAssignments = allAssignments.filter(
                a => a.validator.user_id === user?.user_id && a.is_reviewer
            );
            const myReviewRequestIds = new Set(myReviewerAssignments.map(a => a.request_id));
            const reviewWork = allRequests.filter(
                req => myReviewRequestIds.has(req.request_id) && req.current_status === 'Review'
            );
            setMyReviews(reviewWork);

            // Create map of request_id to assignment_id for reviewer actions
            const reviewAssignmentMap = new Map<number, number>();
            myReviewerAssignments.forEach(a => {
                reviewAssignmentMap.set(a.request_id, a.assignment_id);
            });
            setMyReviewAssignments(reviewAssignmentMap);

            // Filter for pending requests (Intake/Planning) that are unassigned
            const pending = allRequests.filter(
                req => (req.current_status === 'Intake' || req.current_status === 'Planning') && !req.primary_validator
            );
            setPendingRequests(pending);

        } catch (err: any) {
            console.error('Failed to fetch dashboard data:', err);
            setError(err.response?.data?.detail || 'Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    };

    const claimRequest = async (requestId: number) => {
        if (!user) return;

        try {
            setClaimingId(requestId);
            setError(null);

            await api.post(`/validation-workflow/requests/${requestId}/assignments`, {
                validator_id: user.user_id,
                is_primary: true,
                independence_attestation: true
            });

            // Refresh data to show the request in my assignments
            await fetchData();
        } catch (err: any) {
            console.error('Failed to claim request:', err);
            setError(err.response?.data?.detail || 'Failed to claim validation project');
        } finally {
            setClaimingId(null);
        }
    };

    const openReviewModal = (req: ValidationRequest) => {
        const assignmentId = myReviewAssignments.get(req.request_id);
        if (!assignmentId) {
            setError('Assignment ID not found for this review');
            return;
        }

        setReviewModal({
            request_id: req.request_id,
            assignment_id: assignmentId,
            model_names: req.model_names
        });
        setReviewComments('');
        setReviewModalError(null); // Clear any previous modal errors
    };

    const handleReviewAction = async (action: 'sign-off' | 'send-back') => {
        if (!reviewModal) return;

        if (action === 'send-back' && !reviewComments.trim()) {
            setReviewModalError('Please provide comments when sending back for revisions');
            return;
        }

        try {
            setReviewLoading(true);
            setReviewModalError(null);

            const endpoint = action === 'sign-off'
                ? `/validation-workflow/assignments/${reviewModal.assignment_id}/sign-off`
                : `/validation-workflow/assignments/${reviewModal.assignment_id}/send-back`;

            await api.post(endpoint, {
                comments: reviewComments || null
            });

            // Success - close modal and refresh data
            setReviewModal(null);
            setReviewComments('');
            await fetchData();
        } catch (err: any) {
            console.error(`Failed to ${action}:`, err);
            // Display error within the modal - do NOT close it
            const errorMessage = err.response?.data?.detail || `Failed to ${action.replace('-', ' ')} review. Please try again.`;
            setReviewModalError(errorMessage);
        } finally {
            setReviewLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Intake': return 'bg-gray-100 text-gray-800';
            case 'Planning': return 'bg-blue-100 text-blue-800';
            case 'In Progress': return 'bg-yellow-100 text-yellow-800';
            case 'Review': return 'bg-purple-100 text-purple-800';
            case 'Pending Approval': return 'bg-orange-100 text-orange-800';
            case 'Approved': return 'bg-green-100 text-green-800';
            case 'On Hold': return 'bg-red-100 text-red-800';
            case 'Cancelled': return 'bg-gray-400 text-white';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'Critical': return 'bg-red-100 text-red-800';
            case 'High': return 'bg-orange-100 text-orange-800';
            case 'Medium': return 'bg-yellow-100 text-yellow-800';
            case 'Low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const activeAssignments = myAssignments.filter(
        req => !['Approved', 'Cancelled'].includes(req.current_status)
    );

    const completedAssignments = myAssignments.filter(
        req => req.current_status === 'Approved'
    );

    // Generate activity feed
    const getActivityFeed = (): ActivityItem[] => {
        const activities: ActivityItem[] = [];
        const now = new Date();

        myAssignments.forEach(req => {
            // Sent back from review
            if (req.current_status === 'In Progress' && req.days_in_status <= 3) {
                // Check if it was recently in review (approximate by checking if updated recently)
                const updatedAt = new Date(req.updated_at);
                const daysSinceUpdate = Math.floor((now.getTime() - updatedAt.getTime()) / (1000 * 60 * 60 * 24));

                if (daysSinceUpdate <= 3) {
                    activities.push({
                        type: 'sent_back_review',
                        request: req,
                        message: `Validation sent back for revisions`,
                        severity: 'critical'
                    });
                }
            }

            // Approaching deadlines (within 7 days)
            if (req.target_completion_date && !['Approved', 'Cancelled'].includes(req.current_status)) {
                const targetDate = new Date(req.target_completion_date);
                const daysUntil = Math.ceil((targetDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

                if (daysUntil >= 0 && daysUntil <= 7) {
                    activities.push({
                        type: 'approaching_deadline',
                        request: req,
                        message: `Target date in ${daysUntil} day${daysUntil !== 1 ? 's' : ''}`,
                        severity: daysUntil <= 2 ? 'critical' : daysUntil <= 5 ? 'high' : 'medium',
                        daysUntil
                    });
                } else if (daysUntil < 0) {
                    activities.push({
                        type: 'approaching_deadline',
                        request: req,
                        message: `OVERDUE by ${Math.abs(daysUntil)} day${Math.abs(daysUntil) !== 1 ? 's' : ''}`,
                        severity: 'critical',
                        daysUntil
                    });
                }
            }

            // Newly assigned (within last 3 days and still in Intake/Planning)
            if (req.current_status === 'Intake' || req.current_status === 'Planning') {
                const createdAt = new Date(req.created_at);
                const daysSinceCreated = Math.floor((now.getTime() - createdAt.getTime()) / (1000 * 60 * 60 * 24));

                if (daysSinceCreated <= 3) {
                    activities.push({
                        type: 'newly_assigned',
                        request: req,
                        message: `Newly assigned ${daysSinceCreated} day${daysSinceCreated !== 1 ? 's' : ''} ago`,
                        severity: 'medium'
                    });
                }
            }
        });

        // Sort by severity and then by days until
        return activities.sort((a, b) => {
            const severityOrder = { critical: 0, high: 1, medium: 2 };
            if (severityOrder[a.severity] !== severityOrder[b.severity]) {
                return severityOrder[a.severity] - severityOrder[b.severity];
            }
            if (a.type === 'approaching_deadline' && b.type === 'approaching_deadline') {
                return (a.daysUntil || 0) - (b.daysUntil || 0);
            }
            return 0;
        });
    };

    const activityFeed = getActivityFeed();

    // Calculate SLA time remaining for a validation request
    const calculateSLARemaining = (req: ValidationRequest): {
        daysRemaining: number;
        severity: 'ok' | 'warning' | 'critical';
        displayText: string;
    } => {
        if (!workflowSLA) {
            return { daysRemaining: 0, severity: 'ok', displayText: 'N/A' };
        }

        let slaDays = 0;

        // Map status to SLA days
        switch (req.current_status) {
            case 'Intake':
            case 'Planning':
                slaDays = workflowSLA.assignment_days;
                break;
            case 'In Progress':
                slaDays = workflowSLA.complete_work_days;
                break;
            case 'Review':
                slaDays = workflowSLA.complete_work_days; // Review uses complete_work_days
                break;
            case 'Pending Approval':
                slaDays = workflowSLA.approval_days;
                break;
            default:
                return { daysRemaining: 0, severity: 'ok', displayText: 'N/A' };
        }

        const daysRemaining = slaDays - req.days_in_status;

        let severity: 'ok' | 'warning' | 'critical' = 'ok';
        let displayText = '';

        if (daysRemaining < 0) {
            severity = 'critical';
            displayText = `${Math.abs(daysRemaining)}d overdue`;
        } else if (daysRemaining === 0) {
            severity = 'critical';
            displayText = 'Due today';
        } else if (daysRemaining <= 2) {
            severity = 'critical';
            displayText = `${daysRemaining}d remaining`;
        } else if (daysRemaining <= 5) {
            severity = 'warning';
            displayText = `${daysRemaining}d remaining`;
        } else {
            severity = 'ok';
            displayText = `${daysRemaining}d remaining`;
        }

        return { daysRemaining, severity, displayText };
    };

    // Get SLA badge styling
    const getSLABadge = (severity: 'ok' | 'warning' | 'critical'): string => {
        switch (severity) {
            case 'critical':
                return 'bg-red-100 text-red-800';
            case 'warning':
                return 'bg-yellow-100 text-yellow-800';
            case 'ok':
                return 'bg-green-100 text-green-800';
        }
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
                <h2 className="text-2xl font-bold">Validator Dashboard</h2>
                <p className="text-gray-600 mt-1">
                    Welcome back, {user?.full_name}. Here's your validation workload.
                </p>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500">Active Assignments</div>
                    <div className="text-3xl font-bold text-blue-600">{activeAssignments.length}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500">Pending Reviews</div>
                    <div className="text-3xl font-bold text-purple-600">{myReviews.length}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500">Completed This Month</div>
                    <div className="text-3xl font-bold text-green-600">{completedAssignments.length}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500">Unassigned Projects</div>
                    <div className="text-3xl font-bold text-orange-600">{pendingRequests.length}</div>
                </div>
            </div>

            {/* Action Required / Activity Feed */}
            {activityFeed.length > 0 && (
                <div className="bg-white rounded-lg shadow-md mb-6 border-l-4 border-red-500">
                    <div className="p-4 border-b bg-red-50">
                        <h3 className="text-lg font-bold text-red-900 flex items-center gap-2">
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                            Action Required
                        </h3>
                        <p className="text-sm text-red-700 mt-1">Important updates on your validation assignments</p>
                    </div>
                    <div className="divide-y divide-gray-200">
                        {activityFeed.map((activity, idx) => {
                            const bgColor = activity.severity === 'critical' ? 'bg-red-50' : activity.severity === 'high' ? 'bg-orange-50' : 'bg-yellow-50';
                            const textColor = activity.severity === 'critical' ? 'text-red-900' : activity.severity === 'high' ? 'text-orange-900' : 'text-yellow-900';
                            const badgeColor = activity.severity === 'critical' ? 'bg-red-600' : activity.severity === 'high' ? 'bg-orange-600' : 'bg-yellow-600';

                            let icon;
                            if (activity.type === 'sent_back_review' || activity.type === 'sent_back_approval') {
                                icon = (
                                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                    </svg>
                                );
                            } else if (activity.type === 'approaching_deadline') {
                                icon = (
                                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                                    </svg>
                                );
                            } else {
                                icon = (
                                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                        <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
                                    </svg>
                                );
                            }

                            return (
                                <div key={idx} className={`p-4 ${bgColor} hover:bg-opacity-75 transition-colors`}>
                                    <div className="flex items-start gap-3">
                                        <div className={`flex-shrink-0 ${textColor}`}>
                                            {icon}
                                        </div>
                                        <div className="flex-grow min-w-0">
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex-grow">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className={`inline-block px-2 py-0.5 text-xs font-semibold text-white rounded ${badgeColor}`}>
                                                            {activity.severity.toUpperCase()}
                                                        </span>
                                                        <span className="text-xs text-gray-600">
                                                            #{activity.request.request_id}
                                                        </span>
                                                    </div>
                                                    <p className={`text-sm font-semibold ${textColor} mb-1`}>
                                                        {activity.request.model_names.join(', ')}
                                                    </p>
                                                    <p className="text-sm text-gray-700">
                                                        {activity.message}
                                                    </p>
                                                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-600">
                                                        <span>{activity.request.validation_type}</span>
                                                        <span>•</span>
                                                        <span className={`px-2 py-0.5 rounded ${getPriorityColor(activity.request.priority)}`}>
                                                            {activity.request.priority}
                                                        </span>
                                                    </div>
                                                </div>
                                                <Link
                                                    to={`/validation-workflow/${activity.request.request_id}`}
                                                    className={`flex-shrink-0 px-3 py-1.5 rounded text-sm font-medium text-white ${badgeColor} hover:opacity-90`}
                                                >
                                                    View
                                                </Link>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* My Active Assignments */}
            <div className="bg-white rounded-lg shadow-md mb-6">
                <div className="p-4 border-b bg-blue-50">
                    <h3 className="text-lg font-bold">My Active Assignments</h3>
                    <p className="text-sm text-gray-600">Validation projects where you are the primary validator</p>
                </div>
                {activeAssignments.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">
                        No active assignments. Check pending projects below or wait to be assigned.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {activeAssignments.map((req) => (
                                    <tr key={req.request_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                            #{req.request_id}
                                        </td>
                                        <td className="px-6 py-4">
                                            {req.model_ids.length === 1 ? (
                                                <Link
                                                    to={`/models/${req.model_ids[0]}`}
                                                    className="font-medium text-blue-600 hover:text-blue-800"
                                                >
                                                    {req.model_names[0]}
                                                </Link>
                                            ) : (
                                                <div className="space-y-1">
                                                    {req.model_names.map((name, idx) => (
                                                        <div key={idx}>
                                                            <Link
                                                                to={`/models/${req.model_ids[idx]}`}
                                                                className="font-medium text-blue-600 hover:text-blue-800 text-sm"
                                                            >
                                                                {name}
                                                            </Link>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.validation_type}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(req.priority)}`}>
                                                {req.priority}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getStatusColor(req.current_status)}`}>
                                                {req.current_status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.target_completion_date}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/validation-workflow/${req.request_id}`}
                                                className={`px-3 py-1 rounded text-sm ${req.current_status === 'Intake' || req.current_status === 'Planning'
                                                    ? 'bg-green-600 text-white hover:bg-green-700'
                                                    : req.current_status === 'In Progress'
                                                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                                                        : 'bg-gray-600 text-white hover:bg-gray-700'
                                                    }`}
                                            >
                                                {req.current_status === 'Intake' || req.current_status === 'Planning'
                                                    ? 'Begin Work'
                                                    : req.current_status === 'In Progress'
                                                        ? 'Continue Work'
                                                        : 'View Status'}
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Pending Reviews */}
            {myReviews.length > 0 && (
                <div className="bg-white rounded-lg shadow-md mb-6">
                    <div className="p-4 border-b bg-purple-50">
                        <h3 className="text-lg font-bold">Pending Reviews</h3>
                        <p className="text-sm text-gray-600">Validation projects awaiting your review</p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Primary Validator</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">SLA Time Remaining</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {myReviews.map((req) => {
                                    const slaInfo = calculateSLARemaining(req);
                                    return (
                                        <tr key={req.request_id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                                #{req.request_id}
                                            </td>
                                            <td className="px-6 py-4">
                                                {req.model_ids.length === 1 ? (
                                                    <Link
                                                        to={`/models/${req.model_ids[0]}`}
                                                        className="font-medium text-blue-600 hover:text-blue-800"
                                                    >
                                                        {req.model_names[0]}
                                                    </Link>
                                                ) : (
                                                    <div className="space-y-1">
                                                        {req.model_names.map((name, idx) => (
                                                            <div key={idx}>
                                                                <Link
                                                                    to={`/models/${req.model_ids[idx]}`}
                                                                    className="font-medium text-blue-600 hover:text-blue-800 text-sm"
                                                                >
                                                                    {name}
                                                                </Link>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                {req.validation_type}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(req.priority)}`}>
                                                    {req.priority}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                {req.primary_validator}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs font-semibold rounded ${getSLABadge(slaInfo.severity)}`}>
                                                    {slaInfo.displayText}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                {req.target_completion_date}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <button
                                                    onClick={() => openReviewModal(req)}
                                                    className="bg-purple-600 text-white px-3 py-1 rounded text-sm hover:bg-purple-700"
                                                >
                                                    Complete Review
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Pending Requests Available for Assignment */}
            <div className="bg-white rounded-lg shadow-md">
                <div className="p-4 border-b bg-orange-50">
                    <h3 className="text-lg font-bold">Pending Validation Projects</h3>
                    <p className="text-sm text-gray-600">Projects awaiting validator assignment</p>
                </div>
                {pendingRequests.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">
                        No pending projects at this time.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Requestor</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assigned To</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Request Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {pendingRequests.map((req) => (
                                    <tr key={req.request_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                            #{req.request_id}
                                        </td>
                                        <td className="px-6 py-4">
                                            {req.model_ids.length === 1 ? (
                                                <Link
                                                    to={`/models/${req.model_ids[0]}`}
                                                    className="font-medium text-blue-600 hover:text-blue-800"
                                                >
                                                    {req.model_names[0]}
                                                </Link>
                                            ) : (
                                                <div className="space-y-1">
                                                    {req.model_names.map((name, idx) => (
                                                        <div key={idx}>
                                                            <Link
                                                                to={`/models/${req.model_ids[idx]}`}
                                                                className="font-medium text-blue-600 hover:text-blue-800 text-sm"
                                                            >
                                                                {name}
                                                            </Link>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.requestor_name}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.validation_type}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(req.priority)}`}>
                                                {req.priority}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getStatusColor(req.current_status)}`}>
                                                {req.current_status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.primary_validator || (
                                                <span className="text-orange-600 font-medium">Unassigned</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.request_date}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => claimRequest(req.request_id)}
                                                    disabled={claimingId === req.request_id || !!req.primary_validator}
                                                    className={`px-3 py-1 rounded text-sm ${req.primary_validator
                                                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                                        : claimingId === req.request_id
                                                            ? 'bg-green-400 text-white cursor-wait'
                                                            : 'bg-green-600 text-white hover:bg-green-700'
                                                        }`}
                                                >
                                                    {claimingId === req.request_id
                                                        ? 'Claiming...'
                                                        : req.primary_validator
                                                            ? 'Assigned'
                                                            : 'Claim'}
                                                </button>
                                                <Link
                                                    to={`/validation-workflow/${req.request_id}`}
                                                    className="text-blue-600 hover:text-blue-800 text-sm py-1"
                                                >
                                                    View
                                                </Link>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Quick Actions */}
            <div className="mt-6 bg-white rounded-lg shadow-md p-4">
                <h3 className="text-lg font-bold mb-3">Quick Actions</h3>
                <div className="flex gap-4">
                    <Link
                        to="/validation-workflow"
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    >
                        View All Validation Projects
                    </Link>
                    <Link
                        to="/models"
                        className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                    >
                        Browse Model Inventory
                    </Link>
                </div>
            </div>

            {/* Review Action Modal */}
            {reviewModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
                        <h2 className="text-2xl font-bold mb-4">Complete Review</h2>

                        {/* Error Display */}
                        {reviewModalError && (
                            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
                                <span className="block sm:inline">{reviewModalError}</span>
                            </div>
                        )}

                        <div className="mb-4">
                            <p className="text-sm text-gray-600 mb-2">
                                <strong>Model(s):</strong> {reviewModal.model_names.join(', ')}
                            </p>
                        </div>

                        <div className="mb-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Review Comments
                            </label>
                            <textarea
                                value={reviewComments}
                                onChange={(e) => setReviewComments(e.target.value)}
                                placeholder="Enter your review comments..."
                                rows={4}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Required if sending back for revisions
                            </p>
                        </div>

                        <div className="flex justify-between gap-3">
                            <button
                                onClick={() => setReviewModal(null)}
                                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                                disabled={reviewLoading}
                            >
                                Cancel
                            </button>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => handleReviewAction('send-back')}
                                    className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:bg-gray-400"
                                    disabled={reviewLoading}
                                >
                                    {reviewLoading ? 'Processing...' : 'Send Back for Revisions'}
                                </button>
                                <button
                                    onClick={() => handleReviewAction('sign-off')}
                                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
                                    disabled={reviewLoading}
                                >
                                    {reviewLoading ? 'Processing...' : 'Sign Off (Approve)'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

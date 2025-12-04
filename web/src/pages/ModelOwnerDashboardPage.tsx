import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';
import OverdueCommentaryModal, { OverdueType } from '../components/OverdueCommentaryModal';

interface OverdueItem {
    overdue_type: 'PRE_SUBMISSION' | 'VALIDATION_IN_PROGRESS';
    request_id: number;
    model_id: number;
    model_name: string;
    risk_tier: string | null;
    due_date: string;
    grace_period_end: string | null;
    days_overdue: number;
    urgency: 'overdue' | 'in_grace_period';
    current_status: string;
    comment_status: 'CURRENT' | 'STALE' | 'MISSING';
    latest_comment: string | null;
    latest_comment_date: string | null;
    target_date: string | null;
    needs_comment_update: boolean;
}

interface NewsFeedItem {
    id: number;
    type: string;
    action: string | null;
    text: string;
    user_name: string;
    model_name: string;
    model_id: number;
    created_at: string;
}

interface MySubmission {
    model_id: number;
    model_name: string;
    description: string | null;
    development_type: string;
    owner: { full_name: string };
    submitted_at: string;
    row_approval_status: string;
}

interface RecentApproval {
    model_id: number;
    model_name: string;
    owner_name: string;
    developer_name: string | null;
    use_approval_date: string;
    validation_request_id: number | null;
    validation_type: string;
    days_ago: number;
}

interface PendingDecommissioningReview {
    request_id: number;
    model_id: number;
    model_name: string;
    status: string;
    reason: string | null;
    last_production_date: string;
    created_at: string;
    created_by_name: string | null;
}

interface AttestationWidgetData {
    pending_count: number;
    overdue_count: number;
    days_until_due: number | null;
    current_cycle: {
        cycle_id: number;
        cycle_name: string;
        submission_due_date: string;
        status: string;
    } | null;
}

export default function ModelOwnerDashboardPage() {
    const { user } = useAuth();
    const [newsFeed, setNewsFeed] = useState<NewsFeedItem[]>([]);
    const [mySubmissions, setMySubmissions] = useState<MySubmission[]>([]);
    const [recentApprovals, setRecentApprovals] = useState<RecentApproval[]>([]);
    const [overdueItems, setOverdueItems] = useState<OverdueItem[]>([]);
    const [pendingDecomReviews, setPendingDecomReviews] = useState<PendingDecommissioningReview[]>([]);
    const [attestationData, setAttestationData] = useState<AttestationWidgetData | null>(null);
    const [loading, setLoading] = useState(true);

    // Commentary modal state
    const [showCommentaryModal, setShowCommentaryModal] = useState(false);
    const [selectedOverdueItem, setSelectedOverdueItem] = useState<OverdueItem | null>(null);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            const [feedRes, submissionsRes, approvalsRes, overdueRes, decomReviewsRes, attestationsRes] = await Promise.all([
                api.get('/dashboard/news-feed'),
                api.get('/models/my-submissions'),
                api.get('/validation-workflow/dashboard/recent-approvals?days_back=30'),
                api.get('/validation-workflow/my-overdue-items'),
                api.get('/decommissioning/my-pending-owner-reviews'),
                api.get('/attestations/my-upcoming').catch(() => ({ data: null }))
            ]);
            setNewsFeed(feedRes.data);
            setMySubmissions(submissionsRes.data);
            setRecentApprovals(approvalsRes.data);
            setOverdueItems(overdueRes.data);
            setPendingDecomReviews(decomReviewsRes.data);
            setAttestationData(attestationsRes.data);
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    const openCommentaryModal = (item: OverdueItem) => {
        setSelectedOverdueItem(item);
        setShowCommentaryModal(true);
    };

    const handleCommentarySuccess = () => {
        fetchDashboardData();
    };

    const getCommentStatusBadge = (status: string) => {
        switch (status) {
            case 'CURRENT':
                return <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded">Current</span>;
            case 'STALE':
                return <span className="px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-700 rounded">Stale</span>;
            case 'MISSING':
                return <span className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 rounded">Missing</span>;
            default:
                return null;
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

    const getActionIcon = (action: string | null, type?: string) => {
        // Decommissioning events get a purple archive icon
        if (type === 'decommissioning') {
            return (
                <svg className="w-4 h-4 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4z" />
                    <path fillRule="evenodd" d="M3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clipRule="evenodd" />
                </svg>
            );
        }
        switch (action) {
            case 'approved':
                return (
                    <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                );
            case 'sent_back':
                return (
                    <svg className="w-4 h-4 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                );
            case 'submitted':
            case 'resubmitted':
                return (
                    <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                        <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                    </svg>
                );
            default:
                return (
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
                    </svg>
                );
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
                <h2 className="text-2xl font-bold">My Dashboard</h2>
                <p className="text-gray-600 mt-1">Welcome back, {user?.full_name}</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">My Records</h3>
                    <p className="text-3xl font-bold text-blue-600 mt-2">{mySubmissions.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Pending approval</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Needs Revision</h3>
                    <p className="text-3xl font-bold text-orange-600 mt-2">
                        {mySubmissions.filter(s => s.row_approval_status === 'needs_revision').length}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">Requires your attention</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Overdue Items</h3>
                    <p className={`text-3xl font-bold mt-2 ${overdueItems.length > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {overdueItems.length}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                        {overdueItems.filter(i => i.needs_comment_update).length} need commentary
                    </p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Quick Actions</h3>
                    <div className="mt-2 space-y-1">
                        <Link to="/models" className="block text-blue-600 hover:text-blue-800 text-xs">
                            View My Models &rarr;
                        </Link>
                        <Link to="/my-pending-submissions" className="block text-blue-600 hover:text-blue-800 text-xs">
                            My Pending Submissions &rarr;
                        </Link>
                    </div>
                </div>
            </div>

            {/* Pending Attestations Alert */}
            {attestationData && attestationData.pending_count > 0 && (
                <div className={`border-l-4 p-4 rounded-lg shadow mb-6 ${
                    attestationData.overdue_count > 0
                        ? 'bg-red-50 border-red-500'
                        : 'bg-yellow-50 border-yellow-500'
                }`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <svg className={`w-6 h-6 ${attestationData.overdue_count > 0 ? 'text-red-500' : 'text-yellow-500'}`} fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            <div>
                                <h3 className={`text-sm font-semibold ${attestationData.overdue_count > 0 ? 'text-red-800' : 'text-yellow-800'}`}>
                                    {attestationData.overdue_count > 0 ? 'Attestations Overdue' : 'Attestations Pending'}
                                </h3>
                                <p className={`text-sm ${attestationData.overdue_count > 0 ? 'text-red-700' : 'text-yellow-700'}`}>
                                    {attestationData.overdue_count > 0 ? (
                                        <>
                                            You have <span className="font-bold">{attestationData.overdue_count}</span> overdue attestation{attestationData.overdue_count !== 1 ? 's' : ''}
                                            {attestationData.pending_count > attestationData.overdue_count && (
                                                <> and <span className="font-bold">{attestationData.pending_count - attestationData.overdue_count}</span> pending</>
                                            )}
                                            .
                                        </>
                                    ) : (
                                        <>
                                            You have <span className="font-bold">{attestationData.pending_count}</span> attestation{attestationData.pending_count !== 1 ? 's' : ''} to complete
                                            {attestationData.days_until_due !== null && attestationData.days_until_due >= 0 && (
                                                <> (due in <span className="font-bold">{attestationData.days_until_due}</span> day{attestationData.days_until_due !== 1 ? 's' : ''})</>
                                            )}
                                            .
                                        </>
                                    )}
                                </p>
                            </div>
                        </div>
                        <Link
                            to="/my-attestations"
                            className={`inline-flex items-center px-4 py-2 text-sm font-medium text-white rounded-md transition-colors ${
                                attestationData.overdue_count > 0
                                    ? 'bg-red-600 hover:bg-red-700'
                                    : 'bg-yellow-600 hover:bg-yellow-700'
                            }`}
                        >
                            Complete Attestations
                            <svg className="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                        </Link>
                    </div>
                </div>
            )}

            {/* My Overdue Items - Alert Section */}
            {overdueItems.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-red-200">
                        <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-red-800">My Overdue Items</h3>
                        <span className="text-xs text-red-600 ml-auto">
                            {overdueItems.filter(i => i.needs_comment_update).length} need commentary update
                        </span>
                    </div>
                    <p className="text-xs text-red-700 mb-3">
                        The following items are overdue and require your attention. Please provide an explanation and target date.
                    </p>
                    <div className="space-y-2">
                        {overdueItems.map((item) => (
                            <div
                                key={`${item.overdue_type}-${item.request_id}`}
                                className="bg-white border border-red-100 rounded p-3"
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                                            <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${
                                                item.overdue_type === 'PRE_SUBMISSION'
                                                    ? 'bg-orange-100 text-orange-700'
                                                    : 'bg-purple-100 text-purple-700'
                                            }`}>
                                                {item.overdue_type === 'PRE_SUBMISSION' ? 'Submission Overdue' : 'Validation Overdue'}
                                            </span>
                                            <span className="text-xs text-red-600 font-medium">
                                                {item.days_overdue} days overdue
                                            </span>
                                            {getCommentStatusBadge(item.comment_status)}
                                        </div>
                                        <Link
                                            to={`/validation-workflow/${item.request_id}`}
                                            className="text-sm font-medium text-gray-900 hover:text-blue-600 hover:underline"
                                        >
                                            {item.model_name}
                                        </Link>
                                        <div className="text-xs text-gray-600 mt-1">
                                            <span>Due: {item.due_date}</span>
                                            {item.grace_period_end && (
                                                <span className="ml-2">Grace Period End: {item.grace_period_end}</span>
                                            )}
                                        </div>
                                        {item.latest_comment && (
                                            <div className="text-xs text-gray-500 mt-1 italic">
                                                Latest: "{item.latest_comment.substring(0, 100)}..."
                                            </div>
                                        )}
                                        {item.target_date && (
                                            <div className="text-xs text-blue-600 mt-1">
                                                Target: {item.target_date}
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex-shrink-0">
                                        <button
                                            onClick={() => openCommentaryModal(item)}
                                            className={`inline-flex items-center px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                                                item.needs_comment_update
                                                    ? 'bg-red-600 text-white hover:bg-red-700'
                                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                        >
                                            {item.needs_comment_update ? 'Add Comment' : 'Update Comment'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Pending Decommissioning Reviews */}
            {pendingDecomReviews.length > 0 && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-purple-200">
                        <svg className="w-5 h-5 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4z" />
                            <path fillRule="evenodd" d="M3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-purple-800">Pending Decommissioning Reviews</h3>
                        <span className="text-xs text-purple-600 ml-auto">
                            {pendingDecomReviews.length} awaiting your approval
                        </span>
                    </div>
                    <p className="text-xs text-purple-700 mb-3">
                        The following decommissioning requests require your approval as the model owner.
                    </p>
                    <div className="space-y-2">
                        {pendingDecomReviews.map((request) => (
                            <div
                                key={request.request_id}
                                className="bg-white border border-purple-100 rounded p-3"
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                                            <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-700">
                                                Owner Review Required
                                            </span>
                                            {request.reason && (
                                                <span className="text-xs text-gray-600">
                                                    Reason: {request.reason}
                                                </span>
                                            )}
                                        </div>
                                        <Link
                                            to={`/models/${request.model_id}/decommission`}
                                            className="text-sm font-medium text-gray-900 hover:text-purple-600 hover:underline"
                                        >
                                            {request.model_name}
                                        </Link>
                                        <div className="text-xs text-gray-600 mt-1">
                                            <span>Last Production: {request.last_production_date}</span>
                                            {request.created_by_name && (
                                                <span className="ml-2">• Requested by: {request.created_by_name}</span>
                                            )}
                                        </div>
                                        <div className="text-xs text-gray-400 mt-0.5">
                                            Submitted: {request.created_at.split('T')[0]}
                                        </div>
                                    </div>
                                    <div className="flex-shrink-0">
                                        <Link
                                            to={`/models/${request.model_id}/decommission`}
                                            className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-purple-600 hover:bg-purple-700 rounded transition-colors"
                                        >
                                            Review
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* My Pending Records */}
            {mySubmissions.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">My Model Records</h3>
                        <span className="text-xs text-gray-500 ml-auto">{mySubmissions.length} pending</span>
                    </div>
                    <div className="space-y-2">
                        {mySubmissions.map((submission) => (
                            <div
                                key={submission.model_id}
                                className="border-l-3 pl-3 py-2 hover:bg-gray-50 rounded-r"
                                style={{
                                    borderLeftWidth: '3px',
                                    borderLeftColor: submission.row_approval_status === 'needs_revision' ? '#f59e0b' : '#3b82f6'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${
                                                submission.row_approval_status === 'needs_revision'
                                                    ? 'bg-orange-100 text-orange-700'
                                                    : submission.row_approval_status === 'pending'
                                                    ? 'bg-blue-100 text-blue-700'
                                                    : 'bg-gray-100 text-gray-700'
                                            }`}>
                                                {submission.row_approval_status === 'needs_revision' ? 'Needs Revision' :
                                                 submission.row_approval_status === 'pending' ? 'Under Review' :
                                                 submission.row_approval_status}
                                            </span>
                                            <span className="text-xs text-gray-400">
                                                Submitted {formatTimeAgo(submission.submitted_at)}
                                            </span>
                                        </div>
                                        <Link
                                            to={`/models/${submission.model_id}`}
                                            className="text-sm font-medium text-gray-800 hover:text-blue-600 truncate block"
                                        >
                                            {submission.model_name}
                                        </Link>
                                        <p className="text-xs text-gray-600 mt-0.5">
                                            Owner: {submission.owner.full_name} • {submission.development_type}
                                        </p>
                                    </div>
                                    <div className="flex-shrink-0">
                                        {submission.row_approval_status === 'needs_revision' ? (
                                            <Link
                                                to={`/models/${submission.model_id}?edit=true`}
                                                className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-orange-600 hover:bg-orange-700 rounded transition-colors"
                                            >
                                                Edit & Resubmit
                                            </Link>
                                        ) : (
                                            <Link
                                                to={`/models/${submission.model_id}`}
                                                className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 border border-blue-600 hover:border-blue-800 rounded transition-colors"
                                            >
                                                View
                                            </Link>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Recently Approved Models Widget */}
            {recentApprovals.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">Recently Approved Models</h3>
                        <span className="text-xs text-gray-500 ml-auto">Last 30 days</span>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {recentApprovals.slice(0, 10).map((approval) => (
                            <div
                                key={approval.model_id}
                                className="border-l-3 pl-3 py-2 hover:bg-gray-50 rounded-r"
                                style={{
                                    borderLeftWidth: '3px',
                                    borderLeftColor: '#10b981'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <Link
                                                to={`/models/${approval.model_id}`}
                                                className="text-sm font-medium text-gray-900 hover:text-blue-600 hover:underline truncate"
                                            >
                                                {approval.model_name}
                                            </Link>
                                            <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded font-medium">
                                                Approved
                                            </span>
                                        </div>
                                        <div className="text-xs text-gray-600">
                                            <div>{approval.validation_type}</div>
                                            <div className="flex items-center gap-1 mt-0.5">
                                                <span>Owner: {approval.owner_name}</span>
                                                {approval.developer_name && (
                                                    <>
                                                        <span className="text-gray-400">•</span>
                                                        <span>Developer: {approval.developer_name}</span>
                                                    </>
                                                )}
                                            </div>
                                            <div className="text-gray-400 mt-0.5">
                                                Approved {approval.days_ago === 0 ? 'today' :
                                                         approval.days_ago === 1 ? 'yesterday' :
                                                         `${approval.days_ago} days ago`}
                                            </div>
                                        </div>
                                    </div>
                                    {approval.validation_request_id && (
                                        <div className="flex-shrink-0">
                                            <Link
                                                to={`/validation-workflow/${approval.validation_request_id}`}
                                                className="inline-flex items-center px-2 py-1 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded transition-colors"
                                            >
                                                View
                                            </Link>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Activity News Feed */}
            <div className="bg-white p-4 rounded-lg shadow">
                <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                    <svg className="w-4 h-4 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
                        <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-700">Recent Activity</h3>
                    <span className="text-xs text-gray-500 ml-auto">{newsFeed.length} activities</span>
                </div>
                {newsFeed.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-4">No recent activity on your models.</p>
                ) : (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                        {newsFeed.map((item) => (
                            <div
                                key={item.id}
                                className="flex items-start gap-3 p-2 hover:bg-gray-50 rounded"
                            >
                                {getActionIcon(item.action, item.type)}
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-gray-800">
                                        <span className="font-medium">{item.user_name}</span>
                                        {item.type === 'decommissioning' ? (
                                            <span className="text-gray-600"> on </span>
                                        ) : item.action && (
                                            <span className="text-gray-600">
                                                {' '}{item.action === 'approved' ? 'approved' :
                                                      item.action === 'sent_back' ? 'sent back' :
                                                      item.action === 'submitted' ? 'submitted' :
                                                      item.action === 'resubmitted' ? 'resubmitted' :
                                                      'commented on'}
                                            </span>
                                        )}
                                        {' '}
                                        <Link to={`/models/${item.model_id}`} className="font-medium text-blue-600 hover:text-blue-800">
                                            {item.model_name}
                                        </Link>
                                    </p>
                                    <p className="text-xs text-gray-600 mt-0.5">{item.text}</p>
                                    <p className="text-xs text-gray-400 mt-0.5">{formatTimeAgo(item.created_at)}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Commentary Modal */}
            {showCommentaryModal && selectedOverdueItem && (
                <OverdueCommentaryModal
                    requestId={selectedOverdueItem.request_id}
                    overdueType={selectedOverdueItem.overdue_type as OverdueType}
                    modelName={selectedOverdueItem.model_name}
                    currentComment={null}
                    onClose={() => {
                        setShowCommentaryModal(false);
                        setSelectedOverdueItem(null);
                    }}
                    onSuccess={handleCommentarySuccess}
                />
            )}
        </Layout>
    );
}

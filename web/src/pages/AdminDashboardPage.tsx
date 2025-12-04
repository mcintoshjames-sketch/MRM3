import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';
import { overdueCommentaryApi, MyOverdueItem } from '../api/overdueCommentary';
import OverdueCommentaryModal, { OverdueType } from '../components/OverdueCommentaryModal';

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
    // Commentary fields
    comment_status: 'CURRENT' | 'STALE' | 'MISSING';
    latest_comment: string | null;
    latest_comment_date: string | null;
    target_submission_date: string | null;
    needs_comment_update: boolean;
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
    // Commentary fields
    comment_status: 'CURRENT' | 'STALE' | 'MISSING';
    latest_comment: string | null;
    latest_comment_date: string | null;
    target_completion_date: string | null;
    needs_comment_update: boolean;
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

interface PendingModelEdit {
    pending_edit_id: number;
    model_id: number;
    model_name: string;
    model_owner: { user_id: number; full_name: string; email: string } | null;
    requested_by: { user_id: number; full_name: string; email: string };
    requested_at: string;
    proposed_changes: Record<string, unknown>;
    original_values: Record<string, unknown>;
    status: string;
}

interface PendingAdditionalApproval {
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

interface OverdueMonitoringCycle {
    cycle_id: number;
    plan_id: number;
    plan_name: string;
    period_label: string;
    due_date: string;
    status: string;
    days_overdue: number;
    team_name: string | null;
    data_provider_name: string | null;
    result_count: number;
    green_count: number;
    yellow_count: number;
    red_count: number;
}

interface RecommendationsSummary {
    total_open: number;
    overdue_count: number;
    by_status: { status_code: string; status_label: string; count: number }[];
    by_priority: { priority_code: string; priority_label: string; count: number }[];
}

interface OverdueRecommendation {
    recommendation_id: number;
    recommendation_code: string;
    title: string;
    model: { model_id: number; model_name: string };
    priority: { code: string; label: string };
    current_status: { code: string; label: string };
    assigned_to: { full_name: string };
    current_target_date: string;
    days_overdue: number;
}

interface CycleReminder {
    should_show_reminder: boolean;
    suggested_cycle_name: string | null;
    last_cycle_end_date: string | null;
    message: string | null;
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
    const [pendingModelEdits, setPendingModelEdits] = useState<PendingModelEdit[]>([]);
    const [pendingAdditionalApprovals, setPendingAdditionalApprovals] = useState<PendingAdditionalApproval[]>([]);
    const [myOverdueItems, setMyOverdueItems] = useState<MyOverdueItem[]>([]);
    const [overdueMonitoringCycles, setOverdueMonitoringCycles] = useState<OverdueMonitoringCycle[]>([]);
    const [recommendationsSummary, setRecommendationsSummary] = useState<RecommendationsSummary | null>(null);
    const [overdueRecommendations, setOverdueRecommendations] = useState<OverdueRecommendation[]>([]);
    const [cycleReminder, setCycleReminder] = useState<CycleReminder | null>(null);
    const [attestationReviewCount, setAttestationReviewCount] = useState<number>(0);
    const [loading, setLoading] = useState(true);

    // Commentary modal state
    const [showCommentaryModal, setShowCommentaryModal] = useState(false);
    const [commentaryModalRequestId, setCommentaryModalRequestId] = useState<number | null>(null);
    const [commentaryModalType, setCommentaryModalType] = useState<OverdueType>('PRE_SUBMISSION');
    const [commentaryModalModelName, setCommentaryModalModelName] = useState<string>('');

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
                pendingEditsRes,
                conditionalApprovalsRes,
                myOverdueRes,
                monitoringOverviewRes,
                recommendationsOpenRes,
                recommendationsOverdueRes,
                cycleReminderRes,
                attestationStatsRes
            ] = await Promise.all([
                api.get('/validation-workflow/dashboard/sla-violations'),
                api.get('/validation-workflow/dashboard/out-of-order'),
                api.get('/validation-workflow/dashboard/pending-assignments'),
                api.get('/validation-workflow/dashboard/overdue-submissions'),
                api.get('/validation-workflow/dashboard/overdue-validations'),
                api.get('/validation-workflow/dashboard/upcoming-revalidations?days_ahead=90'),
                api.get('/models/pending-submissions'),
                api.get('/models/pending-edits/all'),
                api.get('/validation-workflow/dashboard/pending-additional-approvals'),
                overdueCommentaryApi.getMyOverdueItems(),
                api.get('/monitoring/admin-overview'),
                api.get('/recommendations/dashboard/open'),
                api.get('/recommendations/dashboard/overdue'),
                api.get('/attestations/cycles/reminder').catch(() => ({ data: { should_show_reminder: false } })),
                api.get('/attestations/dashboard/stats').catch(() => ({ data: { submitted_count: 0 } }))
            ]);
            setSlaViolations(violationsRes.data);
            setOutOfOrder(outOfOrderRes.data);
            setPendingAssignments(pendingRes.data);
            setOverdueSubmissions(overdueSubmissionsRes.data);
            setOverdueValidations(overdueValidationsRes.data);
            // Filter to only show truly upcoming submissions (not past due)
            setUpcomingRevalidations(
                upcomingRevalidationsRes.data.filter(
                    (r: UpcomingRevalidation) => r.days_until_submission_due > 0
                )
            );
            setPendingModelSubmissions(pendingModelsRes.data);
            setPendingModelEdits(pendingEditsRes.data);
            setPendingAdditionalApprovals(conditionalApprovalsRes.data);
            setMyOverdueItems(myOverdueRes);
            // Filter monitoring cycles for overdue ones only
            const overdueCycles = monitoringOverviewRes.data.cycles.filter(
                (cycle: OverdueMonitoringCycle & { priority: string }) => cycle.priority === 'overdue'
            );
            setOverdueMonitoringCycles(overdueCycles);
            // Set recommendations data
            setRecommendationsSummary(recommendationsOpenRes.data);
            setOverdueRecommendations(recommendationsOverdueRes.data.recommendations || []);
            // Set cycle reminder
            setCycleReminder(cycleReminderRes.data);
            setAttestationReviewCount(attestationStatsRes.data.submitted_count || 0);
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    const openCommentaryModal = (requestId: number, overdueType: OverdueType, modelName: string) => {
        setCommentaryModalRequestId(requestId);
        setCommentaryModalType(overdueType);
        setCommentaryModalModelName(modelName);
        setShowCommentaryModal(true);
    };

    const handleCommentarySuccess = () => {
        fetchDashboardData();
    };

    // Get badge style for commentary status
    const getCommentStatusBadge = (status: 'CURRENT' | 'STALE' | 'MISSING') => {
        switch (status) {
            case 'CURRENT':
                return 'bg-green-100 text-green-800';
            case 'STALE':
                return 'bg-yellow-100 text-yellow-800';
            case 'MISSING':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getCommentStatusLabel = (status: 'CURRENT' | 'STALE' | 'MISSING') => {
        switch (status) {
            case 'CURRENT':
                return 'Current';
            case 'STALE':
                return 'Stale';
            case 'MISSING':
                return 'Missing';
            default:
                return status;
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

    // Generic CSV export helper
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const exportToCSV = (data: any[], filename: string, columns: { key: string; label: string }[]) => {
        if (data.length === 0) return;

        const headers = columns.map(col => col.label);
        const rows = data.map(item => {
            return columns.map(col => {
                const keys = col.key.split('.');
                let value: unknown = item;
                for (const k of keys) {
                    value = (value as Record<string, unknown>)?.[k];
                }
                const strValue = value != null ? String(value) : '';
                // Escape quotes and wrap in quotes if contains comma, quote, or newline
                const escaped = strValue.replace(/"/g, '""');
                return escaped.includes(',') || escaped.includes('"') || escaped.includes('\n')
                    ? `"${escaped}"`
                    : escaped;
            }).join(',');
        });

        const csv = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const date = new Date().toISOString().split('T')[0];
        link.setAttribute('download', `${filename}_${date}.csv`);
        document.body.appendChild(link);
        link.click();
        link.parentNode?.removeChild(link);
        window.URL.revokeObjectURL(url);
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

            {/* Attestation Cycle Reminder Banner */}
            {cycleReminder?.should_show_reminder && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start gap-3">
                        <div className="flex-shrink-0">
                            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <h3 className="text-sm font-semibold text-blue-800">Attestation Cycle Reminder</h3>
                            <p className="text-sm text-blue-700 mt-1">
                                {cycleReminder.message || `It's time to open a new attestation cycle for ${cycleReminder.suggested_cycle_name}.`}
                            </p>
                            {cycleReminder.last_cycle_end_date && (
                                <p className="text-xs text-blue-600 mt-1">
                                    Last cycle ended: {cycleReminder.last_cycle_end_date.split('T')[0]}
                                </p>
                            )}
                            <div className="mt-3">
                                <Link
                                    to="/attestations/cycles"
                                    className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
                                >
                                    Open Attestation Cycles
                                    <svg className="ml-1.5 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* New Model Records Awaiting Approval Widget */}
            {pendingModelSubmissions.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">New Model Records Awaiting Approval</h3>
                        <span className="text-xs text-gray-500 ml-auto">{pendingModelSubmissions.length} pending</span>
                        <button
                            onClick={() => exportToCSV(pendingModelSubmissions, 'pending_model_submissions', [
                                { key: 'model_id', label: 'Model ID' },
                                { key: 'model_name', label: 'Model Name' },
                                { key: 'development_type', label: 'Development Type' },
                                { key: 'owner.full_name', label: 'Owner' },
                                { key: 'submitted_by_user.full_name', label: 'Submitted By' },
                                { key: 'submitted_at', label: 'Submitted At' },
                                { key: 'row_approval_status', label: 'Status' },
                            ])}
                            className="text-xs text-gray-500 hover:text-gray-700"
                            title="Export to CSV"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </button>
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

            {/* Pending Model Edits Widget */}
            {pendingModelEdits.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">Model Record Updates Awaiting Approval</h3>
                        <span className="text-xs text-gray-500 ml-auto">{pendingModelEdits.length} pending</span>
                        <button
                            onClick={() => exportToCSV(pendingModelEdits, 'pending_model_edits', [
                                { key: 'pending_edit_id', label: 'Edit ID' },
                                { key: 'model_id', label: 'Model ID' },
                                { key: 'model_name', label: 'Model Name' },
                                { key: 'requested_by.full_name', label: 'Requested By' },
                                { key: 'requested_at', label: 'Requested At' },
                                { key: 'status', label: 'Status' },
                            ])}
                            className="text-xs text-gray-500 hover:text-gray-700"
                            title="Export to CSV"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </button>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {pendingModelEdits.slice(0, 5).map((edit) => (
                            <div
                                key={edit.pending_edit_id}
                                className="border-l-3 pl-3 py-2 hover:bg-gray-50 rounded-r"
                                style={{
                                    borderLeftWidth: '3px',
                                    borderLeftColor: '#f59e0b'
                                }}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-amber-100 text-amber-700">
                                                Edit Request
                                            </span>
                                            <span className="text-xs text-gray-400">
                                                {formatTimeAgo(edit.requested_at)}
                                            </span>
                                        </div>
                                        <Link
                                            to={`/models/${edit.model_id}`}
                                            className="text-sm font-medium text-gray-800 hover:text-blue-600 truncate block"
                                        >
                                            {edit.model_name}
                                        </Link>
                                        <p className="text-xs text-gray-600 mt-0.5">
                                            Requested by: {edit.requested_by.full_name}
                                            {edit.model_owner && ` • Owner: ${edit.model_owner.full_name}`}
                                        </p>
                                        <p className="text-xs text-gray-500 mt-0.5">
                                            Fields to change: {Object.keys(edit.proposed_changes).join(', ')}
                                        </p>
                                    </div>
                                    <div className="flex-shrink-0">
                                        <Link
                                            to={`/models/${edit.model_id}?reviewEdit=${edit.pending_edit_id}`}
                                            className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded transition-colors"
                                        >
                                            Review
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    {pendingModelEdits.length > 5 && (
                        <div className="mt-3 pt-2 border-t text-center">
                            <span className="text-xs text-gray-500">
                                Showing 5 of {pendingModelEdits.length} pending model edits
                            </span>
                        </div>
                    )}
                </div>
            )}

            {/* Attestation Review Queue Alert */}
            {attestationReviewCount > 0 && (
                <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <svg className="w-6 h-6 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            <div>
                                <h3 className="text-sm font-semibold text-blue-800">Attestations Awaiting Review</h3>
                                <p className="text-sm text-blue-700">
                                    You have <span className="font-bold">{attestationReviewCount}</span> attestation{attestationReviewCount !== 1 ? 's' : ''} in the review queue awaiting approval.
                                </p>
                            </div>
                        </div>
                        <Link
                            to="/attestations?tab=review"
                            className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
                        >
                            View Review Queue
                            <svg className="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                        </Link>
                    </div>
                </div>
            )}

            {/* Pending Additional Approvals Widget */}
            {pendingAdditionalApprovals.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">Pending Additional Approvals</h3>
                        <span className="text-xs text-gray-500 ml-auto">{pendingAdditionalApprovals.length} awaiting</span>
                        <button
                            onClick={() => exportToCSV(pendingAdditionalApprovals, 'pending_additional_approvals', [
                                { key: 'request_id', label: 'Request ID' },
                                { key: 'model_id', label: 'Model ID' },
                                { key: 'model_name', label: 'Model Name' },
                                { key: 'validation_type', label: 'Validation Type' },
                                { key: 'days_pending', label: 'Days Pending' },
                                { key: 'created_at', label: 'Created At' },
                            ])}
                            className="text-xs text-gray-500 hover:text-gray-700"
                            title="Export to CSV"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </button>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {pendingAdditionalApprovals.slice(0, 5).map((item) => (
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
                    {pendingAdditionalApprovals.length > 5 && (
                        <div className="mt-3 pt-2 border-t text-center">
                            <span className="text-xs text-gray-500">
                                Showing 5 of {pendingAdditionalApprovals.length} pending approvals
                            </span>
                        </div>
                    )}
                </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 gap-4 mb-6">
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
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Overdue Monitoring</h3>
                    <p className="text-3xl font-bold text-red-600 mt-2">{overdueMonitoringCycles.length}</p>
                    <p className="text-xs text-gray-600 mt-1">Past report due</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Open Recommendations</h3>
                    <p className="text-3xl font-bold text-orange-600 mt-2">{recommendationsSummary?.total_open || 0}</p>
                    <p className="text-xs text-gray-600 mt-1">
                        {overdueRecommendations.length > 0 ? (
                            <span className="text-red-600 font-medium">{overdueRecommendations.length} overdue</span>
                        ) : (
                            'None overdue'
                        )}
                    </p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <h3 className="text-xs font-medium text-gray-500 uppercase">Quick Actions</h3>
                    <div className="mt-2 space-y-1">
                        <Link to="/validation-workflow" className="block text-blue-600 hover:text-blue-800 text-xs">
                            View All Validations &rarr;
                        </Link>
                        <Link to="/recommendations" className="block text-orange-600 hover:text-orange-800 text-xs">
                            View Recommendations &rarr;
                        </Link>
                        <Link to="/workflow-config" className="block text-blue-600 hover:text-blue-800 text-xs">
                            Configure Workflow SLA &rarr;
                        </Link>
                    </div>
                </div>
            </div>

            {/* My Overdue Items - Items requiring current user's attention */}
            {myOverdueItems.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6 border-l-4 border-orange-500">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-5 h-5 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-lg font-bold text-gray-900">My Overdue Items</h3>
                        <span className="bg-orange-100 text-orange-700 text-xs font-medium px-2 py-0.5 rounded ml-auto">
                            {myOverdueItems.filter(i => i.needs_comment_update).length} need commentary
                        </span>
                        <button
                            onClick={() => exportToCSV(myOverdueItems, 'my_overdue_items', [
                                { key: 'request_id', label: 'Request ID' },
                                { key: 'model_name', label: 'Model Name' },
                                { key: 'overdue_type', label: 'Overdue Type' },
                                { key: 'days_overdue', label: 'Days Overdue' },
                                { key: 'current_status', label: 'Status' },
                                { key: 'comment_status', label: 'Comment Status' },
                                { key: 'target_date', label: 'Target Date' },
                            ])}
                            className="text-xs text-gray-500 hover:text-gray-700"
                            title="Export to CSV"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </button>
                    </div>
                    <p className="text-sm text-gray-600 mb-3">Items where you are responsible for providing delay explanations</p>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Your Role</th>
                                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Days Overdue</th>
                                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Commentary</th>
                                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {myOverdueItems.map((item) => (
                                    <tr
                                        key={`${item.request_id}-${item.overdue_type}`}
                                        className={`hover:bg-orange-50 ${item.needs_comment_update ? 'bg-orange-50' : ''}`}
                                    >
                                        <td className="px-3 py-2 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${
                                                item.overdue_type === 'PRE_SUBMISSION'
                                                    ? 'bg-yellow-100 text-yellow-800'
                                                    : 'bg-red-100 text-red-800'
                                            }`}>
                                                {item.overdue_type === 'PRE_SUBMISSION' ? 'Submission' : 'Validation'}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2 whitespace-nowrap">
                                            <Link
                                                to={`/models/${item.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                                            >
                                                {item.model_name}
                                            </Link>
                                            {item.risk_tier && (
                                                <span className="ml-1 text-xs text-gray-500">({item.risk_tier})</span>
                                            )}
                                        </td>
                                        <td className="px-3 py-2 whitespace-nowrap text-sm">
                                            <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-700 capitalize">
                                                {item.user_role}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2 whitespace-nowrap">
                                            <span className="px-2 py-1 text-xs font-semibold rounded bg-orange-100 text-orange-800">
                                                {item.days_overdue} days
                                            </span>
                                        </td>
                                        <td className="px-3 py-2 whitespace-nowrap">
                                            <div className="flex flex-col gap-1">
                                                <span className={`px-2 py-1 text-xs font-semibold rounded inline-block w-fit ${getCommentStatusBadge(item.comment_status)}`}>
                                                    {getCommentStatusLabel(item.comment_status)}
                                                </span>
                                                {item.latest_comment && (
                                                    <span className="text-xs text-gray-500 truncate max-w-32" title={item.latest_comment}>
                                                        "{item.latest_comment.substring(0, 25)}..."
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-3 py-2 whitespace-nowrap text-sm">
                                            {item.target_date ? item.target_date.split('T')[0] : <span className="text-gray-400">-</span>}
                                        </td>
                                        <td className="px-3 py-2 whitespace-nowrap">
                                            <div className="flex gap-2">
                                                <Link
                                                    to={`/validation-workflow/${item.request_id}`}
                                                    className="text-blue-600 hover:text-blue-800 text-xs"
                                                >
                                                    View
                                                </Link>
                                                {item.needs_comment_update && (
                                                    <button
                                                        onClick={() => openCommentaryModal(item.request_id, item.overdue_type, item.model_name)}
                                                        className="px-2 py-1 text-xs font-medium text-white bg-orange-600 hover:bg-orange-700 rounded"
                                                    >
                                                        Add Commentary
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Pending Validator Assignments Feed */}
            {pendingAssignments.length > 0 && (
                <div className="bg-white p-4 rounded-lg shadow mb-6">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
                        <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                        </svg>
                        <h3 className="text-sm font-semibold text-gray-700">Pending Validator Assignments</h3>
                        <span className="text-xs text-gray-500 ml-auto">{pendingAssignments.length} awaiting</span>
                        <button
                            onClick={() => exportToCSV(pendingAssignments, 'pending_validator_assignments', [
                                { key: 'request_id', label: 'Request ID' },
                                { key: 'model_id', label: 'Model ID' },
                                { key: 'model_name', label: 'Model Name' },
                                { key: 'requestor_name', label: 'Requestor' },
                                { key: 'validation_type', label: 'Validation Type' },
                                { key: 'priority', label: 'Priority' },
                                { key: 'region', label: 'Region' },
                                { key: 'request_date', label: 'Request Date' },
                                { key: 'days_pending', label: 'Days Pending' },
                            ])}
                            className="text-xs text-gray-500 hover:text-gray-700"
                            title="Export to CSV"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </button>
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
                        <button
                            onClick={() => exportToCSV(slaViolations, 'sla_violations', [
                                { key: 'request_id', label: 'Request ID' },
                                { key: 'model_name', label: 'Model Name' },
                                { key: 'violation_type', label: 'Violation Type' },
                                { key: 'sla_days', label: 'SLA Days' },
                                { key: 'actual_days', label: 'Actual Days' },
                                { key: 'days_overdue', label: 'Days Overdue' },
                                { key: 'current_status', label: 'Status' },
                                { key: 'priority', label: 'Priority' },
                                { key: 'severity', label: 'Severity' },
                            ])}
                            className="text-xs text-gray-500 hover:text-gray-700"
                            title="Export to CSV"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </button>
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
                        <button
                            onClick={() => exportToCSV(outOfOrder, 'out_of_order_validations', [
                                { key: 'request_id', label: 'Request ID' },
                                { key: 'model_name', label: 'Model Name' },
                                { key: 'version_number', label: 'Version' },
                                { key: 'validation_type', label: 'Validation Type' },
                                { key: 'target_completion_date', label: 'Target Completion' },
                                { key: 'production_date', label: 'Production Date' },
                                { key: 'days_gap', label: 'Days Gap' },
                                { key: 'current_status', label: 'Status' },
                                { key: 'priority', label: 'Priority' },
                            ])}
                            className="text-xs text-gray-500 hover:text-gray-700"
                            title="Export to CSV"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </button>
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
                                <button
                                    onClick={() => exportToCSV(overdueSubmissions, 'overdue_submissions', [
                                        { key: 'request_id', label: 'Request ID' },
                                        { key: 'model_id', label: 'Model ID' },
                                        { key: 'model_name', label: 'Model Name' },
                                        { key: 'model_owner', label: 'Owner' },
                                        { key: 'submission_due_date', label: 'Submission Due' },
                                        { key: 'grace_period_end', label: 'Grace Period End' },
                                        { key: 'days_overdue', label: 'Days Overdue' },
                                        { key: 'urgency', label: 'Urgency' },
                                        { key: 'submission_status', label: 'Status' },
                                        { key: 'comment_status', label: 'Commentary Status' },
                                    ])}
                                    className="ml-auto text-orange-600 hover:text-orange-800"
                                    title="Export to CSV"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </button>
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
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Late</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Commentary</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {overdueSubmissions.map((submission) => (
                                    <tr
                                        key={submission.request_id}
                                        className={`hover:bg-orange-50 ${submission.needs_comment_update ? 'bg-red-50' : ''}`}
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
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${
                                                submission.urgency === 'overdue'
                                                    ? 'bg-orange-100 text-orange-800'
                                                    : 'bg-blue-100 text-blue-800'
                                            }`}>
                                                {submission.days_overdue} days
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <div className="flex flex-col gap-1">
                                                <span className={`px-2 py-1 text-xs font-semibold rounded inline-block w-fit ${getCommentStatusBadge(submission.comment_status)}`}>
                                                    {getCommentStatusLabel(submission.comment_status)}
                                                </span>
                                                {submission.latest_comment && (
                                                    <span className="text-xs text-gray-500 truncate max-w-32" title={submission.latest_comment}>
                                                        "{submission.latest_comment.substring(0, 30)}..."
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {submission.target_submission_date || <span className="text-gray-400">-</span>}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <div className="flex gap-2">
                                                <Link
                                                    to={`/validation-workflow/${submission.request_id}`}
                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                >
                                                    View
                                                </Link>
                                                {submission.needs_comment_update && (
                                                    <button
                                                        onClick={() => openCommentaryModal(submission.request_id, 'PRE_SUBMISSION', submission.model_name)}
                                                        className="text-orange-600 hover:text-orange-800 text-sm font-medium"
                                                    >
                                                        Add Commentary
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Overdue Monitoring Cycles */}
                {overdueMonitoringCycles.length > 0 && (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-red-50">
                            <div className="flex items-center">
                                <svg className="h-5 w-5 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                                </svg>
                                <h3 className="text-lg font-bold text-red-900">
                                    Overdue Monitoring Cycles ({overdueMonitoringCycles.length})
                                </h3>
                                <button
                                    onClick={() => exportToCSV(overdueMonitoringCycles, 'overdue_monitoring_cycles', [
                                        { key: 'cycle_id', label: 'Cycle ID' },
                                        { key: 'plan_id', label: 'Plan ID' },
                                        { key: 'plan_name', label: 'Plan Name' },
                                        { key: 'period_label', label: 'Period' },
                                        { key: 'due_date', label: 'Due Date' },
                                        { key: 'days_overdue', label: 'Days Overdue' },
                                        { key: 'status', label: 'Status' },
                                        { key: 'team_name', label: 'Team' },
                                        { key: 'data_provider_name', label: 'Data Provider' },
                                    ])}
                                    className="ml-auto text-red-600 hover:text-red-800"
                                    title="Export to CSV"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </button>
                            </div>
                            <p className="text-sm text-red-700 ml-7">Monitoring cycles past their report due date</p>
                        </div>
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Overdue</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Team</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Results</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {overdueMonitoringCycles.map((cycle) => (
                                    <tr key={cycle.cycle_id} className="hover:bg-red-50">
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/monitoring/${cycle.plan_id}`}
                                                className="text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                {cycle.plan_name}
                                            </Link>
                                            {cycle.data_provider_name && (
                                                <div className="text-xs text-gray-500">
                                                    Provider: {cycle.data_provider_name}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{cycle.period_label}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{cycle.due_date.split('T')[0]}</td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800">
                                                {cycle.days_overdue} days
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${
                                                cycle.status === 'PENDING' ? 'bg-gray-100 text-gray-800' :
                                                cycle.status === 'DATA_COLLECTION' ? 'bg-blue-100 text-blue-800' :
                                                cycle.status === 'UNDER_REVIEW' ? 'bg-yellow-100 text-yellow-800' :
                                                cycle.status === 'PENDING_APPROVAL' ? 'bg-orange-100 text-orange-800' :
                                                'bg-gray-100 text-gray-800'
                                            }`}>
                                                {cycle.status.replace(/_/g, ' ')}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                            {cycle.team_name || '-'}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            {cycle.result_count > 0 ? (
                                                <div className="flex items-center gap-1">
                                                    <span className="text-sm text-gray-600">{cycle.result_count}</span>
                                                    {(cycle.green_count > 0 || cycle.yellow_count > 0 || cycle.red_count > 0) && (
                                                        <div className="flex gap-0.5 ml-1">
                                                            {cycle.green_count > 0 && (
                                                                <span className="inline-block w-2.5 h-2.5 bg-green-500 rounded-full" title={`${cycle.green_count} Green`}></span>
                                                            )}
                                                            {cycle.yellow_count > 0 && (
                                                                <span className="inline-block w-2.5 h-2.5 bg-yellow-400 rounded-full" title={`${cycle.yellow_count} Yellow`}></span>
                                                            )}
                                                            {cycle.red_count > 0 && (
                                                                <span className="inline-block w-2.5 h-2.5 bg-red-500 rounded-full" title={`${cycle.red_count} Red`}></span>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            ) : (
                                                <span className="text-sm text-gray-400">-</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/monitoring/${cycle.plan_id}?cycle=${cycle.cycle_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                View Cycle
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Overdue Recommendations */}
                {overdueRecommendations.length > 0 && (
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-orange-50">
                            <div className="flex items-center">
                                <svg className="h-5 w-5 text-orange-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                                <h3 className="text-lg font-bold text-orange-900">
                                    Overdue Recommendations ({overdueRecommendations.length})
                                </h3>
                                <button
                                    onClick={() => exportToCSV(overdueRecommendations, 'overdue_recommendations', [
                                        { key: 'recommendation_id', label: 'ID' },
                                        { key: 'recommendation_code', label: 'Code' },
                                        { key: 'title', label: 'Title' },
                                        { key: 'model.model_name', label: 'Model' },
                                        { key: 'priority.label', label: 'Priority' },
                                        { key: 'current_status.label', label: 'Status' },
                                        { key: 'assigned_to.full_name', label: 'Assigned To' },
                                        { key: 'current_target_date', label: 'Target Date' },
                                        { key: 'days_overdue', label: 'Days Overdue' },
                                    ])}
                                    className="ml-auto text-orange-600 hover:text-orange-800"
                                    title="Export to CSV"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </button>
                            </div>
                            <p className="text-sm text-orange-700 ml-7">Recommendations past their target remediation date</p>
                        </div>
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assigned To</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Overdue</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {overdueRecommendations.slice(0, 10).map((rec) => (
                                    <tr key={rec.recommendation_id} className="hover:bg-orange-50">
                                        <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                                            {rec.recommendation_code}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/recommendations/${rec.recommendation_id}`}
                                                className="text-blue-600 hover:text-blue-800 font-medium text-sm truncate block max-w-48"
                                                title={rec.title}
                                            >
                                                {rec.title}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/models/${rec.model.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                {rec.model.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${
                                                rec.priority.code === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                                                rec.priority.code === 'HIGH' ? 'bg-orange-100 text-orange-800' :
                                                rec.priority.code === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                                                'bg-gray-100 text-gray-800'
                                            }`}>
                                                {rec.priority.label}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-700">
                                                {rec.current_status.label}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                            {rec.assigned_to?.full_name || '-'}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                                            {rec.current_target_date?.split('T')[0]}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800">
                                                {rec.days_overdue} days
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/recommendations/${rec.recommendation_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                View
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {overdueRecommendations.length > 10 && (
                            <div className="p-3 bg-gray-50 text-sm text-gray-600 text-center">
                                <Link to="/recommendations?overdue_only=true" className="text-orange-600 hover:text-orange-800">
                                    View all {overdueRecommendations.length} overdue recommendations &rarr;
                                </Link>
                            </div>
                        )}
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
                                <button
                                    onClick={() => exportToCSV(overdueValidations, 'overdue_validations', [
                                        { key: 'request_id', label: 'Request ID' },
                                        { key: 'model_id', label: 'Model ID' },
                                        { key: 'model_name', label: 'Model Name' },
                                        { key: 'model_owner', label: 'Owner' },
                                        { key: 'model_validation_due_date', label: 'Validation Due' },
                                        { key: 'days_overdue', label: 'Days Overdue' },
                                        { key: 'current_status', label: 'Status' },
                                        { key: 'comment_status', label: 'Commentary Status' },
                                        { key: 'target_completion_date', label: 'Target Date' },
                                    ])}
                                    className="ml-auto text-red-600 hover:text-red-800"
                                    title="Export to CSV"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </button>
                            </div>
                            <p className="text-sm text-red-700 ml-7">Models past their final validation due date</p>
                        </div>
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation Due</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Overdue</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Commentary</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {overdueValidations.map((validation) => (
                                    <tr key={validation.request_id} className={`hover:bg-red-50 ${validation.needs_comment_update ? 'bg-red-50' : ''}`}>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/models/${validation.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                {validation.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{validation.model_owner}</td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{validation.model_validation_due_date}</td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800">
                                                {validation.days_overdue} days
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">{validation.current_status}</td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <div className="flex flex-col gap-1">
                                                <span className={`px-2 py-1 text-xs font-semibold rounded inline-block w-fit ${getCommentStatusBadge(validation.comment_status)}`}>
                                                    {getCommentStatusLabel(validation.comment_status)}
                                                </span>
                                                {validation.latest_comment && (
                                                    <span className="text-xs text-gray-500 truncate max-w-32" title={validation.latest_comment}>
                                                        "{validation.latest_comment.substring(0, 30)}..."
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {validation.target_completion_date || <span className="text-gray-400">-</span>}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <div className="flex gap-2">
                                                <Link
                                                    to={`/validation-workflow/${validation.request_id}`}
                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                >
                                                    View
                                                </Link>
                                                {validation.needs_comment_update && (
                                                    <button
                                                        onClick={() => openCommentaryModal(validation.request_id, 'VALIDATION_IN_PROGRESS', validation.model_name)}
                                                        className="text-red-600 hover:text-red-800 text-sm font-medium"
                                                    >
                                                        Add Commentary
                                                    </button>
                                                )}
                                            </div>
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
                                <button
                                    onClick={() => exportToCSV(upcomingRevalidations, 'upcoming_submissions', [
                                        { key: 'model_id', label: 'Model ID' },
                                        { key: 'model_name', label: 'Model Name' },
                                        { key: 'model_owner', label: 'Owner' },
                                        { key: 'risk_tier', label: 'Risk Tier' },
                                        { key: 'status', label: 'Status' },
                                        { key: 'last_validation_date', label: 'Last Validation' },
                                        { key: 'next_submission_due', label: 'Submission Due' },
                                        { key: 'next_validation_due', label: 'Validation Due' },
                                        { key: 'days_until_submission_due', label: 'Days Until Due' },
                                    ])}
                                    className="ml-auto text-blue-600 hover:text-blue-800"
                                    title="Export to CSV"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </button>
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

            {/* Commentary Modal */}
            {showCommentaryModal && commentaryModalRequestId && (
                <OverdueCommentaryModal
                    requestId={commentaryModalRequestId}
                    overdueType={commentaryModalType}
                    modelName={commentaryModalModelName}
                    onClose={() => {
                        setShowCommentaryModal(false);
                        setCommentaryModalRequestId(null);
                    }}
                    onSuccess={handleCommentarySuccess}
                />
            )}

            {/* UAT Tools Section - TEMPORARY */}
            <UATToolsSection onRefresh={fetchDashboardData} />
        </Layout>
    );
}

// UAT Tools Component - TEMPORARY - Remove before production
interface BackupInfo {
    backup_id: string;
    created_at: string;
    created_by: string;
    table_counts: Record<string, number>;
    total_rows: number;
    size_bytes: number;
    error?: string;
}

function UATToolsSection({ onRefresh }: { onRefresh: () => void }) {
    const [isResetting, setIsResetting] = useState(false);
    const [isSeeding, setIsSeeding] = useState(false);
    const [isBackingUp, setIsBackingUp] = useState(false);
    const [isRestoring, setIsRestoring] = useState(false);
    const [dataSummary, setDataSummary] = useState<Record<string, number> | null>(null);
    const [backups, setBackups] = useState<BackupInfo[]>([]);
    const [lastResult, setLastResult] = useState<{ type: string; message: string; details?: object } | null>(null);
    const [showConfirmReset, setShowConfirmReset] = useState(false);
    const [showConfirmRestore, setShowConfirmRestore] = useState<string | null>(null);
    const [showBackups, setShowBackups] = useState(false);

    const fetchDataSummary = async () => {
        try {
            const response = await api.get('/uat/data-summary');
            setDataSummary(response.data.transactional_data);
        } catch (error) {
            console.error('Failed to fetch data summary:', error);
        }
    };

    const fetchBackups = async () => {
        try {
            const response = await api.get('/uat/backups');
            setBackups(response.data.backups || []);
        } catch (error) {
            console.error('Failed to fetch backups:', error);
        }
    };

    useEffect(() => {
        fetchDataSummary();
        fetchBackups();
    }, []);

    const handleBackup = async () => {
        setIsBackingUp(true);
        setLastResult(null);
        try {
            const response = await api.post('/uat/backup');
            setLastResult({
                type: 'success',
                message: `Backup created: ${response.data.backup_id}`,
                details: {
                    total_rows: response.data.total_rows,
                    size_bytes: response.data.size_bytes,
                    table_counts: response.data.table_counts
                }
            });
            await fetchBackups();
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } };
            setLastResult({
                type: 'error',
                message: err.response?.data?.detail || 'Backup failed'
            });
        } finally {
            setIsBackingUp(false);
        }
    };

    const handleRestore = async (backupId: string) => {
        setShowConfirmRestore(null);
        setIsRestoring(true);
        setLastResult(null);
        try {
            const response = await api.post(`/uat/restore/${backupId}`);
            setLastResult({
                type: 'success',
                message: `Restored from backup: ${backupId}`,
                details: {
                    total_restored: response.data.total_restored,
                    restored_counts: response.data.restored_counts
                }
            });
            await fetchDataSummary();
            onRefresh();
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } };
            setLastResult({
                type: 'error',
                message: err.response?.data?.detail || 'Restore failed'
            });
        } finally {
            setIsRestoring(false);
        }
    };

    const handleDeleteBackup = async (backupId: string) => {
        try {
            await api.delete(`/uat/backups/${backupId}`);
            await fetchBackups();
            setLastResult({
                type: 'success',
                message: `Backup ${backupId} deleted`
            });
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } };
            setLastResult({
                type: 'error',
                message: err.response?.data?.detail || 'Delete failed'
            });
        }
    };

    const handleReset = async () => {
        setShowConfirmReset(false);
        setIsResetting(true);
        setLastResult(null);
        try {
            const response = await api.delete('/uat/reset-transactional-data');
            setLastResult({
                type: 'success',
                message: 'Transactional data reset complete',
                details: response.data
            });
            await fetchDataSummary();
            onRefresh();
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } };
            setLastResult({
                type: 'error',
                message: err.response?.data?.detail || 'Reset failed'
            });
        } finally {
            setIsResetting(false);
        }
    };

    const handleSeed = async () => {
        setIsSeeding(true);
        setLastResult(null);
        try {
            const response = await api.post('/uat/seed-uat-data');
            setLastResult({
                type: 'success',
                message: response.data.message,
                details: response.data.models_created
            });
            await fetchDataSummary();
            onRefresh();
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } };
            setLastResult({
                type: 'error',
                message: err.response?.data?.detail || 'Seeding failed'
            });
        } finally {
            setIsSeeding(false);
        }
    };

    const formatBytes = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const isOperating = isResetting || isSeeding || isBackingUp || isRestoring;

    return (
        <div className="mt-8 border-2 border-dashed border-red-300 rounded-lg p-4 bg-red-50">
            <div className="flex items-center gap-2 mb-4">
                <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <h3 className="text-lg font-bold text-red-900">UAT Tools</h3>
                <span className="text-xs bg-red-200 text-red-800 px-2 py-0.5 rounded">TEMPORARY - Remove before production</span>
            </div>

            <p className="text-sm text-red-700 mb-4">
                These tools are for User Acceptance Testing only. They allow you to reset all transactional data
                (models, validations, recommendations) while preserving configuration (taxonomies, policies, users).
            </p>

            {/* Data Summary */}
            {dataSummary && (
                <div className="mb-4 p-3 bg-white rounded border border-red-200">
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Current Data Summary</h4>
                    <div className="grid grid-cols-4 gap-2 text-sm">
                        {Object.entries(dataSummary).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                                <span className="text-gray-600">{key.replace(/_/g, ' ')}:</span>
                                <span className="font-medium">{value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3 mb-4">
                {/* Backup Button */}
                <button
                    onClick={handleBackup}
                    disabled={isOperating}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {isBackingUp ? (
                        <>
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            Creating Backup...
                        </>
                    ) : (
                        <>
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" />
                            </svg>
                            Create Backup
                        </>
                    )}
                </button>

                {/* View Backups Button */}
                <button
                    onClick={() => { setShowBackups(!showBackups); fetchBackups(); }}
                    disabled={isOperating}
                    className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                    </svg>
                    {showBackups ? 'Hide' : 'View'} Backups ({backups.length})
                </button>

                <div className="border-l border-red-300 mx-2"></div>

                {/* Reset Button */}
                <button
                    onClick={() => setShowConfirmReset(true)}
                    disabled={isOperating}
                    className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {isResetting ? (
                        <>
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            Resetting...
                        </>
                    ) : (
                        <>
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                            Reset All Data
                        </>
                    )}
                </button>

                {/* Seed Button */}
                <button
                    onClick={handleSeed}
                    disabled={isOperating}
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {isSeeding ? (
                        <>
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            Seeding...
                        </>
                    ) : (
                        <>
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM14 11a1 1 0 011 1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1h-1a1 1 0 110-2h1v-1a1 1 0 011-1z" />
                            </svg>
                            Seed UAT Data
                        </>
                    )}
                </button>

                {/* Refresh Button */}
                <button
                    onClick={() => { fetchDataSummary(); fetchBackups(); }}
                    disabled={isOperating}
                    className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                    </svg>
                    Refresh
                </button>
            </div>

            {/* Backups List */}
            {showBackups && (
                <div className="mb-4 p-3 bg-white rounded border border-blue-200">
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Available Backups</h4>
                    {backups.length === 0 ? (
                        <p className="text-sm text-gray-500">No backups available. Create one before resetting data.</p>
                    ) : (
                        <div className="space-y-2">
                            {backups.map((backup) => (
                                <div key={backup.backup_id} className="flex items-center justify-between p-2 bg-gray-50 rounded border">
                                    <div className="flex-1">
                                        <span className="font-mono text-sm font-medium">{backup.backup_id}</span>
                                        <div className="text-xs text-gray-500">
                                            {backup.created_at?.split('T')[0]} by {backup.created_by} • {backup.total_rows} rows • {formatBytes(backup.size_bytes)}
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setShowConfirmRestore(backup.backup_id)}
                                            disabled={isOperating}
                                            className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                                        >
                                            {isRestoring ? 'Restoring...' : 'Restore'}
                                        </button>
                                        <button
                                            onClick={() => handleDeleteBackup(backup.backup_id)}
                                            disabled={isOperating}
                                            className="px-3 py-1 text-sm bg-gray-400 text-white rounded hover:bg-gray-500 disabled:opacity-50"
                                        >
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Confirmation Modal for Reset */}
            {showConfirmReset && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-md">
                        <h4 className="text-lg font-bold text-red-900 mb-2">Confirm Data Reset</h4>
                        <p className="text-gray-700 mb-4">
                            This will permanently delete ALL models, validations, recommendations, monitoring data,
                            and audit logs. Configuration data (taxonomies, policies, users) will be preserved.
                        </p>
                        {backups.length === 0 && (
                            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                                <p className="text-yellow-800 text-sm font-medium">
                                    No backups found! Consider creating a backup first.
                                </p>
                            </div>
                        )}
                        <p className="text-red-600 font-semibold mb-4">This action cannot be undone without a backup!</p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setShowConfirmReset(false)}
                                className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                            >
                                Cancel
                            </button>
                            {backups.length === 0 && (
                                <button
                                    onClick={() => { setShowConfirmReset(false); handleBackup(); }}
                                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                >
                                    Create Backup First
                                </button>
                            )}
                            <button
                                onClick={handleReset}
                                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                            >
                                Yes, Reset All Data
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Confirmation Modal for Restore */}
            {showConfirmRestore && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-md">
                        <h4 className="text-lg font-bold text-blue-900 mb-2">Confirm Restore</h4>
                        <p className="text-gray-700 mb-4">
                            This will delete all current data and restore from backup <strong>{showConfirmRestore}</strong>.
                        </p>
                        <p className="text-orange-600 font-semibold mb-4">Current data will be replaced!</p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setShowConfirmRestore(null)}
                                className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => handleRestore(showConfirmRestore)}
                                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                                Yes, Restore
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Result Display */}
            {lastResult && (
                <div className={`mt-4 p-3 rounded border ${
                    lastResult.type === 'success'
                        ? 'bg-green-50 border-green-200 text-green-800'
                        : 'bg-red-100 border-red-300 text-red-800'
                }`}>
                    <p className="font-medium">{lastResult.message}</p>
                    {lastResult.details && (
                        <pre className="mt-2 text-xs overflow-auto max-h-40">
                            {JSON.stringify(lastResult.details as object, null, 2)}
                        </pre>
                    )}
                </div>
            )}
        </div>
    );
}

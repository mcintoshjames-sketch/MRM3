import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Layout from '../components/Layout';
import { recommendationsApi, Recommendation, TaxonomyValue } from '../api/recommendations';
import { listRecommendationLimitations, LimitationListItem } from '../api/limitations';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import { canManageRecommendations, canViewAdminDashboard } from '../utils/roleUtils';

// Import sub-components
import RecommendationWorkflowActions from '../components/RecommendationWorkflowActions';
import RebuttalModal from '../components/RebuttalModal';
import ActionPlanModal from '../components/ActionPlanModal';
import ClosureSubmitModal from '../components/ClosureSubmitModal';
import ClosureReviewModal from '../components/ClosureReviewModal';
import EvidenceSection from '../components/EvidenceSection';
import ApprovalSection from '../components/ApprovalSection';
import StatusTimeline from '../components/StatusTimeline';
import RecommendationEditModal from '../components/RecommendationEditModal';

interface User {
    user_id: number;
    email: string;
    full_name: string;
}

export default function RecommendationDetailPage() {
    const { id } = useParams<{ id: string }>();
    const { user } = useAuth();
    const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'details' | 'action-plan' | 'rebuttals' | 'evidence' | 'approvals' | 'history' | 'limitations'>('details');
    const [limitations, setLimitations] = useState<LimitationListItem[]>([]);

    // Modal states
    const [showRebuttalModal, setShowRebuttalModal] = useState(false);
    const [showActionPlanModal, setShowActionPlanModal] = useState(false);
    const [showClosureSubmitModal, setShowClosureSubmitModal] = useState(false);
    const [showClosureReviewModal, setShowClosureReviewModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);

    // Users for assignment dropdowns
    const [users, setUsers] = useState<User[]>([]);
    const [taskStatuses, setTaskStatuses] = useState<TaxonomyValue[]>([]);

    // Action plan skip state
    const [canSkipActionPlanState, setCanSkipActionPlanState] = useState(false);

    useEffect(() => {
        if (id) {
            fetchRecommendation();
            fetchUsers();
            fetchTaskStatuses();
            fetchLimitations();
        }
    }, [id]);

    // Fetch can-skip-action-plan status when recommendation changes
    useEffect(() => {
        if (recommendation?.recommendation_id) {
            fetchCanSkipActionPlan(recommendation.recommendation_id);
        }
    }, [recommendation?.recommendation_id, recommendation?.current_status_id]);

    const fetchRecommendation = async () => {
        try {
            setLoading(true);
            const data = await recommendationsApi.get(parseInt(id!));
            setRecommendation(data);
        } catch (err: any) {
            console.error('Failed to fetch recommendation:', err);
            setError(err.response?.data?.detail || 'Failed to load recommendation');
        } finally {
            setLoading(false);
        }
    };

    const fetchUsers = async () => {
        try {
            const response = await api.get('/auth/users');
            setUsers(response.data);
        } catch (err) {
            console.error('Failed to fetch users:', err);
        }
    };

    const fetchTaskStatuses = async () => {
        try {
            const taxonomiesRes = await api.get('/taxonomies/');
            const taskStatusTax = taxonomiesRes.data.find((t: any) => t.name === 'Action Plan Task Status');
            if (taskStatusTax) {
                const detailRes = await api.get(`/taxonomies/${taskStatusTax.taxonomy_id}`);
                setTaskStatuses(detailRes.data.values || []);
            }
        } catch (err) {
            console.error('Failed to fetch task statuses:', err);
        }
    };

    const fetchLimitations = async () => {
        try {
            const data = await listRecommendationLimitations(parseInt(id!));
            setLimitations(data);
        } catch (err) {
            console.error('Failed to fetch limitations:', err);
        }
    };

    const fetchCanSkipActionPlan = async (recId: number) => {
        try {
            const result = await recommendationsApi.canSkipActionPlan(recId);
            setCanSkipActionPlanState(result.can_skip_action_plan);
        } catch (err) {
            console.error('Failed to check if action plan can be skipped:', err);
            setCanSkipActionPlanState(false);
        }
    };

    // Permission helpers
    const canManageRecommendationsFlag = canManageRecommendations(user);
    const canViewAdminDashboardFlag = canViewAdminDashboard(user);
    const isAssignedDeveloper = recommendation?.assigned_to_id === user?.user_id;
    const currentStatus = recommendation?.current_status?.code || '';

    // Status-based permissions
    const canFinalize = canManageRecommendationsFlag && currentStatus === 'REC_DRAFT';
    const canSubmitRebuttal = (isAssignedDeveloper || canViewAdminDashboardFlag) && currentStatus === 'REC_PENDING_RESPONSE';
    const canSubmitActionPlan = (isAssignedDeveloper || canViewAdminDashboardFlag) &&
        (currentStatus === 'REC_PENDING_RESPONSE' || currentStatus === 'REC_PENDING_ACTION_PLAN');
    const canReviewRebuttal = canManageRecommendationsFlag && currentStatus === 'REC_IN_REBUTTAL';
    const canReviewActionPlan = canManageRecommendationsFlag && currentStatus === 'REC_PENDING_VALIDATOR_REVIEW';
    const canAcknowledge = (isAssignedDeveloper || canViewAdminDashboardFlag) && currentStatus === 'REC_PENDING_ACKNOWLEDGEMENT';
    const canSubmitForClosure = (isAssignedDeveloper || canViewAdminDashboardFlag) &&
        (currentStatus === 'REC_OPEN' || currentStatus === 'REC_REWORK_REQUIRED');
    const canReviewClosure = canManageRecommendationsFlag && currentStatus === 'REC_PENDING_CLOSURE_REVIEW';
    const canUploadEvidence = (isAssignedDeveloper || canViewAdminDashboardFlag) &&
        ['REC_OPEN', 'REC_REWORK_REQUIRED'].includes(currentStatus);
    // Skip action plan - must be assigned dev/admin and backend must confirm skip is allowed
    const canSkipActionPlan = (isAssignedDeveloper || canViewAdminDashboardFlag) && canSkipActionPlanState;
    // Edit recommendation - validators/admins can edit in certain statuses
    const editableStatuses = [
        'REC_DRAFT', 'REC_PENDING_RESPONSE', 'REC_PENDING_VALIDATOR_REVIEW',
        'REC_PENDING_ACKNOWLEDGEMENT', 'REC_OPEN', 'REC_REWORK_REQUIRED'
    ];
    const canEdit = canManageRecommendationsFlag && editableStatuses.includes(currentStatus);

    const getStatusColor = (code: string) => {
        switch (code) {
            case 'REC_DRAFT': return 'bg-gray-100 text-gray-800';
            case 'REC_PENDING_RESPONSE': return 'bg-blue-100 text-blue-800';
            case 'REC_PENDING_ACKNOWLEDGEMENT': return 'bg-indigo-100 text-indigo-800';
            case 'REC_IN_REBUTTAL': return 'bg-purple-100 text-purple-800';
            case 'REC_PENDING_ACTION_PLAN': return 'bg-yellow-100 text-yellow-800';
            case 'REC_PENDING_VALIDATOR_REVIEW': return 'bg-orange-100 text-orange-800';
            case 'REC_OPEN': return 'bg-green-100 text-green-800';
            case 'REC_REWORK_REQUIRED': return 'bg-red-100 text-red-800';
            case 'REC_PENDING_CLOSURE_REVIEW': return 'bg-cyan-100 text-cyan-800';
            case 'REC_PENDING_APPROVAL': return 'bg-amber-100 text-amber-800';
            case 'REC_CLOSED': return 'bg-emerald-100 text-emerald-800';
            case 'REC_DROPPED': return 'bg-gray-400 text-white';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getPriorityColor = (code: string) => {
        switch (code) {
            case 'HIGH': return 'bg-red-100 text-red-800';
            case 'MEDIUM': return 'bg-yellow-100 text-yellow-800';
            case 'LOW': return 'bg-green-100 text-green-800';
            case 'CONSIDERATION': return 'bg-blue-100 text-blue-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const isValidEvidenceUrl = (value?: string | null) => {
        if (!value) return false;
        try {
            const parsed = new URL(value);
            return ['http:', 'https:'].includes(parsed.protocol);
        } catch {
            return false;
        }
    };

    // Workflow action handlers
    const handleFinalize = async () => {
        if (!recommendation) return;
        try {
            // Submit draft to developer (DRAFT -> PENDING_RESPONSE)
            await recommendationsApi.submitToDeveloper(recommendation.recommendation_id);
            fetchRecommendation();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to submit recommendation to developer');
        }
    };

    const handleAcknowledge = async () => {
        if (!recommendation) return;
        try {
            await recommendationsApi.acknowledge(recommendation.recommendation_id);
            fetchRecommendation();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to acknowledge');
        }
    };

    const handleDeclineAcknowledge = async () => {
        if (!recommendation) return;
        const reason = prompt('Please provide reason for declining acknowledgement:');
        if (!reason) return;
        try {
            await recommendationsApi.declineAcknowledgement(recommendation.recommendation_id, reason);
            fetchRecommendation();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to decline');
        }
    };

    const handleSkipActionPlan = async () => {
        if (!recommendation) return;
        if (!confirm('Skip action plan for this recommendation? The validator will still need to review and approve.')) {
            return;
        }
        try {
            await recommendationsApi.skipActionPlan(recommendation.recommendation_id);
            fetchRecommendation();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to skip action plan');
        }
    };

    // Task update handler
    const handleUpdateTask = async (taskId: number, statusId: number, notes?: string) => {
        if (!recommendation) return;
        try {
            await recommendationsApi.updateTask(recommendation.recommendation_id, taskId, {
                completion_status_id: statusId,
                completion_notes: notes,
                completed_date: statusId === taskStatuses.find(s => s.code === 'TASK_COMPLETED')?.value_id
                    ? new Date().toISOString().split('T')[0]
                    : undefined
            });
            fetchRecommendation();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to update task');
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    if (error || !recommendation) {
        return (
            <Layout>
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                    {error || 'Recommendation not found'}
                </div>
            </Layout>
        );
    }

    const isTerminal = ['REC_CLOSED', 'REC_DROPPED'].includes(currentStatus);

    return (
        <Layout>
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
                    <Link to="/recommendations" className="hover:text-blue-600">Recommendations</Link>
                    <span>/</span>
                    <span>{recommendation.recommendation_code}</span>
                </div>
                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-3">
                            <span className="font-mono text-blue-600">{recommendation.recommendation_code}</span>
                            <span className={`px-2 py-1 text-sm rounded ${getStatusColor(currentStatus)}`}>
                                {recommendation.current_status?.label}
                            </span>
                            <span className={`px-2 py-1 text-sm rounded ${getPriorityColor(recommendation.priority?.code || '')}`}>
                                {recommendation.priority?.label}
                            </span>
                        </h1>
                        <h2 className="text-lg text-gray-700 mt-1">{recommendation.title}</h2>
                    </div>
                    {canEdit && (
                        <button
                            onClick={() => setShowEditModal(true)}
                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-2"
                        >
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            Edit
                        </button>
                    )}
                </div>

                {/* Key Info Row */}
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                        <span className="text-gray-500">Model:</span>{' '}
                        {recommendation.model_accessible !== false ? (
                            <Link to={`/models/${recommendation.model?.model_id}`} className="text-blue-600 hover:underline">
                                {recommendation.model?.model_name}
                            </Link>
                        ) : (
                            <span className="text-gray-900">{recommendation.model?.model_name}</span>
                        )}
                    </div>
                    <div>
                        <span className="text-gray-500">Assigned To:</span>{' '}
                        <span className="font-medium">{recommendation.assigned_to?.full_name}</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Created By:</span>{' '}
                        <span className="font-medium">{recommendation.created_by?.full_name}</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Target Date:</span>{' '}
                        <span className={`font-medium ${
                            !isTerminal && new Date(recommendation.current_target_date) < new Date()
                                ? 'text-red-600' : ''
                        }`}>
                            {recommendation.current_target_date}
                        </span>
                    </div>
                </div>

                {/* Source Linkage Row */}
                {(recommendation.validation_request_id || recommendation.monitoring_cycle_id) && (
                    <div className="mt-3 pt-3 border-t text-sm">
                        <span className="text-gray-500">Source:</span>{' '}
                        {recommendation.validation_request_id && recommendation.validation_request && (
                            <Link
                                to={`/validation-workflow/${recommendation.validation_request_id}`}
                                className="inline-flex items-center gap-1 text-blue-600 hover:underline"
                            >
                                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Validation {recommendation.validation_request.validation_code}
                                {recommendation.validation_request.validation_type && (
                                    <span className="text-gray-500">({recommendation.validation_request.validation_type})</span>
                                )}
                            </Link>
                        )}
                        {recommendation.monitoring_cycle_id && recommendation.monitoring_cycle && (
                            <Link
                                to={`/monitoring/plans`}
                                className="inline-flex items-center gap-1 text-purple-600 hover:underline"
                            >
                                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                                Monitoring Cycle ({recommendation.monitoring_cycle.period_start?.split('T')[0]} to {recommendation.monitoring_cycle.period_end?.split('T')[0]})
                                {recommendation.monitoring_cycle.plan_name && (
                                    <span className="text-gray-500"> - {recommendation.monitoring_cycle.plan_name}</span>
                                )}
                            </Link>
                        )}
                        {!recommendation.validation_request && !recommendation.monitoring_cycle && (
                            <span className="text-gray-500 italic">Standalone recommendation</span>
                        )}
                    </div>
                )}
            </div>

            {/* Terminal State Banner - CLOSED */}
            {currentStatus === 'REC_CLOSED' && (
                <div className="mb-6 bg-emerald-50 border border-emerald-200 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                        <div className="flex-shrink-0">
                            <svg className="h-6 w-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-emerald-800">Recommendation Closed</h3>
                            <div className="mt-2 text-sm text-emerald-700 space-y-1">
                                <p>
                                    <span className="font-medium">Closed on:</span>{' '}
                                    {recommendation.closed_at?.split('T')[0]}
                                </p>
                                {recommendation.closed_by && (
                                    <p>
                                        <span className="font-medium">Closed by:</span>{' '}
                                        {recommendation.closed_by.full_name}
                                    </p>
                                )}
                            </div>
                            {recommendation.closure_summary && (
                                <div className="mt-3 pt-3 border-t border-emerald-200">
                                    <h4 className="text-sm font-medium text-emerald-800 mb-1">Closure Summary</h4>
                                    <p className="text-sm text-emerald-700 whitespace-pre-wrap">{recommendation.closure_summary}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Terminal State Banner - DROPPED */}
            {currentStatus === 'REC_DROPPED' && (
                <div className="mb-6 bg-gray-100 border border-gray-300 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                        <div className="flex-shrink-0">
                            <svg className="h-6 w-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-gray-800">Recommendation Dropped</h3>
                            <p className="mt-2 text-sm text-gray-600">
                                This recommendation was dropped after the rebuttal was accepted by the validator.
                            </p>
                            {recommendation.rebuttals && recommendation.rebuttals.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-gray-300">
                                    <h4 className="text-sm font-medium text-gray-700 mb-1">Accepted Rebuttal</h4>
                                    {recommendation.rebuttals.filter(r => r.review_decision === 'ACCEPT').slice(-1).map(rebuttal => (
                                        <div key={rebuttal.rebuttal_id} className="text-sm text-gray-600">
                                            <p className="mb-1"><span className="font-medium">Accepted by:</span> {rebuttal.reviewed_by?.full_name} on {rebuttal.reviewed_at?.split('T')[0]}</p>
                                            <p className="whitespace-pre-wrap">{rebuttal.rationale}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Pending Final Approval Banner */}
            {currentStatus === 'REC_PENDING_APPROVAL' && (
                <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                        <div className="flex-shrink-0">
                            <svg className="h-6 w-6 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-amber-800">Pending Final Approval</h3>
                            <p className="mt-2 text-sm text-amber-700">
                                The validator has approved the closure. This recommendation is now awaiting final approval from required stakeholders before it can be closed.
                            </p>
                            {recommendation.approvals && recommendation.approvals.length > 0 && (
                                <div className="mt-3">
                                    <div className="flex items-center gap-4 text-sm">
                                        <span className="text-amber-700">
                                            <span className="font-medium">
                                                {recommendation.approvals.filter(a => a.approval_status === 'APPROVED').length}
                                            </span>
                                            {' '}of{' '}
                                            <span className="font-medium">
                                                {recommendation.approvals.filter(a => a.is_required).length}
                                            </span>
                                            {' '}required approvals received
                                        </span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Workflow Actions Panel */}
            {!isTerminal && (
                <RecommendationWorkflowActions
                    currentStatus={currentStatus}
                    canFinalize={canFinalize}
                    canSubmitRebuttal={canSubmitRebuttal}
                    canSubmitActionPlan={canSubmitActionPlan}
                    canSkipActionPlan={canSkipActionPlan}
                    canReviewRebuttal={canReviewRebuttal}
                    canReviewActionPlan={canReviewActionPlan}
                    canAcknowledge={canAcknowledge}
                    canSubmitForClosure={canSubmitForClosure}
                    canReviewClosure={canReviewClosure}
                    onFinalize={handleFinalize}
                    onAcknowledge={handleAcknowledge}
                    onDeclineAcknowledge={handleDeclineAcknowledge}
                    onShowRebuttalModal={() => setShowRebuttalModal(true)}
                    onShowActionPlanModal={() => setShowActionPlanModal(true)}
                    onSkipActionPlan={handleSkipActionPlan}
                    onShowClosureSubmitModal={() => setShowClosureSubmitModal(true)}
                    onShowClosureReviewModal={() => setShowClosureReviewModal(true)}
                    onRefresh={fetchRecommendation}
                />
            )}

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-4">
                <nav className="-mb-px flex space-x-8">
                    {[
                        { key: 'details', label: 'Details' },
                        { key: 'action-plan', label: `Action Plan (${recommendation.action_plan_tasks?.length || 0})` },
                        { key: 'rebuttals', label: `Rebuttals (${recommendation.rebuttals?.length || 0})` },
                        { key: 'evidence', label: `Evidence (${recommendation.closure_evidence?.length || 0})` },
                        { key: 'approvals', label: `Approvals (${recommendation.approvals?.length || 0})` },
                        { key: 'limitations', label: `Limitations (${limitations.length})` },
                        { key: 'history', label: 'History' },
                    ].map(tab => (
                        <button
                            key={tab.key}
                            onClick={() => setActiveTab(tab.key as any)}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === tab.key
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </nav>
            </div>

            {/* Tab Content */}
            <div className="bg-white rounded-lg shadow-md p-6">
                {/* Details Tab */}
                {activeTab === 'details' && (
                    <div className="space-y-6">
                        <div>
                            <h3 className="text-sm font-medium text-gray-500 mb-1">Description</h3>
                            <p className="text-gray-900 whitespace-pre-wrap">{recommendation.description}</p>
                        </div>
                        {recommendation.root_cause_analysis && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1">Root Cause Analysis</h3>
                                <p className="text-gray-900 whitespace-pre-wrap">{recommendation.root_cause_analysis}</p>
                            </div>
                        )}
                        {recommendation.category && (
                            <div>
                                <h3 className="text-sm font-medium text-gray-500 mb-1">Category</h3>
                                <span className="inline-block px-2 py-1 bg-gray-100 text-gray-800 text-sm rounded">
                                    {recommendation.category.label}
                                </span>
                            </div>
                        )}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
                            <div>
                                <h3 className="text-sm font-medium text-gray-500">Original Target</h3>
                                <p>{recommendation.original_target_date}</p>
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-gray-500">Current Target</h3>
                                <p>{recommendation.current_target_date}</p>
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-gray-500">Created</h3>
                                <p>{recommendation.created_at?.split('T')[0]}</p>
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-gray-500">Last Updated</h3>
                                <p>{recommendation.updated_at?.split('T')[0]}</p>
                            </div>
                        </div>
                        {recommendation.closure_summary && (
                            <div className="pt-4 border-t">
                                <h3 className="text-sm font-medium text-gray-500 mb-1">Closure Summary</h3>
                                <p className="text-gray-900 whitespace-pre-wrap">{recommendation.closure_summary}</p>
                            </div>
                        )}
                    </div>
                )}

                {/* Action Plan Tab */}
                {activeTab === 'action-plan' && (
                    <div>
                        {recommendation.action_plan_tasks && recommendation.action_plan_tasks.length > 0 ? (
                            <div className="space-y-4">
                                {recommendation.action_plan_tasks.map((task, index) => (
                                    <div key={task.task_id} className="border rounded-lg p-4">
                                        <div className="flex justify-between items-start">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <span className="text-sm font-medium text-gray-500">Task {index + 1}</span>
                                                    <span className={`px-2 py-0.5 text-xs rounded ${
                                                        task.completion_status?.code === 'TASK_COMPLETED'
                                                            ? 'bg-green-100 text-green-800'
                                                            : task.completion_status?.code === 'TASK_IN_PROGRESS'
                                                                ? 'bg-blue-100 text-blue-800'
                                                                : 'bg-gray-100 text-gray-800'
                                                    }`}>
                                                        {task.completion_status?.label}
                                                    </span>
                                                </div>
                                                <p className="text-gray-900">{task.description}</p>
                                                <div className="mt-2 text-sm text-gray-500">
                                                    <span>Owner: {task.owner?.full_name}</span>
                                                    <span className="mx-2">•</span>
                                                    <span>Target: {task.target_date}</span>
                                                    {task.completed_date && (
                                                        <>
                                                            <span className="mx-2">•</span>
                                                            <span className="text-green-600">Completed: {task.completed_date}</span>
                                                        </>
                                                    )}
                                                </div>
                                                {task.completion_notes && (
                                                    <p className="mt-2 text-sm text-gray-600 italic">{task.completion_notes}</p>
                                                )}
                                            </div>
                                            {/* Task status update dropdown - only for task owner or admin when in OPEN status */}
                                            {(currentStatus === 'REC_OPEN' || currentStatus === 'REC_REWORK_REQUIRED') &&
                                             (task.owner?.user_id === user?.user_id || canViewAdminDashboardFlag) && (
                                                <select
                                                    className="ml-4 text-sm border rounded px-2 py-1"
                                                    value={task.completion_status?.value_id ?? task.completion_status_id}
                                                    onChange={(e) => handleUpdateTask(task.task_id, parseInt(e.target.value))}
                                                >
                                                    {taskStatuses.map(status => (
                                                        <option key={status.value_id} value={status.value_id}>
                                                            {status.label}
                                                        </option>
                                                    ))}
                                                </select>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-gray-500 text-center py-8">No action plan tasks defined yet.</p>
                        )}
                    </div>
                )}

                {/* Rebuttals Tab */}
                {activeTab === 'rebuttals' && (
                    <div>
                        {recommendation.rebuttals && recommendation.rebuttals.length > 0 ? (
                            <div className="space-y-4">
                                {recommendation.rebuttals.map((rebuttal) => (
                                    <div key={rebuttal.rebuttal_id} className={`border rounded-lg p-4 ${
                                        rebuttal.is_current ? 'border-blue-300 bg-blue-50' : ''
                                    }`}>
                                        <div className="flex justify-between items-start mb-2">
                                            <div className="flex items-center gap-2">
                                                <span className="font-medium">{rebuttal.submitted_by?.full_name}</span>
                                                {rebuttal.is_current && (
                                                    <span className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded">Current</span>
                                                )}
                                            </div>
                                            <span className="text-sm text-gray-500">
                                                {rebuttal.submitted_at?.split('T')[0]}
                                            </span>
                                        </div>
                                        <div className="mb-3">
                                            <h4 className="text-sm font-medium text-gray-500 mb-1">Rationale</h4>
                                            <p className="text-gray-900 whitespace-pre-wrap">{rebuttal.rationale}</p>
                                        </div>
                                        {rebuttal.supporting_evidence && (
                                            <div className="mb-3">
                                                <h4 className="text-sm font-medium text-gray-500 mb-1">Supporting Evidence</h4>
                                                {isValidEvidenceUrl(rebuttal.supporting_evidence) ? (
                                                    <a
                                                        href={rebuttal.supporting_evidence}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-blue-600 hover:underline break-all"
                                                    >
                                                        {rebuttal.supporting_evidence}
                                                    </a>
                                                ) : (
                                                    <p className="text-gray-900 whitespace-pre-wrap">{rebuttal.supporting_evidence}</p>
                                                )}
                                            </div>
                                        )}
                                        {rebuttal.review_decision && (
                                            <div className="mt-3 pt-3 border-t">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className={`px-2 py-0.5 text-xs rounded ${
                                                        rebuttal.review_decision === 'ACCEPT'
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-red-100 text-red-800'
                                                    }`}>
                                                        {rebuttal.review_decision === 'ACCEPT' ? 'Accepted' : 'Overridden'}
                                                    </span>
                                                    <span className="text-sm text-gray-500">
                                                        by {rebuttal.reviewed_by?.full_name} on {rebuttal.reviewed_at?.split('T')[0]}
                                                    </span>
                                                </div>
                                                {rebuttal.review_comments && (
                                                    <p className="text-sm text-gray-700 mt-1">{rebuttal.review_comments}</p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-gray-500 text-center py-8">No rebuttals submitted.</p>
                        )}
                    </div>
                )}

                {/* Evidence Tab */}
                {activeTab === 'evidence' && (
                    <EvidenceSection
                        recommendation={recommendation}
                        canUpload={canUploadEvidence}
                        onRefresh={fetchRecommendation}
                    />
                )}

                {/* Approvals Tab */}
                {activeTab === 'approvals' && (
                    <ApprovalSection
                        recommendation={recommendation}
                        currentUser={user}
                        onRefresh={fetchRecommendation}
                    />
                )}

                {/* Limitations Tab */}
                {activeTab === 'limitations' && (
                    <div>
                        {limitations.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Significance</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Conclusion</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {limitations.map(limitation => (
                                            <tr key={limitation.limitation_id}>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                                    #{limitation.limitation_id}
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs rounded ${
                                                        limitation.significance === 'Critical'
                                                            ? 'bg-red-100 text-red-800'
                                                            : 'bg-blue-100 text-blue-800'
                                                    }`}>
                                                        {limitation.significance}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                                    {limitation.category?.label || '-'}
                                                </td>
                                                <td className="px-4 py-2 text-sm text-gray-900 max-w-xs truncate" title={limitation.description}>
                                                    {limitation.description.length > 80
                                                        ? `${limitation.description.substring(0, 80)}...`
                                                        : limitation.description}
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs rounded ${
                                                        limitation.conclusion === 'Mitigate'
                                                            ? 'bg-yellow-100 text-yellow-800'
                                                            : 'bg-green-100 text-green-800'
                                                    }`}>
                                                        {limitation.conclusion}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                                                    {limitation.created_at?.split('T')[0]}
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                    <Link
                                                        to={`/models/${limitation.model_id}?tab=limitations`}
                                                        className="text-blue-600 hover:text-blue-800 hover:underline"
                                                    >
                                                        View on Model
                                                    </Link>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <p className="text-gray-500 text-center py-8">No limitations linked to this recommendation.</p>
                        )}
                    </div>
                )}

                {/* History Tab */}
                {activeTab === 'history' && (
                    <StatusTimeline statusHistory={recommendation.status_history || []} />
                )}
            </div>

            {/* Modals */}
            {showRebuttalModal && (
                <RebuttalModal
                    recommendation={recommendation}
                    onClose={() => setShowRebuttalModal(false)}
                    onSuccess={() => {
                        setShowRebuttalModal(false);
                        fetchRecommendation();
                    }}
                />
            )}

            {showActionPlanModal && (
                <ActionPlanModal
                    recommendation={recommendation}
                    users={users}
                    onClose={() => setShowActionPlanModal(false)}
                    onSuccess={() => {
                        setShowActionPlanModal(false);
                        fetchRecommendation();
                    }}
                />
            )}

            {showClosureSubmitModal && (
                <ClosureSubmitModal
                    recommendation={recommendation}
                    onClose={() => setShowClosureSubmitModal(false)}
                    onSuccess={() => {
                        setShowClosureSubmitModal(false);
                        fetchRecommendation();
                    }}
                />
            )}

            {showClosureReviewModal && (
                <ClosureReviewModal
                    recommendation={recommendation}
                    onClose={() => setShowClosureReviewModal(false)}
                    onSuccess={() => {
                        setShowClosureReviewModal(false);
                        fetchRecommendation();
                    }}
                />
            )}

            {showEditModal && (
                <RecommendationEditModal
                    recommendation={recommendation}
                    isOpen={showEditModal}
                    onClose={() => setShowEditModal(false)}
                    onSave={() => {
                        setShowEditModal(false);
                        fetchRecommendation();
                    }}
                />
            )}
        </Layout>
    );
}

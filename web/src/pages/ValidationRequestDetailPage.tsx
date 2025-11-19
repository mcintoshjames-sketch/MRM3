import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
}

interface UserSummary {
    user_id: number;
    full_name: string;
    email: string;
    role: string;
}

interface ModelSummary {
    model_id: number;
    model_name: string;
    status: string;
}

interface ValidationAssignment {
    assignment_id: number;
    request_id: number;
    validator: UserSummary;
    is_primary: boolean;
    is_reviewer: boolean;
    assignment_date: string;
    estimated_hours: number | null;
    actual_hours: number | null;
    independence_attestation: boolean;
    reviewer_signed_off: boolean;
    reviewer_signed_off_at: string | null;
    reviewer_sign_off_comments: string | null;
    created_at: string;
}

interface ValidationOutcome {
    outcome_id: number;
    request_id: number;
    overall_rating: TaxonomyValue;
    executive_summary: string;
    recommended_review_frequency: number;
    effective_date: string;
    expiration_date: string | null;
    created_at: string;
    updated_at: string;
}

interface ValidationApproval {
    approval_id: number;
    request_id: number;
    approver: UserSummary;
    approver_role: string;
    is_required: boolean;
    approval_status: string;
    comments: string | null;
    approved_at: string | null;
    created_at: string;
}

interface ValidationStatusHistory {
    history_id: number;
    request_id: number;
    old_status: TaxonomyValue | null;
    new_status: TaxonomyValue;
    changed_by: UserSummary;
    change_reason: string | null;
    changed_at: string;
}

interface AuditLog {
    log_id: number;
    entity_type: string;
    entity_id: number;
    action: string;
    user_id: number;
    changes: any;
    timestamp: string;
    user: UserSummary;
}

interface ModelVersion {
    version_id: number;
    version_number: string;
    change_type: string;
    change_description: string;
    production_date: string | null;
    status: string;
    created_at: string;
    created_by_name: string;
}

interface ValidationRequestDetail {
    request_id: number;
    models: ModelSummary[];  // Support multiple models
    request_date: string;
    requestor: UserSummary;
    validation_type: TaxonomyValue;
    priority: TaxonomyValue;
    target_completion_date: string;
    trigger_reason: string | null;
    current_status: TaxonomyValue;
    created_at: string;
    updated_at: string;
    assignments: ValidationAssignment[];
    status_history: ValidationStatusHistory[];
    approvals: ValidationApproval[];
    outcome: ValidationOutcome | null;
    review_outcome: ValidationReviewOutcome | null;
}

interface ValidationReviewOutcome {
    review_outcome_id: number;
    request_id: number;
    reviewer: UserSummary;
    decision: string;
    comments: string | null;
    agrees_with_rating: boolean | null;
    review_date: string;
    created_at: string;
    updated_at: string;
}

type TabType = 'overview' | 'assignments' | 'outcome' | 'review' | 'approvals' | 'history';

export default function ValidationRequestDetailPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();
    const [searchParams, setSearchParams] = useSearchParams();
    const [request, setRequest] = useState<ValidationRequestDetail | null>(null);
    const [relatedVersions, setRelatedVersions] = useState<ModelVersion[]>([]);
    const [allAuditLogs, setAllAuditLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [actionLoading, setActionLoading] = useState(false);

    // Form states
    const [showStatusModal, setShowStatusModal] = useState(false);
    const [showAssignmentModal, setShowAssignmentModal] = useState(false);
    const [showEditAssignmentModal, setShowEditAssignmentModal] = useState(false);
    const [showOutcomeModal, setShowOutcomeModal] = useState(false);
    const [showApprovalModal, setShowApprovalModal] = useState(false);

    const [statusOptions, setStatusOptions] = useState<TaxonomyValue[]>([]);
    const [ratingOptions, setRatingOptions] = useState<TaxonomyValue[]>([]);
    const [users, setUsers] = useState<UserSummary[]>([]);

    const [newStatus, setNewStatus] = useState({ status_id: 0, reason: '' });
    const [newAssignment, setNewAssignment] = useState({
        validator_id: 0,
        is_primary: false,
        is_reviewer: false,
        estimated_hours: '',
        independence_attestation: false
    });
    const [newOutcome, setNewOutcome] = useState({
        overall_rating_id: 0,
        executive_summary: '',
        recommended_review_frequency: 12,
        effective_date: new Date().toISOString().split('T')[0],
        expiration_date: ''
    });
    const [approvalUpdate, setApprovalUpdate] = useState({ approval_id: 0, status: '', comments: '' });
    const [newReviewOutcome, setNewReviewOutcome] = useState({
        decision: '',
        comments: '',
        agrees_with_rating: null as boolean | null
    });
    const [showSignOffModal, setShowSignOffModal] = useState(false);
    const [signOffData, setSignOffData] = useState({ assignment_id: 0, comments: '' });
    const [editAssignment, setEditAssignment] = useState({
        assignment_id: 0,
        is_primary: false,
        is_reviewer: false,
        estimated_hours: '',
        actual_hours: ''
    });
    const [showSelectPrimaryModal, setShowSelectPrimaryModal] = useState(false);
    const [deleteAssignmentData, setDeleteAssignmentData] = useState({ assignment_id: 0, new_primary_id: 0 });

    useEffect(() => {
        fetchData();
    }, [id]);

    // Auto-open assignment modal if URL parameter is present
    useEffect(() => {
        if (searchParams.get('assignValidator') === 'true' && !loading) {
            setActiveTab('assignments');
            setShowAssignmentModal(true);
            // Clear the URL parameter after opening
            searchParams.delete('assignValidator');
            setSearchParams(searchParams, { replace: true });
        }
    }, [searchParams, loading]);

    // Set Primary checkbox default based on existing assignments
    useEffect(() => {
        if (showAssignmentModal && request) {
            // Check if there's already a primary validator
            const hasPrimary = request.assignments?.some(a => a.is_primary) || false;

            // If no primary exists, default the checkbox to true
            setNewAssignment(prev => ({
                ...prev,
                is_primary: !hasPrimary
            }));
        } else if (!showAssignmentModal) {
            // Reset form when modal closes
            setNewAssignment({
                validator_id: 0,
                is_primary: false,
                is_reviewer: false,
                estimated_hours: '',
                independence_attestation: false
            });
        }
    }, [showAssignmentModal, request]);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch request details, taxonomy options, users, and all audit logs in parallel
            const [requestRes, taxonomiesRes, usersRes, assignmentAuditRes, outcomeAuditRes, reviewAuditRes] = await Promise.all([
                api.get(`/validation-workflow/requests/${id}`),
                api.get('/taxonomies/'),
                api.get('/auth/users'),
                api.get(`/audit-logs/?entity_type=ValidationAssignment&entity_id=${id}&limit=100`),
                api.get(`/audit-logs/?entity_type=ValidationOutcome&entity_id=${id}&limit=100`),
                api.get(`/audit-logs/?entity_type=ValidationReviewOutcome&entity_id=${id}&limit=100`)
            ]);

            setRequest(requestRes.data);
            setUsers(usersRes.data);

            // Combine all audit logs
            const combinedAuditLogs = [
                ...assignmentAuditRes.data,
                ...outcomeAuditRes.data,
                ...reviewAuditRes.data
            ];
            setAllAuditLogs(combinedAuditLogs);

            // Fetch model versions for all associated models that link to this validation request
            if (requestRes.data.models && requestRes.data.models.length > 0 && id) {
                try {
                    // Fetch versions for all models in parallel
                    const versionPromises = requestRes.data.models.map((model: ModelSummary) =>
                        api.get(`/models/${model.model_id}/versions`)
                    );
                    const versionResults = await Promise.all(versionPromises);

                    // Combine and filter versions that link to this validation request
                    const allVersions = versionResults.flatMap(res => res.data);
                    const linkedVersions = allVersions.filter((v: any) => v.validation_request_id === parseInt(id));
                    setRelatedVersions(linkedVersions);
                } catch (err) {
                    console.error('Failed to fetch related versions:', err);
                }
            }

            // Fetch taxonomy values
            const taxDetails = await Promise.all(
                taxonomiesRes.data.map((t: any) => api.get(`/taxonomies/${t.taxonomy_id}`))
            );
            const taxonomies = taxDetails.map((r: any) => r.data);

            const statusTax = taxonomies.find((t: any) => t.name === 'Validation Request Status');
            const ratingTax = taxonomies.find((t: any) => t.name === 'Overall Rating');

            if (statusTax) setStatusOptions(statusTax.values || []);
            if (ratingTax) setRatingOptions(ratingTax.values || []);

        } catch (err: any) {
            console.error('Failed to fetch request details:', err);
            setError(err.response?.data?.detail || 'Failed to load validation request');
        } finally {
            setLoading(false);
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

    const getApprovalStatusColor = (status: string) => {
        switch (status) {
            case 'Pending': return 'bg-yellow-100 text-yellow-800';
            case 'Approved': return 'bg-green-100 text-green-800';
            case 'Rejected': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const handleStatusUpdate = async () => {
        if (!newStatus.status_id) return;
        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/requests/${id}/status`, {
                new_status_id: newStatus.status_id,
                change_reason: newStatus.reason || null
            });
            setShowStatusModal(false);
            setNewStatus({ status_id: 0, reason: '' });
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update status');
        } finally {
            setActionLoading(false);
        }
    };

    const handleAddAssignment = async () => {
        if (!newAssignment.validator_id || !newAssignment.independence_attestation) {
            setError('Validator and independence attestation are required');
            return;
        }
        setActionLoading(true);
        try {
            await api.post(`/validation-workflow/requests/${id}/assignments`, {
                validator_id: newAssignment.validator_id,
                is_primary: newAssignment.is_primary,
                is_reviewer: newAssignment.is_reviewer,
                estimated_hours: newAssignment.estimated_hours ? parseFloat(newAssignment.estimated_hours) : null,
                independence_attestation: newAssignment.independence_attestation
            });
            setShowAssignmentModal(false);
            setNewAssignment({ validator_id: 0, is_primary: false, is_reviewer: false, estimated_hours: '', independence_attestation: false });
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to add assignment');
        } finally {
            setActionLoading(false);
        }
    };

    const handleReviewerSignOff = async () => {
        setActionLoading(true);
        try {
            await api.post(`/validation-workflow/assignments/${signOffData.assignment_id}/sign-off`, {
                comments: signOffData.comments || null
            });
            setShowSignOffModal(false);
            setSignOffData({ assignment_id: 0, comments: '' });
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to sign off');
        } finally {
            setActionLoading(false);
        }
    };

    const handleEditAssignment = async () => {
        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/assignments/${editAssignment.assignment_id}`, {
                is_primary: editAssignment.is_primary,
                is_reviewer: editAssignment.is_reviewer,
                estimated_hours: editAssignment.estimated_hours ? parseFloat(editAssignment.estimated_hours) : null,
                actual_hours: editAssignment.actual_hours ? parseFloat(editAssignment.actual_hours) : null
            });
            setShowEditAssignmentModal(false);
            setEditAssignment({ assignment_id: 0, is_primary: false, is_reviewer: false, estimated_hours: '', actual_hours: '' });
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update assignment');
        } finally {
            setActionLoading(false);
        }
    };

    const handleDeleteAssignment = async (assignmentId: number, newPrimaryId?: number) => {
        const assignment = request?.assignments.find(a => a.assignment_id === assignmentId);
        if (!assignment) return;

        // Check if this is the last validator
        if (request && request.assignments.length <= 1) {
            setError('Cannot remove the last validator. Assign another validator before removing this one.');
            return;
        }

        // If removing primary with multiple remaining validators and no new primary selected
        if (assignment.is_primary && request && request.assignments.length > 2 && !newPrimaryId) {
            // Show modal to select new primary
            setDeleteAssignmentData({ assignment_id: assignmentId, new_primary_id: 0 });
            setShowSelectPrimaryModal(true);
            return;
        }

        // Confirm deletion
        if (!confirm(`Are you sure you want to remove ${assignment.validator.full_name} from this validation?`)) return;

        setActionLoading(true);
        try {
            const url = newPrimaryId
                ? `/validation-workflow/assignments/${assignmentId}?new_primary_id=${newPrimaryId}`
                : `/validation-workflow/assignments/${assignmentId}`;
            await api.delete(url);
            setShowSelectPrimaryModal(false);
            setDeleteAssignmentData({ assignment_id: 0, new_primary_id: 0 });
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to delete assignment');
        } finally {
            setActionLoading(false);
        }
    };

    const confirmDeleteWithNewPrimary = () => {
        if (!deleteAssignmentData.new_primary_id) {
            setError('Please select a new primary validator');
            return;
        }
        handleDeleteAssignment(deleteAssignmentData.assignment_id, deleteAssignmentData.new_primary_id);
    };

    const handleCreateOutcome = async () => {
        if (!newOutcome.overall_rating_id || !newOutcome.executive_summary) {
            setError('Rating and executive summary are required');
            return;
        }
        setActionLoading(true);
        try {
            await api.post(`/validation-workflow/requests/${id}/outcome`, {
                overall_rating_id: newOutcome.overall_rating_id,
                executive_summary: newOutcome.executive_summary,
                recommended_review_frequency: newOutcome.recommended_review_frequency,
                effective_date: newOutcome.effective_date,
                expiration_date: newOutcome.expiration_date || null
            });
            setShowOutcomeModal(false);
            setNewOutcome({
                overall_rating_id: 0,
                executive_summary: '',
                recommended_review_frequency: 12,
                effective_date: new Date().toISOString().split('T')[0],
                expiration_date: ''
            });
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create outcome');
        } finally {
            setActionLoading(false);
        }
    };

    const handleUpdateOutcome = async () => {
        if (!request?.outcome) return;
        if (!newOutcome.overall_rating_id || !newOutcome.executive_summary) {
            setError('Rating and executive summary are required');
            return;
        }
        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/outcomes/${request.outcome.outcome_id}`, {
                overall_rating_id: newOutcome.overall_rating_id,
                executive_summary: newOutcome.executive_summary,
                recommended_review_frequency: newOutcome.recommended_review_frequency,
                effective_date: newOutcome.effective_date,
                expiration_date: newOutcome.expiration_date || null
            });
            setShowOutcomeModal(false);
            setNewOutcome({
                overall_rating_id: 0,
                executive_summary: '',
                recommended_review_frequency: 12,
                effective_date: new Date().toISOString().split('T')[0],
                expiration_date: ''
            });
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update outcome');
        } finally {
            setActionLoading(false);
        }
    };

    const handleApprovalUpdate = async () => {
        if (!approvalUpdate.status) {
            setError('Approval status is required');
            return;
        }
        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/approvals/${approvalUpdate.approval_id}`, {
                approval_status: approvalUpdate.status,
                comments: approvalUpdate.comments || null
            });
            setShowApprovalModal(false);
            setApprovalUpdate({ approval_id: 0, status: '', comments: '' });
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update approval');
        } finally {
            setActionLoading(false);
        }
    };

    const handleCreateReviewOutcome = async () => {
        if (!newReviewOutcome.decision) {
            setError('Decision is required');
            return;
        }
        setActionLoading(true);
        try {
            await api.post(`/validation-workflow/requests/${id}/review-outcome`, {
                decision: newReviewOutcome.decision,
                comments: newReviewOutcome.comments || null,
                agrees_with_rating: newReviewOutcome.agrees_with_rating
            });
            setNewReviewOutcome({ decision: '', comments: '', agrees_with_rating: null });
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create review outcome');
        } finally {
            setActionLoading(false);
        }
    };

    const handleBeginWork = async () => {
        if (!request) return;

        // Find "In Progress" status
        const inProgressStatus = statusOptions.find(s => s.code === 'IN_PROGRESS');
        if (!inProgressStatus) {
            setError('In Progress status not found');
            return;
        }

        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/requests/${id}/status`, {
                new_status_id: inProgressStatus.value_id,
                change_reason: 'Beginning validation work'
            });
            await fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to begin work');
        } finally {
            setActionLoading(false);
        }
    };

    const handleCompleteWork = async () => {
        if (!request) return;

        // Check if outcome has been created
        if (!request.outcome) {
            setError('Cannot complete work without creating a validation outcome. Please go to the Outcome tab and complete the validation outcome form.');
            return;
        }

        // Check if there's a reviewer assigned
        const hasReviewer = request.assignments.some(a => a.is_reviewer);

        let targetStatusCode = 'PENDING_APPROVAL';
        let warningMessage = '';

        if (hasReviewer) {
            targetStatusCode = 'REVIEW';
        } else {
            warningMessage = 'No reviewer is assigned to this validation. The validation will move directly to Pending Approval, skipping the review step. ';
        }

        const confirmMessage = warningMessage + 'Are you sure you want to complete this validation?';
        if (!confirm(confirmMessage)) return;

        const targetStatus = statusOptions.find(s => s.code === targetStatusCode);
        if (!targetStatus) {
            setError(`${targetStatusCode} status not found`);
            return;
        }

        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/requests/${id}/status`, {
                new_status_id: targetStatus.value_id,
                change_reason: hasReviewer ? 'Work completed, ready for review' : 'Work completed, moving to approval (no reviewer assigned)'
            });
            await fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to complete work');
        } finally {
            setActionLoading(false);
        }
    };

    const canEditRequest = user?.role === 'Admin' || user?.role === 'Validator';
    const isPrimaryValidator = request && user && request.assignments.some(
        a => a.is_primary && a.validator.user_id === user.user_id
    );
    const isReviewer = request && user && request.assignments.some(
        a => a.is_reviewer && a.validator.user_id === user.user_id
    );

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    if (!request) {
        return (
            <Layout>
                <div className="text-center">
                    <h2 className="text-2xl font-bold mb-4">Validation Request Not Found</h2>
                    <button onClick={() => navigate('/validation-workflow')} className="btn-primary">
                        Back to Validation Workflow
                    </button>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <button
                        onClick={() => navigate('/validation-workflow')}
                        className="text-blue-600 hover:text-blue-800 text-sm mb-2"
                    >
                        &larr; Back to Validation Workflow
                    </button>
                    <h2 className="text-2xl font-bold">
                        Validation Request #{request.request_id}
                    </h2>
                    <div className="flex items-center gap-3 mt-2 flex-wrap">
                        <div className="flex items-center gap-2">
                            <span className="text-sm text-gray-600">Models:</span>
                            {request.models.map((model, idx) => (
                                <span key={model.model_id}>
                                    <Link
                                        to={`/models/${model.model_id}`}
                                        className="text-blue-600 hover:text-blue-800 font-medium"
                                    >
                                        {model.model_name}
                                    </Link>
                                    {idx < request.models.length - 1 && <span className="text-gray-400">, </span>}
                                </span>
                            ))}
                        </div>
                        <span className={`px-2 py-1 text-xs rounded ${getStatusColor(request.current_status.label)}`}>
                            {request.current_status.label}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(request.priority.label)}`}>
                            {request.priority.label} Priority
                        </span>
                    </div>
                </div>
                <div className="flex gap-2">
                    {/* Begin Work Button */}
                    {isPrimaryValidator &&
                     (request.current_status.code === 'INTAKE' || request.current_status.code === 'PLANNING') && (
                        <button
                            onClick={handleBeginWork}
                            disabled={actionLoading}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                        >
                            {actionLoading ? 'Starting...' : 'Begin Work'}
                        </button>
                    )}

                    {/* Complete Work Button */}
                    {isPrimaryValidator && request.current_status.code === 'IN_PROGRESS' && (
                        <button
                            onClick={handleCompleteWork}
                            disabled={actionLoading}
                            className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
                        >
                            {actionLoading ? 'Completing...' : 'Complete Work'}
                        </button>
                    )}

                    {/* Update Status Button (for admins/validators) */}
                    {canEditRequest && (
                        <button
                            onClick={() => setShowStatusModal(true)}
                            className="btn-primary"
                        >
                            Update Status
                        </button>
                    )}
                </div>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                    <button onClick={() => setError(null)} className="float-right font-bold">×</button>
                </div>
            )}

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="-mb-px flex space-x-8">
                    {(['overview', 'assignments', 'outcome', ...(isReviewer ? ['review'] as TabType[] : []), 'approvals', 'history'] as TabType[]).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`py-2 px-1 border-b-2 font-medium text-sm capitalize ${
                                activeTab === tab
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            {tab}
                            {tab === 'assignments' && ` (${request.assignments.length})`}
                            {tab === 'approvals' && ` (${request.approvals.length})`}
                            {tab === 'history' && ` (${request.status_history.length})`}
                        </button>
                    ))}
                </nav>
            </div>

            {/* Tab Content */}
            <div className="bg-white rounded-lg shadow-md p-6">
                {activeTab === 'overview' && (
                    <div>
                        <h3 className="text-lg font-bold mb-4">Request Overview</h3>
                        <div className="grid grid-cols-2 gap-6">
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Request ID</h4>
                                <p className="text-lg font-mono">#{request.request_id}</p>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Models ({request.models.length})</h4>
                                <div className="flex flex-col gap-1">
                                    {request.models.map(model => (
                                        <div key={model.model_id}>
                                            <Link to={`/models/${model.model_id}`} className="text-blue-600 hover:text-blue-800">
                                                {model.model_name}
                                            </Link>
                                            <span className="ml-2 text-sm text-gray-500">({model.status})</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Validation Type</h4>
                                <span className="px-2 py-1 text-sm rounded bg-indigo-100 text-indigo-800">
                                    {request.validation_type.label}
                                </span>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Priority</h4>
                                <span className={`px-2 py-1 text-sm rounded ${getPriorityColor(request.priority.label)}`}>
                                    {request.priority.label}
                                </span>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Request Date</h4>
                                <p className="text-lg">{request.request_date}</p>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Target Completion</h4>
                                <p className="text-lg">{request.target_completion_date}</p>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Requestor</h4>
                                <p className="text-lg">{request.requestor.full_name}</p>
                                <p className="text-sm text-gray-500">{request.requestor.email}</p>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Current Status</h4>
                                <span className={`px-2 py-1 text-sm rounded ${getStatusColor(request.current_status.label)}`}>
                                    {request.current_status.label}
                                </span>
                            </div>
                            {request.trigger_reason && (
                                <div className="col-span-2">
                                    <h4 className="text-sm font-medium text-gray-500 mb-1">Trigger Reason</h4>
                                    <p className="text-gray-700 bg-gray-50 p-3 rounded">{request.trigger_reason}</p>
                                </div>
                            )}
                            {relatedVersions.length > 0 && (
                                <div className="col-span-2">
                                    <h4 className="text-sm font-medium text-gray-500 mb-2">Related Model Change(s)</h4>
                                    <div className="space-y-2">
                                        {relatedVersions.map(version => (
                                            <div key={version.version_id} className="bg-blue-50 border border-blue-200 rounded p-3">
                                                <div className="flex justify-between items-start mb-2">
                                                    <div>
                                                        <span className="font-medium text-gray-900">Version {version.version_number}</span>
                                                        <span className={`ml-2 px-2 py-0.5 rounded text-xs font-semibold ${
                                                            version.change_type === 'MAJOR'
                                                                ? 'bg-orange-200 text-orange-800'
                                                                : 'bg-blue-200 text-blue-800'
                                                        }`}>
                                                            {version.change_type}
                                                        </span>
                                                        <span className={`ml-2 px-2 py-0.5 rounded text-xs font-semibold ${
                                                            version.status === 'ACTIVE' ? 'bg-green-600 text-white' :
                                                            version.status === 'APPROVED' ? 'bg-green-200 text-green-800' :
                                                            version.status === 'IN_VALIDATION' ? 'bg-blue-200 text-blue-800' :
                                                            'bg-gray-200 text-gray-800'
                                                        }`}>
                                                            {version.status}
                                                        </span>
                                                    </div>
                                                    {version.production_date && (
                                                        <div className="text-sm text-gray-600">
                                                            Production: {new Date(version.production_date).toLocaleDateString()}
                                                        </div>
                                                    )}
                                                </div>
                                                <p className="text-sm text-gray-700 mb-1">{version.change_description}</p>
                                                <div className="text-xs text-gray-500">
                                                    Created by {version.created_by_name} on {new Date(version.created_at).toLocaleDateString()}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Created</h4>
                                <p className="text-sm">{new Date(request.created_at).toLocaleString()}</p>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Last Updated</h4>
                                <p className="text-sm">{new Date(request.updated_at).toLocaleString()}</p>
                            </div>
                        </div>

                        {/* Timeline visualization */}
                        <div className="mt-8">
                            <h4 className="text-sm font-medium text-gray-500 mb-4">Workflow Progress</h4>
                            <div className="flex items-center justify-between">
                                {['Intake', 'Planning', 'In Progress', 'Review', 'Pending Approval', 'Approved'].map((status, index) => {
                                    const isCompleted = request.status_history.some(h => h.new_status.label === status);
                                    const isCurrent = request.current_status.label === status;
                                    return (
                                        <div key={status} className="flex items-center">
                                            <div className={`flex flex-col items-center ${index > 0 ? 'ml-4' : ''}`}>
                                                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                                                    isCurrent
                                                        ? 'bg-blue-600 text-white'
                                                        : isCompleted
                                                            ? 'bg-green-600 text-white'
                                                            : 'bg-gray-200 text-gray-500'
                                                }`}>
                                                    {isCompleted && !isCurrent ? '✓' : index + 1}
                                                </div>
                                                <span className={`mt-1 text-xs ${isCurrent ? 'font-bold text-blue-600' : 'text-gray-500'}`}>
                                                    {status}
                                                </span>
                                            </div>
                                            {index < 5 && (
                                                <div className={`w-12 h-1 ml-4 ${
                                                    isCompleted && !isCurrent ? 'bg-green-600' : 'bg-gray-200'
                                                }`} />
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'assignments' && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold">Validator Assignments</h3>
                            {canEditRequest && (
                                <button onClick={() => setShowAssignmentModal(true)} className="btn-primary text-sm">
                                    + Add Validator
                                </button>
                            )}
                        </div>
                        {request.assignments.length === 0 ? (
                            <div className="text-gray-500 text-center py-8">
                                No validators assigned yet. Click "Add Validator" to assign validators.
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {request.assignments.map((assignment) => (
                                    <div key={assignment.assignment_id} className="border rounded-lg p-4 bg-gray-50">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <p className="font-medium">{assignment.validator.full_name}</p>
                                                <p className="text-sm text-gray-500">{assignment.validator.email}</p>
                                                <p className="text-xs text-gray-400">Role: {assignment.validator.role}</p>
                                            </div>
                                            <div className="flex gap-2 items-start">
                                                <div className="flex gap-2">
                                                    {assignment.is_primary && (
                                                        <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                            Primary
                                                        </span>
                                                    )}
                                                    {assignment.is_reviewer && (
                                                        <span className="px-2 py-1 text-xs rounded bg-purple-100 text-purple-800">
                                                            Reviewer
                                                        </span>
                                                    )}
                                                </div>
                                                {canEditRequest && (
                                                    <div className="flex gap-1 ml-2">
                                                        <button
                                                            onClick={() => {
                                                                setEditAssignment({
                                                                    assignment_id: assignment.assignment_id,
                                                                    is_primary: assignment.is_primary,
                                                                    is_reviewer: assignment.is_reviewer,
                                                                    estimated_hours: String(assignment.estimated_hours || ''),
                                                                    actual_hours: String(assignment.actual_hours || '')
                                                                });
                                                                setShowEditAssignmentModal(true);
                                                            }}
                                                            className="text-blue-600 hover:text-blue-800 text-xs px-2 py-1"
                                                        >
                                                            Edit
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteAssignment(assignment.assignment_id)}
                                                            className="text-red-600 hover:text-red-800 text-xs px-2 py-1"
                                                        >
                                                            Remove
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-3 gap-4 mt-3 text-sm">
                                            <div>
                                                <span className="text-gray-500">Assigned:</span>{' '}
                                                {assignment.assignment_date}
                                            </div>
                                            <div>
                                                <span className="text-gray-500">Estimated Hours:</span>{' '}
                                                {assignment.estimated_hours || 'N/A'}
                                            </div>
                                            <div>
                                                <span className="text-gray-500">Actual Hours:</span>{' '}
                                                {assignment.actual_hours || 'N/A'}
                                            </div>
                                        </div>
                                        <div className="mt-2 flex items-center gap-2">
                                            <span className={`px-2 py-1 text-xs rounded ${
                                                assignment.independence_attestation
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-red-100 text-red-800'
                                            }`}>
                                                Independence: {assignment.independence_attestation ? 'Attested' : 'Not Attested'}
                                            </span>
                                        </div>
                                        {/* Reviewer Sign-off Section */}
                                        {assignment.is_reviewer && (
                                            <div className="mt-3 pt-3 border-t border-gray-200">
                                                <div className="flex items-center justify-between">
                                                    <div>
                                                        <span className="text-sm font-medium text-gray-700">Reviewer Sign-off: </span>
                                                        {assignment.reviewer_signed_off ? (
                                                            <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">
                                                                Signed Off
                                                            </span>
                                                        ) : (
                                                            <span className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-800">
                                                                Pending
                                                            </span>
                                                        )}
                                                    </div>
                                                    {!assignment.reviewer_signed_off &&
                                                        user?.user_id === assignment.validator.user_id &&
                                                        request.outcome && (
                                                        <button
                                                            onClick={() => {
                                                                setSignOffData({ assignment_id: assignment.assignment_id, comments: '' });
                                                                setShowSignOffModal(true);
                                                            }}
                                                            className="bg-purple-600 text-white px-3 py-1 rounded text-xs hover:bg-purple-700"
                                                        >
                                                            Sign Off
                                                        </button>
                                                    )}
                                                </div>
                                                {assignment.reviewer_signed_off && assignment.reviewer_signed_off_at && (
                                                    <div className="mt-2 text-xs text-gray-500">
                                                        Signed off on: {new Date(assignment.reviewer_signed_off_at).toLocaleString()}
                                                    </div>
                                                )}
                                                {assignment.reviewer_sign_off_comments && (
                                                    <div className="mt-2 text-sm">
                                                        <span className="text-gray-500">Comments:</span>{' '}
                                                        <span className="text-gray-700">{assignment.reviewer_sign_off_comments}</span>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'outcome' && (
                    <div>
                        <h3 className="text-lg font-bold mb-4">Validation Outcome</h3>

                        {request.outcome && !showOutcomeModal ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-6">
                                    <div>
                                        <h4 className="text-sm font-medium text-gray-500 mb-1">Overall Rating</h4>
                                        <span className={`px-3 py-1 text-sm rounded ${
                                            request.outcome.overall_rating.label.includes('Fit')
                                                ? request.outcome.overall_rating.label === 'Fit for Use'
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-orange-100 text-orange-800'
                                                : 'bg-red-100 text-red-800'
                                        }`}>
                                            {request.outcome.overall_rating.label}
                                        </span>
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-medium text-gray-500 mb-1">Recommended Review</h4>
                                        <p className="text-lg">{request.outcome.recommended_review_frequency} months</p>
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-medium text-gray-500 mb-1">Effective Date</h4>
                                        <p className="text-lg">{request.outcome.effective_date}</p>
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-medium text-gray-500 mb-1">Expiration Date</h4>
                                        <p className="text-lg">{request.outcome.expiration_date || 'N/A'}</p>
                                    </div>
                                </div>
                                <div>
                                    <h4 className="text-sm font-medium text-gray-500 mb-1">Executive Summary</h4>
                                    <p className="text-gray-700 bg-gray-50 p-4 rounded whitespace-pre-wrap">
                                        {request.outcome.executive_summary}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <div className="text-xs text-gray-400">
                                        Created: {new Date(request.outcome.created_at).toLocaleString()} |
                                        Updated: {new Date(request.outcome.updated_at).toLocaleString()}
                                    </div>
                                    {canEditRequest && !['REVIEW', 'PENDING_APPROVAL', 'APPROVED'].includes(request.current_status.code) && (
                                        <button
                                            onClick={() => {
                                                setNewOutcome({
                                                    overall_rating_id: request.outcome!.overall_rating.value_id,
                                                    executive_summary: request.outcome!.executive_summary,
                                                    recommended_review_frequency: request.outcome!.recommended_review_frequency,
                                                    effective_date: request.outcome!.effective_date,
                                                    expiration_date: request.outcome!.expiration_date || ''
                                                });
                                                setShowOutcomeModal(true);
                                            }}
                                            className="btn-secondary text-sm"
                                        >
                                            Edit Outcome
                                        </button>
                                    )}
                                </div>
                            </div>
                        ) : (
                            <div className="bg-white border border-gray-200 rounded-lg p-6">
                                <p className="text-sm text-gray-600 mb-4">
                                    {request.outcome
                                        ? 'Edit the validation outcome details below.'
                                        : 'Complete the validation outcome form below. This information is required before you can complete your work.'}
                                </p>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Overall Rating *</label>
                                        <select
                                            className="input-field"
                                            value={newOutcome.overall_rating_id}
                                            onChange={(e) => setNewOutcome({ ...newOutcome, overall_rating_id: parseInt(e.target.value) })}
                                        >
                                            <option value={0}>Select Rating</option>
                                            {ratingOptions.map((opt) => (
                                                <option key={opt.value_id} value={opt.value_id}>
                                                    {opt.label}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Recommended Review (months) *</label>
                                        <input
                                            type="number"
                                            className="input-field"
                                            value={newOutcome.recommended_review_frequency}
                                            onChange={(e) => setNewOutcome({ ...newOutcome, recommended_review_frequency: parseInt(e.target.value) })}
                                            min="1"
                                            max="60"
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Effective Date *</label>
                                        <input
                                            type="date"
                                            className="input-field"
                                            value={newOutcome.effective_date}
                                            onChange={(e) => setNewOutcome({ ...newOutcome, effective_date: e.target.value })}
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">Expiration Date (Optional)</label>
                                        <input
                                            type="date"
                                            className="input-field"
                                            value={newOutcome.expiration_date}
                                            onChange={(e) => setNewOutcome({ ...newOutcome, expiration_date: e.target.value })}
                                        />
                                    </div>
                                </div>
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Executive Summary *</label>
                                    <textarea
                                        className="input-field"
                                        rows={6}
                                        value={newOutcome.executive_summary}
                                        onChange={(e) => setNewOutcome({ ...newOutcome, executive_summary: e.target.value })}
                                        placeholder="Provide a comprehensive summary of the validation findings and conclusions..."
                                    />
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={request.outcome ? handleUpdateOutcome : handleCreateOutcome}
                                        disabled={actionLoading || !newOutcome.overall_rating_id || !newOutcome.executive_summary}
                                        className="btn-primary"
                                    >
                                        {actionLoading ? 'Saving...' : request.outcome ? 'Update Outcome' : 'Save Outcome'}
                                    </button>
                                    {request.outcome && (
                                        <button
                                            onClick={() => setShowOutcomeModal(false)}
                                            className="btn-secondary"
                                            disabled={actionLoading}
                                        >
                                            Cancel
                                        </button>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'review' && (
                    <div>
                        <h3 className="text-lg font-bold mb-4">Review Validation Outcome</h3>

                        {/* Show the validation outcome being reviewed */}
                        {request.outcome ? (
                            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-6">
                                <h4 className="font-semibold mb-4 text-gray-700">Validation Outcome to Review</h4>
                                <div className="grid grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <p className="text-sm text-gray-600">Overall Rating</p>
                                        <p className="font-medium">{request.outcome.overall_rating?.label || 'N/A'}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-600">Recommended Review Frequency</p>
                                        <p className="font-medium">{request.outcome.recommended_review_frequency} months</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-600">Effective Date</p>
                                        <p className="font-medium">{new Date(request.outcome.effective_date).toLocaleDateString()}</p>
                                    </div>
                                    {request.outcome.expiration_date && (
                                        <div>
                                            <p className="text-sm text-gray-600">Expiration Date</p>
                                            <p className="font-medium">{new Date(request.outcome.expiration_date).toLocaleDateString()}</p>
                                        </div>
                                    )}
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600 mb-2">Executive Summary</p>
                                    <p className="text-sm whitespace-pre-wrap bg-white p-3 rounded border">{request.outcome.executive_summary}</p>
                                </div>
                            </div>
                        ) : (
                            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                                <p className="text-yellow-800 text-sm">
                                    No validation outcome has been created yet. The validator must complete the outcome before review can begin.
                                </p>
                            </div>
                        )}

                        {/* Show existing review outcome or form to create one */}
                        {request.review_outcome ? (
                            <div className="bg-white border border-gray-200 rounded-lg p-6">
                                <h4 className="font-semibold mb-4">Review Decision</h4>
                                <div className="space-y-3">
                                    <div>
                                        <p className="text-sm text-gray-600">Reviewer</p>
                                        <p className="font-medium">{request.review_outcome.reviewer.full_name}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-600">Decision</p>
                                        <span className={`inline-block px-3 py-1 rounded text-sm font-medium ${
                                            request.review_outcome.decision === 'AGREE'
                                                ? 'bg-green-100 text-green-800'
                                                : 'bg-yellow-100 text-yellow-800'
                                        }`}>
                                            {request.review_outcome.decision === 'AGREE' ? 'Agree' : 'Send Back'}
                                        </span>
                                    </div>
                                    {request.review_outcome.agrees_with_rating !== null && (
                                        <div>
                                            <p className="text-sm text-gray-600">Agrees with Rating?</p>
                                            <p className="font-medium">{request.review_outcome.agrees_with_rating ? 'Yes' : 'No'}</p>
                                        </div>
                                    )}
                                    {request.review_outcome.comments && (
                                        <div>
                                            <p className="text-sm text-gray-600">Comments</p>
                                            <p className="text-sm whitespace-pre-wrap bg-gray-50 p-3 rounded border">{request.review_outcome.comments}</p>
                                        </div>
                                    )}
                                    <div>
                                        <p className="text-sm text-gray-600">Review Date</p>
                                        <p className="font-medium">{new Date(request.review_outcome.review_date).toLocaleString()}</p>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <>
                                {isReviewer && request.outcome ? (
                                    <div className="bg-white border border-gray-200 rounded-lg p-6">
                                        <h4 className="font-semibold mb-4">Submit Review Decision</h4>
                                        <p className="text-sm text-gray-600 mb-4">
                                            Review the validation outcome above and provide your decision.
                                        </p>

                                        <div className="mb-4">
                                            <label className="block text-sm font-medium mb-2">Decision *</label>
                                            <select
                                                className="input-field"
                                                value={newReviewOutcome.decision}
                                                onChange={(e) => setNewReviewOutcome({ ...newReviewOutcome, decision: e.target.value })}
                                            >
                                                <option value="">Select Decision</option>
                                                <option value="AGREE">Agree - Approve for final approval</option>
                                                <option value="SEND_BACK">Send Back - Request revisions</option>
                                            </select>
                                        </div>

                                        <div className="mb-4">
                                            <label className="flex items-center gap-2 text-sm">
                                                <input
                                                    type="checkbox"
                                                    checked={newReviewOutcome.agrees_with_rating === true}
                                                    onChange={(e) => setNewReviewOutcome({
                                                        ...newReviewOutcome,
                                                        agrees_with_rating: e.target.checked ? true : null
                                                    })}
                                                    className="rounded"
                                                />
                                                <span>I agree with the overall rating assessment</span>
                                            </label>
                                        </div>

                                        <div className="mb-4">
                                            <label className="block text-sm font-medium mb-2">
                                                Comments {newReviewOutcome.decision === 'SEND_BACK' && '*'}
                                            </label>
                                            <textarea
                                                className="input-field"
                                                rows={4}
                                                value={newReviewOutcome.comments}
                                                onChange={(e) => setNewReviewOutcome({ ...newReviewOutcome, comments: e.target.value })}
                                                placeholder={newReviewOutcome.decision === 'SEND_BACK'
                                                    ? "Please explain what changes are needed..."
                                                    : "Optional comments about the review..."}
                                            />
                                            {newReviewOutcome.decision === 'SEND_BACK' && (
                                                <p className="text-xs text-gray-500 mt-1">
                                                    Comments are required when sending back for revisions
                                                </p>
                                            )}
                                        </div>

                                        <button
                                            onClick={handleCreateReviewOutcome}
                                            disabled={
                                                actionLoading ||
                                                !newReviewOutcome.decision ||
                                                (newReviewOutcome.decision === 'SEND_BACK' && !newReviewOutcome.comments?.trim())
                                            }
                                            className="btn-primary"
                                        >
                                            {actionLoading ? 'Submitting...' : 'Submit Review Decision'}
                                        </button>
                                    </div>
                                ) : (
                                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
                                        <p className="text-gray-600 text-sm">
                                            {!isReviewer
                                                ? 'You are not assigned as a reviewer for this validation request.'
                                                : 'Waiting for validation outcome to be completed before review can begin.'}
                                        </p>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}

                {activeTab === 'approvals' && (
                    <div>
                        <h3 className="text-lg font-bold mb-4">Approval Status</h3>
                        {request.approvals.length === 0 ? (
                            <div className="text-gray-500 text-center py-8">
                                No approvals configured for this request.
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {request.approvals.map((approval) => (
                                    <div key={approval.approval_id} className="border rounded-lg p-4">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <p className="font-medium">{approval.approver.full_name}</p>
                                                <p className="text-sm text-gray-500">{approval.approver.email}</p>
                                                <p className="text-xs text-gray-400">
                                                    Role: {approval.approver_role}
                                                    {approval.is_required && ' (Required)'}
                                                </p>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className={`px-2 py-1 text-xs rounded ${getApprovalStatusColor(approval.approval_status)}`}>
                                                    {approval.approval_status}
                                                </span>
                                                {approval.approval_status === 'Pending' &&
                                                    user?.user_id === approval.approver.user_id && (
                                                    <button
                                                        onClick={() => {
                                                            setApprovalUpdate({ approval_id: approval.approval_id, status: '', comments: '' });
                                                            setShowApprovalModal(true);
                                                        }}
                                                        className="btn-primary text-xs"
                                                    >
                                                        Submit
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                        {approval.approved_at && (
                                            <div className="mt-2 text-sm text-gray-500">
                                                {approval.approval_status === 'Approved' ? 'Approved' : 'Rejected'} on:{' '}
                                                {new Date(approval.approved_at).toLocaleString()}
                                            </div>
                                        )}
                                        {approval.comments && (
                                            <div className="mt-2 text-sm">
                                                <span className="text-gray-500">Comments:</span>{' '}
                                                <span className="text-gray-700">{approval.comments}</span>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'history' && (
                    <div>
                        <h3 className="text-lg font-bold mb-4">Activity History</h3>
                        {request.status_history.length === 0 && allAuditLogs.length === 0 ? (
                            <div className="text-gray-500 text-center py-8">
                                No activity recorded.
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {/* Merge and sort status history and all audit logs */}
                                {[
                                    ...request.status_history.map((h) => ({
                                        type: 'status' as const,
                                        timestamp: h.changed_at,
                                        data: h
                                    })),
                                    ...allAuditLogs.map((a) => ({
                                        type: 'audit' as const,
                                        timestamp: a.timestamp,
                                        data: a
                                    }))
                                ]
                                    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                                    .map((item) => {
                                        if (item.type === 'status') {
                                            const history = item.data as ValidationStatusHistory;
                                            return (
                                                <div key={`status-${history.history_id}`} className="border-l-4 border-blue-500 pl-4 py-2">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-xs font-semibold text-blue-700">STATUS CHANGE</span>
                                                        {history.old_status && (
                                                            <>
                                                                <span className={`px-2 py-1 text-xs rounded ${getStatusColor(history.old_status.label)}`}>
                                                                    {history.old_status.label}
                                                                </span>
                                                                <span className="text-gray-400">→</span>
                                                            </>
                                                        )}
                                                        <span className={`px-2 py-1 text-xs rounded ${getStatusColor(history.new_status.label)}`}>
                                                            {history.new_status.label}
                                                        </span>
                                                    </div>
                                                    <div className="mt-2 text-sm">
                                                        <span className="text-gray-500">Changed by:</span>{' '}
                                                        {history.changed_by.full_name}
                                                    </div>
                                                    <div className="text-xs text-gray-400">
                                                        {new Date(history.changed_at).toLocaleString()}
                                                    </div>
                                                    {history.change_reason && (
                                                        <div className="mt-1 text-sm">
                                                            <span className="text-gray-500">Reason:</span>{' '}
                                                            <span className="text-gray-700">{history.change_reason}</span>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        } else {
                                            const audit = item.data as AuditLog;

                                            // Determine styling and label based on entity type and action
                                            let borderColor = 'border-gray-500';
                                            let label = audit.action;

                                            if (audit.entity_type === 'ValidationAssignment') {
                                                const colors = {
                                                    'CREATE': 'border-green-500',
                                                    'UPDATE': 'border-orange-500',
                                                    'DELETE': 'border-red-500',
                                                    'REVIEWER_SIGN_OFF': 'border-purple-500'
                                                };
                                                const labels = {
                                                    'CREATE': 'VALIDATOR ASSIGNED',
                                                    'UPDATE': 'ASSIGNMENT UPDATED',
                                                    'DELETE': 'VALIDATOR REMOVED',
                                                    'REVIEWER_SIGN_OFF': 'REVIEWER SIGN-OFF'
                                                };
                                                borderColor = colors[audit.action as keyof typeof colors] || borderColor;
                                                label = labels[audit.action as keyof typeof labels] || audit.action;
                                            } else if (audit.entity_type === 'ValidationOutcome') {
                                                const colors = {
                                                    'CREATE': 'border-green-500',
                                                    'UPDATE': 'border-orange-500'
                                                };
                                                const labels = {
                                                    'CREATE': 'OUTCOME CREATED',
                                                    'UPDATE': 'OUTCOME UPDATED'
                                                };
                                                borderColor = colors[audit.action as keyof typeof colors] || borderColor;
                                                label = labels[audit.action as keyof typeof labels] || audit.action;
                                            } else if (audit.entity_type === 'ValidationReviewOutcome') {
                                                const colors = {
                                                    'CREATE': 'border-purple-500',
                                                    'UPDATE': 'border-orange-500'
                                                };
                                                const labels = {
                                                    'CREATE': 'REVIEW SUBMITTED',
                                                    'UPDATE': 'REVIEW UPDATED'
                                                };
                                                borderColor = colors[audit.action as keyof typeof colors] || borderColor;
                                                label = labels[audit.action as keyof typeof labels] || audit.action;
                                            }

                                            return (
                                                <div key={`audit-${audit.log_id}`} className={`border-l-4 ${borderColor} pl-4 py-2`}>
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-xs font-semibold text-gray-700">
                                                            {label}
                                                        </span>
                                                    </div>
                                                    <div className="mt-2 text-sm">
                                                        {/* Assignment-specific fields */}
                                                        {audit.entity_type === 'ValidationAssignment' && (
                                                            <>
                                                                {audit.changes?.validator && (
                                                                    <div>
                                                                        <span className="text-gray-500">Validator:</span>{' '}
                                                                        <span className="font-medium">{audit.changes.validator}</span>
                                                                    </div>
                                                                )}
                                                                {audit.changes?.role && (
                                                                    <div>
                                                                        <span className="text-gray-500">Role:</span>{' '}
                                                                        <span className="text-gray-700">{audit.changes.role}</span>
                                                                    </div>
                                                                )}
                                                                {audit.changes?.estimated_hours !== undefined && (
                                                                    <div>
                                                                        <span className="text-gray-500">Estimated Hours:</span>{' '}
                                                                        <span className="text-gray-700">{audit.changes.estimated_hours || 'N/A'}</span>
                                                                    </div>
                                                                )}
                                                                {audit.changes?.is_primary !== undefined && (
                                                                    <div>
                                                                        <span className="text-gray-500">Primary Validator:</span>{' '}
                                                                        <span className="text-gray-700">
                                                                            {audit.changes.is_primary.old} → {audit.changes.is_primary.new}
                                                                        </span>
                                                                    </div>
                                                                )}
                                                                {audit.changes?.is_reviewer !== undefined && (
                                                                    <div>
                                                                        <span className="text-gray-500">Reviewer Role:</span>{' '}
                                                                        <span className="text-gray-700">
                                                                            {audit.changes.is_reviewer.old} → {audit.changes.is_reviewer.new}
                                                                        </span>
                                                                    </div>
                                                                )}
                                                                {audit.changes?.actual_hours !== undefined && (
                                                                    <div>
                                                                        <span className="text-gray-500">Actual Hours:</span>{' '}
                                                                        <span className="text-gray-700">
                                                                            {audit.changes.actual_hours.old || 'N/A'} → {audit.changes.actual_hours.new || 'N/A'}
                                                                        </span>
                                                                    </div>
                                                                )}
                                                            </>
                                                        )}

                                                        {/* Outcome-specific fields */}
                                                        {audit.entity_type === 'ValidationOutcome' && (
                                                            <>
                                                                {audit.changes?.overall_rating && (
                                                                    <div>
                                                                        <span className="text-gray-500">Overall Rating:</span>{' '}
                                                                        <span className="font-medium">{audit.changes.overall_rating}</span>
                                                                    </div>
                                                                )}
                                                                {audit.changes?.recommended_review_frequency !== undefined && (
                                                                    <div>
                                                                        <span className="text-gray-500">Recommended Review Frequency:</span>{' '}
                                                                        <span className="text-gray-700">{audit.changes.recommended_review_frequency} months</span>
                                                                    </div>
                                                                )}
                                                            </>
                                                        )}

                                                        {/* Review Outcome-specific fields */}
                                                        {audit.entity_type === 'ValidationReviewOutcome' && (
                                                            <>
                                                                {audit.changes?.decision && (
                                                                    <div>
                                                                        <span className="text-gray-500">Decision:</span>{' '}
                                                                        <span className={`font-medium ${audit.changes.decision === 'AGREE' ? 'text-green-700' : 'text-yellow-700'}`}>
                                                                            {audit.changes.decision === 'AGREE' ? 'Agree' : 'Send Back'}
                                                                        </span>
                                                                    </div>
                                                                )}
                                                                {audit.changes?.agrees_with_rating !== undefined && audit.changes.agrees_with_rating !== null && (
                                                                    <div>
                                                                        <span className="text-gray-500">Agrees with Rating:</span>{' '}
                                                                        <span className="text-gray-700">{audit.changes.agrees_with_rating ? 'Yes' : 'No'}</span>
                                                                    </div>
                                                                )}
                                                            </>
                                                        )}

                                                        {/* Common fields */}
                                                        {audit.changes?.comments && (
                                                            <div>
                                                                <span className="text-gray-500">Comments:</span>{' '}
                                                                <span className="text-gray-700">{audit.changes.comments}</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                    <div className="mt-2 text-sm">
                                                        <span className="text-gray-500">By:</span>{' '}
                                                        {audit.user.full_name}
                                                    </div>
                                                    <div className="text-xs text-gray-400">
                                                        {new Date(audit.timestamp).toLocaleString()}
                                                    </div>
                                                </div>
                                            );
                                        }
                                    })}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Status Update Modal */}
            {showStatusModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-lg font-bold mb-4">Update Request Status</h3>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">New Status</label>
                            <select
                                className="input-field"
                                value={newStatus.status_id}
                                onChange={(e) => setNewStatus({ ...newStatus, status_id: parseInt(e.target.value) })}
                            >
                                <option value={0}>Select Status</option>
                                {statusOptions.map((opt) => (
                                    <option key={opt.value_id} value={opt.value_id}>
                                        {opt.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Reason (Optional)</label>
                            <textarea
                                className="input-field"
                                rows={3}
                                value={newStatus.reason}
                                onChange={(e) => setNewStatus({ ...newStatus, reason: e.target.value })}
                                placeholder="Explain why this status change is being made..."
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleStatusUpdate}
                                disabled={actionLoading || !newStatus.status_id}
                                className="btn-primary"
                            >
                                {actionLoading ? 'Updating...' : 'Update Status'}
                            </button>
                            <button onClick={() => setShowStatusModal(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Add Assignment Modal */}
            {showAssignmentModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-lg font-bold mb-4">Add Validator Assignment</h3>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Validator</label>
                            <select
                                className="input-field"
                                value={newAssignment.validator_id}
                                onChange={(e) => setNewAssignment({ ...newAssignment, validator_id: parseInt(e.target.value) })}
                            >
                                <option value={0}>Select Validator</option>
                                {users.filter(u => u.role === 'Validator' || u.role === 'Admin').map((u) => (
                                    <option key={u.user_id} value={u.user_id}>
                                        {u.full_name} ({u.role})
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="mb-4">
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={newAssignment.is_primary}
                                    onChange={(e) => setNewAssignment({ ...newAssignment, is_primary: e.target.checked })}
                                />
                                <span className="text-sm">Primary Validator</span>
                            </label>
                        </div>
                        <div className="mb-4">
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={newAssignment.is_reviewer}
                                    onChange={(e) => setNewAssignment({ ...newAssignment, is_reviewer: e.target.checked })}
                                />
                                <span className="text-sm">Reviewer (QA Sign-off required)</span>
                            </label>
                            <p className="text-xs text-gray-500 mt-1 ml-6">
                                If checked, this validator must sign off before moving to Pending Approval
                            </p>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Estimated Hours</label>
                            <input
                                type="number"
                                className="input-field"
                                value={newAssignment.estimated_hours}
                                onChange={(e) => setNewAssignment({ ...newAssignment, estimated_hours: e.target.value })}
                                placeholder="e.g., 40"
                                step="0.5"
                            />
                        </div>
                        <div className="mb-4">
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={newAssignment.independence_attestation}
                                    onChange={(e) => setNewAssignment({ ...newAssignment, independence_attestation: e.target.checked })}
                                />
                                <span className="text-sm font-medium">
                                    I attest that this validator is independent from model development
                                </span>
                            </label>
                            <p className="text-xs text-gray-500 mt-1">
                                Required: Validator cannot be model owner or developer
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleAddAssignment}
                                disabled={actionLoading || !newAssignment.validator_id || !newAssignment.independence_attestation}
                                className="btn-primary"
                            >
                                {actionLoading ? 'Adding...' : 'Add Assignment'}
                            </button>
                            <button onClick={() => setShowAssignmentModal(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Assignment Modal */}
            {showEditAssignmentModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-lg font-bold mb-4">Edit Validator Assignment</h3>
                        <div className="mb-4">
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={editAssignment.is_primary}
                                    onChange={(e) => setEditAssignment({ ...editAssignment, is_primary: e.target.checked })}
                                />
                                <span className="text-sm">Primary Validator</span>
                            </label>
                        </div>
                        <div className="mb-4">
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={editAssignment.is_reviewer}
                                    onChange={(e) => setEditAssignment({ ...editAssignment, is_reviewer: e.target.checked })}
                                />
                                <span className="text-sm">Reviewer (QA Sign-off required)</span>
                            </label>
                            <p className="text-xs text-gray-500 mt-1 ml-6">
                                If checked, this validator must sign off before moving to Pending Approval
                            </p>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Estimated Hours</label>
                            <input
                                type="number"
                                className="input-field"
                                value={editAssignment.estimated_hours}
                                onChange={(e) => setEditAssignment({ ...editAssignment, estimated_hours: e.target.value })}
                                placeholder="e.g., 40"
                                step="0.5"
                            />
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Actual Hours</label>
                            <input
                                type="number"
                                className="input-field"
                                value={editAssignment.actual_hours}
                                onChange={(e) => setEditAssignment({ ...editAssignment, actual_hours: e.target.value })}
                                placeholder="e.g., 35"
                                step="0.5"
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleEditAssignment}
                                disabled={actionLoading}
                                className="btn-primary"
                            >
                                {actionLoading ? 'Updating...' : 'Update Assignment'}
                            </button>
                            <button onClick={() => setShowEditAssignmentModal(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Approval Modal */}
            {showApprovalModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-lg font-bold mb-4">Submit Approval</h3>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Decision</label>
                            <select
                                className="input-field"
                                value={approvalUpdate.status}
                                onChange={(e) => setApprovalUpdate({ ...approvalUpdate, status: e.target.value })}
                            >
                                <option value="">Select Decision</option>
                                <option value="Approved">Approve</option>
                                <option value="Rejected">Reject</option>
                            </select>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Comments</label>
                            <textarea
                                className="input-field"
                                rows={4}
                                value={approvalUpdate.comments}
                                onChange={(e) => setApprovalUpdate({ ...approvalUpdate, comments: e.target.value })}
                                placeholder="Provide any comments or feedback..."
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleApprovalUpdate}
                                disabled={actionLoading || !approvalUpdate.status}
                                className="btn-primary"
                            >
                                {actionLoading ? 'Submitting...' : 'Submit'}
                            </button>
                            <button onClick={() => setShowApprovalModal(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Reviewer Sign-Off Modal */}
            {showSignOffModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-lg font-bold mb-4">Reviewer Sign-Off</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            By signing off, you confirm that you have reviewed the validation outcome and attest to its quality and completeness.
                        </p>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Comments (Optional)</label>
                            <textarea
                                className="input-field"
                                rows={4}
                                value={signOffData.comments}
                                onChange={(e) => setSignOffData({ ...signOffData, comments: e.target.value })}
                                placeholder="Add any comments or notes about your review..."
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleReviewerSignOff}
                                disabled={actionLoading}
                                className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
                            >
                                {actionLoading ? 'Signing Off...' : 'Confirm Sign-Off'}
                            </button>
                            <button onClick={() => setShowSignOffModal(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Select New Primary Modal */}
            {showSelectPrimaryModal && request && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-lg font-bold mb-4">Select New Primary Validator</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            You are removing the primary validator. Please select which of the remaining validators should become the new primary.
                        </p>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">New Primary Validator</label>
                            <select
                                className="input-field"
                                value={deleteAssignmentData.new_primary_id}
                                onChange={(e) => setDeleteAssignmentData({ ...deleteAssignmentData, new_primary_id: parseInt(e.target.value) })}
                            >
                                <option value={0}>-- Select Validator --</option>
                                {request.assignments
                                    .filter(a => a.assignment_id !== deleteAssignmentData.assignment_id)
                                    .map(a => (
                                        <option key={a.validator.user_id} value={a.validator.user_id}>
                                            {a.validator.full_name} ({a.validator.role})
                                        </option>
                                    ))
                                }
                            </select>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={confirmDeleteWithNewPrimary}
                                disabled={actionLoading || !deleteAssignmentData.new_primary_id}
                                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50"
                            >
                                {actionLoading ? 'Removing...' : 'Confirm & Remove'}
                            </button>
                            <button
                                onClick={() => {
                                    setShowSelectPrimaryModal(false);
                                    setDeleteAssignmentData({ assignment_id: 0, new_primary_id: 0 });
                                }}
                                className="btn-secondary"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

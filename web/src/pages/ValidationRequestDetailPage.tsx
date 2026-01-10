import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';
import ValidationPlanForm, { ValidationPlanFormHandle } from '../components/ValidationPlanForm';
import ConditionalApprovalsSection from '../components/ConditionalApprovalsSection';
import OverdueCommentaryModal, { OverdueType } from '../components/OverdueCommentaryModal';
import { overdueCommentaryApi, CurrentOverdueCommentaryResponse } from '../api/overdueCommentary';
import { recommendationsApi, RecommendationListItem, TaxonomyValue as RecTaxonomyValue } from '../api/recommendations';
import { listValidationRequestLimitations, LimitationListItem } from '../api/limitations';
import RecommendationCreateModal from '../components/RecommendationCreateModal';
import ValidationScorecardTab from '../components/ValidationScorecardTab';
import DeployModal from '../components/DeployModal';
import ManageModelsModal from '../components/ManageModelsModal';
import { Region } from '../api/regions';
import PreTransitionWarningModal from '../components/PreTransitionWarningModal';
import { validationWorkflowApi, PreTransitionWarningsResponse, ValidationRequestModelUpdateResponse } from '../api/validationWorkflow';
import { canManageRecommendations, canManageValidations, canProxyApprove, canViewAdminDashboard, getUserRoleCode } from '../utils/roleUtils';

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
    role_code?: string | null;
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
    approval_type: string;  // Global, Regional, Conditional
    is_required: boolean;
    approval_status: string;
    comments: string | null;
    approved_at: string | null;
    created_at: string;
    // Voided status - approvals may be voided due to model risk tier changes
    voided_at: string | null;
    void_reason: string | null;
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
    validation_request_id: number | null;
    scope?: string;  // GLOBAL | REGIONAL
    affected_region_ids?: number[] | null;
}

interface ValidationRequestDetail {
    request_id: number;
    models: ModelSummary[];  // API returns array of models
    request_date: string;
    requestor: UserSummary;
    validation_type: TaxonomyValue;
    priority: TaxonomyValue;
    target_completion_date: string;
    trigger_reason: string | null;
    external_project_id: string | null;
    current_status: TaxonomyValue;
    created_at: string;
    updated_at: string;
    completion_date: string | null;
    submission_received_date: string | null;  // Date when model documentation was submitted
    prior_validation_request_id: number | null;
    prior_full_validation_request_id: number | null;  // Most recent INITIAL or COMPREHENSIVE validation
    assignments: ValidationAssignment[];
    status_history: ValidationStatusHistory[];
    approvals: ValidationApproval[];
    outcome: ValidationOutcome | null;
    // Risk-tier-based lead time (replaces fixed complete_work_days for work stages)
    applicable_lead_time_days: number;
    // Hold time tracking
    total_hold_days: number;
    previous_status_before_hold: string | null;
    adjusted_validation_team_sla_due_date: string | null;
    // Scoped regions for regional approval logic
    regions?: Region[];
}

const getPrimaryModel = (models?: ModelSummary[]): ModelSummary | undefined => {
    if (!models || models.length === 0) return undefined;
    return models.reduce((min, model) => (model.model_id < min.model_id ? model : min), models[0]);
};

interface PriorValidationSummary {
    request_id: number;
    validation_type: TaxonomyValue;
    current_status: TaxonomyValue;
    completion_date: string | null;
    updated_at: string;
    outcome: {
        overall_rating: TaxonomyValue | null;
        executive_summary: string;
    } | null;
}

interface WorkflowSLA {
    sla_id: number;
    workflow_type: string;
    assignment_days: number;
    begin_work_days: number;
    // NOTE: complete_work_days removed - now uses applicable_lead_time_days from each request
    approval_days: number;
    created_at: string;
    updated_at: string;
}

type TabType = 'overview' | 'plan' | 'assignments' | 'outcome' | 'scorecard' | 'limitations' | 'approvals' | 'history';

export default function ValidationRequestDetailPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();
    const canViewAdminDashboardFlag = canViewAdminDashboard(user);
    const canManageValidationsFlag = canManageValidations(user);
    const canManageRecommendationsFlag = canManageRecommendations(user);
    const canProxyApproveFlag = canProxyApprove(user);
    const [searchParams, setSearchParams] = useSearchParams();
    const [request, setRequest] = useState<ValidationRequestDetail | null>(null);
    const [relatedVersions, setRelatedVersions] = useState<ModelVersion[]>([]);
    const [assignmentAuditLogs, setAssignmentAuditLogs] = useState<AuditLog[]>([]);
    const [approvalAuditLogs, setApprovalAuditLogs] = useState<AuditLog[]>([]);
    const [commentaryAuditLogs, setCommentaryAuditLogs] = useState<AuditLog[]>([]);
    const [workflowSLA, setWorkflowSLA] = useState<WorkflowSLA | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [modelChangeNotices, setModelChangeNotices] = useState<string[]>([]);
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [actionLoading, setActionLoading] = useState(false);

    // Ref to validation plan form for checking unsaved changes
    const validationPlanRef = useRef<ValidationPlanFormHandle>(null);

    // Form states
    const [showAssignmentModal, setShowAssignmentModal] = useState(false);
    const [showEditAssignmentModal, setShowEditAssignmentModal] = useState(false);
    const [showOutcomeModal, setShowOutcomeModal] = useState(false);
    const [showApprovalModal, setShowApprovalModal] = useState(false);
    const [showSubmissionModal, setShowSubmissionModal] = useState(false);
    const [showManageModelsModal, setShowManageModelsModal] = useState(false);
    // Hold/Cancel/Resume modals
    const [showHoldModal, setShowHoldModal] = useState(false);
    const [showCancelModal, setShowCancelModal] = useState(false);
    const [showResumeModal, setShowResumeModal] = useState(false);
    const [holdReason, setHoldReason] = useState('');
    const [cancelReason, setCancelReason] = useState('');
    const [resumeNotes, setResumeNotes] = useState('');
    const [showSendBackModal, setShowSendBackModal] = useState(false);
    const [sendBackReason, setSendBackReason] = useState('');

    // Deploy modal state (Issue 5: Deploy Approved Version CTA)
    const [showDeployModal, setShowDeployModal] = useState(false);
    const [deployVersion, setDeployVersion] = useState<ModelVersion | null>(null);

    const [statusOptions, setStatusOptions] = useState<TaxonomyValue[]>([]);
    const [ratingOptions, setRatingOptions] = useState<TaxonomyValue[]>([]);
    const [users, setUsers] = useState<UserSummary[]>([]);

    // Recommendations state
    const [recommendations, setRecommendations] = useState<RecommendationListItem[]>([]);
    const [showRecommendationModal, setShowRecommendationModal] = useState(false);
    const [recPriorities, setRecPriorities] = useState<RecTaxonomyValue[]>([]);
    const [recCategories, setRecCategories] = useState<RecTaxonomyValue[]>([]);

    // Limitations state
    const [limitations, setLimitations] = useState<LimitationListItem[]>([]);

    // Admin status override state (kept for potential future use)
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [_showStatusModal, setShowStatusModal] = useState(false);
    const [newStatus, setNewStatus] = useState({ status_id: 0, reason: '' });

    const [newAssignment, setNewAssignment] = useState({
        validator_id: 0,
        is_primary: false,
        is_reviewer: false,
        estimated_hours: '',
        independence_attestation: false
    });
    const [submissionReceivedDate, setSubmissionReceivedDate] = useState(new Date().toISOString().split('T')[0]);
    const [submissionNotes, setSubmissionNotes] = useState('');
    // Submission metadata fields
    const [submissionConfirmedVersionId, setSubmissionConfirmedVersionId] = useState<number | null>(null);
    const [submissionDocVersion, setSubmissionDocVersion] = useState('');
    const [submissionModelVersion, setSubmissionModelVersion] = useState('');
    const [submissionDocId, setSubmissionDocId] = useState('');
    const [availableVersions, setAvailableVersions] = useState<ModelVersion[]>([]);

    const [newOutcome, setNewOutcome] = useState({
        overall_rating_id: 0,
        executive_summary: '',
        effective_date: new Date().toISOString().split('T')[0],
        expiration_date: ''
    });
    const [approvalUpdate, setApprovalUpdate] = useState({ approval_id: 0, status: '', comments: '', isProxyApproval: false, certificationEvidence: '', proxyCertified: false });
    const [approvalValidationError, setApprovalValidationError] = useState<string | null>(null);
    const [showSignOffModal, setShowSignOffModal] = useState(false);
    const [signOffData, setSignOffData] = useState({ assignment_id: 0, comments: '' });
    const [overdueCommentary, setOverdueCommentary] = useState<CurrentOverdueCommentaryResponse | null>(null);
    const [showCommentaryModal, setShowCommentaryModal] = useState(false);
    const [showResubmitModal, setShowResubmitModal] = useState(false);
    const [resubmitResponse, setResubmitResponse] = useState('');
    const [commentaryModalType, setCommentaryModalType] = useState<OverdueType>('VALIDATION_IN_PROGRESS');
    const [editAssignment, setEditAssignment] = useState({
        assignment_id: 0,
        is_primary: false,
        is_reviewer: false,
        estimated_hours: '',
        actual_hours: ''
    });
    const [showSelectPrimaryModal, setShowSelectPrimaryModal] = useState(false);
    const [deleteAssignmentData, setDeleteAssignmentData] = useState({ assignment_id: 0, new_primary_id: 0 });
    const [priorValidation, setPriorValidation] = useState<PriorValidationSummary | null>(null);

    // Assessment warning modal state (for status transitions that trigger risk assessment checks)
    const [showAssessmentWarningModal, setShowAssessmentWarningModal] = useState(false);
    const [assessmentWarnings, setAssessmentWarnings] = useState<string[]>([]);
    const [pendingStatusUpdate, setPendingStatusUpdate] = useState<{ status_id: number; reason: string } | null>(null);
    const [pendingCompleteWork, setPendingCompleteWork] = useState<{ status_id: number; reason: string } | null>(null);

    // Pre-transition warning modal state (for PENDING_APPROVAL transitions)
    const [preTransitionWarnings, setPreTransitionWarnings] = useState<PreTransitionWarningsResponse | null>(null);
    const [showPreTransitionModal, setShowPreTransitionModal] = useState(false);
    const [pendingTransitionAction, setPendingTransitionAction] = useState<'complete_work' | 'status_update' | 'resubmit' | null>(null);
    const [pendingResubmitResponse, setPendingResubmitResponse] = useState<string>('');

    useEffect(() => {
        fetchData();
    }, [id]);

    // Fetch prior full validation (INITIAL or COMPREHENSIVE) when request has prior_full_validation_request_id
    useEffect(() => {
        const fetchPriorValidation = async () => {
            if (!request?.prior_full_validation_request_id) {
                setPriorValidation(null);
                return;
            }
            try {
                const response = await api.get(`/validation-workflow/requests/${request.prior_full_validation_request_id}`);
                const priorData = response.data;
                // prior_full_validation_request_id is already filtered to INITIAL/COMPREHENSIVE in backend
                setPriorValidation({
                    request_id: priorData.request_id,
                    validation_type: priorData.validation_type,
                    current_status: priorData.current_status,
                    completion_date: priorData.completion_date,
                    updated_at: priorData.updated_at,
                    outcome: priorData.outcome ? {
                        overall_rating: priorData.outcome.overall_rating,
                        executive_summary: priorData.outcome.executive_summary
                    } : null
                });
            } catch (err) {
                console.error('Failed to fetch prior validation:', err);
                setPriorValidation(null);
            }
        };
        fetchPriorValidation();
    }, [request?.prior_full_validation_request_id]);

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

    // Fetch overdue commentary when request is loaded
    useEffect(() => {
        const fetchOverdueCommentary = async () => {
            if (request?.request_id) {
                try {
                    const response = await overdueCommentaryApi.getForRequest(request.request_id);
                    setOverdueCommentary(response);
                } catch (error) {
                    console.error('Failed to fetch overdue commentary:', error);
                }
            }
        };
        fetchOverdueCommentary();
    }, [request?.request_id]);

    const handleOpenCommentaryModal = (type: OverdueType) => {
        setCommentaryModalType(type);
        setShowCommentaryModal(true);
    };

    const handleCommentarySuccess = async () => {
        // Refresh commentary data
        if (request?.request_id) {
            try {
                const response = await overdueCommentaryApi.getForRequest(request.request_id);
                setOverdueCommentary(response);
            } catch (error) {
                console.error('Failed to refresh commentary:', error);
            }
        }
    };

    // Check if this validation request is overdue
    const isOverdueValidation = () => {
        if (!request) return false;
        const targetDate = new Date(request.target_completion_date);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return targetDate < today && !['Approved', 'Cancelled'].includes(request.current_status.label);
    };

    const getOverdueDays = () => {
        if (!request) return 0;
        const targetDate = new Date(request.target_completion_date);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const diffTime = today.getTime() - targetDate.getTime();
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    };

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch request details, taxonomy options, users, assignment audit logs, approval audit logs, commentary audit logs, and SLA config in parallel
            const [requestRes, taxonomiesRes, usersRes, assignmentAuditRes, approvalAuditRes, commentaryAuditRes, slaRes] = await Promise.all([
                api.get(`/validation-workflow/requests/${id}`),
                api.get('/taxonomies/'),
                api.get('/auth/users'),
                api.get(`/audit-logs/?entity_type=ValidationAssignment&entity_id=${id}&limit=100`),
                api.get(`/audit-logs/?entity_type=ValidationApproval&entity_id=${id}&limit=100`),
                api.get(`/audit-logs/?entity_type=ValidationRequest&entity_id=${id}&limit=100`),
                api.get('/workflow-sla/validation').catch(() => ({ data: null })) // Gracefully handle if SLA not configured
            ]);

            setRequest(requestRes.data);
            setUsers(usersRes.data);
            setAssignmentAuditLogs(assignmentAuditRes.data);
            setApprovalAuditLogs(approvalAuditRes.data);
            // Filter commentary audit logs to only include overdue commentary entries
            const commentaryLogs = commentaryAuditRes.data.filter((log: AuditLog) =>
                log.action === 'overdue_commentary_created' || log.action === 'overdue_commentary_updated'
            );
            setCommentaryAuditLogs(commentaryLogs);
            setWorkflowSLA(slaRes.data);

            // Fetch model versions that link to this validation project
            const primaryModel = getPrimaryModel(requestRes.data.models);
            if (primaryModel && primaryModel.model_id && id) {
                try {
                    const versionsRes = await api.get(`/models/${primaryModel.model_id}/versions`);
                    const linkedVersions = versionsRes.data.filter((v: any) => v.validation_request_id === parseInt(id));
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

            // Fetch recommendation taxonomies for create modal
            const recPriorityTax = taxonomies.find((t: any) => t.name === 'Recommendation Priority');
            const recCategoryTax = taxonomies.find((t: any) => t.name === 'Recommendation Category');
            if (recPriorityTax) setRecPriorities(recPriorityTax.values || []);
            if (recCategoryTax) setRecCategories(recCategoryTax.values || []);

            // Fetch recommendations for the models in this validation
            if (requestRes.data.models && requestRes.data.models.length > 0) {
                try {
                    const modelIds = requestRes.data.models.map((m: any) => m.model_id);
                    // Fetch recommendations for all models
                    const recPromises = modelIds.map((modelId: number) =>
                        recommendationsApi.list({ model_id: modelId })
                    );
                    const recResults = await Promise.all(recPromises);
                    // Flatten and dedupe by recommendation_id
                    const allRecs = recResults.flat();
                    const uniqueRecs = allRecs.filter((rec, index, self) =>
                        index === self.findIndex(r => r.recommendation_id === rec.recommendation_id)
                    );
                    setRecommendations(uniqueRecs);
                } catch (err) {
                    console.error('Failed to fetch recommendations:', err);
                }
            }

            // Fetch limitations for this validation request
            try {
                const limitationsData = await listValidationRequestLimitations(parseInt(id!));
                setLimitations(limitationsData);
            } catch (err) {
                console.error('Failed to fetch limitations:', err);
            }

        } catch (err: any) {
            console.error('Failed to fetch request details:', err);
            setError(err.response?.data?.detail || 'Failed to load validation project');
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
            case 'Revision': return 'bg-amber-100 text-amber-800';  // Sent back for revisions
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
            case 'Sent Back': return 'bg-amber-100 text-amber-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    // Helper to check for unsaved plan changes before status transitions
    const checkUnsavedPlanChanges = async (): Promise<boolean> => {
        if (!validationPlanRef.current) return true; // No plan form, proceed

        const hasUnsaved = validationPlanRef.current.hasUnsavedChanges();
        if (!hasUnsaved) return true; // No unsaved changes, proceed

        // Prompt user
        const choice = window.confirm(
            'You have unsaved changes in the validation plan.\n\n' +
            'Click OK to save changes now, or Cancel to continue without saving (unsaved changes will be lost).'
        );

        if (choice) {
            // User wants to save
            const saveSuccess = await validationPlanRef.current.saveForm();
            if (!saveSuccess) {
                alert('Failed to save validation plan. Please fix any errors before changing status.');
                return false;
            }
            return true; // Save succeeded, proceed
        } else {
            // User chose to discard changes
            const confirmDiscard = window.confirm(
                'Are you sure you want to discard your unsaved validation plan changes?'
            );
            return confirmDiscard; // Only proceed if user confirms discard
        }
    };

    // Admin status update handler (with assessment warning support and pre-transition warning support)
    const handleStatusUpdate = async (skipAssessmentWarning: boolean = false, skipPreTransitionWarning: boolean = false) => {
        const statusToUpdate = pendingStatusUpdate || newStatus;
        if (!statusToUpdate.status_id) return;

        // Check for unsaved plan changes first (only if this is the initial request)
        if (!skipAssessmentWarning) {
            const canProceed = await checkUnsavedPlanChanges();
            if (!canProceed) return;
        }

        // Check if target status is PENDING_APPROVAL - if so, check for pre-transition warnings
        const targetStatus = statusOptions.find(s => s.value_id === statusToUpdate.status_id);
        if (targetStatus?.code === 'PENDING_APPROVAL' && !skipPreTransitionWarning) {
            try {
                const warningsResponse = await validationWorkflowApi.getPreTransitionWarnings(
                    Number(id),
                    'PENDING_APPROVAL'
                );
                if (warningsResponse.warnings.length > 0) {
                    // Store pending state and show modal
                    setPendingStatusUpdate(statusToUpdate);
                    setPreTransitionWarnings(warningsResponse);
                    setPendingTransitionAction('status_update');
                    setShowPreTransitionModal(true);
                    setShowStatusModal(false);
                    return; // Wait for user confirmation via modal
                }
            } catch (err) {
                // Fail-open: if warning check fails, proceed without warnings
                console.error('Failed to check pre-transition warnings:', err);
            }
        }

        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/requests/${id}/status`, {
                new_status_id: statusToUpdate.status_id,
                change_reason: statusToUpdate.reason || null,
                skip_assessment_warning: skipAssessmentWarning
            });
            setShowStatusModal(false);
            setShowAssessmentWarningModal(false);
            setNewStatus({ status_id: 0, reason: '' });
            setPendingStatusUpdate(null);
            setPendingTransitionAction(null);
            setAssessmentWarnings([]);
            fetchData();
        } catch (err: any) {
            // Check for 409 Conflict with assessment warnings
            if (err.response?.status === 409) {
                const detail = err.response?.data?.detail;
                if (detail?.warning_type === 'outdated_risk_assessment') {
                    // Store the pending status update and show warning modal
                    setPendingStatusUpdate(statusToUpdate);
                    setAssessmentWarnings(detail.warnings || [detail.message]);
                    setShowAssessmentWarningModal(true);
                    setShowStatusModal(false);
                    return;
                }
            }
            // Handle other errors (including 400 blocking errors)
            const errorDetail = err.response?.data?.detail;
            if (typeof errorDetail === 'string') {
                setError(errorDetail);
            } else if (typeof errorDetail === 'object' && errorDetail?.message) {
                setError(errorDetail.message);
            } else {
                setError('Failed to update status');
            }
        } finally {
            setActionLoading(false);
        }
    };

    const handleConfirmAssessmentWarning = () => {
        // User acknowledged the warning, retry with skip flag
        if (pendingCompleteWork) {
            // Retry complete work action
            handleCompleteWork(true);
        } else if (pendingStatusUpdate) {
            // Retry status update
            handleStatusUpdate(true);
        }
    };

    const handleCancelAssessmentWarning = () => {
        setShowAssessmentWarningModal(false);
        setPendingStatusUpdate(null);
        setPendingCompleteWork(null);
        setAssessmentWarnings([]);
    };

    // Hold/Cancel/Resume handlers
    const handlePutOnHold = async () => {
        if (holdReason.trim().length < 10) {
            setError('Hold reason must be at least 10 characters');
            return;
        }
        setActionLoading(true);
        try {
            await api.post(`/validation-workflow/requests/${id}/hold`, {
                hold_reason: holdReason.trim()
            });
            setShowHoldModal(false);
            setHoldReason('');
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to put request on hold');
        } finally {
            setActionLoading(false);
        }
    };

    const handleCancelRequest = async () => {
        if (cancelReason.trim().length < 10) {
            setError('Cancel reason must be at least 10 characters');
            return;
        }
        setActionLoading(true);
        try {
            await api.post(`/validation-workflow/requests/${id}/cancel`, {
                cancel_reason: cancelReason.trim()
            });
            setShowCancelModal(false);
            setCancelReason('');
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to cancel request');
        } finally {
            setActionLoading(false);
        }
    };

    const handleResumeFromHold = async () => {
        setActionLoading(true);
        try {
            await api.post(`/validation-workflow/requests/${id}/resume`, {
                resume_notes: resumeNotes.trim() || null
            });
            setShowResumeModal(false);
            setResumeNotes('');
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to resume request');
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

        // Check if this is the last validator - allow removal in PLANNING (will auto-revert to INTAKE)
        if (request && request.assignments.length <= 1 && request.current_status?.code !== 'PLANNING') {
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
        // INTERIM validations require expiration date
        if (request?.validation_type?.code === 'INTERIM' && !newOutcome.expiration_date) {
            setError('Expiration date is required for INTERIM validations. Interim approvals are time-limited and must have an expiration date.');
            return;
        }
        setActionLoading(true);
        try {
            await api.post(`/validation-workflow/requests/${id}/outcome`, {
                overall_rating_id: newOutcome.overall_rating_id,
                executive_summary: newOutcome.executive_summary,
                effective_date: newOutcome.effective_date,
                expiration_date: newOutcome.expiration_date || null
            });
            setShowOutcomeModal(false);
            setNewOutcome({
                overall_rating_id: 0,
                executive_summary: '',
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
        // INTERIM validations require expiration date
        if (request?.validation_type?.code === 'INTERIM' && !newOutcome.expiration_date) {
            setError('Expiration date is required for INTERIM validations. Interim approvals are time-limited and must have an expiration date.');
            return;
        }
        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/outcomes/${request.outcome.outcome_id}`, {
                overall_rating_id: newOutcome.overall_rating_id,
                executive_summary: newOutcome.executive_summary,
                effective_date: newOutcome.effective_date,
                expiration_date: newOutcome.expiration_date || null
            });
            setShowOutcomeModal(false);
            setNewOutcome({
                overall_rating_id: 0,
                executive_summary: '',
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
        setApprovalValidationError(null);

        if (!approvalUpdate.status) {
            setApprovalValidationError('Please select a decision');
            return;
        }

        // Validate comments required for "Sent Back"
        if (approvalUpdate.status === 'Sent Back' && !approvalUpdate.comments?.trim()) {
            setApprovalValidationError('Comments are required when sending back for revision. Please explain what needs to be addressed.');
            return;
        }

        // Validate proxy approval certification (not required for Send Back)
        if (approvalUpdate.isProxyApproval && approvalUpdate.status !== 'Sent Back') {
            if (!approvalUpdate.certificationEvidence.trim()) {
                setApprovalValidationError('Authorization evidence is required. Please provide a reference to the documentation that evidences proper authorization.');
                return;
            }
            if (!approvalUpdate.proxyCertified) {
                setApprovalValidationError('You must certify that you have obtained proper authorization by checking the certification box.');
                return;
            }
        }

        setActionLoading(true);
        try {
            // Build comments with certification evidence if proxy approval (not for Send Back)
            let finalComments = approvalUpdate.comments || '';
            if (approvalUpdate.isProxyApproval && approvalUpdate.status !== 'Sent Back' && approvalUpdate.certificationEvidence) {
                finalComments = `${finalComments}\n\n[PROXY APPROVAL - Authorization Evidence: ${approvalUpdate.certificationEvidence}]`.trim();
            }

            await api.patch(`/validation-workflow/approvals/${approvalUpdate.approval_id}`, {
                approval_status: approvalUpdate.status,
                comments: finalComments || null
            });
            setShowApprovalModal(false);
            setApprovalUpdate({ approval_id: 0, status: '', comments: '', isProxyApproval: false, certificationEvidence: '', proxyCertified: false });
            setApprovalValidationError(null);
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update approval');
        } finally {
            setActionLoading(false);
        }
    };

    const handleOpenSubmissionModal = async () => {
        if (!request || !request.models || request.models.length === 0) return;

        // Load available versions for the first model
        try {
            const primary = getPrimaryModel(request.models);
            if (!primary) return;
            const modelId = primary.model_id;
            const versionsRes = await api.get(`/models/${modelId}/versions`);
            setAvailableVersions(versionsRes.data);

            // Pre-select the currently associated version if there is one linked to this validation
            const linkedVersion = versionsRes.data.find((v: ModelVersion) =>
                v.validation_request_id === request.request_id
            );
            if (linkedVersion) {
                setSubmissionConfirmedVersionId(linkedVersion.version_id);
            } else {
                setSubmissionConfirmedVersionId(null);
            }
        } catch (err) {
            console.error('Failed to fetch versions:', err);
            setAvailableVersions([]);
            setSubmissionConfirmedVersionId(null);
        }

        // Reset the metadata fields
        setSubmissionDocVersion('');
        setSubmissionModelVersion('');
        setSubmissionDocId('');
        setSubmissionNotes('');
        setShowSubmissionModal(true);
    };

    const handleMarkSubmissionReceived = async () => {
        if (!request) return;

        setActionLoading(true);
        try {
            await api.post(`/validation-workflow/requests/${id}/mark-submission`, {
                submission_received_date: submissionReceivedDate,
                notes: submissionNotes.trim() || null,
                confirmed_model_version_id: submissionConfirmedVersionId || null,
                model_documentation_version: submissionDocVersion.trim() || null,
                model_submission_version: submissionModelVersion.trim() || null,
                model_documentation_id: submissionDocId.trim() || null
            });
            setShowSubmissionModal(false);
            setSubmissionNotes('');
            setSubmissionDocVersion('');
            setSubmissionModelVersion('');
            setSubmissionDocId('');
            setSubmissionConfirmedVersionId(null);
            await fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to mark submission as received');
        } finally {
            setActionLoading(false);
        }
    };

    const handleCompleteWork = async (skipAssessmentWarning: boolean = false, skipPreTransitionWarning: boolean = false) => {
        if (!request) return;

        // Check if outcome has been created
        if (!request.outcome) {
            setError('Cannot complete work without creating a validation outcome. Please go to the Outcome tab and complete the validation outcome form.');
            return;
        }

        // Check for unsaved plan changes (only on initial request)
        if (!skipAssessmentWarning) {
            const canProceed = await checkUnsavedPlanChanges();
            if (!canProceed) return;
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

        // Only show confirmation on first attempt (not when retrying after assessment warning)
        if (!skipAssessmentWarning) {
            const confirmMessage = warningMessage + 'Are you sure you want to complete this validation?';
            if (!confirm(confirmMessage)) return;
        }

        // Check for pre-transition warnings when moving to PENDING_APPROVAL
        if (targetStatusCode === 'PENDING_APPROVAL' && !skipPreTransitionWarning) {
            try {
                const warningsResponse = await validationWorkflowApi.getPreTransitionWarnings(
                    Number(id),
                    'PENDING_APPROVAL'
                );
                if (warningsResponse.warnings.length > 0) {
                    setPreTransitionWarnings(warningsResponse);
                    setPendingTransitionAction('complete_work');
                    setShowPreTransitionModal(true);
                    return; // Wait for user confirmation via modal
                }
            } catch (err) {
                // Fail-open: if warning check fails, proceed without warnings
                console.error('Failed to check pre-transition warnings:', err);
            }
        }

        const targetStatus = statusOptions.find(s => s.code === targetStatusCode);
        if (!targetStatus) {
            setError(`${targetStatusCode} status not found`);
            return;
        }

        const changeReason = hasReviewer ? 'Work completed, ready for review' : 'Work completed, moving to approval (no reviewer assigned)';

        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/requests/${id}/status`, {
                new_status_id: targetStatus.value_id,
                change_reason: changeReason,
                skip_assessment_warning: skipAssessmentWarning
            });
            // Clear any pending state on success
            setPendingCompleteWork(null);
            setAssessmentWarnings([]);
            setShowAssessmentWarningModal(false);
            await fetchData();
        } catch (err: any) {
            // Check for 409 Conflict with assessment warnings
            if (err.response?.status === 409) {
                const detail = err.response?.data?.detail;
                if (detail?.warning_type === 'outdated_risk_assessment') {
                    // Store the pending action and show warning modal
                    setPendingCompleteWork({ status_id: targetStatus.value_id, reason: changeReason });
                    setAssessmentWarnings(detail.warnings || [detail.message]);
                    setShowAssessmentWarningModal(true);
                    return;
                }
            }
            // Handle other errors
            const errorDetail = err.response?.data?.detail;
            if (typeof errorDetail === 'string') {
                setError(errorDetail);
            } else if (typeof errorDetail === 'object' && errorDetail?.message) {
                setError(errorDetail.message);
            } else {
                setError('Failed to complete work');
            }
        } finally {
            setActionLoading(false);
        }
    };

    // Handle sending validation back from Pending Approval to In Progress
    const handleSendBackToInProgress = async () => {
        if (!request) return;
        setShowSendBackModal(true);
    };

    const confirmSendBackToInProgress = async () => {
        if (!request) return;

        const trimmedReason = sendBackReason.trim();
        if (!trimmedReason) {
            setError('A reason is required to send back to In Progress.');
            return;
        }

        const inProgressStatus = statusOptions.find(s => s.code === 'IN_PROGRESS');
        if (!inProgressStatus) {
            setError('IN_PROGRESS status not found');
            return;
        }

        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/requests/${id}/status`, {
                new_status_id: inProgressStatus.value_id,
                change_reason: trimmedReason
            });
            setShowSendBackModal(false);
            setSendBackReason('');
            await fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to send back to In Progress');
        } finally {
            setActionLoading(false);
        }
    };

    // Get the most recent send-back feedback from status history
    const getSendBackFeedback = () => {
        if (!request?.status_history) return null;
        // Find the most recent transition TO REVISION status
        const revisionEntry = request.status_history.find(
            h => h.new_status?.code === 'REVISION'
        );
        if (!revisionEntry) return null;

        // Extract the feedback - format is "Sent back by {role}: {comments}"
        const reason = revisionEntry.change_reason || '';
        const match = reason.match(/^Sent back by (.+?): (.+)$/s);
        if (match) {
            return {
                approverRole: match[1],
                comments: match[2],
                date: revisionEntry.changed_at
            };
        }
        return { approverRole: 'Approver', comments: reason, date: revisionEntry.changed_at };
    };

    // Get the most recent hold reason from status history
    const getLastHoldReason = () => {
        if (!request?.status_history) return null;
        // Find the most recent transition TO ON_HOLD status
        const holdEntries = request.status_history
            .filter(h => h.new_status?.code === 'ON_HOLD')
            .sort((a, b) => new Date(b.changed_at).getTime() - new Date(a.changed_at).getTime());
        if (holdEntries.length === 0) return null;
        const mostRecent = holdEntries[0];
        return {
            reason: mostRecent.change_reason || 'No reason provided',
            date: mostRecent.changed_at,
            changedBy: mostRecent.changed_by?.full_name || 'Unknown'
        };
    };

    // Handle resubmitting validation from REVISION to PENDING_APPROVAL
    const handleResubmitForApproval = async (skipPreTransitionWarning: boolean = false) => {
        if (!request || !resubmitResponse.trim()) return;

        const pendingApprovalStatus = statusOptions.find(s => s.code === 'PENDING_APPROVAL');
        if (!pendingApprovalStatus) {
            setError('PENDING_APPROVAL status not found');
            return;
        }

        // Check for pre-transition warnings before moving to PENDING_APPROVAL
        if (!skipPreTransitionWarning) {
            try {
                const warningsResponse = await validationWorkflowApi.getPreTransitionWarnings(
                    Number(id),
                    'PENDING_APPROVAL'
                );
                if (warningsResponse.warnings.length > 0) {
                    // Store pending state and show modal
                    setPendingResubmitResponse(resubmitResponse);
                    setPreTransitionWarnings(warningsResponse);
                    setPendingTransitionAction('resubmit');
                    setShowPreTransitionModal(true);
                    setShowResubmitModal(false);
                    return; // Wait for user confirmation via modal
                }
            } catch (err) {
                // Fail-open: if warning check fails, proceed without warnings
                console.error('Failed to check pre-transition warnings:', err);
            }
        }

        setActionLoading(true);
        try {
            await api.patch(`/validation-workflow/requests/${id}/status`, {
                new_status_id: pendingApprovalStatus.value_id,
                change_reason: resubmitResponse
            });
            setShowResubmitModal(false);
            setResubmitResponse('');
            setPendingResubmitResponse('');
            await fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to resubmit for approval');
        } finally {
            setActionLoading(false);
        }
    };

    // Handle downloading effective challenge PDF report
    const handleDownloadEffectiveChallengeReport = async () => {
        if (!request) return;

        setActionLoading(true);
        try {
            const response = await api.get(`/validation-workflow/requests/${id}/effective-challenge-report`, {
                responseType: 'blob'
            });

            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `effective_challenge_VR${id}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to download report');
        } finally {
            setActionLoading(false);
        }
    };

    const handleModelsUpdated = async (response: ValidationRequestModelUpdateResponse) => {
        const notices: string[] = [];
        if (response.warnings?.length) {
            response.warnings.forEach((warning) => {
                notices.push(`${warning.severity}: ${warning.message}`);
            });
        }
        if (response.validators_unassigned?.length) {
            notices.push(`Validators unassigned: ${response.validators_unassigned.join(', ')}`);
        }
        if (response.plan_deviations_flagged > 0) {
            notices.push(`${response.plan_deviations_flagged} plan component(s) flagged for review.`);
        }
        if (response.approvals_voided > 0 || response.approvals_added > 0) {
            notices.push(`Approvals updated: +${response.approvals_added} / voided ${response.approvals_voided}.`);
        }
        if (response.conditional_approvals_added > 0 || response.conditional_approvals_voided > 0) {
            notices.push(`Conditional approvals updated: +${response.conditional_approvals_added} / voided ${response.conditional_approvals_voided}.`);
        }
        setModelChangeNotices(notices);
        setShowManageModelsModal(false);
        await fetchData();
    };

    const canEditRequest = canManageValidationsFlag;
    const canEditModels = (
        canManageValidationsFlag &&
        (request?.current_status?.code === 'INTAKE' || request?.current_status?.code === 'PLANNING')
    );
    const primaryModel = getPrimaryModel(request?.models);
    const isPrimaryValidator = request && user && request.assignments.some(
        a => a.is_primary && a.validator.user_id === user.user_id
    );

    // Helper functions for workflow timing
    const getTimeInCurrentStage = () => {
        if (!request) return 0;
        const currentStatusEntry = request.status_history
            .filter(h => h.new_status.label === request.current_status.label)
            .sort((a, b) => new Date(b.changed_at).getTime() - new Date(a.changed_at).getTime())[0];

        // If no status history entry found, fallback to created_at date
        // This handles cases where requests were created before status history tracking
        // or where the initial status was set directly without a history entry
        const statusChangeDate = currentStatusEntry
            ? new Date(currentStatusEntry.changed_at)
            : new Date(request.created_at);

        const now = new Date();
        const diffMs = now.getTime() - statusChangeDate.getTime();
        // Use Math.max to prevent negative days due to minor clock differences
        return Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));
    };

    const getStageSLA = (stageName: string): number | null => {
        if (!workflowSLA) return null;

        // For 'In Progress', use risk-tier-based lead time from the request
        // This varies by model risk tier (configured in Validation Policies per risk tier)
        if (stageName === 'In Progress' && request) {
            return request.applicable_lead_time_days ?? 90; // Default fallback
        }

        const stageMap: { [key: string]: keyof WorkflowSLA } = {
            'Intake': 'assignment_days',
            'Planning': 'assignment_days',
            'Review': 'begin_work_days',
            'Pending Approval': 'approval_days'
        };

        const slaField = stageMap[stageName];
        return slaField ? workflowSLA[slaField] as number : null;
    };

    const getStageStatus = (stageName: string) => {
        if (!request) return { completed: false, current: false, daysInStage: 0, slaDays: null, daysRemaining: null, isOverdue: false };

        const isCompleted = request.status_history.some(h => h.new_status.label === stageName);
        const isCurrent = request.current_status.label === stageName;
        const slaDays = getStageSLA(stageName);

        let daysInStage = 0;
        let daysRemaining: number | null = null;
        let isOverdue = false;

        if (isCurrent) {
            daysInStage = getTimeInCurrentStage();
            if (slaDays !== null) {
                daysRemaining = slaDays - daysInStage;
                isOverdue = daysRemaining < 0;
            }
        }

        return { completed: isCompleted, current: isCurrent, daysInStage, slaDays, daysRemaining, isOverdue };
    };

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
                    <h2 className="text-2xl font-bold mb-4">Validation Project Not Found</h2>
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
                        Validation Project #{request.request_id}
                    </h2>
                    <div className="flex items-center gap-3 mt-2">
                        {primaryModel && (
                            <Link
                                to={`/models/${primaryModel.model_id}`}
                                className="text-blue-600 hover:text-blue-800 font-medium"
                            >
                                {primaryModel.model_name}
                            </Link>
                        )}
                        <span className={`px-2 py-1 text-xs rounded ${getStatusColor(request.current_status.label)}`}>
                            {request.current_status.label}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(request.priority.label)}`}>
                            {request.priority.label} Priority
                        </span>
                    </div>
                </div>
                <div className="flex gap-2">
                    {canEditModels && (
                        <button
                            onClick={() => setShowManageModelsModal(true)}
                            className="bg-slate-700 text-white px-4 py-2 rounded hover:bg-slate-800"
                        >
                            Manage Models
                        </button>
                    )}
                    {/* Mark Submission Received Button */}
                    {isPrimaryValidator && request.current_status.code === 'PLANNING' && (
                        <button
                            onClick={handleOpenSubmissionModal}
                            disabled={actionLoading}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                        >
                            Mark Submission Received
                        </button>
                    )}

                    {/* Admin Mark Submission Received Button (Admin only, when in Planning) */}
                    {canViewAdminDashboardFlag && !isPrimaryValidator && request.current_status.code === 'PLANNING' && (
                        <button
                            onClick={handleOpenSubmissionModal}
                            disabled={actionLoading}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                        >
                            Mark Submission Received
                        </button>
                    )}

                    {/* Complete Work Button */}
                    {isPrimaryValidator && request.current_status.code === 'IN_PROGRESS' && (
                        <button
                            onClick={() => handleCompleteWork()}
                            disabled={actionLoading}
                            className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
                        >
                            {actionLoading ? 'Completing...' : 'Complete Work'}
                        </button>
                    )}

                    {/* Admin Progress Work Button (Admin only, when in In Progress) */}
                    {canViewAdminDashboardFlag && request.current_status.code === 'IN_PROGRESS' && (
                        <button
                            onClick={() => handleCompleteWork()}
                            disabled={actionLoading}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                        >
                            {actionLoading ? 'Progressing...' : 'Progress to Review'}
                        </button>
                    )}

                    {/* Send Back to In Progress Button (Admin only, when in Pending Approval) */}
                    {canViewAdminDashboardFlag && request.current_status.code === 'PENDING_APPROVAL' && (
                        <button
                            onClick={handleSendBackToInProgress}
                            disabled={actionLoading}
                            className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 disabled:opacity-50"
                        >
                            {actionLoading ? 'Sending Back...' : 'Send Back to In Progress'}
                        </button>
                    )}

                    {/* Resubmit for Approval Button (when in REVISION status) */}
                    {canEditRequest && request.current_status.code === 'REVISION' && (
                        <button
                            onClick={() => setShowResubmitModal(true)}
                            disabled={actionLoading}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                        >
                            Resubmit for Approval
                        </button>
                    )}

                    {/* Deploy Approved Version Button (Issue 5: when validation is APPROVED) */}
                    {request.current_status.code === 'APPROVED' && relatedVersions.length > 0 && (
                        <button
                            onClick={() => {
                                const approvedVersion = relatedVersions.find(v => v.status === 'APPROVED' || v.status === 'ACTIVE');
                                if (approvedVersion) {
                                    setDeployVersion(approvedVersion);
                                    setShowDeployModal(true);
                                }
                            }}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                        >
                            Deploy Approved Version
                        </button>
                    )}

                    {/* Hold/Cancel/Resume Buttons - replaces generic Update Status for cleaner workflow */}
                    {canEditRequest && !['APPROVED', 'CANCELLED', 'ON_HOLD'].includes(request.current_status.code) && (
                        <>
                            <button
                                onClick={() => setShowHoldModal(true)}
                                className="bg-amber-600 text-white px-4 py-2 rounded hover:bg-amber-700"
                            >
                                Put on Hold
                            </button>
                            <button
                                onClick={() => setShowCancelModal(true)}
                                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                            >
                                Cancel Request
                            </button>
                        </>
                    )}

                    {/* Resume and Cancel when ON_HOLD */}
                    {canEditRequest && request.current_status.code === 'ON_HOLD' && (
                        <>
                            <button
                                onClick={() => setShowResumeModal(true)}
                                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                            >
                                Resume Work
                            </button>
                            <button
                                onClick={() => setShowCancelModal(true)}
                                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                            >
                                Cancel Request
                            </button>
                        </>
                    )}

                </div>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                    <button onClick={() => setError(null)} className="float-right font-bold">×</button>
                </div>
            )}

            {modelChangeNotices.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 text-blue-900 px-4 py-3 rounded mb-4">
                    <div className="flex items-start justify-between">
                        <span className="font-medium">Model changes saved</span>
                        <button onClick={() => setModelChangeNotices([])} className="font-bold">×</button>
                    </div>
                    <ul className="mt-2 list-disc ml-5 text-sm space-y-1">
                        {modelChangeNotices.map((notice, index) => (
                            <li key={`${notice}-${index}`}>{notice}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* On Hold Banner - shown when request is currently on hold */}
            {request.current_status?.code === 'ON_HOLD' && (() => {
                const holdInfo = getLastHoldReason();
                return (
                    <div className="bg-amber-50 border-l-4 border-amber-500 p-4 mb-6">
                        <div className="flex items-start">
                            <svg className="h-6 w-6 text-amber-600 mt-0.5 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25v13.5m-7.5-13.5v13.5" />
                            </svg>
                            <div className="flex-1">
                                <h3 className="text-sm font-bold text-amber-800">
                                    This Validation Request is ON HOLD
                                </h3>
                                <div className="mt-1 text-sm text-amber-700 space-y-1">
                                    <p>
                                        <strong>Duration:</strong> {request.total_hold_days} day{request.total_hold_days !== 1 ? 's' : ''}
                                        {request.previous_status_before_hold && (
                                            <span className="ml-3">
                                                <strong>Previous status:</strong> {request.previous_status_before_hold}
                                            </span>
                                        )}
                                    </p>
                                    {holdInfo && (
                                        <p className="text-xs text-amber-600">
                                            Put on hold by {holdInfo.changedBy} on {holdInfo.date.split('T')[0]}
                                        </p>
                                    )}
                                </div>
                                {holdInfo && (
                                    <div className="mt-2 p-3 bg-white border border-amber-200 rounded">
                                        <p className="text-sm text-gray-700 font-medium mb-1">Reason:</p>
                                        <p className="text-sm text-gray-800 whitespace-pre-wrap">{holdInfo.reason}</p>
                                    </div>
                                )}
                                <p className="text-sm text-amber-700 mt-3">
                                    Team SLA clock is paused. Click <strong>"Resume Work"</strong> to continue validation.
                                </p>
                            </div>
                        </div>
                    </div>
                );
            })()}

            {/* Revision Feedback Banner - shown when request is sent back for revision */}
            {request.current_status?.code === 'REVISION' && (() => {
                const feedback = getSendBackFeedback();
                return feedback ? (
                    <div className="bg-amber-50 border-l-4 border-amber-500 p-4 mb-6">
                        <div className="flex items-start">
                            <svg className="h-6 w-6 text-amber-600 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            <div className="flex-1">
                                <h3 className="text-sm font-bold text-amber-800">Revision Requested</h3>
                                <p className="text-xs text-amber-600 mt-0.5">
                                    Sent back by {feedback.approverRole} on {new Date(feedback.date).toLocaleDateString()}
                                </p>
                                <div className="mt-2 p-3 bg-white border border-amber-200 rounded">
                                    <p className="text-sm text-gray-800 whitespace-pre-wrap">{feedback.comments}</p>
                                </div>
                                <p className="text-sm text-amber-700 mt-3">
                                    Please address the feedback above and click <strong>"Resubmit for Approval"</strong> when ready.
                                </p>
                            </div>
                        </div>
                    </div>
                ) : null;
            })()}

            {/* Overdue Validation Alert Banner */}
            {isOverdueValidation() && (
                <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
                    <div className="flex items-start">
                        <svg className="h-5 w-5 text-red-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        <div className="flex-1">
                            <h3 className="text-sm font-bold text-red-800">Validation Overdue</h3>
                            <p className="text-sm text-red-700 mt-1">
                                This validation is <strong>{getOverdueDays()} days overdue</strong>.
                                Target completion was {request.target_completion_date.split('T')[0]}.
                            </p>
                            {/* Commentary Status - Only ask validator for explanation if submission was received.
                                If submission hasn't been received, the delay is due to the owner/developer not submitting,
                                so only PRE_SUBMISSION commentary should be required. */}
                            {request.submission_received_date && overdueCommentary && (
                                <div className="mt-3 pt-3 border-t border-red-200">
                                    {overdueCommentary.has_current_comment && overdueCommentary.current_comment ? (
                                        <div className="text-sm">
                                            <p className="text-red-800">
                                                <span className="font-medium">Current explanation:</span>{' '}
                                                <span className="italic">"{overdueCommentary.current_comment.reason_comment}"</span>
                                            </p>
                                            <p className="text-red-700 text-xs mt-1">
                                                Target: {overdueCommentary.current_comment.target_date.split('T')[0]} •
                                                By: {overdueCommentary.current_comment.created_by_user.full_name}
                                                {overdueCommentary.is_stale && (
                                                    <span className="ml-2 text-red-900 font-medium">
                                                        ⚠ Update required: {overdueCommentary.stale_reason}
                                                    </span>
                                                )}
                                            </p>
                                        </div>
                                    ) : (
                                        <p className="text-sm text-red-800 font-medium">
                                            ⚠ No explanation provided for this delay
                                        </p>
                                    )}
                                    <button
                                        onClick={() => handleOpenCommentaryModal('VALIDATION_IN_PROGRESS')}
                                        className="mt-2 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                                    >
                                        {overdueCommentary.has_current_comment ? 'Update Explanation' : 'Provide Explanation'}
                                    </button>
                                </div>
                            )}
                            {/* If submission hasn't been received, show message explaining the cause */}
                            {!request.submission_received_date && (
                                <div className="mt-3 pt-3 border-t border-red-200">
                                    <p className="text-sm text-red-800">
                                        <span className="font-medium">Cause:</span> Model documentation has not been submitted for validation.
                                        The model owner/developer must submit documentation and provide an explanation for this delay.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Submission Required Banner - shows when validation is overdue but submission not received */}
            {isOverdueValidation() && !request.submission_received_date && (
                <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 mb-6">
                    <div className="flex items-start">
                        <svg className="h-5 w-5 text-yellow-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                        <div className="flex-1">
                            <h3 className="text-sm font-bold text-yellow-800">Submission Required - Owner/Developer Action Needed</h3>
                            <p className="text-sm text-yellow-700 mt-1">
                                Model documentation has not been submitted for validation.
                                The model owner/developer must provide an explanation for this delay.
                            </p>
                            {/* Commentary Status for Pre-Submission */}
                            {overdueCommentary && (
                                <div className="mt-3 pt-3 border-t border-yellow-200">
                                    {overdueCommentary.has_current_comment && overdueCommentary.current_comment ? (
                                        <div className="text-sm">
                                            <p className="text-yellow-800">
                                                <span className="font-medium">Current explanation:</span>{' '}
                                                <span className="italic">"{overdueCommentary.current_comment.reason_comment}"</span>
                                            </p>
                                            <p className="text-yellow-700 text-xs mt-1">
                                                Target submission: {overdueCommentary.current_comment.target_date.split('T')[0]} •
                                                By: {overdueCommentary.current_comment.created_by_user.full_name}
                                                {overdueCommentary.is_stale && (
                                                    <span className="ml-2 text-yellow-900 font-medium">
                                                        ⚠ Update required: {overdueCommentary.stale_reason}
                                                    </span>
                                                )}
                                            </p>
                                        </div>
                                    ) : (
                                        <p className="text-sm text-yellow-800 font-medium">
                                            ⚠ No explanation provided for this delay
                                        </p>
                                    )}
                                    <button
                                        onClick={() => handleOpenCommentaryModal('PRE_SUBMISSION')}
                                        className="mt-2 px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700"
                                    >
                                        {overdueCommentary.has_current_comment ? 'Update Explanation' : 'Provide Explanation'}
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="-mb-px flex space-x-8">
                    {(['overview', 'assignments', 'plan', 'scorecard', 'outcome', 'limitations', 'approvals', 'history'] as TabType[]).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => {
                                // Prevent navigating away from the plan tab if there are unsaved changes
                                if (
                                    activeTab === 'plan' &&
                                    tab !== 'plan' &&
                                    validationPlanRef.current?.hasUnsavedChanges()
                                ) {
                                    const confirmLeave = window.confirm(
                                        'You have unsaved changes in the validation plan. Leaving will discard them. Continue?'
                                    );
                                    if (!confirmLeave) return;
                                }
                                setActiveTab(tab);
                            }}
                            className={`py-2 px-1 border-b-2 font-medium text-sm capitalize ${activeTab === tab
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                        >
                            {tab === 'outcome' ? 'Outcome & Recommendations' : tab}
                            {tab === 'assignments' && ` (${request.assignments.length})`}
                            {tab === 'approvals' && ` (${request.approvals.length})`}
                            {tab === 'history' && ` (${request.status_history.length + assignmentAuditLogs.length + approvalAuditLogs.length + commentaryAuditLogs.length})`}
                            {tab === 'outcome' && recommendations.length > 0 && ` (${recommendations.length})`}
                            {tab === 'limitations' && limitations.length > 0 && ` (${limitations.length})`}
                        </button>
                    ))}
                </nav>
            </div>

            {/* Tab Content */}
            <div className="bg-white rounded-lg shadow-md p-6">
                {activeTab === 'overview' && (
                    <div>
                        {/* Prior Validation Summary */}
                        {priorValidation && (
                            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-md font-semibold text-blue-900 flex items-center gap-2">
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        Prior Validation Summary
                                    </h3>
                                    <Link
                                        to={`/validation-workflow/${priorValidation.request_id}`}
                                        className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                                    >
                                        View Full Details →
                                    </Link>
                                </div>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                    <div>
                                        <span className="text-gray-500">Type:</span>{' '}
                                        <span className="font-medium">{priorValidation.validation_type.label}</span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Status:</span>{' '}
                                        <span className={`font-medium ${priorValidation.current_status.code === 'APPROVED' ? 'text-green-700' : 'text-gray-700'}`}>
                                            {priorValidation.current_status.label}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Completed:</span>{' '}
                                        <span className="font-medium">
                                            {priorValidation.completion_date
                                                ? priorValidation.completion_date.split('T')[0]
                                                : priorValidation.updated_at.split('T')[0]}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Rating:</span>{' '}
                                        <span className={`font-medium ${
                                            priorValidation.outcome?.overall_rating?.code === 'FIT_FOR_PURPOSE' ? 'text-green-700' :
                                            priorValidation.outcome?.overall_rating?.code === 'NOT_FIT_FOR_PURPOSE' ? 'text-red-700' :
                                            'text-gray-500'
                                        }`}>
                                            {priorValidation.outcome?.overall_rating?.label || 'Not recorded'}
                                        </span>
                                    </div>
                                </div>
                                {priorValidation.outcome?.executive_summary && (
                                    <div className="mt-3 pt-3 border-t border-blue-200">
                                        <span className="text-gray-500 text-sm">Summary:</span>
                                        <p className="text-sm text-gray-700 mt-1 line-clamp-2">
                                            {priorValidation.outcome.executive_summary}
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}

                        <h3 className="text-lg font-bold mb-4">Project Overview</h3>
                        <div className="grid grid-cols-2 gap-6">
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Project ID</h4>
                                <p className="text-lg font-mono">#{request.request_id}</p>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Model</h4>
                                {primaryModel && (
                                    <>
                                        <Link to={`/models/${primaryModel.model_id}`} className="text-blue-600 hover:text-blue-800">
                                            {primaryModel.model_name}
                                        </Link>
                                        <span className="ml-2 text-sm text-gray-500">({primaryModel.status})</span>
                                    </>
                                )}
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">External Project ID</h4>
                                {request.external_project_id ? (
                                    <p className="text-lg font-mono">{request.external_project_id}</p>
                                ) : (
                                    <p className="text-sm text-gray-400 italic">Not set</p>
                                )}
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
                                <h4 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-1">
                                    Project Date
                                    <span
                                        className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-300 text-white text-xs cursor-help"
                                        title="The date when this validation project was initiated and opened in the system"
                                    >
                                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                        </svg>
                                    </span>
                                </h4>
                                <p className="text-lg">{request.request_date}</p>
                            </div>
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-1">
                                    Original Target Date
                                    <span
                                        className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-300 text-white text-xs cursor-help"
                                        title="The original target completion date calculated from policy (submission grace period + lead time)"
                                    >
                                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                        </svg>
                                    </span>
                                </h4>
                                <p className="text-lg">{request.target_completion_date}</p>
                            </div>
                            {overdueCommentary?.computed_completion_date && (
                                <div>
                                    <h4 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-1">
                                        Latest Target Date
                                        <span
                                            className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-300 text-white text-xs cursor-help"
                                            title={overdueCommentary.overdue_type === 'PRE_SUBMISSION'
                                                ? "Projected validation completion date (owner's submission target + policy lead time)"
                                                : "Validator's estimated completion date"}
                                        >
                                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                            </svg>
                                        </span>
                                    </h4>
                                    <p className="text-lg text-amber-600 font-medium">{overdueCommentary.computed_completion_date}</p>
                                </div>
                            )}
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-1">
                                    Documentation Submitted
                                    <span
                                        className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-300 text-white text-xs cursor-help"
                                        title="The date when the model owner submitted model development documentation to the validation team"
                                    >
                                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                        </svg>
                                    </span>
                                </h4>
                                {request.submission_received_date ? (
                                    <p className="text-lg">{request.submission_received_date.split('T')[0]}</p>
                                ) : (
                                    <p className="text-sm text-gray-400 italic">Not yet submitted</p>
                                )}
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
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1 flex items-center gap-1">
                                    Date Approved
                                    <span
                                        className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-300 text-white text-xs cursor-help"
                                        title="The date when the last required approval was obtained, marking the validation as complete"
                                    >
                                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                        </svg>
                                    </span>
                                </h4>
                                {request.completion_date ? (
                                    <p className="text-lg">
                                        {request.completion_date.split('T')[0]}
                                    </p>
                                ) : (
                                    <p className="text-sm text-gray-400 italic">Not yet approved</p>
                                )}
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
                                                        <span className={`ml-2 px-2 py-0.5 rounded text-xs font-semibold ${version.change_type === 'MAJOR'
                                                            ? 'bg-orange-200 text-orange-800'
                                                            : 'bg-blue-200 text-blue-800'
                                                            }`}>
                                                            {version.change_type}
                                                        </span>
                                                        <span className={`ml-2 px-2 py-0.5 rounded text-xs font-semibold ${version.status === 'ACTIVE' ? 'bg-green-600 text-white' :
                                                            version.status === 'APPROVED' ? 'bg-green-200 text-green-800' :
                                                                version.status === 'IN_VALIDATION' ? 'bg-blue-200 text-blue-800' :
                                                                    'bg-gray-200 text-gray-800'
                                                            }`}>
                                                            {version.status}
                                                        </span>
                                                    </div>
                                                    {version.production_date && (
                                                        <div className="text-sm text-gray-600">
                                                            Production: {version.production_date.split('T')[0]}
                                                        </div>
                                                    )}
                                                </div>
                                                <p className="text-sm text-gray-700 mb-1">{version.change_description}</p>
                                                <div className="flex justify-between items-center">
                                                    <div className="text-xs text-gray-500">
                                                        Created by {version.created_by_name} on {version.created_at.split('T')[0]}
                                                    </div>
                                                    {(version.status === 'APPROVED' || version.status === 'ACTIVE') && primaryModel && (
                                                        <Link
                                                            to={`/models/${primaryModel.model_id}/versions/${version.version_id}`}
                                                            className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-purple-700 bg-purple-100 rounded-full hover:bg-purple-200 transition-colors"
                                                        >
                                                            <span>🚀</span> Deploy
                                                        </Link>
                                                    )}
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
                            <div className="flex items-start justify-between">
                                {['Intake', 'Planning', 'In Progress', 'Review', 'Pending Approval', 'Approved'].map((status, index) => {
                                    const stageStatus = getStageStatus(status);
                                    const isCompleted = stageStatus.completed;
                                    const isCurrent = stageStatus.current;
                                    const isOverdue = stageStatus.isOverdue;

                                    return (
                                        <div key={status} className="flex items-center">
                                            <div className={`flex flex-col items-center ${index > 0 ? 'ml-4' : ''}`}>
                                                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold ${
                                                    isOverdue
                                                        ? 'bg-red-600 text-white ring-2 ring-red-300'
                                                        : isCurrent
                                                            ? 'bg-blue-600 text-white'
                                                            : isCompleted
                                                                ? 'bg-green-600 text-white'
                                                                : 'bg-gray-200 text-gray-500'
                                                    }`}>
                                                    {isCompleted && !isCurrent ? '✓' : index + 1}
                                                </div>
                                                <span className={`mt-2 text-xs text-center max-w-[90px] ${
                                                    isCurrent ? 'font-bold text-blue-600' : 'text-gray-500'
                                                }`}>
                                                    {status}
                                                </span>

                                                {/* SLA Timing Information */}
                                                {isCurrent && (
                                                    <div className="mt-2 text-center">
                                                        <div className={`text-xs font-medium ${isOverdue ? 'text-red-600' : 'text-blue-600'}`}>
                                                            {stageStatus.daysInStage} {stageStatus.daysInStage === 1 ? 'day' : 'days'} in stage
                                                        </div>
                                                        {stageStatus.slaDays !== null && (
                                                            <div className="text-xs text-gray-500 mt-0.5">
                                                                SLA: {stageStatus.slaDays} {stageStatus.slaDays === 1 ? 'day' : 'days'}
                                                            </div>
                                                        )}
                                                        {stageStatus.daysRemaining !== null && (
                                                            <div className={`text-xs font-semibold mt-0.5 ${
                                                                isOverdue ? 'text-red-600' : 'text-green-600'
                                                            }`}>
                                                                {isOverdue
                                                                    ? `${Math.abs(stageStatus.daysRemaining!)} ${Math.abs(stageStatus.daysRemaining!) === 1 ? 'day' : 'days'} overdue`
                                                                    : `${stageStatus.daysRemaining} ${stageStatus.daysRemaining === 1 ? 'day' : 'days'} remaining`
                                                                }
                                                            </div>
                                                        )}
                                                    </div>
                                                )}

                                                {/* Show SLA target for non-current stages if SLA is configured */}
                                                {!isCurrent && stageStatus.slaDays !== null && (
                                                    <div className="mt-2 text-center">
                                                        <div className="text-xs text-gray-400">
                                                            Target: {stageStatus.slaDays}d
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                            {index < 5 && (
                                                <div className={`w-12 h-1 ml-4 mt-5 ${
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

                {activeTab === 'plan' && request && (
                    <ValidationPlanForm
                        ref={validationPlanRef}
                        requestId={request.request_id}
                        modelId={primaryModel?.model_id}
                        modelName={primaryModel?.model_name}
                        riskTier={primaryModel?.model_id ? 'Loading...' : undefined}
                        onSave={fetchData}
                        canEdit={canEditRequest}
                        validationTypeCode={request.validation_type?.code}
                    />
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
                                            <span className={`px-2 py-1 text-xs rounded ${assignment.independence_attestation
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
                                        <span className={`px-3 py-1 text-sm rounded ${request.outcome.overall_rating.label.includes('Fit')
                                            ? request.outcome.overall_rating.label === 'Fit for Use'
                                                ? 'bg-green-100 text-green-800'
                                                : 'bg-orange-100 text-orange-800'
                                            : 'bg-red-100 text-red-800'
                                            }`}>
                                            {request.outcome.overall_rating.label}
                                        </span>
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
                                        <label className="block text-sm font-medium mb-2">Effective Date *</label>
                                        <input
                                            type="date"
                                            className="input-field"
                                            value={newOutcome.effective_date}
                                            onChange={(e) => setNewOutcome({ ...newOutcome, effective_date: e.target.value })}
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-2">
                                            Expiration Date {request?.validation_type?.code === 'INTERIM' ? '*' : '(Optional)'}
                                        </label>
                                        <input
                                            type="date"
                                            className="input-field"
                                            value={newOutcome.expiration_date}
                                            onChange={(e) => setNewOutcome({ ...newOutcome, expiration_date: e.target.value })}
                                            required={request?.validation_type?.code === 'INTERIM'}
                                        />
                                        {request?.validation_type?.code === 'INTERIM' && (
                                            <p className="mt-1 text-xs text-amber-600">
                                                Required for INTERIM validations. Interim approvals are time-limited.
                                            </p>
                                        )}
                                    </div>
                                </div>
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Executive Summary *</label>
                                    <textarea
                                        className="input-field"
                                        rows={6}
                                        value={newOutcome.executive_summary}
                                        onChange={(e) => setNewOutcome({ ...newOutcome, executive_summary: e.target.value })}
                                        placeholder="Provide a comprehensive summary of the validation findings and conclusions, including rationale for overall rating..."
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

                        {/* Recommendations Section */}
                        <div className="mt-8 pt-6 border-t">
                            <div className="flex justify-between items-center mb-4">
                                <div>
                                    <h3 className="text-lg font-bold">Recommendations</h3>
                                    <p className="text-sm text-gray-600">
                                        Track and manage remediation actions from this validation's findings.
                                    </p>
                                </div>
                                {canManageRecommendationsFlag && (
                                    <button
                                        onClick={() => setShowRecommendationModal(true)}
                                        className="bg-orange-600 text-white px-4 py-2 rounded text-sm hover:bg-orange-700"
                                    >
                                        + Create Recommendation
                                    </button>
                                )}
                            </div>

                            {recommendations.length === 0 ? (
                                <div className="text-gray-500 text-center py-8 bg-gray-50 rounded-lg">
                                    No recommendations have been created for this validation yet.
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
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
                                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {recommendations.map((rec) => (
                                                <tr key={rec.recommendation_id} className="hover:bg-gray-50">
                                                    <td className="px-4 py-3 text-sm font-mono text-gray-900">
                                                        {rec.recommendation_code}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate" title={rec.title}>
                                                        {rec.title}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-gray-600">
                                                        {rec.model?.model_name || '-'}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm">
                                                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                                                            rec.priority?.code === 'HIGH' ? 'bg-red-100 text-red-800' :
                                                            rec.priority?.code === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                                                            'bg-green-100 text-green-800'
                                                        }`}>
                                                            {rec.priority?.label || '-'}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-sm">
                                                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                                                            rec.current_status?.code === 'CLOSED' ? 'bg-green-100 text-green-800' :
                                                            rec.current_status?.code === 'DRAFT' ? 'bg-gray-100 text-gray-800' :
                                                            'bg-blue-100 text-blue-800'
                                                        }`}>
                                                            {rec.current_status?.label || '-'}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-gray-600">
                                                        {rec.assigned_to?.full_name || '-'}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm text-gray-600">
                                                        {rec.current_target_date}
                                                    </td>
                                                    <td className="px-4 py-3 text-sm">
                                                        <Link
                                                            to={`/recommendations/${rec.recommendation_id}`}
                                                            className="text-blue-600 hover:text-blue-800 text-sm"
                                                        >
                                                            View →
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {activeTab === 'scorecard' && (
                    <div>
                        <h3 className="text-lg font-bold mb-4">Validation Scorecard</h3>
                        <ValidationScorecardTab
                            requestId={request.request_id}
                            canEdit={
                                canManageValidationsFlag &&
                                !['APPROVED', 'CANCELLED'].includes(request.current_status.code)
                            }
                            onScorecardChange={fetchData}
                        />
                    </div>
                )}

                {activeTab === 'limitations' && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold">Limitations Documented</h3>
                            <span className="text-sm text-gray-500">
                                Limitations linked to this validation request
                            </span>
                        </div>

                        {limitations.length === 0 ? (
                            <div className="text-gray-500 text-center py-8 bg-gray-50 rounded-lg">
                                <svg className="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <p>No limitations have been documented for this validation.</p>
                                <p className="text-xs mt-2">
                                    Limitations can be added from the model's Limitations tab and linked to this validation.
                                </p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Significance</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Conclusion</th>
                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {limitations.map((lim) => (
                                            <tr key={lim.limitation_id} className="hover:bg-gray-50">
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                                    #{lim.limitation_id}
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                                                        lim.significance === 'Critical'
                                                            ? 'bg-red-100 text-red-800'
                                                            : 'bg-blue-100 text-blue-800'
                                                    }`}>
                                                        {lim.significance}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                                    {lim.category?.label || '-'}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-gray-900 max-w-xs">
                                                    <div className="truncate" title={lim.description}>
                                                        {lim.description.length > 80
                                                            ? `${lim.description.slice(0, 80)}...`
                                                            : lim.description}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                                                        lim.conclusion === 'Mitigate'
                                                            ? 'bg-yellow-100 text-yellow-800'
                                                            : 'bg-green-100 text-green-800'
                                                    }`}>
                                                        {lim.conclusion}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 whitespace-nowrap">
                                                    {lim.is_retired ? (
                                                        <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-600">
                                                            Retired
                                                        </span>
                                                    ) : (
                                                        <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                                                            Active
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {/* Link to model's limitations tab for full management */}
                        {request.models && request.models.length > 0 && (
                            <div className="mt-4 pt-4 border-t border-gray-200">
                                <p className="text-sm text-gray-600">
                                    To add, edit, or retire limitations, go to the model's Limitations tab:
                                </p>
                                <div className="mt-2 flex flex-wrap gap-2">
                                    {request.models.map((m) => (
                                        <Link
                                            key={m.model_id}
                                            to={`/models/${m.model_id}`}
                                            className="text-blue-600 hover:text-blue-800 text-sm hover:underline"
                                        >
                                            {m.model_name} →
                                        </Link>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'approvals' && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold">Approval Status</h3>
                            <button
                                onClick={handleDownloadEffectiveChallengeReport}
                                disabled={actionLoading}
                                className="bg-gray-600 text-white px-3 py-1.5 text-sm rounded hover:bg-gray-700 disabled:opacity-50"
                                title="Download PDF report documenting effective challenge (send-backs and responses)"
                            >
                                {actionLoading ? 'Downloading...' : '📄 Export Challenge Report'}
                            </button>
                        </div>

                        {/* Info box explaining how regional approvals are determined */}
                        {request.approvals.filter(a => a.approver_role !== 'Conditional' && a.approver_role !== 'Global' && !a.voided_at).length > 0 && (
                            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm">
                                <strong>Regional Approvals:</strong> Based on {
                                    request.regions && request.regions.length > 0
                                        ? "validation scope (explicitly selected regions)"
                                        : relatedVersions.some(v => v.scope === 'REGIONAL')
                                            ? relatedVersions.every(v => v.scope === 'REGIONAL')
                                                ? "linked version's regional scope"
                                                : "model deployment regions (global version present)"
                                            : "model deployment regions"
                                }
                            </div>
                        )}

                        {/* Filter out Conditional approvals - they're shown in the ConditionalApprovalsSection below */}
                        {request.approvals.filter(a => a.approver_role !== 'Conditional' && !a.voided_at).length === 0 ? (
                            <div className="text-gray-500 text-center py-8">
                                {request.approvals.filter(a => a.approver_role !== 'Conditional' && a.voided_at).length > 0
                                    ? 'All approvals have been voided. New approvals will be created when status returns to Pending Approval.'
                                    : 'No approvals configured for this project.'}
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {/* Active (non-voided) Global/Regional approvals */}
                                {request.approvals
                                    .filter(a => a.approver_role !== 'Conditional' && !a.voided_at)
                                    .map((approval) => (
                                    <div key={approval.approval_id} className="border rounded-lg p-4">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                {approval.approver ? (
                                                    <>
                                                        <p className="font-medium">{approval.approver.full_name}</p>
                                                        <p className="text-sm text-gray-500">{approval.approver.email}</p>
                                                    </>
                                                ) : (
                                                    <p className="font-medium text-orange-600">Pending Assignment</p>
                                                )}
                                                <p className="text-xs text-gray-400">
                                                    Role: {approval.approver_role}
                                                    {approval.is_required && ' (Required)'}
                                                </p>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className={`px-2 py-1 text-xs rounded ${getApprovalStatusColor(approval.approval_status)}`}>
                                                    {approval.approval_status}
                                                </span>
                                                {approval.approval_status === 'Pending' && approval.approver &&
                                                    (user?.user_id === approval.approver.user_id || canProxyApproveFlag) && (
                                                        <button
                                                            onClick={() => {
                                                                const isProxyApproval = canProxyApproveFlag && user?.user_id !== approval.approver.user_id;
                                                                setApprovalUpdate({
                                                                    approval_id: approval.approval_id,
                                                                    status: '',
                                                                    comments: '',
                                                                    isProxyApproval,
                                                                    certificationEvidence: '',
                                                                    proxyCertified: false
                                                                });
                                                                setShowApprovalModal(true);
                                                            }}
                                                            disabled={request?.current_status?.code !== 'PENDING_APPROVAL'}
                                                            className={`text-xs ${
                                                                request?.current_status?.code !== 'PENDING_APPROVAL'
                                                                    ? 'btn-secondary opacity-50 cursor-not-allowed'
                                                                    : 'btn-primary'
                                                            }`}
                                                            title={request?.current_status?.code !== 'PENDING_APPROVAL'
                                                                ? `Cannot submit approval until request reaches 'Pending Approval' status (currently: ${request?.current_status?.label || 'Unknown'})`
                                                                : undefined}
                                                        >
                                                            {canProxyApproveFlag && user?.user_id !== approval.approver.user_id ? 'Decision on Behalf' : 'Decision'}
                                                        </button>
                                                    )}
                                                {(approval.approval_status === 'Approved' || approval.approval_status === 'Rejected') && approval.approver &&
                                                    (user?.user_id === approval.approver.user_id || canProxyApproveFlag) && (
                                                        <button
                                                            onClick={async () => {
                                                                if (window.confirm('Are you sure you want to withdraw this approval? This will reset it to Pending status.')) {
                                                                    try {
                                                                        await api.patch(`/validation-workflow/approvals/${approval.approval_id}`, {
                                                                            approval_status: 'Pending',
                                                                            comments: approval.comments
                                                                        });
                                                                        fetchData();
                                                                    } catch (err: any) {
                                                                        alert(err.response?.data?.detail || 'Failed to withdraw approval');
                                                                    }
                                                                }
                                                            }}
                                                            className="text-xs px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
                                                        >
                                                            Withdraw
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
                                        {approval.comments && (() => {
                                            const proxyMatch = approval.comments.match(/\[PROXY APPROVAL - Authorization Evidence: (.+?)\]/);
                                            const regularComments = approval.comments.replace(/\[PROXY APPROVAL - Authorization Evidence: .+?\]/g, '').trim();

                                            return (
                                                <>
                                                    {proxyMatch && (
                                                        <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                                                            <div className="text-xs font-medium text-yellow-800 flex items-center gap-1">
                                                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                                                </svg>
                                                                Proxy Approval (Submitted by Admin on behalf)
                                                            </div>
                                                            <div className="text-xs text-yellow-700 mt-1">
                                                                Authorization Evidence: {proxyMatch[1]}
                                                            </div>
                                                        </div>
                                                    )}
                                                    {regularComments && (
                                                        <div className="mt-2 text-sm">
                                                            <span className="text-gray-500">Comments:</span>{' '}
                                                            <span className="text-gray-700">{regularComments}</span>
                                                        </div>
                                                    )}
                                                </>
                                            );
                                        })()}
                                    </div>
                                ))}

                                {/* Voided approvals (historical, shown collapsed) */}
                                {request.approvals.filter(a => a.approver_role !== 'Conditional' && a.voided_at).length > 0 && (
                                    <details className="mt-4 border border-gray-200 rounded-lg">
                                        <summary className="px-4 py-2 bg-gray-50 cursor-pointer text-sm text-gray-600 hover:bg-gray-100 rounded-t-lg">
                                            <span className="ml-1">
                                                Voided Approvals ({request.approvals.filter(a => a.approver_role !== 'Conditional' && a.voided_at).length})
                                            </span>
                                        </summary>
                                        <div className="p-4 space-y-3">
                                            {request.approvals
                                                .filter(a => a.approver_role !== 'Conditional' && a.voided_at)
                                                .map((approval) => (
                                                <div key={approval.approval_id} className="border border-gray-200 rounded-lg p-3 bg-gray-50 opacity-60">
                                                    <div className="flex justify-between items-start">
                                                        <div>
                                                            <p className="font-medium text-gray-500 line-through">
                                                                {approval.approver?.full_name || 'Unknown Approver'}
                                                            </p>
                                                            <p className="text-xs text-gray-400">
                                                                Role: {approval.approver_role}
                                                            </p>
                                                        </div>
                                                        <span className="px-2 py-1 text-xs rounded bg-gray-200 text-gray-600">
                                                            Voided
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-gray-400 mt-2">
                                                        {approval.void_reason || 'No reason provided'}
                                                    </p>
                                                    <p className="text-xs text-gray-400">
                                                        Voided on: {approval.voided_at ? new Date(approval.voided_at).toLocaleDateString() : 'Unknown'}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    </details>
                                )}
                            </div>
                        )}

                        {/* Conditional Model Use Approvals Section */}
                        {user && (
                            <ConditionalApprovalsSection
                                requestId={request.request_id}
                                currentUser={user}
                                onUpdate={fetchData}
                            />
                        )}
                    </div>
                )}

                {activeTab === 'history' && (
                    <div>
                        <h3 className="text-lg font-bold mb-4">Activity History</h3>
                        {request.status_history.length === 0 && assignmentAuditLogs.length === 0 && approvalAuditLogs.length === 0 && commentaryAuditLogs.length === 0 ? (
                            <div className="text-gray-500 text-center py-8">
                                No activity recorded.
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {/* Merge and sort status history, assignment audit logs, approval audit logs, and commentary audit logs */}
                                {[
                                    ...request.status_history.map((h) => ({
                                        type: 'status' as const,
                                        timestamp: h.changed_at,
                                        data: h
                                    })),
                                    ...assignmentAuditLogs.map((a) => ({
                                        type: 'assignment' as const,
                                        timestamp: a.timestamp,
                                        data: a
                                    })),
                                    ...approvalAuditLogs.map((a) => ({
                                        type: 'approval' as const,
                                        timestamp: a.timestamp,
                                        data: a
                                    })),
                                    ...commentaryAuditLogs.map((a) => ({
                                        type: 'commentary' as const,
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
                                        } else if (item.type === 'assignment') {
                                            const audit = item.data as AuditLog;
                                            const actionColors = {
                                                'CREATE': 'border-green-500',
                                                'UPDATE': 'border-orange-500',
                                                'DELETE': 'border-red-500',
                                                'REVIEWER_SIGN_OFF': 'border-purple-500'
                                            };
                                            const actionLabels = {
                                                'CREATE': 'VALIDATOR ASSIGNED',
                                                'UPDATE': 'ASSIGNMENT UPDATED',
                                                'DELETE': 'VALIDATOR REMOVED',
                                                'REVIEWER_SIGN_OFF': 'REVIEWER SIGN-OFF'
                                            };
                                            return (
                                                <div key={`audit-${audit.log_id}`} className={`border-l-4 ${actionColors[audit.action as keyof typeof actionColors] || 'border-gray-500'} pl-4 py-2`}>
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-xs font-semibold text-gray-700">
                                                            {actionLabels[audit.action as keyof typeof actionLabels] || audit.action}
                                                        </span>
                                                    </div>
                                                    <div className="mt-2 text-sm">
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
                                        } else if (item.type === 'approval') {
                                            const audit = item.data as AuditLog;
                                            const actionColors = {
                                                'APPROVAL_SUBMITTED': 'border-green-500',
                                                'APPROVAL_WITHDRAWN': 'border-orange-500'
                                            };
                                            const actionLabels = {
                                                'APPROVAL_SUBMITTED': 'APPROVAL SUBMITTED',
                                                'APPROVAL_WITHDRAWN': 'APPROVAL WITHDRAWN'
                                            };
                                            const isProxyApproval = audit.changes?.proxy_approval === true;
                                            return (
                                                <div key={`audit-${audit.log_id}`} className={`border-l-4 ${actionColors[audit.action as keyof typeof actionColors] || 'border-purple-500'} pl-4 py-2`}>
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-xs font-semibold text-gray-700">
                                                            {actionLabels[audit.action as keyof typeof actionLabels] || audit.action}
                                                        </span>
                                                        {isProxyApproval && (
                                                            <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded">
                                                                Proxy Approval
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="mt-2 text-sm">
                                                        {audit.changes?.approver_role && (
                                                            <div>
                                                                <span className="text-gray-500">Approver Role:</span>{' '}
                                                                <span className="font-medium">{audit.changes.approver_role}</span>
                                                            </div>
                                                        )}
                                                        {audit.changes?.status && (
                                                            <div>
                                                                <span className="text-gray-500">Status:</span>{' '}
                                                                <span className={`px-2 py-1 text-xs rounded ${
                                                                    audit.changes.status === 'Approved' ? 'bg-green-100 text-green-800' :
                                                                    audit.changes.status === 'Rejected' ? 'bg-red-100 text-red-800' :
                                                                    'bg-gray-100 text-gray-800'
                                                                }`}>
                                                                    {audit.changes.status}
                                                                </span>
                                                            </div>
                                                        )}
                                                        {isProxyApproval && (
                                                            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                                                                <div className="text-xs text-yellow-800">
                                                                    <div><strong>Approved by:</strong> {audit.changes.approved_by_admin}</div>
                                                                    <div><strong>On behalf of:</strong> {audit.changes.on_behalf_of}</div>
                                                                </div>
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
                                        } else if (item.type === 'commentary') {
                                            const audit = item.data as AuditLog;
                                            const isUpdate = audit.action === 'overdue_commentary_updated';
                                            const overdueTypeLabel = audit.changes?.overdue_type === 'PRE_SUBMISSION'
                                                ? 'Pre-Submission'
                                                : 'Validation In Progress';
                                            return (
                                                <div key={`commentary-${audit.log_id}`} className="border-l-4 border-amber-500 pl-4 py-2">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-xs font-semibold text-amber-700">
                                                            {isUpdate ? 'OVERDUE COMMENTARY UPDATED' : 'OVERDUE COMMENTARY ADDED'}
                                                        </span>
                                                        <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-800 rounded">
                                                            {overdueTypeLabel}
                                                        </span>
                                                    </div>
                                                    <div className="mt-2 text-sm">
                                                        {audit.changes?.target_date && (
                                                            <div>
                                                                <span className="text-gray-500">Target Date:</span>{' '}
                                                                <span className="font-medium">{audit.changes.target_date}</span>
                                                            </div>
                                                        )}
                                                        {audit.changes?.reason_comment && (
                                                            <div className="mt-1">
                                                                <span className="text-gray-500">Reason:</span>{' '}
                                                                <span className="text-gray-700">{audit.changes.reason_comment}</span>
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
                                        return null;
                                    })}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Put on Hold Modal */}
            {showHoldModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md border-t-4 border-amber-500">
                        <div className="flex items-center gap-3 mb-4">
                            <svg className="h-6 w-6 text-amber-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25v13.5m-7.5-13.5v13.5" />
                            </svg>
                            <h3 className="text-lg font-bold text-amber-800">Put Validation on Hold</h3>
                        </div>
                        <div className="bg-amber-50 border border-amber-200 rounded p-3 mb-4">
                            <p className="text-sm text-amber-800">
                                <strong>What happens when on hold:</strong>
                            </p>
                            <ul className="text-sm text-amber-700 mt-2 ml-4 list-disc">
                                <li>Model version status reverts to DRAFT</li>
                                <li>Team SLA clock is paused (hold time excluded from calculations)</li>
                                <li>Compliance deadline remains unchanged</li>
                            </ul>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">
                                Hold Reason <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                className="input-field"
                                rows={4}
                                value={holdReason}
                                onChange={(e) => setHoldReason(e.target.value)}
                                placeholder="Explain why this validation is being put on hold (minimum 10 characters)..."
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                {holdReason.length}/10 characters minimum
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handlePutOnHold}
                                disabled={actionLoading || holdReason.trim().length < 10}
                                className="bg-amber-600 text-white px-4 py-2 rounded hover:bg-amber-700 disabled:opacity-50"
                            >
                                {actionLoading ? 'Processing...' : 'Put on Hold'}
                            </button>
                            <button
                                onClick={() => { setShowHoldModal(false); setHoldReason(''); }}
                                className="btn-secondary"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Cancel Request Modal */}
            {showCancelModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md border-t-4 border-red-500">
                        <div className="flex items-center gap-3 mb-4">
                            <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            <h3 className="text-lg font-bold text-red-800">Cancel Validation Request</h3>
                        </div>
                        <div className="bg-red-50 border border-red-200 rounded p-3 mb-4">
                            <p className="text-sm text-red-800 font-medium">
                                Warning: This action cannot be undone
                            </p>
                            <p className="text-sm text-red-700 mt-1">
                                Cancelling will terminate this validation request permanently.
                                Model version status will revert to DRAFT.
                            </p>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">
                                Cancellation Reason <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                className="input-field"
                                rows={4}
                                value={cancelReason}
                                onChange={(e) => setCancelReason(e.target.value)}
                                placeholder="Explain why this validation is being cancelled (minimum 10 characters)..."
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                {cancelReason.length}/10 characters minimum
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleCancelRequest}
                                disabled={actionLoading || cancelReason.trim().length < 10}
                                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50"
                            >
                                {actionLoading ? 'Processing...' : 'Cancel Request'}
                            </button>
                            <button
                                onClick={() => { setShowCancelModal(false); setCancelReason(''); }}
                                className="btn-secondary"
                            >
                                Go Back
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Send Back to In Progress Modal */}
            {showSendBackModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md border-t-4 border-orange-500">
                        <div className="flex items-center gap-3 mb-4">
                            <svg className="h-6 w-6 text-orange-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h13.5m0 0L11.25 6.75M16.5 12l-5.25 5.25" />
                            </svg>
                            <h3 className="text-lg font-bold text-orange-800">Send Back to In Progress</h3>
                        </div>
                        <div className="bg-orange-50 border border-orange-200 rounded p-3 mb-4">
                            <p className="text-sm text-orange-800">
                                <strong>This returns the validation to In Progress for major rework.</strong>
                            </p>
                            <ul className="text-sm text-orange-700 mt-2 ml-4 list-disc">
                                <li>Global/Regional approvals will be reset</li>
                                <li>Conditional approvals will be voided</li>
                            </ul>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">
                                Reason <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                className="input-field"
                                rows={4}
                                value={sendBackReason}
                                onChange={(e) => setSendBackReason(e.target.value)}
                                placeholder="Explain why this requires major rework..."
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                {sendBackReason.trim().length} characters
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={confirmSendBackToInProgress}
                                disabled={actionLoading || sendBackReason.trim().length < 1}
                                className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 disabled:opacity-50"
                            >
                                {actionLoading ? 'Sending...' : 'Send Back'}
                            </button>
                            <button
                                onClick={() => { setShowSendBackModal(false); setSendBackReason(''); }}
                                className="btn-secondary"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Resume from Hold Modal */}
            {showResumeModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md border-t-4 border-green-500">
                        <div className="flex items-center gap-3 mb-4">
                            <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                            </svg>
                            <h3 className="text-lg font-bold text-green-800">Resume Validation Work</h3>
                        </div>
                        <div className="bg-green-50 border border-green-200 rounded p-3 mb-4">
                            <p className="text-sm text-green-800">
                                <strong>Hold Summary:</strong>
                            </p>
                            <ul className="text-sm text-green-700 mt-2">
                                <li>On hold for: <strong>{request.total_hold_days}</strong> days</li>
                                <li>Will resume to: <strong>{request.previous_status_before_hold || 'Previous status'}</strong></li>
                            </ul>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Resume Notes (Optional)</label>
                            <textarea
                                className="input-field"
                                rows={3}
                                value={resumeNotes}
                                onChange={(e) => setResumeNotes(e.target.value)}
                                placeholder="Add any notes about resuming work..."
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleResumeFromHold}
                                disabled={actionLoading}
                                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                            >
                                {actionLoading ? 'Processing...' : 'Resume Work'}
                            </button>
                            <button
                                onClick={() => { setShowResumeModal(false); setResumeNotes(''); }}
                                className="btn-secondary"
                            >
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
                                {users.filter((u) => {
                                    const roleCode = getUserRoleCode(u);
                                    return roleCode === 'VALIDATOR' || roleCode === 'ADMIN';
                                }).map((u) => (
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
                        <h3 className="text-lg font-bold mb-4">
                            {approvalUpdate.isProxyApproval ? 'Proxy Decision (On Behalf)' : 'Submit Decision'}
                        </h3>

                        {approvalUpdate.isProxyApproval && request && (
                            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                                <p className="text-sm font-medium text-yellow-800">
                                    You are submitting a decision on behalf of: {request.approvals.find(a => a.approval_id === approvalUpdate.approval_id)?.approver?.full_name || 'Unassigned Approver'}
                                </p>
                                <p className="text-xs text-yellow-700 mt-1">
                                    Certification required: You must attest that you have obtained proper authorization.
                                </p>
                            </div>
                        )}

                        {approvalValidationError && (
                            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
                                <p className="text-sm text-red-800">{approvalValidationError}</p>
                            </div>
                        )}

                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Decision</label>
                            <select
                                className="input-field"
                                value={approvalUpdate.status}
                                onChange={(e) => {
                                    setApprovalUpdate({ ...approvalUpdate, status: e.target.value });
                                    setApprovalValidationError(null);
                                }}
                            >
                                <option value="">Select Decision</option>
                                <option value="Approved">Approve</option>
                                {/* Only Global and Regional approvers can send back for revision */}
                                {request && (() => {
                                    const currentApproval = request.approvals.find(a => a.approval_id === approvalUpdate.approval_id);
                                    if (!currentApproval) return false;
                                    // Check approval_type first, fallback to approver_role for compatibility
                                    const isGlobalOrRegional =
                                        currentApproval.approval_type === 'Global' ||
                                        currentApproval.approval_type === 'Regional' ||
                                        currentApproval.approver_role?.includes('Global') ||
                                        currentApproval.approver_role?.includes('Regional');
                                    return isGlobalOrRegional;
                                })() && (
                                    <option value="Sent Back">Send Back for Revision</option>
                                )}
                            </select>
                            {approvalUpdate.status === 'Sent Back' && (
                                <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded">
                                    <p className="text-sm text-amber-800">
                                        <strong>Send Back:</strong> This will return the validation to the team for revisions.
                                    </p>
                                    <p className="text-xs text-amber-700 mt-1">
                                        Comments are required to explain what needs to be addressed.
                                    </p>
                                </div>
                            )}
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

                        {/* Authorization Evidence only required for proxy Approve/Reject, not Send Back */}
                        {approvalUpdate.isProxyApproval && approvalUpdate.status !== 'Sent Back' && (
                            <>
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">
                                        Authorization Evidence <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        className="input-field"
                                        value={approvalUpdate.certificationEvidence}
                                        onChange={(e) => {
                                            setApprovalUpdate({ ...approvalUpdate, certificationEvidence: e.target.value });
                                            setApprovalValidationError(null);
                                        }}
                                        placeholder="e.g., Email dated 2025-11-20, Ticket #12345, Meeting notes..."
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        Provide reference to documentation that evidences proper authorization
                                    </p>
                                </div>
                                <div className="mb-4">
                                    <label className="flex items-start gap-2">
                                        <input
                                            type="checkbox"
                                            className="mt-1"
                                            checked={approvalUpdate.proxyCertified}
                                            onChange={(e) => {
                                                setApprovalUpdate({ ...approvalUpdate, proxyCertified: e.target.checked });
                                                setApprovalValidationError(null);
                                            }}
                                        />
                                        <span className="text-sm font-medium">
                                            I certify that I have obtained and evidenced proper authorization from the designated approver to submit this approval on their behalf. <span className="text-red-500">*</span>
                                        </span>
                                    </label>
                                </div>
                            </>
                        )}

                        <div className="flex gap-2">
                            <button
                                onClick={handleApprovalUpdate}
                                disabled={actionLoading}
                                className="btn-primary"
                            >
                                {actionLoading ? 'Submitting...' : 'Submit'}
                            </button>
                            <button
                                onClick={() => {
                                    setShowApprovalModal(false);
                                    setApprovalValidationError(null);
                                }}
                                className="btn-secondary"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Resubmit for Approval Modal */}
            {showResubmitModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-lg">
                        <h3 className="text-lg font-bold mb-4">Resubmit for Approval</h3>

                        {/* Show the original feedback */}
                        {(() => {
                            const feedback = getSendBackFeedback();
                            return feedback ? (
                                <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded">
                                    <p className="text-xs font-medium text-amber-800 mb-1">
                                        Feedback from {feedback.approverRole}:
                                    </p>
                                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{feedback.comments}</p>
                                </div>
                            ) : null;
                        })()}

                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">
                                Your Response <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                className="input-field"
                                rows={4}
                                value={resubmitResponse}
                                onChange={(e) => setResubmitResponse(e.target.value)}
                                placeholder="Describe the changes made to address the feedback..."
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Explain how you've addressed the approver's concerns.
                            </p>
                        </div>

                        <div className="flex gap-2">
                            <button
                                onClick={() => handleResubmitForApproval()}
                                disabled={actionLoading || !resubmitResponse.trim()}
                                className="btn-primary disabled:opacity-50"
                            >
                                {actionLoading ? 'Resubmitting...' : 'Resubmit for Approval'}
                            </button>
                            <button
                                onClick={() => {
                                    setShowResubmitModal(false);
                                    setResubmitResponse('');
                                }}
                                className="btn-secondary"
                            >
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

            {/* Mark Submission Received Modal */}
            {showSubmissionModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
                        <h3 className="text-lg font-bold mb-4">Mark Submission Received</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            Recording when the validation documentation was received will start the validation team's SLA timer
                            and automatically transition this project to "In Progress" status.
                        </p>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Date Submission Received *
                            </label>
                            <input
                                type="date"
                                value={submissionReceivedDate}
                                onChange={(e) => setSubmissionReceivedDate(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                required
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Confirm or adjust the date the submission was actually received
                            </p>
                        </div>

                        {/* Model Version Confirmation */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Model Version
                            </label>
                            <select
                                value={submissionConfirmedVersionId || ''}
                                onChange={(e) => setSubmissionConfirmedVersionId(e.target.value ? parseInt(e.target.value) : null)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="">-- No version selected --</option>
                                {availableVersions.map((v) => (
                                    <option key={v.version_id} value={v.version_id}>
                                        Version {v.version_number} - {v.change_type} ({v.status})
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-gray-500 mt-1">
                                Confirm or correct the model version being validated
                            </p>
                        </div>

                        {/* Optional submission metadata fields */}
                        <div className="border-t border-gray-200 pt-4 mt-4">
                            <p className="text-sm font-medium text-gray-700 mb-3">
                                Optional Submission Details
                            </p>

                            <div className="mb-3">
                                <label className="block text-sm font-medium text-gray-600 mb-1">
                                    Model Documentation Version
                                </label>
                                <input
                                    type="text"
                                    value={submissionDocVersion}
                                    onChange={(e) => setSubmissionDocVersion(e.target.value)}
                                    placeholder="e.g., v2.1.0"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>

                            <div className="mb-3">
                                <label className="block text-sm font-medium text-gray-600 mb-1">
                                    Model Submission Version
                                </label>
                                <input
                                    type="text"
                                    value={submissionModelVersion}
                                    onChange={(e) => setSubmissionModelVersion(e.target.value)}
                                    placeholder="e.g., 1.5.2"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>

                            <div className="mb-3">
                                <label className="block text-sm font-medium text-gray-600 mb-1">
                                    Model Documentation ID
                                </label>
                                <input
                                    type="text"
                                    value={submissionDocId}
                                    onChange={(e) => setSubmissionDocId(e.target.value)}
                                    placeholder="e.g., DOC-2025-001234"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    External reference ID (e.g., from document management system)
                                </p>
                            </div>
                        </div>

                        <div className="mb-4 mt-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Notes (Optional)
                            </label>
                            <textarea
                                value={submissionNotes}
                                onChange={(e) => setSubmissionNotes(e.target.value)}
                                placeholder="Add any notes about the submission..."
                                rows={3}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>

                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => {
                                    setShowSubmissionModal(false);
                                    setSubmissionNotes('');
                                    setSubmissionDocVersion('');
                                    setSubmissionModelVersion('');
                                    setSubmissionDocId('');
                                    setSubmissionConfirmedVersionId(null);
                                }}
                                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                                disabled={actionLoading}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleMarkSubmissionReceived}
                                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
                                disabled={actionLoading || !submissionReceivedDate}
                            >
                                {actionLoading ? 'Processing...' : 'Confirm Receipt'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {showManageModelsModal && request && (
                <ManageModelsModal
                    request={request}
                    isOpen={showManageModelsModal}
                    onClose={() => setShowManageModelsModal(false)}
                    onSave={handleModelsUpdated}
                />
            )}

            {/* Overdue Commentary Modal */}
            {showCommentaryModal && request && (
                <OverdueCommentaryModal
                    requestId={request.request_id}
                    overdueType={commentaryModalType}
                    modelName={primaryModel?.model_name}
                    currentComment={overdueCommentary?.current_comment}
                    onClose={() => setShowCommentaryModal(false)}
                    onSuccess={handleCommentarySuccess}
                />
            )}

            {/* Create Recommendation Modal */}
            {showRecommendationModal && request && (
                <RecommendationCreateModal
                    onClose={() => setShowRecommendationModal(false)}
                    onCreated={async () => {
                        setShowRecommendationModal(false);
                        // Refresh recommendations
                        if (request.models && request.models.length > 0) {
                            try {
                                const modelIds = request.models.map((m) => m.model_id);
                                const recPromises = modelIds.map((modelId) =>
                                    recommendationsApi.list({ model_id: modelId })
                                );
                                const recResults = await Promise.all(recPromises);
                                const allRecs = recResults.flat();
                                const uniqueRecs = allRecs.filter((rec, index, self) =>
                                    index === self.findIndex(r => r.recommendation_id === rec.recommendation_id)
                                );
                                setRecommendations(uniqueRecs);
                            } catch (err) {
                                console.error('Failed to refresh recommendations:', err);
                            }
                        }
                    }}
                    models={request.models.map(m => ({ model_id: m.model_id, model_name: m.model_name }))}
                    users={users.map(u => ({ user_id: u.user_id, email: u.email, full_name: u.full_name }))}
                    priorities={recPriorities}
                    categories={recCategories}
                    preselectedModelId={primaryModel?.model_id}
                    preselectedValidationRequestId={request.request_id}
                />
            )}

            {/* Assessment Warning Modal - shown when status transition would proceed despite outdated risk assessment */}
            {showAssessmentWarningModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <div className="flex items-center gap-3 mb-4">
                            <svg className="h-6 w-6 text-amber-500" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                            </svg>
                            <h3 className="text-lg font-bold text-amber-800">Risk Assessment Warning</h3>
                        </div>
                        <div className="bg-amber-50 border border-amber-200 rounded p-3 mb-4">
                            <p className="text-sm text-amber-800 font-medium mb-2">
                                The following issues were detected:
                            </p>
                            <ul className="list-disc list-inside text-sm text-amber-700 space-y-1">
                                {assessmentWarnings.map((warning, idx) => (
                                    <li key={idx}>{warning}</li>
                                ))}
                            </ul>
                        </div>
                        <p className="text-sm text-gray-600 mb-4">
                            Do you want to proceed with this status change despite the warning? The validation will continue, but consider updating the risk assessment afterward.
                        </p>
                        <div className="flex gap-2">
                            <button
                                onClick={handleConfirmAssessmentWarning}
                                disabled={actionLoading}
                                className="bg-amber-600 text-white px-4 py-2 rounded hover:bg-amber-700 disabled:opacity-50"
                            >
                                {actionLoading ? 'Processing...' : 'Proceed Anyway'}
                            </button>
                            <button
                                onClick={handleCancelAssessmentWarning}
                                className="btn-secondary"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Pre-Transition Warning Modal - shown when advancing to Pending Approval with open recommendations or pending attestations */}
            {showPreTransitionModal && preTransitionWarnings && (
                <PreTransitionWarningModal
                    warnings={preTransitionWarnings.warnings}
                    canProceed={preTransitionWarnings.can_proceed}
                    onClose={() => {
                        setShowPreTransitionModal(false);
                        setPendingTransitionAction(null);
                        setPendingResubmitResponse('');
                    }}
                    onProceed={async () => {
                        setShowPreTransitionModal(false);
                        // Handle different action types that can trigger pre-transition warnings
                        switch (pendingTransitionAction) {
                            case 'complete_work':
                                await handleCompleteWork(false, true); // Skip pre-transition warning on proceed
                                break;
                            case 'status_update':
                                await handleStatusUpdate(true, true); // Skip both warnings on proceed
                                break;
                            case 'resubmit':
                                // Restore the response and execute resubmit
                                setResubmitResponse(pendingResubmitResponse);
                                await handleResubmitForApproval(true); // Skip pre-transition warning on proceed
                                break;
                        }
                        setPendingTransitionAction(null);
                        setPendingResubmitResponse('');
                    }}
                    loading={actionLoading}
                />
            )}

            {/* Deploy Modal (Issue 5: Deploy Approved Version) */}
            {showDeployModal && deployVersion && (
                <DeployModal
                    versionId={deployVersion.version_id}
                    onClose={() => {
                        setShowDeployModal(false);
                        setDeployVersion(null);
                    }}
                    onSuccess={() => {
                        setShowDeployModal(false);
                        setDeployVersion(null);
                        fetchData();
                    }}
                />
            )}
        </Layout>
    );
}

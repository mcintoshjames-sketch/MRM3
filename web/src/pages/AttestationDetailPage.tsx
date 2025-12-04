import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

// Interfaces
interface AttestationQuestion {
    value_id: number;
    code: string;
    label: string;
    description: string;
    sort_order: number;
    is_active: boolean;
    frequency_scope: string;
    requires_comment_if_no: boolean;
}

interface AttestationResponse {
    response_id: number;
    question_id: number;
    answer: boolean;
    comment: string | null;
}

interface AttestationEvidence {
    evidence_id: number;
    evidence_type: string;
    url: string;
    description: string | null;
    added_by: { user_id: number; full_name: string };
    added_at: string;
}

interface ChangeProposal {
    proposal_id: number;
    attestation_id: number;
    change_type: 'UPDATE_EXISTING' | 'NEW_MODEL' | 'DECOMMISSION';
    model_id: number | null;
    proposed_data: Record<string, unknown> | null;
    status: 'PENDING' | 'ACCEPTED' | 'REJECTED';
    admin_comment: string | null;
    decided_by: { user_id: number; full_name: string } | null;
    decided_at: string | null;
    created_at: string;
    model: { model_id: number; model_name: string } | null;
}

interface ModelRef {
    model_id: number;
    model_name: string;
    risk_tier_code: string | null;
    risk_tier_label: string | null;
    owner_id: number | null;
    owner_name: string | null;
}

interface AttestationRecord {
    attestation_id: number;
    cycle_id: number;
    model: ModelRef;
    attesting_user: { user_id: number; email: string; full_name: string };
    due_date: string;
    status: 'PENDING' | 'SUBMITTED' | 'ACCEPTED' | 'REJECTED';
    attested_at: string | null;
    decision: string | null;
    decision_comment: string | null;
    reviewed_by: { user_id: number; full_name: string } | null;
    reviewed_at: string | null;
    review_comment: string | null;
    responses: AttestationResponse[];
    evidence: AttestationEvidence[];
    change_proposals: ChangeProposal[];
}

interface SimpleModel {
    model_id: number;
    model_name: string;
}

interface FormAnswer {
    answer: boolean;
    comment: string;
}

export default function AttestationDetailPage() {
    const { id } = useParams<{ id: string }>();
    const { user } = useAuth();

    const [attestation, setAttestation] = useState<AttestationRecord | null>(null);
    const [questions, setQuestions] = useState<AttestationQuestion[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Form state
    const [answers, setAnswers] = useState<Record<number, FormAnswer>>({});
    const [decisionComment, setDecisionComment] = useState('');

    // Admin review state (for SUBMITTED attestations)
    const [reviewComment, setReviewComment] = useState('');
    const [isReviewing, setIsReviewing] = useState(false);

    // Change proposal state
    const [showChangeModal, setShowChangeModal] = useState(false);
    const [changeType, setChangeType] = useState<'UPDATE_EXISTING' | 'NEW_MODEL' | 'DECOMMISSION'>('UPDATE_EXISTING');
    const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
    const [proposedData, setProposedData] = useState<Record<string, string>>({});
    const [availableModels, setAvailableModels] = useState<SimpleModel[]>([]);
    const [submittingChange, setSubmittingChange] = useState(false);

    // Prompt modal for I_ATTEST_WITH_UPDATES without change proposals
    const [showUpdatePrompt, setShowUpdatePrompt] = useState(false);

    useEffect(() => {
        fetchData();
    }, [id]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [attestationRes, questionsRes] = await Promise.all([
                api.get(`/attestations/records/${id}`),
                api.get('/attestations/questions')
            ]);

            setAttestation(attestationRes.data);
            setQuestions(questionsRes.data);

            // Initialize answers from existing responses
            const existingAnswers: Record<number, FormAnswer> = {};
            attestationRes.data.responses.forEach((r: AttestationResponse) => {
                existingAnswers[r.question_id] = {
                    answer: r.answer,
                    comment: r.comment || ''
                };
            });

            // Initialize empty answers for questions without responses
            questionsRes.data.forEach((q: AttestationQuestion) => {
                if (!existingAnswers[q.value_id]) {
                    existingAnswers[q.value_id] = { answer: true, comment: '' };
                }
            });

            setAnswers(existingAnswers);

            if (attestationRes.data.decision_comment) {
                setDecisionComment(attestationRes.data.decision_comment);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load attestation');
        } finally {
            setLoading(false);
        }
    };

    const handleAnswerChange = (questionId: number, value: boolean) => {
        setAnswers(prev => ({
            ...prev,
            [questionId]: { ...prev[questionId], answer: value }
        }));
    };

    const handleCommentChange = (questionId: number, comment: string) => {
        setAnswers(prev => ({
            ...prev,
            [questionId]: { ...prev[questionId], comment }
        }));
    };

    const validateSubmission = (): string | null => {
        for (const q of questions) {
            const answer = answers[q.value_id];
            if (!answer) {
                return `Please answer question: ${q.label}`;
            }
            if (!answer.answer && q.requires_comment_if_no && !answer.comment.trim()) {
                return `A comment is required when answering "No" to: ${q.label}`;
            }
        }
        return null;
    };

    const handleSubmit = async (bypassPrompt: boolean = false) => {
        const validationError = validateSubmission();
        if (validationError) {
            setError(validationError);
            return;
        }

        // Check if any answers are "No" and no change proposals exist
        const hasNoAnswers = questions.some(q => answers[q.value_id]?.answer === false);
        const hasChangeProposals = attestation?.change_proposals && attestation.change_proposals.length > 0;

        // Prompt user to add change proposals if they have "No" answers but haven't added any
        if (hasNoAnswers && !hasChangeProposals && !bypassPrompt) {
            setShowUpdatePrompt(true);
            return;
        }

        setShowUpdatePrompt(false);
        setSubmitting(true);
        setError(null);

        try {
            // Build responses array
            const responses = questions.map(q => ({
                question_id: q.value_id,
                answer: answers[q.value_id].answer,
                comment: answers[q.value_id].comment || null
            }));

            // Determine decision based on answers
            // Backend expects: I_ATTEST, I_ATTEST_WITH_UPDATES, or OTHER
            const allYes = responses.every(r => r.answer);
            const decision = allYes ? 'I_ATTEST' : 'I_ATTEST_WITH_UPDATES';

            await api.post(`/attestations/records/${id}/submit`, {
                responses,
                decision,
                decision_comment: decisionComment || null
            });

            setSuccess('Attestation submitted successfully');
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit attestation');
        } finally {
            setSubmitting(false);
        }
    };

    const handleAccept = async () => {
        setIsReviewing(true);
        try {
            await api.post(`/attestations/records/${id}/accept`, {
                review_comment: reviewComment || null
            });
            setSuccess('Attestation accepted');
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to accept attestation');
        } finally {
            setIsReviewing(false);
        }
    };

    const handleReject = async () => {
        if (!reviewComment.trim()) {
            setError('A comment is required when rejecting an attestation');
            return;
        }
        setIsReviewing(true);
        try {
            await api.post(`/attestations/records/${id}/reject`, {
                review_comment: reviewComment
            });
            setSuccess('Attestation rejected');
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to reject attestation');
        } finally {
            setIsReviewing(false);
        }
    };

    const fetchModels = async () => {
        try {
            const res = await api.get('/models/?limit=500');
            setAvailableModels(res.data.items || res.data);
        } catch (err) {
            console.error('Failed to fetch models', err);
        }
    };

    const openChangeModal = (type: 'UPDATE_EXISTING' | 'NEW_MODEL' | 'DECOMMISSION') => {
        setChangeType(type);
        setSelectedModelId(type === 'UPDATE_EXISTING' || type === 'DECOMMISSION' ? attestation?.model.model_id || null : null);
        setProposedData({});
        setShowChangeModal(true);
        if (type === 'UPDATE_EXISTING' || type === 'DECOMMISSION') {
            fetchModels();
        }
    };

    const handleSubmitChange = async () => {
        setSubmittingChange(true);
        setError(null);

        try {
            const payload: {
                change_type: string;
                model_id?: number | null;
                proposed_data?: Record<string, unknown>;
            } = {
                change_type: changeType
            };

            if (changeType === 'UPDATE_EXISTING') {
                if (!selectedModelId) {
                    setError('Please select a model to update');
                    setSubmittingChange(false);
                    return;
                }
                payload.model_id = selectedModelId;
                payload.proposed_data = proposedData;
            } else if (changeType === 'NEW_MODEL') {
                if (!proposedData.model_name) {
                    setError('Model name is required for new models');
                    setSubmittingChange(false);
                    return;
                }
                payload.proposed_data = proposedData;
            } else if (changeType === 'DECOMMISSION') {
                if (!selectedModelId) {
                    setError('Please select a model to decommission');
                    setSubmittingChange(false);
                    return;
                }
                payload.model_id = selectedModelId;
                payload.proposed_data = { reason: proposedData.reason || '' };
            }

            await api.post(`/attestations/records/${id}/changes`, payload);
            setSuccess('Change proposal submitted successfully');
            setShowChangeModal(false);
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit change proposal');
        } finally {
            setSubmittingChange(false);
        }
    };

    const handleAcceptProposal = async (proposalId: number) => {
        try {
            await api.post(`/attestations/changes/${proposalId}/accept`, {});
            setSuccess('Change proposal accepted');
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to accept proposal');
        }
    };

    const handleRejectProposal = async (proposalId: number) => {
        const comment = prompt('Please provide a reason for rejecting this proposal:');
        if (!comment) return;
        try {
            await api.post(`/attestations/changes/${proposalId}/reject`, { admin_comment: comment });
            setSuccess('Change proposal rejected');
            fetchData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to reject proposal');
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'SUBMITTED':
                return <span className="px-3 py-1 text-sm font-medium rounded-full bg-blue-100 text-blue-800">Submitted - Pending Review</span>;
            case 'ACCEPTED':
                return <span className="px-3 py-1 text-sm font-medium rounded-full bg-green-100 text-green-800">Accepted</span>;
            case 'REJECTED':
                return <span className="px-3 py-1 text-sm font-medium rounded-full bg-red-100 text-red-800">Rejected</span>;
            default:
                return <span className="px-3 py-1 text-sm font-medium rounded-full bg-yellow-100 text-yellow-800">Pending Submission</span>;
        }
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        return dateStr.split('T')[0];
    };

    const formatDateTime = (dateStr: string | null) => {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleString();
    };

    const canEdit = attestation?.status === 'PENDING' || attestation?.status === 'REJECTED';
    const canReview = (user?.role === 'Admin' || user?.role === 'Validator') && attestation?.status === 'SUBMITTED';
    // User is owner if they are the attesting user OR the model owner
    const isOwner = attestation?.attesting_user.user_id === user?.user_id ||
                    attestation?.model.owner_id === user?.user_id;

    if (loading) {
        return (
            <Layout>
                <div className="p-8 text-center text-gray-500">Loading...</div>
            </Layout>
        );
    }

    if (!attestation) {
        return (
            <Layout>
                <div className="p-8 text-center text-red-500">Attestation not found</div>
            </Layout>
        );
    }

    return (
        <Layout>
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center justify-between">
                    <div>
                        <div className="flex items-center gap-3">
                            <Link
                                to="/my-attestations"
                                className="text-gray-500 hover:text-gray-700"
                            >
                                &larr; Back
                            </Link>
                            <h1 className="text-2xl font-bold text-gray-900">
                                Attestation for {attestation.model.model_name}
                            </h1>
                        </div>
                        <p className="text-gray-600 mt-1">
                            Due: {formatDate(attestation.due_date)}
                        </p>
                    </div>
                    <div>{getStatusBadge(attestation.status)}</div>
                </div>
            </div>

            {/* Messages */}
            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded">
                    {error}
                    <button onClick={() => setError(null)} className="float-right font-bold">&times;</button>
                </div>
            )}
            {success && (
                <div className="mb-4 p-4 bg-green-50 border border-green-200 text-green-700 rounded">
                    {success}
                    <button onClick={() => setSuccess(null)} className="float-right font-bold">&times;</button>
                </div>
            )}

            {/* Rejection Warning */}
            {attestation.status === 'REJECTED' && attestation.review_comment && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <h3 className="font-medium text-red-800 mb-2">Rejection Reason</h3>
                    <p className="text-red-700">{attestation.review_comment}</p>
                    <p className="text-sm text-red-600 mt-2">
                        Please address the concerns above and resubmit your attestation.
                    </p>
                </div>
            )}

            {/* Model Info Card */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Model Information</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                        <div className="text-sm text-gray-500">Model</div>
                        <Link to={`/models/${attestation.model.model_id}`} className="text-blue-600 hover:text-blue-800 font-medium">
                            {attestation.model.model_name}
                        </Link>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500">Risk Tier</div>
                        <div className="font-medium">{attestation.model.risk_tier_label || attestation.model.risk_tier_code || '-'}</div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500">Attesting User</div>
                        <div className="font-medium">{attestation.attesting_user.full_name}</div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500">Owner</div>
                        <div className="font-medium">{attestation.model.owner_name || '-'}</div>
                    </div>
                </div>
            </div>

            {/* Questions Form */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Attestation Questions</h2>
                <p className="text-sm text-gray-600 mb-6">
                    Please answer all questions below. Questions marked with * require a comment if you answer "No".
                </p>

                <div className="space-y-6">
                    {questions.map((q, index) => (
                        <div key={q.value_id} className="border-b border-gray-100 pb-6 last:border-0">
                            <div className="flex items-start gap-4">
                                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-medium">
                                    {index + 1}
                                </div>
                                <div className="flex-1">
                                    <div className="font-medium text-gray-900 mb-1">
                                        {q.label}
                                        {q.requires_comment_if_no && <span className="text-red-500 ml-1">*</span>}
                                    </div>
                                    <p className="text-sm text-gray-600 mb-3">{q.description}</p>

                                    {/* Answer Selection */}
                                    <div className="flex gap-4 mb-3">
                                        <label className={`flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer transition-colors ${
                                            answers[q.value_id]?.answer === true
                                                ? 'border-green-500 bg-green-50 text-green-700'
                                                : 'border-gray-200 hover:border-gray-300'
                                        } ${!canEdit ? 'cursor-default' : ''}`}>
                                            <input
                                                type="radio"
                                                name={`question-${q.value_id}`}
                                                checked={answers[q.value_id]?.answer === true}
                                                onChange={() => handleAnswerChange(q.value_id, true)}
                                                disabled={!canEdit}
                                                className="hidden"
                                            />
                                            <span className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                                                answers[q.value_id]?.answer === true
                                                    ? 'border-green-500 bg-green-500'
                                                    : 'border-gray-300'
                                            }`}>
                                                {answers[q.value_id]?.answer === true && (
                                                    <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                                                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                                    </svg>
                                                )}
                                            </span>
                                            Yes
                                        </label>
                                        <label className={`flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer transition-colors ${
                                            answers[q.value_id]?.answer === false
                                                ? 'border-red-500 bg-red-50 text-red-700'
                                                : 'border-gray-200 hover:border-gray-300'
                                        } ${!canEdit ? 'cursor-default' : ''}`}>
                                            <input
                                                type="radio"
                                                name={`question-${q.value_id}`}
                                                checked={answers[q.value_id]?.answer === false}
                                                onChange={() => handleAnswerChange(q.value_id, false)}
                                                disabled={!canEdit}
                                                className="hidden"
                                            />
                                            <span className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                                                answers[q.value_id]?.answer === false
                                                    ? 'border-red-500 bg-red-500'
                                                    : 'border-gray-300'
                                            }`}>
                                                {answers[q.value_id]?.answer === false && (
                                                    <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                                                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                                                    </svg>
                                                )}
                                            </span>
                                            No
                                        </label>
                                    </div>

                                    {/* Comment Field (shown if No is selected or there's an existing comment) */}
                                    {(answers[q.value_id]?.answer === false || answers[q.value_id]?.comment) && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                {q.requires_comment_if_no ? 'Comment (Required)' : 'Comment (Optional)'}
                                            </label>
                                            <textarea
                                                value={answers[q.value_id]?.comment || ''}
                                                onChange={(e) => handleCommentChange(q.value_id, e.target.value)}
                                                disabled={!canEdit}
                                                className="input-field text-sm"
                                                rows={2}
                                                placeholder="Please explain..."
                                            />
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Additional Comments */}
            {(canEdit || decisionComment) && (
                <div className="bg-white rounded-lg shadow p-6 mb-6">
                    <h2 className="text-lg font-semibold mb-4">Additional Comments</h2>
                    <textarea
                        value={decisionComment}
                        onChange={(e) => setDecisionComment(e.target.value)}
                        disabled={!canEdit}
                        className="input-field"
                        rows={3}
                        placeholder="Any additional comments or explanations..."
                    />
                </div>
            )}

            {/* Inventory Change Proposals */}
            <div id="change-proposals-section" className="bg-white rounded-lg shadow p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Inventory Change Proposals</h2>
                    {canEdit && (
                        <div className="flex gap-2">
                            <button
                                onClick={() => openChangeModal('UPDATE_EXISTING')}
                                className="text-sm px-3 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100"
                            >
                                Update Model
                            </button>
                            <button
                                onClick={() => openChangeModal('NEW_MODEL')}
                                className="text-sm px-3 py-1 bg-green-50 text-green-600 rounded hover:bg-green-100"
                            >
                                Register New Model
                            </button>
                            <button
                                onClick={() => openChangeModal('DECOMMISSION')}
                                className="text-sm px-3 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100"
                            >
                                Decommission Model
                            </button>
                        </div>
                    )}
                </div>

                {(!attestation.change_proposals || attestation.change_proposals.length === 0) ? (
                    <p className="text-sm text-gray-500 italic">
                        No inventory changes proposed during this attestation.
                    </p>
                ) : (
                    <div className="space-y-3">
                        {attestation.change_proposals.map((proposal) => (
                            <div key={proposal.proposal_id} className="border border-gray-200 rounded-lg p-4">
                                <div className="flex items-start justify-between">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                                proposal.change_type === 'UPDATE_EXISTING' ? 'bg-blue-100 text-blue-700' :
                                                proposal.change_type === 'NEW_MODEL' ? 'bg-green-100 text-green-700' :
                                                'bg-red-100 text-red-700'
                                            }`}>
                                                {proposal.change_type.replace('_', ' ')}
                                            </span>
                                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                                proposal.status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' :
                                                proposal.status === 'ACCEPTED' ? 'bg-green-100 text-green-700' :
                                                'bg-red-100 text-red-700'
                                            }`}>
                                                {proposal.status}
                                            </span>
                                        </div>
                                        {proposal.model && (
                                            <p className="text-sm font-medium mt-1">
                                                Model: {proposal.model.model_name}
                                            </p>
                                        )}
                                        {proposal.change_type === 'NEW_MODEL' && proposal.proposed_data && (
                                            <p className="text-sm font-medium mt-1">
                                                New Model: {(proposal.proposed_data as { model_name?: string }).model_name || 'Unknown'}
                                            </p>
                                        )}
                                        {proposal.proposed_data && Object.keys(proposal.proposed_data).length > 0 && (
                                            <div className="mt-2 text-xs">
                                                <p className="text-gray-500 font-medium mb-1">Proposed Changes:</p>
                                                <ul className="space-y-0.5 ml-2">
                                                    {Object.entries(proposal.proposed_data).map(([key, value]) => (
                                                        <li key={key} className="text-gray-600">
                                                            <span className="font-medium text-gray-700">{key.replace(/_/g, ' ')}:</span>{' '}
                                                            {typeof value === 'string' ? value : JSON.stringify(value)}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {proposal.admin_comment && (
                                            <p className="text-sm text-gray-600 mt-2 italic">
                                                Admin: {proposal.admin_comment}
                                            </p>
                                        )}
                                    </div>
                                    {/* Admin controls */}
                                    {(user?.role === 'Admin' || user?.role === 'Validator') && proposal.status === 'PENDING' && (
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => handleAcceptProposal(proposal.proposal_id)}
                                                className="text-xs px-2 py-1 bg-green-50 text-green-600 rounded hover:bg-green-100"
                                            >
                                                Accept
                                            </button>
                                            <button
                                                onClick={() => handleRejectProposal(proposal.proposal_id)}
                                                className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100"
                                            >
                                                Reject
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Change Proposal Modal */}
            {showChangeModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
                        <h3 className="text-lg font-semibold mb-4">
                            {changeType === 'UPDATE_EXISTING' ? 'Propose Model Update' :
                             changeType === 'NEW_MODEL' ? 'Register New Model' :
                             'Propose Model Decommissioning'}
                        </h3>

                        {(changeType === 'UPDATE_EXISTING' || changeType === 'DECOMMISSION') && (
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Select Model
                                </label>
                                <select
                                    value={selectedModelId || ''}
                                    onChange={(e) => setSelectedModelId(Number(e.target.value) || null)}
                                    className="input-field"
                                >
                                    <option value="">Select a model...</option>
                                    {availableModels.map(m => (
                                        <option key={m.model_id} value={m.model_id}>
                                            {m.model_name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {changeType === 'UPDATE_EXISTING' && (
                            <div className="space-y-3">
                                <p className="text-sm text-gray-600">
                                    Specify the fields you want to change:
                                </p>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        New Description (optional)
                                    </label>
                                    <textarea
                                        value={proposedData.description || ''}
                                        onChange={(e) => setProposedData(prev => ({ ...prev, description: e.target.value }))}
                                        className="input-field"
                                        rows={2}
                                        placeholder="Updated description..."
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        New Status (optional)
                                    </label>
                                    <input
                                        type="text"
                                        value={proposedData.status || ''}
                                        onChange={(e) => setProposedData(prev => ({ ...prev, status: e.target.value }))}
                                        className="input-field"
                                        placeholder="e.g., Active, Under Review"
                                    />
                                </div>
                            </div>
                        )}

                        {changeType === 'NEW_MODEL' && (
                            <div className="space-y-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Model Name *
                                    </label>
                                    <input
                                        type="text"
                                        value={proposedData.model_name || ''}
                                        onChange={(e) => setProposedData(prev => ({ ...prev, model_name: e.target.value }))}
                                        className="input-field"
                                        placeholder="Enter model name..."
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Description
                                    </label>
                                    <textarea
                                        value={proposedData.description || ''}
                                        onChange={(e) => setProposedData(prev => ({ ...prev, description: e.target.value }))}
                                        className="input-field"
                                        rows={3}
                                        placeholder="Enter model description..."
                                    />
                                </div>
                            </div>
                        )}

                        {changeType === 'DECOMMISSION' && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Reason for Decommissioning
                                </label>
                                <textarea
                                    value={proposedData.reason || ''}
                                    onChange={(e) => setProposedData(prev => ({ ...prev, reason: e.target.value }))}
                                    className="input-field"
                                    rows={3}
                                    placeholder="Please explain why this model should be decommissioned..."
                                />
                            </div>
                        )}

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setShowChangeModal(false)}
                                className="btn-secondary"
                                disabled={submittingChange}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSubmitChange}
                                className="btn-primary"
                                disabled={submittingChange}
                            >
                                {submittingChange ? 'Submitting...' : 'Submit Proposal'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Update Prompt Modal - shown when user has "No" answers but no change proposals */}
            {showUpdatePrompt && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-yellow-100 flex items-center justify-center">
                                <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                            </div>
                            <h3 className="text-lg font-semibold">Inventory Changes Recommended</h3>
                        </div>

                        <p className="text-gray-600 mb-4">
                            You've answered "No" to one or more questions. This indicates potential inventory changes may be needed.
                        </p>

                        <p className="text-gray-600 mb-6">
                            Would you like to propose inventory changes (update existing models, register new models, or request decommissioning) before submitting your attestation?
                        </p>

                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => handleSubmit(true)}
                                className="btn-secondary"
                            >
                                Submit Without Changes
                            </button>
                            <button
                                onClick={() => {
                                    setShowUpdatePrompt(false);
                                    // Scroll to change proposals section
                                    const section = document.getElementById('change-proposals-section');
                                    if (section) {
                                        section.scrollIntoView({ behavior: 'smooth' });
                                    }
                                }}
                                className="btn-primary"
                            >
                                Add Change Proposals
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Submission History */}
            {(attestation.attested_at || attestation.reviewed_at) && (
                <div className="bg-white rounded-lg shadow p-6 mb-6">
                    <h2 className="text-lg font-semibold mb-4">History</h2>
                    <div className="space-y-3">
                        {attestation.attested_at && (
                            <div className="flex items-center gap-3 text-sm">
                                <span className="w-24 text-gray-500">Submitted:</span>
                                <span>{formatDateTime(attestation.attested_at)} by {attestation.attesting_user.full_name}</span>
                            </div>
                        )}
                        {attestation.reviewed_at && attestation.reviewed_by && (
                            <div className="flex items-center gap-3 text-sm">
                                <span className="w-24 text-gray-500">Reviewed:</span>
                                <span>{formatDateTime(attestation.reviewed_at)} by {attestation.reviewed_by.full_name}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Submit Button (for owners) */}
            {canEdit && isOwner && (
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-600">
                                By submitting, you confirm that you have reviewed and answered all questions truthfully.
                            </p>
                        </div>
                        <button
                            onClick={() => handleSubmit()}
                            disabled={submitting}
                            className="btn-primary"
                        >
                            {submitting ? 'Submitting...' : 'Submit Attestation'}
                        </button>
                    </div>
                </div>
            )}

            {/* Review Panel (for Admin/Validator) */}
            {canReview && (
                <div className="bg-white rounded-lg shadow p-6">
                    <h2 className="text-lg font-semibold mb-4">Review Attestation</h2>
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Review Comment {attestation.status === 'SUBMITTED' && '(Required for rejection)'}
                        </label>
                        <textarea
                            value={reviewComment}
                            onChange={(e) => setReviewComment(e.target.value)}
                            className="input-field"
                            rows={3}
                            placeholder="Add review comments..."
                        />
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={handleAccept}
                            disabled={isReviewing}
                            className="btn-primary bg-green-600 hover:bg-green-700"
                        >
                            {isReviewing ? 'Processing...' : 'Accept'}
                        </button>
                        <button
                            onClick={handleReject}
                            disabled={isReviewing}
                            className="btn-secondary bg-red-50 text-red-600 border-red-200 hover:bg-red-100"
                        >
                            {isReviewing ? 'Processing...' : 'Reject'}
                        </button>
                    </div>
                </div>
            )}
        </Layout>
    );
}

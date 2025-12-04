import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Layout from '../components/Layout';
import BulkModelSelectionTable from '../components/BulkModelSelectionTable';
import { useBulkAttestation } from '../hooks/useBulkAttestation';

export default function BulkAttestationPage() {
    const { cycleId } = useParams<{ cycleId: string }>();
    const navigate = useNavigate();
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [showDiscardModal, setShowDiscardModal] = useState(false);

    const {
        // State
        cycle,
        models,
        questions,
        summary,
        selectedModelIds,
        excludedModelIds,
        responses,
        decisionComment,
        isDirty,
        lastSaved,
        isSaving,
        draftExists,
        isLoading,
        isSubmitting,
        error,
        successMessage,
        selectedCount,
        pendingModelIds,
        canSubmit,
        validationErrors,

        // Actions
        toggleModel,
        selectAll,
        deselectAll,
        setResponse,
        setResponseComment,
        setDecisionComment,
        saveDraft,
        discardDraft,
        submit,
        clearError,
        clearSuccess
    } = useBulkAttestation(Number(cycleId));

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        return dateStr.split('T')[0];
    };

    const handleSubmit = async () => {
        const success = await submit();
        if (success) {
            setShowConfirmModal(false);
            // Navigate back to my attestations after short delay to show success
            setTimeout(() => {
                navigate('/my-attestations');
            }, 2000);
        }
    };

    const handleDiscard = async () => {
        await discardDraft();
        setShowDiscardModal(false);
    };

    // Loading state
    if (isLoading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-64">
                    <div className="text-gray-500">Loading bulk attestation...</div>
                </div>
            </Layout>
        );
    }

    // No cycle found
    if (!cycle) {
        return (
            <Layout>
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                    <h2 className="text-lg font-semibold text-red-800 mb-2">Cycle Not Found</h2>
                    <p className="text-red-600 mb-4">The requested attestation cycle could not be found.</p>
                    <Link to="/my-attestations" className="btn-secondary">
                        Back to My Attestations
                    </Link>
                </div>
            </Layout>
        );
    }

    // No pending models - show completion summary instead of empty state
    if (pendingModelIds.length === 0) {
        const submittedModels = models.filter(m => m.attestation_status === 'SUBMITTED');
        const acceptedModels = models.filter(m => m.attestation_status === 'ACCEPTED');
        const rejectedModels = models.filter(m => m.attestation_status === 'REJECTED');
        const hasSubmissions = submittedModels.length > 0 || acceptedModels.length > 0;

        return (
            <Layout>
                <div className="mb-6">
                    <Link to="/my-attestations" className="text-blue-600 hover:text-blue-800 flex items-center gap-1">
                        <span>&larr;</span> Back to My Attestations
                    </Link>
                </div>

                {/* Cycle Header */}
                <div className="mb-6">
                    <h1 className="text-2xl font-bold text-gray-900">Bulk Attestation Summary</h1>
                    <p className="text-gray-600 mt-1">{cycle.cycle_name}</p>
                </div>

                {/* Completion Status */}
                {hasSubmissions ? (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-6">
                        <div className="flex items-center gap-3">
                            <span className="text-green-500 text-2xl">&#10003;</span>
                            <div>
                                <h2 className="text-lg font-semibold text-green-800">
                                    Bulk Attestation Complete
                                </h2>
                                <p className="text-green-700 mt-1">
                                    All models in this cycle have been attested.
                                </p>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
                        <h2 className="text-lg font-semibold text-blue-800 mb-2">No Pending Models</h2>
                        <p className="text-blue-600">
                            You have no pending models for bulk attestation in this cycle.
                        </p>
                    </div>
                )}

                {/* Summary Stats */}
                {summary && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <div className="bg-white p-4 rounded-lg shadow">
                            <div className="text-sm text-gray-500">Submitted</div>
                            <div className="text-2xl font-bold text-blue-600">{summary.submitted_count}</div>
                        </div>
                        <div className="bg-white p-4 rounded-lg shadow">
                            <div className="text-sm text-gray-500">Accepted</div>
                            <div className="text-2xl font-bold text-green-600">{summary.accepted_count}</div>
                        </div>
                        <div className="bg-white p-4 rounded-lg shadow">
                            <div className="text-sm text-gray-500">Rejected</div>
                            <div className="text-2xl font-bold text-red-600">{summary.rejected_count}</div>
                        </div>
                        <div className="bg-white p-4 rounded-lg shadow">
                            <div className="text-sm text-gray-500">Total</div>
                            <div className="text-2xl font-bold text-gray-800">{summary.total_models}</div>
                        </div>
                    </div>
                )}

                {/* Rejected Models Warning */}
                {rejectedModels.length > 0 && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                        <div className="flex items-start gap-3">
                            <span className="text-red-500 text-xl">&#9888;</span>
                            <div>
                                <div className="font-medium text-red-800">
                                    {rejectedModels.length} attestation{rejectedModels.length !== 1 ? 's' : ''} rejected
                                </div>
                                <div className="text-sm text-red-700 mt-1">
                                    These require individual resubmission:
                                </div>
                                <ul className="text-sm text-red-700 mt-2 list-disc list-inside">
                                    {rejectedModels.map(m => (
                                        <li key={m.model_id}>
                                            <Link to={`/attestations/${m.attestation_id}`} className="hover:underline">
                                                {m.model_name}
                                            </Link>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                )}

                {/* Models Table (read-only) */}
                {models.length > 0 && (
                    <div className="bg-white rounded-lg shadow overflow-hidden">
                        <div className="px-6 py-4 border-b border-gray-200">
                            <h2 className="text-lg font-semibold text-gray-900">Attestation Status</h2>
                        </div>
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {models.map(model => (
                                    <tr key={model.model_id}>
                                        <td className="px-6 py-4">
                                            <Link to={`/models/${model.model_id}`} className="text-blue-600 hover:text-blue-800">
                                                {model.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-600">
                                            {model.risk_tier_label || '-'}
                                        </td>
                                        <td className="px-6 py-4">
                                            {model.attestation_status === 'SUBMITTED' && (
                                                <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">Submitted</span>
                                            )}
                                            {model.attestation_status === 'ACCEPTED' && (
                                                <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">Accepted</span>
                                            )}
                                            {model.attestation_status === 'REJECTED' && (
                                                <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">Rejected</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            <Link to={`/attestations/${model.attestation_id}`} className="text-blue-600 hover:text-blue-800 text-sm">
                                                View
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                <div className="mt-6 text-center">
                    <Link to="/my-attestations" className="btn-primary">
                        Back to My Attestations
                    </Link>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            {/* Header */}
            <div className="mb-6">
                <Link to="/my-attestations" className="text-blue-600 hover:text-blue-800 flex items-center gap-1 mb-4">
                    <span>&larr;</span> Back to My Attestations
                </Link>

                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Bulk Attestation</h1>
                        <p className="text-gray-600 mt-1">{cycle.cycle_name}</p>
                    </div>

                    <div className="text-right">
                        <div className="text-sm text-gray-600">
                            Due: <span className="font-medium">{formatDate(cycle.submission_due_date)}</span>
                        </div>
                        <div className={`text-sm ${cycle.days_until_due < 0 ? 'text-red-600' : cycle.days_until_due <= 7 ? 'text-orange-600' : 'text-gray-600'}`}>
                            {cycle.days_until_due < 0
                                ? `${Math.abs(cycle.days_until_due)} days overdue`
                                : `${cycle.days_until_due} days remaining`}
                        </div>
                    </div>
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex justify-between items-center">
                    <span>{error}</span>
                    <button onClick={clearError} className="font-bold text-red-800">&times;</button>
                </div>
            )}

            {/* Success Message */}
            {successMessage && (
                <div className="mb-4 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg flex justify-between items-center">
                    <span>{successMessage}</span>
                    <button onClick={clearSuccess} className="font-bold text-green-800">&times;</button>
                </div>
            )}

            {/* Draft Status Bar */}
            <div className="mb-6 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 flex justify-between items-center">
                <div className="flex items-center gap-4">
                    {draftExists && (
                        <span className="text-sm text-gray-600">
                            Draft saved
                            {lastSaved && (
                                <span className="ml-1">
                                    at {lastSaved.toLocaleTimeString()}
                                </span>
                            )}
                        </span>
                    )}
                    {isSaving && (
                        <span className="text-sm text-blue-600">Saving...</span>
                    )}
                    {isDirty && !isSaving && (
                        <span className="text-sm text-orange-600">Unsaved changes</span>
                    )}
                </div>
                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        onClick={saveDraft}
                        disabled={isSaving || isSubmitting}
                        className="btn-secondary text-sm py-1.5 px-3"
                    >
                        Save Draft
                    </button>
                    {draftExists && (
                        <button
                            type="button"
                            onClick={() => setShowDiscardModal(true)}
                            disabled={isSaving || isSubmitting}
                            className="text-sm text-red-600 hover:text-red-800"
                        >
                            Discard Draft
                        </button>
                    )}
                </div>
            </div>

            {/* Step 1: Model Selection */}
            <div className="bg-white rounded-lg shadow mb-6">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">Step 1: Select Models</h2>
                    <p className="text-sm text-gray-600 mt-1">
                        Select the models you can fully attest to. Unchecked models will need to be attested individually.
                    </p>
                </div>
                <div className="p-6">
                    <BulkModelSelectionTable
                        models={models}
                        selectedModelIds={selectedModelIds}
                        onToggleModel={toggleModel}
                        onSelectAll={selectAll}
                        onDeselectAll={deselectAll}
                        disabled={isSubmitting}
                    />
                </div>
            </div>

            {/* Step 2: Attestation Questions */}
            <div className="bg-white rounded-lg shadow mb-6">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">Step 2: Answer Attestation Questions</h2>
                    <p className="text-sm text-gray-600 mt-1">
                        Your answers will apply to ALL {selectedCount} selected models.
                        If any statement does not apply to a specific model, exclude that model above.
                    </p>
                </div>
                <div className="p-6 space-y-6">
                    {questions.map((question, index) => {
                        const response = responses.get(question.value_id);
                        const answer = response?.answer;
                        const comment = response?.comment || '';
                        const showCommentField = answer === false && question.requires_comment_if_no;

                        return (
                            <div key={question.value_id} className="border border-gray-200 rounded-lg p-4">
                                <div className="flex items-start gap-3">
                                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-800 font-semibold text-sm">
                                        {index + 1}
                                    </div>
                                    <div className="flex-1">
                                        <div className="font-medium text-gray-900 mb-2">
                                            {question.label}
                                            {question.requires_comment_if_no && (
                                                <span className="text-red-500 ml-1">*</span>
                                            )}
                                        </div>
                                        {question.description && (
                                            <div className="text-sm text-gray-600 mb-3">
                                                {question.description}
                                            </div>
                                        )}

                                        {/* Yes/No Buttons */}
                                        <div className="flex gap-4 mt-3">
                                            <button
                                                type="button"
                                                onClick={() => setResponse(question.value_id, true)}
                                                disabled={isSubmitting}
                                                className={`px-6 py-2 rounded-lg border-2 font-medium transition-colors ${
                                                    answer === true
                                                        ? 'bg-green-100 border-green-500 text-green-800'
                                                        : 'bg-white border-gray-300 text-gray-700 hover:border-green-300 hover:bg-green-50'
                                                }`}
                                            >
                                                Yes
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setResponse(question.value_id, false)}
                                                disabled={isSubmitting}
                                                className={`px-6 py-2 rounded-lg border-2 font-medium transition-colors ${
                                                    answer === false
                                                        ? 'bg-red-100 border-red-500 text-red-800'
                                                        : 'bg-white border-gray-300 text-gray-700 hover:border-red-300 hover:bg-red-50'
                                                }`}
                                            >
                                                No
                                            </button>
                                        </div>

                                        {/* Comment field when answer is No */}
                                        {showCommentField && (
                                            <div className="mt-3">
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Please provide an explanation <span className="text-red-500">*</span>
                                                </label>
                                                <textarea
                                                    value={comment}
                                                    onChange={(e) => setResponseComment(question.value_id, e.target.value)}
                                                    disabled={isSubmitting}
                                                    rows={3}
                                                    className="input-field"
                                                    placeholder="Explain why you answered No..."
                                                />
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Step 3: Additional Comments */}
            <div className="bg-white rounded-lg shadow mb-6">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">Step 3: Additional Comments (Optional)</h2>
                </div>
                <div className="p-6">
                    <textarea
                        value={decisionComment}
                        onChange={(e) => setDecisionComment(e.target.value)}
                        disabled={isSubmitting}
                        rows={4}
                        className="input-field"
                        placeholder="Any additional comments for this attestation..."
                    />
                </div>
            </div>

            {/* Summary and Submit */}
            <div className="bg-white rounded-lg shadow">
                <div className="p-6">
                    {/* Excluded Models Warning */}
                    {excludedModelIds.size > 0 && (
                        <div className="mb-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                            <div className="flex items-start gap-3">
                                <span className="text-orange-500 text-xl">&#9888;</span>
                                <div>
                                    <div className="font-medium text-orange-800">
                                        {excludedModelIds.size} model{excludedModelIds.size !== 1 ? 's' : ''} excluded from bulk attestation
                                    </div>
                                    <div className="text-sm text-orange-700 mt-1">
                                        These models will require individual attestation:
                                    </div>
                                    <ul className="text-sm text-orange-700 mt-2 list-disc list-inside">
                                        {models
                                            .filter(m => excludedModelIds.has(m.model_id))
                                            .map(m => (
                                                <li key={m.model_id}>{m.model_name}</li>
                                            ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Validation Errors */}
                    {validationErrors.length > 0 && (
                        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                            <div className="font-medium text-red-800 mb-2">Please fix the following issues:</div>
                            <ul className="text-sm text-red-700 list-disc list-inside">
                                {validationErrors.map((err, i) => (
                                    <li key={i}>{err}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Confirmation Text */}
                    <div className="text-sm text-gray-600 mb-4">
                        By submitting, I confirm that I have reviewed all {selectedCount} selected models
                        and that the statements above apply to each of them.
                    </div>

                    {/* Action Buttons */}
                    <div className="flex justify-end gap-3">
                        <Link to="/my-attestations" className="btn-secondary">
                            Cancel
                        </Link>
                        <button
                            type="button"
                            onClick={saveDraft}
                            disabled={isSaving || isSubmitting}
                            className="btn-secondary"
                        >
                            {isSaving ? 'Saving...' : 'Save Draft'}
                        </button>
                        <button
                            type="button"
                            onClick={() => setShowConfirmModal(true)}
                            disabled={!canSubmit}
                            className="btn-primary"
                        >
                            Submit {selectedCount} Attestation{selectedCount !== 1 ? 's' : ''}
                        </button>
                    </div>
                </div>
            </div>

            {/* Confirmation Modal */}
            {showConfirmModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                        <div className="p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">
                                Confirm Bulk Attestation
                            </h3>
                            <p className="text-gray-600 mb-4">
                                You are about to submit attestations for {selectedCount} model{selectedCount !== 1 ? 's' : ''}.
                                This action cannot be undone.
                            </p>
                            {excludedModelIds.size > 0 && (
                                <p className="text-orange-600 text-sm mb-4">
                                    {excludedModelIds.size} model{excludedModelIds.size !== 1 ? 's' : ''} will need to be attested individually.
                                </p>
                            )}
                            <div className="flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmModal(false)}
                                    disabled={isSubmitting}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="button"
                                    onClick={handleSubmit}
                                    disabled={isSubmitting}
                                    className="btn-primary"
                                >
                                    {isSubmitting ? 'Submitting...' : 'Confirm Submit'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Discard Draft Modal */}
            {showDiscardModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                        <div className="p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">
                                Discard Draft?
                            </h3>
                            <p className="text-gray-600 mb-4">
                                Are you sure you want to discard your draft? All your selections and answers will be lost.
                            </p>
                            <div className="flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowDiscardModal(false)}
                                    className="btn-secondary"
                                >
                                    Keep Draft
                                </button>
                                <button
                                    type="button"
                                    onClick={handleDiscard}
                                    className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg"
                                >
                                    Discard
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

import { useState } from 'react';
import { recommendationsApi, Recommendation } from '../api/recommendations';

interface RebuttalModalProps {
    recommendation: Recommendation;
    onClose: () => void;
    onSuccess: () => void;
}

export default function RebuttalModal({ recommendation, onClose, onSuccess }: RebuttalModalProps) {
    const currentStatus = recommendation.current_status?.code || '';
    const isReviewMode = currentStatus === 'REC_IN_REBUTTAL';

    // For submitting a new rebuttal
    const [rationale, setRationale] = useState('');
    const [supportingEvidence, setSupportingEvidence] = useState('');

    // For reviewing an existing rebuttal
    const [decision, setDecision] = useState<'ACCEPT' | 'OVERRIDE'>('ACCEPT');
    const [reviewComments, setReviewComments] = useState('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Find the current rebuttal for review
    const currentRebuttal = recommendation.rebuttals?.find(r => r.is_current);

    const handleSubmitRebuttal = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!rationale.trim()) {
            setError('Please provide a rationale for your rebuttal');
            return;
        }

        try {
            setLoading(true);
            await recommendationsApi.submitRebuttal(recommendation.recommendation_id, {
                rationale: rationale.trim(),
                supporting_evidence: supportingEvidence.trim() || undefined
            });
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit rebuttal');
        } finally {
            setLoading(false);
        }
    };

    const handleReviewRebuttal = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!currentRebuttal) {
            setError('No current rebuttal to review');
            return;
        }

        try {
            setLoading(true);
            await recommendationsApi.reviewRebuttal(
                recommendation.recommendation_id,
                currentRebuttal.rebuttal_id,
                {
                    decision,
                    comments: reviewComments.trim() || undefined
                }
            );
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit review');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold">
                            {isReviewMode ? 'Review Rebuttal' : 'Submit Rebuttal'}
                        </h3>
                        <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {error && (
                        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                            {error}
                        </div>
                    )}

                    {isReviewMode ? (
                        // Review Mode - Validator reviewing existing rebuttal
                        <form onSubmit={handleReviewRebuttal}>
                            {currentRebuttal && (
                                <div className="bg-gray-50 p-4 rounded-lg mb-4">
                                    <h4 className="font-medium mb-2">Developer's Rebuttal</h4>
                                    <p className="text-gray-700 mb-2">{currentRebuttal.rationale}</p>
                                    {currentRebuttal.supporting_evidence && (
                                        <div className="mt-2 pt-2 border-t">
                                            <span className="text-sm font-medium text-gray-500">Supporting Evidence:</span>
                                            <p className="text-gray-700 text-sm">{currentRebuttal.supporting_evidence}</p>
                                        </div>
                                    )}
                                    <div className="mt-2 text-sm text-gray-500">
                                        Submitted by {currentRebuttal.submitted_by?.full_name} on {currentRebuttal.submitted_at?.split('T')[0]}
                                    </div>
                                </div>
                            )}

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Decision <span className="text-red-500">*</span>
                                    </label>
                                    <div className="space-y-2">
                                        <label className="flex items-center">
                                            <input
                                                type="radio"
                                                value="ACCEPT"
                                                checked={decision === 'ACCEPT'}
                                                onChange={() => setDecision('ACCEPT')}
                                                className="mr-2"
                                            />
                                            <span className="text-green-700">Accept Rebuttal</span>
                                            <span className="text-sm text-gray-500 ml-2">
                                                (Recommendation will be dropped)
                                            </span>
                                        </label>
                                        <label className="flex items-center">
                                            <input
                                                type="radio"
                                                value="OVERRIDE"
                                                checked={decision === 'OVERRIDE'}
                                                onChange={() => setDecision('OVERRIDE')}
                                                className="mr-2"
                                            />
                                            <span className="text-red-700">Override Rebuttal</span>
                                            <span className="text-sm text-gray-500 ml-2">
                                                (Developer must submit action plan)
                                            </span>
                                        </label>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Review Comments
                                    </label>
                                    <textarea
                                        value={reviewComments}
                                        onChange={(e) => setReviewComments(e.target.value)}
                                        rows={3}
                                        className="input-field"
                                        placeholder="Optional comments on your decision..."
                                    />
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                    disabled={loading}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className={`px-4 py-2 text-white rounded ${
                                        decision === 'ACCEPT'
                                            ? 'bg-green-600 hover:bg-green-700'
                                            : 'bg-red-600 hover:bg-red-700'
                                    }`}
                                    disabled={loading}
                                >
                                    {loading ? 'Submitting...' : decision === 'ACCEPT' ? 'Accept Rebuttal' : 'Override Rebuttal'}
                                </button>
                            </div>
                        </form>
                    ) : (
                        // Submit Mode - Developer submitting new rebuttal
                        <form onSubmit={handleSubmitRebuttal}>
                            <p className="text-sm text-gray-600 mb-4">
                                Submit a rebuttal if you believe this recommendation should be dropped or modified.
                                Your rebuttal will be reviewed by the validator.
                            </p>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Rationale <span className="text-red-500">*</span>
                                    </label>
                                    <textarea
                                        value={rationale}
                                        onChange={(e) => setRationale(e.target.value)}
                                        rows={4}
                                        className="input-field"
                                        placeholder="Explain why this recommendation should be reconsidered..."
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Supporting Evidence
                                    </label>
                                    <textarea
                                        value={supportingEvidence}
                                        onChange={(e) => setSupportingEvidence(e.target.value)}
                                        rows={3}
                                        className="input-field"
                                        placeholder="Optional: Provide supporting evidence for your rebuttal..."
                                    />
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                    disabled={loading}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
                                    disabled={loading}
                                >
                                    {loading ? 'Submitting...' : 'Submit Rebuttal'}
                                </button>
                            </div>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );
}

import { useState } from 'react';
import { recommendationsApi, Recommendation } from '../api/recommendations';

interface ClosureReviewModalProps {
    recommendation: Recommendation;
    onClose: () => void;
    onSuccess: () => void;
}

export default function ClosureReviewModal({ recommendation, onClose, onSuccess }: ClosureReviewModalProps) {
    const [decision, setDecision] = useState<'APPROVE' | 'RETURN'>('APPROVE');
    const [reviewComments, setReviewComments] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (decision === 'RETURN' && !reviewComments.trim()) {
            setError('Please provide feedback explaining what rework is needed');
            return;
        }

        try {
            setLoading(true);
            await recommendationsApi.reviewClosure(recommendation.recommendation_id, {
                decision,
                review_comments: reviewComments.trim() || undefined
            });
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit review');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold">Review Closure Request</h3>
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

                    {/* Closure Summary */}
                    {recommendation.closure_summary && (
                        <div className="bg-gray-50 p-4 rounded-lg mb-4">
                            <h4 className="font-medium mb-2">Developer's Closure Summary</h4>
                            <p className="text-gray-700 whitespace-pre-wrap">{recommendation.closure_summary}</p>
                        </div>
                    )}

                    {/* Action Plan Tasks */}
                    {recommendation.action_plan_tasks && recommendation.action_plan_tasks.length > 0 && (
                        <div className="bg-gray-50 p-4 rounded-lg mb-4">
                            <h4 className="font-medium mb-2">Action Plan Tasks</h4>
                            <div className="space-y-2">
                                {recommendation.action_plan_tasks.map((task, index) => (
                                    <div key={task.task_id} className="flex items-center gap-2">
                                        <span className={`w-5 h-5 flex items-center justify-center rounded-full text-xs ${
                                            task.completion_status?.code === 'TASK_COMPLETED'
                                                ? 'bg-green-100 text-green-700'
                                                : 'bg-gray-200 text-gray-600'
                                        }`}>
                                            {task.completion_status?.code === 'TASK_COMPLETED' ? '✓' : index + 1}
                                        </span>
                                        <span className={`text-sm ${
                                            task.completion_status?.code === 'TASK_COMPLETED'
                                                ? 'text-gray-700'
                                                : 'text-gray-500'
                                        }`}>
                                            {task.description}
                                        </span>
                                        <span className={`text-xs px-2 py-0.5 rounded ${
                                            task.completion_status?.code === 'TASK_COMPLETED'
                                                ? 'bg-green-100 text-green-700'
                                                : task.completion_status?.code === 'TASK_IN_PROGRESS'
                                                    ? 'bg-blue-100 text-blue-700'
                                                    : 'bg-gray-100 text-gray-600'
                                        }`}>
                                            {task.completion_status?.label}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Evidence */}
                    {recommendation.closure_evidence && recommendation.closure_evidence.length > 0 && (
                        <div className="bg-gray-50 p-4 rounded-lg mb-4">
                            <h4 className="font-medium mb-2">Supporting Evidence</h4>
                            <div className="space-y-2">
                                {recommendation.closure_evidence.map((ev) => (
                                    <div key={ev.evidence_id} className="text-sm">
                                        {ev.description && (
                                            <p className="text-gray-700">{ev.description}</p>
                                        )}
                                        {ev.file_path && (
                                            <a
                                                href={ev.file_path}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-blue-600 hover:underline text-xs break-all"
                                            >
                                                {ev.file_name || ev.file_path}
                                            </a>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <form onSubmit={handleSubmit}>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Review Decision <span className="text-red-500">*</span>
                                </label>
                                <div className="space-y-2">
                                    <label className="flex items-center">
                                        <input
                                            type="radio"
                                            value="APPROVE"
                                            checked={decision === 'APPROVE'}
                                            onChange={() => setDecision('APPROVE')}
                                            className="mr-2"
                                        />
                                        <span className="text-green-700 font-medium">Approve Closure</span>
                                        <span className="text-sm text-gray-500 ml-2">
                                            (Proceed to final approval)
                                        </span>
                                    </label>
                                    <label className="flex items-center">
                                        <input
                                            type="radio"
                                            value="RETURN"
                                            checked={decision === 'RETURN'}
                                            onChange={() => setDecision('RETURN')}
                                            className="mr-2"
                                        />
                                        <span className="text-orange-700 font-medium">Return for Rework</span>
                                        <span className="text-sm text-gray-500 ml-2">
                                            (Developer must address feedback)
                                        </span>
                                    </label>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Review Comments
                                    {decision === 'RETURN' && <span className="text-red-500"> *</span>}
                                </label>
                                <textarea
                                    value={reviewComments}
                                    onChange={(e) => setReviewComments(e.target.value)}
                                    rows={3}
                                    className="input-field"
                                    placeholder={decision === 'RETURN'
                                        ? "Explain what additional work or changes are required..."
                                        : "Optional comments on closure approval..."}
                                    required={decision === 'RETURN'}
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
                                    decision === 'APPROVE'
                                        ? 'bg-green-600 hover:bg-green-700'
                                        : 'bg-orange-600 hover:bg-orange-700'
                                }`}
                                disabled={loading}
                            >
                                {loading ? 'Submitting...' : decision === 'APPROVE' ? 'Approve Closure' : 'Return for Rework'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

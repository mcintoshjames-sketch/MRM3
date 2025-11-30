import { useState } from 'react';
import { recommendationsApi, Recommendation } from '../api/recommendations';

interface ClosureSubmitModalProps {
    recommendation: Recommendation;
    onClose: () => void;
    onSuccess: () => void;
}

export default function ClosureSubmitModal({ recommendation, onClose, onSuccess }: ClosureSubmitModalProps) {
    const [closureSummary, setClosureSummary] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Check if all tasks are completed
    const allTasksCompleted = recommendation.action_plan_tasks?.every(
        task => task.completion_status?.code === 'TASK_COMPLETED'
    ) ?? true;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!closureSummary.trim()) {
            setError('Please provide a closure summary');
            return;
        }

        try {
            setLoading(true);
            await recommendationsApi.submitForClosure(recommendation.recommendation_id, {
                closure_summary: closureSummary.trim()
            });
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit for closure');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold">Submit for Closure</h3>
                        <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Warning if not all tasks complete */}
                    {!allTasksCompleted && recommendation.action_plan_tasks && recommendation.action_plan_tasks.length > 0 && (
                        <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 px-4 py-3 rounded mb-4">
                            <div className="flex items-center gap-2">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                                <span className="font-medium">Not all action plan tasks are completed</span>
                            </div>
                            <p className="text-sm mt-1">
                                You can still submit for closure, but please explain why incomplete tasks are acceptable.
                            </p>
                        </div>
                    )}

                    {error && (
                        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit}>
                        {/* Task Summary */}
                        {recommendation.action_plan_tasks && recommendation.action_plan_tasks.length > 0 && (
                            <div className="bg-gray-50 p-4 rounded-lg mb-4">
                                <h4 className="font-medium mb-2">Action Plan Summary</h4>
                                <div className="text-sm">
                                    <span className="text-green-600">
                                        {recommendation.action_plan_tasks.filter(t => t.completion_status?.code === 'TASK_COMPLETED').length}
                                    </span>
                                    <span className="text-gray-600"> of </span>
                                    <span className="font-medium">{recommendation.action_plan_tasks.length}</span>
                                    <span className="text-gray-600"> tasks completed</span>
                                </div>
                            </div>
                        )}

                        {/* Evidence Summary */}
                        {recommendation.closure_evidence && recommendation.closure_evidence.length > 0 && (
                            <div className="bg-gray-50 p-4 rounded-lg mb-4">
                                <h4 className="font-medium mb-2">Evidence Attached</h4>
                                <p className="text-sm text-gray-600">
                                    {recommendation.closure_evidence.length} evidence item(s) uploaded
                                </p>
                            </div>
                        )}

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Closure Summary <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    value={closureSummary}
                                    onChange={(e) => setClosureSummary(e.target.value)}
                                    rows={5}
                                    className="input-field"
                                    placeholder="Summarize the actions taken to address this recommendation..."
                                    required
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Provide a clear summary of remediation activities. This will be reviewed by the validator.
                                </p>
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
                                className="px-4 py-2 bg-cyan-600 text-white rounded hover:bg-cyan-700"
                                disabled={loading}
                            >
                                {loading ? 'Submitting...' : 'Submit for Closure Review'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

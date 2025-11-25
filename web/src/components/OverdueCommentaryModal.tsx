import React, { useState, useEffect } from 'react';
import { overdueCommentaryApi, OverdueComment } from '../api/overdueCommentary';

export type OverdueType = 'PRE_SUBMISSION' | 'VALIDATION_IN_PROGRESS';

interface OverdueCommentaryModalProps {
    requestId: number;
    overdueType: OverdueType;
    modelName?: string;
    currentComment?: OverdueComment | null;
    onClose: () => void;
    onSuccess: () => void;
}

/**
 * Modal for submitting or updating overdue commentary.
 * Shows current comment if exists, and allows creating new commentary.
 */
const OverdueCommentaryModal: React.FC<OverdueCommentaryModalProps> = ({
    requestId,
    overdueType,
    modelName,
    currentComment,
    onClose,
    onSuccess
}) => {
    const [reasonComment, setReasonComment] = useState('');
    const [targetDate, setTargetDate] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [history, setHistory] = useState<OverdueComment[]>([]);
    const [showHistory, setShowHistory] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(false);

    // Set minimum date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const minDate = tomorrow.toISOString().split('T')[0];

    // Load history when toggled
    useEffect(() => {
        if (showHistory && history.length === 0) {
            loadHistory();
        }
    }, [showHistory]);

    const loadHistory = async () => {
        setLoadingHistory(true);
        try {
            const response = await overdueCommentaryApi.getHistoryForRequest(requestId);
            setHistory(response.comment_history);
        } catch (err) {
            console.error('Failed to load history:', err);
        } finally {
            setLoadingHistory(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validate minimum comment length
        if (reasonComment.trim().length < 10) {
            setError('Please provide a more detailed explanation (at least 10 characters).');
            return;
        }

        // Validate date is in the future
        const selectedDate = new Date(targetDate);
        if (selectedDate <= new Date()) {
            setError('Target date must be in the future.');
            return;
        }

        setLoading(true);

        try {
            await overdueCommentaryApi.createForRequest(requestId, {
                overdue_type: overdueType,
                reason_comment: reasonComment.trim(),
                target_date: targetDate
            });
            onSuccess();
            onClose();
        } catch (err: any) {
            const message = err.response?.data?.detail || 'Failed to submit commentary. Please try again.';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateStr: string) => {
        return dateStr.split('T')[0];
    };

    const formatDateTime = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">
                        {overdueType === 'PRE_SUBMISSION'
                            ? 'Submission Delay Explanation'
                            : 'Validation Delay Explanation'}
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 text-2xl"
                        aria-label="Close"
                    >
                        &times;
                    </button>
                </div>

                {modelName && (
                    <p className="text-sm text-gray-600 mb-4">
                        Model: <span className="font-medium">{modelName}</span>
                    </p>
                )}

                {/* Current Comment Display */}
                {currentComment && (
                    <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded">
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-sm font-medium text-blue-900">Current explanation:</span>
                            <span className="text-xs text-blue-700">
                                {formatDateTime(currentComment.created_at)}
                            </span>
                        </div>
                        <p className="text-sm text-blue-800 italic mb-2">
                            "{currentComment.reason_comment}"
                        </p>
                        <p className="text-xs text-blue-700">
                            Target {overdueType === 'PRE_SUBMISSION' ? 'submission' : 'completion'}: {formatDate(currentComment.target_date)}
                        </p>
                        <p className="text-xs text-blue-600 mt-1">
                            By: {currentComment.created_by_user.full_name}
                        </p>
                    </div>
                )}

                {error && (
                    <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    {/* Reason Comment */}
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Reason for Delay *
                        </label>
                        <textarea
                            value={reasonComment}
                            onChange={(e) => setReasonComment(e.target.value)}
                            placeholder={`Explain why the ${overdueType === 'PRE_SUBMISSION' ? 'submission' : 'validation'} is delayed...`}
                            rows={4}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            required
                            minLength={10}
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            Minimum 10 characters. Be specific about the cause and any blockers.
                        </p>
                    </div>

                    {/* Target Date */}
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            {overdueType === 'PRE_SUBMISSION'
                                ? 'Target Submission Date *'
                                : 'Target Completion Date *'}
                        </label>
                        <input
                            type="date"
                            value={targetDate}
                            onChange={(e) => setTargetDate(e.target.value)}
                            min={minDate}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            required
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            When do you expect to {overdueType === 'PRE_SUBMISSION' ? 'submit the documentation' : 'complete the validation'}?
                        </p>
                    </div>

                    {/* History Toggle */}
                    {currentComment && (
                        <div className="mb-4">
                            <button
                                type="button"
                                onClick={() => setShowHistory(!showHistory)}
                                className="text-sm text-blue-600 hover:text-blue-800 underline"
                            >
                                {showHistory ? 'Hide history' : 'Show previous explanations'}
                            </button>

                            {showHistory && (
                                <div className="mt-2 border border-gray-200 rounded max-h-40 overflow-y-auto">
                                    {loadingHistory ? (
                                        <p className="p-3 text-sm text-gray-500">Loading...</p>
                                    ) : history.length === 0 ? (
                                        <p className="p-3 text-sm text-gray-500">No previous explanations</p>
                                    ) : (
                                        <div className="divide-y divide-gray-100">
                                            {history.map((comment) => (
                                                <div key={comment.comment_id} className="p-3 bg-gray-50">
                                                    <div className="flex justify-between items-start mb-1">
                                                        <span className="text-xs text-gray-600">
                                                            {formatDateTime(comment.created_at)}
                                                        </span>
                                                        <span className="text-xs text-gray-500">
                                                            Target: {formatDate(comment.target_date)}
                                                        </span>
                                                    </div>
                                                    <p className="text-sm text-gray-700 italic">
                                                        "{comment.reason_comment}"
                                                    </p>
                                                    <p className="text-xs text-gray-500 mt-1">
                                                        By: {comment.created_by_user.full_name}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex justify-end gap-3 pt-4 border-t">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                            disabled={loading}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                            disabled={loading}
                        >
                            {loading ? 'Submitting...' : (currentComment ? 'Update Explanation' : 'Submit Explanation')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default OverdueCommentaryModal;

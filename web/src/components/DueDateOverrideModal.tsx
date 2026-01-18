import React, { useState, useEffect } from 'react';
import {
    dueDateOverrideApi,
    DueDateOverride,
    CreateDueDateOverrideRequest,
    CurrentDueDateOverrideResponse
} from '../api/dueDateOverride';

interface DueDateOverrideModalProps {
    modelId: number;
    modelName: string;
    overrideData: CurrentDueDateOverrideResponse;
    onClose: () => void;
    onSuccess: () => void;
}

/**
 * Modal for creating or replacing a due date override.
 * Allows admin to accelerate (pull forward) validation due dates.
 */
const DueDateOverrideModal: React.FC<DueDateOverrideModalProps> = ({
    modelId,
    modelName,
    overrideData,
    onClose,
    onSuccess
}) => {
    const [overrideType, setOverrideType] = useState<'ONE_TIME' | 'PERMANENT'>('ONE_TIME');
    const [targetScope, setTargetScope] = useState<'CURRENT_REQUEST' | 'NEXT_CYCLE'>(
        overrideData.current_validation_request_id ? 'CURRENT_REQUEST' : 'NEXT_CYCLE'
    );
    const [overrideDate, setOverrideDate] = useState('');
    const [reason, setReason] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [history, setHistory] = useState<DueDateOverride[]>([]);
    const [showHistory, setShowHistory] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(false);

    const hasActiveOverride = overrideData.has_active_override;
    const currentOverride = overrideData.active_override;
    const policyDate = overrideData.policy_calculated_date;
    const hasOpenValidation = !!overrideData.current_validation_request_id;

    // Set minimum date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const minDate = tomorrow.toISOString().split('T')[0];

    // Max date is one day before policy calculated date
    const maxDate = policyDate
        ? new Date(new Date(policyDate).getTime() - 86400000).toISOString().split('T')[0]
        : undefined;

    // Load history when toggled
    useEffect(() => {
        if (showHistory && history.length === 0) {
            loadHistory();
        }
    }, [showHistory]);

    const loadHistory = async () => {
        setLoadingHistory(true);
        try {
            const response = await dueDateOverrideApi.getHistory(modelId);
            setHistory(response.override_history);
        } catch (err) {
            console.error('Failed to load history:', err);
        } finally {
            setLoadingHistory(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validate reason length
        if (reason.trim().length < 10) {
            setError('Please provide a more detailed reason (at least 10 characters).');
            return;
        }

        // Validate date is in the future
        const selectedDate = new Date(overrideDate);
        if (selectedDate <= new Date()) {
            setError('Override date must be in the future.');
            return;
        }

        // Validate date is earlier than policy date
        if (policyDate && selectedDate >= new Date(policyDate)) {
            setError(`Override date must be earlier than the policy-calculated date (${formatDate(policyDate)}).`);
            return;
        }

        // Validate CURRENT_REQUEST requires open validation
        if (targetScope === 'CURRENT_REQUEST' && !hasOpenValidation) {
            setError('Cannot target current request - no open validation exists.');
            return;
        }

        setLoading(true);

        try {
            const request: CreateDueDateOverrideRequest = {
                override_type: overrideType,
                target_scope: targetScope,
                override_date: overrideDate,
                reason: reason.trim()
            };
            await dueDateOverrideApi.create(modelId, request);
            onSuccess();
            onClose();
        } catch (err: any) {
            const message = err.response?.data?.detail || 'Failed to create override. Please try again.';
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

    const getClearedTypeLabel = (clearedType: string | null): string => {
        switch (clearedType) {
            case 'MANUAL':
                return 'Manually Cleared';
            case 'AUTO_VALIDATION_COMPLETE':
                return 'Auto-cleared (Validation Approved)';
            case 'AUTO_ROLL_FORWARD':
                return 'Rolled Forward';
            case 'AUTO_REQUEST_CANCELLED':
                return 'Auto-voided (Request Cancelled)';
            case 'SUPERSEDED':
                return 'Superseded';
            default:
                return clearedType || 'Unknown';
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">
                        {hasActiveOverride ? 'Replace Due Date Override' : 'Override Due Date'}
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 text-2xl"
                        aria-label="Close"
                    >
                        &times;
                    </button>
                </div>

                <p className="text-sm text-gray-600 mb-4">
                    Model: <span className="font-medium">{modelName}</span>
                </p>

                {/* Warning: replacing existing override */}
                {hasActiveOverride && currentOverride && (
                    <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                        <div className="flex items-start gap-2">
                            <span className="text-yellow-600">&#9888;</span>
                            <div>
                                <p className="text-sm font-medium text-yellow-800">Existing Override Will Be Superseded</p>
                                <p className="text-xs text-yellow-700 mt-1">
                                    Current override: {formatDate(currentOverride.override_date)} ({currentOverride.override_type})
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Policy-calculated date reference */}
                {policyDate && (
                    <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded">
                        <p className="text-sm text-gray-700">
                            <span className="font-medium">Policy-Calculated Due Date:</span>{' '}
                            <span className="text-gray-900">{formatDate(policyDate)}</span>
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                            Override must be earlier than this date (you can only accelerate, not delay)
                        </p>
                    </div>
                )}

                {error && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Override Type */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Override Type
                        </label>
                        <div className="space-y-2">
                            <label className="flex items-start gap-3 p-3 border rounded cursor-pointer hover:bg-gray-50">
                                <input
                                    type="radio"
                                    name="overrideType"
                                    value="ONE_TIME"
                                    checked={overrideType === 'ONE_TIME'}
                                    onChange={() => setOverrideType('ONE_TIME')}
                                    className="mt-1"
                                />
                                <div>
                                    <span className="font-medium">One-Time</span>
                                    <p className="text-xs text-gray-500">
                                        Auto-clears after the targeted validation is approved
                                    </p>
                                </div>
                            </label>
                            <label className="flex items-start gap-3 p-3 border rounded cursor-pointer hover:bg-gray-50">
                                <input
                                    type="radio"
                                    name="overrideType"
                                    value="PERMANENT"
                                    checked={overrideType === 'PERMANENT'}
                                    onChange={() => setOverrideType('PERMANENT')}
                                    className="mt-1"
                                />
                                <div>
                                    <span className="font-medium">Permanent</span>
                                    <p className="text-xs text-gray-500">
                                        Automatically rolls forward each validation cycle
                                    </p>
                                </div>
                            </label>
                        </div>
                    </div>

                    {/* Target Scope */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Target Scope
                        </label>
                        <div className="space-y-2">
                            <label
                                className={`flex items-start gap-3 p-3 border rounded ${
                                    hasOpenValidation
                                        ? 'cursor-pointer hover:bg-gray-50'
                                        : 'opacity-50 cursor-not-allowed bg-gray-100'
                                }`}
                            >
                                <input
                                    type="radio"
                                    name="targetScope"
                                    value="CURRENT_REQUEST"
                                    checked={targetScope === 'CURRENT_REQUEST'}
                                    onChange={() => setTargetScope('CURRENT_REQUEST')}
                                    disabled={!hasOpenValidation}
                                    className="mt-1"
                                />
                                <div>
                                    <span className="font-medium">Current Request</span>
                                    <p className="text-xs text-gray-500">
                                        {hasOpenValidation
                                            ? `Applies to active validation (Request #${overrideData.current_validation_request_id})`
                                            : 'No open validation request exists'}
                                    </p>
                                </div>
                            </label>
                            <label className="flex items-start gap-3 p-3 border rounded cursor-pointer hover:bg-gray-50">
                                <input
                                    type="radio"
                                    name="targetScope"
                                    value="NEXT_CYCLE"
                                    checked={targetScope === 'NEXT_CYCLE'}
                                    onChange={() => setTargetScope('NEXT_CYCLE')}
                                    className="mt-1"
                                />
                                <div>
                                    <span className="font-medium">Next Cycle</span>
                                    <p className="text-xs text-gray-500">
                                        Applies when the next validation request is created
                                    </p>
                                </div>
                            </label>
                        </div>
                    </div>

                    {/* Override Date */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            New Due Date
                        </label>
                        <input
                            type="date"
                            value={overrideDate}
                            onChange={(e) => setOverrideDate(e.target.value)}
                            min={minDate}
                            max={maxDate}
                            required
                            className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            Must be in the future and earlier than the policy-calculated date
                        </p>
                    </div>

                    {/* Reason */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Reason for Override
                        </label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            rows={3}
                            required
                            placeholder="e.g., Model showing poor performance trend, expedited review required..."
                            className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            Minimum 10 characters. This will be logged in the audit trail.
                        </p>
                    </div>

                    {/* History toggle */}
                    <div className="border-t pt-4">
                        <button
                            type="button"
                            onClick={() => setShowHistory(!showHistory)}
                            className="text-sm text-blue-600 hover:text-blue-800"
                        >
                            {showHistory ? 'Hide' : 'Show'} Override History
                        </button>

                        {showHistory && (
                            <div className="mt-3 max-h-48 overflow-y-auto">
                                {loadingHistory ? (
                                    <p className="text-sm text-gray-500">Loading history...</p>
                                ) : history.length === 0 ? (
                                    <p className="text-sm text-gray-500">No previous overrides</p>
                                ) : (
                                    <div className="space-y-2">
                                        {history.map((item) => (
                                            <div
                                                key={item.override_id}
                                                className="p-2 bg-gray-50 rounded text-xs border"
                                            >
                                                <div className="flex justify-between items-start">
                                                    <span className="font-medium">
                                                        {formatDate(item.override_date)} ({item.override_type})
                                                    </span>
                                                    <span className="text-gray-500">
                                                        {formatDateTime(item.created_at)}
                                                    </span>
                                                </div>
                                                <p className="text-gray-600 mt-1 italic">"{item.reason}"</p>
                                                <p className="text-gray-500 mt-1">
                                                    Created by: {item.created_by_user.full_name}
                                                </p>
                                                {item.cleared_type && (
                                                    <p className="text-gray-500">
                                                        Status: {getClearedTypeLabel(item.cleared_type)}
                                                        {item.cleared_at && ` on ${formatDate(item.cleared_at)}`}
                                                    </p>
                                                )}
                                                {item.rolled_from_override_id && (
                                                    <p className="text-gray-500">
                                                        Rolled from override #{item.rolled_from_override_id}
                                                    </p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end gap-3 border-t pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 border rounded text-gray-700 hover:bg-gray-50"
                            disabled={loading}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                            {loading ? 'Creating...' : hasActiveOverride ? 'Replace Override' : 'Create Override'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default DueDateOverrideModal;

import React, { useState, useEffect } from 'react';
import {
    dueDateOverrideApi,
    CurrentDueDateOverrideResponse,
    ClearDueDateOverrideRequest
} from '../api/dueDateOverride';
import DueDateOverrideModal from './DueDateOverrideModal';
import { canManageDueDateOverrides, UserLike } from '../utils/roleUtils';

interface DueDateOverrideSectionProps {
    modelId: number;
    modelName: string;
    user: UserLike | null;
}

/**
 * Section displaying due date override status for a model.
 * Shows current override details and admin controls to create/clear overrides.
 */
const DueDateOverrideSection: React.FC<DueDateOverrideSectionProps> = ({
    modelId,
    modelName,
    user
}) => {
    const [overrideData, setOverrideData] = useState<CurrentDueDateOverrideResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showModal, setShowModal] = useState(false);
    const [showClearConfirm, setShowClearConfirm] = useState(false);
    const [clearReason, setClearReason] = useState('');
    const [clearing, setClearing] = useState(false);

    const canManage = canManageDueDateOverrides(user);

    const fetchOverrideData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await dueDateOverrideApi.getForModel(modelId);
            setOverrideData(data);
        } catch (err) {
            console.error('Failed to load override data:', err);
            setError('Failed to load due date override status');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOverrideData();
    }, [modelId]);

    const handleClearOverride = async () => {
        if (clearReason.trim().length < 10) {
            return;
        }

        setClearing(true);
        try {
            const request: ClearDueDateOverrideRequest = {
                reason: clearReason.trim()
            };
            await dueDateOverrideApi.clear(modelId, request);
            await fetchOverrideData();
            setShowClearConfirm(false);
            setClearReason('');
        } catch (err: any) {
            console.error('Failed to clear override:', err);
            setError(err.response?.data?.detail || 'Failed to clear override');
        } finally {
            setClearing(false);
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

    if (loading) {
        return (
            <div className="bg-white p-4 rounded-lg border border-gray-200">
                <h4 className="text-sm font-medium text-gray-500 mb-2">Due Date Override</h4>
                <p className="text-sm text-gray-400">Loading...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-white p-4 rounded-lg border border-gray-200">
                <h4 className="text-sm font-medium text-gray-500 mb-2">Due Date Override</h4>
                <p className="text-sm text-red-600">{error}</p>
                <button
                    onClick={fetchOverrideData}
                    className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                >
                    Retry
                </button>
            </div>
        );
    }

    if (!overrideData) {
        return null;
    }

    const hasActiveOverride = overrideData.has_active_override;
    const override = overrideData.active_override;
    const policyDate = overrideData.policy_calculated_date;
    const effectiveDate = overrideData.effective_due_date;

    // Check if effective date differs from override (meaning policy is now earlier)
    const policyIsNowEarlier = hasActiveOverride && effectiveDate && override &&
        effectiveDate !== formatDate(override.override_date);

    return (
        <div className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex justify-between items-start mb-3">
                <h4 className="text-sm font-medium text-gray-500">Due Date Override</h4>
                {canManage && (
                    <button
                        onClick={() => setShowModal(true)}
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                        {hasActiveOverride ? 'Replace' : 'Override Due Date'}
                    </button>
                )}
            </div>

            {!hasActiveOverride ? (
                <div className="text-sm text-gray-600">
                    <p>No active override</p>
                    {policyDate && (
                        <p className="text-gray-500 mt-1">
                            Policy-calculated due date: <span className="font-medium">{formatDate(policyDate)}</span>
                        </p>
                    )}
                </div>
            ) : override && (
                <div className="space-y-3">
                    {/* Override Info Card */}
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded">
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-sm font-medium text-amber-900">
                                    Override Active
                                </p>
                                <p className="text-xs text-amber-700 mt-1">
                                    {override.override_type === 'ONE_TIME' ? 'One-Time' : 'Permanent'} &middot;{' '}
                                    {override.target_scope === 'CURRENT_REQUEST' ? 'Current Request' : 'Next Cycle'}
                                </p>
                            </div>
                            {canManage && (
                                <button
                                    onClick={() => setShowClearConfirm(true)}
                                    className="text-xs text-amber-700 hover:text-amber-900 underline"
                                >
                                    Clear
                                </button>
                            )}
                        </div>

                        <div className="mt-3 grid grid-cols-2 gap-3">
                            <div>
                                <p className="text-xs text-amber-600">Override Date</p>
                                <p className="text-sm font-medium text-amber-900">
                                    {formatDate(override.override_date)}
                                </p>
                            </div>
                            <div>
                                <p className="text-xs text-amber-600">Original Policy Date</p>
                                <p className="text-sm font-medium text-amber-900">
                                    {formatDate(override.original_calculated_date)}
                                </p>
                            </div>
                        </div>

                        {/* Show effective date if different from override (policy became earlier) */}
                        {policyIsNowEarlier && effectiveDate && (
                            <div className="mt-3 p-2 bg-yellow-100 border border-yellow-300 rounded">
                                <p className="text-xs text-yellow-800">
                                    <span className="font-medium">Note:</span> Policy now calculates an earlier date.
                                    Effective due date is <span className="font-medium">{effectiveDate}</span>
                                </p>
                            </div>
                        )}

                        <div className="mt-3 text-xs text-amber-700">
                            <p className="italic">"{override.reason}"</p>
                            <p className="mt-1">
                                Created by {override.created_by_user.full_name} on {formatDateTime(override.created_at)}
                            </p>
                        </div>

                        {/* Show if rolled from previous override */}
                        {override.rolled_from_override_id && (
                            <p className="mt-2 text-xs text-amber-600 bg-amber-100 px-2 py-1 rounded inline-block">
                                Auto-rolled from override #{override.rolled_from_override_id}
                            </p>
                        )}

                        {/* Show linked validation request */}
                        {override.validation_request_id && (
                            <p className="mt-2 text-xs text-amber-600">
                                Linked to Validation Request #{override.validation_request_id}
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* Clear Confirmation Dialog */}
            {showClearConfirm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
                        <h3 className="text-lg font-bold mb-4">Clear Due Date Override</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            This will remove the active override. The due date will revert to the policy-calculated date.
                        </p>
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Reason for clearing
                            </label>
                            <textarea
                                value={clearReason}
                                onChange={(e) => setClearReason(e.target.value)}
                                rows={3}
                                placeholder="Explain why you are clearing this override..."
                                className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Minimum 10 characters required
                            </p>
                        </div>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => {
                                    setShowClearConfirm(false);
                                    setClearReason('');
                                }}
                                className="px-4 py-2 border rounded text-gray-700 hover:bg-gray-50"
                                disabled={clearing}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleClearOverride}
                                disabled={clearing || clearReason.trim().length < 10}
                                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                            >
                                {clearing ? 'Clearing...' : 'Clear Override'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Create/Replace Modal */}
            {showModal && overrideData && (
                <DueDateOverrideModal
                    modelId={modelId}
                    modelName={modelName}
                    overrideData={overrideData}
                    onClose={() => setShowModal(false)}
                    onSuccess={fetchOverrideData}
                />
            )}
        </div>
    );
};

export default DueDateOverrideSection;

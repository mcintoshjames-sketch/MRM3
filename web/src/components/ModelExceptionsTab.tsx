import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
    exceptionsApi,
    ModelExceptionListItem,
    ModelExceptionDetail,
    TaxonomyValueBrief,
    EXCEPTION_TYPE_LABELS,
    EXCEPTION_STATUS_CONFIG,
} from '../api/exceptions';
import { canViewAdminDashboard } from '../utils/roleUtils';

interface Props {
    modelId: number;
}

const ModelExceptionsTab: React.FC<Props> = ({ modelId }) => {
    const { user } = useAuth();
    const canViewAdminDashboardFlag = canViewAdminDashboard(user);

    // List state
    const [exceptions, setExceptions] = useState<ModelExceptionListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Filter state
    const [statusFilter, setStatusFilter] = useState<string>('');

    // Modal state
    const [selectedExceptionId, setSelectedExceptionId] = useState<number | null>(null);
    const [exceptionDetail, setExceptionDetail] = useState<ModelExceptionDetail | null>(null);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [showAcknowledgeModal, setShowAcknowledgeModal] = useState(false);
    const [showCloseModal, setShowCloseModal] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);

    // Form state
    const [acknowledgmentNotes, setAcknowledgmentNotes] = useState('');
    const [closureNarrative, setClosureNarrative] = useState('');
    const [closureReasonId, setClosureReasonId] = useState<number | null>(null);
    const [closureReasons, setClosureReasons] = useState<TaxonomyValueBrief[]>([]);
    const [submitting, setSubmitting] = useState(false);

    // Create form state
    const [createExceptionType, setCreateExceptionType] = useState<string>('');
    const [createDescription, setCreateDescription] = useState('');
    const [createInitialStatus, setCreateInitialStatus] = useState<'OPEN' | 'ACKNOWLEDGED'>('OPEN');
    const [createAcknowledgmentNotes, setCreateAcknowledgmentNotes] = useState('');

    // Fetch exceptions
    const fetchExceptions = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await exceptionsApi.getByModel(modelId, statusFilter || undefined);
            setExceptions(data);
        } catch (err) {
            console.error('Error fetching exceptions:', err);
            setError('Failed to load exceptions');
        } finally {
            setLoading(false);
        }
    }, [modelId, statusFilter]);

    useEffect(() => {
        fetchExceptions();
    }, [fetchExceptions]);

    // Fetch closure reasons on mount
    useEffect(() => {
        const fetchClosureReasons = async () => {
            try {
                const reasons = await exceptionsApi.getClosureReasons();
                setClosureReasons(reasons);
            } catch (err) {
                console.error('Error fetching closure reasons:', err);
            }
        };
        fetchClosureReasons();
    }, []);

    // Fetch exception detail
    const fetchExceptionDetail = async (exceptionId: number) => {
        try {
            const detail = await exceptionsApi.get(exceptionId);
            setExceptionDetail(detail);
            return detail;
        } catch (err) {
            console.error('Error fetching exception detail:', err);
            setError('Failed to load exception details');
            return null;
        }
    };

    // Open detail modal
    const handleViewDetail = async (exceptionId: number) => {
        setSelectedExceptionId(exceptionId);
        await fetchExceptionDetail(exceptionId);
        setShowDetailModal(true);
    };

    // Open acknowledge modal
    const handleOpenAcknowledge = async (exceptionId: number) => {
        setSelectedExceptionId(exceptionId);
        setAcknowledgmentNotes('');
        await fetchExceptionDetail(exceptionId);
        setShowAcknowledgeModal(true);
    };

    // Open close modal
    const handleOpenClose = async (exceptionId: number) => {
        setSelectedExceptionId(exceptionId);
        setClosureNarrative('');
        setClosureReasonId(null);
        await fetchExceptionDetail(exceptionId);
        setShowCloseModal(true);
    };

    // Submit acknowledge
    const handleAcknowledge = async () => {
        if (!selectedExceptionId) return;
        setSubmitting(true);
        try {
            await exceptionsApi.acknowledge(selectedExceptionId, {
                notes: acknowledgmentNotes || undefined,
            });
            setShowAcknowledgeModal(false);
            fetchExceptions();
        } catch (err) {
            console.error('Error acknowledging exception:', err);
            setError('Failed to acknowledge exception');
        } finally {
            setSubmitting(false);
        }
    };

    // Submit close
    const handleClose = async () => {
        if (!selectedExceptionId || !closureReasonId || closureNarrative.length < 10) return;
        setSubmitting(true);
        try {
            await exceptionsApi.close(selectedExceptionId, {
                closure_narrative: closureNarrative,
                closure_reason_id: closureReasonId,
            });
            setShowCloseModal(false);
            fetchExceptions();
        } catch (err) {
            console.error('Error closing exception:', err);
            setError('Failed to close exception');
        } finally {
            setSubmitting(false);
        }
    };

    // Close all modals
    const closeModals = () => {
        setShowDetailModal(false);
        setShowAcknowledgeModal(false);
        setShowCloseModal(false);
        setShowCreateModal(false);
        setSelectedExceptionId(null);
        setExceptionDetail(null);
    };

    // Reset create form
    const resetCreateForm = () => {
        setCreateExceptionType('');
        setCreateDescription('');
        setCreateInitialStatus('OPEN');
        setCreateAcknowledgmentNotes('');
    };

    // Submit create exception
    const handleCreate = async () => {
        if (!createExceptionType || createDescription.length < 10) return;
        setSubmitting(true);
        try {
            await exceptionsApi.create({
                model_id: modelId,
                exception_type: createExceptionType,
                description: createDescription,
                initial_status: createInitialStatus,
                acknowledgment_notes: createInitialStatus === 'ACKNOWLEDGED' ? createAcknowledgmentNotes || undefined : undefined,
            });
            setShowCreateModal(false);
            resetCreateForm();
            fetchExceptions();
        } catch (err) {
            console.error('Error creating exception:', err);
            setError('Failed to create exception');
        } finally {
            setSubmitting(false);
        }
    };

    // Format date
    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        return dateStr.split('T')[0];
    };

    // Render status badge
    const renderStatusBadge = (status: string) => {
        const config = EXCEPTION_STATUS_CONFIG[status] || {
            label: status,
            color: 'text-gray-800',
            bgColor: 'bg-gray-100',
        };
        return (
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${config.bgColor} ${config.color}`}>
                {config.label}
            </span>
        );
    };

    // Render exception type label
    const getTypeLabel = (type: string) => {
        return EXCEPTION_TYPE_LABELS[type] || type;
    };

    if (loading && exceptions.length === 0) {
        return (
            <div className="p-6 text-center text-gray-500">
                Loading exceptions...
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Header and Filters */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <h3 className="text-lg font-semibold text-gray-900">
                    Model Exceptions
                </h3>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <label htmlFor="statusFilter" className="text-sm text-gray-600">
                            Status:
                        </label>
                        <select
                            id="statusFilter"
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="input-field py-1 px-2 text-sm w-40"
                        >
                            <option value="">All</option>
                            <option value="OPEN">Open</option>
                            <option value="ACKNOWLEDGED">Acknowledged</option>
                            <option value="CLOSED">Closed</option>
                        </select>
                    </div>
                    {canViewAdminDashboardFlag && (
                        <button
                            onClick={() => {
                                resetCreateForm();
                                setShowCreateModal(true);
                            }}
                            className="btn-primary text-sm py-1 px-3"
                        >
                            + Create Exception
                        </button>
                    )}
                </div>
            </div>

            {/* Error message */}
            {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                    {error}
                </div>
            )}

            {/* Exceptions Table */}
            {exceptions.length === 0 ? (
                <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
                    <p>No exceptions found for this model.</p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Code
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Type
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Status
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Detected
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {exceptions.map((exc) => (
                                <tr key={exc.exception_id} className="hover:bg-gray-50">
                                    <td className="px-4 py-3 text-sm font-mono text-gray-900">
                                        {exc.exception_code}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-700">
                                        {getTypeLabel(exc.exception_type)}
                                    </td>
                                    <td className="px-4 py-3">
                                        {renderStatusBadge(exc.status)}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-500">
                                        {formatDate(exc.detected_at)}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => handleViewDetail(exc.exception_id)}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                View
                                            </button>
                                            {canViewAdminDashboardFlag && exc.status === 'OPEN' && (
                                                <button
                                                    onClick={() => handleOpenAcknowledge(exc.exception_id)}
                                                    className="text-yellow-600 hover:text-yellow-800 text-sm"
                                                >
                                                    Acknowledge
                                                </button>
                                            )}
                                            {canViewAdminDashboardFlag && exc.status !== 'CLOSED' && (
                                                <button
                                                    onClick={() => handleOpenClose(exc.exception_id)}
                                                    className="text-green-600 hover:text-green-800 text-sm"
                                                >
                                                    Close
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Detail Modal */}
            {showDetailModal && exceptionDetail && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                        <div className="px-4 py-2 border-b border-gray-200">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-semibold text-gray-900">
                                    Exception Details
                                </h3>
                                <button
                                    onClick={closeModals}
                                    className="text-gray-400 hover:text-gray-600"
                                >
                                    ✕
                                </button>
                            </div>
                        </div>
                        <div className="px-4 py-2 space-y-4">
                            {/* Basic Info */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-xs text-gray-500 uppercase">Exception Code</label>
                                    <p className="font-mono text-gray-900">{exceptionDetail.exception_code}</p>
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500 uppercase">Status</label>
                                    <div className="mt-1">{renderStatusBadge(exceptionDetail.status)}</div>
                                </div>
                                <div className="col-span-2">
                                    <label className="text-xs text-gray-500 uppercase">Type</label>
                                    <p className="text-gray-900">{getTypeLabel(exceptionDetail.exception_type)}</p>
                                </div>
                                <div className="col-span-2">
                                    <label className="text-xs text-gray-500 uppercase">Description</label>
                                    <p className="text-gray-700">{exceptionDetail.description}</p>
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500 uppercase">Detected At</label>
                                    <p className="text-gray-700">{formatDate(exceptionDetail.detected_at)}</p>
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500 uppercase">Auto-Closed</label>
                                    <p className="text-gray-700">{exceptionDetail.auto_closed ? 'Yes' : 'No'}</p>
                                </div>
                            </div>

                            {/* Acknowledgment Info */}
                            {exceptionDetail.acknowledged_at && (
                                <div className="border-t pt-4">
                                    <h4 className="text-sm font-medium text-gray-900 mb-2">Acknowledgment</h4>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs text-gray-500 uppercase">Acknowledged By</label>
                                            <p className="text-gray-700">
                                                {exceptionDetail.acknowledged_by?.full_name || exceptionDetail.acknowledged_by?.email || '-'}
                                            </p>
                                        </div>
                                        <div>
                                            <label className="text-xs text-gray-500 uppercase">Acknowledged At</label>
                                            <p className="text-gray-700">{formatDate(exceptionDetail.acknowledged_at)}</p>
                                        </div>
                                        {exceptionDetail.acknowledgment_notes && (
                                            <div className="col-span-2">
                                                <label className="text-xs text-gray-500 uppercase">Notes</label>
                                                <p className="text-gray-700">{exceptionDetail.acknowledgment_notes}</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Closure Info */}
                            {exceptionDetail.closed_at && (
                                <div className="border-t pt-4">
                                    <h4 className="text-sm font-medium text-gray-900 mb-2">Closure</h4>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs text-gray-500 uppercase">Closed By</label>
                                            <p className="text-gray-700">
                                                {exceptionDetail.auto_closed
                                                    ? 'System (Auto-Closed)'
                                                    : exceptionDetail.closed_by?.full_name || exceptionDetail.closed_by?.email || '-'}
                                            </p>
                                        </div>
                                        <div>
                                            <label className="text-xs text-gray-500 uppercase">Closed At</label>
                                            <p className="text-gray-700">{formatDate(exceptionDetail.closed_at)}</p>
                                        </div>
                                        <div>
                                            <label className="text-xs text-gray-500 uppercase">Closure Reason</label>
                                            <p className="text-gray-700">
                                                {exceptionDetail.closure_reason?.label || '-'}
                                            </p>
                                        </div>
                                        {exceptionDetail.closure_narrative && (
                                            <div className="col-span-2">
                                                <label className="text-xs text-gray-500 uppercase">Closure Narrative</label>
                                                <p className="text-gray-700">{exceptionDetail.closure_narrative}</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Status History */}
                            {exceptionDetail.status_history && exceptionDetail.status_history.length > 0 && (
                                <div className="border-t pt-4">
                                    <h4 className="text-sm font-medium text-gray-900 mb-2">Status History</h4>
                                    <div className="space-y-2">
                                        {exceptionDetail.status_history.map((history) => (
                                            <div
                                                key={history.history_id}
                                                className="flex items-center justify-between text-sm bg-gray-50 px-3 py-2 rounded"
                                            >
                                                <div className="flex items-center gap-2">
                                                    {history.old_status && (
                                                        <>
                                                            <span className="text-gray-500">{history.old_status}</span>
                                                            <span className="text-gray-400">→</span>
                                                        </>
                                                    )}
                                                    <span className="font-medium">{history.new_status}</span>
                                                </div>
                                                <div className="text-gray-500 text-xs">
                                                    {formatDate(history.changed_at)}
                                                    {history.changed_by && (
                                                        <span> by {history.changed_by.full_name || history.changed_by.email}</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                        <div className="px-4 py-2 border-t border-gray-200 flex justify-end">
                            <button
                                onClick={closeModals}
                                className="btn-secondary"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Acknowledge Modal */}
            {showAcknowledgeModal && exceptionDetail && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                        <div className="px-4 py-2 border-b border-gray-200">
                            <h3 className="text-lg font-semibold text-gray-900">
                                Acknowledge Exception
                            </h3>
                        </div>
                        <div className="px-4 py-2 space-y-4">
                            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                                <p className="text-sm text-yellow-800">
                                    <strong>{exceptionDetail.exception_code}</strong>: {getTypeLabel(exceptionDetail.exception_type)}
                                </p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Notes (Optional)
                                </label>
                                <textarea
                                    value={acknowledgmentNotes}
                                    onChange={(e) => setAcknowledgmentNotes(e.target.value)}
                                    rows={3}
                                    className="input-field"
                                    placeholder="Add any notes about this acknowledgment..."
                                />
                            </div>
                        </div>
                        <div className="px-4 py-2 border-t border-gray-200 flex justify-end gap-3">
                            <button
                                onClick={closeModals}
                                className="btn-secondary"
                                disabled={submitting}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAcknowledge}
                                className="btn-primary bg-yellow-600 hover:bg-yellow-700"
                                disabled={submitting}
                            >
                                {submitting ? 'Acknowledging...' : 'Acknowledge'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Close Modal */}
            {showCloseModal && exceptionDetail && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                        <div className="px-4 py-2 border-b border-gray-200">
                            <h3 className="text-lg font-semibold text-gray-900">
                                Close Exception
                            </h3>
                        </div>
                        <div className="px-4 py-2 space-y-4">
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <p className="text-sm text-blue-800">
                                    <strong>{exceptionDetail.exception_code}</strong>: {getTypeLabel(exceptionDetail.exception_type)}
                                </p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Closure Reason <span className="text-red-500">*</span>
                                </label>
                                <select
                                    value={closureReasonId || ''}
                                    onChange={(e) => setClosureReasonId(e.target.value ? Number(e.target.value) : null)}
                                    className="input-field"
                                    required
                                >
                                    <option value="">Select a reason...</option>
                                    {closureReasons.map((reason) => (
                                        <option key={reason.value_id} value={reason.value_id}>
                                            {reason.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Closure Narrative <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    value={closureNarrative}
                                    onChange={(e) => setClosureNarrative(e.target.value)}
                                    rows={4}
                                    className="input-field"
                                    placeholder="Explain why this exception is being closed (min 10 characters)..."
                                    required
                                />
                                {closureNarrative.length > 0 && closureNarrative.length < 10 && (
                                    <p className="text-xs text-red-500 mt-1">
                                        Narrative must be at least 10 characters ({closureNarrative.length}/10)
                                    </p>
                                )}
                            </div>
                        </div>
                        <div className="px-4 py-2 border-t border-gray-200 flex justify-end gap-3">
                            <button
                                onClick={closeModals}
                                className="btn-secondary"
                                disabled={submitting}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleClose}
                                className="btn-primary bg-green-600 hover:bg-green-700"
                                disabled={submitting || !closureReasonId || closureNarrative.length < 10}
                            >
                                {submitting ? 'Closing...' : 'Close Exception'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Create Exception Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
                        <div className="px-4 py-2 border-b border-gray-200">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-semibold text-gray-900">
                                    Create Exception
                                </h3>
                                <button
                                    onClick={closeModals}
                                    className="text-gray-400 hover:text-gray-600"
                                >
                                    ✕
                                </button>
                            </div>
                        </div>
                        <div className="px-4 py-2 space-y-4">
                            {/* Exception Type */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Exception Type <span className="text-red-500">*</span>
                                </label>
                                <select
                                    value={createExceptionType}
                                    onChange={(e) => setCreateExceptionType(e.target.value)}
                                    className="input-field"
                                    required
                                >
                                    <option value="">Select exception type...</option>
                                    {Object.entries(EXCEPTION_TYPE_LABELS).map(([value, label]) => (
                                        <option key={value} value={value}>
                                            {label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Description */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Description <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    value={createDescription}
                                    onChange={(e) => setCreateDescription(e.target.value)}
                                    rows={4}
                                    className="input-field"
                                    placeholder="Describe the exception in detail (min 10 characters)..."
                                    required
                                />
                                {createDescription.length > 0 && createDescription.length < 10 && (
                                    <p className="text-xs text-red-500 mt-1">
                                        Description must be at least 10 characters ({createDescription.length}/10)
                                    </p>
                                )}
                            </div>

                            {/* Initial Status */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Initial Status
                                </label>
                                <select
                                    value={createInitialStatus}
                                    onChange={(e) => setCreateInitialStatus(e.target.value as 'OPEN' | 'ACKNOWLEDGED')}
                                    className="input-field"
                                >
                                    <option value="OPEN">Open</option>
                                    <option value="ACKNOWLEDGED">Acknowledged</option>
                                </select>
                                <p className="text-xs text-gray-500 mt-1">
                                    Create as "Acknowledged" if this exception is already known and accepted.
                                </p>
                            </div>

                            {/* Acknowledgment Notes (only if ACKNOWLEDGED) */}
                            {createInitialStatus === 'ACKNOWLEDGED' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Acknowledgment Notes
                                    </label>
                                    <textarea
                                        value={createAcknowledgmentNotes}
                                        onChange={(e) => setCreateAcknowledgmentNotes(e.target.value)}
                                        rows={3}
                                        className="input-field"
                                        placeholder="Optional notes about why this exception is being acknowledged..."
                                    />
                                </div>
                            )}
                        </div>
                        <div className="px-4 py-2 border-t border-gray-200 flex justify-end gap-3">
                            <button
                                onClick={closeModals}
                                className="btn-secondary"
                                disabled={submitting}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreate}
                                className="btn-primary"
                                disabled={submitting || !createExceptionType || createDescription.length < 10}
                            >
                                {submitting ? 'Creating...' : 'Create Exception'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ModelExceptionsTab;

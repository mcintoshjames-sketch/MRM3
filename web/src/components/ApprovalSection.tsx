import { useState } from 'react';
import { recommendationsApi, Recommendation } from '../api/recommendations';

interface ApprovalSectionProps {
    recommendation: Recommendation;
    currentUser: { user_id: number; role: string } | null;
    onRefresh: () => void;
}

export default function ApprovalSection({ recommendation, currentUser, onRefresh }: ApprovalSectionProps) {
    const [loading, setLoading] = useState(false);
    const [approvalComments, setApprovalComments] = useState('');
    const [rejectionComments, setRejectionComments] = useState('');
    const [showRejectionForm, setShowRejectionForm] = useState<number | null>(null);
    const [showVoidForm, setShowVoidForm] = useState<number | null>(null);
    const [voidReason, setVoidReason] = useState('');

    const currentStatus = recommendation.current_status?.code || '';
    const approvals = recommendation.approvals || [];

    // Check if user can approve/reject
    const canApprove = (approval: any) => {
        if (currentStatus !== 'REC_PENDING_APPROVAL') return false;
        if (approval.decision) return false; // Already decided

        // Check if user is the approver or an admin
        const isApprover = approval.approver_id === currentUser?.user_id;
        const isAdmin = currentUser?.role === 'Admin';

        return isApprover || isAdmin;
    };

    // Check if user can void an approval (Admin only, on already decided approvals)
    const canVoid = (approval: any) => {
        // Only admins can void
        if (currentUser?.role !== 'Admin') return false;
        // Can only void approvals that have a decision and are not already voided
        if (!approval.decision) return false;
        if (approval.approval_status === 'VOIDED') return false;
        // Can only void when in pending approval status
        if (currentStatus !== 'REC_PENDING_APPROVAL') return false;
        return true;
    };

    const handleApprove = async (approvalId: number) => {
        try {
            setLoading(true);
            await recommendationsApi.submitApproval(recommendation.recommendation_id, approvalId, {
                decision: 'APPROVE',
                comments: approvalComments.trim() || undefined
            });
            setApprovalComments('');
            onRefresh();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to submit approval');
        } finally {
            setLoading(false);
        }
    };

    const handleReject = async (approvalId: number) => {
        if (!rejectionComments.trim()) {
            alert('Please provide a reason for rejection');
            return;
        }

        try {
            setLoading(true);
            await recommendationsApi.submitApproval(recommendation.recommendation_id, approvalId, {
                decision: 'REJECT',
                comments: rejectionComments.trim()
            });
            setRejectionComments('');
            setShowRejectionForm(null);
            onRefresh();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to submit rejection');
        } finally {
            setLoading(false);
        }
    };

    const handleVoid = async (approvalId: number) => {
        if (!voidReason.trim()) {
            alert('Please provide a reason for voiding this approval');
            return;
        }

        try {
            setLoading(true);
            await recommendationsApi.voidApproval(recommendation.recommendation_id, approvalId, voidReason.trim());
            setVoidReason('');
            setShowVoidForm(null);
            onRefresh();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to void approval');
        } finally {
            setLoading(false);
        }
    };

    const getDecisionColor = (decision: string | null, status?: string) => {
        if (status === 'VOIDED') return 'bg-purple-100 text-purple-800';
        switch (decision) {
            case 'APPROVE': return 'bg-green-100 text-green-800';
            case 'REJECT': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-600';
        }
    };

    const getDecisionLabel = (decision: string | null, status?: string) => {
        if (status === 'VOIDED') return 'Voided';
        switch (decision) {
            case 'APPROVE': return 'Approved';
            case 'REJECT': return 'Rejected';
            default: return 'Pending';
        }
    };

    if (approvals.length === 0) {
        return (
            <p className="text-gray-500 text-center py-8">
                No approvals required or closure review not yet submitted.
            </p>
        );
    }

    return (
        <div className="space-y-4">
            {/* Progress Summary */}
            <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">Approval Progress</span>
                    <span className="text-sm text-gray-500">
                        {approvals.filter(a => a.decision === 'APPROVE').length} of {approvals.length} approved
                    </span>
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                    <div
                        className="bg-green-500 h-2 rounded-full"
                        style={{
                            width: `${(approvals.filter(a => a.decision === 'APPROVE').length / approvals.length) * 100}%`
                        }}
                    />
                </div>
            </div>

            {/* Approval List */}
            {approvals.map((approval) => (
                <div key={approval.approval_id} className={`border rounded-lg p-4 ${approval.approval_status === 'VOIDED' ? 'bg-gray-50 border-purple-200' : ''}`}>
                    <div className="flex justify-between items-start">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <span className={`font-medium ${approval.approval_status === 'VOIDED' ? 'text-gray-500' : ''}`}>
                                    {approval.approver?.full_name}
                                </span>
                                <span className={`px-2 py-0.5 text-xs rounded ${getDecisionColor(approval.decision, approval.approval_status)}`}>
                                    {getDecisionLabel(approval.decision, approval.approval_status)}
                                </span>
                            </div>
                            <p className="text-sm text-gray-500">{approval.approver_role?.label}</p>
                        </div>
                        {approval.decided_at && (
                            <span className="text-sm text-gray-500">
                                {approval.decided_at.split('T')[0]}
                            </span>
                        )}
                    </div>

                    {/* Show comments if any */}
                    {approval.comments && (
                        <p className="mt-2 text-sm text-gray-600 italic">
                            "{approval.comments}"
                        </p>
                    )}

                    {/* Show void info if voided */}
                    {approval.approval_status === 'VOIDED' && (
                        <div className="mt-2 pt-2 border-t border-purple-200">
                            <p className="text-sm text-purple-700">
                                <span className="font-medium">Voided by:</span> {approval.voided_by?.full_name}
                                {approval.voided_at && <span className="text-purple-500 ml-2">on {approval.voided_at.split('T')[0]}</span>}
                            </p>
                            {approval.void_reason && (
                                <p className="text-sm text-purple-600 mt-1">
                                    <span className="font-medium">Reason:</span> {approval.void_reason}
                                </p>
                            )}
                        </div>
                    )}

                    {/* Action buttons for pending approvals */}
                    {canApprove(approval) && (
                        <div className="mt-3 pt-3 border-t">
                            {showRejectionForm === approval.approval_id ? (
                                <div className="space-y-2">
                                    <textarea
                                        value={rejectionComments}
                                        onChange={(e) => setRejectionComments(e.target.value)}
                                        rows={2}
                                        className="input-field text-sm"
                                        placeholder="Reason for rejection (required)..."
                                    />
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleReject(approval.approval_id)}
                                            className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                                            disabled={loading}
                                        >
                                            {loading ? 'Submitting...' : 'Confirm Rejection'}
                                        </button>
                                        <button
                                            onClick={() => {
                                                setShowRejectionForm(null);
                                                setRejectionComments('');
                                            }}
                                            className="px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                            disabled={loading}
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <input
                                        type="text"
                                        value={approvalComments}
                                        onChange={(e) => setApprovalComments(e.target.value)}
                                        className="input-field text-sm"
                                        placeholder="Optional comments..."
                                    />
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleApprove(approval.approval_id)}
                                            className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                                            disabled={loading}
                                        >
                                            {loading ? 'Approving...' : 'Approve'}
                                        </button>
                                        <button
                                            onClick={() => setShowRejectionForm(approval.approval_id)}
                                            className="px-3 py-1.5 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                                            disabled={loading}
                                        >
                                            Reject
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Void button for admins on decided approvals */}
                    {canVoid(approval) && (
                        <div className="mt-3 pt-3 border-t">
                            {showVoidForm === approval.approval_id ? (
                                <div className="space-y-2">
                                    <div className="bg-purple-50 border border-purple-200 rounded p-2 mb-2">
                                        <p className="text-sm text-purple-700">
                                            <strong>Warning:</strong> Voiding this approval will reset it to pending status.
                                            The approver will need to submit their decision again.
                                        </p>
                                    </div>
                                    <textarea
                                        value={voidReason}
                                        onChange={(e) => setVoidReason(e.target.value)}
                                        rows={2}
                                        className="input-field text-sm"
                                        placeholder="Reason for voiding this approval (required)..."
                                    />
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleVoid(approval.approval_id)}
                                            className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700"
                                            disabled={loading}
                                        >
                                            {loading ? 'Voiding...' : 'Confirm Void'}
                                        </button>
                                        <button
                                            onClick={() => {
                                                setShowVoidForm(null);
                                                setVoidReason('');
                                            }}
                                            className="px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                            disabled={loading}
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <button
                                    onClick={() => setShowVoidForm(approval.approval_id)}
                                    className="px-3 py-1.5 text-sm bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                                    disabled={loading}
                                >
                                    Void Approval
                                </button>
                            )}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

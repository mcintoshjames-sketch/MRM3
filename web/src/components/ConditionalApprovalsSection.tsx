import { useState, useEffect } from 'react';
import api from '../api/client';
import { isAdmin, UserLike } from '../utils/roleUtils';

interface RequiredApproverRole {
    role_id: number;
    role_name: string;
    description: string | null;
    approval_status: string | null;
    approval_id: number | null;
}

interface AppliedRuleInfo {
    rule_id: number;
    rule_name: string;
    explanation: string;
}

interface ConditionalApprovalsEvaluation {
    required_roles: RequiredApproverRole[];
    rules_applied: AppliedRuleInfo[];
    explanation_summary: string;
}

interface ConditionalApprovalsSectionProps {
    requestId: number;
    currentUser?: UserLike | null;
    onUpdate: () => void;
}

export default function ConditionalApprovalsSection({ requestId, currentUser, onUpdate }: ConditionalApprovalsSectionProps) {
    const [evaluation, setEvaluation] = useState<ConditionalApprovalsEvaluation | null>(null);
    const [loading, setLoading] = useState(true);
    const [showApprovalModal, setShowApprovalModal] = useState(false);
    const [showVoidModal, setShowVoidModal] = useState(false);
    const [selectedApprovalId, setSelectedApprovalId] = useState<number | null>(null);
    const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
    const [approvalData, setApprovalData] = useState({
        approval_status: 'Approved',
        approval_evidence: '',
        comments: ''
    });
    const [voidReason, setVoidReason] = useState('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchEvaluation();
    }, [requestId]);

    const fetchEvaluation = async () => {
        try {
            const response = await api.get(`/validation-workflow/requests/${requestId}/additional-approvals`);
            setEvaluation(response.data);
        } catch (err: any) {
            console.error('Failed to fetch additional approvals:', err);
            setEvaluation({
                required_roles: [],
                rules_applied: [],
                explanation_summary: ''
            });
        } finally {
            setLoading(false);
        }
    };

    const handleSubmitApproval = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!selectedApprovalId || !selectedRoleId) return;

        if (!approvalData.approval_evidence.trim()) {
            setError('Approval evidence is required');
            return;
        }

        try {
            await api.post(`/validation-workflow/approvals/${selectedApprovalId}/submit-additional`, {
                approver_role_id: selectedRoleId,
                approval_status: approvalData.approval_status,
                approval_evidence: approvalData.approval_evidence,
                comments: approvalData.comments || null
            });

            // Reset form
            setShowApprovalModal(false);
            setSelectedApprovalId(null);
            setSelectedRoleId(null);
            setApprovalData({
                approval_status: 'Approved',
                approval_evidence: '',
                comments: ''
            });

            // Refresh data
            fetchEvaluation();
            onUpdate();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit additional approval');
        }
    };

    const handleVoid = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!selectedApprovalId) return;

        if (!voidReason.trim()) {
            setError('Void reason is required');
            return;
        }

        try {
            await api.post(`/validation-workflow/approvals/${selectedApprovalId}/void`, {
                void_reason: voidReason
            });

            // Reset form
            setShowVoidModal(false);
            setSelectedApprovalId(null);
            setVoidReason('');

            // Refresh data
            fetchEvaluation();
            onUpdate();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to void approval requirement');
        }
    };

    if (loading) {
        return <div className="text-center py-4">Loading additional approvals...</div>;
    }

    if (!evaluation || evaluation.required_roles.length === 0) {
        return null; // Don't show section if no additional approvals required
    }

    return (
        <div className="mt-8 border-t pt-6">
            <h3 className="text-lg font-bold mb-4">Additional Model Use Approvals</h3>

            {/* Explanation Summary */}
            {evaluation.explanation_summary && (
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded">
                    <p className="text-sm text-blue-900">{evaluation.explanation_summary}</p>
                </div>
            )}

            {/* Rules Applied */}
            {evaluation.rules_applied.length > 0 && (
                <details className="mb-4">
                    <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
                        View Applied Rules ({evaluation.rules_applied.length})
                    </summary>
                    <div className="mt-2 space-y-2">
                        {evaluation.rules_applied.map((rule) => (
                            <div key={rule.rule_id} className="bg-gray-50 border border-gray-200 rounded p-3">
                                <div className="font-medium text-sm">{rule.rule_name}</div>
                                <pre className="text-xs text-gray-600 mt-1 whitespace-pre-wrap font-sans">
                                    {rule.explanation}
                                </pre>
                            </div>
                        ))}
                    </div>
                </details>
            )}

            {/* Required Approvals */}
            <div className="space-y-3">
                {evaluation.required_roles.map((role) => (
                    <div key={role.role_id} className="border rounded-lg p-4 bg-white">
                        <div className="flex justify-between items-start">
                            <div className="flex-1">
                                <p className="font-medium">{role.role_name}</p>
                                {role.description && (
                                    <p className="text-sm text-gray-500 mt-1">{role.description}</p>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                <span
                                    className={`px-2 py-1 text-xs rounded ${
                                        role.approval_status === 'Approved'
                                            ? 'bg-green-100 text-green-800'
                                            : role.approval_status === 'Rejected'
                                            ? 'bg-red-100 text-red-800'
                                            : role.approval_status === 'Pending'
                                            ? 'bg-yellow-100 text-yellow-800'
                                            : 'bg-gray-100 text-gray-800'
                                    }`}
                                >
                                    {role.approval_status || 'Not Created'}
                                </span>

                                {isAdmin(currentUser) && (
                                    <>
                                        {(!role.approval_status || role.approval_status === 'Pending') && role.approval_id && (
                                            <>
                                                <button
                                                    onClick={() => {
                                                        setSelectedApprovalId(role.approval_id);
                                                        setSelectedRoleId(role.role_id);
                                                        setShowApprovalModal(true);
                                                    }}
                                                    className="btn-primary text-xs"
                                                >
                                                    Submit Approval
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        setSelectedApprovalId(role.approval_id);
                                                        setShowVoidModal(true);
                                                    }}
                                                    className="text-xs px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
                                                >
                                                    Void
                                                </button>
                                            </>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Approval Modal */}
            {showApprovalModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        <h3 className="text-lg font-bold mb-4">Submit Additional Approval</h3>

                        {error && (
                            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmitApproval}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Approval Status *
                                </label>
                                <select
                                    className="input-field"
                                    value={approvalData.approval_status}
                                    onChange={(e) =>
                                        setApprovalData({ ...approvalData, approval_status: e.target.value })
                                    }
                                    required
                                >
                                    <option value="Approved">Approved</option>
                                    <option value="Sent Back">Sent Back for Revision</option>
                                </select>
                                <p className="text-xs text-gray-500 mt-1">
                                    To reject this validation entirely, cancel the validation workflow instead.
                                </p>
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Approval Evidence * <span className="text-xs text-gray-500">(e.g., meeting minutes, email confirmation)</span>
                                </label>
                                <textarea
                                    className="input-field"
                                    rows={3}
                                    value={approvalData.approval_evidence}
                                    onChange={(e) =>
                                        setApprovalData({ ...approvalData, approval_evidence: e.target.value })
                                    }
                                    placeholder="Describe the evidence of this approval (e.g., 'Minutes from MRM Committee meeting on 2025-11-20, Motion #5')"
                                    required
                                />
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Additional Comments
                                </label>
                                <textarea
                                    className="input-field"
                                    rows={2}
                                    value={approvalData.comments}
                                    onChange={(e) =>
                                        setApprovalData({ ...approvalData, comments: e.target.value })
                                    }
                                    placeholder="Optional additional comments"
                                />
                            </div>

                            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
                                <div className="text-sm text-yellow-800">
                                    <p className="font-medium mb-1">Note:</p>
                                    <p>
                                        You are submitting this approval as an Admin on behalf of the approver role.
                                        Ensure you have proper authorization evidence.
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-2">
                                <button type="submit" className="btn-primary">
                                    Submit Approval
                                </button>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowApprovalModal(false);
                                        setSelectedApprovalId(null);
                                        setSelectedRoleId(null);
                                        setError(null);
                                        setApprovalData({
                                            approval_status: 'Approved',
                                            approval_evidence: '',
                                            comments: ''
                                        });
                                    }}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Void Modal */}
            {showVoidModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-lg w-full">
                        <h3 className="text-lg font-bold mb-4">Void Approval Requirement</h3>

                        {error && (
                            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleVoid}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Void Reason *
                                </label>
                                <textarea
                                    className="input-field"
                                    rows={3}
                                    value={voidReason}
                                    onChange={(e) => setVoidReason(e.target.value)}
                                    placeholder="Explain why this approval requirement is being voided"
                                    required
                                />
                            </div>

                            <div className="bg-red-50 border border-red-200 rounded p-3 mb-4">
                                <div className="text-sm text-red-800">
                                    <p className="font-medium mb-1">Warning:</p>
                                    <p>
                                        Voiding this approval requirement will cancel it permanently. This action
                                        is logged and auditable.
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-2">
                                <button type="submit" className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
                                    Void Requirement
                                </button>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowVoidModal(false);
                                        setSelectedApprovalId(null);
                                        setError(null);
                                        setVoidReason('');
                                    }}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

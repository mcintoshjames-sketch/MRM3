import { useState, useEffect } from 'react';
import api from '../api/client';
import { canManageConditionalApprovals, UserLike } from '../utils/roleUtils';

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
    manual_approvals: ManualApprovalSummary[];
}

interface ManualApprovalSummary {
    approval_id: number;
    approval_type: string;
    approval_status: string;
    approver_role_id: number | null;
    approver_role_name: string | null;
    assigned_approver_id: number | null;
    assigned_approver_name: string | null;
    assigned_approver_active: boolean | null;
    manually_added_by_name: string | null;
    manual_add_reason: string | null;
    manually_added_at: string | null;
    voided_at: string | null;
    void_reason: string | null;
}

interface ApproverRole {
    role_id: number;
    role_name: string;
    description: string | null;
    is_active: boolean;
}

interface UserSearchResult {
    user_id: number;
    full_name: string;
    email: string;
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
    const [selectedApprovalRoleId, setSelectedApprovalRoleId] = useState<number | null>(null);
    const [selectedApprovalIsAssignedUser, setSelectedApprovalIsAssignedUser] = useState(false);
    const [approvalData, setApprovalData] = useState({
        approval_status: 'Approved',
        approval_evidence: '',
        comments: ''
    });
    const [voidReason, setVoidReason] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [approvalMode, setApprovalMode] = useState<'role' | 'user'>('role');
    const [approverRoles, setApproverRoles] = useState<ApproverRole[]>([]);
    const [rolesLoading, setRolesLoading] = useState(false);
    const [selectedManualRoleId, setSelectedManualRoleId] = useState<number | null>(null);
    const [selectedManualUser, setSelectedManualUser] = useState<UserSearchResult | null>(null);
    const [userSearchQuery, setUserSearchQuery] = useState('');
    const [userSearchResults, setUserSearchResults] = useState<UserSearchResult[]>([]);
    const [addReason, setAddReason] = useState('');
    const [addError, setAddError] = useState<string | null>(null);

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
                explanation_summary: '',
                manual_approvals: []
            });
        } finally {
            setLoading(false);
        }
    };

    const fetchApproverRoles = async () => {
        setRolesLoading(true);
        try {
            const response = await api.get('/approver-roles/', { params: { is_active: true } });
            setApproverRoles(response.data || []);
        } catch (err) {
            console.error('Failed to fetch approver roles:', err);
            setApproverRoles([]);
        } finally {
            setRolesLoading(false);
        }
    };

    const searchUsers = async (query: string) => {
        try {
            const response = await api.get('/auth/users', {
                params: { search: query, limit: 20 }
            });
            const results = (response.data || []).map((user: any) => ({
                user_id: user.user_id,
                full_name: user.full_name,
                email: user.email
            }));
            setUserSearchResults(results);
        } catch (err) {
            console.error('Failed to search users:', err);
            setUserSearchResults([]);
        }
    };

    useEffect(() => {
        if (showAddModal && canManageConditionalApprovals(currentUser)) {
            fetchApproverRoles();
        }
    }, [showAddModal]);

    useEffect(() => {
        if (!showAddModal || approvalMode !== 'user') return;
        const trimmed = userSearchQuery.trim();
        if (trimmed.length < 2) {
            setUserSearchResults([]);
            return;
        }
        const handle = setTimeout(() => {
            searchUsers(trimmed);
        }, 300);
        return () => clearTimeout(handle);
    }, [userSearchQuery, approvalMode, showAddModal]);

    const handleSubmitApproval = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!selectedApprovalId) return;

        const approvalEvidence = approvalData.approval_evidence.trim();
        const approvalComments = approvalData.comments.trim();
        if (approvalData.approval_status === 'Sent Back' && !approvalComments) {
            setError('Comments are required when sending back for revision');
            return;
        }
        if (!selectedApprovalIsAssignedUser && !approvalEvidence) {
            setError('Approval evidence is required');
            return;
        }

        try {
            const payload: Record<string, any> = {
                approval_status: approvalData.approval_status,
                comments: approvalComments || null
            };
            if (approvalEvidence) {
                payload.approval_evidence = approvalEvidence;
            }
            if (selectedApprovalRoleId !== null) {
                payload.approver_role_id = selectedApprovalRoleId;
            }
            await api.post(`/validation-workflow/approvals/${selectedApprovalId}/submit-additional`, payload);

            // Reset form
            setShowApprovalModal(false);
            setSelectedApprovalId(null);
            setSelectedApprovalRoleId(null);
            setSelectedApprovalIsAssignedUser(false);
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

    const resetAddModal = () => {
        setShowAddModal(false);
        setApprovalMode('role');
        setSelectedManualRoleId(null);
        setSelectedManualUser(null);
        setUserSearchQuery('');
        setUserSearchResults([]);
        setAddReason('');
        setAddError(null);
    };

    const handleAddManualApproval = async (e: React.FormEvent) => {
        e.preventDefault();
        setAddError(null);

        if (!addReason.trim()) {
            setAddError('Reason is required');
            return;
        }

        const payload: Record<string, any> = { reason: addReason.trim() };
        if (approvalMode === 'role') {
            if (!selectedManualRoleId) {
                setAddError('Select an approver role');
                return;
            }
            payload.approver_role_id = selectedManualRoleId;
        } else {
            if (!selectedManualUser) {
                setAddError('Select a user');
                return;
            }
            payload.assigned_approver_id = selectedManualUser.user_id;
        }

        try {
            await api.post(`/validation-workflow/requests/${requestId}/add-manual-approval`, payload);
            resetAddModal();
            fetchEvaluation();
            onUpdate();
        } catch (err: any) {
            setAddError(err.response?.data?.detail || 'Failed to add manual approval');
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

    if (!evaluation) {
        return null;
    }

    const hasConditionalApprovals = evaluation.required_roles.length > 0;
    const hasManualApprovals = evaluation.manual_approvals.length > 0;
    const canManageApprovals = canManageConditionalApprovals(currentUser);
    const isAssignedSubmitter = selectedApprovalIsAssignedUser;
    const isSentBack = approvalData.approval_status === 'Sent Back';

    if (!hasConditionalApprovals && !hasManualApprovals && !canManageApprovals) {
        return null;
    }

    return (
        <div className="mt-8 border-t pt-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold">Additional Model Use Approvals</h3>
                {canManageApprovals && (
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="btn-primary text-xs"
                    >
                        + Add Manual Approval
                    </button>
                )}
            </div>

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

                                {canManageApprovals && (
                                    <>
                                        {(!role.approval_status || role.approval_status === 'Pending') && role.approval_id && (
                                            <>
                                                <button
                                                    onClick={() => {
                                                        setSelectedApprovalId(role.approval_id);
                                                        setSelectedApprovalRoleId(role.role_id);
                                                        setSelectedApprovalIsAssignedUser(false);
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

            {hasManualApprovals && (
                <div className="mt-6">
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Manual Approvals</h4>
                    <div className="space-y-3">
                        {evaluation.manual_approvals.map((approval) => {
                            const isVoided = Boolean(approval.voided_at);
                            const statusLabel = isVoided ? 'Voided' : (approval.approval_status || 'Pending');
                            const isPending = statusLabel === 'Pending';
                            const isAssignedUser = approval.assigned_approver_id !== null
                                && approval.assigned_approver_id === currentUser?.user_id;
                            const canSubmit = !isVoided && isPending && (canManageApprovals || isAssignedUser);
                            const canVoid = !isVoided && isPending && canManageApprovals;
                            const title = approval.approver_role_name
                                ? approval.approver_role_name
                                : approval.assigned_approver_name
                                    ? `Assigned to ${approval.assigned_approver_name}`
                                    : 'Manual Approval';

                            return (
                                <div key={approval.approval_id} className="border rounded-lg p-4 bg-white">
                                    <div className="flex justify-between items-start">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <p className="font-medium">{title}</p>
                                                {approval.assigned_approver_active === false && (
                                                    <span className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded">
                                                        INACTIVE USER
                                                    </span>
                                                )}
                                            </div>
                                            {approval.manually_added_by_name && approval.manually_added_at && (
                                                <p className="text-sm text-gray-500 mt-1">
                                                    Manually added by {approval.manually_added_by_name} on{' '}
                                                    {approval.manually_added_at.split('T')[0]}
                                                </p>
                                            )}
                                            {approval.manual_add_reason && (
                                                <p className="text-sm text-gray-500 mt-1">
                                                    Reason: {approval.manual_add_reason}
                                                </p>
                                            )}
                                            {isVoided && (
                                                <p className="text-sm text-gray-400 mt-1">
                                                    Voided: {approval.void_reason || 'No reason provided'}
                                                </p>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span
                                                className={`px-2 py-1 text-xs rounded ${
                                                    isVoided
                                                        ? 'bg-gray-100 text-gray-800'
                                                        : statusLabel === 'Approved'
                                                            ? 'bg-green-100 text-green-800'
                                                            : statusLabel === 'Sent Back'
                                                                ? 'bg-red-100 text-red-800'
                                                                : 'bg-yellow-100 text-yellow-800'
                                                }`}
                                            >
                                                {statusLabel}
                                            </span>

                                            {canSubmit && (
                                                <button
                                                    onClick={() => {
                                                        setSelectedApprovalId(approval.approval_id);
                                                        setSelectedApprovalRoleId(approval.approver_role_id);
                                                        setSelectedApprovalIsAssignedUser(isAssignedUser);
                                                        setShowApprovalModal(true);
                                                    }}
                                                    className="btn-primary text-xs"
                                                >
                                                    Submit Approval
                                                </button>
                                            )}
                                            {canVoid && (
                                                <button
                                                    onClick={() => {
                                                        setSelectedApprovalId(approval.approval_id);
                                                        setShowVoidModal(true);
                                                    }}
                                                    className="text-xs px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
                                                >
                                                    Void
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {showAddModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        <h3 className="text-lg font-bold mb-4">Add Manual Approval</h3>

                        {addError && (
                            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                                {addError}
                            </div>
                        )}

                        <form onSubmit={handleAddManualApproval}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">Approval Type</label>
                                <div className="flex gap-2">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setApprovalMode('role');
                                            setSelectedManualUser(null);
                                            setUserSearchQuery('');
                                            setUserSearchResults([]);
                                        }}
                                        className={`px-3 py-1.5 text-xs rounded border ${
                                            approvalMode === 'role'
                                                ? 'bg-blue-600 text-white border-blue-600'
                                                : 'bg-white text-gray-700 border-gray-300'
                                        }`}
                                    >
                                        Approver Role / Committee
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setApprovalMode('user');
                                            setSelectedManualRoleId(null);
                                        }}
                                        className={`px-3 py-1.5 text-xs rounded border ${
                                            approvalMode === 'user'
                                                ? 'bg-blue-600 text-white border-blue-600'
                                                : 'bg-white text-gray-700 border-gray-300'
                                        }`}
                                    >
                                        Individual User
                                    </button>
                                </div>
                            </div>

                            {approvalMode === 'role' ? (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Approver Role *</label>
                                    <select
                                        className="input-field"
                                        value={selectedManualRoleId ?? ''}
                                        onChange={(e) =>
                                            setSelectedManualRoleId(e.target.value ? Number(e.target.value) : null)
                                        }
                                        disabled={rolesLoading}
                                    >
                                        <option value="">
                                            {rolesLoading ? 'Loading roles...' : 'Select approver role'}
                                        </option>
                                        {approverRoles.map((role) => (
                                            <option key={role.role_id} value={role.role_id}>
                                                {role.role_name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            ) : (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Assigned User *</label>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            placeholder="Search users by name or email..."
                                            value={userSearchQuery}
                                            onChange={(e) => {
                                                setUserSearchQuery(e.target.value);
                                                setSelectedManualUser(null);
                                            }}
                                            className="input-field"
                                        />
                                        {userSearchResults.length > 0 && (
                                            <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-y-auto">
                                                {userSearchResults.map((user) => (
                                                    <div
                                                        key={user.user_id}
                                                        className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                                                        onClick={() => {
                                                            setSelectedManualUser(user);
                                                            setUserSearchQuery(user.full_name);
                                                            setUserSearchResults([]);
                                                        }}
                                                    >
                                                        <div className="font-medium">{user.full_name}</div>
                                                        <div className="text-sm text-gray-500">{user.email}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {userSearchQuery.trim().length >= 2 && userSearchResults.length === 0 && (
                                            <div className="mt-2 text-xs text-gray-500">No results found</div>
                                        )}
                                    </div>
                                    {selectedManualUser && (
                                        <p className="mt-2 text-sm text-green-600">
                                            ✓ Selected: {selectedManualUser.full_name}
                                        </p>
                                    )}
                                </div>
                            )}

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">Reason *</label>
                                <textarea
                                    className="input-field"
                                    rows={3}
                                    value={addReason}
                                    onChange={(e) => setAddReason(e.target.value)}
                                    placeholder="Provide justification for this manual approval requirement"
                                    required
                                />
                            </div>

                            <div className="flex gap-2">
                                <button type="submit" className="btn-primary">
                                    Add Approval
                                </button>
                                <button
                                    type="button"
                                    onClick={resetAddModal}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

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

                            {!isAssignedSubmitter && (
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
                            )}

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Additional Comments
                                    {isSentBack && <span className="text-red-600"> *</span>}
                                </label>
                                <textarea
                                    className="input-field"
                                    rows={2}
                                    value={approvalData.comments}
                                    onChange={(e) =>
                                        setApprovalData({ ...approvalData, comments: e.target.value })
                                    }
                                    placeholder={
                                        isSentBack
                                            ? 'Provide the reason for sending this approval back'
                                            : 'Optional additional comments'
                                    }
                                    required={isSentBack}
                                />
                            </div>

                            {isAssignedSubmitter ? (
                                <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4">
                                    <div className="text-sm text-blue-800">
                                        <p className="font-medium mb-1">Note:</p>
                                        <p>You are submitting your assigned approval requirement.</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
                                    <div className="text-sm text-yellow-800">
                                        <p className="font-medium mb-1">Note:</p>
                                        <p>
                                            You are submitting this approval as an Admin on behalf of the approver role.
                                            Ensure you have proper authorization evidence.
                                        </p>
                                    </div>
                                </div>
                            )}

                            <div className="flex gap-2">
                                <button type="submit" className="btn-primary">
                                    Submit Approval
                                </button>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowApprovalModal(false);
                                        setSelectedApprovalId(null);
                                        setSelectedApprovalRoleId(null);
                                        setSelectedApprovalIsAssignedUser(false);
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

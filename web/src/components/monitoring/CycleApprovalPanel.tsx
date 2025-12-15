import React from 'react';

// Types
interface RegionRef {
    region_id: number;
    region_name: string;
    region_code: string;
}

interface UserRef {
    user_id: number;
    email: string;
    full_name: string;
}

export interface CycleApproval {
    approval_id: number;
    cycle_id: number;
    approval_type: string;
    region?: RegionRef | null;
    approver?: UserRef | null;
    represented_region?: RegionRef | null;
    is_required: boolean;
    approval_status: string;
    comments?: string | null;
    approved_at?: string | null;
    approval_evidence?: string | null;
    voided_by?: UserRef | null;
    void_reason?: string | null;
    voided_at?: string | null;
    created_at: string;
    can_approve: boolean;
    is_proxy_approval: boolean;
}

export interface CycleApprovalPanelProps {
    approvals: CycleApproval[];
    reportUrl?: string | null;
    canApprove: (approval: CycleApproval) => boolean;
    canVoid: (approval: CycleApproval) => boolean;
    onApprove: (approval: CycleApproval) => void;
    onReject: (approval: CycleApproval) => void;
    onVoid: (approval: CycleApproval) => void;
}

// Helper functions
export const getApprovalProgress = (approvals: CycleApproval[]): { completed: number; total: number } => {
    const required = approvals.filter(a => a.is_required && !a.voided_at);
    const completed = required.filter(a => a.approval_status === 'Approved');
    return { completed: completed.length, total: required.length };
};

const CycleApprovalPanel: React.FC<CycleApprovalPanelProps> = ({
    approvals,
    reportUrl,
    canApprove,
    canVoid,
    onApprove,
    onReject,
    onVoid,
}) => {
    if (!approvals || approvals.length === 0) {
        return (
            <div className="text-gray-500 text-center py-8">
                No approvals configured for this cycle.
            </div>
        );
    }

    const progress = getApprovalProgress(approvals);

    return (
        <div className="space-y-4">
            {/* Report Document for Approvers */}
            {reportUrl && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-center gap-3">
                        <span className="text-2xl">📄</span>
                        <div className="flex-1">
                            <h4 className="font-semibold text-blue-800">Final Monitoring Report</h4>
                            <p className="text-sm text-blue-600 mt-1">
                                Please review the report before providing your approval.
                            </p>
                        </div>
                        <a
                            href={reportUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium flex items-center gap-2"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                            Open Report
                        </a>
                    </div>
                </div>
            )}

            {/* Approvals Header with Progress */}
            <div className="flex items-center justify-between">
                <h4 className="font-semibold">Approvals</h4>
                <div className="flex items-center gap-2">
                    <span className={`text-sm ${
                        progress.completed === progress.total
                            ? 'text-green-600 font-medium'
                            : 'text-gray-600'
                    }`}>
                        {progress.completed} / {progress.total} Complete
                    </span>
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                        <div
                            className={`h-2 rounded-full transition-all ${
                                progress.completed === progress.total
                                    ? 'bg-green-500'
                                    : 'bg-blue-500'
                            }`}
                            style={{ width: progress.total > 0 ? `${(progress.completed / progress.total) * 100}%` : '0%' }}
                        />
                    </div>
                </div>
            </div>

            {/* Approval List */}
            <div className="space-y-2">
                {approvals.map((approval) => (
                    <div key={approval.approval_id} className={`p-3 rounded-lg border ${
                        approval.approval_status === 'Approved' ? 'bg-green-50 border-green-200' :
                        approval.approval_status === 'Rejected' ? 'bg-red-50 border-red-200' :
                        approval.voided_at ? 'bg-gray-50 border-gray-200' :
                        'bg-yellow-50 border-yellow-200'
                    }`}>
                        <div className="flex items-center justify-between">
                            <div className="flex-1">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium">
                                        {approval.approval_type === 'Global' ? 'Global Approval' : `${approval.region?.region_name || 'Regional'} Approval`}
                                    </span>
                                    <span className={`px-2 py-0.5 rounded text-xs ${
                                        approval.approval_status === 'Approved' ? 'bg-green-100 text-green-800' :
                                        approval.approval_status === 'Rejected' ? 'bg-red-100 text-red-800' :
                                        approval.voided_at ? 'bg-gray-100 text-gray-600' :
                                        'bg-yellow-100 text-yellow-800'
                                    }`}>
                                        {approval.voided_at ? 'Voided' : approval.approval_status}
                                    </span>
                                </div>
                                {/* Approval details */}
                                {approval.approver && (
                                    <p className="text-sm text-gray-600 mt-1">
                                        {approval.approval_status === 'Approved' ? 'Approved' : 'Processed'} by {approval.approver.full_name}
                                        {approval.approved_at && ` on ${approval.approved_at.split('T')[0]}`}
                                    </p>
                                )}
                                {approval.comments && (
                                    <p className="text-sm text-gray-700 mt-1 italic">"{approval.comments}"</p>
                                )}
                                {approval.voided_at && approval.void_reason && (
                                    <p className="text-sm text-gray-600 mt-1">
                                        <span className="font-medium">Void reason:</span> {approval.void_reason}
                                    </p>
                                )}
                            </div>
                            {/* Action buttons */}
                            <div className="flex items-center gap-2 ml-4">
                                {canApprove(approval) && (
                                    <>
                                        <button
                                            onClick={() => onApprove(approval)}
                                            className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                                        >
                                            Approve
                                        </button>
                                        <button
                                            onClick={() => onReject(approval)}
                                            className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                                        >
                                            Reject
                                        </button>
                                    </>
                                )}
                                {canVoid(approval) && (
                                    <button
                                        onClick={() => onVoid(approval)}
                                        className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                                    >
                                        Void
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default CycleApprovalPanel;

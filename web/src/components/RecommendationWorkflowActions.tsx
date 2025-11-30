
interface RecommendationWorkflowActionsProps {
    currentStatus: string;
    canFinalize: boolean;
    canSubmitRebuttal: boolean;
    canSubmitActionPlan: boolean;
    canReviewRebuttal: boolean;
    canReviewActionPlan: boolean;
    canAcknowledge: boolean;
    canSubmitForClosure: boolean;
    canReviewClosure: boolean;
    onFinalize: () => void;
    onAcknowledge: () => void;
    onDeclineAcknowledge: () => void;
    onShowRebuttalModal: () => void;
    onShowActionPlanModal: () => void;
    onShowClosureSubmitModal: () => void;
    onShowClosureReviewModal: () => void;
    onRefresh: () => void;
}

export default function RecommendationWorkflowActions({
    currentStatus,
    canFinalize,
    canSubmitRebuttal,
    canSubmitActionPlan,
    canReviewRebuttal,
    canReviewActionPlan,
    canAcknowledge,
    canSubmitForClosure,
    canReviewClosure,
    onFinalize,
    onAcknowledge,
    onDeclineAcknowledge,
    onShowRebuttalModal,
    onShowActionPlanModal,
    onShowClosureSubmitModal,
    onShowClosureReviewModal,
}: RecommendationWorkflowActionsProps) {
    // Helper to get status-specific guidance text
    const getStatusGuidance = () => {
        switch (currentStatus) {
            case 'REC_DRAFT':
                return 'This recommendation is in draft. Finalize to send it to the assigned developer.';
            case 'REC_PENDING_RESPONSE':
                return 'Waiting for developer response. Developer can acknowledge, submit rebuttal, or provide action plan.';
            case 'REC_PENDING_ACKNOWLEDGEMENT':
                return 'Developer needs to acknowledge this recommendation or decline with reason.';
            case 'REC_IN_REBUTTAL':
                return 'A rebuttal has been submitted. Validator review is required.';
            case 'REC_PENDING_ACTION_PLAN':
                return 'Developer needs to submit an action plan for remediation.';
            case 'REC_PENDING_VALIDATOR_REVIEW':
                return 'Action plan submitted. Waiting for validator review and approval.';
            case 'REC_OPEN':
                return 'Recommendation is active. Developer is working on remediation.';
            case 'REC_REWORK_REQUIRED':
                return 'Additional work required based on validator feedback.';
            case 'REC_PENDING_CLOSURE_REVIEW':
                return 'Closure submitted. Waiting for validator review.';
            case 'REC_PENDING_APPROVAL':
                return 'Closure approved. Waiting for final approval(s).';
            default:
                return '';
        }
    };

    const hasActions = canFinalize || canSubmitRebuttal || canSubmitActionPlan ||
        canReviewRebuttal || canReviewActionPlan || canAcknowledge ||
        canSubmitForClosure || canReviewClosure;

    if (!hasActions) {
        const guidance = getStatusGuidance();
        if (!guidance) return null;

        return (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
                <p className="text-sm text-gray-600">{guidance}</p>
            </div>
        );
    }

    return (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="text-sm text-blue-700">
                    {getStatusGuidance()}
                </div>
                <div className="flex flex-wrap gap-2">
                    {/* Draft -> Finalize */}
                    {canFinalize && (
                        <button
                            onClick={onFinalize}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            Finalize & Send
                        </button>
                    )}

                    {/* Pending Response -> Acknowledge */}
                    {canAcknowledge && (
                        <>
                            <button
                                onClick={onAcknowledge}
                                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                            >
                                Acknowledge
                            </button>
                            <button
                                onClick={onDeclineAcknowledge}
                                className="px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200"
                            >
                                Decline
                            </button>
                        </>
                    )}

                    {/* Submit Rebuttal */}
                    {canSubmitRebuttal && (
                        <button
                            onClick={onShowRebuttalModal}
                            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
                        >
                            Submit Rebuttal
                        </button>
                    )}

                    {/* Submit Action Plan */}
                    {canSubmitActionPlan && (
                        <button
                            onClick={onShowActionPlanModal}
                            className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
                        >
                            Submit Action Plan
                        </button>
                    )}

                    {/* Review Rebuttal (Validator) */}
                    {canReviewRebuttal && (
                        <button
                            onClick={onShowRebuttalModal}
                            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
                        >
                            Review Rebuttal
                        </button>
                    )}

                    {/* Review Action Plan (Validator) */}
                    {canReviewActionPlan && (
                        <button
                            onClick={onShowActionPlanModal}
                            className="px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
                        >
                            Review Action Plan
                        </button>
                    )}

                    {/* Submit for Closure */}
                    {canSubmitForClosure && (
                        <button
                            onClick={onShowClosureSubmitModal}
                            className="px-4 py-2 bg-cyan-600 text-white rounded hover:bg-cyan-700"
                        >
                            Submit for Closure
                        </button>
                    )}

                    {/* Review Closure (Validator) */}
                    {canReviewClosure && (
                        <button
                            onClick={onShowClosureReviewModal}
                            className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700"
                        >
                            Review Closure
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

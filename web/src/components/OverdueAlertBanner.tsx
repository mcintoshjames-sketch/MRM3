import React from 'react';

export type OverdueType = 'PRE_SUBMISSION' | 'VALIDATION_IN_PROGRESS';
export type CommentStatus = 'CURRENT' | 'STALE' | 'MISSING';

interface OverdueAlertBannerProps {
    overdueType: OverdueType;
    daysOverdue?: number;
    commentStatus: CommentStatus;
    latestComment?: string | null;
    latestCommentDate?: string | null;
    staleReason?: string | null;
    targetDate?: string | null;
    userRole?: 'owner' | 'developer' | 'delegate' | 'validator' | 'admin';
    needsRequestCreation?: boolean;
    onProvideExplanation: () => void;
    onCreateRequest?: () => void;
}

/**
 * Reusable alert banner for overdue revalidation status.
 * Shows different messaging based on overdue type and comment status.
 */
const OverdueAlertBanner: React.FC<OverdueAlertBannerProps> = ({
    overdueType,
    daysOverdue,
    commentStatus,
    latestComment,
    latestCommentDate,
    staleReason,
    targetDate,
    userRole,
    needsRequestCreation,
    onProvideExplanation,
    onCreateRequest
}) => {
    // Determine banner style based on comment status
    const getBannerStyle = () => {
        if (needsRequestCreation) {
            return 'bg-red-50 border-red-300 text-red-900';
        }
        switch (commentStatus) {
            case 'MISSING':
                return 'bg-red-50 border-red-300 text-red-900';
            case 'STALE':
                return 'bg-yellow-50 border-yellow-300 text-yellow-900';
            case 'CURRENT':
                return 'bg-blue-50 border-blue-300 text-blue-900';
            default:
                return 'bg-gray-50 border-gray-300 text-gray-900';
        }
    };

    // Get icon based on status
    const getIcon = () => {
        if (needsRequestCreation || commentStatus === 'MISSING') {
            return '🔴';
        }
        if (commentStatus === 'STALE') {
            return '⚠️';
        }
        return 'ℹ️';
    };

    // Get title based on type and status
    const getTitle = () => {
        if (needsRequestCreation) {
            return 'REVALIDATION OVERDUE - REQUEST NEEDED';
        }
        if (overdueType === 'PRE_SUBMISSION') {
            return 'SUBMISSION OVERDUE';
        }
        return 'VALIDATION OVERDUE';
    };

    // Format date for display
    const formatDate = (dateStr: string | null | undefined) => {
        if (!dateStr) return null;
        return dateStr.split('T')[0];
    };

    // Get responsible party text
    const getResponsiblePartyText = () => {
        if (overdueType === 'PRE_SUBMISSION') {
            switch (userRole) {
                case 'owner':
                    return 'As the model owner';
                case 'developer':
                    return 'As the model developer';
                case 'delegate':
                    return 'As a model delegate';
                case 'admin':
                    return 'As an administrator';
                default:
                    return 'The model owner/developer';
            }
        } else {
            if (userRole === 'validator') {
                return 'As the assigned validator';
            }
            if (userRole === 'admin') {
                return 'As an administrator';
            }
            return 'The assigned validator';
        }
    };

    // Get action button text
    const getButtonText = () => {
        if (needsRequestCreation) {
            return 'Create Validation Request';
        }
        if (commentStatus === 'MISSING') {
            return 'Provide Explanation';
        }
        return 'Update Explanation';
    };

    return (
        <div className={`border rounded-lg p-4 mb-4 ${getBannerStyle()}`}>
            <div className="flex items-start gap-3">
                <span className="text-xl flex-shrink-0">{getIcon()}</span>
                <div className="flex-grow">
                    <h3 className="font-bold text-lg mb-2">{getTitle()}</h3>

                    {/* Main message */}
                    {needsRequestCreation ? (
                        <p className="mb-3">
                            This model is overdue for revalidation with no active request.
                            To track this overdue revalidation, please create a validation request first.
                        </p>
                    ) : (
                        <p className="mb-3">
                            This {overdueType === 'PRE_SUBMISSION' ? 'submission' : 'validation'} is
                            {daysOverdue !== undefined && <span className="font-semibold"> {daysOverdue} days</span>} past its deadline.
                        </p>
                    )}

                    {/* Current comment display */}
                    {!needsRequestCreation && latestComment && (
                        <div className={`p-3 rounded border mb-3 ${
                            commentStatus === 'STALE'
                                ? 'bg-yellow-100 border-yellow-400'
                                : 'bg-white border-gray-200'
                        }`}>
                            <div className="flex justify-between items-start mb-1">
                                <span className="text-sm font-medium">Current explanation:</span>
                                {latestCommentDate && (
                                    <span className="text-xs text-gray-500">
                                        {formatDate(latestCommentDate)}
                                    </span>
                                )}
                            </div>
                            <p className="text-sm italic">"{latestComment}"</p>
                            {targetDate && (
                                <p className="text-xs mt-1">
                                    Target {overdueType === 'PRE_SUBMISSION' ? 'submission' : 'completion'} date:
                                    <span className="font-medium ml-1">{formatDate(targetDate)}</span>
                                </p>
                            )}
                        </div>
                    )}

                    {/* Stale warning */}
                    {commentStatus === 'STALE' && staleReason && (
                        <div className="p-2 bg-yellow-100 border border-yellow-400 rounded text-sm mb-3">
                            <strong>Update required:</strong> {staleReason}
                        </div>
                    )}

                    {/* Action prompt */}
                    {!needsRequestCreation && commentStatus !== 'CURRENT' && (
                        <p className="text-sm mb-3">
                            {getResponsiblePartyText()}, please provide:
                            <ul className="list-disc ml-5 mt-1">
                                <li>Reason for the delay</li>
                                <li>
                                    {overdueType === 'PRE_SUBMISSION'
                                        ? 'Updated target submission date'
                                        : 'Updated target completion date'}
                                </li>
                            </ul>
                        </p>
                    )}

                    {/* Action button */}
                    <button
                        onClick={needsRequestCreation ? onCreateRequest : onProvideExplanation}
                        className={`px-4 py-2 rounded-md font-medium ${
                            commentStatus === 'CURRENT'
                                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 border border-blue-300'
                                : 'bg-blue-600 text-white hover:bg-blue-700'
                        }`}
                    >
                        {getButtonText()}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default OverdueAlertBanner;

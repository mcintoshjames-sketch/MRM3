export type MRSAReviewStatusCode =
    | 'CURRENT'
    | 'UPCOMING'
    | 'OVERDUE'
    | 'NO_IRP'
    | 'NEVER_REVIEWED'
    | 'NO_REQUIREMENT';

const STATUS_STYLES: Record<MRSAReviewStatusCode, { label: string; className: string }> = {
    CURRENT: {
        label: 'Current',
        className: 'bg-green-100 text-green-800'
    },
    UPCOMING: {
        label: 'Upcoming',
        className: 'bg-amber-100 text-amber-800'
    },
    OVERDUE: {
        label: 'Overdue',
        className: 'bg-red-100 text-red-800'
    },
    NO_IRP: {
        label: 'No IRP',
        className: 'bg-red-200 text-red-900'
    },
    NEVER_REVIEWED: {
        label: 'Never Reviewed',
        className: 'bg-orange-100 text-orange-800'
    },
    NO_REQUIREMENT: {
        label: 'No Requirement',
        className: 'bg-gray-100 text-gray-600'
    }
};

interface MRSAReviewStatusBadgeProps {
    status: MRSAReviewStatusCode | string;
    className?: string;
}

export default function MRSAReviewStatusBadge({ status, className = '' }: MRSAReviewStatusBadgeProps) {
    const config = STATUS_STYLES[status as MRSAReviewStatusCode] || {
        label: status,
        className: 'bg-gray-100 text-gray-700'
    };

    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className} ${className}`}>
            {config.label}
        </span>
    );
}

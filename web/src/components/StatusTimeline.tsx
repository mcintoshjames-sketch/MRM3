import { StatusHistory } from '../api/recommendations';

interface StatusTimelineProps {
    statusHistory: StatusHistory[];
}

export default function StatusTimeline({ statusHistory }: StatusTimelineProps) {
    if (!statusHistory || statusHistory.length === 0) {
        return (
            <p className="text-gray-500 text-center py-8">No status history available.</p>
        );
    }

    // Sort by timestamp descending (most recent first)
    const sortedHistory = [...statusHistory].sort((a, b) =>
        new Date(b.changed_at).getTime() - new Date(a.changed_at).getTime()
    );

    const getStatusColor = (code: string) => {
        switch (code) {
            case 'REC_DRAFT': return 'bg-gray-500';
            case 'REC_PENDING_RESPONSE': return 'bg-blue-500';
            case 'REC_PENDING_ACKNOWLEDGEMENT': return 'bg-indigo-500';
            case 'REC_IN_REBUTTAL': return 'bg-purple-500';
            case 'REC_PENDING_ACTION_PLAN': return 'bg-yellow-500';
            case 'REC_PENDING_VALIDATOR_REVIEW': return 'bg-orange-500';
            case 'REC_OPEN': return 'bg-green-500';
            case 'REC_REWORK_REQUIRED': return 'bg-red-500';
            case 'REC_PENDING_CLOSURE_REVIEW': return 'bg-cyan-500';
            case 'REC_PENDING_APPROVAL': return 'bg-amber-500';
            case 'REC_CLOSED': return 'bg-emerald-500';
            case 'REC_DROPPED': return 'bg-gray-400';
            default: return 'bg-gray-500';
        }
    };

    return (
        <div className="flow-root">
            <ul className="-mb-8">
                {sortedHistory.map((entry, index) => (
                    <li key={entry.history_id}>
                        <div className="relative pb-8">
                            {/* Connecting line */}
                            {index !== sortedHistory.length - 1 && (
                                <span
                                    className="absolute left-4 top-4 -ml-px h-full w-0.5 bg-gray-200"
                                    aria-hidden="true"
                                />
                            )}
                            <div className="relative flex space-x-3">
                                {/* Status dot */}
                                <div>
                                    <span className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${getStatusColor(entry.new_status?.code || '')}`}>
                                        <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            {entry.new_status?.code === 'REC_CLOSED' ? (
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            ) : entry.new_status?.code === 'REC_DROPPED' ? (
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                            ) : (
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            )}
                                        </svg>
                                    </span>
                                </div>
                                {/* Content */}
                                <div className="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5">
                                    <div>
                                        <p className="text-sm font-medium text-gray-900">
                                            {entry.new_status?.label}
                                        </p>
                                        {entry.change_reason && (
                                            <p className="mt-1 text-sm text-gray-500">
                                                {entry.change_reason}
                                            </p>
                                        )}
                                        <p className="mt-1 text-xs text-gray-400">
                                            by {entry.changed_by?.full_name || 'System'}
                                        </p>
                                    </div>
                                    <div className="whitespace-nowrap text-right text-sm text-gray-500">
                                        <time dateTime={entry.changed_at}>
                                            {entry.changed_at?.split('T')[0]}
                                        </time>
                                        <span className="block text-xs text-gray-400">
                                            {entry.changed_at?.split('T')[1]?.substring(0, 5)}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}

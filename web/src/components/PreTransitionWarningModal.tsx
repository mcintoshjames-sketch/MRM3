import { PreTransitionWarning } from '../api/validationWorkflow';

interface PreTransitionWarningModalProps {
    warnings: PreTransitionWarning[];
    canProceed: boolean;
    onClose: () => void;
    onProceed: () => void;
    loading?: boolean;
}

/**
 * Modal displayed when advancing a validation request to Pending Approval stage.
 * Shows warnings about potential issues (e.g., open recommendations, pending attestations)
 * that validators should review before proceeding.
 */
export default function PreTransitionWarningModal({
    warnings,
    canProceed,
    onClose,
    onProceed,
    loading = false
}: PreTransitionWarningModalProps) {
    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'ERROR': return 'bg-red-50 border-red-300';
            case 'WARNING': return 'bg-yellow-50 border-yellow-300';
            case 'INFO': return 'bg-blue-50 border-blue-300';
            default: return 'bg-gray-50 border-gray-300';
        }
    };

    const getSeverityIcon = (severity: string) => {
        switch (severity) {
            case 'ERROR':
                return (
                    <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                );
            case 'WARNING':
                return (
                    <svg className="w-6 h-6 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                );
            case 'INFO':
                return (
                    <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                );
            default:
                return null;
        }
    };

    const getSeverityTextColor = (severity: string) => {
        switch (severity) {
            case 'ERROR': return 'text-red-900';
            case 'WARNING': return 'text-yellow-900';
            case 'INFO': return 'text-blue-900';
            default: return 'text-gray-900';
        }
    };

    const getWarningTypeLabel = (warningType: string) => {
        switch (warningType) {
            case 'PENDING_RECOMMENDATIONS':
                return 'Pending Recommendations';
            case 'UNADDRESSED_ATTESTATIONS':
                return 'Unaddressed Attestations';
            default:
                return warningType.replace(/_/g, ' ');
        }
    };

    const errorWarnings = warnings.filter(w => w.severity === 'ERROR');
    const warningWarnings = warnings.filter(w => w.severity === 'WARNING');
    const infoWarnings = warnings.filter(w => w.severity === 'INFO');

    const renderWarningSection = (
        sectionWarnings: PreTransitionWarning[],
        title: string,
        badgeClass: string,
        titleClass: string
    ) => {
        if (sectionWarnings.length === 0) return null;

        return (
            <div>
                <h3 className={`text-sm font-semibold mb-3 flex items-center gap-2 ${titleClass}`}>
                    <span className={`px-2 py-1 rounded text-xs ${badgeClass}`}>{title}</span>
                    <span>({sectionWarnings.length})</span>
                </h3>
                <div className="space-y-3">
                    {sectionWarnings.map((warning, idx) => (
                        <div key={idx} className={`border rounded-lg p-4 ${getSeverityColor(warning.severity)}`}>
                            <div className="flex items-start gap-3">
                                <div className="flex-shrink-0 mt-0.5">
                                    {getSeverityIcon(warning.severity)}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-2">
                                        <span className="font-semibold text-sm text-gray-900">
                                            {warning.model_name}
                                        </span>
                                        <span className="text-xs bg-white px-2 py-0.5 rounded border border-gray-300">
                                            {getWarningTypeLabel(warning.warning_type)}
                                        </span>
                                    </div>
                                    <p className={`text-sm ${getSeverityTextColor(warning.severity)}`}>
                                        {warning.message}
                                    </p>
                                    {warning.details && Object.keys(warning.details).length > 0 && (
                                        <div className="mt-2 text-xs bg-white bg-opacity-70 rounded p-2 space-y-1">
                                            {Object.entries(warning.details).map(([key, value]) => (
                                                <div key={key} className="flex justify-between">
                                                    <span className="text-gray-600 capitalize">
                                                        {key.replace(/_/g, ' ')}:
                                                    </span>
                                                    <span className="font-medium text-gray-900">
                                                        {String(value)}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-4 py-2 border-b border-gray-200 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {canProceed ? (
                            <svg className="w-8 h-8 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                        ) : (
                            <svg className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                        )}
                        <div>
                            <h2 className="text-xl font-semibold text-gray-900">
                                {canProceed ? 'Pre-Transition Warnings' : 'Cannot Proceed - Issues Found'}
                            </h2>
                            <p className="text-sm text-gray-600 mt-1">
                                {canProceed
                                    ? 'Please review the following before advancing to Pending Approval'
                                    : 'The following issues must be resolved before proceeding'
                                }
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600"
                        disabled={loading}
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Warning List */}
                <div className="flex-1 overflow-y-auto px-4 py-2">
                    <div className="space-y-4">
                        {renderWarningSection(
                            errorWarnings,
                            'BLOCKING ERRORS',
                            'bg-red-100',
                            'text-red-800'
                        )}
                        {renderWarningSection(
                            warningWarnings,
                            'WARNINGS',
                            'bg-yellow-100',
                            'text-yellow-800'
                        )}
                        {renderWarningSection(
                            infoWarnings,
                            'INFORMATION',
                            'bg-blue-100',
                            'text-blue-800'
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="px-4 py-2 border-t border-gray-200 bg-gray-50">
                    <div className="flex items-center justify-between gap-4">
                        <div className="text-sm text-gray-600">
                            {canProceed ? (
                                <p>
                                    These are <strong>advisory warnings</strong>. You may proceed, but consider
                                    resolving these issues before final approval.
                                </p>
                            ) : (
                                <p>
                                    <strong>Cannot proceed</strong> until blocking issues are resolved.
                                </p>
                            )}
                        </div>
                        <div className="flex gap-3">
                            <button
                                onClick={onClose}
                                className="btn-secondary"
                                disabled={loading}
                            >
                                Cancel
                            </button>
                            {canProceed && (
                                <button
                                    onClick={onProceed}
                                    className="btn-primary"
                                    disabled={loading}
                                >
                                    {loading ? 'Processing...' : 'Proceed Anyway'}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

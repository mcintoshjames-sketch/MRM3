import { Link } from 'react-router-dom';

interface VersionAvailable {
    version_id: number;
    version_number: string;
    change_description?: string;
}

interface VersionBlocker {
    type: 'NO_DRAFT_VERSION' | 'MISSING_VERSION_LINK';
    severity: string;
    model_id: number;
    model_name: string;
    message: string;
    available_versions?: VersionAvailable[];
}

interface VersionBlockerModalProps {
    blockers: VersionBlocker[];
    onClose: () => void;
    onSelectVersion: (modelId: number, versionId: number) => void;
}

export default function VersionBlockerModal({
    blockers,
    onClose,
    onSelectVersion
}: VersionBlockerModalProps) {
    const noDraftVersionBlockers = blockers.filter(b => b.type === 'NO_DRAFT_VERSION');
    const missingVersionLinkBlockers = blockers.filter(b => b.type === 'MISSING_VERSION_LINK');

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-red-50">
                    <div className="flex items-center gap-3">
                        <svg className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        <div>
                            <h2 className="text-xl font-semibold text-gray-900">
                                Cannot Create CHANGE Validation
                            </h2>
                            <p className="text-sm text-gray-600 mt-1">
                                CHANGE validations require each model to be linked to a specific version
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Blocker List */}
                <div className="flex-1 overflow-y-auto px-6 py-4">
                    <div className="space-y-6">
                        {/* Models with no DRAFT version - requires submitting model changes first */}
                        {noDraftVersionBlockers.length > 0 && (
                            <div>
                                <h3 className="text-sm font-semibold text-red-800 mb-3 flex items-center gap-2">
                                    <span className="px-2 py-1 bg-red-100 rounded text-xs">NO DRAFT VERSION</span>
                                    <span>({noDraftVersionBlockers.length})</span>
                                </h3>
                                <p className="text-sm text-gray-600 mb-3">
                                    These models have no pending changes (DRAFT versions) to validate.
                                    You must submit model changes first before requesting a CHANGE validation.
                                </p>
                                <div className="space-y-3">
                                    {noDraftVersionBlockers.map((blocker, idx) => (
                                        <div key={idx} className="border border-red-300 rounded-lg p-4 bg-red-50">
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className="font-semibold text-gray-900">
                                                            {blocker.model_name}
                                                        </span>
                                                    </div>
                                                    <p className="text-sm text-red-900">
                                                        {blocker.message}
                                                    </p>
                                                </div>
                                                <Link
                                                    to={`/models/${blocker.model_id}?tab=versions`}
                                                    className="flex-shrink-0 inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-blue-700 bg-blue-100 rounded-lg hover:bg-blue-200 transition-colors"
                                                >
                                                    Submit Model Change
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                                    </svg>
                                                </Link>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Models with DRAFT versions available but not selected */}
                        {missingVersionLinkBlockers.length > 0 && (
                            <div>
                                <h3 className="text-sm font-semibold text-orange-800 mb-3 flex items-center gap-2">
                                    <span className="px-2 py-1 bg-orange-100 rounded text-xs">VERSION NOT SELECTED</span>
                                    <span>({missingVersionLinkBlockers.length})</span>
                                </h3>
                                <p className="text-sm text-gray-600 mb-3">
                                    These models have DRAFT versions available. Select a version for each model to continue.
                                </p>
                                <div className="space-y-3">
                                    {missingVersionLinkBlockers.map((blocker, idx) => (
                                        <div key={idx} className="border border-orange-300 rounded-lg p-4 bg-orange-50">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 mb-3">
                                                    <span className="font-semibold text-gray-900">
                                                        {blocker.model_name}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-orange-900 mb-3">
                                                    {blocker.message}
                                                </p>
                                                {blocker.available_versions && blocker.available_versions.length > 0 && (
                                                    <div className="bg-white rounded border border-orange-200 p-3">
                                                        <label className="block text-xs font-medium text-gray-700 mb-2">
                                                            Select a version:
                                                        </label>
                                                        <select
                                                            className="input-field text-sm"
                                                            defaultValue=""
                                                            onChange={(e) => {
                                                                if (e.target.value) {
                                                                    onSelectVersion(blocker.model_id, parseInt(e.target.value));
                                                                }
                                                            }}
                                                        >
                                                            <option value="">Choose a version...</option>
                                                            {blocker.available_versions.map(v => (
                                                                <option key={v.version_id} value={v.version_id}>
                                                                    {v.version_number}
                                                                    {v.change_description ? ` - ${v.change_description.substring(0, 50)}${v.change_description.length > 50 ? '...' : ''}` : ''}
                                                                </option>
                                                            ))}
                                                        </select>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                    <div className="flex items-center justify-between gap-4">
                        <div className="text-sm text-gray-600">
                            {noDraftVersionBlockers.length > 0 ? (
                                <p>
                                    <strong>Action required:</strong> Submit model changes for models without DRAFT versions,
                                    then return to create the validation.
                                </p>
                            ) : (
                                <p>
                                    <strong>Select versions above</strong> for each model, then close this dialog to continue.
                                </p>
                            )}
                        </div>
                        <button
                            onClick={onClose}
                            className="btn-primary"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export type { VersionBlocker, VersionAvailable };

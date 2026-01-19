interface Props {
    selectedCount: number;
    totalOnPage: number;
    onAssignTag: () => void;
    onRemoveTag: () => void;
    onUpdateFields: () => void;
    onExportSelected: () => void;
    onDeselectAll: () => void;
}

export default function BulkActionsToolbar({
    selectedCount,
    totalOnPage: _totalOnPage,  // Kept for potential future "Select all on page (N)" feature
    onAssignTag,
    onRemoveTag,
    onUpdateFields,
    onExportSelected,
    onDeselectAll
}: Props) {
    void _totalOnPage;  // Suppress unused variable warning
    if (selectedCount === 0) {
        return (
            <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 mb-4 flex items-center justify-between">
                <span className="text-sm text-gray-500">
                    Select models using the checkboxes below to perform bulk actions
                </span>
            </div>
        );
    }

    return (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-blue-800">
                    {selectedCount} model{selectedCount !== 1 ? 's' : ''} selected
                </span>
                <div className="h-4 w-px bg-blue-300"></div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={onAssignTag}
                        className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center gap-1"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                        Assign Tag
                    </button>
                    <button
                        onClick={onRemoveTag}
                        className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors flex items-center gap-1"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                        Remove Tag
                    </button>
                    <button
                        onClick={onUpdateFields}
                        className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition-colors flex items-center gap-1"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        Update Other Fields
                    </button>
                    <button
                        onClick={onExportSelected}
                        className="px-3 py-1.5 text-sm bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors flex items-center gap-1"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Export Selected ({selectedCount})
                    </button>
                </div>
            </div>
            <button
                onClick={onDeselectAll}
                className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
            >
                Clear Selection
            </button>
        </div>
    );
}

/**
 * ColumnPickerModal Component
 *
 * Reusable modal for selecting which columns to display in a table.
 * Works with the useColumnPreferences hook for state management.
 */

import React from 'react';
import { ColumnDefinition, CombinedView } from '../hooks/useColumnPreferences';

interface ColumnPickerModalProps {
    isOpen: boolean;
    onClose: () => void;

    // Column state
    availableColumns: ColumnDefinition[];
    selectedColumns: string[];
    toggleColumn: (key: string) => void;
    selectAllColumns: () => void;
    deselectAllColumns: () => void;

    // View state
    currentViewId: string;
    allViews: Record<string, CombinedView>;
    loadView: (viewId: string) => void;

    // Save view modal trigger
    onSaveAsNew: () => void;
}

export const ColumnPickerModal: React.FC<ColumnPickerModalProps> = ({
    isOpen,
    onClose,
    availableColumns,
    selectedColumns,
    toggleColumn,
    selectAllColumns,
    deselectAllColumns,
    currentViewId,
    allViews,
    loadView,
    onSaveAsNew,
}) => {
    if (!isOpen) return null;

    const defaultViews = Object.values(allViews).filter(v => v.isDefault);
    const myViews = Object.values(allViews).filter(v => !v.isDefault && !v.isPublic);
    const publicViews = Object.values(allViews).filter(v => !v.isDefault && v.isPublic);

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
                <div className="p-6 border-b border-gray-200">
                    <h3 className="text-xl font-bold">Customize Table Columns</h3>
                    <p className="text-sm text-gray-600 mt-1">
                        Select which columns to display in the table. This also affects CSV exports.
                    </p>
                </div>

                <div className="flex-1 overflow-y-auto p-6">
                    {/* View Selector */}
                    <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                        <label className="block text-sm font-medium mb-2">Saved Views</label>
                        <div className="flex gap-2">
                            <select
                                value={currentViewId}
                                onChange={(e) => loadView(e.target.value)}
                                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <optgroup label="Default Views">
                                    {defaultViews.map((view) => (
                                        <option key={view.id} value={view.id}>
                                            {view.name} ({view.columns.length} columns)
                                        </option>
                                    ))}
                                </optgroup>
                                {myViews.length > 0 && (
                                    <optgroup label="My Views">
                                        {myViews.map((view) => (
                                            <option key={view.id} value={view.id}>
                                                {view.name} ({view.columns.length} columns)
                                            </option>
                                        ))}
                                    </optgroup>
                                )}
                                {publicViews.length > 0 && (
                                    <optgroup label="Public Views">
                                        {publicViews.map((view) => (
                                            <option key={view.id} value={view.id}>
                                                {view.name} ({view.columns.length} columns)
                                            </option>
                                        ))}
                                    </optgroup>
                                )}
                            </select>
                            <button
                                onClick={onSaveAsNew}
                                className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm whitespace-nowrap"
                            >
                                Save as New
                            </button>
                        </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="flex gap-2 mb-4">
                        <button
                            onClick={selectAllColumns}
                            className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50"
                        >
                            Select All
                        </button>
                        <button
                            onClick={deselectAllColumns}
                            className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50"
                        >
                            Deselect All
                        </button>
                        <button
                            onClick={() => loadView('default')}
                            className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50"
                        >
                            Reset to Default
                        </button>
                        <div className="ml-auto text-sm text-gray-600">
                            {selectedColumns.length} of {availableColumns.length} columns selected
                        </div>
                    </div>

                    {/* Column Checkboxes */}
                    <div className="grid grid-cols-2 gap-3">
                        {availableColumns.map(col => (
                            <label
                                key={col.key}
                                className="flex items-center gap-2 p-3 border border-gray-200 rounded hover:bg-gray-50 cursor-pointer"
                            >
                                <input
                                    type="checkbox"
                                    checked={selectedColumns.includes(col.key)}
                                    onChange={() => toggleColumn(col.key)}
                                    className="w-4 h-4 text-blue-600 rounded"
                                />
                                <span className="text-sm">{col.label}</span>
                            </label>
                        ))}
                    </div>
                </div>

                <div className="p-6 border-t border-gray-200 flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="btn-primary"
                    >
                        Done
                    </button>
                </div>
            </div>
        </div>
    );
};

interface SaveViewModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: () => void;
    viewName: string;
    setViewName: (name: string) => void;
    viewDescription: string;
    setViewDescription: (desc: string) => void;
    isPublic: boolean;
    setIsPublic: (pub: boolean) => void;
    isEditing: boolean;
}

export const SaveViewModal: React.FC<SaveViewModalProps> = ({
    isOpen,
    onClose,
    onSave,
    viewName,
    setViewName,
    viewDescription,
    setViewDescription,
    isPublic,
    setIsPublic,
    isEditing,
}) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                <h3 className="text-xl font-bold mb-4">
                    {isEditing ? 'Edit View' : 'Save View'}
                </h3>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            View Name *
                        </label>
                        <input
                            type="text"
                            value={viewName}
                            onChange={(e) => setViewName(e.target.value)}
                            placeholder="My Custom View"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description (optional)
                        </label>
                        <textarea
                            value={viewDescription}
                            onChange={(e) => setViewDescription(e.target.value)}
                            placeholder="Describe what this view is for..."
                            rows={2}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={isPublic}
                            onChange={(e) => setIsPublic(e.target.checked)}
                            className="w-4 h-4 text-blue-600 rounded"
                        />
                        <span className="text-sm">
                            Make this view public (visible to all users)
                        </span>
                    </label>
                </div>

                <div className="mt-6 flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-600 hover:text-gray-800"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onSave}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    >
                        {isEditing ? 'Update' : 'Save'}
                    </button>
                </div>
            </div>
        </div>
    );
};

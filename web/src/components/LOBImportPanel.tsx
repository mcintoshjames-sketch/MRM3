import React, { useState, useRef } from 'react';
import { LOBImportPreview, LOBImportResult, lobApi } from '../api/lob';

interface LOBImportPanelProps {
    onImportComplete: () => void;
}

const LOBImportPanel: React.FC<LOBImportPanelProps> = ({ onImportComplete }) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [preview, setPreview] = useState<LOBImportPreview | null>(null);
    const [result, setResult] = useState<LOBImportResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setPreview(null);
            setResult(null);
            setError(null);
        }
    };

    const handlePreview = async () => {
        if (!selectedFile) return;

        setLoading(true);
        setError(null);
        setPreview(null);

        try {
            const previewData = await lobApi.previewImport(selectedFile);
            setPreview(previewData);
        } catch (err: unknown) {
            const errorMsg = err instanceof Error ? err.message : 'Failed to preview import';
            setError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const handleImport = async () => {
        if (!selectedFile) return;

        setLoading(true);
        setError(null);

        try {
            const importResult = await lobApi.importCSV(selectedFile);
            setResult(importResult);
            setPreview(null);
            onImportComplete();
        } catch (err: unknown) {
            const errorMsg = err instanceof Error ? err.message : 'Failed to import';
            setError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async () => {
        try {
            const blob = await lobApi.exportCSV();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `lob_hierarchy_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Export failed:', err);
            alert('Failed to export LOB hierarchy');
        }
    };

    const reset = () => {
        setSelectedFile(null);
        setPreview(null);
        setResult(null);
        setError(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    return (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4">Import / Export LOB Hierarchy</h3>

            {/* Export Section */}
            <div className="mb-6 pb-4 border-b border-gray-200">
                <p className="text-sm text-gray-600 mb-2">
                    Export the current LOB hierarchy to CSV for backup or editing.
                </p>
                <button
                    onClick={handleExport}
                    className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700"
                >
                    Export to CSV
                </button>
            </div>

            {/* Import Section */}
            <div>
                <p className="text-sm text-gray-600 mb-3">
                    Import LOB hierarchy from CSV. The CSV should have columns like: SBU, LOB1, LOB2, LOB3, etc.
                    Each row represents a path in the hierarchy.
                </p>

                {/* File Selection */}
                <div className="flex items-center gap-4 mb-4">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".csv"
                        onChange={handleFileSelect}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    />
                    {selectedFile && (
                        <button
                            onClick={reset}
                            className="text-sm text-gray-500 hover:text-gray-700"
                        >
                            Clear
                        </button>
                    )}
                </div>

                {/* Action Buttons */}
                {selectedFile && !result && (
                    <div className="flex gap-2 mb-4">
                        <button
                            onClick={handlePreview}
                            disabled={loading}
                            className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                            {loading ? 'Processing...' : 'Preview Changes'}
                        </button>
                        {preview && preview.errors.length === 0 && (
                            <button
                                onClick={handleImport}
                                disabled={loading}
                                className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
                            >
                                {loading ? 'Importing...' : 'Confirm Import'}
                            </button>
                        )}
                    </div>
                )}

                {/* Error Display */}
                {error && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                        {error}
                    </div>
                )}

                {/* Preview Results */}
                {preview && (
                    <div className="space-y-4">
                        {/* Detected Columns */}
                        <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                            <p className="text-sm font-medium text-blue-800 mb-1">
                                Detected Columns ({preview.max_depth} levels)
                            </p>
                            <p className="text-sm text-blue-700">
                                {preview.detected_columns.join(' → ')}
                            </p>
                        </div>

                        {/* Validation Errors */}
                        {preview.errors.length > 0 && (
                            <div className="p-3 bg-red-50 border border-red-200 rounded">
                                <p className="text-sm font-medium text-red-800 mb-2">
                                    Validation Errors ({preview.errors.length})
                                </p>
                                <ul className="text-sm text-red-700 list-disc list-inside max-h-32 overflow-y-auto">
                                    {preview.errors.map((err, i) => (
                                        <li key={i}>{err}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Summary */}
                        <div className="grid grid-cols-3 gap-4">
                            <div className="p-3 bg-green-50 border border-green-200 rounded text-center">
                                <p className="text-2xl font-bold text-green-700">{preview.to_create.length}</p>
                                <p className="text-sm text-green-600">To Create</p>
                            </div>
                            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded text-center">
                                <p className="text-2xl font-bold text-yellow-700">{preview.to_update.length}</p>
                                <p className="text-sm text-yellow-600">To Update</p>
                            </div>
                            <div className="p-3 bg-gray-50 border border-gray-200 rounded text-center">
                                <p className="text-2xl font-bold text-gray-700">{preview.to_skip.length}</p>
                                <p className="text-sm text-gray-600">Unchanged</p>
                            </div>
                        </div>

                        {/* Details */}
                        {preview.to_create.length > 0 && (
                            <div>
                                <p className="text-sm font-medium text-gray-700 mb-2">New LOB Units to Create:</p>
                                <div className="max-h-40 overflow-y-auto border border-gray-200 rounded">
                                    <table className="min-w-full text-sm">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-3 py-2 text-left">Code</th>
                                                <th className="px-3 py-2 text-left">Name</th>
                                                <th className="px-3 py-2 text-left">Parent</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {preview.to_create.map((item, i) => (
                                                <tr key={i} className="border-t">
                                                    <td className="px-3 py-2">{String(item.code)}</td>
                                                    <td className="px-3 py-2">{String(item.name)}</td>
                                                    <td className="px-3 py-2 text-gray-500">{String(item.parent_code || '(root)')}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Import Results */}
                {result && (
                    <div className="space-y-4">
                        <div className="p-3 bg-green-50 border border-green-200 rounded">
                            <p className="text-lg font-medium text-green-800 mb-2">Import Complete!</p>
                            <div className="grid grid-cols-3 gap-4 text-center">
                                <div>
                                    <p className="text-xl font-bold text-green-700">{result.created_count}</p>
                                    <p className="text-sm text-green-600">Created</p>
                                </div>
                                <div>
                                    <p className="text-xl font-bold text-yellow-700">{result.updated_count}</p>
                                    <p className="text-sm text-yellow-600">Updated</p>
                                </div>
                                <div>
                                    <p className="text-xl font-bold text-gray-700">{result.skipped_count}</p>
                                    <p className="text-sm text-gray-600">Skipped</p>
                                </div>
                            </div>
                        </div>

                        {result.errors.length > 0 && (
                            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                                <p className="text-sm font-medium text-yellow-800 mb-2">
                                    Warnings ({result.errors.length})
                                </p>
                                <ul className="text-sm text-yellow-700 list-disc list-inside">
                                    {result.errors.map((err, i) => (
                                        <li key={i}>{err}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <button
                            onClick={reset}
                            className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
                        >
                            Import Another File
                        </button>
                    </div>
                )}

                {/* CSV Format Help */}
                <div className="mt-6 p-3 bg-gray-50 border border-gray-200 rounded">
                    <p className="text-sm font-medium text-gray-700 mb-2">Expected CSV Format:</p>
                    <pre className="text-xs text-gray-600 bg-white p-2 rounded border overflow-x-auto">
{`SBU,LOB1,LOB2,LOB3
BCM,Global Markets,Equities,Derivatives
BCM,Global Markets,Equities,Cash Equities
BCM,Global Markets,FX,
CB,Retail Lending,Mortgage,
CB,Retail Lending,Auto Finance,`}
                    </pre>
                    <p className="text-xs text-gray-500 mt-2">
                        Empty cells indicate the end of the path for that row.
                        Column headers should be: SBU, LOB1, LOB2, LOB3, etc.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default LOBImportPanel;

import React, { useState, useRef } from 'react';
import api from '../api/client';

interface MetricSnapshot {
    original_metric_id: number | null;
    kpm_name: string;
    evaluation_type: string;
}

interface Model {
    model_id: number;
    model_name: string;
}

interface ImportPreviewRow {
    row_number: number;
    model_id: number;
    model_name: string;
    metric_id: number;
    metric_name: string;
    value: number | null;
    outcome: string | null;
    narrative: string | null;
    action: 'create' | 'update' | 'skip';
    error: string | null;
}

interface ImportPreview {
    valid_rows: ImportPreviewRow[];
    error_rows: ImportPreviewRow[];
    summary: {
        total_rows: number;
        create_count: number;
        update_count: number;
        skip_count: number;
        error_count: number;
    };
}

interface ImportResult {
    success: boolean;
    created: number;
    updated: number;
    skipped: number;
    errors: number;
    error_messages: string[];
}

interface MonitoringCSVImportProps {
    cycleId: number;
    metrics: MetricSnapshot[];
    models: Model[];
    onImportComplete: () => void;
    onClose: () => void;
}

const MonitoringCSVImport: React.FC<MonitoringCSVImportProps> = ({
    cycleId,
    metrics,
    models,
    onImportComplete,
    onClose,
}) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [preview, setPreview] = useState<ImportPreview | null>(null);
    const [result, setResult] = useState<ImportResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Step tracking: 'upload' | 'preview' | 'result'
    const currentStep = result ? 'result' : preview ? 'preview' : 'upload';

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
            const formData = new FormData();
            formData.append('file', selectedFile);

            const response = await api.post(
                `/monitoring/cycles/${cycleId}/results/import?dry_run=true`,
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );
            setPreview(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to preview import');
        } finally {
            setLoading(false);
        }
    };

    const handleImport = async () => {
        if (!selectedFile) return;

        setLoading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);

            const response = await api.post(
                `/monitoring/cycles/${cycleId}/results/import?dry_run=false`,
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );
            setResult(response.data);
            setPreview(null);
            onImportComplete();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to import');
        } finally {
            setLoading(false);
        }
    };

    const downloadTemplate = () => {
        // Generate CSV template with headers and all model/metric combinations
        // Include human-readable names (ignored on import) for user convenience
        const headers = ['model_id', 'model_name', 'metric_id', 'metric_name', 'value', 'outcome', 'narrative'];
        const validMetrics = metrics.filter(m => m.original_metric_id !== null);

        // Generate a row for every model/metric combination
        const dataRows = models.flatMap((model) =>
            validMetrics.map((metric) => [
                model.model_id,
                `"${model.model_name.replace(/"/g, '""')}"`,  // Escape quotes in CSV
                metric.original_metric_id,
                `"${metric.kpm_name.replace(/"/g, '""')}"`,   // Escape quotes in CSV
                '',  // value - to be filled
                '',  // outcome - for qualitative metrics (GREEN/YELLOW/RED)
                ''   // narrative - optional
            ].join(','))
        );

        const csv = [headers.join(','), ...dataRows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `monitoring_results_template_cycle_${cycleId}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
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
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
                    <div>
                        <h3 className="text-lg font-bold">Import Results from CSV</h3>
                        <p className="text-sm text-gray-600">
                            Bulk import monitoring results for this cycle
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 p-1"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Step Indicator */}
                <div className="px-4 py-3 border-b bg-gray-50">
                    <div className="flex items-center gap-4">
                        <StepIndicator step={1} label="Upload" active={currentStep === 'upload'} completed={currentStep !== 'upload'} />
                        <div className="flex-1 h-0.5 bg-gray-300"></div>
                        <StepIndicator step={2} label="Preview" active={currentStep === 'preview'} completed={currentStep === 'result'} />
                        <div className="flex-1 h-0.5 bg-gray-300"></div>
                        <StepIndicator step={3} label="Complete" active={currentStep === 'result'} completed={false} />
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    {error && (
                        <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                            {error}
                        </div>
                    )}

                    {/* Step 1: Upload */}
                    {currentStep === 'upload' && (
                        <div className="space-y-6">
                            {/* Instructions */}
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <h4 className="font-medium text-blue-900 mb-2">CSV Format Requirements</h4>
                                <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
                                    <li>Required columns: <code className="bg-blue-100 px-1">model_id</code>, <code className="bg-blue-100 px-1">metric_id</code>, <code className="bg-blue-100 px-1">value</code></li>
                                    <li>Optional columns: <code className="bg-blue-100 px-1">outcome</code> (for qualitative metrics), <code className="bg-blue-100 px-1">narrative</code></li>
                                    <li>Reference columns (ignored on import): <code className="bg-blue-100 px-1">model_name</code>, <code className="bg-blue-100 px-1">metric_name</code></li>
                                    <li>For qualitative metrics, use outcome labels: GREEN, YELLOW, or RED</li>
                                    <li>First row must contain column headers</li>
                                </ul>
                            </div>

                            {/* Template Download */}
                            <div className="flex items-center gap-4">
                                <button
                                    onClick={downloadTemplate}
                                    className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                                >
                                    <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                    Download Template
                                </button>
                                <span className="text-sm text-gray-500">
                                    Pre-filled with your plan's models and metrics
                                </span>
                            </div>

                            {/* File Upload */}
                            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8">
                                <div className="text-center">
                                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                    <div className="mt-4">
                                        <label className="cursor-pointer">
                                            <span className="text-blue-600 hover:text-blue-500 font-medium">
                                                Choose a file
                                            </span>
                                            <span className="text-gray-500"> or drag and drop</span>
                                            <input
                                                ref={fileInputRef}
                                                type="file"
                                                accept=".csv"
                                                onChange={handleFileSelect}
                                                className="hidden"
                                            />
                                        </label>
                                    </div>
                                    <p className="mt-1 text-sm text-gray-500">CSV file up to 10MB</p>
                                </div>
                            </div>

                            {/* Selected File */}
                            {selectedFile && (
                                <div className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3">
                                    <div className="flex items-center gap-3">
                                        <svg className="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        <div>
                                            <p className="font-medium">{selectedFile.name}</p>
                                            <p className="text-sm text-gray-500">
                                                {(selectedFile.size / 1024).toFixed(1)} KB
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => {
                                            setSelectedFile(null);
                                            if (fileInputRef.current) fileInputRef.current.value = '';
                                        }}
                                        className="text-red-600 hover:text-red-700 text-sm"
                                    >
                                        Remove
                                    </button>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 2: Preview */}
                    {currentStep === 'preview' && preview && (
                        <div className="space-y-4">
                            {/* Summary */}
                            <div className="grid grid-cols-5 gap-3">
                                <SummaryCard label="Total Rows" value={preview.summary.total_rows} color="gray" />
                                <SummaryCard label="To Create" value={preview.summary.create_count} color="green" />
                                <SummaryCard label="To Update" value={preview.summary.update_count} color="blue" />
                                <SummaryCard label="To Skip" value={preview.summary.skip_count} color="gray" />
                                <SummaryCard label="Errors" value={preview.summary.error_count} color="red" />
                            </div>

                            {/* Error Rows */}
                            {preview.error_rows.length > 0 && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                    <h4 className="font-medium text-red-900 mb-2">
                                        Rows with Errors ({preview.error_rows.length})
                                    </h4>
                                    <div className="max-h-40 overflow-y-auto">
                                        <table className="w-full text-sm">
                                            <thead className="text-left text-red-800">
                                                <tr>
                                                    <th className="py-1 pr-4">Row</th>
                                                    <th className="py-1 pr-4">Model</th>
                                                    <th className="py-1 pr-4">Metric</th>
                                                    <th className="py-1">Error</th>
                                                </tr>
                                            </thead>
                                            <tbody className="text-red-700">
                                                {preview.error_rows.map((row) => (
                                                    <tr key={row.row_number}>
                                                        <td className="py-1 pr-4">{row.row_number}</td>
                                                        <td className="py-1 pr-4">{row.model_name || row.model_id}</td>
                                                        <td className="py-1 pr-4">{row.metric_name || row.metric_id}</td>
                                                        <td className="py-1">{row.error}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* Valid Rows Preview */}
                            {preview.valid_rows.length > 0 && (
                                <div>
                                    <h4 className="font-medium text-gray-900 mb-2">
                                        Preview ({preview.valid_rows.length} valid rows)
                                    </h4>
                                    <div className="max-h-60 overflow-y-auto border rounded-lg">
                                        <table className="w-full text-sm">
                                            <thead className="bg-gray-50 sticky top-0">
                                                <tr>
                                                    <th className="text-left py-2 px-3">Model</th>
                                                    <th className="text-left py-2 px-3">Metric</th>
                                                    <th className="text-left py-2 px-3">Value</th>
                                                    <th className="text-left py-2 px-3">Outcome</th>
                                                    <th className="text-left py-2 px-3">Action</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y">
                                                {preview.valid_rows.slice(0, 50).map((row) => (
                                                    <tr key={`${row.model_id}-${row.metric_id}`}>
                                                        <td className="py-2 px-3">{row.model_name}</td>
                                                        <td className="py-2 px-3">{row.metric_name}</td>
                                                        <td className="py-2 px-3 font-mono">
                                                            {row.value !== null ? row.value : '-'}
                                                        </td>
                                                        <td className="py-2 px-3">
                                                            {row.outcome && (
                                                                <span className={`px-2 py-0.5 rounded text-xs ${
                                                                    row.outcome === 'GREEN' ? 'bg-green-100 text-green-800' :
                                                                    row.outcome === 'YELLOW' ? 'bg-yellow-100 text-yellow-800' :
                                                                    row.outcome === 'RED' ? 'bg-red-100 text-red-800' :
                                                                    'bg-gray-100 text-gray-800'
                                                                }`}>
                                                                    {row.outcome}
                                                                </span>
                                                            )}
                                                        </td>
                                                        <td className="py-2 px-3">
                                                            <span className={`px-2 py-0.5 rounded text-xs ${
                                                                row.action === 'create' ? 'bg-green-100 text-green-800' :
                                                                row.action === 'update' ? 'bg-blue-100 text-blue-800' :
                                                                'bg-gray-100 text-gray-800'
                                                            }`}>
                                                                {row.action}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                        {preview.valid_rows.length > 50 && (
                                            <div className="py-2 px-3 text-center text-sm text-gray-500 bg-gray-50">
                                                ... and {preview.valid_rows.length - 50} more rows
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 3: Result */}
                    {currentStep === 'result' && result && (
                        <div className="text-center py-8">
                            {result.success ? (
                                <>
                                    <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                                        <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                    <h4 className="text-xl font-bold text-green-900 mb-2">Import Successful!</h4>
                                    <div className="text-gray-600 space-y-1">
                                        <p>{result.created} results created</p>
                                        <p>{result.updated} results updated</p>
                                        {result.skipped > 0 && (
                                            <p className="text-gray-500">{result.skipped} rows skipped</p>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                                        <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </div>
                                    <h4 className="text-xl font-bold text-red-900 mb-2">Import Failed</h4>
                                    {result.error_messages.length > 0 && (
                                        <div className="mt-4 text-left bg-red-50 rounded-lg p-4 max-w-md mx-auto">
                                            <ul className="text-sm text-red-700 space-y-1">
                                                {result.error_messages.map((msg, i) => (
                                                    <li key={i}>• {msg}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t bg-gray-50 flex justify-between">
                    <button
                        onClick={currentStep === 'result' ? onClose : reset}
                        disabled={loading}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 disabled:opacity-50"
                    >
                        {currentStep === 'result' ? 'Close' : 'Cancel'}
                    </button>

                    <div className="flex gap-2">
                        {currentStep === 'preview' && (
                            <button
                                onClick={reset}
                                disabled={loading}
                                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 disabled:opacity-50"
                            >
                                Back
                            </button>
                        )}

                        {currentStep === 'upload' && (
                            <button
                                onClick={handlePreview}
                                disabled={!selectedFile || loading}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                            >
                                {loading && <Spinner />}
                                Preview Import
                            </button>
                        )}

                        {currentStep === 'preview' && preview && (
                            <button
                                onClick={handleImport}
                                disabled={loading || preview.summary.error_count > 0 || preview.valid_rows.length === 0}
                                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                            >
                                {loading && <Spinner />}
                                Import {preview.valid_rows.length} Results
                            </button>
                        )}

                        {currentStep === 'result' && result?.success && (
                            <button
                                onClick={onClose}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                            >
                                Done
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

// Helper Components
const StepIndicator: React.FC<{
    step: number;
    label: string;
    active: boolean;
    completed: boolean;
}> = ({ step, label, active, completed }) => (
    <div className="flex items-center gap-2">
        <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                completed
                    ? 'bg-green-600 text-white'
                    : active
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-600'
            }`}
        >
            {completed ? '✓' : step}
        </div>
        <span className={`text-sm ${active ? 'text-blue-600 font-medium' : 'text-gray-500'}`}>
            {label}
        </span>
    </div>
);

const SummaryCard: React.FC<{
    label: string;
    value: number;
    color: 'green' | 'blue' | 'red' | 'gray';
}> = ({ label, value, color }) => {
    const colorClasses = {
        green: 'bg-green-50 text-green-700 border-green-200',
        blue: 'bg-blue-50 text-blue-700 border-blue-200',
        red: 'bg-red-50 text-red-700 border-red-200',
        gray: 'bg-gray-50 text-gray-700 border-gray-200',
    };

    return (
        <div className={`rounded-lg border p-3 text-center ${colorClasses[color]}`}>
            <div className="text-2xl font-bold">{value}</div>
            <div className="text-xs">{label}</div>
        </div>
    );
};

const Spinner: React.FC = () => (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
);

export default MonitoringCSVImport;

import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

interface MetricInfo {
    metricName: string;
    modelName: string;
    numericValue: number | null;
    outcome: string | null;
    thresholds: {
        yellow_min: number | null;
        yellow_max: number | null;
        red_min: number | null;
        red_max: number | null;
    };
}

interface BreachAnnotationPanelProps {
    isOpen: boolean;
    resultId: number | null;
    metricInfo: MetricInfo | null;
    existingNarrative: string;
    readOnly?: boolean;
    linkedRecommendations?: LinkedRecommendation[];
    linkedRecommendationsLoading?: boolean;
    linkedRecommendationsError?: string | null;
    onSave: (narrative: string) => Promise<void>;
    onValueChange?: (newValue: number | null) => Promise<void>;
    onCreateRecommendation?: () => void;
    onClose: () => void;
}

interface LinkedRecommendation {
    recommendation_id: number;
    recommendation_code: string;
    title: string;
    current_status: { code: string; label: string };
    priority: { code: string; label: string };
    current_target_date: string;
}

const BreachAnnotationPanel: React.FC<BreachAnnotationPanelProps> = ({
    isOpen,
    resultId: _resultId, // Reserved for future use - parent uses this to track which result is being edited
    metricInfo,
    existingNarrative,
    readOnly = false,
    linkedRecommendations = [],
    linkedRecommendationsLoading = false,
    linkedRecommendationsError = null,
    onSave,
    onValueChange,
    onCreateRecommendation,
    onClose,
}) => {
    const [narrative, setNarrative] = useState(existingNarrative);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Value editing state
    const [isEditingValue, setIsEditingValue] = useState(false);
    const [editValue, setEditValue] = useState('');
    const [savingValue, setSavingValue] = useState(false);
    const [valueError, setValueError] = useState<string | null>(null);
    const valueInputRef = useRef<HTMLInputElement>(null);

    // Sync narrative when panel opens with existing narrative
    useEffect(() => {
        if (isOpen) {
            setNarrative(existingNarrative);
            setError(null);
            setIsEditingValue(false);
            setEditValue('');
            setValueError(null);
            // Focus textarea when panel opens
            setTimeout(() => textareaRef.current?.focus(), 100);
        }
    }, [isOpen, existingNarrative]);

    // Start editing the value
    const handleStartEditValue = () => {
        if (readOnly) return;
        if (metricInfo && metricInfo.numericValue !== null) {
            setEditValue(metricInfo.numericValue.toString());
        } else {
            setEditValue('');
        }
        setIsEditingValue(true);
        setValueError(null);
        setTimeout(() => valueInputRef.current?.focus(), 50);
    };

    // Cancel value editing
    const handleCancelEditValue = () => {
        setIsEditingValue(false);
        setEditValue('');
        setValueError(null);
    };

    // Save the new value
    const handleSaveValue = async () => {
        if (readOnly) return;
        if (!onValueChange) return;

        const trimmed = editValue.trim();
        let newValue: number | null = null;

        if (trimmed !== '') {
            newValue = parseFloat(trimmed);
            if (isNaN(newValue)) {
                setValueError('Please enter a valid number');
                return;
            }
        }

        setSavingValue(true);
        setValueError(null);

        try {
            await onValueChange(newValue);
            setIsEditingValue(false);
            setEditValue('');
        } catch (err: any) {
            setValueError(err.message || 'Failed to save value');
        } finally {
            setSavingValue(false);
        }
    };

    // Handle save
    const handleSave = async () => {
        if (readOnly) return;
        if (!narrative.trim()) {
            setError('Breach explanation is required');
            return;
        }

        setSaving(true);
        setError(null);

        try {
            await onSave(narrative);
            onClose();
        } catch (err: any) {
            setError(err.message || 'Failed to save explanation');
        } finally {
            setSaving(false);
        }
    };

    // Handle keyboard shortcuts
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Escape') {
            onClose();
        } else if (!readOnly && e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            handleSave();
        }
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/20 z-40"
                onClick={onClose}
            />

            {/* Slide-in Panel */}
            <div
                className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50 flex flex-col transform transition-transform duration-200 ease-out"
                style={{ transform: isOpen ? 'translateX(0)' : 'translateX(100%)' }}
                onKeyDown={handleKeyDown}
            >
                {/* Header */}
                <div className="p-4 border-b bg-red-50">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-bold text-red-900">
                            {readOnly ? 'Breach Details' : 'Breach Explanation Required'}
                        </h3>
                        <button
                            onClick={onClose}
                            className="text-gray-500 hover:text-gray-700 p-1"
                            aria-label="Close panel"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {/* Metric Info */}
                    {metricInfo && (
                        <div className="space-y-3">
                            <div>
                                <span className="text-xs text-gray-500">Metric</span>
                                <p className="font-semibold text-gray-900">{metricInfo.metricName}</p>
                            </div>

                            <div>
                                <span className="text-xs text-gray-500">Model</span>
                                <p className="font-medium text-gray-800">{metricInfo.modelName}</p>
                            </div>

                            {/* Value and Outcome */}
                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <span className="text-xs text-gray-500">Value</span>
                                    {isEditingValue ? (
                                        <div className="mt-1">
                                            <div className="flex items-center gap-2">
                                                <input
                                                    ref={valueInputRef}
                                                    type="text"
                                                    className={`w-24 px-2 py-1 font-mono text-lg border rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                                                        valueError ? 'border-red-500' : 'border-gray-300'
                                                    }`}
                                                    value={editValue}
                                                    onChange={(e) => setEditValue(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') {
                                                            e.preventDefault();
                                                            handleSaveValue();
                                                        } else if (e.key === 'Escape') {
                                                            handleCancelEditValue();
                                                        }
                                                    }}
                                                    disabled={savingValue}
                                                    placeholder="0.0000"
                                                />
                                                <button
                                                    onClick={handleSaveValue}
                                                    disabled={savingValue}
                                                    className="p-1 text-green-600 hover:text-green-800 disabled:opacity-50"
                                                    title="Save"
                                                >
                                                    {savingValue ? (
                                                        <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                                        </svg>
                                                    ) : (
                                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    )}
                                                </button>
                                                <button
                                                    onClick={handleCancelEditValue}
                                                    disabled={savingValue}
                                                    className="p-1 text-gray-500 hover:text-gray-700 disabled:opacity-50"
                                                    title="Cancel"
                                                >
                                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                    </svg>
                                                </button>
                                            </div>
                                            {valueError && (
                                                <p className="text-red-600 text-xs mt-1">{valueError}</p>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2">
                                            <p className="font-mono text-lg">
                                                {metricInfo.numericValue !== null
                                                    ? metricInfo.numericValue.toFixed(4)
                                                    : '-'}
                                            </p>
                                            {onValueChange && !readOnly && (
                                                <button
                                                    onClick={handleStartEditValue}
                                                    className="p-1 text-gray-400 hover:text-blue-600"
                                                    title="Edit value"
                                                >
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                                    </svg>
                                                </button>
                                            )}
                                        </div>
                                    )}
                                </div>
                                <div>
                                    <span className="text-xs text-gray-500">Outcome</span>
                                    <p className={`inline-flex px-2 py-0.5 rounded text-sm font-medium ${
                                        metricInfo.outcome === 'RED'
                                            ? 'bg-red-100 text-red-800'
                                            : metricInfo.outcome === 'YELLOW'
                                            ? 'bg-yellow-100 text-yellow-800'
                                            : 'bg-green-100 text-green-800'
                                    }`}>
                                        {metricInfo.outcome || 'N/A'}
                                    </p>
                                </div>
                            </div>

                            {/* Threshold Info */}
                            <div className="bg-gray-50 rounded-lg p-3">
                                <span className="text-xs text-gray-500 block mb-2">Thresholds</span>
                                <div className="flex flex-wrap gap-2 text-xs">
                                    {metricInfo.thresholds.red_min !== null && (
                                        <span className="px-2 py-1 bg-red-100 text-red-700 rounded">
                                            RED: &lt; {metricInfo.thresholds.red_min}
                                        </span>
                                    )}
                                    {metricInfo.thresholds.red_max !== null && (
                                        <span className="px-2 py-1 bg-red-100 text-red-700 rounded">
                                            RED: &gt; {metricInfo.thresholds.red_max}
                                        </span>
                                    )}
                                    {(metricInfo.thresholds.yellow_min !== null || metricInfo.thresholds.yellow_max !== null) && (
                                        <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded">
                                            YELLOW: {metricInfo.thresholds.yellow_min ?? '-'} to {metricInfo.thresholds.yellow_max ?? '-'}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Linked Recommendations */}
                    <div className="border border-gray-200 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                            <h4 className="text-sm font-semibold text-gray-800">Linked Recommendations</h4>
                            <span className="text-xs text-gray-500">{linkedRecommendations.length}</span>
                        </div>
                        {linkedRecommendationsLoading ? (
                            <p className="text-xs text-gray-500">Loading recommendations...</p>
                        ) : linkedRecommendationsError ? (
                            <p className="text-xs text-red-600">{linkedRecommendationsError}</p>
                        ) : linkedRecommendations.length === 0 ? (
                            <p className="text-xs text-gray-500">No linked recommendations yet.</p>
                        ) : (
                            <div className="space-y-2">
                                {linkedRecommendations.map((rec) => (
                                    <div key={rec.recommendation_id} className="rounded border border-gray-100 bg-gray-50 p-2">
                                        <div className="flex items-center justify-between gap-2">
                                            <Link
                                                to={`/recommendations/${rec.recommendation_id}`}
                                                className="text-sm font-medium text-blue-600 hover:text-blue-800"
                                            >
                                                {rec.recommendation_code}
                                            </Link>
                                            <span className="text-xs text-gray-500">
                                                {rec.current_target_date?.split('T')[0] || '-'}
                                            </span>
                                        </div>
                                        <p className="text-xs text-gray-700 mt-1">{rec.title}</p>
                                        <div className="flex flex-wrap gap-2 mt-2 text-[11px]">
                                            <span className="px-2 py-0.5 rounded bg-gray-200 text-gray-700">
                                                {rec.current_status?.label || rec.current_status?.code}
                                            </span>
                                            <span className="px-2 py-0.5 rounded bg-gray-200 text-gray-700">
                                                {rec.priority?.label || rec.priority?.code}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Divider */}
                    <hr className="border-gray-200" />

                    {/* Explanation Textarea */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Breach Explanation {!readOnly && <span className="text-red-500">*</span>}
                        </label>
                        <p className="text-xs text-gray-500 mb-2">
                            {readOnly
                                ? 'Explanation recorded for this breach.'
                                : 'Explain why this metric breached its threshold and any remediation actions planned.'}
                        </p>
                        <textarea
                            ref={textareaRef}
                            className={`w-full border rounded-lg px-3 py-2 text-sm h-40 resize-none focus:ring-2 focus:ring-red-500 focus:border-red-500 ${
                                error ? 'border-red-500' : 'border-gray-300'
                            } ${readOnly ? 'bg-gray-50' : ''}`}
                            value={narrative}
                            onChange={(e) => setNarrative(e.target.value)}
                            placeholder={readOnly ? 'No breach explanation provided.' : 'Enter breach explanation...'}
                            readOnly={readOnly}
                        />
                        {error && (
                            <p className="text-red-600 text-xs mt-1">{error}</p>
                        )}
                        {!readOnly && (
                            <p className="text-xs text-gray-400 mt-1">
                                Tip: Press Ctrl+Enter to save
                            </p>
                        )}
                    </div>

                    {/* Guidance */}
                    {!readOnly && (
                        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                            <div className="flex gap-2">
                                <span className="text-amber-600">💡</span>
                                <div className="text-xs text-amber-800">
                                    <p className="font-medium mb-1">Explanation should include:</p>
                                    <ul className="list-disc list-inside space-y-0.5">
                                        <li>Root cause of the breach</li>
                                        <li>Impact assessment</li>
                                        <li>Remediation actions (if any)</li>
                                        <li>Expected resolution timeline</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t bg-gray-50 flex justify-between">
                    {/* Create Recommendation button - only for RED outcomes */}
                    <div>
                        {onCreateRecommendation && metricInfo?.outcome === 'RED' && (
                            <button
                                onClick={onCreateRecommendation}
                                disabled={saving}
                                className="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 text-sm disabled:opacity-50 flex items-center gap-2"
                                title="Create a recommendation to track remediation of this breach"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                Create Recommendation
                            </button>
                        )}
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={onClose}
                            disabled={saving}
                            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 text-sm disabled:opacity-50"
                        >
                            {readOnly ? 'Close' : 'Cancel'}
                        </button>
                        {!readOnly && (
                            <button
                                onClick={handleSave}
                                disabled={saving || !narrative.trim()}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm disabled:opacity-50 flex items-center gap-2"
                            >
                                {saving && (
                                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                )}
                                {saving ? 'Saving...' : 'Save Explanation'}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
};

export default BreachAnnotationPanel;

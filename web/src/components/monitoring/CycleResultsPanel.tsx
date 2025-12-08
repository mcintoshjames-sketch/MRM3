import React from 'react';

// Types
export interface UserRef {
    user_id: number;
    email: string;
    full_name: string;
}

export interface Model {
    model_id: number;
    model_name: string;
}

export interface OutcomeValue {
    value_id: number;
    code: string;
    label: string;
}

export interface MetricSnapshot {
    snapshot_id: number;
    original_metric_id: number | null;
    kpm_id: number;
    kpm_name: string;
    kpm_category_name: string | null;
    evaluation_type: string;
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
    qualitative_guidance: string | null;
    sort_order: number;
}

export interface VersionDetail {
    version_id: number;
    plan_id: number;
    version_number: number;
    version_name: string | null;
    effective_date: string;
    published_at: string;
    is_active: boolean;
    metric_snapshots: MetricSnapshot[];
}

export interface MonitoringCycle {
    cycle_id: number;
    plan_id: number;
    period_start_date: string;
    period_end_date: string;
    submission_due_date: string;
    report_due_date: string;
    status: string;
    version_locked_at?: string | null;
}

export interface ResultFormData {
    metric_id: number;
    snapshot_id?: number;
    kpm_name: string;
    evaluation_type: string;
    numeric_value: string;
    outcome_value_id: number | null;
    narrative: string;
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
    qualitative_guidance: string | null;
    calculatedOutcome: string | null;
    existingResultId: number | null;
    dirty: boolean;
    skipped: boolean;
    previousValue: number | null;
    previousOutcome: string | null;
    previousPeriod: string | null;
    model_id: number | null;
}

export interface CycleResultsPanelProps {
    cycle: MonitoringCycle;
    versionDetail: VersionDetail | null;
    resultForms: ResultFormData[];
    models: Model[];
    outcomeValues: OutcomeValue[];
    selectedModel: number | null;
    existingResultsMode: 'none' | 'plan-level' | 'model-specific';
    loadingResults: boolean;
    savingResult: number | null;
    deletingResult: number | null;
    resultsError: string | null;
    onResultChange: (index: number, field: string, value: string | number | null) => void;
    onSkipToggle: (index: number, skipped: boolean) => void;
    onSaveResult: (index: number) => void;
    onDeleteResult: (index: number) => void;
    onModelChange: (modelId: number | null) => void;
    onClose: () => void;
}

// Helper functions
export const formatPeriod = (start: string, end: string): string => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const startMonth = startDate.toLocaleString('default', { month: 'short' });
    const endMonth = endDate.toLocaleString('default', { month: 'short' });
    const year = endDate.getFullYear();
    return `${startMonth} - ${endMonth} ${year}`;
};

export const getOutcomeColor = (outcome: string | null): string => {
    switch (outcome) {
        case 'GREEN': return 'bg-green-100 text-green-800 border-green-300';
        case 'YELLOW': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
        case 'RED': return 'bg-red-100 text-red-800 border-red-300';
        default: return 'bg-gray-100 text-gray-600 border-gray-300';
    }
};

export const getOutcomeIcon = (outcome: string | null): string => {
    switch (outcome) {
        case 'GREEN': return '●';
        case 'YELLOW': return '●';
        case 'RED': return '●';
        default: return '○';
    }
};

const CycleResultsPanel: React.FC<CycleResultsPanelProps> = ({
    cycle,
    versionDetail,
    resultForms,
    models,
    outcomeValues,
    selectedModel,
    existingResultsMode,
    loadingResults,
    savingResult,
    deletingResult,
    resultsError,
    onResultChange,
    onSkipToggle,
    onSaveResult,
    onDeleteResult,
    onModelChange,
    onClose,
}) => {
    return (
        <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
                <div>
                    <h3 className="text-lg font-bold">Enter Results</h3>
                    <p className="text-sm text-gray-600">
                        {formatPeriod(cycle.period_start_date, cycle.period_end_date)}
                    </p>
                </div>
                <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            {/* Version Info Banner */}
            {versionDetail && (
                <div className="px-4 py-3 bg-blue-50 border-b border-blue-200">
                    <div className="flex items-center gap-2">
                        <span className="text-blue-600 font-medium">
                            Using v{versionDetail.version_number} metrics configuration
                        </span>
                        {cycle.version_locked_at && (
                            <span className="text-blue-500 text-sm">
                                (locked {cycle.version_locked_at.split('T')[0]})
                            </span>
                        )}
                    </div>
                    <p className="text-sm text-blue-600">
                        Effective: {versionDetail.effective_date} | {versionDetail.metric_snapshots.length} metrics
                    </p>
                </div>
            )}

            {!versionDetail && !loadingResults && (
                <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
                    <p className="text-amber-700 text-sm">
                        Using live plan metrics (not yet locked to a version)
                    </p>
                </div>
            )}

            {/* Model Selector - Only show when plan has multiple models */}
            {models && models.length > 1 && (
                <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-3">
                            <label className="text-sm font-medium text-gray-700">
                                Enter Results For:
                            </label>
                            <select
                                value={selectedModel === null ? 'plan-level' : selectedModel}
                                onChange={(e) => {
                                    const value = e.target.value;
                                    onModelChange(value === 'plan-level' ? null : parseInt(value));
                                }}
                                className="border rounded-md px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                                <option
                                    value="plan-level"
                                    disabled={existingResultsMode === 'model-specific'}
                                >
                                    Plan Level (All Models){existingResultsMode === 'model-specific' ? ' - locked' : ''}
                                </option>
                                {models.map((model) => (
                                    <option
                                        key={model.model_id}
                                        value={model.model_id}
                                        disabled={existingResultsMode === 'plan-level'}
                                    >
                                        {model.model_name} (ID: {model.model_id}){existingResultsMode === 'plan-level' ? ' - locked' : ''}
                                    </option>
                                ))}
                            </select>
                            {/* Mode indicator badge */}
                            {existingResultsMode !== 'none' && (
                                <span className={`px-2 py-0.5 text-xs rounded-full ${
                                    existingResultsMode === 'plan-level'
                                        ? 'bg-blue-100 text-blue-700'
                                        : 'bg-purple-100 text-purple-700'
                                }`}>
                                    {existingResultsMode === 'plan-level' ? 'Plan-level mode' : 'Model-specific mode'}
                                </span>
                            )}
                        </div>
                        {/* Contextual guidance */}
                        <p className="text-xs text-gray-500">
                            {existingResultsMode === 'none' ? (
                                selectedModel === null
                                    ? 'Results will apply to all models in this plan. Once saved, you cannot switch to model-specific results.'
                                    : `Results specific to ${models.find((m) => m.model_id === selectedModel)?.model_name}. Once saved, you cannot switch to plan-level results.`
                            ) : existingResultsMode === 'plan-level' ? (
                                'This cycle has plan-level results. Model-specific entry is disabled to maintain consistency.'
                            ) : (
                                'This cycle has model-specific results. Plan-level entry is disabled to maintain consistency.'
                            )}
                        </p>
                    </div>
                </div>
            )}

            {/* Error display */}
            {resultsError && (
                <div className="px-4 py-3 bg-red-100 border-b border-red-300">
                    <p className="text-red-700 text-sm">{resultsError}</p>
                </div>
            )}

            {/* Metrics List */}
            <div className="flex-1 overflow-y-auto p-4">
                {loadingResults ? (
                    <div className="text-center py-12 text-gray-500">Loading metrics...</div>
                ) : resultForms.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">No metrics configured for this plan.</div>
                ) : (
                    <div className="space-y-6">
                        {/* Progress indicator */}
                        <div className="flex items-center gap-4 mb-4">
                            <span className="text-sm text-gray-600">
                                Progress{models && models.length > 1 && selectedModel !== null
                                    ? ` (${models.find((m) => m.model_id === selectedModel)?.model_name})`
                                    : models && models.length > 1
                                    ? ' (Plan Level)'
                                    : ''}: {resultForms.filter(f => f.existingResultId !== null).length} / {resultForms.length} entered
                            </span>
                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                                <div
                                    className="bg-green-500 h-2 rounded-full transition-all"
                                    style={{ width: `${(resultForms.filter(f => f.existingResultId !== null).length / resultForms.length) * 100}%` }}
                                />
                            </div>
                        </div>

                        {resultForms.map((form, index) => (
                            <div key={form.metric_id} className="border rounded-lg p-4 bg-white shadow-sm">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h4 className="font-semibold text-lg">{form.kpm_name}</h4>
                                        <span className={`inline-block mt-1 px-2 py-0.5 text-xs rounded-full ${
                                            form.evaluation_type === 'Quantitative' ? 'bg-blue-100 text-blue-800' :
                                            form.evaluation_type === 'Qualitative' ? 'bg-purple-100 text-purple-800' :
                                            'bg-green-100 text-green-800'
                                        }`}>
                                            {form.evaluation_type}
                                        </span>
                                    </div>
                                    <div className={`px-3 py-1.5 rounded-lg border text-sm font-medium ${getOutcomeColor(form.calculatedOutcome)}`}>
                                        <span className="mr-1">{getOutcomeIcon(form.calculatedOutcome)}</span>
                                        {form.calculatedOutcome || 'Not Set'}
                                    </div>
                                </div>

                                {/* Quantitative Metric */}
                                {form.evaluation_type === 'Quantitative' && (
                                    <QuantitativeMetricForm
                                        form={form}
                                        index={index}
                                        onResultChange={onResultChange}
                                        onSkipToggle={onSkipToggle}
                                    />
                                )}

                                {/* Qualitative Metric */}
                                {form.evaluation_type === 'Qualitative' && (
                                    <QualitativeMetricForm
                                        form={form}
                                        index={index}
                                        outcomeValues={outcomeValues}
                                        onResultChange={onResultChange}
                                        onSkipToggle={onSkipToggle}
                                    />
                                )}

                                {/* Outcome Only Metric */}
                                {form.evaluation_type === 'Outcome Only' && (
                                    <OutcomeOnlyMetricForm
                                        form={form}
                                        index={index}
                                        outcomeValues={outcomeValues}
                                        onResultChange={onResultChange}
                                        onSkipToggle={onSkipToggle}
                                    />
                                )}

                                {/* Save/Delete Buttons */}
                                <div className="mt-4 flex justify-between items-center">
                                    <div className="flex items-center gap-2">
                                        {form.existingResultId && !form.dirty && (
                                            <span className="text-green-600 text-sm flex items-center gap-1">
                                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                </svg>
                                                Saved
                                            </span>
                                        )}
                                        {form.dirty && (
                                            <span className="text-amber-600 text-sm">Unsaved changes</span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {form.existingResultId && (
                                            <button
                                                onClick={() => onDeleteResult(index)}
                                                disabled={deletingResult === index || savingResult === index}
                                                className="px-3 py-2 rounded text-sm font-medium text-red-600 hover:bg-red-50 border border-red-300 disabled:opacity-50"
                                            >
                                                {deletingResult === index ? 'Deleting...' : 'Delete'}
                                            </button>
                                        )}
                                        <button
                                            onClick={() => onSaveResult(index)}
                                            disabled={savingResult === index || deletingResult === index || (!form.dirty && form.existingResultId !== null)}
                                            className={`px-4 py-2 rounded text-sm font-medium ${
                                                form.dirty
                                                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                                                    : 'bg-gray-200 text-gray-600'
                                            } disabled:opacity-50`}
                                        >
                                            {savingResult === index ? 'Saving...' : form.existingResultId ? 'Update' : 'Save'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t bg-gray-50 flex justify-between items-center">
                <div className="text-sm text-gray-600">
                    {resultForms.filter(f => f.dirty).length > 0 && (
                        <span className="text-amber-600">
                            {resultForms.filter(f => f.dirty).length} unsaved changes
                        </span>
                    )}
                </div>
                <button onClick={onClose} className="btn-secondary">
                    Close
                </button>
            </div>
        </div>
    );
};

// Quantitative Metric Form Sub-component
const QuantitativeMetricForm: React.FC<{
    form: ResultFormData;
    index: number;
    onResultChange: (index: number, field: string, value: string | number | null) => void;
    onSkipToggle: (index: number, skipped: boolean) => void;
}> = ({ form, index, onResultChange, onSkipToggle }) => (
    <div className="space-y-3">
        {/* Threshold Visualization */}
        <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-sm text-gray-600 mb-2">Thresholds:</div>
            <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                    <span className="w-2 h-2 rounded-full bg-green-500 mr-1"></span>
                    Green: {form.yellow_min !== null || form.yellow_max !== null ? (
                        <>
                            {form.yellow_min !== null ? `>${form.yellow_min}` : ''}
                            {form.yellow_min !== null && form.yellow_max !== null ? ' and ' : ''}
                            {form.yellow_max !== null ? `<${form.yellow_max}` : ''}
                        </>
                    ) : 'Default'}
                </span>
                {(form.yellow_min !== null || form.yellow_max !== null) && (
                    <span className="inline-flex items-center px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
                        <span className="w-2 h-2 rounded-full bg-yellow-500 mr-1"></span>
                        Yellow: {form.yellow_min ?? '-'} to {form.yellow_max ?? '-'}
                    </span>
                )}
                {(form.red_min !== null || form.red_max !== null) && (
                    <span className="inline-flex items-center px-2 py-1 bg-red-100 text-red-800 rounded text-xs">
                        <span className="w-2 h-2 rounded-full bg-red-500 mr-1"></span>
                        Red: {form.red_min !== null ? `<${form.red_min}` : ''}{form.red_min !== null && form.red_max !== null ? ' or ' : ''}{form.red_max !== null ? `>${form.red_max}` : ''}
                    </span>
                )}
            </div>
        </div>

        {/* Previous Value Context */}
        {form.previousValue !== null && (
            <div className="bg-blue-50 rounded-lg p-3 flex items-center justify-between">
                <div>
                    <span className="text-xs text-blue-600 font-medium">Previous Cycle</span>
                    {form.previousPeriod && (
                        <span className="text-xs text-blue-500 ml-1">({form.previousPeriod})</span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-blue-900">{form.previousValue.toFixed(4)}</span>
                    {form.previousOutcome && (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            form.previousOutcome === 'GREEN' ? 'bg-green-100 text-green-800' :
                            form.previousOutcome === 'YELLOW' ? 'bg-yellow-100 text-yellow-800' :
                            form.previousOutcome === 'RED' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                        }`}>
                            {form.previousOutcome}
                        </span>
                    )}
                </div>
            </div>
        )}

        {/* Value Input with Skip checkbox */}
        <div>
            <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">Value</label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                        type="checkbox"
                        checked={form.skipped}
                        onChange={(e) => onSkipToggle(index, e.target.checked)}
                        className="rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                    />
                    <span className="text-gray-600">Skip this metric</span>
                </label>
            </div>
            <input
                type="number"
                step="any"
                className={`w-full border border-gray-300 rounded-lg px-3 py-2 ${
                    form.skipped ? 'bg-gray-100 text-gray-400' : ''
                }`}
                value={form.numeric_value}
                onChange={(e) => onResultChange(index, 'numeric_value', e.target.value)}
                placeholder={form.skipped ? "Skipped" : "Enter numeric value..."}
                disabled={form.skipped}
            />
        </div>

        {/* Skip Explanation (only shown when skipped) */}
        {form.skipped && (
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Skip Explanation <span className="text-red-500">*</span>
                </label>
                <textarea
                    className={`w-full border rounded-lg px-3 py-2 text-sm ${
                        !form.narrative.trim()
                            ? 'border-amber-300 bg-amber-50'
                            : 'border-gray-300'
                    }`}
                    rows={2}
                    value={form.narrative}
                    onChange={(e) => onResultChange(index, 'narrative', e.target.value)}
                    placeholder="Required: Explain why this metric was not measured..."
                />
                {!form.narrative.trim() && (
                    <p className="text-xs text-amber-600 mt-1">
                        An explanation is required when skipping a metric.
                    </p>
                )}
            </div>
        )}

        {/* Notes (only shown when not skipped) */}
        {!form.skipped && (
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
                <textarea
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    rows={2}
                    value={form.narrative}
                    onChange={(e) => onResultChange(index, 'narrative', e.target.value)}
                    placeholder="Any supporting notes..."
                />
            </div>
        )}
    </div>
);

// Qualitative Metric Form Sub-component
const QualitativeMetricForm: React.FC<{
    form: ResultFormData;
    index: number;
    outcomeValues: OutcomeValue[];
    onResultChange: (index: number, field: string, value: string | number | null) => void;
    onSkipToggle: (index: number, skipped: boolean) => void;
}> = ({ form, index, outcomeValues, onResultChange, onSkipToggle }) => (
    <div className="space-y-3">
        {form.qualitative_guidance && (
            <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-sm text-gray-600 mb-1">Guidance:</div>
                <p className="text-sm">{form.qualitative_guidance}</p>
            </div>
        )}

        {/* Outcome Input with Skip checkbox */}
        <div>
            <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">Outcome</label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                        type="checkbox"
                        checked={form.skipped}
                        onChange={(e) => onSkipToggle(index, e.target.checked)}
                        className="rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                    />
                    <span className="text-gray-600">Skip this metric</span>
                </label>
            </div>
            <select
                className={`w-full border border-gray-300 rounded-lg px-3 py-2 ${
                    form.skipped ? 'bg-gray-100 text-gray-400' : ''
                }`}
                value={form.outcome_value_id || ''}
                onChange={(e) => onResultChange(index, 'outcome_value_id', e.target.value ? parseInt(e.target.value) : null)}
                disabled={form.skipped}
            >
                <option value="">{form.skipped ? "Skipped" : "Select outcome..."}</option>
                {outcomeValues.map(o => (
                    <option key={o.value_id} value={o.value_id}>{o.label}</option>
                ))}
            </select>
        </div>

        {/* Skip Explanation (only shown when skipped) */}
        {form.skipped && (
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Skip Explanation <span className="text-red-500">*</span>
                </label>
                <textarea
                    className={`w-full border rounded-lg px-3 py-2 text-sm ${
                        !form.narrative.trim()
                            ? 'border-amber-300 bg-amber-50'
                            : 'border-gray-300'
                    }`}
                    rows={2}
                    value={form.narrative}
                    onChange={(e) => onResultChange(index, 'narrative', e.target.value)}
                    placeholder="Required: Explain why this metric was not measured..."
                />
                {!form.narrative.trim() && (
                    <p className="text-xs text-amber-600 mt-1">
                        An explanation is required when skipping a metric.
                    </p>
                )}
            </div>
        )}

        {/* Rationale (only shown when not skipped) */}
        {!form.skipped && (
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Rationale <span className="text-red-500">*</span>
                </label>
                <textarea
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    rows={3}
                    value={form.narrative}
                    onChange={(e) => onResultChange(index, 'narrative', e.target.value)}
                    placeholder="Required: Explain the rationale for this outcome..."
                />
            </div>
        )}
    </div>
);

// Outcome Only Metric Form Sub-component
const OutcomeOnlyMetricForm: React.FC<{
    form: ResultFormData;
    index: number;
    outcomeValues: OutcomeValue[];
    onResultChange: (index: number, field: string, value: string | number | null) => void;
    onSkipToggle: (index: number, skipped: boolean) => void;
}> = ({ form, index, outcomeValues, onResultChange, onSkipToggle }) => (
    <div className="space-y-3">
        {form.qualitative_guidance && (
            <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-sm text-gray-600 mb-1">Guidance:</div>
                <p className="text-sm">{form.qualitative_guidance}</p>
            </div>
        )}

        {/* Outcome Input with Skip checkbox */}
        <div>
            <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">Outcome</label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                        type="checkbox"
                        checked={form.skipped}
                        onChange={(e) => onSkipToggle(index, e.target.checked)}
                        className="rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                    />
                    <span className="text-gray-600">Skip this metric</span>
                </label>
            </div>
            <select
                className={`w-full border border-gray-300 rounded-lg px-3 py-2 ${
                    form.skipped ? 'bg-gray-100 text-gray-400' : ''
                }`}
                value={form.outcome_value_id || ''}
                onChange={(e) => onResultChange(index, 'outcome_value_id', e.target.value ? parseInt(e.target.value) : null)}
                disabled={form.skipped}
            >
                <option value="">{form.skipped ? "Skipped" : "Select outcome..."}</option>
                {outcomeValues.map(o => (
                    <option key={o.value_id} value={o.value_id}>{o.label}</option>
                ))}
            </select>
        </div>

        {/* Skip Explanation (only shown when skipped) */}
        {form.skipped && (
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Skip Explanation <span className="text-red-500">*</span>
                </label>
                <textarea
                    className={`w-full border rounded-lg px-3 py-2 text-sm ${
                        !form.narrative.trim()
                            ? 'border-amber-300 bg-amber-50'
                            : 'border-gray-300'
                    }`}
                    rows={2}
                    value={form.narrative}
                    onChange={(e) => onResultChange(index, 'narrative', e.target.value)}
                    placeholder="Required: Explain why this metric was not measured..."
                />
                {!form.narrative.trim() && (
                    <p className="text-xs text-amber-600 mt-1">
                        An explanation is required when skipping a metric.
                    </p>
                )}
            </div>
        )}

        {/* Notes (only shown when not skipped) */}
        {!form.skipped && (
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
                <textarea
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    rows={2}
                    value={form.narrative}
                    onChange={(e) => onResultChange(index, 'narrative', e.target.value)}
                    placeholder="Any supporting notes..."
                />
            </div>
        )}
    </div>
);

export default CycleResultsPanel;

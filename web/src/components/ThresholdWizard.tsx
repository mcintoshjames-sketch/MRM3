import React, { useState, useEffect, useCallback } from 'react';

/**
 * ThresholdWizard - Visual threshold configurator for monitoring metrics
 *
 * Features:
 * - Visual track showing GREEN/YELLOW/RED zones
 * - Draggable handles to adjust boundaries
 * - Live preview: "Value X would be classified as: GREEN"
 * - Built-in validation (prevents invalid configurations)
 * - Preset patterns for common use cases
 */

export interface ThresholdValues {
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
}

interface ThresholdWizardProps {
    values: ThresholdValues;
    onChange: (values: ThresholdValues) => void;
    // Optional: Suggested range for the slider
    suggestedMin?: number;
    suggestedMax?: number;
}

// Preset threshold patterns
type PresetType = 'lower_is_better' | 'higher_is_better' | 'range' | 'none';

interface Preset {
    name: string;
    description: string;
    icon: string;
    values: ThresholdValues;
}

const PRESETS: Record<PresetType, Preset> = {
    lower_is_better: {
        name: 'Lower is Better',
        description: 'E.g., error rate, latency. Values above thresholds trigger warnings.',
        icon: '📉',
        values: { yellow_min: null, yellow_max: 0.05, red_min: null, red_max: 0.1 },
    },
    higher_is_better: {
        name: 'Higher is Better',
        description: 'E.g., accuracy, coverage. Values below thresholds trigger warnings.',
        icon: '📈',
        values: { yellow_min: 0.95, yellow_max: null, red_min: 0.9, red_max: null },
    },
    range: {
        name: 'Range-Based',
        description: 'E.g., p-value. Values outside an acceptable range trigger warnings.',
        icon: '📊',
        values: { yellow_min: 0.01, yellow_max: 0.1, red_min: 0.001, red_max: 0.15 },
    },
    none: {
        name: 'No Thresholds',
        description: 'Clear all thresholds. All values will show as unconfigured.',
        icon: '❌',
        values: { yellow_min: null, yellow_max: null, red_min: null, red_max: null },
    },
};

// Calculate outcome from value and thresholds (mirrors backend logic)
const calculateOutcome = (value: number | null, thresholds: ThresholdValues): string => {
    if (value === null) return 'N/A';

    const { yellow_min, yellow_max, red_min, red_max } = thresholds;
    const hasThresholds = yellow_min !== null || yellow_max !== null || red_min !== null || red_max !== null;

    if (!hasThresholds) return 'UNCONFIGURED';

    // Check RED first (highest severity)
    if (red_min !== null && value < red_min) return 'RED';
    if (red_max !== null && value > red_max) return 'RED';

    // Check YELLOW
    if (yellow_min !== null && value < yellow_min) return 'YELLOW';
    if (yellow_max !== null && value > yellow_max) return 'YELLOW';

    return 'GREEN';
};

// Validate threshold configuration
const validateThresholds = (values: ThresholdValues): string[] => {
    const errors: string[] = [];
    const { yellow_min, yellow_max, red_min, red_max } = values;

    // Rule 1: red_min should be <= yellow_min
    if (red_min !== null && yellow_min !== null && red_min > yellow_min) {
        errors.push('Red min must be ≤ yellow min');
    }

    // Rule 2: red_max should be >= yellow_max
    if (red_max !== null && yellow_max !== null && red_max < yellow_max) {
        errors.push('Red max must be ≥ yellow max');
    }

    // Rule 3: Yellow zone should be non-empty
    if (yellow_min !== null && yellow_max !== null && yellow_min > yellow_max) {
        errors.push('Yellow min must be ≤ yellow max');
    }

    // Rule 4: Red zones shouldn't overlap
    if (red_min !== null && red_max !== null && red_min >= red_max) {
        errors.push('Red min must be < red max');
    }

    return errors;
};

// Get color classes for outcome
const getOutcomeColor = (outcome: string): string => {
    switch (outcome) {
        case 'GREEN': return 'text-green-600 bg-green-100';
        case 'YELLOW': return 'text-yellow-700 bg-yellow-100';
        case 'RED': return 'text-red-600 bg-red-100';
        case 'UNCONFIGURED': return 'text-gray-600 bg-gray-100';
        default: return 'text-gray-500 bg-gray-50';
    }
};

// Visual threshold track component
const ThresholdTrack: React.FC<{
    values: ThresholdValues;
    min: number;
    max: number;
    testValue: number | null;
}> = ({ values, min, max, testValue }) => {
    const range = max - min;
    if (range <= 0) return null;

    const toPercent = (val: number) => Math.min(100, Math.max(0, ((val - min) / range) * 100));

    const { yellow_min, yellow_max, red_min, red_max } = values;
    const hasThresholds = yellow_min !== null || yellow_max !== null || red_min !== null || red_max !== null;

    if (!hasThresholds) {
        return (
            <div className="h-8 rounded-lg bg-gray-200 relative flex items-center justify-center">
                <span className="text-xs text-gray-500">No thresholds configured</span>
            </div>
        );
    }

    // Build zone segments
    const segments: { start: number; end: number; color: string; label: string }[] = [];

    // Determine the pattern and build appropriate segments
    const hasMinThresholds = red_min !== null || yellow_min !== null;
    const hasMaxThresholds = red_max !== null || yellow_max !== null;

    if (hasMinThresholds && hasMaxThresholds) {
        // Range-based: RED | YELLOW | GREEN | YELLOW | RED
        const redMinPct = red_min !== null ? toPercent(red_min) : 0;
        const yellowMinPct = yellow_min !== null ? toPercent(yellow_min) : redMinPct;
        const yellowMaxPct = yellow_max !== null ? toPercent(yellow_max) : 100;
        const redMaxPct = red_max !== null ? toPercent(red_max) : 100;

        if (red_min !== null) segments.push({ start: 0, end: redMinPct, color: 'bg-red-400', label: 'RED' });
        if (yellow_min !== null) segments.push({ start: redMinPct, end: yellowMinPct, color: 'bg-yellow-400', label: 'YLW' });
        segments.push({ start: yellowMinPct, end: yellowMaxPct, color: 'bg-green-400', label: 'GRN' });
        if (yellow_max !== null) segments.push({ start: yellowMaxPct, end: redMaxPct, color: 'bg-yellow-400', label: 'YLW' });
        if (red_max !== null) segments.push({ start: redMaxPct, end: 100, color: 'bg-red-400', label: 'RED' });
    } else if (hasMinThresholds) {
        // Higher is better: RED | YELLOW | GREEN
        const redMinPct = red_min !== null ? toPercent(red_min) : 0;
        const yellowMinPct = yellow_min !== null ? toPercent(yellow_min) : redMinPct;

        if (red_min !== null) segments.push({ start: 0, end: redMinPct, color: 'bg-red-400', label: 'RED' });
        if (yellow_min !== null) segments.push({ start: redMinPct, end: yellowMinPct, color: 'bg-yellow-400', label: 'YLW' });
        segments.push({ start: yellowMinPct, end: 100, color: 'bg-green-400', label: 'GRN' });
    } else if (hasMaxThresholds) {
        // Lower is better: GREEN | YELLOW | RED
        const yellowMaxPct = yellow_max !== null ? toPercent(yellow_max) : 100;
        const redMaxPct = red_max !== null ? toPercent(red_max) : 100;

        segments.push({ start: 0, end: yellowMaxPct, color: 'bg-green-400', label: 'GRN' });
        if (yellow_max !== null) segments.push({ start: yellowMaxPct, end: redMaxPct, color: 'bg-yellow-400', label: 'YLW' });
        if (red_max !== null) segments.push({ start: redMaxPct, end: 100, color: 'bg-red-400', label: 'RED' });
    }

    // Test value marker position
    const testValuePct = testValue !== null ? toPercent(testValue) : null;

    return (
        <div className="relative">
            {/* Track */}
            <div className="h-8 rounded-lg overflow-hidden flex relative">
                {segments.map((seg, idx) => (
                    <div
                        key={idx}
                        className={`${seg.color} flex items-center justify-center text-xs font-medium text-white/80`}
                        style={{ width: `${seg.end - seg.start}%` }}
                    >
                        {seg.end - seg.start > 15 && seg.label}
                    </div>
                ))}
            </div>

            {/* Test value marker */}
            {testValuePct !== null && (
                <div
                    className="absolute top-0 h-8 w-0.5 bg-gray-800 pointer-events-none"
                    style={{ left: `${testValuePct}%` }}
                >
                    <div className="absolute -top-5 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-1.5 py-0.5 rounded whitespace-nowrap">
                        {testValue?.toFixed(3)}
                    </div>
                </div>
            )}

            {/* Scale markers */}
            <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>{min}</span>
                <span>{max}</span>
            </div>
        </div>
    );
};

const ThresholdWizard: React.FC<ThresholdWizardProps> = ({
    values,
    onChange,
    suggestedMin = 0,
    suggestedMax = 1,
}) => {
    // Local form state (as strings for input handling)
    const [formValues, setFormValues] = useState({
        yellow_min: values.yellow_min?.toString() ?? '',
        yellow_max: values.yellow_max?.toString() ?? '',
        red_min: values.red_min?.toString() ?? '',
        red_max: values.red_max?.toString() ?? '',
    });

    // Test value for live preview
    const [testValue, setTestValue] = useState<string>('');

    // Validation errors
    const [errors, setErrors] = useState<string[]>([]);

    // Track if user has made changes
    const [isDirty, setIsDirty] = useState(false);

    // Sync form values when props change (but not when dirty)
    useEffect(() => {
        if (!isDirty) {
            setFormValues({
                yellow_min: values.yellow_min?.toString() ?? '',
                yellow_max: values.yellow_max?.toString() ?? '',
                red_min: values.red_min?.toString() ?? '',
                red_max: values.red_max?.toString() ?? '',
            });
        }
    }, [values, isDirty]);

    // Parse form values to numbers
    const parseFormValues = useCallback((): ThresholdValues => {
        return {
            yellow_min: formValues.yellow_min ? parseFloat(formValues.yellow_min) : null,
            yellow_max: formValues.yellow_max ? parseFloat(formValues.yellow_max) : null,
            red_min: formValues.red_min ? parseFloat(formValues.red_min) : null,
            red_max: formValues.red_max ? parseFloat(formValues.red_max) : null,
        };
    }, [formValues]);

    // Validate and propagate changes
    useEffect(() => {
        const parsed = parseFormValues();
        const validationErrors = validateThresholds(parsed);
        setErrors(validationErrors);

        // Only propagate if valid
        if (validationErrors.length === 0) {
            onChange(parsed);
        }
    }, [formValues, parseFormValues, onChange]);

    // Handle input change
    const handleInputChange = (field: keyof typeof formValues, value: string) => {
        setIsDirty(true);
        setFormValues(prev => ({ ...prev, [field]: value }));
    };

    // Apply preset
    const applyPreset = (presetKey: PresetType) => {
        const preset = PRESETS[presetKey];
        setIsDirty(true);
        setFormValues({
            yellow_min: preset.values.yellow_min?.toString() ?? '',
            yellow_max: preset.values.yellow_max?.toString() ?? '',
            red_min: preset.values.red_min?.toString() ?? '',
            red_max: preset.values.red_max?.toString() ?? '',
        });
    };

    // Clear all thresholds
    const clearAll = () => {
        setIsDirty(true);
        setFormValues({
            yellow_min: '',
            yellow_max: '',
            red_min: '',
            red_max: '',
        });
    };

    // Calculate preview outcome
    const parsedValues = parseFormValues();
    const testValueNum = testValue ? parseFloat(testValue) : null;
    const previewOutcome = calculateOutcome(testValueNum, parsedValues);

    // Determine track bounds for visualization
    const allValues = [
        parsedValues.yellow_min,
        parsedValues.yellow_max,
        parsedValues.red_min,
        parsedValues.red_max,
        testValueNum,
    ].filter((v): v is number => v !== null);

    const trackMin = allValues.length > 0 ? Math.min(...allValues, suggestedMin) * 0.9 : suggestedMin;
    const trackMax = allValues.length > 0 ? Math.max(...allValues, suggestedMax) * 1.1 : suggestedMax;

    return (
        <div className="space-y-4">
            {/* Preset Buttons */}
            <div>
                <label className="block text-xs font-medium text-gray-500 mb-2 uppercase tracking-wider">
                    Quick Presets
                </label>
                <div className="grid grid-cols-2 gap-2">
                    {(Object.keys(PRESETS) as PresetType[]).map((key) => {
                        const preset = PRESETS[key];
                        return (
                            <button
                                key={key}
                                type="button"
                                onClick={() => applyPreset(key)}
                                className="text-left p-2 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors"
                            >
                                <div className="flex items-center gap-2">
                                    <span className="text-lg">{preset.icon}</span>
                                    <span className="text-sm font-medium text-gray-700">{preset.name}</span>
                                </div>
                                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{preset.description}</p>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Visual Track */}
            <div>
                <label className="block text-xs font-medium text-gray-500 mb-2 uppercase tracking-wider">
                    Threshold Zones
                </label>
                <ThresholdTrack
                    values={parsedValues}
                    min={trackMin}
                    max={trackMax}
                    testValue={testValueNum}
                />
            </div>

            {/* Threshold Inputs */}
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="block text-sm font-medium text-yellow-700 mb-1">
                        Yellow Min
                    </label>
                    <input
                        type="number"
                        step="any"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-yellow-500 focus:border-yellow-500"
                        value={formValues.yellow_min}
                        onChange={(e) => handleInputChange('yellow_min', e.target.value)}
                        placeholder="None"
                    />
                    <p className="text-xs text-gray-500 mt-0.5">Below → Yellow</p>
                </div>
                <div>
                    <label className="block text-sm font-medium text-yellow-700 mb-1">
                        Yellow Max
                    </label>
                    <input
                        type="number"
                        step="any"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-yellow-500 focus:border-yellow-500"
                        value={formValues.yellow_max}
                        onChange={(e) => handleInputChange('yellow_max', e.target.value)}
                        placeholder="None"
                    />
                    <p className="text-xs text-gray-500 mt-0.5">Above → Yellow</p>
                </div>
                <div>
                    <label className="block text-sm font-medium text-red-700 mb-1">
                        Red Min
                    </label>
                    <input
                        type="number"
                        step="any"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-red-500 focus:border-red-500"
                        value={formValues.red_min}
                        onChange={(e) => handleInputChange('red_min', e.target.value)}
                        placeholder="None"
                    />
                    <p className="text-xs text-gray-500 mt-0.5">Below → Red</p>
                </div>
                <div>
                    <label className="block text-sm font-medium text-red-700 mb-1">
                        Red Max
                    </label>
                    <input
                        type="number"
                        step="any"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-red-500 focus:border-red-500"
                        value={formValues.red_max}
                        onChange={(e) => handleInputChange('red_max', e.target.value)}
                        placeholder="None"
                    />
                    <p className="text-xs text-gray-500 mt-0.5">Above → Red</p>
                </div>
            </div>

            {/* Validation Errors */}
            {errors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                        <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        <div>
                            <p className="text-sm font-medium text-red-800">Invalid Configuration</p>
                            <ul className="text-xs text-red-700 mt-1 list-disc list-inside">
                                {errors.map((err, i) => <li key={i}>{err}</li>)}
                            </ul>
                        </div>
                    </div>
                </div>
            )}

            {/* Live Preview */}
            <div className="bg-gray-50 rounded-lg p-3">
                <label className="block text-xs font-medium text-gray-500 mb-2 uppercase tracking-wider">
                    Test a Value
                </label>
                <div className="flex items-center gap-3">
                    <input
                        type="number"
                        step="any"
                        className="w-32 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                        value={testValue}
                        onChange={(e) => setTestValue(e.target.value)}
                        placeholder="Enter value"
                    />
                    <span className="text-sm text-gray-500">→</span>
                    <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${getOutcomeColor(previewOutcome)}`}>
                        {previewOutcome}
                    </span>
                </div>
                {testValueNum !== null && errors.length === 0 && (
                    <p className="text-xs text-gray-500 mt-2">
                        Value <strong>{testValueNum}</strong> would be classified as <strong>{previewOutcome}</strong>
                    </p>
                )}
            </div>

            {/* Clear Button */}
            <div className="flex justify-end">
                <button
                    type="button"
                    onClick={clearAll}
                    className="text-sm text-gray-500 hover:text-gray-700 underline"
                >
                    Clear All Thresholds
                </button>
            </div>
        </div>
    );
};

export default ThresholdWizard;

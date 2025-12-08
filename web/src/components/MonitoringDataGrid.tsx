import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    flexRender,
    createColumnHelper,
    ColumnDef,
} from '@tanstack/react-table';

// Types
export interface Model {
    model_id: number;
    model_name: string;
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

export interface MonitoringResult {
    result_id: number;
    cycle_id: number;
    plan_metric_id: number;
    model_id: number | null;
    numeric_value: number | null;
    outcome_value?: { value_id: number; code: string; label: string } | null;
    calculated_outcome: string | null;
    narrative: string | null;
}

export interface OutcomeValue {
    value_id: number;
    code: string;
    label: string;
}

export interface CellPosition {
    modelId: number;
    metricId: number;
    snapshotId: number;
}

export interface ResultSavePayload {
    plan_metric_id: number;
    model_id: number | null;
    numeric_value?: number | null;
    outcome_value_id?: number | null;
    narrative?: string | null;
    result_id?: number | null; // For updates
}

export interface MonitoringDataGridProps {
    cycleId: number;
    metrics: MetricSnapshot[];
    models: Model[];
    existingResults: MonitoringResult[];
    outcomeValues: OutcomeValue[];
    onSaveResult: (payload: ResultSavePayload) => Promise<void>;
    onOpenBreachAnnotation: (cell: CellPosition, result: MonitoringResult | null) => void;
    readOnly?: boolean;
}

/**
 * Calculate outcome (GREEN, YELLOW, RED, UNCONFIGURED) from numeric value and thresholds.
 *
 * WARNING: This logic is duplicated in the backend at api/app/api/monitoring.py
 * in the `calculate_outcome()` function. Any changes here MUST be synchronized
 * with the backend to ensure consistent behavior. The backend is the source of
 * truth for persisted data; this frontend function provides immediate visual
 * feedback during data entry.
 *
 * Outcome codes must match api/app/core/monitoring_constants.py
 */
const calculateOutcome = (
    value: number | null,
    metric: MetricSnapshot
): string | null => {
    if (value === null) return null;

    // Check if any thresholds are configured
    const hasThresholds = (
        metric.red_min !== null ||
        metric.red_max !== null ||
        metric.yellow_min !== null ||
        metric.yellow_max !== null
    );
    if (!hasThresholds) return 'UNCONFIGURED';

    // Check RED thresholds first (highest severity)
    if (metric.red_min !== null && value < metric.red_min) return 'RED';
    if (metric.red_max !== null && value > metric.red_max) return 'RED';

    // Check YELLOW thresholds
    if (metric.yellow_min !== null && value < metric.yellow_min) return 'YELLOW';
    if (metric.yellow_max !== null && value > metric.yellow_max) return 'YELLOW';

    return 'GREEN';
};

// Helper to get cell background color based on outcome
const getOutcomeBgColor = (outcome: string | null): string => {
    switch (outcome) {
        case 'GREEN': return 'bg-green-100';
        case 'YELLOW': return 'bg-yellow-100';
        case 'RED': return 'bg-red-100';
        case 'UNCONFIGURED': return 'bg-gray-100';  // Gray indicates no thresholds configured
        default: return 'bg-white';
    }
};

// Row data type for the table
interface GridRow {
    model: Model;
    results: Record<number, MonitoringResult | undefined>; // metricId -> result
}

// Editable cell component
const EditableCell: React.FC<{
    modelId: number;
    metric: MetricSnapshot;
    result: MonitoringResult | undefined;
    outcomeValues: OutcomeValue[];
    onSave: (payload: ResultSavePayload) => Promise<void>;
    onOpenBreachAnnotation: (cell: CellPosition, result: MonitoringResult | null) => void;
    readOnly: boolean;
    isActive: boolean;
    onActivate: () => void;
    onNavigate: (direction: 'up' | 'down' | 'left' | 'right') => void;
}> = ({
    modelId,
    metric,
    result,
    outcomeValues,
    onSave,
    onOpenBreachAnnotation,
    readOnly,
    isActive,
    onActivate,
    onNavigate,
}) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState('');
    const [saving, setSaving] = useState(false);
    const inputRef = useRef<HTMLInputElement | HTMLSelectElement>(null);

    // Get current value/outcome
    const currentValue = result?.numeric_value;
    const currentOutcome = result?.calculated_outcome ||
        (currentValue !== null && currentValue !== undefined
            ? calculateOutcome(currentValue, metric)
            : null);

    // Display value based on metric type
    const displayValue = useMemo(() => {
        if (metric.evaluation_type === 'Quantitative') {
            return currentValue !== null && currentValue !== undefined
                ? currentValue.toFixed(4)
                : '';
        } else {
            return result?.outcome_value?.label || '';
        }
    }, [metric.evaluation_type, currentValue, result?.outcome_value]);

    // Start editing
    const startEditing = useCallback(() => {
        if (readOnly) return;

        if (metric.evaluation_type === 'Quantitative') {
            setEditValue(currentValue?.toString() || '');
        } else {
            setEditValue(result?.outcome_value?.value_id?.toString() || '');
        }
        setIsEditing(true);
    }, [readOnly, metric.evaluation_type, currentValue, result?.outcome_value]);

    // Focus input when editing starts
    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
            if (inputRef.current instanceof HTMLInputElement) {
                inputRef.current.select();
            }
        }
    }, [isEditing]);

    // Save and exit editing
    const saveAndExit = async () => {
        if (metric.evaluation_type === 'Quantitative') {
            const numValue = editValue.trim() === '' ? null : parseFloat(editValue);
            if (editValue.trim() !== '' && isNaN(numValue!)) {
                setIsEditing(false);
                return;
            }

            // Only save if value changed
            const changed = numValue !== currentValue;
            if (changed) {
                setSaving(true);
                try {
                    await onSave({
                        plan_metric_id: metric.original_metric_id!,
                        model_id: modelId,
                        numeric_value: numValue,
                        result_id: result?.result_id,
                    });
                } catch (err) {
                    console.error('Failed to save result:', err);
                } finally {
                    setSaving(false);
                }
            }
        } else {
            // Qualitative metric
            const valueId = editValue ? parseInt(editValue) : null;
            const changed = valueId !== result?.outcome_value?.value_id;
            if (changed) {
                setSaving(true);
                try {
                    await onSave({
                        plan_metric_id: metric.original_metric_id!,
                        model_id: modelId,
                        outcome_value_id: valueId,
                        result_id: result?.result_id,
                    });
                } catch (err) {
                    console.error('Failed to save result:', err);
                } finally {
                    setSaving(false);
                }
            }
        }
        setIsEditing(false);
    };

    // Handle keyboard navigation
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (isEditing) {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveAndExit();
            } else if (e.key === 'Escape') {
                setIsEditing(false);
            } else if (e.key === 'Tab') {
                e.preventDefault();
                saveAndExit();
                onNavigate(e.shiftKey ? 'left' : 'right');
            }
        } else {
            if (e.key === 'Enter' || e.key === 'F2') {
                e.preventDefault();
                startEditing();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                onNavigate('up');
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                onNavigate('down');
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                onNavigate('left');
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                onNavigate('right');
            } else if (e.key === 'Tab') {
                e.preventDefault();
                onNavigate(e.shiftKey ? 'left' : 'right');
            } else if (/^[0-9\.\-]$/.test(e.key) && metric.evaluation_type === 'Quantitative') {
                // Start editing on number input
                setEditValue(e.key);
                setIsEditing(true);
            }
        }
    };

    // Handle click to open breach annotation
    const handleClick = () => {
        if (!isEditing) {
            onActivate();
            // If RED outcome, clicking opens breach annotation
            if (currentOutcome === 'RED' && !readOnly) {
                onOpenBreachAnnotation(
                    { modelId, metricId: metric.original_metric_id!, snapshotId: metric.snapshot_id },
                    result || null
                );
            }
        }
    };

    // Handle double-click to edit
    const handleDoubleClick = () => {
        if (!readOnly) {
            startEditing();
        }
    };

    // Handle paste
    const handlePaste = (e: React.ClipboardEvent) => {
        if (readOnly || metric.evaluation_type !== 'Quantitative') return;

        e.preventDefault();
        const pastedText = e.clipboardData.getData('text').trim();
        const numValue = parseFloat(pastedText);

        if (!isNaN(numValue)) {
            setEditValue(numValue.toString());
            setIsEditing(true);
            // Auto-save after paste
            setTimeout(() => saveAndExit(), 100);
        }
    };

    const bgColor = getOutcomeBgColor(currentOutcome);
    const borderColor = isActive ? 'ring-2 ring-blue-500' : '';
    const hasNarrative = result?.narrative && result.narrative.trim() !== '';

    return (
        <div
            className={`relative h-10 ${bgColor} ${borderColor} cursor-pointer select-none`}
            onClick={handleClick}
            onDoubleClick={handleDoubleClick}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            tabIndex={0}
            role="gridcell"
        >
            {isEditing ? (
                metric.evaluation_type === 'Quantitative' ? (
                    <input
                        ref={inputRef as React.RefObject<HTMLInputElement>}
                        type="text"
                        className="w-full h-full px-2 text-sm border-none focus:outline-none bg-white"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={saveAndExit}
                        onKeyDown={handleKeyDown}
                    />
                ) : (
                    <select
                        ref={inputRef as React.RefObject<HTMLSelectElement>}
                        className="w-full h-full px-2 text-sm border-none focus:outline-none bg-white"
                        value={editValue}
                        onChange={(e) => {
                            setEditValue(e.target.value);
                        }}
                        onBlur={saveAndExit}
                        onKeyDown={handleKeyDown}
                    >
                        <option value="">--</option>
                        {outcomeValues.map((ov) => (
                            <option key={ov.value_id} value={ov.value_id}>
                                {ov.label}
                            </option>
                        ))}
                    </select>
                )
            ) : (
                <div className="flex items-center h-full px-2">
                    <span className="text-sm truncate flex-1">
                        {saving ? '...' : displayValue || '-'}
                    </span>
                    {/* Indicator icons */}
                    <div className="flex items-center gap-1 ml-1">
                        {hasNarrative && (
                            <span className="text-xs text-gray-500" title="Has narrative">
                                📝
                            </span>
                        )}
                        {currentOutcome === 'RED' && !hasNarrative && (
                            <span className="text-xs text-red-600" title="Breach explanation required">
                                ⚠️
                            </span>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

// Main Grid Component
const MonitoringDataGrid: React.FC<MonitoringDataGridProps> = ({
    cycleId: _cycleId, // Reserved for future API calls if needed
    metrics,
    models,
    existingResults,
    outcomeValues,
    onSaveResult,
    onOpenBreachAnnotation,
    readOnly = false,
}) => {
    // Active cell for keyboard navigation
    const [activeCell, setActiveCell] = useState<{ row: number; col: number } | null>(null);
    const gridRef = useRef<HTMLDivElement>(null);

    // Build row data: one row per model
    const data = useMemo<GridRow[]>(() => {
        return models.map((model) => {
            const results: Record<number, MonitoringResult | undefined> = {};
            metrics.forEach((metric) => {
                const matchingResult = existingResults.find(
                    (r) => r.model_id === model.model_id && r.plan_metric_id === metric.original_metric_id
                );
                if (metric.original_metric_id) {
                    results[metric.original_metric_id] = matchingResult;
                }
            });
            return { model, results };
        });
    }, [models, metrics, existingResults]);

    // Handle cell navigation
    const handleNavigate = useCallback((fromRow: number, fromCol: number, direction: 'up' | 'down' | 'left' | 'right') => {
        let newRow = fromRow;
        let newCol = fromCol;

        switch (direction) {
            case 'up':
                newRow = Math.max(0, fromRow - 1);
                break;
            case 'down':
                newRow = Math.min(models.length - 1, fromRow + 1);
                break;
            case 'left':
                newCol = Math.max(0, fromCol - 1);
                break;
            case 'right':
                newCol = Math.min(metrics.length - 1, fromCol + 1);
                break;
        }

        setActiveCell({ row: newRow, col: newCol });
    }, [models.length, metrics.length]);

    // Create column definitions using TanStack Table
    const columnHelper = createColumnHelper<GridRow>();

    const columns = useMemo<ColumnDef<GridRow, any>[]>(() => {
        // First column: Model name (frozen)
        const modelColumn = columnHelper.accessor('model.model_name', {
            id: 'model_name',
            header: 'Model',
            cell: (info) => (
                <div className="px-3 py-2 font-medium text-gray-900 truncate" title={info.getValue()}>
                    {info.getValue()}
                </div>
            ),
            size: 200,
        });

        // Metric columns
        const metricColumns = metrics.map((metric, colIndex) =>
            columnHelper.display({
                id: `metric_${metric.original_metric_id}`,
                header: () => (
                    <div className="px-2 py-1 text-xs">
                        <div className="font-medium truncate" title={metric.kpm_name}>
                            {metric.kpm_name}
                        </div>
                        <div className="text-gray-500 text-[10px]">
                            {metric.evaluation_type === 'Quantitative' ? 'Quant' : 'Qual'}
                        </div>
                    </div>
                ),
                cell: ({ row }) => {
                    const rowIndex = row.index;
                    const isActive = activeCell?.row === rowIndex && activeCell?.col === colIndex;
                    const result = row.original.results[metric.original_metric_id!];

                    return (
                        <EditableCell
                            modelId={row.original.model.model_id}
                            metric={metric}
                            result={result}
                            outcomeValues={outcomeValues}
                            onSave={onSaveResult}
                            onOpenBreachAnnotation={onOpenBreachAnnotation}
                            readOnly={readOnly}
                            isActive={isActive}
                            onActivate={() => setActiveCell({ row: rowIndex, col: colIndex })}
                            onNavigate={(dir) => handleNavigate(rowIndex, colIndex, dir)}
                        />
                    );
                },
                size: 120,
            })
        );

        return [modelColumn, ...metricColumns];
    }, [metrics, outcomeValues, onSaveResult, onOpenBreachAnnotation, readOnly, activeCell, handleNavigate, columnHelper]);

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
    });

    // Summary stats
    const stats = useMemo(() => {
        let green = 0, yellow = 0, red = 0, empty = 0;

        existingResults.forEach((r) => {
            if (r.calculated_outcome === 'GREEN') green++;
            else if (r.calculated_outcome === 'YELLOW') yellow++;
            else if (r.calculated_outcome === 'RED') red++;
        });

        const total = models.length * metrics.length;
        empty = total - existingResults.length;

        return { green, yellow, red, empty, total };
    }, [existingResults, models.length, metrics.length]);

    if (metrics.length === 0) {
        return (
            <div className="text-center py-8 text-gray-500">
                No metrics configured for this monitoring plan.
            </div>
        );
    }

    if (models.length === 0) {
        return (
            <div className="text-center py-8 text-gray-500">
                No models assigned to this monitoring plan.
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-4">
            {/* Summary Stats */}
            <div className="flex items-center gap-6 px-4 py-2 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-600">
                    Progress: {stats.total - stats.empty} / {stats.total}
                </span>
                <div className="flex items-center gap-4">
                    <span className="inline-flex items-center gap-1 text-sm">
                        <span className="w-3 h-3 rounded-full bg-green-500"></span>
                        {stats.green} Green
                    </span>
                    <span className="inline-flex items-center gap-1 text-sm">
                        <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
                        {stats.yellow} Yellow
                    </span>
                    <span className="inline-flex items-center gap-1 text-sm">
                        <span className="w-3 h-3 rounded-full bg-red-500"></span>
                        {stats.red} Red
                    </span>
                    <span className="inline-flex items-center gap-1 text-sm text-gray-500">
                        <span className="w-3 h-3 rounded-full bg-gray-300"></span>
                        {stats.empty} Empty
                    </span>
                </div>
            </div>

            {/* Grid Instructions */}
            <div className="text-xs text-gray-500 px-2">
                <strong>Keyboard:</strong> Arrow keys to navigate • Enter/F2 to edit • Tab to move right • Escape to cancel •
                <strong className="ml-2">Click RED cells</strong> to add breach explanations
            </div>

            {/* Data Grid */}
            <div
                ref={gridRef}
                className="border rounded-lg overflow-auto max-h-[60vh]"
                role="grid"
            >
                <table className="w-full border-collapse">
                    <thead className="bg-gray-100 sticky top-0 z-10">
                        {table.getHeaderGroups().map((headerGroup) => (
                            <tr key={headerGroup.id}>
                                {headerGroup.headers.map((header, index) => (
                                    <th
                                        key={header.id}
                                        className={`border-b border-r text-left ${
                                            index === 0
                                                ? 'sticky left-0 bg-gray-100 z-20 min-w-[200px]'
                                                : 'min-w-[120px]'
                                        }`}
                                        style={{ width: header.getSize() }}
                                    >
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(header.column.columnDef.header, header.getContext())}
                                    </th>
                                ))}
                            </tr>
                        ))}
                    </thead>
                    <tbody>
                        {table.getRowModel().rows.map((row) => (
                            <tr key={row.id} className="hover:bg-gray-50/50">
                                {row.getVisibleCells().map((cell, index) => (
                                    <td
                                        key={cell.id}
                                        className={`border-b border-r p-0 ${
                                            index === 0
                                                ? 'sticky left-0 bg-white z-10'
                                                : ''
                                        }`}
                                        style={{ width: cell.column.getSize() }}
                                    >
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default MonitoringDataGrid;

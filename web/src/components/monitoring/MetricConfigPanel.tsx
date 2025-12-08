import React from 'react';

// Types
export interface KpmRef {
    kpm_id: number;
    name: string;
    category_id: number;
    category_name: string | null;
    evaluation_type: string;
}

export interface PlanMetric {
    metric_id: number;
    kpm_id: number;
    kpm: KpmRef;
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
    qualitative_guidance: string | null;
    sort_order: number;
    is_active: boolean;
}

export interface TrendModalMetric {
    metric_id: number;
    metric_name: string;
    thresholds: {
        yellow_min: number | null;
        yellow_max: number | null;
        red_min: number | null;
        red_max: number | null;
    };
}

export interface MetricConfigPanelProps {
    metrics: PlanMetric[];
    canEdit: boolean;
    onAddMetric: () => void;
    onEditMetric: (metric: PlanMetric) => void;
    onDeactivateMetric: (metricId: number) => void;
    onViewTrend: (metric: TrendModalMetric) => void;
}

// Bullet Chart Component for threshold visualization
export const BulletChart: React.FC<{
    value: number | null;
    yellowMin: number | null;
    yellowMax: number | null;
    redMin: number | null;
    redMax: number | null;
    width?: number;
    height?: number;
}> = ({ value, yellowMin, yellowMax, redMin, redMax, width = 200, height = 24 }) => {
    // Determine the metric type and calculate range
    // Type 1: Lower is better (yellowMax and redMax set) - G < yellowMax < Y < redMax < R
    // Type 2: Higher is better (yellowMin and redMin set) - R < redMin < Y < yellowMin < G
    // Type 3: Range-based (yellowMin AND yellowMax set) - Green is within the range
    const isLowerBetter = yellowMax !== null && redMax !== null;
    const isHigherBetter = yellowMin !== null && redMin !== null;
    const isRangeBased = yellowMin !== null && yellowMax !== null && !isLowerBetter && !isHigherBetter;

    // Check if any thresholds are configured
    const hasAnyThreshold = yellowMin !== null || yellowMax !== null || redMin !== null || redMax !== null;

    if (!hasAnyThreshold) {
        return <span className="text-xs text-gray-400 italic">No thresholds</span>;
    }

    // Calculate min/max for the chart
    let minVal: number, maxVal: number;
    if (isLowerBetter) {
        minVal = 0;
        maxVal = (redMax || 0) * 1.3;
    } else if (isHigherBetter) {
        minVal = (redMin || 0) * 0.7;
        maxVal = (yellowMin || 0) * 1.3;
    } else if (isRangeBased) {
        minVal = (yellowMin || 0) * 0.7;
        maxVal = (yellowMax || 0) * 1.3;
    } else {
        const allVals = [yellowMin, yellowMax, redMin, redMax].filter(v => v !== null) as number[];
        minVal = Math.min(...allVals) * 0.7;
        maxVal = Math.max(...allVals) * 1.3;
    }
    const range = maxVal - minVal || 1;

    const getPosition = (val: number) => Math.max(0, Math.min(100, ((val - minVal) / range) * 100));

    return (
        <div className="relative" style={{ width, height }}>
            {/* Background segments */}
            <div className="absolute inset-0 flex rounded-sm overflow-hidden">
                {isLowerBetter ? (
                    <>
                        <div
                            className="bg-green-200 h-full"
                            style={{ width: `${getPosition(yellowMax || 0)}%` }}
                        />
                        <div
                            className="bg-yellow-200 h-full"
                            style={{ width: `${getPosition(redMax || 0) - getPosition(yellowMax || 0)}%` }}
                        />
                        <div className="bg-red-200 h-full flex-1" />
                    </>
                ) : isHigherBetter ? (
                    <>
                        <div
                            className="bg-red-200 h-full"
                            style={{ width: `${getPosition(redMin || 0)}%` }}
                        />
                        <div
                            className="bg-yellow-200 h-full"
                            style={{ width: `${getPosition(yellowMin || 0) - getPosition(redMin || 0)}%` }}
                        />
                        <div className="bg-green-200 h-full flex-1" />
                    </>
                ) : isRangeBased ? (
                    <>
                        <div
                            className="bg-yellow-200 h-full"
                            style={{ width: `${getPosition(yellowMin || 0)}%` }}
                        />
                        <div
                            className="bg-green-200 h-full"
                            style={{ width: `${getPosition(yellowMax || 0) - getPosition(yellowMin || 0)}%` }}
                        />
                        <div className="bg-yellow-200 h-full flex-1" />
                    </>
                ) : (
                    <div className="bg-gray-200 h-full flex-1" />
                )}
            </div>
            {/* Value marker */}
            {value !== null && (
                <div
                    className="absolute top-0 bottom-0 w-0.5 bg-gray-800"
                    style={{ left: `${Math.min(100, Math.max(0, getPosition(value)))}%` }}
                >
                    <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-gray-800 rotate-45" />
                </div>
            )}
            {/* Threshold lines */}
            {isLowerBetter && yellowMax !== null && (
                <div
                    className="absolute top-0 bottom-0 w-px bg-yellow-600"
                    style={{ left: `${getPosition(yellowMax)}%` }}
                />
            )}
            {isLowerBetter && redMax !== null && (
                <div
                    className="absolute top-0 bottom-0 w-px bg-red-600"
                    style={{ left: `${getPosition(redMax)}%` }}
                />
            )}
            {isHigherBetter && yellowMin !== null && (
                <div
                    className="absolute top-0 bottom-0 w-px bg-yellow-600"
                    style={{ left: `${getPosition(yellowMin)}%` }}
                />
            )}
            {isHigherBetter && redMin !== null && (
                <div
                    className="absolute top-0 bottom-0 w-px bg-red-600"
                    style={{ left: `${getPosition(redMin)}%` }}
                />
            )}
        </div>
    );
};

const MetricConfigPanel: React.FC<MetricConfigPanelProps> = ({
    metrics,
    canEdit,
    onAddMetric,
    onEditMetric,
    onDeactivateMetric,
    onViewTrend,
}) => {
    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <div>
                    <h3 className="text-lg font-semibold">Configured Metrics ({metrics?.length || 0})</h3>
                    {canEdit && (
                        <p className="text-sm text-gray-500 mt-1">
                            Add metrics, edit thresholds, and publish a new version when ready
                        </p>
                    )}
                </div>
                {canEdit && (
                    <button
                        onClick={onAddMetric}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        Add Metric
                    </button>
                )}
            </div>
            {!metrics?.length ? (
                <p className="text-gray-500">No metrics configured for this plan.</p>
            ) : (
                <div className="space-y-4">
                    {metrics.map((metric) => (
                        <div key={metric.metric_id} className="border rounded-lg p-4 hover:bg-gray-50">
                            <div className="flex justify-between items-start">
                                <div className="flex-1">
                                    <div className="flex items-center gap-3">
                                        <span className="font-medium text-gray-900">{metric.kpm?.name || '-'}</span>
                                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                                            metric.kpm?.evaluation_type === 'Quantitative' ? 'bg-blue-100 text-blue-800' :
                                            metric.kpm?.evaluation_type === 'Qualitative' ? 'bg-purple-100 text-purple-800' :
                                            'bg-green-100 text-green-800'
                                        }`}>
                                            {metric.kpm?.evaluation_type || '-'}
                                        </span>
                                    </div>
                                    <div className="text-sm text-gray-500 mt-1">{metric.kpm?.category_name || '-'}</div>
                                </div>
                                <div className="flex items-center gap-3">
                                    {canEdit && (
                                        <>
                                            <button
                                                onClick={() => onEditMetric(metric)}
                                                className="text-gray-600 hover:text-gray-800 text-sm flex items-center gap-1"
                                                title="Edit thresholds"
                                            >
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                </svg>
                                                Edit
                                            </button>
                                            <button
                                                onClick={() => onDeactivateMetric(metric.metric_id)}
                                                className="text-red-600 hover:text-red-800 text-sm flex items-center gap-1"
                                                title="Deactivate metric"
                                            >
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                                                </svg>
                                                Deactivate
                                            </button>
                                        </>
                                    )}
                                    {metric.kpm?.evaluation_type === 'Quantitative' && (
                                        <button
                                            onClick={() => onViewTrend({
                                                metric_id: metric.metric_id,
                                                metric_name: metric.kpm?.name || '',
                                                thresholds: {
                                                    yellow_min: metric.yellow_min,
                                                    yellow_max: metric.yellow_max,
                                                    red_min: metric.red_min,
                                                    red_max: metric.red_max,
                                                }
                                            })}
                                            className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1"
                                            title="View trend chart"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                                            </svg>
                                            Trend
                                        </button>
                                    )}
                                </div>
                            </div>
                            {metric.kpm?.evaluation_type === 'Quantitative' && (
                                <div className="mt-3 pt-3 border-t">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs text-gray-500 uppercase">Thresholds</span>
                                        <div className="flex flex-wrap items-center gap-2 text-xs">
                                            {metric.yellow_min !== null || metric.yellow_max !== null || metric.red_min !== null || metric.red_max !== null ? (
                                                <>
                                                    <span className="inline-flex items-center px-2 py-0.5 bg-green-100 text-green-800 rounded">
                                                        G: {metric.yellow_min !== null || metric.yellow_max !== null ? (
                                                            <>
                                                                {metric.yellow_min !== null ? `>${metric.yellow_min}` : ''}
                                                                {metric.yellow_min !== null && metric.yellow_max !== null ? ' and ' : ''}
                                                                {metric.yellow_max !== null ? `<${metric.yellow_max}` : ''}
                                                            </>
                                                        ) : 'Default'}
                                                    </span>
                                                    {(metric.yellow_min !== null || metric.yellow_max !== null) && (
                                                        <span className="inline-flex items-center px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded">
                                                            Y: {metric.yellow_min ?? '-'} to {metric.yellow_max ?? '-'}
                                                        </span>
                                                    )}
                                                    {(metric.red_min !== null || metric.red_max !== null) && (
                                                        <span className="inline-flex items-center px-2 py-0.5 bg-red-100 text-red-800 rounded">
                                                            R: {metric.red_min !== null ? `<${metric.red_min}` : ''}{metric.red_min !== null && metric.red_max !== null ? ' or ' : ''}{metric.red_max !== null ? `>${metric.red_max}` : ''}
                                                        </span>
                                                    )}
                                                </>
                                            ) : (
                                                <span className="text-gray-400 italic">No thresholds configured</span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="mt-2">
                                        <BulletChart
                                            value={null}
                                            yellowMin={metric.yellow_min}
                                            yellowMax={metric.yellow_max}
                                            redMin={metric.red_min}
                                            redMax={metric.red_max}
                                            width={300}
                                            height={20}
                                        />
                                    </div>
                                </div>
                            )}
                            {metric.kpm?.evaluation_type !== 'Quantitative' && (
                                <div className="mt-3 pt-3 border-t">
                                    <span className="text-xs text-gray-500">Judgment-based evaluation</span>
                                    {metric.qualitative_guidance && (
                                        <p className="text-sm text-gray-600 mt-1">{metric.qualitative_guidance}</p>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default MetricConfigPanel;

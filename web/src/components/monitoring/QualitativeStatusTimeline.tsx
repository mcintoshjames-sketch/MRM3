import React, { useMemo } from 'react';
import ModelSearchSelect from '../ModelSearchSelect';

interface TrendDataPoint {
    cycle_id: number;
    period_end_date: string;
    numeric_value: number | null;
    calculated_outcome: string | null;
    model_id: number | null;
    model_name: string | null;
    narrative?: string;
    cycle_name?: string;
}

interface TrendData {
    plan_metric_id: number;
    metric_name: string;
    kpm_name: string;
    evaluation_type: string;
    data_points: TrendDataPoint[];
}

interface AvailableModel {
    model_id: number;
    model_name: string;
}

interface QualitativeStatusTimelineProps {
    data: TrendData;
    onClose: () => void;
    modelFilter?: 'all' | 'plan-level' | number;
    availableModels?: AvailableModel[];
    onModelFilterChange?: (value: string) => void;
}

const MAX_CYCLES_DISPLAY = 10;

type OutcomeType = 'GREEN' | 'YELLOW' | 'RED' | 'N/A';

const outcomeConfig: Record<OutcomeType, { bg: string; icon: string; label: string }> = {
    GREEN: { bg: 'bg-green-500', icon: '✓', label: 'Green' },
    YELLOW: { bg: 'bg-yellow-400', icon: '⚠', label: 'Yellow' },
    RED: { bg: 'bg-red-500', icon: '✕', label: 'Red' },
    'N/A': { bg: 'bg-gray-300', icon: '—', label: 'N/A' },
};

const StatusBlock: React.FC<{
    outcome: string | null;
    date: string;
    modelName: string | null;
    narrative?: string;
}> = ({ outcome, date, modelName, narrative }) => {
    const normalizedOutcome = (outcome as OutcomeType) || 'N/A';
    const config = outcomeConfig[normalizedOutcome] || outcomeConfig['N/A'];

    // Format date for display (e.g., "Dec '24") - ISO compliant parsing
    const formatDate = (dateStr: string): string => {
        const parts = dateStr.split('T')[0].split('-');
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const month = monthNames[parseInt(parts[1], 10) - 1];
        const year = parts[0].slice(-2);
        return `${month} '${year}`;
    };

    const displayLabel = formatDate(date);

    return (
        <div className="relative group flex flex-col items-center">
            <div
                className={`w-12 h-12 ${config.bg} rounded-lg flex items-center justify-center ${normalizedOutcome === 'YELLOW' || normalizedOutcome === 'N/A' ? 'text-gray-900' : 'text-white'} text-lg font-bold shadow cursor-pointer transition-transform hover:scale-110`}
            >
                {config.icon}
            </div>
            <div className="text-xs text-center mt-1 text-gray-500 truncate w-14">
                {displayLabel}
            </div>

            {/* Tooltip */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10 pointer-events-none">
                <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg min-w-[180px]">
                    <div className="font-medium">{date.split('T')[0]}</div>
                    {modelName && (
                        <div className="text-gray-300 mt-1">{modelName}</div>
                    )}
                    <div className="mt-1">
                        <span
                            className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                                normalizedOutcome === 'GREEN'
                                    ? 'bg-green-600'
                                    : normalizedOutcome === 'YELLOW'
                                    ? 'bg-yellow-500 text-gray-900'
                                    : normalizedOutcome === 'RED'
                                    ? 'bg-red-600'
                                    : 'bg-gray-500'
                            }`}
                        >
                            {config.label}
                        </span>
                    </div>
                    {narrative && (
                        <div className="mt-2 text-gray-300 max-w-xs text-wrap">
                            {narrative.length > 100 ? `${narrative.slice(0, 100)}...` : narrative}
                        </div>
                    )}
                </div>
                {/* Tooltip arrow */}
                <div className="absolute left-1/2 -translate-x-1/2 -bottom-1 w-2 h-2 bg-gray-900 rotate-45"></div>
            </div>
        </div>
    );
};

const QualitativeStatusTimeline: React.FC<QualitativeStatusTimelineProps> = ({
    data,
    onClose,
    modelFilter = 'all',
    availableModels = [],
    onModelFilterChange,
}) => {
    // Filter and sort data points
    const { displayPoints, totalCount, truncated } = useMemo(() => {
        // First filter by model
        let filtered = data.data_points;
        if (modelFilter === 'plan-level') {
            filtered = data.data_points.filter(p => p.model_id === null);
        } else if (typeof modelFilter === 'number') {
            filtered = data.data_points.filter(p => p.model_id === modelFilter);
        }

        // Sort by date (oldest first)
        const sorted = [...filtered].sort(
            (a, b) => new Date(a.period_end_date).getTime() - new Date(b.period_end_date).getTime()
        );

        // Limit to last MAX_CYCLES_DISPLAY cycles
        const total = sorted.length;
        const display = sorted.slice(-MAX_CYCLES_DISPLAY);

        return {
            displayPoints: display,
            totalCount: total,
            truncated: total > MAX_CYCLES_DISPLAY
        };
    }, [data.data_points, modelFilter]);

    // Legacy alias for existing code that uses sortedPoints
    const sortedPoints = displayPoints;

    // Calculate distribution
    const distribution = {
        green: sortedPoints.filter((o) => o.calculated_outcome === 'GREEN').length,
        yellow: sortedPoints.filter((o) => o.calculated_outcome === 'YELLOW').length,
        red: sortedPoints.filter((o) => o.calculated_outcome === 'RED').length,
        na: sortedPoints.filter(
            (o) => !o.calculated_outcome || o.calculated_outcome === 'N/A'
        ).length,
    };

    // Determine trend (compare last 2 outcomes)
    const getTrend = () => {
        const outcomePoints = sortedPoints.filter(
            (p) => p.calculated_outcome && p.calculated_outcome !== 'N/A'
        );
        if (outcomePoints.length < 2) return null;

        const last = outcomePoints[outcomePoints.length - 1].calculated_outcome;
        const prev = outcomePoints[outcomePoints.length - 2].calculated_outcome;
        const order: Record<string, number> = { GREEN: 1, YELLOW: 2, RED: 3 };

        if (!last || !prev) return null;
        const lastOrder = order[last] || 0;
        const prevOrder = order[prev] || 0;

        if (lastOrder > prevOrder) return { icon: '↘️', text: 'Degrading', color: 'text-red-600' };
        if (lastOrder < prevOrder) return { icon: '↗️', text: 'Improving', color: 'text-green-600' };
        return { icon: '➡️', text: 'Stable', color: 'text-gray-600' };
    };

    // Calculate streak
    const getStreak = () => {
        if (sortedPoints.length === 0) return null;

        const lastOutcome = sortedPoints[sortedPoints.length - 1].calculated_outcome;
        if (!lastOutcome || lastOutcome === 'N/A') return null;

        let streak = 1;
        for (let i = sortedPoints.length - 2; i >= 0; i--) {
            if (sortedPoints[i].calculated_outcome === lastOutcome) {
                streak++;
            } else {
                break;
            }
        }

        if (streak >= 2) {
            return { count: streak, outcome: lastOutcome };
        }
        return null;
    };

    const trend = getTrend();
    const streak = getStreak();

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
                {/* Header */}
                <div className="p-4 border-b flex justify-between items-center bg-gray-50">
                    <div>
                        <h3 className="text-lg font-bold">Metric Trend Analysis</h3>
                        <p className="text-sm text-gray-600">{data.metric_name}</p>
                        <span className="inline-block mt-1 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
                            {data.evaluation_type}
                        </span>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <svg
                            className="w-6 h-6"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M6 18L18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>

                {/* Model Filter - Only show when multiple models exist and handler provided */}
                {availableModels.length > 1 && onModelFilterChange && (
                    <div className="px-6 py-3 border-b bg-gray-50 flex items-center gap-3">
                        <label className="text-sm font-medium text-gray-700">Filter by Model:</label>
                        <ModelSearchSelect
                            models={availableModels}
                            value={modelFilter === 'all' || modelFilter === 'plan-level' ? modelFilter : modelFilter}
                            onChange={(value) => {
                                if (value === null) {
                                    onModelFilterChange('all');
                                    return;
                                }
                                onModelFilterChange(String(value));
                            }}
                            specialOptions={[
                                { value: 'all', label: 'All Results' },
                                { value: 'plan-level', label: 'Plan Level (All Models)' }
                            ]}
                            inputClassName="border rounded-md px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            placeholder="Search models..."
                        />
                        {modelFilter !== 'all' && (
                            <span className="text-xs text-gray-500">
                                Showing results for selected model only
                            </span>
                        )}
                    </div>
                )}

                {/* Content */}
                <div className="p-6">
                    {sortedPoints.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            <p>No trend data available for this metric.</p>
                            <p className="text-sm mt-2">
                                Complete some monitoring cycles with results to see trends.
                            </p>
                        </div>
                    ) : (
                        <>
                            {/* Timeline Header */}
                            <div className="mb-4">
                                <p className="text-sm text-gray-600 mb-2">
                                    Outcome History ({sortedPoints.length} cycle
                                    {sortedPoints.length !== 1 ? 's' : ''})
                                    {truncated && (
                                        <span className="text-xs text-gray-500 ml-2">
                                            (showing last {MAX_CYCLES_DISPLAY} of {totalCount})
                                        </span>
                                    )}
                                </p>
                            </div>

                            {/* Status Strip */}
                            <div className="flex gap-3 justify-center flex-wrap mb-8 p-4 bg-gray-50 rounded-lg">
                                {sortedPoints.map((point, i) => (
                                    <StatusBlock
                                        key={`${point.cycle_id}-${point.model_id || 'plan'}-${i}`}
                                        outcome={point.calculated_outcome}
                                        date={point.period_end_date}
                                        modelName={point.model_name}
                                        narrative={point.narrative}
                                    />
                                ))}
                            </div>

                            {/* Legend */}
                            <div className="flex justify-center gap-6 mb-6 text-sm">
                                <span className="flex items-center gap-2">
                                    <span className="w-4 h-4 bg-green-500 rounded"></span>
                                    <span className="text-gray-600">Green (Pass)</span>
                                </span>
                                <span className="flex items-center gap-2">
                                    <span className="w-4 h-4 bg-yellow-400 rounded"></span>
                                    <span className="text-gray-600">Yellow (Warning)</span>
                                </span>
                                <span className="flex items-center gap-2">
                                    <span className="w-4 h-4 bg-red-500 rounded"></span>
                                    <span className="text-gray-600">Red (Action Required)</span>
                                </span>
                            </div>

                            {/* Summary Statistics */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                                <div className="bg-green-50 rounded-lg p-4 text-center border border-green-200">
                                    <p className="text-2xl font-bold text-green-600">
                                        {distribution.green}
                                    </p>
                                    <p className="text-xs text-green-700 uppercase font-medium">
                                        Green
                                    </p>
                                </div>
                                <div className="bg-yellow-50 rounded-lg p-4 text-center border border-yellow-200">
                                    <p className="text-2xl font-bold text-yellow-600">
                                        {distribution.yellow}
                                    </p>
                                    <p className="text-xs text-yellow-700 uppercase font-medium">
                                        Yellow
                                    </p>
                                </div>
                                <div className="bg-red-50 rounded-lg p-4 text-center border border-red-200">
                                    <p className="text-2xl font-bold text-red-600">
                                        {distribution.red}
                                    </p>
                                    <p className="text-xs text-red-700 uppercase font-medium">
                                        Red
                                    </p>
                                </div>
                                <div className="bg-gray-50 rounded-lg p-4 text-center border border-gray-200">
                                    <p className="text-2xl font-bold text-gray-600">
                                        {distribution.na}
                                    </p>
                                    <p className="text-xs text-gray-700 uppercase font-medium">
                                        N/A
                                    </p>
                                </div>
                            </div>

                            {/* Trend & Streak Indicators */}
                            <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                                <p className="font-medium text-blue-800 mb-2">Trend Analysis</p>
                                <div className="flex flex-wrap gap-4 text-sm">
                                    {trend && (
                                        <span className={`${trend.color} font-medium`}>
                                            {trend.icon} {trend.text}
                                        </span>
                                    )}
                                    {streak && (
                                        <span className="text-gray-700">
                                            {streak.count} consecutive{' '}
                                            <span
                                                className={
                                                    streak.outcome === 'GREEN'
                                                        ? 'text-green-600 font-medium'
                                                        : streak.outcome === 'YELLOW'
                                                        ? 'text-yellow-600 font-medium'
                                                        : 'text-red-600 font-medium'
                                                }
                                            >
                                                {streak.outcome}
                                            </span>{' '}
                                            assessments
                                        </span>
                                    )}
                                    {!trend && !streak && (
                                        <span className="text-gray-500">
                                            Not enough data for trend analysis
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Info Note */}
                            <div className="mt-4 text-sm text-gray-500 bg-gray-50 p-3 rounded">
                                <p>
                                    <strong>Note:</strong> Qualitative metrics are assessed
                                    based on expert judgment rather than numeric thresholds.
                                    Hover over each status block to see details and narrative
                                    comments.
                                </p>
                            </div>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t bg-gray-50 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default QualitativeStatusTimeline;

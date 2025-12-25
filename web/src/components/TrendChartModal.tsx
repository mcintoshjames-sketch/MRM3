import React, { useEffect, useState } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    ReferenceArea,
    ReferenceLine,
} from 'recharts';
import api from '../api/client';
import QualitativeStatusTimeline from './monitoring/QualitativeStatusTimeline';

interface TrendDataPoint {
    cycle_id: number;
    period_end_date: string;
    numeric_value: number | null;
    calculated_outcome: string | null;
    model_id: number | null;
    model_name: string | null;
    yellow_min?: number | null;
    yellow_max?: number | null;
    red_min?: number | null;
    red_max?: number | null;
    narrative?: string;
}

interface TrendData {
    plan_metric_id: number;
    metric_name: string;
    kpm_name: string;
    evaluation_type: string;
    // Thresholds from API
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
    data_points: TrendDataPoint[];
}

interface ThresholdConfig {
    yellow_min: number | null;
    yellow_max: number | null;
    red_min: number | null;
    red_max: number | null;
}

interface TrendChartModalProps {
    isOpen: boolean;
    onClose: () => void;
    planMetricId: number;
    metricName: string;
    thresholds: ThresholdConfig;
}

// Colors for multiple model lines
const MODEL_COLORS = [
    '#2563eb', // blue-600
    '#7c3aed', // violet-600
    '#db2777', // pink-600
    '#ea580c', // orange-600
    '#059669', // emerald-600
    '#0891b2', // cyan-600
];

const TrendChartModal: React.FC<TrendChartModalProps> = ({
    isOpen,
    onClose,
    planMetricId,
    metricName,
    thresholds,
}) => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [trendData, setTrendData] = useState<TrendData | null>(null);
    // Model filter: 'all' = show all, 'plan-level' = only null model_id, number = specific model
    const [modelFilter, setModelFilter] = useState<'all' | 'plan-level' | number>('all');
    // Available models extracted from trend data
    const [availableModels, setAvailableModels] = useState<Array<{ model_id: number; model_name: string }>>([]);

    useEffect(() => {
        if (isOpen && planMetricId) {
            // Reset filter when modal opens
            setModelFilter('all');
            fetchTrendData();
        }
    }, [isOpen, planMetricId]);

    const fetchTrendData = async (filterModelId?: number | null) => {
        setLoading(true);
        setError(null);
        try {
            // Build URL with optional model_id filter
            let url = `/monitoring/metrics/${planMetricId}/trend`;
            if (filterModelId !== undefined && filterModelId !== null) {
                url += `?model_id=${filterModelId}`;
            }
            const response = await api.get(url);
            setTrendData(response.data);

            // Extract unique models from data for filter dropdown (only on initial load)
            if (filterModelId === undefined) {
                const models = new Map<number, string>();
                let hasPlanLevel = false;
                response.data.data_points.forEach((point: TrendDataPoint) => {
                    if (point.model_id === null) {
                        hasPlanLevel = true;
                    } else if (point.model_name) {
                        models.set(point.model_id, point.model_name);
                    }
                });
                const modelList = Array.from(models.entries()).map(([id, name]) => ({
                    model_id: id,
                    model_name: name
                }));
                // Sort by name
                modelList.sort((a, b) => a.model_name.localeCompare(b.model_name));
                // Add plan-level option if exists
                if (hasPlanLevel) {
                    modelList.unshift({ model_id: -1, model_name: 'Plan Level (All Models)' });
                }
                setAvailableModels(modelList);
            }
        } catch (err: unknown) {
            console.error('Error fetching trend data:', err);
            if (err && typeof err === 'object' && 'response' in err) {
                const axiosError = err as { response?: { data?: { detail?: string } } };
                setError(axiosError.response?.data?.detail || 'Failed to load trend data');
            } else {
                setError('Failed to load trend data');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleModelFilterChange = (value: string) => {
        if (value === 'all') {
            setModelFilter('all');
            fetchTrendData(); // Fetch all
        } else if (value === 'plan-level') {
            setModelFilter('plan-level');
            // Backend doesn't support filtering for null, so we filter client-side
            fetchTrendData();
        } else {
            const modelId = parseInt(value);
            setModelFilter(modelId);
            fetchTrendData(modelId);
        }
    };

    if (!isOpen) return null;

    // Check if this is a qualitative/outcome-only metric (case-insensitive)
    const evalType = trendData?.evaluation_type?.toLowerCase();
    const isQualitative = evalType === 'qualitative' || evalType === 'outcome only';

    // For qualitative metrics, render the specialized status timeline instead of line chart
    // Wait until data is loaded before making this decision
    if (!loading && trendData && isQualitative) {
        return (
            <QualitativeStatusTimeline
                data={trendData}
                onClose={onClose}
                modelFilter={modelFilter}
                availableModels={availableModels}
                onModelFilterChange={handleModelFilterChange}
            />
        );
    }

    // Base thresholds: prefer API data, fallback to props
    const baseThresholds: ThresholdConfig = {
        yellow_min: trendData?.yellow_min ?? thresholds.yellow_min,
        yellow_max: trendData?.yellow_max ?? thresholds.yellow_max,
        red_min: trendData?.red_min ?? thresholds.red_min,
        red_max: trendData?.red_max ?? thresholds.red_max,
    };

    // Chart data point type - date is always a string, model values are numbers or null
    interface ChartDataPoint {
        date: string;
        [modelKey: string]: string | number | null;
    }

    // Process data for chart - group by model if multiple models exist
    const processChartData = () => {
        if (!trendData || !trendData.data_points.length) {
            return {
                chartData: [] as ChartDataPoint[],
                modelNames: [] as string[],
                thresholdsByDate: new Map<string, ThresholdConfig>(),
            };
        }

        const modelNames = new Set<string>();
        const dateMap = new Map<string, ChartDataPoint>();
        const thresholdsByDate = new Map<string, ThresholdConfig>();

        // Filter data points based on model filter
        let filteredPoints = trendData.data_points;
        if (modelFilter === 'plan-level') {
            // Only show plan-level results (model_id = null)
            filteredPoints = trendData.data_points.filter(p => p.model_id === null);
        }
        // Note: specific model filtering is done server-side via API query param

        filteredPoints.forEach((point) => {
            const modelKey = point.model_name || 'Plan Level';
            modelNames.add(modelKey);

            const dateKey = point.period_end_date;
            if (!dateMap.has(dateKey)) {
                dateMap.set(dateKey, { date: dateKey });
            }
            if (!thresholdsByDate.has(dateKey)) {
                thresholdsByDate.set(dateKey, {
                    yellow_min: point.yellow_min ?? baseThresholds.yellow_min,
                    yellow_max: point.yellow_max ?? baseThresholds.yellow_max,
                    red_min: point.red_min ?? baseThresholds.red_min,
                    red_max: point.red_max ?? baseThresholds.red_max,
                });
            }
            const dateEntry = dateMap.get(dateKey)!;
            dateEntry[modelKey] = point.numeric_value;
        });

        // Convert map to sorted array
        const chartData = Array.from(dateMap.values()).sort((a, b) =>
            a.date.localeCompare(b.date)
        );

        return { chartData, modelNames: Array.from(modelNames), thresholdsByDate };
    };

    const { chartData, modelNames, thresholdsByDate } = processChartData();

    // Calculate Y-axis domain based on data and thresholds
    const calculateYDomain = (): [number, number] => {
        if (!chartData.length) return [0, 1];

        const allValues = chartData.flatMap((d) =>
            modelNames.map((m) => d[m] as number | null).filter((v): v is number => v !== null)
        );

        if (!allValues.length) return [0, 1];

        const dataMin = Math.min(...allValues);
        const dataMax = Math.max(...allValues);

        const thresholdValues = Array.from(thresholdsByDate.values()).flatMap(
            (threshold) => [
                threshold.yellow_min,
                threshold.yellow_max,
                threshold.red_min,
                threshold.red_max,
            ].filter((v): v is number => v !== null)
        );
        const fallbackThresholdValues = [
            baseThresholds.yellow_min,
            baseThresholds.yellow_max,
            baseThresholds.red_min,
            baseThresholds.red_max,
        ].filter((v): v is number => v !== null);
        const allThresholdValues = thresholdValues.length > 0 ? thresholdValues : fallbackThresholdValues;

        const allMin = allThresholdValues.length ? Math.min(dataMin, ...allThresholdValues) : dataMin;
        const allMax = allThresholdValues.length ? Math.max(dataMax, ...allThresholdValues) : dataMax;

        // Add 10% padding
        const padding = (allMax - allMin) * 0.1 || 0.1;
        return [Math.max(0, allMin - padding), allMax + padding];
    };

    const yDomain = calculateYDomain();

    // Format date for X-axis
    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
    };

    // Custom tooltip
    const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: unknown[]; label?: string }) => {
        if (!active || !payload || !payload.length) return null;

        return (
            <div className="bg-white border rounded shadow-lg p-3">
                <p className="font-medium text-gray-900 mb-2">{label}</p>
                {(payload as Array<{ dataKey: string; value: number | null; color: string }>).map((entry, index) => (
                    <p key={index} style={{ color: entry.color }} className="text-sm">
                        {entry.dataKey}: {entry.value !== null ? entry.value.toFixed(4) : 'N/A'}
                    </p>
                ))}
            </div>
        );
    };

    const hasDynamicThresholds = Array.from(thresholdsByDate.values()).some((threshold) => {
        const lowerIsBetter = threshold.yellow_max !== null && threshold.red_max !== null && threshold.red_max > threshold.yellow_max;
        const higherIsBetter = threshold.yellow_min !== null && threshold.red_min !== null && threshold.red_min < threshold.yellow_min;
        return lowerIsBetter || higherIsBetter;
    });

    const renderStaticBands = (thresholdsToRender: ThresholdConfig) => {
        const bands = [];
        const { yellow_min, yellow_max, red_min, red_max } = thresholdsToRender;

        if (yellow_max !== null && red_max !== null && red_max > yellow_max) {
            bands.push(
                <ReferenceArea key="green" y1={yDomain[0]} y2={yellow_max} fill="#22c55e" fillOpacity={0.1} />,
                <ReferenceArea key="yellow" y1={yellow_max} y2={red_max} fill="#eab308" fillOpacity={0.1} />,
                <ReferenceArea key="red" y1={red_max} y2={yDomain[1]} fill="#ef4444" fillOpacity={0.1} />,
                <ReferenceLine key="yellow-line" y={yellow_max} stroke="#eab308" strokeDasharray="5 5" />,
                <ReferenceLine key="red-line" y={red_max} stroke="#ef4444" strokeDasharray="5 5" />
            );
        } else if (yellow_min !== null && red_min !== null && red_min < yellow_min) {
            bands.push(
                <ReferenceArea key="red" y1={yDomain[0]} y2={red_min} fill="#ef4444" fillOpacity={0.1} />,
                <ReferenceArea key="yellow" y1={red_min} y2={yellow_min} fill="#eab308" fillOpacity={0.1} />,
                <ReferenceArea key="green" y1={yellow_min} y2={yDomain[1]} fill="#22c55e" fillOpacity={0.1} />,
                <ReferenceLine key="yellow-line" y={yellow_min} stroke="#eab308" strokeDasharray="5 5" />,
                <ReferenceLine key="red-line" y={red_min} stroke="#ef4444" strokeDasharray="5 5" />
            );
        }

        return bands;
    };

    const renderThresholdBands = () => {
        if (!chartData.length) return [];
        if (chartData.length < 2 || !hasDynamicThresholds) {
            return renderStaticBands(baseThresholds);
        }

        const dateKeys = chartData.map((entry) => entry.date);
        const bands = [];

        for (let index = 1; index < dateKeys.length; index += 1) {
            const startDate = dateKeys[index - 1];
            const endDate = dateKeys[index];
            const threshold = thresholdsByDate.get(endDate) ?? baseThresholds;

            const lowerIsBetter = threshold.yellow_max !== null && threshold.red_max !== null && threshold.red_max > threshold.yellow_max;
            const higherIsBetter = threshold.yellow_min !== null && threshold.red_min !== null && threshold.red_min < threshold.yellow_min;

            if (lowerIsBetter) {
                bands.push(
                    <ReferenceArea key={`green-${endDate}`} x1={startDate} x2={endDate} y1={yDomain[0]} y2={threshold.yellow_max as number} fill="#22c55e" fillOpacity={0.1} />,
                    <ReferenceArea key={`yellow-${endDate}`} x1={startDate} x2={endDate} y1={threshold.yellow_max as number} y2={threshold.red_max as number} fill="#eab308" fillOpacity={0.1} />,
                    <ReferenceArea key={`red-${endDate}`} x1={startDate} x2={endDate} y1={threshold.red_max as number} y2={yDomain[1]} fill="#ef4444" fillOpacity={0.1} />
                );
            } else if (higherIsBetter) {
                bands.push(
                    <ReferenceArea key={`red-${endDate}`} x1={startDate} x2={endDate} y1={yDomain[0]} y2={threshold.red_min as number} fill="#ef4444" fillOpacity={0.1} />,
                    <ReferenceArea key={`yellow-${endDate}`} x1={startDate} x2={endDate} y1={threshold.red_min as number} y2={threshold.yellow_min as number} fill="#eab308" fillOpacity={0.1} />,
                    <ReferenceArea key={`green-${endDate}`} x1={startDate} x2={endDate} y1={threshold.yellow_min as number} y2={yDomain[1]} fill="#22c55e" fillOpacity={0.1} />
                );
            }
        }

        return bands;
    };

    const latestThresholds = (() => {
        if (!chartData.length) return baseThresholds;
        const lastDate = chartData[chartData.length - 1].date;
        return thresholdsByDate.get(lastDate) ?? baseThresholds;
    })();

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
                {/* Header */}
                <div className="p-4 border-b flex justify-between items-center bg-gray-50">
                    <div>
                        <h3 className="text-lg font-bold">Metric Trend Analysis</h3>
                        <p className="text-sm text-gray-600">{metricName}</p>
                    </div>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Model Filter - Only show when multiple models exist */}
                {availableModels.length > 1 && (
                    <div className="px-6 py-3 border-b bg-gray-50 flex items-center gap-3">
                        <label className="text-sm font-medium text-gray-700">Filter by Model:</label>
                        <select
                            value={modelFilter === 'all' ? 'all' : modelFilter === 'plan-level' ? 'plan-level' : modelFilter.toString()}
                            onChange={(e) => handleModelFilterChange(e.target.value)}
                            className="border rounded-md px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            disabled={loading}
                        >
                            <option value="all">All Results (Multi-Line)</option>
                            {availableModels.map((model) => (
                                <option
                                    key={model.model_id}
                                    value={model.model_id === -1 ? 'plan-level' : model.model_id.toString()}
                                >
                                    {model.model_name}
                                </option>
                            ))}
                        </select>
                        {modelFilter !== 'all' && (
                            <span className="text-xs text-gray-500">
                                Showing single line for selected model
                            </span>
                        )}
                    </div>
                )}

                {/* Content */}
                <div className="p-6">
                    {loading ? (
                        <div className="flex justify-center items-center h-64">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                            <span className="ml-3 text-gray-600">Loading trend data...</span>
                        </div>
                    ) : error ? (
                        <div className="text-center py-8 text-red-600">
                            <p>{error}</p>
                            <button
                                onClick={() => fetchTrendData()}
                                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                                Retry
                            </button>
                        </div>
                    ) : chartData.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            <p>No trend data available for this metric.</p>
                            <p className="text-sm mt-2">Complete some monitoring cycles with results to see trends.</p>
                        </div>
                    ) : (
                        <>
                            {/* Legend for threshold bands */}
                            <div className="mb-4 flex items-center gap-4 text-sm">
                                <span className="flex items-center gap-1">
                                    <span className="w-4 h-4 bg-green-500 bg-opacity-20 border border-green-500"></span>
                                    Green Zone
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="w-4 h-4 bg-yellow-500 bg-opacity-20 border border-yellow-500"></span>
                                    Yellow Zone
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="w-4 h-4 bg-red-500 bg-opacity-20 border border-red-500"></span>
                                    Red Zone
                                </span>
                            </div>

                            {/* Chart */}
                            <div className="h-80">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                        {renderThresholdBands()}
                                        <XAxis
                                            dataKey="date"
                                            tickFormatter={formatDate}
                                            tick={{ fontSize: 12 }}
                                            stroke="#6b7280"
                                        />
                                        <YAxis
                                            domain={yDomain}
                                            tick={{ fontSize: 12 }}
                                            stroke="#6b7280"
                                            tickFormatter={(value) => value.toFixed(2)}
                                        />
                                        <Tooltip content={<CustomTooltip />} />
                                        {modelNames.length > 1 && <Legend />}
                                        {modelNames.map((modelName, index) => (
                                            <Line
                                                key={modelName}
                                                type="monotone"
                                                dataKey={modelName}
                                                stroke={MODEL_COLORS[index % MODEL_COLORS.length]}
                                                strokeWidth={2}
                                                dot={{ r: 4 }}
                                                activeDot={{ r: 6 }}
                                                connectNulls
                                            />
                                        ))}
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            {/* Summary Stats */}
                            <div className="mt-6 grid grid-cols-4 gap-4">
                                <div className="bg-gray-50 rounded p-3 text-center">
                                    <p className="text-xs text-gray-500 uppercase">Data Points</p>
                                    <p className="text-xl font-bold text-gray-900">{trendData?.data_points.length || 0}</p>
                                </div>
                                <div className="bg-gray-50 rounded p-3 text-center">
                                    <p className="text-xs text-gray-500 uppercase">Latest Value</p>
                                    <p className="text-xl font-bold text-gray-900">
                                        {trendData?.data_points.length
                                            ? (trendData.data_points[trendData.data_points.length - 1].numeric_value?.toFixed(4) || 'N/A')
                                            : 'N/A'}
                                    </p>
                                </div>
                                <div className="bg-gray-50 rounded p-3 text-center">
                                    <p className="text-xs text-gray-500 uppercase">Yellow Threshold</p>
                                    <p className="text-xl font-bold text-yellow-600">
                                        {latestThresholds.yellow_max?.toFixed(2) || latestThresholds.yellow_min?.toFixed(2) || 'N/A'}
                                    </p>
                                </div>
                                <div className="bg-gray-50 rounded p-3 text-center">
                                    <p className="text-xs text-gray-500 uppercase">Red Threshold</p>
                                    <p className="text-xl font-bold text-red-600">
                                        {latestThresholds.red_max?.toFixed(2) || latestThresholds.red_min?.toFixed(2) || 'N/A'}
                                    </p>
                                </div>
                            </div>

                            {/* Threshold Info */}
                            <div className="mt-4 text-sm text-gray-600 bg-blue-50 p-3 rounded">
                                <p className="font-medium text-blue-800">Threshold Configuration:</p>
                                <p className="text-xs text-blue-700 mt-1">
                                    Bands reflect thresholds active for each cycle; values below show the latest thresholds.
                                </p>
                                <p>
                                    {latestThresholds.yellow_max !== null && latestThresholds.red_max !== null && (
                                        <>Lower is better: Green &lt; {latestThresholds.yellow_max}, Yellow {latestThresholds.yellow_max}-{latestThresholds.red_max}, Red &gt; {latestThresholds.red_max}</>
                                    )}
                                    {latestThresholds.yellow_min !== null && latestThresholds.red_min !== null && (
                                        <>Higher is better: Green &gt; {latestThresholds.yellow_min}, Yellow {latestThresholds.red_min}-{latestThresholds.yellow_min}, Red &lt; {latestThresholds.red_min}</>
                                    )}
                                    {latestThresholds.yellow_max === null && latestThresholds.yellow_min === null && latestThresholds.red_max === null && latestThresholds.red_min === null && (
                                        <>No thresholds configured for this metric.</>
                                    )}
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

export default TrendChartModal;

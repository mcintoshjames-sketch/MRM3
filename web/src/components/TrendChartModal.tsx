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

interface TrendDataPoint {
    cycle_id: number;
    period_end_date: string;
    numeric_value: number | null;
    calculated_outcome: string | null;
    model_id: number | null;
    model_name: string | null;
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

    useEffect(() => {
        if (isOpen && planMetricId) {
            fetchTrendData();
        }
    }, [isOpen, planMetricId]);

    const fetchTrendData = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get(`/monitoring/metrics/${planMetricId}/trend`);
            setTrendData(response.data);
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

    if (!isOpen) return null;

    // Effective thresholds: prefer API data, fallback to props
    const effectiveThresholds: ThresholdConfig = {
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
        if (!trendData || !trendData.data_points.length) return { chartData: [] as ChartDataPoint[], modelNames: [] as string[] };

        const modelNames = new Set<string>();
        const dateMap = new Map<string, ChartDataPoint>();

        trendData.data_points.forEach((point) => {
            const modelKey = point.model_name || 'All Models';
            modelNames.add(modelKey);

            const dateKey = point.period_end_date;
            if (!dateMap.has(dateKey)) {
                dateMap.set(dateKey, { date: dateKey });
            }
            const dateEntry = dateMap.get(dateKey)!;
            dateEntry[modelKey] = point.numeric_value;
        });

        // Convert map to sorted array
        const chartData = Array.from(dateMap.values()).sort((a, b) =>
            a.date.localeCompare(b.date)
        );

        return { chartData, modelNames: Array.from(modelNames) };
    };

    const { chartData, modelNames } = processChartData();

    // Calculate Y-axis domain based on data and thresholds
    const calculateYDomain = (): [number, number] => {
        if (!chartData.length) return [0, 1];

        const allValues = chartData.flatMap((d) =>
            modelNames.map((m) => d[m] as number | null).filter((v): v is number => v !== null)
        );

        if (!allValues.length) return [0, 1];

        const dataMin = Math.min(...allValues);
        const dataMax = Math.max(...allValues);

        // Include threshold values in range
        const thresholdValues = [
            effectiveThresholds.yellow_min,
            effectiveThresholds.yellow_max,
            effectiveThresholds.red_min,
            effectiveThresholds.red_max,
        ].filter((v): v is number => v !== null);

        const allMin = Math.min(dataMin, ...thresholdValues);
        const allMax = Math.max(dataMax, ...thresholdValues);

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

    // Determine threshold band rendering based on threshold configuration
    const renderThresholdBands = () => {
        const bands = [];
        const { yellow_min, yellow_max, red_min, red_max } = effectiveThresholds;

        // For "lower is better" metrics like PSI: green < yellow_max < red_max
        if (yellow_max !== null && red_max !== null && red_max > yellow_max) {
            // Green zone: 0 to yellow_max
            bands.push(
                <ReferenceArea
                    key="green"
                    y1={yDomain[0]}
                    y2={yellow_max}
                    fill="#22c55e"
                    fillOpacity={0.1}
                />
            );
            // Yellow zone: yellow_max to red_max
            bands.push(
                <ReferenceArea
                    key="yellow"
                    y1={yellow_max}
                    y2={red_max}
                    fill="#eab308"
                    fillOpacity={0.1}
                />
            );
            // Red zone: red_max to top
            bands.push(
                <ReferenceArea
                    key="red"
                    y1={red_max}
                    y2={yDomain[1]}
                    fill="#ef4444"
                    fillOpacity={0.1}
                />
            );
            // Threshold lines
            bands.push(
                <ReferenceLine key="yellow-line" y={yellow_max} stroke="#eab308" strokeDasharray="5 5" />,
                <ReferenceLine key="red-line" y={red_max} stroke="#ef4444" strokeDasharray="5 5" />
            );
        }
        // For "higher is better" metrics like Gini: green > yellow_min > red_min
        else if (yellow_min !== null && red_min !== null && red_min < yellow_min) {
            // Red zone: bottom to red_min
            bands.push(
                <ReferenceArea
                    key="red"
                    y1={yDomain[0]}
                    y2={red_min}
                    fill="#ef4444"
                    fillOpacity={0.1}
                />
            );
            // Yellow zone: red_min to yellow_min
            bands.push(
                <ReferenceArea
                    key="yellow"
                    y1={red_min}
                    y2={yellow_min}
                    fill="#eab308"
                    fillOpacity={0.1}
                />
            );
            // Green zone: yellow_min to top
            bands.push(
                <ReferenceArea
                    key="green"
                    y1={yellow_min}
                    y2={yDomain[1]}
                    fill="#22c55e"
                    fillOpacity={0.1}
                />
            );
            // Threshold lines
            bands.push(
                <ReferenceLine key="yellow-line" y={yellow_min} stroke="#eab308" strokeDasharray="5 5" />,
                <ReferenceLine key="red-line" y={red_min} stroke="#ef4444" strokeDasharray="5 5" />
            );
        }

        return bands;
    };

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
                                onClick={fetchTrendData}
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
                                        {effectiveThresholds.yellow_max?.toFixed(2) || effectiveThresholds.yellow_min?.toFixed(2) || 'N/A'}
                                    </p>
                                </div>
                                <div className="bg-gray-50 rounded p-3 text-center">
                                    <p className="text-xs text-gray-500 uppercase">Red Threshold</p>
                                    <p className="text-xl font-bold text-red-600">
                                        {effectiveThresholds.red_max?.toFixed(2) || effectiveThresholds.red_min?.toFixed(2) || 'N/A'}
                                    </p>
                                </div>
                            </div>

                            {/* Threshold Info */}
                            <div className="mt-4 text-sm text-gray-600 bg-blue-50 p-3 rounded">
                                <p className="font-medium text-blue-800">Threshold Configuration:</p>
                                <p>
                                    {effectiveThresholds.yellow_max !== null && effectiveThresholds.red_max !== null && (
                                        <>Lower is better: Green &lt; {effectiveThresholds.yellow_max}, Yellow {effectiveThresholds.yellow_max}-{effectiveThresholds.red_max}, Red &gt; {effectiveThresholds.red_max}</>
                                    )}
                                    {effectiveThresholds.yellow_min !== null && effectiveThresholds.red_min !== null && (
                                        <>Higher is better: Green &gt; {effectiveThresholds.yellow_min}, Yellow {effectiveThresholds.red_min}-{effectiveThresholds.yellow_min}, Red &lt; {effectiveThresholds.red_min}</>
                                    )}
                                    {effectiveThresholds.yellow_max === null && effectiveThresholds.yellow_min === null && effectiveThresholds.red_max === null && effectiveThresholds.red_min === null && (
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

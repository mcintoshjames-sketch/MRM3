/**
 * KPIMetricCard - displays a single KPI metric with value and optional decomposition.
 */
import React from 'react';
import { KPIMetric, KPIBreakdown } from '../api/kpiReport';

interface KPIMetricCardProps {
    metric: KPIMetric;
    onInfoClick: (metric: KPIMetric) => void;
}

const KPIMetricCard: React.FC<KPIMetricCardProps> = ({ metric, onInfoClick }) => {
    const isKRI = metric.is_kri;

    // Render the main value based on metric type
    const renderValue = () => {
        switch (metric.metric_type) {
            case 'count':
                return (
                    <div className="text-3xl font-bold text-gray-900">
                        {metric.count_value?.toLocaleString() ?? 'N/A'}
                    </div>
                );

            case 'ratio':
                if (metric.ratio_value) {
                    const { numerator, denominator, percentage, numerator_label, denominator_label } = metric.ratio_value;
                    return (
                        <>
                            <div className="text-3xl font-bold text-gray-900">
                                {percentage.toFixed(1)}%
                            </div>
                            <div className="text-sm text-gray-500 mt-1">
                                <span className="text-blue-600 font-medium">{numerator.toLocaleString()}</span>
                                {' '}{numerator_label} /{' '}
                                <span className="text-gray-700 font-medium">{denominator.toLocaleString()}</span>
                                {' '}{denominator_label}
                            </div>
                        </>
                    );
                }
                return <div className="text-3xl font-bold text-gray-400">N/A</div>;

            case 'duration':
                if (metric.duration_value !== null) {
                    return (
                        <div className="text-3xl font-bold text-gray-900">
                            {metric.duration_value.toFixed(1)}
                            <span className="text-lg text-gray-500 ml-1">days</span>
                        </div>
                    );
                }
                return <div className="text-3xl font-bold text-gray-400">N/A</div>;

            case 'breakdown':
                if (metric.breakdown_value && metric.breakdown_value.length > 0) {
                    return <BreakdownChart data={metric.breakdown_value} />;
                }
                return <div className="text-gray-400">No data</div>;

            default:
                return <div className="text-gray-400">N/A</div>;
        }
    };

    return (
        <div
            className={`bg-white rounded-lg shadow p-4 ${
                isKRI ? 'border-2 border-red-500' : 'border border-gray-200'
            }`}
        >
            {/* Header with metric ID, name, and info button */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                        {metric.metric_id}
                    </span>
                    {isKRI && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                            KRI
                        </span>
                    )}
                </div>
                <button
                    onClick={() => onInfoClick(metric)}
                    className="text-gray-400 hover:text-blue-600 focus:outline-none"
                    title="View definition"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                </button>
            </div>

            {/* Metric name */}
            <h3 className="text-sm font-medium text-gray-700 mb-3 line-clamp-2">
                {metric.metric_name}
            </h3>

            {/* Value display */}
            <div className="mt-2">
                {renderValue()}
            </div>
        </div>
    );
};

/**
 * Simple horizontal bar chart for breakdown metrics.
 */
interface BreakdownChartProps {
    data: KPIBreakdown[];
}

const BreakdownChart: React.FC<BreakdownChartProps> = ({ data }) => {
    // Sort by count descending
    const sortedData = [...data].sort((a, b) => b.count - a.count);
    const maxCount = Math.max(...sortedData.map(d => d.count), 1);

    // Colors for different categories
    const colors = [
        'bg-blue-500',
        'bg-green-500',
        'bg-yellow-500',
        'bg-purple-500',
        'bg-pink-500',
        'bg-indigo-500',
        'bg-red-500',
        'bg-orange-500',
    ];

    return (
        <div className="space-y-2">
            {sortedData.slice(0, 5).map((item, index) => (
                <div key={item.category} className="flex items-center gap-2">
                    <div className="w-24 text-xs text-gray-600 truncate" title={item.category}>
                        {item.category}
                    </div>
                    <div className="flex-1 h-4 bg-gray-100 rounded overflow-hidden">
                        <div
                            className={`h-full ${colors[index % colors.length]} transition-all`}
                            style={{ width: `${(item.count / maxCount) * 100}%` }}
                        />
                    </div>
                    <div className="w-16 text-xs text-gray-600 text-right">
                        {item.count} ({item.percentage.toFixed(0)}%)
                    </div>
                </div>
            ))}
            {sortedData.length > 5 && (
                <div className="text-xs text-gray-400 text-center">
                    +{sortedData.length - 5} more categories
                </div>
            )}
        </div>
    );
};

export default KPIMetricCard;

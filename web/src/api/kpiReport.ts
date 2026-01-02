/**
 * KPI Report API client and TypeScript interfaces.
 */
import client from './client';

/**
 * Decomposition of a ratio/percentage metric showing numerator and denominator.
 */
export interface KPIDecomposition {
    numerator: number;
    denominator: number;
    percentage: number;
    numerator_label: string;
    denominator_label: string;
    numerator_model_ids?: number[];  // Model IDs comprising the numerator for drill-down
}

/**
 * Breakdown category for metrics showing distribution across categories.
 */
export interface KPIBreakdown {
    category: string;
    count: number;
    percentage: number;
    avg_days?: number;  // Average duration in days (for duration breakdown metrics like 4.8)
}

/**
 * Individual KPI metric with value and metadata.
 */
export interface KPIMetric {
    metric_id: string;
    metric_name: string;
    category: string;
    metric_type: 'count' | 'ratio' | 'duration' | 'breakdown';

    // Value fields - only one will be populated based on metric_type
    count_value: number | null;
    ratio_value: KPIDecomposition | null;
    duration_value: number | null;
    breakdown_value: KPIBreakdown[] | null;

    // Metadata
    definition: string;
    calculation: string;
    is_kri: boolean;
}

/**
 * Complete KPI report response.
 */
export interface KPIReportResponse {
    report_generated_at: string;
    as_of_date: string;
    metrics: KPIMetric[];
    total_active_models: number;
    // Region filter context
    region_id: number | null;
    region_name: string;
    // Team filter context
    team_id: number | null;
    team_name: string;
}

/**
 * Fetch the KPI Report with all metrics.
 * @param regionId - Optional region ID to filter metrics by models deployed to that region
 */
export const getKPIReport = async (regionId?: number, teamId?: number): Promise<KPIReportResponse> => {
    const params = new URLSearchParams();
    if (regionId !== undefined) {
        params.append('region_id', String(regionId));
    }
    if (teamId !== undefined) {
        params.append('team_id', String(teamId));
    }
    const suffix = params.toString() ? `?${params.toString()}` : '';
    const response = await client.get<KPIReportResponse>(`/kpi-report/${suffix}`);
    return response.data;
};

/**
 * Group metrics by category for display.
 */
export const groupMetricsByCategory = (metrics: KPIMetric[]): Record<string, KPIMetric[]> => {
    return metrics.reduce((acc, metric) => {
        const category = metric.category;
        if (!acc[category]) {
            acc[category] = [];
        }
        acc[category].push(metric);
        return acc;
    }, {} as Record<string, KPIMetric[]>);
};

/**
 * Get formatted value for display based on metric type.
 */
export const getDisplayValue = (metric: KPIMetric): string => {
    switch (metric.metric_type) {
        case 'count':
            return metric.count_value?.toLocaleString() ?? 'N/A';
        case 'ratio':
            if (metric.ratio_value) {
                return `${metric.ratio_value.percentage.toFixed(1)}%`;
            }
            return 'N/A';
        case 'duration':
            if (metric.duration_value !== null) {
                return `${metric.duration_value.toFixed(1)} days`;
            }
            return 'N/A';
        case 'breakdown':
            if (metric.breakdown_value && metric.breakdown_value.length > 0) {
                return `${metric.breakdown_value.length} categories`;
            }
            return 'N/A';
        default:
            return 'N/A';
    }
};

/**
 * Export KPI report data to CSV format.
 */
export const exportKPIReportToCSV = (report: KPIReportResponse): string => {
    const lines: string[] = [];

    // Report metadata header
    lines.push(`# KPI Report - ${report.region_name}`);
    if (report.team_name && report.team_name !== 'All Teams') {
        lines.push(`# Team: ${report.team_name}`);
    }
    lines.push(`# As of: ${report.as_of_date}`);
    lines.push(`# Total Active Models: ${report.total_active_models}`);
    lines.push('');

    // Column header
    lines.push('Metric ID,Metric Name,Category,Type,Value,Numerator,Denominator,Is KRI,Definition');

    for (const metric of report.metrics) {
        let value = '';
        let numerator = '';
        let denominator = '';

        switch (metric.metric_type) {
            case 'count':
                value = metric.count_value?.toString() ?? '';
                break;
            case 'ratio':
                if (metric.ratio_value) {
                    value = `${metric.ratio_value.percentage.toFixed(2)}%`;
                    numerator = metric.ratio_value.numerator.toString();
                    denominator = metric.ratio_value.denominator.toString();
                }
                break;
            case 'duration':
                value = metric.duration_value !== null ? `${metric.duration_value.toFixed(1)} days` : '';
                break;
            case 'breakdown':
                if (metric.breakdown_value) {
                    value = metric.breakdown_value.map(b => `${b.category}: ${b.count}`).join('; ');
                }
                break;
        }

        // Escape fields with commas or quotes
        const escapeCSV = (field: string) => {
            if (field.includes(',') || field.includes('"') || field.includes('\n')) {
                return `"${field.replace(/"/g, '""')}"`;
            }
            return field;
        };

        lines.push([
            escapeCSV(metric.metric_id),
            escapeCSV(metric.metric_name),
            escapeCSV(metric.category),
            escapeCSV(metric.metric_type),
            escapeCSV(value),
            escapeCSV(numerator),
            escapeCSV(denominator),
            metric.is_kri ? 'Yes' : 'No',
            escapeCSV(metric.definition),
        ].join(','));
    }

    return lines.join('\n');
};

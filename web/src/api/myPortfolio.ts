/**
 * My Portfolio Report API client
 */
import client from './client';

export interface PortfolioSummary {
    total_models: number;
    action_items_count: number;
    overdue_count: number;
    compliant_percentage: number;
    models_compliant: number;
    models_non_compliant: number;
    yellow_alerts: number;
    red_alerts: number;
}

export interface ActionItem {
    type: 'attestation' | 'recommendation' | 'validation_submission';
    urgency: 'overdue' | 'in_grace_period' | 'due_soon' | 'upcoming' | 'unknown';
    model_id: number;
    model_name: string;
    item_id: number;
    item_code: string | null;
    title: string;
    action_description: string;
    due_date: string | null;
    days_until_due: number | null;
    link: string;
}

export interface MonitoringAlert {
    model_id: number;
    model_name: string;
    metric_name: string;
    metric_value: number | null;
    qualitative_outcome: string | null;
    outcome: 'YELLOW' | 'RED';
    cycle_name: string;
    cycle_id: number;
    plan_id: number;
    result_date: string;
}

export interface CalendarItem {
    due_date: string;
    type: 'attestation' | 'recommendation' | 'validation_submission';
    model_id: number;
    model_name: string;
    item_id: number;
    item_code: string | null;
    title: string;
    is_overdue: boolean;
}

export interface PortfolioModel {
    model_id: number;
    model_name: string;
    risk_tier: string | null;
    risk_tier_code: string | null;
    approval_status: string | null;
    approval_status_code: string | null;
    last_validation_date: string | null;
    next_validation_due: string | null;
    days_until_due: number | null;
    open_recommendations: number;
    attestation_status: string | null;
    yellow_alerts: number;
    red_alerts: number;
    has_overdue_items: boolean;
    ownership_type: 'primary' | 'shared' | 'delegate';
}

export interface MyPortfolioResponse {
    report_generated_at: string;
    as_of_date: string;
    team_id: number | null;
    team_name: string;
    summary: PortfolioSummary;
    action_items: ActionItem[];
    monitoring_alerts: MonitoringAlert[];
    calendar_items: CalendarItem[];
    models: PortfolioModel[];
}

export async function getMyPortfolio(teamId?: number): Promise<MyPortfolioResponse> {
    const params = new URLSearchParams();
    if (teamId !== undefined) {
        params.append('team_id', String(teamId));
    }
    const suffix = params.toString() ? `?${params.toString()}` : '';
    const response = await client.get<MyPortfolioResponse>(`/reports/my-portfolio${suffix}`);
    return response.data;
}

/**
 * Export portfolio to PDF via backend API
 */
export async function exportPortfolioToPDF(): Promise<Blob> {
    const response = await client.get('/reports/my-portfolio/pdf', {
        responseType: 'blob',
    });
    return response.data;
}

/**
 * Get urgency badge color class based on urgency level
 */
export function getUrgencyColorClass(urgency: string): string {
    switch (urgency) {
        case 'overdue':
            return 'bg-red-100 text-red-800';
        case 'in_grace_period':
            return 'bg-orange-100 text-orange-800';
        case 'due_soon':
            return 'bg-yellow-100 text-yellow-800';
        case 'upcoming':
            return 'bg-blue-100 text-blue-800';
        default:
            return 'bg-gray-100 text-gray-800';
    }
}

/**
 * Get urgency label for display
 */
export function getUrgencyLabel(urgency: string): string {
    switch (urgency) {
        case 'overdue':
            return 'Overdue';
        case 'in_grace_period':
            return 'Grace Period';
        case 'due_soon':
            return 'Due Soon';
        case 'upcoming':
            return 'Upcoming';
        default:
            return 'Unknown';
    }
}

/**
 * Get action type icon
 */
export function getActionTypeIcon(type: string): string {
    switch (type) {
        case 'attestation':
            return '⏰';
        case 'recommendation':
            return '📋';
        case 'validation_submission':
            return '📝';
        default:
            return '📌';
    }
}

/**
 * Get ownership type label
 */
export function getOwnershipLabel(type: string): string {
    switch (type) {
        case 'primary':
            return 'Owner';
        case 'shared':
            return 'Shared Owner';
        case 'delegate':
            return 'Delegate';
        default:
            return type;
    }
}

/**
 * Format days until due for display
 */
export function formatDaysUntilDue(days: number | null): string {
    if (days === null) return 'No date';
    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    if (days === -1) return '1 day ago';
    if (days < 0) return `${Math.abs(days)} days ago`;
    return `In ${days} days`;
}

/**
 * Export portfolio to CSV
 */
export function exportPortfolioToCSV(report: MyPortfolioResponse): string {
    const lines: string[] = [];

    // Header
    lines.push('My Model Portfolio Report');
    lines.push(`Generated: ${report.report_generated_at}`);
    lines.push(`As of: ${report.as_of_date}`);
    lines.push('');

    // Summary
    lines.push('SUMMARY');
    lines.push(`Total Models,${report.summary.total_models}`);
    lines.push(`Action Items,${report.summary.action_items_count}`);
    lines.push(`Overdue Items,${report.summary.overdue_count}`);
    lines.push(`Compliance Rate,${report.summary.compliant_percentage}%`);
    lines.push(`Yellow Alerts,${report.summary.yellow_alerts}`);
    lines.push(`Red Alerts,${report.summary.red_alerts}`);
    lines.push('');

    // Action Items
    lines.push('ACTION ITEMS');
    lines.push('Type,Urgency,Model,Item Code,Title,Action,Due Date,Days Until Due');
    for (const item of report.action_items) {
        lines.push([
            item.type,
            item.urgency,
            `"${item.model_name}"`,
            item.item_code || '',
            `"${item.title}"`,
            `"${item.action_description}"`,
            item.due_date || '',
            item.days_until_due?.toString() || '',
        ].join(','));
    }
    lines.push('');

    // Monitoring Alerts
    lines.push('MONITORING ALERTS');
    lines.push('Model,Metric,Value,Outcome,Cycle,Date');
    for (const alert of report.monitoring_alerts) {
        lines.push([
            `"${alert.model_name}"`,
            `"${alert.metric_name}"`,
            alert.metric_value?.toString() || alert.qualitative_outcome || '',
            alert.outcome,
            alert.cycle_name,
            alert.result_date,
        ].join(','));
    }
    lines.push('');

    // Models
    lines.push('MODEL PORTFOLIO');
    lines.push('Model ID,Model Name,Risk Tier,Approval Status,Last Validation,Open Recs,Yellow Alerts,Red Alerts,Ownership');
    for (const model of report.models) {
        lines.push([
            model.model_id.toString(),
            `"${model.model_name}"`,
            model.risk_tier || '',
            model.approval_status || '',
            model.last_validation_date || '',
            model.open_recommendations.toString(),
            model.yellow_alerts.toString(),
            model.red_alerts.toString(),
            model.ownership_type,
        ].join(','));
    }

    return lines.join('\n');
}

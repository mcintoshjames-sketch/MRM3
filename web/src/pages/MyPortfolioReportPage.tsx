/**
 * My Model Portfolio Report Page
 * Comprehensive dashboard for model owners showing their portfolio summary,
 * action items, monitoring alerts, and calendar view.
 */
import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import {
    getMyPortfolio,
    getUrgencyColorClass,
    getUrgencyLabel,
    getActionTypeIcon,
    getOwnershipLabel,
    formatDaysUntilDue,
    exportPortfolioToCSV,
    exportPortfolioToPDF,
    MyPortfolioResponse,
    ActionItem,
    MonitoringAlert,
    CalendarItem,
    PortfolioModel,
} from '../api/myPortfolio';
import { getTeams, Team as TeamOption } from '../api/teams';

type ViewMode = 'list' | 'calendar';

const MyPortfolioReportPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [report, setReport] = useState<MyPortfolioResponse | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('list');
    const [selectedMonth, setSelectedMonth] = useState(new Date());
    const [modelFilter, setModelFilter] = useState('');
    const [riskTierFilter, setRiskTierFilter] = useState('all');
    const [teams, setTeams] = useState<TeamOption[]>([]);
    const [selectedTeam, setSelectedTeam] = useState<string>('');

    useEffect(() => {
        fetchReport();
    }, [selectedTeam]);

    useEffect(() => {
        getTeams().then((res) => setTeams(res.data)).catch(console.error);
    }, []);

    const fetchReport = async () => {
        setLoading(true);
        setError(null);
        try {
            const teamId = selectedTeam === 'unassigned'
                ? 0
                : selectedTeam
                    ? parseInt(selectedTeam)
                    : undefined;
            const data = await getMyPortfolio(teamId);
            setReport(data);
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to load portfolio report';
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    // Group action items by urgency
    const groupedActionItems = useMemo(() => {
        if (!report) return { overdue: [], in_grace_period: [], due_soon: [], upcoming: [] };

        const groups: Record<string, ActionItem[]> = {
            overdue: [],
            in_grace_period: [],
            due_soon: [],
            upcoming: [],
        };

        report.action_items.forEach(item => {
            if (groups[item.urgency]) {
                groups[item.urgency].push(item);
            } else {
                groups.upcoming.push(item);
            }
        });

        return groups;
    }, [report]);

    // Filter models
    const filteredModels = useMemo(() => {
        if (!report) return [];

        return report.models.filter(model => {
            const matchesName = model.model_name.toLowerCase().includes(modelFilter.toLowerCase());
            const matchesTier = riskTierFilter === 'all' || model.risk_tier_code === riskTierFilter;
            return matchesName && matchesTier;
        });
    }, [report, modelFilter, riskTierFilter]);

    // Get unique risk tiers for filter
    const riskTiers = useMemo(() => {
        if (!report) return [];
        const tiers = new Set(report.models.map(m => m.risk_tier_code).filter(Boolean));
        return Array.from(tiers) as string[];
    }, [report]);

    // Calendar helpers
    const calendarDays = useMemo(() => {
        const year = selectedMonth.getFullYear();
        const month = selectedMonth.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startPadding = firstDay.getDay();

        const days: (Date | null)[] = [];

        // Add padding for days before first of month
        for (let i = 0; i < startPadding; i++) {
            days.push(null);
        }

        // Add all days of the month
        for (let d = 1; d <= lastDay.getDate(); d++) {
            days.push(new Date(year, month, d));
        }

        return days;
    }, [selectedMonth]);

    const getItemsForDate = (date: Date): CalendarItem[] => {
        if (!report) return [];
        const dateStr = date.toISOString().split('T')[0];
        return report.calendar_items.filter(item => item.due_date === dateStr);
    };

    const getItemsForMonth = (): CalendarItem[] => {
        if (!report) return [];
        const year = selectedMonth.getFullYear();
        const month = selectedMonth.getMonth();
        return report.calendar_items.filter(item => {
            const itemDate = new Date(item.due_date);
            return itemDate.getFullYear() === year && itemDate.getMonth() === month;
        }).sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime());
    };

    const handleExportCSV = () => {
        if (!report) return;
        const csv = exportPortfolioToCSV(report);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `my_portfolio_${report.as_of_date}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const [exportingPDF, setExportingPDF] = useState(false);

    const handleExportPDF = async () => {
        if (!report) return;
        setExportingPDF(true);
        try {
            const blob = await exportPortfolioToPDF();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `my_portfolio_${report.as_of_date}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to export PDF:', err);
            alert('Failed to export PDF. Please try again.');
        } finally {
            setExportingPDF(false);
        }
    };

    const navigateMonth = (delta: number) => {
        setSelectedMonth(prev => {
            const newDate = new Date(prev);
            newDate.setMonth(newDate.getMonth() + delta);
            return newDate;
        });
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex justify-center items-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            </Layout>
        );
    }

    if (error) {
        return (
            <Layout>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h3 className="text-red-800 font-medium">Error Loading Report</h3>
                    <p className="text-red-600 mt-1">{error}</p>
                    <button
                        onClick={fetchReport}
                        className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                    >
                        Retry
                    </button>
                </div>
            </Layout>
        );
    }

    if (!report) {
        return (
            <Layout>
                <div className="text-center text-gray-500 py-8">No data available</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="print:p-4">
                {/* Header */}
                <div className="flex justify-between items-center mb-6 print:mb-4">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">📊 My Model Portfolio</h1>
                        <p className="text-sm text-gray-500 mt-1">
                            As of {report.as_of_date} • Generated {new Date(report.report_generated_at).toLocaleString()}
                        </p>
                    </div>
                    <div className="flex gap-2 print:hidden">
                        <div className="flex items-center gap-2">
                            <label className="text-sm font-medium text-gray-700">Team</label>
                            <select
                                value={selectedTeam}
                                onChange={(e) => setSelectedTeam(e.target.value)}
                                className="px-3 py-2 border rounded-lg text-sm"
                            >
                                <option value="">All Teams</option>
                                <option value="unassigned">Unassigned</option>
                                {teams.filter(team => team.is_active).map((team) => (
                                    <option key={team.team_id} value={String(team.team_id)}>
                                        {team.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        {/* View Toggle */}
                        <div className="flex rounded-lg border border-gray-300 overflow-hidden">
                            <button
                                onClick={() => setViewMode('list')}
                                className={`px-4 py-2 text-sm font-medium ${viewMode === 'list'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-white text-gray-700 hover:bg-gray-50'
                                    }`}
                            >
                                List
                            </button>
                            <button
                                onClick={() => setViewMode('calendar')}
                                className={`px-4 py-2 text-sm font-medium ${viewMode === 'calendar'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-white text-gray-700 hover:bg-gray-50'
                                    }`}
                            >
                                Calendar
                            </button>
                        </div>
                        <button
                            onClick={handleExportCSV}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
                        >
                            Export CSV
                        </button>
                        <button
                            onClick={handleExportPDF}
                            disabled={exportingPDF}
                            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {exportingPDF ? 'Exporting...' : 'Export PDF'}
                        </button>
                    </div>
                </div>

                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
                        <div className="text-3xl font-bold text-gray-900">{report.summary.total_models}</div>
                        <div className="text-sm text-gray-500">🏛️ Models in Scope</div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4 border-l-4 border-amber-500">
                        <div className="text-3xl font-bold text-gray-900">{report.summary.action_items_count}</div>
                        <div className="text-sm text-gray-500">⚠️ Action Items</div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
                        <div className="text-3xl font-bold text-gray-900">{report.summary.compliant_percentage.toFixed(0)}%</div>
                        <div className="text-sm text-gray-500">✅ Compliant ({report.summary.models_compliant}/{report.summary.total_models})</div>
                    </div>
                    <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
                        <div className="text-3xl font-bold text-gray-900">{report.summary.overdue_count}</div>
                        <div className="text-sm text-gray-500">🔴 Overdue Items</div>
                    </div>
                </div>

                {viewMode === 'list' ? (
                    <>
                        {/* Action Items Section */}
                        <div className="mb-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                <span className="border-t border-gray-300 flex-grow"></span>
                                <span>ACTION ITEMS ({report.action_items.length} pending)</span>
                                <span className="border-t border-gray-300 flex-grow"></span>
                            </h2>

                            {report.action_items.length === 0 ? (
                                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center text-green-700">
                                    🎉 No action items pending - you're all caught up!
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {/* Overdue */}
                                    {groupedActionItems.overdue.length > 0 && (
                                        <div>
                                            <h3 className="text-sm font-medium text-red-700 mb-2">🔴 OVERDUE ({groupedActionItems.overdue.length})</h3>
                                            <div className="bg-white rounded-lg shadow divide-y">
                                                {groupedActionItems.overdue.map((item, idx) => (
                                                    <ActionItemRow key={`overdue-${idx}`} item={item} />
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* In Grace Period */}
                                    {groupedActionItems.in_grace_period.length > 0 && (
                                        <div>
                                            <h3 className="text-sm font-medium text-orange-700 mb-2">🟠 IN GRACE PERIOD ({groupedActionItems.in_grace_period.length})</h3>
                                            <div className="bg-white rounded-lg shadow divide-y">
                                                {groupedActionItems.in_grace_period.map((item, idx) => (
                                                    <ActionItemRow key={`grace-${idx}`} item={item} />
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Due Soon */}
                                    {groupedActionItems.due_soon.length > 0 && (
                                        <div>
                                            <h3 className="text-sm font-medium text-yellow-700 mb-2">🟡 DUE SOON ({groupedActionItems.due_soon.length})</h3>
                                            <div className="bg-white rounded-lg shadow divide-y">
                                                {groupedActionItems.due_soon.map((item, idx) => (
                                                    <ActionItemRow key={`soon-${idx}`} item={item} />
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Upcoming */}
                                    {groupedActionItems.upcoming.length > 0 && (
                                        <div>
                                            <h3 className="text-sm font-medium text-blue-700 mb-2">🔵 UPCOMING ({groupedActionItems.upcoming.length})</h3>
                                            <div className="bg-white rounded-lg shadow divide-y">
                                                {groupedActionItems.upcoming.map((item, idx) => (
                                                    <ActionItemRow key={`upcoming-${idx}`} item={item} />
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Monitoring Alerts Section */}
                        <div className="mb-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                                <span className="border-t border-gray-300 flex-grow"></span>
                                <span>MONITORING ALERTS</span>
                                <span className="border-t border-gray-300 flex-grow"></span>
                            </h2>

                            <div className="flex gap-4 mb-3">
                                <span className="text-sm">
                                    🟡 Yellow: <strong>{report.summary.yellow_alerts}</strong>
                                </span>
                                <span className="text-sm">
                                    🔴 Red: <strong>{report.summary.red_alerts}</strong>
                                </span>
                            </div>

                            {report.monitoring_alerts.length === 0 ? (
                                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center text-green-700">
                                    ✅ No yellow or red monitoring alerts in the last 90 days
                                </div>
                            ) : (
                                <div className="bg-white rounded-lg shadow divide-y">
                                    {report.monitoring_alerts.map((alert, idx) => (
                                        <MonitoringAlertRow key={idx} alert={alert} />
                                    ))}
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    /* Calendar View */
                    <div className="mb-6">
                        <div className="bg-white rounded-lg shadow p-4">
                            {/* Month Navigation */}
                            <div className="flex justify-between items-center mb-4">
                                <button
                                    onClick={() => navigateMonth(-1)}
                                    className="p-2 hover:bg-gray-100 rounded"
                                >
                                    ◀
                                </button>
                                <h2 className="text-lg font-semibold">
                                    {selectedMonth.toLocaleString('default', { month: 'long', year: 'numeric' })}
                                </h2>
                                <button
                                    onClick={() => navigateMonth(1)}
                                    className="p-2 hover:bg-gray-100 rounded"
                                >
                                    ▶
                                </button>
                            </div>

                            {/* Calendar Grid */}
                            <div className="grid grid-cols-7 gap-1 mb-4">
                                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                                    <div key={day} className="text-center text-sm font-medium text-gray-500 py-2">
                                        {day}
                                    </div>
                                ))}
                                {calendarDays.map((date, idx) => {
                                    if (!date) {
                                        return <div key={`empty-${idx}`} className="p-2"></div>;
                                    }
                                    const items = getItemsForDate(date);
                                    const hasOverdue = items.some(i => i.is_overdue);
                                    const today = new Date();
                                    const isToday = date.toDateString() === today.toDateString();

                                    return (
                                        <div
                                            key={date.toISOString()}
                                            className={`p-2 min-h-[60px] border rounded ${isToday ? 'bg-blue-50 border-blue-300' :
                                                    hasOverdue ? 'bg-red-50 border-red-200' : 'border-gray-200'
                                                }`}
                                        >
                                            <div className={`text-sm ${isToday ? 'font-bold text-blue-600' : 'text-gray-700'}`}>
                                                {date.getDate()}
                                            </div>
                                            <div className="flex flex-wrap gap-1 mt-1">
                                                {items.map((item, i) => (
                                                    <span
                                                        key={i}
                                                        title={`${item.title} - ${item.model_name}`}
                                                        className={`text-xs ${item.is_overdue ? 'text-red-600' : ''}`}
                                                    >
                                                        {item.is_overdue && '🔴'}
                                                        {getActionTypeIcon(item.type)}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Legend */}
                            <div className="flex gap-4 text-sm text-gray-600 border-t pt-3">
                                <span>⏰ Attestation</span>
                                <span>📋 Recommendation</span>
                                <span>📝 Validation</span>
                                <span>🔴 Overdue</span>
                            </div>
                        </div>

                        {/* Items for Month */}
                        <div className="mt-4">
                            <h3 className="text-md font-semibold text-gray-700 mb-2">
                                Items in {selectedMonth.toLocaleString('default', { month: 'long' })}
                            </h3>
                            <div className="bg-white rounded-lg shadow divide-y">
                                {getItemsForMonth().length === 0 ? (
                                    <div className="p-4 text-center text-gray-500">
                                        No items due this month
                                    </div>
                                ) : (
                                    getItemsForMonth().map((item, idx) => (
                                        <div key={idx} className="p-3 flex items-center gap-3">
                                            <span className="text-sm text-gray-500 w-16">
                                                {new Date(item.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                            </span>
                                            <span className={item.is_overdue ? 'text-red-600' : ''}>
                                                {item.is_overdue && '🔴 '}
                                                {getActionTypeIcon(item.type)} {item.title}
                                            </span>
                                            <span className="text-gray-400">•</span>
                                            <Link
                                                to={`/models/${item.model_id}`}
                                                className="text-blue-600 hover:underline text-sm"
                                            >
                                                {item.model_name}
                                            </Link>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Model Portfolio Table */}
                <div className="mb-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <span className="border-t border-gray-300 flex-grow"></span>
                        <span>MODEL PORTFOLIO ({report.models.length} models)</span>
                        <span className="border-t border-gray-300 flex-grow"></span>
                    </h2>

                    {/* Filters */}
                    <div className="flex gap-4 mb-3 print:hidden">
                        <input
                            type="text"
                            placeholder="Search models..."
                            value={modelFilter}
                            onChange={(e) => setModelFilter(e.target.value)}
                            className="px-3 py-2 border rounded-lg text-sm w-64"
                        />
                        <select
                            value={riskTierFilter}
                            onChange={(e) => setRiskTierFilter(e.target.value)}
                            className="px-3 py-2 border rounded-lg text-sm"
                        >
                            <option value="all">All Risk Tiers</option>
                            {riskTiers.map(tier => (
                                <option key={tier} value={tier}>{tier}</option>
                            ))}
                        </select>
                    </div>

                    <div className="bg-white rounded-lg shadow overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Tier</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Validation</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Next Due</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Open Recs</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Alerts</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ownership</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                                {filteredModels.length === 0 ? (
                                    <tr>
                                        <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                                            No models match your filters
                                        </td>
                                    </tr>
                                ) : (
                                    filteredModels.map(model => (
                                        <ModelRow key={model.model_id} model={model} />
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Print Styles */}
            <style>{`
                @media print {
                    .print\\:hidden { display: none !important; }
                    .print\\:p-4 { padding: 1rem !important; }
                    .print\\:mb-4 { margin-bottom: 1rem !important; }
                    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                }
            `}</style>
        </Layout>
    );
};

// Sub-components

const ActionItemRow: React.FC<{ item: ActionItem }> = ({ item }) => {
    return (
        <div className="p-4 flex items-center justify-between hover:bg-gray-50">
            <div className="flex items-start gap-3">
                <span className="text-xl">{getActionTypeIcon(item.type)}</span>
                <div>
                    <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getUrgencyColorClass(item.urgency)}`}>
                            {getUrgencyLabel(item.urgency)}
                        </span>
                        <span className="text-sm text-gray-500 capitalize">{item.type.replace('_', ' ')}</span>
                        {item.item_code && (
                            <span className="text-sm text-gray-400">• {item.item_code}</span>
                        )}
                    </div>
                    <div className="font-medium text-gray-900 mt-1">{item.title}</div>
                    <div className="text-sm text-gray-500">
                        <Link to={`/models/${item.model_id}`} className="text-blue-600 hover:underline">
                            {item.model_name}
                        </Link>
                        {item.due_date && (
                            <span className="ml-2">
                                • Due: {item.due_date} ({formatDaysUntilDue(item.days_until_due)})
                            </span>
                        )}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">→ {item.action_description}</div>
                </div>
            </div>
            <Link
                to={item.link}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm print:hidden"
            >
                Action
            </Link>
        </div>
    );
};

const MonitoringAlertRow: React.FC<{ alert: MonitoringAlert }> = ({ alert }) => {
    const isRed = alert.outcome === 'RED';

    return (
        <div className="p-4 flex items-center justify-between hover:bg-gray-50">
            <div className="flex items-start gap-3">
                <span className="text-xl">{isRed ? '🔴' : '🟡'}</span>
                <div>
                    <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${isRed ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                            }`}>
                            {alert.outcome}
                        </span>
                        <span className="font-medium text-gray-900">{alert.metric_name}</span>
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                        <Link to={`/models/${alert.model_id}`} className="text-blue-600 hover:underline">
                            {alert.model_name}
                        </Link>
                        <span className="ml-2">
                            • Value: {alert.metric_value !== null ? alert.metric_value : alert.qualitative_outcome}
                        </span>
                        <span className="ml-2">• {alert.cycle_name}</span>
                        <span className="ml-2">• {alert.result_date}</span>
                    </div>
                </div>
            </div>
            <Link
                to={`/monitoring/${alert.plan_id}?tab=cycles`}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 text-sm print:hidden"
            >
                View
            </Link>
        </div>
    );
};

const ModelRow: React.FC<{ model: PortfolioModel }> = ({ model }) => {
    return (
        <tr className="hover:bg-gray-50">
            <td className="px-4 py-3">
                <Link to={`/models/${model.model_id}`} className="text-blue-600 hover:underline font-medium">
                    {model.model_name}
                </Link>
                {model.has_overdue_items && (
                    <span className="ml-2 text-red-500" title="Has overdue items">⚠️</span>
                )}
            </td>
            <td className="px-4 py-3 text-sm">
                {model.risk_tier ? (
                    <span className={`px-2 py-1 rounded text-xs font-medium ${model.risk_tier_code === 'TIER_1' ? 'bg-red-100 text-red-800' :
                            model.risk_tier_code === 'TIER_2' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-green-100 text-green-800'
                        }`}>
                        {model.risk_tier}
                    </span>
                ) : (
                    <span className="text-gray-400">—</span>
                )}
            </td>
            <td className="px-4 py-3 text-sm">
                {model.approval_status ? (
                    <span className={`px-2 py-1 rounded text-xs font-medium ${model.approval_status_code === 'APPROVED' ? 'bg-green-100 text-green-800' :
                            model.approval_status_code === 'INTERIM_APPROVED' ? 'bg-blue-100 text-blue-800' :
                                model.approval_status_code === 'VALIDATION_IN_PROGRESS' ? 'bg-yellow-100 text-yellow-800' :
                                    model.approval_status_code === 'EXPIRED' ? 'bg-red-100 text-red-800' :
                                        model.approval_status_code === 'NEVER_VALIDATED' ? 'bg-gray-100 text-gray-600' :
                                            'bg-gray-100 text-gray-600'
                        }`}>
                        {model.approval_status}
                    </span>
                ) : (
                    <span className="text-gray-400">—</span>
                )}
            </td>
            <td className="px-4 py-3 text-sm">{model.last_validation_date || '—'}</td>
            <td className="px-4 py-3 text-sm">
                {model.next_validation_due ? (
                    <span className={model.days_until_due !== null && model.days_until_due < 0 ? 'text-red-600 font-medium' : ''}>
                        {model.next_validation_due}
                        {model.days_until_due !== null && (
                            <span className="text-gray-400 ml-1">
                                ({formatDaysUntilDue(model.days_until_due)})
                            </span>
                        )}
                    </span>
                ) : (
                    <span className="text-gray-400">—</span>
                )}
            </td>
            <td className="px-4 py-3 text-sm">
                {model.open_recommendations > 0 ? (
                    <span className="px-2 py-1 bg-amber-100 text-amber-800 rounded text-xs font-medium">
                        {model.open_recommendations}
                    </span>
                ) : (
                    <span className="text-gray-400">0</span>
                )}
            </td>
            <td className="px-4 py-3 text-sm">
                {model.red_alerts > 0 && (
                    <span className="mr-1">🔴 {model.red_alerts}</span>
                )}
                {model.yellow_alerts > 0 && (
                    <span>🟡 {model.yellow_alerts}</span>
                )}
                {model.red_alerts === 0 && model.yellow_alerts === 0 && (
                    <span className="text-green-600">✓</span>
                )}
            </td>
            <td className="px-4 py-3 text-sm">
                <span className={`px-2 py-1 rounded text-xs ${model.ownership_type === 'primary' ? 'bg-blue-100 text-blue-800' :
                        model.ownership_type === 'shared' ? 'bg-purple-100 text-purple-800' :
                            model.ownership_type === 'developer' ? 'bg-teal-100 text-teal-800' :
                                'bg-gray-100 text-gray-800'
                    }`}>
                    {getOwnershipLabel(model.ownership_type)}
                </span>
            </td>
        </tr>
    );
};

export default MyPortfolioReportPage;

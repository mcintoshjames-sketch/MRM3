import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/client';

// Types
interface MonitoringTask {
    cycle_id: number;
    plan_id: number;
    plan_name: string;
    period_start_date: string;
    period_end_date: string;
    submission_due_date: string;
    report_due_date: string;
    status: string;
    user_role: string;
    action_needed: string;
    result_count: number;
    pending_approval_count: number;
    is_overdue: boolean;
    days_until_due: number | null;
}

const MyMonitoringTasksPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [tasks, setTasks] = useState<MonitoringTask[]>([]);

    useEffect(() => {
        const fetchTasks = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await api.get('/monitoring/my-tasks');
                setTasks(response.data);
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to load monitoring tasks');
            } finally {
                setLoading(false);
            }
        };

        fetchTasks();
    }, []);

    // Separate tasks into action required and informational
    const actionRequired = tasks.filter(t =>
        t.is_overdue ||
        t.action_needed.includes('Submit') ||
        t.action_needed.includes('Approve') ||
        t.status === 'PENDING_APPROVAL'
    );

    const informational = tasks.filter(t =>
        !t.is_overdue &&
        !t.action_needed.includes('Submit') &&
        !t.action_needed.includes('Approve') &&
        t.status !== 'PENDING_APPROVAL'
    );

    const formatPeriod = (start: string, end: string) => {
        const startDate = new Date(start);
        const endDate = new Date(end);
        const startMonth = startDate.toLocaleDateString('en-US', { month: 'short' });
        const endMonth = endDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        return `${startMonth} - ${endMonth}`;
    };

    const getStatusBadgeColor = (status: string) => {
        switch (status) {
            case 'PENDING': return 'bg-gray-100 text-gray-800';
            case 'DATA_COLLECTION': return 'bg-blue-100 text-blue-800';
            case 'ON_HOLD': return 'bg-orange-100 text-orange-800';
            case 'UNDER_REVIEW': return 'bg-yellow-100 text-yellow-800';
            case 'PENDING_APPROVAL': return 'bg-purple-100 text-purple-800';
            case 'APPROVED': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getRoleBadge = (role: string) => {
        switch (role) {
            case 'data_provider': return { label: 'Data Provider', color: 'bg-blue-100 text-blue-700' };
            case 'team_member': return { label: 'Team Member', color: 'bg-purple-100 text-purple-700' };
            case 'assignee': return { label: 'Assignee', color: 'bg-green-100 text-green-700' };
            default: return { label: role, color: 'bg-gray-100 text-gray-700' };
        }
    };

    const TaskCard: React.FC<{ task: MonitoringTask }> = ({ task }) => {
        const roleBadge = getRoleBadge(task.user_role);

        return (
            <div className={`bg-white rounded-lg border ${task.is_overdue ? 'border-red-300' : 'border-gray-200'} p-4 hover:shadow-md transition-shadow`}>
                <div className="flex items-start justify-between">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                            <Link
                                to={`/monitoring/${task.plan_id}`}
                                className="font-semibold text-gray-900 hover:text-blue-600"
                            >
                                {task.plan_name}
                            </Link>
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${roleBadge.color}`}>
                                {roleBadge.label}
                            </span>
                        </div>
                        <p className="text-sm text-gray-600">
                            {formatPeriod(task.period_start_date, task.period_end_date)}
                        </p>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadgeColor(task.status)}`}>
                        {task.status.replace(/_/g, ' ')}
                    </span>
                </div>

                <div className="mt-3 flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <span className="text-gray-600">Due: {task.submission_due_date}</span>
                    </div>
                    {task.is_overdue && (
                        <span className="text-red-600 font-medium">Overdue</span>
                    )}
                    {!task.is_overdue && task.days_until_due !== null && task.days_until_due <= 7 && (
                        <span className="text-amber-600 font-medium">
                            {task.days_until_due === 0 ? 'Due today' : `${task.days_until_due} days left`}
                        </span>
                    )}
                </div>

                <div className="mt-3 flex items-center justify-between">
                    <div className="text-sm text-gray-500">
                        {task.result_count > 0 ? (
                            <span>{task.result_count} results entered</span>
                        ) : (
                            <span className="text-amber-600">No results yet</span>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-700">{task.action_needed}</span>
                        <Link
                            to={`/monitoring/cycles/${task.cycle_id}`}
                            className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                        >
                            Open
                        </Link>
                    </div>
                </div>
            </div>
        );
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">My Monitoring Tasks</h1>
                <p className="text-gray-600 mt-1">
                    View and manage your monitoring cycle responsibilities
                </p>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
                    {error}
                </div>
            )}

            {/* ACTION REQUIRED Section */}
            <section className="mb-8">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <h2 className="text-lg font-semibold text-red-800">
                            Action Required ({actionRequired.length})
                        </h2>
                    </div>

                    {actionRequired.length === 0 ? (
                        <p className="text-red-700">No urgent tasks requiring your attention.</p>
                    ) : (
                        <div className="space-y-3">
                            {actionRequired.map(task => (
                                <TaskCard key={task.cycle_id} task={task} />
                            ))}
                        </div>
                    )}
                </div>
            </section>

            {/* INFORMATION Section */}
            <section>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <h2 className="text-lg font-semibold text-blue-800">
                            Information ({informational.length})
                        </h2>
                    </div>

                    {informational.length === 0 ? (
                        <p className="text-blue-700">No additional monitoring tasks.</p>
                    ) : (
                        <div className="space-y-3">
                            {informational.map(task => (
                                <TaskCard key={task.cycle_id} task={task} />
                            ))}
                        </div>
                    )}
                </div>
            </section>

            {/* Empty state when no tasks at all */}
            {tasks.length === 0 && !loading && !error && (
                <div className="text-center py-12 bg-gray-50 rounded-lg">
                    <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-lg font-medium text-gray-900">All caught up!</h3>
                    <p className="text-gray-500 mt-1">
                        You have no monitoring tasks assigned to you.
                    </p>
                    <Link
                        to="/monitoring-plans"
                        className="inline-block mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                        View All Plans
                    </Link>
                </div>
            )}
        </Layout>
    );
};

export default MyMonitoringTasksPage;

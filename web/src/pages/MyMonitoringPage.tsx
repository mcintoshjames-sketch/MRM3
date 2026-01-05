import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import AdminMonitoringOverview from '../components/AdminMonitoringOverview';
import { canManageMonitoringPlans } from '../utils/roleUtils';

interface MonitoringTask {
    cycle_id: number;
    plan_id: number;
    plan_name: string;
    period_start_date: string;
    period_end_date: string;
    submission_due_date: string;
    report_due_date: string;
    status: string;
    user_role: string;  // "data_provider", "team_member", or "assignee"
    action_needed: string;
    result_count: number;
    pending_approval_count: number;
    is_overdue: boolean;
    days_until_due: number | null;
}

const requiresMonitoringAction = (task: MonitoringTask) => {
    switch (task.user_role) {
        case 'data_provider':
            return task.status === 'DATA_COLLECTION';
        case 'assignee':
            return ['PENDING', 'DATA_COLLECTION', 'UNDER_REVIEW'].includes(task.status);
        case 'team_member':
            return ['UNDER_REVIEW', 'PENDING_APPROVAL'].includes(task.status);
        default:
            return false;
    }
};

export default function MyMonitoringPage() {
    const { user } = useAuth();
    const [tasks, setTasks] = useState<MonitoringTask[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'data_provider' | 'team_member' | 'assignee'>('all');
    const [includeClosed, setIncludeClosed] = useState(false);

    // Check if user is Admin - they see the governance overview instead
    const canManageMonitoringPlansFlag = canManageMonitoringPlans(user);

    useEffect(() => {
        // Only fetch tasks if not admin (admin has their own component)
        if (!canManageMonitoringPlansFlag) {
            fetchTasks();
        } else {
            setLoading(false);
        }
    }, [canManageMonitoringPlansFlag, includeClosed]);

    const fetchTasks = async () => {
        try {
            const response = await api.get('/monitoring/my-tasks', {
                params: { include_closed: includeClosed }
            });
            setTasks(response.data);
        } catch (error) {
            console.error('Failed to fetch monitoring tasks:', error);
        } finally {
            setLoading(false);
        }
    };

    const getRoleBadge = (role: string) => {
        switch (role) {
            case 'data_provider':
                return 'bg-purple-100 text-purple-800';
            case 'team_member':
                return 'bg-blue-100 text-blue-800';
            case 'assignee':
                return 'bg-green-100 text-green-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getRoleLabel = (role: string) => {
        switch (role) {
            case 'data_provider':
                return 'Data Provider';
            case 'team_member':
                return 'Team Member';
            case 'assignee':
                return 'Assignee';
            default:
                return role;
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'PENDING':
                return 'bg-gray-100 text-gray-800';
            case 'DATA_COLLECTION':
                return 'bg-blue-100 text-blue-800';
            case 'ON_HOLD':
                return 'bg-orange-100 text-orange-800';
            case 'UNDER_REVIEW':
                return 'bg-yellow-100 text-yellow-800';
            case 'PENDING_APPROVAL':
                return 'bg-orange-100 text-orange-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'PENDING':
                return 'Pending';
            case 'DATA_COLLECTION':
                return 'Data Collection';
            case 'ON_HOLD':
                return 'On Hold';
            case 'UNDER_REVIEW':
                return 'Under Review';
            case 'PENDING_APPROVAL':
                return 'Pending Approval';
            default:
                return status;
        }
    };

    const getFilteredTasks = () => {
        if (filter === 'all') {
            return tasks;
        }
        return tasks.filter(t => t.user_role === filter);
    };

    const filteredTasks = getFilteredTasks();

    // Admin users see the governance overview
    if (canManageMonitoringPlansFlag) {
        return (
            <Layout>
                <AdminMonitoringOverview />
            </Layout>
        );
    }

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-64">
                    <div className="text-gray-500">Loading...</div>
                </div>
            </Layout>
        );
    }

    // Split tasks into Action Required and Information
    const actionRequiredTasks = tasks.filter((task) => requiresMonitoringAction(task));

    // Note: Can use for two-section layout if needed
    // const informationalTasks = tasks.filter(t =>
    //     !t.is_overdue &&
    //     !t.action_needed.toLowerCase().includes('approve') &&
    //     t.status !== 'PENDING_APPROVAL'
    // );

    return (
        <Layout>
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900">My Monitoring Tasks</h1>
                <p className="mt-2 text-gray-600">
                    Monitoring cycles that require your attention
                </p>
            </div>
            <div className="flex items-center justify-between mb-6">
                <div className="text-sm text-gray-500">
                    {includeClosed ? 'Showing active and past cycles.' : 'Showing active cycles only.'}
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input
                        type="checkbox"
                        checked={includeClosed}
                        onChange={(e) => setIncludeClosed(e.target.checked)}
                    />
                    Show completed/cancelled cycles
                </label>
            </div>

            {/* Quick Stats Cards */}
            {tasks.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                        <div className="text-2xl font-bold text-gray-900">{tasks.length}</div>
                        <div className="text-sm text-gray-500">Total Active Tasks</div>
                    </div>
                    <div className={`p-4 rounded-lg border shadow-sm ${actionRequiredTasks.length > 0 ? 'bg-red-50 border-red-200' : 'bg-white border-gray-200'}`}>
                        <div className={`text-2xl font-bold ${actionRequiredTasks.length > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                            {actionRequiredTasks.length}
                        </div>
                        <div className="text-sm text-gray-500">Action Required</div>
                    </div>
                    <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                        <div className="text-2xl font-bold text-orange-600">
                            {tasks.filter(t => t.is_overdue).length}
                        </div>
                        <div className="text-sm text-gray-500">Overdue</div>
                    </div>
                    <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                        <div className="text-2xl font-bold text-purple-600">
                            {tasks.filter(t => t.status === 'PENDING_APPROVAL').length}
                        </div>
                        <div className="text-sm text-gray-500">Pending Approval</div>
                    </div>
                </div>
            )}

            {/* Filter buttons */}
            <div className="flex gap-2 mb-6">
                <button
                    onClick={() => setFilter('all')}
                    className={`px-4 py-2 rounded ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    All ({tasks.length})
                </button>
                <button
                    onClick={() => setFilter('data_provider')}
                    className={`px-4 py-2 rounded ${filter === 'data_provider' ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    Data Provider ({tasks.filter(t => t.user_role === 'data_provider').length})
                </button>
                <button
                    onClick={() => setFilter('team_member')}
                    className={`px-4 py-2 rounded ${filter === 'team_member' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    Team Member ({tasks.filter(t => t.user_role === 'team_member').length})
                </button>
                <button
                    onClick={() => setFilter('assignee')}
                    className={`px-4 py-2 rounded ${filter === 'assignee' ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    Assignee ({tasks.filter(t => t.user_role === 'assignee').length})
                </button>
            </div>

            {filteredTasks.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md p-8 text-center">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="mt-2 text-lg font-medium text-gray-900">
                        {filter === 'all' ? 'No Monitoring Tasks' : `No ${getRoleLabel(filter)} Tasks`}
                    </h3>
                    <p className="mt-1 text-sm text-gray-500">
                        {filter === 'all'
                            ? 'You don\'t have any active monitoring cycles assigned to you.'
                            : `You don't have any tasks as a ${getRoleLabel(filter).toLowerCase()}.`
                        }
                    </p>
                </div>
            ) : (
                <div className="bg-white rounded-lg shadow-md overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Role
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Plan
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Period
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Status
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Due Date
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Action Needed
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {filteredTasks.map((task) => (
                                <tr key={task.cycle_id} className={`hover:bg-gray-50 ${requiresMonitoringAction(task) && task.is_overdue ? 'bg-red-50' : ''}`}>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs font-semibold rounded ${getRoleBadge(task.user_role)}`}>
                                            {getRoleLabel(task.user_role)}
                                        </span>
                                    </td>
                                    <td className="px-4 py-2">
                                        <Link
                                            to={`/monitoring/${task.plan_id}`}
                                            className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                        >
                                            {task.plan_name}
                                        </Link>
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                        {task.period_start_date.split('T')[0]} - {task.period_end_date.split('T')[0]}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs font-semibold rounded ${getStatusBadge(task.status)}`}>
                                            {getStatusLabel(task.status)}
                                        </span>
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <div className="text-sm text-gray-900">
                                            {task.user_role === 'team_member'
                                                ? task.report_due_date.split('T')[0]
                                                : task.submission_due_date.split('T')[0]
                                            }
                                        </div>
                                        {requiresMonitoringAction(task) && task.is_overdue ? (
                                            <div className="text-xs font-medium text-red-600">
                                                Overdue
                                            </div>
                                        ) : task.days_until_due !== null && (
                                            <div className={`text-xs font-medium ${
                                                task.days_until_due < 7 ? 'text-orange-600' :
                                                task.days_until_due < 30 ? 'text-yellow-600' :
                                                'text-gray-500'
                                            }`}>
                                                {task.days_until_due} days left
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <span className={`text-sm font-medium ${
                                            task.action_needed.includes('Submit') ? 'text-blue-600' :
                                            task.action_needed.includes('Review') ? 'text-yellow-600' :
                                            task.action_needed.includes('Approve') ? 'text-green-600' :
                                            'text-gray-600'
                                        }`}>
                                            {task.action_needed}
                                        </span>
                                        {task.result_count > 0 && (
                                            <div className="text-xs text-gray-500">
                                                {task.result_count} result{task.result_count !== 1 ? 's' : ''} entered
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        <Link
                                            to={`/monitoring/${task.plan_id}?cycle=${task.cycle_id}`}
                                            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                                        >
                                            {task.user_role === 'data_provider' && task.status === 'DATA_COLLECTION'
                                                ? 'Enter Results'
                                                : task.user_role === 'team_member' && task.status === 'PENDING_APPROVAL'
                                                ? 'Approve'
                                                : 'View Cycle'
                                            }
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {/* Summary Footer */}
                    <div className="bg-gray-50 px-4 py-2 border-t border-gray-200">
                        <div className="text-sm text-gray-600">
                            {filter !== 'all' ? (
                                <>
                                    Showing <span className="font-medium">{filteredTasks.length}</span> of <span className="font-medium">{tasks.length}</span> total task{tasks.length !== 1 ? 's' : ''}
                                </>
                            ) : (
                                <>
                                    <span className="font-medium">{tasks.length}</span> total task{tasks.length !== 1 ? 's' : ''} •
                                    <span className="ml-2 font-medium text-red-600">
                                        {tasks.filter(t => t.is_overdue).length}
                                    </span> overdue •
                                    <span className="ml-2 font-medium text-purple-600">
                                        {tasks.filter(t => t.user_role === 'data_provider').length}
                                    </span> as data provider •
                                    <span className="ml-2 font-medium text-blue-600">
                                        {tasks.filter(t => t.user_role === 'team_member').length}
                                    </span> as team member
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Help Text */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex">
                    <svg className="h-5 w-5 text-blue-600 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <div className="text-sm text-blue-800">
                        <p className="font-medium">Monitoring Roles Definitions</p>
                        <ul className="mt-2 list-disc list-inside space-y-1">
                            <li><strong>Data Provider:</strong> You are responsible for providing monitoring data for this plan. Submit results during the Data Collection phase.</li>
                            <li><strong>Team Member:</strong> You are part of the monitoring team (risk function) responsible for reviewing and approving results.</li>
                            <li><strong>Assignee:</strong> You have been specifically assigned to this monitoring cycle.</li>
                        </ul>
                    </div>
                </div>
            </div>
        </Layout>
    );
}

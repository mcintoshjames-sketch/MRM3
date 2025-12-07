import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface PendingApproval {
    approval_id: number;
    request_id: number;
    model_ids: number[];
    model_names: string[];
    validation_type: string;
    priority: string;
    current_status: string;
    requestor_name: string;
    primary_validator: string | null;
    target_completion_date: string | null;
    approval_type: string;
    approver_role: string;
    is_required: boolean;
    represented_region: string | null;
    days_pending: number;
    request_date: string;
}

export default function ApproverDashboardPage() {
    const { user } = useAuth();
    const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchPendingApprovals();
    }, []);

    const fetchPendingApprovals = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get('/validation-workflow/my-pending-approvals');
            setPendingApprovals(response.data);
        } catch (err: any) {
            console.error('Failed to fetch pending approvals:', err);
            setError(err.response?.data?.detail || 'Failed to load pending approvals');
        } finally {
            setLoading(false);
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'Critical': return 'bg-red-100 text-red-800';
            case 'High': return 'bg-orange-100 text-orange-800';
            case 'Medium': return 'bg-yellow-100 text-yellow-800';
            case 'Low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getApprovalTypeColor = (approvalType: string) => {
        switch (approvalType) {
            case 'Global': return 'bg-blue-100 text-blue-800';
            case 'Regional': return 'bg-purple-100 text-purple-800';
            case 'Conditional': return 'bg-orange-100 text-orange-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getUrgencyColor = (daysPending: number) => {
        if (daysPending >= 7) return 'bg-red-100 text-red-800';
        if (daysPending >= 3) return 'bg-yellow-100 text-yellow-800';
        return 'bg-green-100 text-green-800';
    };

    const getRoleDisplay = () => {
        if (user?.role === 'Admin') return 'Administrator';
        if (user?.role === 'Global Approver') return 'Global Approver';
        if (user?.role === 'Regional Approver') return 'Regional Approver';
        return user?.role || 'User';
    };

    // Group approvals by urgency
    const urgentApprovals = pendingApprovals.filter(a => a.days_pending >= 7);
    const needsAttention = pendingApprovals.filter(a => a.days_pending >= 3 && a.days_pending < 7);
    const normalApprovals = pendingApprovals.filter(a => a.days_pending < 3);

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="mb-6">
                <h2 className="text-2xl font-bold">Approver Dashboard</h2>
                <p className="text-gray-600 mt-1">
                    Welcome, {user?.full_name}. You are logged in as <span className="font-medium">{getRoleDisplay()}</span>.
                </p>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500">Total Pending</div>
                    <div className="text-3xl font-bold text-blue-600">{pendingApprovals.length}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow border-l-4 border-red-500">
                    <div className="text-sm text-gray-500">Urgent (7+ days)</div>
                    <div className="text-3xl font-bold text-red-600">{urgentApprovals.length}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow border-l-4 border-yellow-500">
                    <div className="text-sm text-gray-500">Needs Attention (3-6 days)</div>
                    <div className="text-3xl font-bold text-yellow-600">{needsAttention.length}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow border-l-4 border-green-500">
                    <div className="text-sm text-gray-500">New (&lt;3 days)</div>
                    <div className="text-3xl font-bold text-green-600">{normalApprovals.length}</div>
                </div>
            </div>

            {/* Urgent Approvals Section */}
            {urgentApprovals.length > 0 && (
                <div className="bg-white rounded-lg shadow-md mb-6 border-l-4 border-red-500">
                    <div className="p-4 border-b bg-red-50">
                        <h3 className="text-lg font-bold text-red-900 flex items-center gap-2">
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                            Urgent - Awaiting Your Approval
                        </h3>
                        <p className="text-sm text-red-700 mt-1">These validation requests have been pending for 7+ days</p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model(s)</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation Type</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Your Approval</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Pending</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {urgentApprovals.map((approval) => (
                                    <tr key={approval.approval_id} className="hover:bg-red-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                            #{approval.request_id}
                                        </td>
                                        <td className="px-6 py-4">
                                            {approval.model_ids.length === 1 ? (
                                                <Link
                                                    to={`/models/${approval.model_ids[0]}`}
                                                    className="font-medium text-blue-600 hover:text-blue-800"
                                                >
                                                    {approval.model_names[0]}
                                                </Link>
                                            ) : (
                                                <div className="space-y-1">
                                                    {approval.model_names.map((name, idx) => (
                                                        <div key={idx}>
                                                            <Link
                                                                to={`/models/${approval.model_ids[idx]}`}
                                                                className="font-medium text-blue-600 hover:text-blue-800 text-sm"
                                                            >
                                                                {name}
                                                            </Link>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {approval.validation_type}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(approval.priority)}`}>
                                                {approval.priority}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getApprovalTypeColor(approval.approval_type)}`}>
                                                {approval.approval_type}
                                            </span>
                                            {approval.represented_region && (
                                                <span className="ml-1 text-xs text-gray-500">
                                                    ({approval.represented_region})
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${getUrgencyColor(approval.days_pending)}`}>
                                                {approval.days_pending} days
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/validation-workflow/${approval.request_id}`}
                                                className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
                                            >
                                                Review & Approve
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* All Pending Approvals Section */}
            <div className="bg-white rounded-lg shadow-md">
                <div className="p-4 border-b bg-blue-50">
                    <h3 className="text-lg font-bold">All Pending Approvals</h3>
                    <p className="text-sm text-gray-600">Validation requests awaiting your approval</p>
                </div>
                {pendingApprovals.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <p className="text-lg font-medium">All caught up!</p>
                        <p className="text-sm">You have no pending approvals at this time.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model(s)</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validation Type</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Requestor</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validator</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Your Approval</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Pending</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {pendingApprovals.map((approval) => (
                                    <tr key={approval.approval_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                            #{approval.request_id}
                                        </td>
                                        <td className="px-6 py-4">
                                            {approval.model_ids.length === 1 ? (
                                                <Link
                                                    to={`/models/${approval.model_ids[0]}`}
                                                    className="font-medium text-blue-600 hover:text-blue-800"
                                                >
                                                    {approval.model_names[0]}
                                                </Link>
                                            ) : (
                                                <div className="space-y-1">
                                                    {approval.model_names.map((name, idx) => (
                                                        <div key={idx}>
                                                            <Link
                                                                to={`/models/${approval.model_ids[idx]}`}
                                                                className="font-medium text-blue-600 hover:text-blue-800 text-sm"
                                                            >
                                                                {name}
                                                            </Link>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {approval.validation_type}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(approval.priority)}`}>
                                                {approval.priority}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {approval.requestor_name}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {approval.primary_validator || <span className="text-gray-400">Not assigned</span>}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getApprovalTypeColor(approval.approval_type)}`}>
                                                {approval.approval_type}
                                            </span>
                                            {approval.represented_region && (
                                                <span className="ml-1 text-xs text-gray-500">
                                                    ({approval.represented_region})
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded ${getUrgencyColor(approval.days_pending)}`}>
                                                {approval.days_pending} days
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {approval.target_completion_date?.split('T')[0] || '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/validation-workflow/${approval.request_id}`}
                                                className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                            >
                                                Review & Approve
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Quick Actions */}
            <div className="mt-6 bg-white rounded-lg shadow-md p-4">
                <h3 className="text-lg font-bold mb-3">Quick Actions</h3>
                <div className="flex gap-4">
                    <Link
                        to="/validation-workflow"
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    >
                        View All Validation Projects
                    </Link>
                    <Link
                        to="/models"
                        className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                    >
                        Browse Model Inventory
                    </Link>
                    <button
                        onClick={fetchPendingApprovals}
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                    >
                        Refresh
                    </button>
                </div>
            </div>
        </Layout>
    );
}

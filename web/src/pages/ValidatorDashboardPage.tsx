import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface ValidationRequest {
    request_id: number;
    model_id: number;
    model_name: string;
    request_date: string;
    requestor_name: string;
    validation_type: string;
    priority: string;
    target_completion_date: string;
    current_status: string;
    days_in_status: number;
    primary_validator: string | null;
    created_at: string;
}

interface Assignment {
    assignment_id: number;
    request_id: number;
    validator: {
        user_id: number;
        full_name: string;
    };
    is_primary: boolean;
    is_reviewer: boolean;
    estimated_hours: number | null;
    actual_hours: number | null;
}

export default function ValidatorDashboardPage() {
    const { user } = useAuth();
    const [myAssignments, setMyAssignments] = useState<ValidationRequest[]>([]);
    const [myReviews, setMyReviews] = useState<ValidationRequest[]>([]);
    const [pendingRequests, setPendingRequests] = useState<ValidationRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [claimingId, setClaimingId] = useState<number | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch all validation requests and detailed assignments
            const [requestsRes, assignmentsRes] = await Promise.all([
                api.get('/validation-workflow/requests/'),
                api.get('/validation-workflow/assignments/')
            ]);

            const allRequests: ValidationRequest[] = requestsRes.data;
            const allAssignments: Assignment[] = assignmentsRes.data;

            // Filter for my primary assignments
            const myWork = allRequests.filter(
                req => req.primary_validator === user?.full_name
            );
            setMyAssignments(myWork);

            // Filter for validations where I'm assigned as reviewer and status is REVIEW
            const myReviewerAssignments = allAssignments.filter(
                a => a.validator.user_id === user?.user_id && a.is_reviewer
            );
            const myReviewRequestIds = new Set(myReviewerAssignments.map(a => a.request_id));
            const reviewWork = allRequests.filter(
                req => myReviewRequestIds.has(req.request_id) && req.current_status === 'Review'
            );
            setMyReviews(reviewWork);

            // Filter for pending requests (Intake/Planning) that are unassigned
            const pending = allRequests.filter(
                req => (req.current_status === 'Intake' || req.current_status === 'Planning') && !req.primary_validator
            );
            setPendingRequests(pending);

        } catch (err: any) {
            console.error('Failed to fetch dashboard data:', err);
            setError(err.response?.data?.detail || 'Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    };

    const claimRequest = async (requestId: number) => {
        if (!user) return;

        try {
            setClaimingId(requestId);
            setError(null);

            await api.post(`/validation-workflow/requests/${requestId}/assignments`, {
                validator_id: user.user_id,
                is_primary: true,
                independence_attestation: true
            });

            // Refresh data to show the request in my assignments
            await fetchData();
        } catch (err: any) {
            console.error('Failed to claim request:', err);
            setError(err.response?.data?.detail || 'Failed to claim validation request');
        } finally {
            setClaimingId(null);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Intake': return 'bg-gray-100 text-gray-800';
            case 'Planning': return 'bg-blue-100 text-blue-800';
            case 'In Progress': return 'bg-yellow-100 text-yellow-800';
            case 'Review': return 'bg-purple-100 text-purple-800';
            case 'Pending Approval': return 'bg-orange-100 text-orange-800';
            case 'Approved': return 'bg-green-100 text-green-800';
            case 'On Hold': return 'bg-red-100 text-red-800';
            case 'Cancelled': return 'bg-gray-400 text-white';
            default: return 'bg-gray-100 text-gray-800';
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

    const activeAssignments = myAssignments.filter(
        req => !['Approved', 'Cancelled'].includes(req.current_status)
    );

    const completedAssignments = myAssignments.filter(
        req => req.current_status === 'Approved'
    );

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
                <h2 className="text-2xl font-bold">Validator Dashboard</h2>
                <p className="text-gray-600 mt-1">
                    Welcome back, {user?.full_name}. Here's your validation workload.
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
                    <div className="text-sm text-gray-500">Active Assignments</div>
                    <div className="text-3xl font-bold text-blue-600">{activeAssignments.length}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500">Pending Reviews</div>
                    <div className="text-3xl font-bold text-purple-600">{myReviews.length}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500">Completed This Month</div>
                    <div className="text-3xl font-bold text-green-600">{completedAssignments.length}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500">Unassigned Requests</div>
                    <div className="text-3xl font-bold text-orange-600">{pendingRequests.length}</div>
                </div>
            </div>

            {/* My Active Assignments */}
            <div className="bg-white rounded-lg shadow-md mb-6">
                <div className="p-4 border-b bg-blue-50">
                    <h3 className="text-lg font-bold">My Active Assignments</h3>
                    <p className="text-sm text-gray-600">Validation requests where you are the primary validator</p>
                </div>
                {activeAssignments.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">
                        No active assignments. Check pending requests below or wait to be assigned.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {activeAssignments.map((req) => (
                                    <tr key={req.request_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                            #{req.request_id}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/models/${req.model_id}`}
                                                className="font-medium text-blue-600 hover:text-blue-800"
                                            >
                                                {req.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.validation_type}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(req.priority)}`}>
                                                {req.priority}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getStatusColor(req.current_status)}`}>
                                                {req.current_status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.target_completion_date}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/validation-workflow/${req.request_id}`}
                                                className={`px-3 py-1 rounded text-sm ${
                                                    req.current_status === 'Intake' || req.current_status === 'Planning'
                                                        ? 'bg-green-600 text-white hover:bg-green-700'
                                                        : req.current_status === 'In Progress'
                                                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                                                        : 'bg-gray-600 text-white hover:bg-gray-700'
                                                }`}
                                            >
                                                {req.current_status === 'Intake' || req.current_status === 'Planning'
                                                    ? 'Begin Work'
                                                    : req.current_status === 'In Progress'
                                                    ? 'Continue Work'
                                                    : 'View Status'}
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Pending Reviews */}
            {myReviews.length > 0 && (
                <div className="bg-white rounded-lg shadow-md mb-6">
                    <div className="p-4 border-b bg-purple-50">
                        <h3 className="text-lg font-bold">Pending Reviews</h3>
                        <p className="text-sm text-gray-600">Validation requests awaiting your review</p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Primary Validator</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {myReviews.map((req) => (
                                    <tr key={req.request_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                            #{req.request_id}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/models/${req.model_id}`}
                                                className="font-medium text-blue-600 hover:text-blue-800"
                                            >
                                                {req.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.validation_type}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(req.priority)}`}>
                                                {req.priority}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.primary_validator}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.target_completion_date}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/validation-workflow/${req.request_id}`}
                                                className="bg-purple-600 text-white px-3 py-1 rounded text-sm hover:bg-purple-700"
                                            >
                                                Review Now
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Pending Requests Available for Assignment */}
            <div className="bg-white rounded-lg shadow-md">
                <div className="p-4 border-b bg-orange-50">
                    <h3 className="text-lg font-bold">Pending Validation Requests</h3>
                    <p className="text-sm text-gray-600">Requests awaiting validator assignment</p>
                </div>
                {pendingRequests.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">
                        No pending requests at this time.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Requestor</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assigned To</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Request Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {pendingRequests.map((req) => (
                                    <tr key={req.request_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                            #{req.request_id}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/models/${req.model_id}`}
                                                className="font-medium text-blue-600 hover:text-blue-800"
                                            >
                                                {req.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.requestor_name}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.validation_type}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(req.priority)}`}>
                                                {req.priority}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${getStatusColor(req.current_status)}`}>
                                                {req.current_status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.primary_validator || (
                                                <span className="text-orange-600 font-medium">Unassigned</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {req.request_date}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => claimRequest(req.request_id)}
                                                    disabled={claimingId === req.request_id || !!req.primary_validator}
                                                    className={`px-3 py-1 rounded text-sm ${
                                                        req.primary_validator
                                                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                                            : claimingId === req.request_id
                                                            ? 'bg-green-400 text-white cursor-wait'
                                                            : 'bg-green-600 text-white hover:bg-green-700'
                                                    }`}
                                                >
                                                    {claimingId === req.request_id
                                                        ? 'Claiming...'
                                                        : req.primary_validator
                                                        ? 'Assigned'
                                                        : 'Claim'}
                                                </button>
                                                <Link
                                                    to={`/validation-workflow/${req.request_id}`}
                                                    className="text-blue-600 hover:text-blue-800 text-sm py-1"
                                                >
                                                    View
                                                </Link>
                                            </div>
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
                        View All Validation Requests
                    </Link>
                    <Link
                        to="/models"
                        className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                    >
                        Browse Model Inventory
                    </Link>
                </div>
            </div>
        </Layout>
    );
}

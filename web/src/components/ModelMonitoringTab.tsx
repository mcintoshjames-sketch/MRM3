import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';

interface MonitoringPlanVersion {
    version_id: number;
    version_number: number;
    version_name: string;
    is_active: boolean;
}

interface MonitoringPlan {
    plan_id: number;
    plan_name: string;
    frequency: string;
    active_version: MonitoringPlanVersion | null;
    all_versions: MonitoringPlanVersion[];
    latest_cycle_status: string | null;
    latest_cycle_outcome_summary: string | null;
}

interface AllPlan {
    plan_id: number;
    name: string;
    frequency: string;
    is_active: boolean;
    model_count?: number;
}

interface MonitoringManagerWithLOB {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
    lob_id: number;
    lob_name: string | null;
    lob_rollup_name: string | null;
}

interface ModelMonitoringTabProps {
    modelId: number;
    modelName: string;
    monitoringManager?: MonitoringManagerWithLOB | null;
}

const ModelMonitoringTab: React.FC<ModelMonitoringTabProps> = ({ modelId, modelName, monitoringManager }) => {
    const { user } = useAuth();
    const [plans, setPlans] = useState<MonitoringPlan[]>([]);
    const [allPlans, setAllPlans] = useState<AllPlan[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showAddDropdown, setShowAddDropdown] = useState(false);
    const [addingToPlan, setAddingToPlan] = useState(false);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const isAdmin = user?.role === 'Admin';

    const fetchMonitoringPlans = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get(`/models/${modelId}/monitoring-plans`);
            setPlans(response.data);
        } catch (err) {
            console.error('Failed to fetch monitoring plans:', err);
            setError('Failed to load monitoring plans');
        } finally {
            setLoading(false);
        }
    };

    const fetchAllPlans = async () => {
        try {
            const response = await api.get('/monitoring/plans?include_inactive=false');
            setAllPlans(response.data);
        } catch (err) {
            console.error('Failed to fetch all plans:', err);
        }
    };

    useEffect(() => {
        fetchMonitoringPlans();
        if (isAdmin) {
            fetchAllPlans();
        }
    }, [modelId, isAdmin]);

    // Get plans that don't already include this model
    const availablePlans = allPlans.filter(
        ap => !plans.some(p => p.plan_id === ap.plan_id)
    );

    const handleAddToExistingPlan = async (planId: number) => {
        try {
            setAddingToPlan(true);
            setError(null);

            // First get the current plan details to get existing model_ids
            const planResponse = await api.get(`/monitoring/plans/${planId}`);
            const existingModelIds = planResponse.data.models?.map((m: { model_id: number }) => m.model_id) || [];

            // Add the new model to the list
            const updatedModelIds = [...existingModelIds, modelId];

            // Update the plan with the new model
            await api.patch(`/monitoring/plans/${planId}`, {
                model_ids: updatedModelIds
            });

            // Refresh the plans list
            await fetchMonitoringPlans();
            await fetchAllPlans();

            setShowAddDropdown(false);
            setSuccessMessage(`Successfully added "${modelName}" to the monitoring plan`);
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err) {
            console.error('Failed to add model to plan:', err);
            setError('Failed to add model to plan. Please try again.');
        } finally {
            setAddingToPlan(false);
        }
    };

    // Format cycle status for display
    const formatStatus = (status: string | null): string => {
        if (!status) return 'No cycles';
        return status.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
    };

    // Get status badge color
    const getStatusColor = (status: string | null): string => {
        if (!status) return 'bg-gray-100 text-gray-600';
        switch (status.toUpperCase()) {
            case 'APPROVED':
                return 'bg-green-100 text-green-800';
            case 'PENDING_APPROVAL':
                return 'bg-yellow-100 text-yellow-800';
            case 'DATA_COLLECTION':
                return 'bg-blue-100 text-blue-800';
            case 'ON_HOLD':
                return 'bg-orange-100 text-orange-800';
            case 'UNDER_REVIEW':
                return 'bg-purple-100 text-purple-800';
            case 'PENDING':
                return 'bg-gray-100 text-gray-600';
            default:
                return 'bg-gray-100 text-gray-600';
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">Loading monitoring plans...</span>
            </div>
        );
    }

    if (error && plans.length === 0) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-700">{error}</p>
                <button
                    onClick={() => window.location.reload()}
                    className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
                >
                    Try again
                </button>
            </div>
        );
    }

    // Empty state
    if (plans.length === 0) {
        return (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
                <svg
                    className="mx-auto h-12 w-12 text-gray-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                </svg>
                <h3 className="mt-4 text-lg font-medium text-gray-900">No Monitoring Plan</h3>
                <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto">
                    This model is not currently included in any performance monitoring plan.
                    Performance monitoring tracks key metrics over time to ensure the model
                    continues to perform as expected.
                </p>
                {isAdmin && (
                    <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
                        <Link
                            to={`/monitoring-plans?model=${modelId}`}
                            className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                            Create New Plan
                        </Link>
                        {availablePlans.length > 0 && (
                            <div className="relative inline-block">
                                <button
                                    onClick={() => setShowAddDropdown(!showAddDropdown)}
                                    className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                                >
                                    Add to Existing Plan
                                    <svg className="ml-2 -mr-1 h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                                    </svg>
                                </button>
                                {showAddDropdown && (
                                    <div className="absolute z-10 mt-1 w-64 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5">
                                        <div className="py-1 max-h-60 overflow-auto">
                                            {availablePlans.map(plan => (
                                                <button
                                                    key={plan.plan_id}
                                                    onClick={() => handleAddToExistingPlan(plan.plan_id)}
                                                    disabled={addingToPlan}
                                                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
                                                >
                                                    <div className="font-medium">{plan.name}</div>
                                                    <div className="text-xs text-gray-500">{plan.frequency}</div>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        );
    }

    // Plans list
    return (
        <div className="space-y-4">
            {/* Monitoring Manager */}
            <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg p-4">
                <div className="flex items-center gap-3">
                    <div className="flex-shrink-0">
                        <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                            <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                    </div>
                    <div className="flex-1">
                        <p className="text-xs font-medium text-purple-600 uppercase tracking-wide mb-0.5">Monitoring Manager</p>
                        {monitoringManager ? (
                            <>
                                <p className="text-sm font-medium text-gray-900">{monitoringManager.full_name}</p>
                                <p className="text-xs text-gray-500">{monitoringManager.email}</p>
                                {monitoringManager.lob_rollup_name && (
                                    <p className="text-xs text-blue-600 mt-0.5">{monitoringManager.lob_rollup_name}</p>
                                )}
                            </>
                        ) : (
                            <p className="text-sm text-gray-400 italic">No monitoring manager assigned</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Success message */}
            {successMessage && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <p className="text-sm text-green-700">{successMessage}</p>
                </div>
            )}

            {/* Error message */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-sm text-red-700">{error}</p>
                </div>
            )}

            {/* Header with actions */}
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">
                    Monitoring Plans ({plans.length})
                </h3>
                {isAdmin && (
                    <div className="flex items-center gap-3">
                        {availablePlans.length > 0 && (
                            <div className="relative">
                                <button
                                    onClick={() => setShowAddDropdown(!showAddDropdown)}
                                    className="text-sm text-gray-600 hover:text-gray-800 hover:underline flex items-center"
                                >
                                    + Add to Existing Plan
                                    <svg className="ml-1 h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                                    </svg>
                                </button>
                                {showAddDropdown && (
                                    <div className="absolute right-0 z-10 mt-1 w-64 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5">
                                        <div className="py-1 max-h-60 overflow-auto">
                                            {availablePlans.map(plan => (
                                                <button
                                                    key={plan.plan_id}
                                                    onClick={() => handleAddToExistingPlan(plan.plan_id)}
                                                    disabled={addingToPlan}
                                                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
                                                >
                                                    <div className="font-medium">{plan.name}</div>
                                                    <div className="text-xs text-gray-500">{plan.frequency}</div>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                        <Link
                            to={`/monitoring-plans?model=${modelId}`}
                            className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                        >
                            + Create New Plan
                        </Link>
                    </div>
                )}
            </div>

            {/* Plans table */}
            <div className="bg-white shadow overflow-hidden rounded-lg">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Plan Name
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Frequency
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Current Cycle Status
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Latest Results
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {plans.map((plan) => (
                            <tr key={plan.plan_id} className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="text-sm font-medium text-gray-900">
                                        {plan.plan_name}
                                    </div>
                                    {plan.active_version && (
                                        <div className="text-xs text-gray-500">
                                            Version: {plan.active_version.version_name}
                                        </div>
                                    )}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span className="text-sm text-gray-700">{plan.frequency}</span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span
                                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(
                                            plan.latest_cycle_status
                                        )}`}
                                    >
                                        {formatStatus(plan.latest_cycle_status)}
                                    </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    {plan.latest_cycle_outcome_summary ? (
                                        <span className="text-sm text-gray-700">
                                            {plan.latest_cycle_outcome_summary}
                                        </span>
                                    ) : (
                                        <span className="text-sm text-gray-400 italic">
                                            No results yet
                                        </span>
                                    )}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                                    <Link
                                        to={`/monitoring/${plan.plan_id}`}
                                        className="text-blue-600 hover:text-blue-800 hover:underline"
                                    >
                                        View
                                    </Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Summary info */}
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
                <p className="text-sm text-blue-700">
                    <strong>Tip:</strong> Monitoring plans track key performance metrics over time.
                    Click "View" to see detailed cycle history, results, and trends for each plan.
                </p>
            </div>
        </div>
    );
};

export default ModelMonitoringTab;

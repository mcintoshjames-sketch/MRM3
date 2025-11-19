import { useState, useEffect } from 'react';
import api from '../api/client';
import Layout from '../components/Layout';

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
    sort_order: number;
}

interface ValidationPolicy {
    policy_id: number;
    risk_tier_id: number;
    risk_tier: TaxonomyValue;
    frequency_months: number;
    model_change_lead_time_days: number;
    description: string | null;
    created_at: string;
    updated_at: string;
}

export default function ValidationPoliciesPage() {
    const [policies, setPolicies] = useState<ValidationPolicy[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [editingPolicy, setEditingPolicy] = useState<number | null>(null);
    const [editFormData, setEditFormData] = useState({
        frequency_months: 12,
        model_change_lead_time_days: 90,
        description: ''
    });

    useEffect(() => {
        fetchPolicies();
    }, []);

    const fetchPolicies = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get('/validations/policies/');
            // Sort by risk tier sort_order to maintain consistent ordering
            const sortedPolicies = [...response.data].sort((a, b) => {
                return (a.risk_tier.sort_order || 0) - (b.risk_tier.sort_order || 0);
            });
            setPolicies(sortedPolicies);
        } catch (err) {
            console.error('Failed to fetch validation policies:', err);
            setError('Failed to load validation policies');
        } finally {
            setLoading(false);
        }
    };

    const startEditing = (policy: ValidationPolicy) => {
        setEditingPolicy(policy.policy_id);
        setEditFormData({
            frequency_months: policy.frequency_months,
            model_change_lead_time_days: policy.model_change_lead_time_days,
            description: policy.description || ''
        });
    };

    const cancelEditing = () => {
        setEditingPolicy(null);
        setEditFormData({
            frequency_months: 12,
            model_change_lead_time_days: 90,
            description: ''
        });
    };

    const handleUpdate = async (policyId: number) => {
        try {
            await api.patch(`/validations/policies/${policyId}`, editFormData);
            await fetchPolicies();
            cancelEditing();
        } catch (err) {
            console.error('Failed to update policy:', err);
            setError('Failed to update validation policy');
        }
    };

    if (loading) {
        return (
            <Layout>
                <div>Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="mb-6">
                <h1 className="text-2xl font-bold mb-2">Validation Policies</h1>
                <p className="text-gray-600">
                    Configure validation frequency and model change lead times by risk tier.
                    These policies govern when validations are required.
                </p>
            </div>

            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded">
                    {error}
                </div>
            )}

            <div className="bg-white rounded-lg shadow">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Risk Tier
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Re-Validation Frequency
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Model Change Lead Time
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Description
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {policies.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                                    No validation policies configured. Run the seed script to create default policies.
                                </td>
                            </tr>
                        ) : (
                            policies.map(policy => (
                                <tr key={policy.policy_id}>
                                    {editingPolicy === policy.policy_id ? (
                                        // Edit mode
                                        <>
                                            <td className="px-6 py-4">
                                                <div className="font-medium text-gray-900">
                                                    {policy.risk_tier.label}
                                                </div>
                                                <div className="text-sm text-gray-500">
                                                    {policy.risk_tier.code}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    <input
                                                        type="number"
                                                        min="1"
                                                        max="60"
                                                        value={editFormData.frequency_months}
                                                        onChange={(e) => setEditFormData({
                                                            ...editFormData,
                                                            frequency_months: parseInt(e.target.value)
                                                        })}
                                                        className="w-24 px-2 py-1 border border-gray-300 rounded"
                                                    />
                                                    <span className="text-sm text-gray-600">months</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    <input
                                                        type="number"
                                                        min="0"
                                                        max="365"
                                                        value={editFormData.model_change_lead_time_days}
                                                        onChange={(e) => setEditFormData({
                                                            ...editFormData,
                                                            model_change_lead_time_days: parseInt(e.target.value)
                                                        })}
                                                        className="w-24 px-2 py-1 border border-gray-300 rounded"
                                                    />
                                                    <span className="text-sm text-gray-600">days</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <textarea
                                                    value={editFormData.description}
                                                    onChange={(e) => setEditFormData({
                                                        ...editFormData,
                                                        description: e.target.value
                                                    })}
                                                    className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                                                    rows={2}
                                                />
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <button
                                                    onClick={() => handleUpdate(policy.policy_id)}
                                                    className="text-green-600 hover:text-green-800 mr-3"
                                                >
                                                    Save
                                                </button>
                                                <button
                                                    onClick={cancelEditing}
                                                    className="text-gray-600 hover:text-gray-800"
                                                >
                                                    Cancel
                                                </button>
                                            </td>
                                        </>
                                    ) : (
                                        // View mode
                                        <>
                                            <td className="px-6 py-4">
                                                <div className="font-medium text-gray-900">
                                                    {policy.risk_tier.label}
                                                </div>
                                                <div className="text-sm text-gray-500">
                                                    {policy.risk_tier.code}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="font-medium">{policy.frequency_months}</span>
                                                <span className="text-sm text-gray-600 ml-1">months</span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="font-medium">{policy.model_change_lead_time_days}</span>
                                                <span className="text-sm text-gray-600 ml-1">days</span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-700">
                                                {policy.description || '-'}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <button
                                                    onClick={() => startEditing(policy)}
                                                    className="text-blue-600 hover:text-blue-800"
                                                >
                                                    Edit
                                                </button>
                                            </td>
                                        </>
                                    )}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded">
                <h3 className="text-sm font-medium text-blue-900 mb-2">About These Settings</h3>
                <ul className="text-sm text-blue-800 space-y-2 list-disc list-inside">
                    <li>
                        <strong>Re-Validation Frequency:</strong> Time from last validation completion to next validation <em>submission/intake</em> (in months)
                    </li>
                    <li>
                        <strong>Model Change Lead Time:</strong> Days before a planned model change date to trigger interim validation
                    </li>
                    <li>
                        These policies apply to models based on their <strong>inherent risk tier</strong>
                    </li>
                </ul>

                <div className="mt-3 p-3 bg-blue-100 rounded text-xs">
                    <p className="font-semibold text-blue-900 mb-1">Overdue Calculation Example (Tier 2: 18 months, 90 days)</p>
                    <p className="text-blue-800">Last validation completed: <span className="font-mono">Jan 1, 2024</span></p>
                    <ul className="mt-1 ml-4 space-y-0.5 text-blue-700">
                        <li>• Submission due: <span className="font-mono">Jul 1, 2025</span> (+ 18 months)</li>
                        <li>• Submission overdue: <span className="font-mono">Oct 1, 2025</span> (+ 3 months grace)</li>
                        <li>• Validation overdue: <span className="font-mono">Dec 30, 2025</span> (+ 90 days lead time)</li>
                    </ul>
                    <p className="mt-2 text-blue-800 italic">
                        A validation is considered overdue if not completed within: <strong>frequency + 3 months grace + lead time days</strong>
                    </p>
                </div>
            </div>
        </Layout>
    );
}

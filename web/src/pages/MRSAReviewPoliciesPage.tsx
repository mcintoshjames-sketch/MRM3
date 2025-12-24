import { useEffect, useMemo, useState } from 'react';
import api from '../api/client';
import Layout from '../components/Layout';
import { useTableSort } from '../hooks/useTableSort';

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
    sort_order: number;
}

interface MRSAReviewPolicy {
    policy_id: number;
    mrsa_risk_level_id: number;
    mrsa_risk_level: TaxonomyValue | null;
    frequency_months: number;
    initial_review_months: number;
    warning_days: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export default function MRSAReviewPoliciesPage() {
    const [policies, setPolicies] = useState<MRSAReviewPolicy[]>([]);
    const [mrsaRiskLevels, setMrsaRiskLevels] = useState<TaxonomyValue[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [editingPolicy, setEditingPolicy] = useState<number | null>(null);
    const [editFormData, setEditFormData] = useState({
        frequency_months: 24,
        initial_review_months: 3,
        warning_days: 90,
        is_active: true
    });
    const [createFormData, setCreateFormData] = useState({
        mrsa_risk_level_id: 0,
        frequency_months: 24,
        initial_review_months: 3,
        warning_days: 90,
        is_active: true
    });

    const { sortedData, requestSort, getSortIcon } = useTableSort<MRSAReviewPolicy>(
        policies,
        'mrsa_risk_level.label'
    );

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);
            const taxonomyQueryString = ['MRSA Risk Level'].map((n) => `names=${encodeURIComponent(n)}`).join('&');
            const [policiesRes, taxonomiesRes] = await Promise.all([
                api.get('/mrsa-review-policies/'),
                api.get(`/taxonomies/by-names/?${taxonomyQueryString}`)
            ]);

            const taxonomy = taxonomiesRes.data.find((t: any) => t.name === 'MRSA Risk Level');
            const riskLevels = (taxonomy?.values || []) as TaxonomyValue[];
            setMrsaRiskLevels(riskLevels);

            const sortedPolicies = [...policiesRes.data].sort((a: MRSAReviewPolicy, b: MRSAReviewPolicy) => {
                const aOrder = a.mrsa_risk_level?.sort_order ?? 0;
                const bOrder = b.mrsa_risk_level?.sort_order ?? 0;
                return aOrder - bOrder;
            });
            setPolicies(sortedPolicies);
        } catch (err: any) {
            console.error('Failed to fetch MRSA review policies:', err);
            setError(err.response?.data?.detail || 'Failed to load MRSA review policies');
        } finally {
            setLoading(false);
        }
    };

    const availableRiskLevels = useMemo(() => {
        const configured = new Set(policies.map((policy) => policy.mrsa_risk_level_id));
        return mrsaRiskLevels
            .filter((level) => !configured.has(level.value_id))
            .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
    }, [mrsaRiskLevels, policies]);

    const startEditing = (policy: MRSAReviewPolicy) => {
        setEditingPolicy(policy.policy_id);
        setEditFormData({
            frequency_months: policy.frequency_months,
            initial_review_months: policy.initial_review_months,
            warning_days: policy.warning_days,
            is_active: policy.is_active
        });
    };

    const cancelEditing = () => {
        setEditingPolicy(null);
        setEditFormData({
            frequency_months: 24,
            initial_review_months: 3,
            warning_days: 90,
            is_active: true
        });
    };

    const handleUpdate = async (policyId: number) => {
        try {
            await api.patch(`/mrsa-review-policies/${policyId}`, editFormData);
            await fetchData();
            cancelEditing();
        } catch (err: any) {
            console.error('Failed to update MRSA review policy:', err);
            setError(err.response?.data?.detail || 'Failed to update MRSA review policy');
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!createFormData.mrsa_risk_level_id) {
            setError('Please select an MRSA risk level.');
            return;
        }
        try {
            await api.post('/mrsa-review-policies/', createFormData);
            await fetchData();
            setCreateFormData({
                mrsa_risk_level_id: 0,
                frequency_months: 24,
                initial_review_months: 3,
                warning_days: 90,
                is_active: true
            });
        } catch (err: any) {
            console.error('Failed to create MRSA review policy:', err);
            setError(err.response?.data?.detail || 'Failed to create MRSA review policy');
        }
    };

    const exportToCsv = () => {
        const headers = [
            'Risk Level',
            'Risk Code',
            'Frequency Months',
            'Initial Review Months',
            'Warning Days',
            'Active'
        ];
        const rows = sortedData.map((policy) => [
            policy.mrsa_risk_level?.label || '',
            policy.mrsa_risk_level?.code || '',
            policy.frequency_months,
            policy.initial_review_months,
            policy.warning_days,
            policy.is_active ? 'Active' : 'Inactive'
        ]);

        const csvContent = [headers, ...rows]
            .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
            .join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `mrsa_review_policies_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        link.parentNode?.removeChild(link);
        URL.revokeObjectURL(url);
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
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <div>
                        <h1 className="text-2xl font-bold mb-2">MRSA Review Policies</h1>
                        <p className="text-gray-600">
                            Configure independent review frequency and warning windows for MRSA risk levels.
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={fetchData}
                            className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-700 hover:bg-gray-50"
                        >
                            Refresh
                        </button>
                        <button
                            onClick={exportToCsv}
                            className="px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                        >
                            Export CSV
                        </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded">
                    {error}
                </div>
            )}

            <div className="bg-white rounded-lg shadow mb-6">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('mrsa_risk_level.label')}
                            >
                                <div className="flex items-center gap-2">
                                    MRSA Risk Level
                                    {getSortIcon('mrsa_risk_level.label')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('frequency_months')}
                            >
                                <div className="flex items-center gap-2">
                                    Frequency
                                    {getSortIcon('frequency_months')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('initial_review_months')}
                            >
                                <div className="flex items-center gap-2">
                                    Initial Review
                                    {getSortIcon('initial_review_months')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('warning_days')}
                            >
                                <div className="flex items-center gap-2">
                                    Warning Days
                                    {getSortIcon('warning_days')}
                                </div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Status
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedData.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                                    No MRSA review policies configured.
                                </td>
                            </tr>
                        ) : (
                            sortedData.map((policy) => (
                                <tr key={policy.policy_id}>
                                    {editingPolicy === policy.policy_id ? (
                                        <>
                                            <td className="px-6 py-4">
                                                <div className="font-medium text-gray-900">
                                                    {policy.mrsa_risk_level?.label || 'Unknown'}
                                                </div>
                                                {policy.mrsa_risk_level?.code && (
                                                    <div className="text-sm text-gray-500">
                                                        {policy.mrsa_risk_level.code}
                                                    </div>
                                                )}
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
                                                            frequency_months: parseInt(e.target.value, 10) || 0
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
                                                        min="1"
                                                        max="24"
                                                        value={editFormData.initial_review_months}
                                                        onChange={(e) => setEditFormData({
                                                            ...editFormData,
                                                            initial_review_months: parseInt(e.target.value, 10) || 0
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
                                                        value={editFormData.warning_days}
                                                        onChange={(e) => setEditFormData({
                                                            ...editFormData,
                                                            warning_days: parseInt(e.target.value, 10) || 0
                                                        })}
                                                        className="w-24 px-2 py-1 border border-gray-300 rounded"
                                                    />
                                                    <span className="text-sm text-gray-600">days</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                                                    <input
                                                        type="checkbox"
                                                        checked={editFormData.is_active}
                                                        onChange={(e) => setEditFormData({
                                                            ...editFormData,
                                                            is_active: e.target.checked
                                                        })}
                                                        className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                                                    />
                                                    Active
                                                </label>
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
                                        <>
                                            <td className="px-6 py-4">
                                                <div className="font-medium text-gray-900">
                                                    {policy.mrsa_risk_level?.label || 'Unknown'}
                                                </div>
                                                {policy.mrsa_risk_level?.code && (
                                                    <div className="text-sm text-gray-500">
                                                        {policy.mrsa_risk_level.code}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="font-medium">{policy.frequency_months}</span>
                                                <span className="text-sm text-gray-600 ml-1">months</span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="font-medium">{policy.initial_review_months}</span>
                                                <span className="text-sm text-gray-600 ml-1">months</span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="font-medium">{policy.warning_days}</span>
                                                <span className="text-sm text-gray-600 ml-1">days</span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                                    policy.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                                                }`}>
                                                    {policy.is_active ? 'Active' : 'Inactive'}
                                                </span>
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

            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Create MRSA Review Policy</h2>
                {availableRiskLevels.length === 0 ? (
                    <p className="text-sm text-gray-600">All MRSA risk levels already have policies.</p>
                ) : (
                    <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-6 gap-4">
                        <div className="md:col-span-2">
                            <label className="block text-xs font-medium text-gray-700 mb-1">MRSA Risk Level</label>
                            <select
                                value={createFormData.mrsa_risk_level_id}
                                onChange={(e) => setCreateFormData({
                                    ...createFormData,
                                    mrsa_risk_level_id: parseInt(e.target.value, 10)
                                })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            >
                                <option value={0}>Select Risk Level</option>
                                {availableRiskLevels.map((level) => (
                                    <option key={level.value_id} value={level.value_id}>
                                        {level.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Frequency (months)</label>
                            <input
                                type="number"
                                min="1"
                                max="60"
                                value={createFormData.frequency_months}
                                onChange={(e) => setCreateFormData({
                                    ...createFormData,
                                    frequency_months: parseInt(e.target.value, 10) || 0
                                })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Initial Review (months)</label>
                            <input
                                type="number"
                                min="1"
                                max="24"
                                value={createFormData.initial_review_months}
                                onChange={(e) => setCreateFormData({
                                    ...createFormData,
                                    initial_review_months: parseInt(e.target.value, 10) || 0
                                })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">Warning Days</label>
                            <input
                                type="number"
                                min="0"
                                max="365"
                                value={createFormData.warning_days}
                                onChange={(e) => setCreateFormData({
                                    ...createFormData,
                                    warning_days: parseInt(e.target.value, 10) || 0
                                })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                        </div>
                        <div className="flex items-center gap-2 pt-6">
                            <input
                                type="checkbox"
                                checked={createFormData.is_active}
                                onChange={(e) => setCreateFormData({
                                    ...createFormData,
                                    is_active: e.target.checked
                                })}
                                className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                            />
                            <span className="text-sm text-gray-700">Active</span>
                        </div>
                        <div className="md:col-span-6 flex justify-end">
                            <button
                                type="submit"
                                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                                Create Policy
                            </button>
                        </div>
                    </form>
                )}
            </div>

            <div className="p-4 bg-blue-50 border border-blue-200 rounded">
                <h3 className="text-sm font-medium text-blue-900 mb-2">Policy Definitions</h3>
                <ul className="text-sm text-blue-800 space-y-2 list-disc list-inside">
                    <li><strong>Frequency:</strong> Time between independent reviews after the latest review.</li>
                    <li><strong>Initial Review:</strong> Time from MRSA designation to the first required review.</li>
                    <li><strong>Warning Days:</strong> Days before due date to flag as upcoming.</li>
                </ul>
            </div>
        </Layout>
    );
}

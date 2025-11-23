import { useState, useEffect } from 'react';
import { regionsApi, Region, ModelRegion, ModelRegionCreate } from '../api/regions';
import api from '../api/client';

interface ModelRegionsSectionProps {
    modelId: number;
    whollyOwnedRegionId?: number | null;
    whollyOwnedRegion?: {
        region_id: number;
        code: string;
        name: string;
    } | null;
}

interface User {
    user_id: number;
    email: string;
    full_name: string;
}

export default function ModelRegionsSection({ modelId, whollyOwnedRegionId, whollyOwnedRegion }: ModelRegionsSectionProps) {
    const [regions, setRegions] = useState<Region[]>([]);
    const [modelRegions, setModelRegions] = useState<ModelRegion[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [formData, setFormData] = useState<ModelRegionCreate>({
        region_id: 0,
        shared_model_owner_id: undefined,
        regional_risk_level: '',
        notes: ''
    });

    useEffect(() => {
        fetchData();
    }, [modelId]);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [regionsData, modelRegionsData, usersData] = await Promise.all([
                regionsApi.getRegions(),
                regionsApi.getModelRegions(modelId),
                api.get('/auth/users')
            ]);
            setRegions(regionsData);
            setModelRegions(modelRegionsData);
            setUsers(usersData.data);
        } catch (err) {
            console.error('Failed to fetch model regions:', err);
            setError('Failed to load model regions');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!formData.region_id) {
            setError('Please select a region');
            return;
        }

        try {
            await regionsApi.createModelRegion(modelId, {
                region_id: formData.region_id,
                shared_model_owner_id: formData.shared_model_owner_id || undefined,
                regional_risk_level: formData.regional_risk_level || undefined,
                notes: formData.notes || undefined
            });
            setShowForm(false);
            setFormData({
                region_id: 0,
                shared_model_owner_id: undefined,
                regional_risk_level: '',
                notes: ''
            });
            fetchData();
        } catch (err: any) {
            console.error('Failed to create model-region link:', err);
            setError(err.response?.data?.detail || 'Failed to create model-region link');
        }
    };

    const handleDelete = async (id: number) => {
        // Check if this is the wholly-owned region
        const regionToDelete = modelRegions.find(mr => mr.id === id);
        if (regionToDelete && whollyOwnedRegionId && regionToDelete.region_id === whollyOwnedRegionId) {
            setError('Cannot remove the wholly-owned region from deployment regions. Change the "Wholly-Owned By Region" field first if needed.');
            return;
        }

        if (!confirm('Are you sure you want to remove this deployment region?')) {
            return;
        }

        try {
            await regionsApi.deleteModelRegion(id);
            fetchData();
        } catch (err: any) {
            console.error('Failed to delete model-region link:', err);
            setError(err.response?.data?.detail || 'Failed to delete deployment region');
        }
    };

    const getUserName = (userId: number) => {
        const user = users.find(u => u.user_id === userId);
        return user ? user.full_name : 'Unknown';
    };

    const availableRegions = regions.filter(
        r => !modelRegions.some(mr => mr.region_id === r.region_id)
    );

    if (loading) {
        return <div className="text-sm text-gray-500">Loading regional configurations...</div>;
    }

    return (
        <div className="mt-6">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Deployment Regions</h3>
                {availableRegions.length > 0 && (
                    <button
                        onClick={() => setShowForm(!showForm)}
                        className="text-sm btn-secondary"
                    >
                        {showForm ? 'Cancel' : '+ Add Region'}
                    </button>
                )}
            </div>
            {whollyOwnedRegion && (
                <div className="mb-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
                    <div className="flex items-start gap-2">
                        <svg className="w-5 h-5 text-indigo-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                        <div className="flex-1">
                            <p className="text-sm font-medium text-indigo-900">Wholly-Owned Model</p>
                            <p className="text-xs text-indigo-700 mt-1">
                                This model is wholly-owned by <strong>{whollyOwnedRegion.name} ({whollyOwnedRegion.code})</strong>.
                                Governance approvals will require {whollyOwnedRegion.code} Regional Approvers.
                                Add additional deployment regions below if this model operates in other regions.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 text-sm">
                    {error}
                </div>
            )}

            {showForm && (
                <div className="bg-gray-50 p-4 rounded-lg mb-4">
                    <h4 className="text-sm font-medium mb-3">Add Deployment Region</h4>
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-xs font-medium mb-1">Region (Required)</label>
                                <select
                                    className="input-field text-sm"
                                    value={formData.region_id || ''}
                                    onChange={(e) => setFormData({ ...formData, region_id: parseInt(e.target.value) || 0 })}
                                    required
                                >
                                    <option value="">Select Region</option>
                                    {availableRegions.map(r => (
                                        <option key={r.region_id} value={r.region_id}>
                                            {r.name} ({r.code})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1">Regional Model Owner (Optional)</label>
                                <select
                                    className="input-field text-sm"
                                    value={formData.shared_model_owner_id || ''}
                                    onChange={(e) => setFormData({ ...formData, shared_model_owner_id: e.target.value ? parseInt(e.target.value) : undefined })}
                                >
                                    <option value="">Same as global owner</option>
                                    {users.map(u => (
                                        <option key={u.user_id} value={u.user_id}>
                                            {u.full_name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1">Regional Risk Level (Optional)</label>
                                <select
                                    className="input-field text-sm"
                                    value={formData.regional_risk_level || ''}
                                    onChange={(e) => setFormData({ ...formData, regional_risk_level: e.target.value })}
                                >
                                    <option value="">Not specified</option>
                                    <option value="HIGH">HIGH</option>
                                    <option value="MEDIUM">MEDIUM</option>
                                    <option value="LOW">LOW</option>
                                </select>
                            </div>
                            <div className="col-span-2">
                                <label className="block text-xs font-medium mb-1">Notes (Optional)</label>
                                <textarea
                                    className="input-field text-sm"
                                    rows={2}
                                    value={formData.notes || ''}
                                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                                    placeholder="Regional-specific notes or considerations..."
                                />
                            </div>
                        </div>
                        <div className="flex gap-2 mt-3">
                            <button type="submit" className="btn-primary text-sm">Add Deployment Region</button>
                            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary text-sm">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {modelRegions.length === 0 ? (
                <div className="text-sm text-gray-500 italic">
                    {whollyOwnedRegion
                        ? `No additional deployment regions. This model operates only in ${whollyOwnedRegion.name}.`
                        : 'No deployment regions specified. This model is global only.'
                    }
                </div>
            ) : (
                <div className="space-y-3">
                    {modelRegions.map(mr => {
                        const region = regions.find(r => r.region_id === mr.region_id);
                        return (
                            <div key={mr.id} className="bg-white border border-gray-200 rounded-lg p-4">
                                <div className="flex justify-between items-start">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="px-2 py-1 text-xs font-semibold rounded bg-blue-100 text-blue-800">
                                                {region?.code}
                                            </span>
                                            <span className="text-sm font-medium">{region?.name}</span>
                                            {mr.regional_risk_level && (
                                                <span className={`px-2 py-1 text-xs rounded ${
                                                    mr.regional_risk_level === 'HIGH' ? 'bg-red-100 text-red-800' :
                                                    mr.regional_risk_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                                                    'bg-green-100 text-green-800'
                                                }`}>
                                                    {mr.regional_risk_level}
                                                </span>
                                            )}
                                        </div>
                                        {mr.shared_model_owner_id && (
                                            <div className="text-xs text-gray-600 mb-1">
                                                Regional Owner: {getUserName(mr.shared_model_owner_id)}
                                            </div>
                                        )}
                                        {mr.notes && (
                                            <div className="text-xs text-gray-600 mt-2">
                                                {mr.notes}
                                            </div>
                                        )}
                                        <div className="text-xs text-gray-400 mt-2">
                                            Added {mr.created_at.split('T')[0]}
                                        </div>
                                    </div>
                                    {whollyOwnedRegionId && mr.region_id === whollyOwnedRegionId ? (
                                        <span className="text-xs text-gray-400 italic flex items-center gap-1">
                                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                                            </svg>
                                            Governance Region
                                        </span>
                                    ) : (
                                        <button
                                            onClick={() => handleDelete(mr.id)}
                                            className="text-red-600 hover:text-red-800 text-xs"
                                        >
                                            Remove
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

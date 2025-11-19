import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface Region {
    region_id: number;
    code: string;
    name: string;
    created_at: string;
}

export default function RegionsPage() {
    const { user } = useAuth();
    const [regions, setRegions] = useState<Region[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingRegion, setEditingRegion] = useState<Region | null>(null);
    const [formData, setFormData] = useState({
        code: '',
        name: ''
    });
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchRegions();
    }, []);

    const fetchRegions = async () => {
        try {
            const response = await api.get('/regions/');
            setRegions(response.data);
        } catch (error) {
            console.error('Failed to fetch regions:', error);
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({ code: '', name: '' });
        setEditingRegion(null);
        setShowForm(false);
        setError(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        try {
            if (editingRegion) {
                await api.put(`/regions/${editingRegion.region_id}`, formData);
            } else {
                await api.post('/regions/', formData);
            }
            resetForm();
            fetchRegions();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save region');
        }
    };

    const handleEdit = (region: Region) => {
        setEditingRegion(region);
        setFormData({
            code: region.code,
            name: region.name
        });
        setShowForm(true);
    };

    const handleDelete = async (regionId: number) => {
        if (!confirm('Are you sure you want to delete this region? This will remove region associations from all Regional Approvers.')) return;

        try {
            await api.delete(`/regions/${regionId}`);
            fetchRegions();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to delete region');
        }
    };

    // Only admins can access this page
    if (user?.role !== 'Admin') {
        return (
            <Layout>
                <div className="text-center py-12">
                    <h2 className="text-2xl font-bold text-gray-800">Access Denied</h2>
                    <p className="text-gray-600 mt-2">Only administrators can manage regions.</p>
                </div>
            </Layout>
        );
    }

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold">Regions</h2>
                    <p className="text-gray-600 text-sm mt-1">Manage geographic regions for validation approvals</p>
                </div>
                <button onClick={() => setShowForm(true)} className="btn-primary">
                    + Add Region
                </button>
            </div>

            {showForm && (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">
                        {editingRegion ? 'Edit Region' : 'Create New Region'}
                    </h3>

                    {error && (
                        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label htmlFor="code" className="block text-sm font-medium mb-2">
                                    Code *
                                </label>
                                <input
                                    id="code"
                                    type="text"
                                    className="input-field"
                                    value={formData.code}
                                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                                    placeholder="e.g., US, UK, EU"
                                    maxLength={10}
                                    required
                                />
                                <p className="text-xs text-gray-500 mt-1">Short code (max 10 characters)</p>
                            </div>
                            <div className="mb-4">
                                <label htmlFor="name" className="block text-sm font-medium mb-2">
                                    Name *
                                </label>
                                <input
                                    id="name"
                                    type="text"
                                    className="input-field"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    placeholder="e.g., United States, United Kingdom"
                                    required
                                />
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">
                                {editingRegion ? 'Update' : 'Create'}
                            </button>
                            <button type="button" onClick={resetForm} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {regions.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                                    No regions yet. Click "Add Region" to create one.
                                </td>
                            </tr>
                        ) : (
                            regions.map((region) => (
                                <tr key={region.region_id}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {region.region_id}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded">
                                            {region.code}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap font-medium">
                                        {region.name}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {new Date(region.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <button
                                            onClick={() => handleEdit(region)}
                                            className="text-blue-600 hover:text-blue-800 text-sm mr-3"
                                        >
                                            Edit
                                        </button>
                                        <button
                                            onClick={() => handleDelete(region.region_id)}
                                            className="text-red-600 hover:text-red-800 text-sm"
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <div className="mt-4 text-sm text-gray-600">
                <p><strong>Note:</strong> Regions are used to define geographic boundaries for validation approvals.</p>
                <p className="mt-1">Regional Approvers can be assigned to one or more regions in the Users page.</p>
            </div>
        </Layout>
    );
}

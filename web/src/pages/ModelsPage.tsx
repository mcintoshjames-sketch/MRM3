import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface User {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
}

interface Vendor {
    vendor_id: number;
    name: string;
    contact_info: string;
}

interface Model {
    model_id: number;
    model_name: string;
    description: string;
    development_type: string;
    owner_id: number;
    developer_id: number | null;
    vendor_id: number | null;
    status: string;
    created_at: string;
    updated_at: string;
    owner: User;
    developer: User | null;
    vendor: Vendor | null;
    users: User[];
}

export default function ModelsPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [models, setModels] = useState<Model[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({
        model_name: '',
        description: '',
        development_type: 'In-House',
        owner_id: user?.user_id || 0,
        developer_id: null as number | null,
        vendor_id: null as number | null,
        status: 'In Development',
        user_ids: [] as number[]
    });
    const [userSearchTerm, setUserSearchTerm] = useState('');

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [modelsRes, usersRes, vendorsRes] = await Promise.all([
                api.get('/models/'),
                api.get('/auth/users'),
                api.get('/vendors/')
            ]);
            setModels(modelsRes.data);
            setUsers(usersRes.data);
            setVendors(vendorsRes.data);
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload = {
                ...formData,
                developer_id: formData.developer_id || null,
                vendor_id: formData.vendor_id || null,
                user_ids: formData.user_ids.length > 0 ? formData.user_ids : null
            };
            await api.post('/models/', payload);
            setShowForm(false);
            setFormData({
                model_name: '',
                description: '',
                development_type: 'In-House',
                owner_id: user?.user_id || 0,
                developer_id: null,
                vendor_id: null,
                status: 'In Development',
                user_ids: []
            });
            fetchData();
        } catch (error) {
            console.error('Failed to create model:', error);
        }
    };

    const handleDelete = async (modelId: number) => {
        if (!confirm('Are you sure you want to delete this model?')) return;

        try {
            await api.delete(`/models/${modelId}`);
            fetchData();
        } catch (error) {
            console.error('Failed to delete model:', error);
        }
    };

    const addUserToModel = (userId: number) => {
        if (!formData.user_ids.includes(userId)) {
            setFormData(prev => ({
                ...prev,
                user_ids: [...prev.user_ids, userId]
            }));
        }
        setUserSearchTerm('');
    };

    const removeUserFromModel = (userId: number) => {
        setFormData(prev => ({
            ...prev,
            user_ids: prev.user_ids.filter(id => id !== userId)
        }));
    };

    const getFilteredUsers = () => {
        if (!userSearchTerm) return [];
        return users.filter(u =>
            !formData.user_ids.includes(u.user_id) &&
            (u.full_name.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
             u.email.toLowerCase().includes(userSearchTerm.toLowerCase()))
        );
    };

    const handleExportCSV = async () => {
        try {
            const response = await api.get('/models/export/csv', {
                responseType: 'blob'
            });

            // Create a download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;

            // Generate filename with current date
            const date = new Date().toISOString().split('T')[0];
            link.setAttribute('download', `models_${date}.csv`);

            // Trigger download
            document.body.appendChild(link);
            link.click();

            // Cleanup
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Failed to export CSV:', error);
            alert('Failed to export CSV. Please try again.');
        }
    };

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
                <h2 className="text-2xl font-bold">Models</h2>
                <div className="flex gap-2">
                    <button onClick={handleExportCSV} className="btn-secondary">
                        Export CSV
                    </button>
                    <button onClick={() => setShowForm(true)} className="btn-primary">
                        + Add Model
                    </button>
                </div>
            </div>

                {showForm && (
                    <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                        <h3 className="text-lg font-bold mb-4">Create New Model</h3>
                        <form onSubmit={handleSubmit}>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="mb-4">
                                    <label htmlFor="model_name" className="block text-sm font-medium mb-2">Model Name</label>
                                    <input
                                        id="model_name"
                                        type="text"
                                        className="input-field"
                                        value={formData.model_name}
                                        onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                                        required
                                    />
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="development_type" className="block text-sm font-medium mb-2">Development Type</label>
                                    <select
                                        id="development_type"
                                        className="input-field"
                                        value={formData.development_type}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            development_type: e.target.value,
                                            vendor_id: e.target.value === 'In-House' ? null : formData.vendor_id
                                        })}
                                    >
                                        <option value="In-House">In-House</option>
                                        <option value="Third-Party">Third-Party</option>
                                    </select>
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="owner_id" className="block text-sm font-medium mb-2">Owner (Required)</label>
                                    <select
                                        id="owner_id"
                                        className="input-field"
                                        value={formData.owner_id}
                                        onChange={(e) => setFormData({ ...formData, owner_id: parseInt(e.target.value) })}
                                        required
                                    >
                                        <option value="">Select Owner</option>
                                        {users.map(u => (
                                            <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="developer_id" className="block text-sm font-medium mb-2">Developer (Optional)</label>
                                    <select
                                        id="developer_id"
                                        className="input-field"
                                        value={formData.developer_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            developer_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">None</option>
                                        {users.map(u => (
                                            <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                                        ))}
                                    </select>
                                </div>

                                {formData.development_type === 'Third-Party' && (
                                    <div className="mb-4">
                                        <label htmlFor="vendor_id" className="block text-sm font-medium mb-2">Vendor (Required for Third-Party)</label>
                                        <select
                                            id="vendor_id"
                                            className="input-field"
                                            value={formData.vendor_id || ''}
                                            onChange={(e) => setFormData({
                                                ...formData,
                                                vendor_id: e.target.value ? parseInt(e.target.value) : null
                                            })}
                                            required
                                        >
                                            <option value="">Select Vendor</option>
                                            {vendors.map(v => (
                                                <option key={v.vendor_id} value={v.vendor_id}>{v.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                <div className="mb-4">
                                    <label htmlFor="status" className="block text-sm font-medium mb-2">Status</label>
                                    <select
                                        id="status"
                                        className="input-field"
                                        value={formData.status}
                                        onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                                    >
                                        <option value="In Development">In Development</option>
                                        <option value="Active">Active</option>
                                        <option value="Retired">Retired</option>
                                    </select>
                                </div>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="description" className="block text-sm font-medium mb-2">Description</label>
                                <textarea
                                    id="description"
                                    className="input-field"
                                    rows={3}
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                />
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Model Users ({formData.user_ids.length} selected)
                                </label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        className="input-field"
                                        placeholder="Search users by name or email..."
                                        value={userSearchTerm}
                                        onChange={(e) => setUserSearchTerm(e.target.value)}
                                    />
                                    {userSearchTerm && getFilteredUsers().length > 0 && (
                                        <div className="absolute z-10 w-full bg-white border rounded shadow-lg max-h-40 overflow-y-auto">
                                            {getFilteredUsers().map(u => (
                                                <button
                                                    key={u.user_id}
                                                    type="button"
                                                    className="w-full text-left px-3 py-2 hover:bg-gray-100"
                                                    onClick={() => addUserToModel(u.user_id)}
                                                >
                                                    {u.full_name} ({u.email})
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                {formData.user_ids.length > 0 && (
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {formData.user_ids.map(uid => {
                                            const selectedUser = users.find(u => u.user_id === uid);
                                            return selectedUser ? (
                                                <div key={uid} className="bg-blue-100 text-blue-800 px-2 py-1 rounded flex items-center gap-1">
                                                    <span className="text-sm">{selectedUser.full_name}</span>
                                                    <button
                                                        type="button"
                                                        onClick={() => removeUserFromModel(uid)}
                                                        className="text-blue-600 hover:text-blue-800 font-bold"
                                                    >
                                                        ×
                                                    </button>
                                                </div>
                                            ) : null;
                                        })}
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-2">
                                <button type="submit" className="btn-primary">Create</button>
                                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
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
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Developer</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vendor</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Users</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {models.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="px-6 py-4 text-center text-gray-500">
                                        No models yet. Click "Add Model" to create one.
                                    </td>
                                </tr>
                            ) : (
                                models.map((model) => (
                                    <tr key={model.model_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <button
                                                onClick={() => navigate(`/models/${model.model_id}`)}
                                                className="font-medium text-blue-600 hover:text-blue-800 text-left"
                                            >
                                                {model.model_name}
                                            </button>
                                            <div className="text-sm text-gray-500">{model.description || '-'}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${
                                                model.development_type === 'In-House'
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-purple-100 text-purple-800'
                                            }`}>
                                                {model.development_type}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {model.owner.full_name}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {model.developer?.full_name || '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {model.vendor?.name || '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            {model.users.length > 0
                                                ? model.users.map(u => u.full_name).join(', ')
                                                : '-'
                                            }
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                {model.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <button
                                                onClick={() => handleDelete(model.model_id)}
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
        </Layout>
    );
}

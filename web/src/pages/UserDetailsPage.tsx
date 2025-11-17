import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';

interface User {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
    created_at: string;
}

interface Vendor {
    vendor_id: number;
    name: string;
}

interface TaxonomyValue {
    value_id: number;
    label: string;
}

interface Model {
    model_id: number;
    model_name: string;
    description: string;
    development_type: string;
    status: string;
    owner: User;
    developer: User | null;
    vendor: Vendor | null;
    risk_tier: TaxonomyValue | null;
    model_type: TaxonomyValue | null;
}

export default function UserDetailsPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [user, setUser] = useState<User | null>(null);
    const [models, setModels] = useState<Model[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
    }, [id]);

    const fetchData = async () => {
        try {
            const [userRes, modelsRes] = await Promise.all([
                api.get(`/auth/users/${id}`),
                api.get(`/auth/users/${id}/models`)
            ]);
            setUser(userRes.data);
            setModels(modelsRes.data);
        } catch (error) {
            console.error('Failed to fetch user:', error);
        } finally {
            setLoading(false);
        }
    };

    const getOwnedModels = () => models.filter(m => m.owner.user_id === parseInt(id!));
    const getDevelopedModels = () => models.filter(m => m.developer?.user_id === parseInt(id!));

    const handleExportCSV = () => {
        if (models.length === 0 || !user) return;

        // Create CSV content
        const headers = ['Model ID', 'Model Name', 'Relationship', 'Development Type', 'Status', 'Risk Tier', 'Model Type', 'Owner', 'Developer', 'Vendor', 'Description'];
        const rows = models.map(model => {
            const relationship = model.owner.user_id === parseInt(id!)
                ? (model.developer?.user_id === parseInt(id!) ? 'Owner & Developer' : 'Owner')
                : 'Developer';
            return [
                model.model_id,
                `"${model.model_name.replace(/"/g, '""')}"`,
                relationship,
                model.development_type,
                model.status,
                model.risk_tier?.label || '',
                model.model_type?.label || '',
                model.owner.full_name,
                model.developer?.full_name || '',
                model.vendor?.name || '',
                `"${(model.description || '').replace(/"/g, '""')}"`
            ].join(',');
        });

        const csvContent = [headers.join(','), ...rows].join('\n');

        // Create and trigger download
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const date = new Date().toISOString().split('T')[0];
        const userName = user.full_name.replace(/\s+/g, '_');
        link.setAttribute('download', `${userName}_related_models_${date}.csv`);
        document.body.appendChild(link);
        link.click();
        link.parentNode?.removeChild(link);
        window.URL.revokeObjectURL(url);
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    if (!user) {
        return (
            <Layout>
                <div className="text-center">
                    <h2 className="text-2xl font-bold mb-4">User Not Found</h2>
                    <button onClick={() => navigate('/users')} className="btn-primary">
                        Back to Users
                    </button>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <button
                        onClick={() => navigate('/users')}
                        className="text-blue-600 hover:text-blue-800 text-sm mb-2"
                    >
                        &larr; Back to Users
                    </button>
                    <h2 className="text-2xl font-bold">{user.full_name}</h2>
                </div>
            </div>

            {/* User Information */}
            <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                <h3 className="text-lg font-bold mb-4">User Information</h3>
                <div className="grid grid-cols-2 gap-6">
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">User ID</h4>
                        <p className="text-lg">{user.user_id}</p>
                    </div>
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">Email</h4>
                        <p className="text-lg">{user.email}</p>
                    </div>
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">Role</h4>
                        <span className={`px-2 py-1 text-sm rounded ${
                            user.role === 'Admin'
                                ? 'bg-purple-100 text-purple-800'
                                : 'bg-blue-100 text-blue-800'
                        }`}>
                            {user.role}
                        </span>
                    </div>
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">Created</h4>
                        <p className="text-sm">{new Date(user.created_at).toLocaleString()}</p>
                    </div>
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">Models Owned</h4>
                        <p className="text-lg font-semibold">{getOwnedModels().length}</p>
                    </div>
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">Models Developed</h4>
                        <p className="text-lg font-semibold">{getDevelopedModels().length}</p>
                    </div>
                </div>
            </div>

            {/* Related Models - Tabbed View */}
            <div className="bg-white p-6 rounded-lg shadow-md">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-bold">
                        Related Models ({models.length} total)
                    </h3>
                    {models.length > 0 && (
                        <button
                            onClick={handleExportCSV}
                            className="btn-secondary"
                        >
                            Export CSV
                        </button>
                    )}
                </div>

                {models.length === 0 ? (
                    <p className="text-gray-500">This user is not the owner or developer of any models.</p>
                ) : (
                    <div className="space-y-6">
                        {/* Models Owned Section */}
                        <div>
                            <h4 className="text-md font-semibold mb-3 text-gray-700">
                                Models Owned ({getOwnedModels().length})
                            </h4>
                            {getOwnedModels().length === 0 ? (
                                <p className="text-gray-500 text-sm">No models owned.</p>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Model Name
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Type
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Risk Tier
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Status
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Actions
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {getOwnedModels().map((model) => (
                                                <tr key={model.model_id}>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        <div className="font-medium">{model.model_name}</div>
                                                        {model.description && (
                                                            <div className="text-sm text-gray-500 truncate max-w-xs">
                                                                {model.description}
                                                            </div>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        <span className={`px-2 py-1 text-xs rounded ${
                                                            model.development_type === 'In-House'
                                                                ? 'bg-green-100 text-green-800'
                                                                : 'bg-purple-100 text-purple-800'
                                                        }`}>
                                                            {model.development_type}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        {model.risk_tier ? (
                                                            <span className="px-2 py-1 text-xs rounded bg-orange-100 text-orange-800">
                                                                {model.risk_tier.label}
                                                            </span>
                                                        ) : (
                                                            <span className="text-gray-400">-</span>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                            {model.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        <Link
                                                            to={`/models/${model.model_id}`}
                                                            className="text-blue-600 hover:text-blue-800"
                                                        >
                                                            View
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>

                        {/* Models Developed Section */}
                        <div>
                            <h4 className="text-md font-semibold mb-3 text-gray-700">
                                Models Developed ({getDevelopedModels().length})
                            </h4>
                            {getDevelopedModels().length === 0 ? (
                                <p className="text-gray-500 text-sm">No models developed.</p>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Model Name
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Owner
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Type
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Status
                                                </th>
                                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                    Actions
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {getDevelopedModels().map((model) => (
                                                <tr key={model.model_id}>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        <div className="font-medium">{model.model_name}</div>
                                                    </td>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        <div className="text-sm">{model.owner.full_name}</div>
                                                    </td>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        <span className={`px-2 py-1 text-xs rounded ${
                                                            model.development_type === 'In-House'
                                                                ? 'bg-green-100 text-green-800'
                                                                : 'bg-purple-100 text-purple-800'
                                                        }`}>
                                                            {model.development_type}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                            {model.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                        <Link
                                                            to={`/models/${model.model_id}`}
                                                            className="text-blue-600 hover:text-blue-800"
                                                        >
                                                            View
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
}

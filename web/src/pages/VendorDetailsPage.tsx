import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
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
    created_at: string;
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
    risk_tier: TaxonomyValue | null;
    model_type: TaxonomyValue | null;
}

export default function VendorDetailsPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [vendor, setVendor] = useState<Vendor | null>(null);
    const [models, setModels] = useState<Model[]>([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        contact_info: ''
    });

    useEffect(() => {
        fetchData();
    }, [id]);

    const fetchData = async () => {
        try {
            const [vendorRes, modelsRes] = await Promise.all([
                api.get(`/vendors/${id}`),
                api.get(`/vendors/${id}/models`)
            ]);
            setVendor(vendorRes.data);
            setModels(modelsRes.data);
            setFormData({
                name: vendorRes.data.name,
                contact_info: vendorRes.data.contact_info || ''
            });
        } catch (error) {
            console.error('Failed to fetch vendor:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.patch(`/vendors/${id}`, formData);
            setEditing(false);
            fetchData();
        } catch (error) {
            console.error('Failed to update vendor:', error);
        }
    };

    const handleDelete = async () => {
        if (models.length > 0) {
            alert(`Cannot delete vendor with ${models.length} associated model(s). Please reassign or delete the models first.`);
            return;
        }
        if (!confirm('Are you sure you want to delete this vendor?')) return;
        try {
            await api.delete(`/vendors/${id}`);
            navigate('/vendors');
        } catch (error) {
            console.error('Failed to delete vendor:', error);
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    if (!vendor) {
        return (
            <Layout>
                <div className="text-center">
                    <h2 className="text-2xl font-bold mb-4">Vendor Not Found</h2>
                    <button onClick={() => navigate('/vendors')} className="btn-primary">
                        Back to Vendors
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
                        onClick={() => navigate('/vendors')}
                        className="text-blue-600 hover:text-blue-800 text-sm mb-2"
                    >
                        &larr; Back to Vendors
                    </button>
                    <h2 className="text-2xl font-bold">{vendor.name}</h2>
                </div>
                <div className="flex gap-2">
                    {!editing && (
                        <>
                            <button onClick={() => setEditing(true)} className="btn-primary">
                                Edit Vendor
                            </button>
                            <button onClick={handleDelete} className="btn-secondary text-red-600">
                                Delete
                            </button>
                        </>
                    )}
                </div>
            </div>

            {editing ? (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">Edit Vendor</h3>
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label htmlFor="name" className="block text-sm font-medium mb-2">
                                    Name
                                </label>
                                <input
                                    id="name"
                                    type="text"
                                    className="input-field"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="contact_info" className="block text-sm font-medium mb-2">
                                    Contact Info
                                </label>
                                <input
                                    id="contact_info"
                                    type="text"
                                    className="input-field"
                                    value={formData.contact_info}
                                    onChange={(e) => setFormData({ ...formData, contact_info: e.target.value })}
                                />
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">Save Changes</button>
                            <button type="button" onClick={() => setEditing(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            ) : (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <div className="grid grid-cols-2 gap-6">
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Vendor ID</h4>
                            <p className="text-lg">{vendor.vendor_id}</p>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Contact Info</h4>
                            <p className="text-lg">{vendor.contact_info || '-'}</p>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Created</h4>
                            <p className="text-sm">{new Date(vendor.created_at).toLocaleString()}</p>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Total Models</h4>
                            <p className="text-lg font-semibold">{models.length}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Related Models */}
            <div className="bg-white p-6 rounded-lg shadow-md">
                <h3 className="text-lg font-bold mb-4">
                    Related Models ({models.length})
                </h3>
                {models.length === 0 ? (
                    <p className="text-gray-500">No models associated with this vendor.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Model Name
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Model Type
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Owner
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Risk Tier
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Status
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {models.map((model) => (
                                    <tr key={model.model_id}>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="font-medium">{model.model_name}</div>
                                            {model.description && (
                                                <div className="text-sm text-gray-500 truncate max-w-xs">
                                                    {model.description}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            {model.model_type ? (
                                                <span className="text-sm">{model.model_type.label}</span>
                                            ) : (
                                                <span className="text-gray-400">-</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm">{model.owner.full_name}</div>
                                            <div className="text-xs text-gray-500">{model.owner.email}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            {model.risk_tier ? (
                                                <span className="px-2 py-1 text-xs rounded bg-orange-100 text-orange-800">
                                                    {model.risk_tier.label}
                                                </span>
                                            ) : (
                                                <span className="text-gray-400">-</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                {model.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
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
        </Layout>
    );
}

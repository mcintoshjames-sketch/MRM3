import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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

interface TaxonomyValue {
    value_id: number;
    taxonomy_id: number;
    code: string;
    label: string;
    description: string | null;
    sort_order: number;
    is_active: boolean;
}

interface Taxonomy {
    taxonomy_id: number;
    name: string;
    description: string | null;
    is_system: boolean;
    values: TaxonomyValue[];
}

interface Model {
    model_id: number;
    model_name: string;
    description: string;
    development_type: string;
    owner_id: number;
    developer_id: number | null;
    vendor_id: number | null;
    risk_tier_id: number | null;
    validation_type_id: number | null;
    status: string;
    created_at: string;
    updated_at: string;
    owner: User;
    developer: User | null;
    vendor: Vendor | null;
    risk_tier: TaxonomyValue | null;
    validation_type: TaxonomyValue | null;
    users: User[];
}

export default function ModelDetailsPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [model, setModel] = useState<Model | null>(null);
    const [users, setUsers] = useState<User[]>([]);
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [taxonomies, setTaxonomies] = useState<Taxonomy[]>([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(false);
    const [userSearchTerm, setUserSearchTerm] = useState('');
    const [showUserDropdown, setShowUserDropdown] = useState(false);
    const [formData, setFormData] = useState({
        model_name: '',
        description: '',
        development_type: 'In-House',
        owner_id: 0,
        developer_id: null as number | null,
        vendor_id: null as number | null,
        risk_tier_id: null as number | null,
        validation_type_id: null as number | null,
        status: 'In Development',
        user_ids: [] as number[]
    });

    useEffect(() => {
        fetchData();
    }, [id]);

    const fetchData = async () => {
        try {
            const [modelRes, usersRes, vendorsRes, taxonomiesRes] = await Promise.all([
                api.get(`/models/${id}`),
                api.get('/auth/users'),
                api.get('/vendors/'),
                api.get('/taxonomies/')
            ]);
            const modelData = modelRes.data;
            setModel(modelData);
            setUsers(usersRes.data);
            setVendors(vendorsRes.data);

            // Fetch full taxonomy details for dropdowns
            const taxDetails = await Promise.all(
                taxonomiesRes.data.map((t: Taxonomy) => api.get(`/taxonomies/${t.taxonomy_id}`))
            );
            setTaxonomies(taxDetails.map((r) => r.data));

            setFormData({
                model_name: modelData.model_name,
                description: modelData.description || '',
                development_type: modelData.development_type,
                owner_id: modelData.owner_id,
                developer_id: modelData.developer_id,
                vendor_id: modelData.vendor_id,
                risk_tier_id: modelData.risk_tier_id,
                validation_type_id: modelData.validation_type_id,
                status: modelData.status,
                user_ids: modelData.users.map((u: User) => u.user_id)
            });
        } catch (error) {
            console.error('Failed to fetch model:', error);
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
                risk_tier_id: formData.risk_tier_id || null,
                validation_type_id: formData.validation_type_id || null,
                user_ids: formData.user_ids.length > 0 ? formData.user_ids : []
            };
            await api.patch(`/models/${id}`, payload);
            setEditing(false);
            fetchData();
        } catch (error) {
            console.error('Failed to update model:', error);
        }
    };

    const getRiskTierTaxonomy = () => taxonomies.find(t => t.name === 'Model Risk Tier');
    const getValidationTypeTaxonomy = () => taxonomies.find(t => t.name === 'Validation Type');

    const addUserToModel = (userId: number) => {
        if (!formData.user_ids.includes(userId)) {
            setFormData(prev => ({
                ...prev,
                user_ids: [...prev.user_ids, userId]
            }));
        }
        setUserSearchTerm('');
        setShowUserDropdown(false);
    };

    const removeUserFromModel = (userId: number) => {
        setFormData(prev => ({
            ...prev,
            user_ids: prev.user_ids.filter(id => id !== userId)
        }));
    };

    const filteredUsersForSearch = users.filter(u =>
        !formData.user_ids.includes(u.user_id) &&
        (u.full_name.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
         u.email.toLowerCase().includes(userSearchTerm.toLowerCase()))
    );

    const selectedUsers = users.filter(u => formData.user_ids.includes(u.user_id));

    const handleDelete = async () => {
        if (!confirm('Are you sure you want to delete this model?')) return;
        try {
            await api.delete(`/models/${id}`);
            navigate('/models');
        } catch (error) {
            console.error('Failed to delete model:', error);
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    if (!model) {
        return (
            <Layout>
                <div className="text-center">
                    <h2 className="text-2xl font-bold mb-4">Model Not Found</h2>
                    <button onClick={() => navigate('/models')} className="btn-primary">
                        Back to Models
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
                        onClick={() => navigate('/models')}
                        className="text-blue-600 hover:text-blue-800 text-sm mb-2"
                    >
                        &larr; Back to Models
                    </button>
                    <h2 className="text-2xl font-bold">{model.model_name}</h2>
                </div>
                <div className="flex gap-2">
                    {!editing && (
                        <>
                            <button onClick={() => setEditing(true)} className="btn-primary">
                                Edit Model
                            </button>
                            <button onClick={handleDelete} className="btn-secondary text-red-600">
                                Delete
                            </button>
                        </>
                    )}
                </div>
            </div>

            {editing ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h3 className="text-lg font-bold mb-4">Edit Model</h3>
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label htmlFor="model_name" className="block text-sm font-medium mb-2">
                                    Model Name
                                </label>
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
                                <label htmlFor="development_type" className="block text-sm font-medium mb-2">
                                    Development Type
                                </label>
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
                                <label htmlFor="owner_id" className="block text-sm font-medium mb-2">
                                    Owner
                                </label>
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
                                <label htmlFor="developer_id" className="block text-sm font-medium mb-2">
                                    Developer
                                </label>
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
                                    <label htmlFor="vendor_id" className="block text-sm font-medium mb-2">
                                        Vendor
                                    </label>
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
                                <label htmlFor="status" className="block text-sm font-medium mb-2">
                                    Status
                                </label>
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

                            {getRiskTierTaxonomy() && (
                                <div className="mb-4">
                                    <label htmlFor="risk_tier_id" className="block text-sm font-medium mb-2">
                                        Risk Tier
                                    </label>
                                    <select
                                        id="risk_tier_id"
                                        className="input-field"
                                        value={formData.risk_tier_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            risk_tier_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">Select Risk Tier</option>
                                        {getRiskTierTaxonomy()?.values
                                            .filter(v => v.is_active)
                                            .sort((a, b) => a.sort_order - b.sort_order)
                                            .map(v => (
                                                <option key={v.value_id} value={v.value_id}>{v.label}</option>
                                            ))}
                                    </select>
                                </div>
                            )}

                            {getValidationTypeTaxonomy() && (
                                <div className="mb-4">
                                    <label htmlFor="validation_type_id" className="block text-sm font-medium mb-2">
                                        Validation Type
                                    </label>
                                    <select
                                        id="validation_type_id"
                                        className="input-field"
                                        value={formData.validation_type_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            validation_type_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">Select Validation Type</option>
                                        {getValidationTypeTaxonomy()?.values
                                            .filter(v => v.is_active)
                                            .sort((a, b) => a.sort_order - b.sort_order)
                                            .map(v => (
                                                <option key={v.value_id} value={v.value_id}>{v.label}</option>
                                            ))}
                                    </select>
                                </div>
                            )}
                        </div>

                        <div className="mb-4">
                            <label htmlFor="description" className="block text-sm font-medium mb-2">
                                Description
                            </label>
                            <textarea
                                id="description"
                                className="input-field"
                                rows={3}
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            />
                        </div>

                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-2">Model Users</label>

                            {/* User search/lookup */}
                            <div className="relative mb-3">
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="Search users by name or email..."
                                    value={userSearchTerm}
                                    onChange={(e) => {
                                        setUserSearchTerm(e.target.value);
                                        setShowUserDropdown(e.target.value.length > 0);
                                    }}
                                    onFocus={() => userSearchTerm.length > 0 && setShowUserDropdown(true)}
                                    onBlur={() => setTimeout(() => setShowUserDropdown(false), 200)}
                                />
                                {showUserDropdown && filteredUsersForSearch.length > 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                                        {filteredUsersForSearch.map(u => (
                                            <button
                                                key={u.user_id}
                                                type="button"
                                                className="w-full text-left px-4 py-2 hover:bg-blue-50 focus:bg-blue-50"
                                                onClick={() => addUserToModel(u.user_id)}
                                            >
                                                <div className="font-medium">{u.full_name}</div>
                                                <div className="text-sm text-gray-500">{u.email}</div>
                                            </button>
                                        ))}
                                    </div>
                                )}
                                {showUserDropdown && userSearchTerm && filteredUsersForSearch.length === 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg p-3 text-gray-500 text-sm">
                                        No users found matching "{userSearchTerm}"
                                    </div>
                                )}
                            </div>

                            {/* Selected users subform */}
                            <div className="border rounded bg-gray-50 p-3">
                                <div className="text-sm font-medium text-gray-600 mb-2">
                                    Selected Users ({selectedUsers.length})
                                </div>
                                {selectedUsers.length === 0 ? (
                                    <div className="text-sm text-gray-500 italic">
                                        No users added. Use the search above to add users.
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {selectedUsers.map(u => (
                                            <div
                                                key={u.user_id}
                                                className="flex items-center justify-between bg-white p-2 rounded border"
                                            >
                                                <div>
                                                    <div className="font-medium text-sm">{u.full_name}</div>
                                                    <div className="text-xs text-gray-500">{u.email}</div>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => removeUserFromModel(u.user_id)}
                                                    className="text-red-500 hover:text-red-700 text-sm px-2"
                                                >
                                                    Remove
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
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
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <div className="grid grid-cols-2 gap-6">
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Model ID</h4>
                            <p className="text-lg">{model.model_id}</p>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Status</h4>
                            <span className="px-2 py-1 text-sm rounded bg-blue-100 text-blue-800">
                                {model.status}
                            </span>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Development Type</h4>
                            <span className={`px-2 py-1 text-sm rounded ${
                                model.development_type === 'In-House'
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-purple-100 text-purple-800'
                            }`}>
                                {model.development_type}
                            </span>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Vendor</h4>
                            <p className="text-lg">{model.vendor?.name || '-'}</p>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Risk Tier</h4>
                            {model.risk_tier ? (
                                <span className="px-2 py-1 text-sm rounded bg-orange-100 text-orange-800">
                                    {model.risk_tier.label}
                                </span>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Validation Type</h4>
                            {model.validation_type ? (
                                <span className="px-2 py-1 text-sm rounded bg-indigo-100 text-indigo-800">
                                    {model.validation_type.label}
                                </span>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Owner</h4>
                            <p className="text-lg">{model.owner.full_name}</p>
                            <p className="text-sm text-gray-500">{model.owner.email}</p>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Developer</h4>
                            {model.developer ? (
                                <>
                                    <p className="text-lg">{model.developer.full_name}</p>
                                    <p className="text-sm text-gray-500">{model.developer.email}</p>
                                </>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
                        </div>
                        <div className="col-span-2">
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Description</h4>
                            <p className="text-lg">{model.description || 'No description'}</p>
                        </div>
                        <div className="col-span-2">
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Model Users</h4>
                            {model.users.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {model.users.map(u => (
                                        <span key={u.user_id} className="px-3 py-1 bg-gray-100 rounded text-sm">
                                            {u.full_name}
                                        </span>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-gray-500">No users assigned</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Created</h4>
                            <p className="text-sm">{new Date(model.created_at).toLocaleString()}</p>
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Last Updated</h4>
                            <p className="text-sm">{new Date(model.updated_at).toLocaleString()}</p>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

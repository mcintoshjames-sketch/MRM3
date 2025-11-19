import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';
import ModelRegionsSection from '../components/ModelRegionsSection';
import SubmitChangeModal from '../components/SubmitChangeModal';
import VersionsList from '../components/VersionsList';
import VersionDetailModal from '../components/VersionDetailModal';
import DelegatesSection from '../components/DelegatesSection';
import { useAuth } from '../contexts/AuthContext';
import { ModelVersion } from '../api/versions';

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

interface Region {
    region_id: number;
    code: string;
    name: string;
    requires_regional_approval: boolean;
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
    model_type_id: number | null;
    wholly_owned_region_id: number | null;
    status: string;
    created_at: string;
    updated_at: string;
    owner: User;
    developer: User | null;
    vendor: Vendor | null;
    risk_tier: TaxonomyValue | null;
    validation_type: TaxonomyValue | null;
    model_type: TaxonomyValue | null;
    wholly_owned_region: Region | null;
    users: User[];
    regulatory_categories: TaxonomyValue[];
}

interface Validation {
    validation_id: number;
    model_id: number;
    model_name: string;
    validation_date: string;
    validator_name: string;
    validation_type: string;
    outcome: string;
    scope: string;
    created_at: string;
}

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

export default function ModelDetailsPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();
    const [model, setModel] = useState<Model | null>(null);
    const [users, setUsers] = useState<User[]>([]);
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [taxonomies, setTaxonomies] = useState<Taxonomy[]>([]);
    const [validations, setValidations] = useState<Validation[]>([]);
    const [validationRequests, setValidationRequests] = useState<ValidationRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(false);
    const [activeTab, setActiveTab] = useState<'details' | 'versions' | 'delegates' | 'validations'>('details');
    const [showSubmitChangeModal, setShowSubmitChangeModal] = useState(false);
    const [selectedVersion, setSelectedVersion] = useState<ModelVersion | null>(null);
    const [versionsRefreshTrigger, setVersionsRefreshTrigger] = useState(0);
    const [userSearchTerm, setUserSearchTerm] = useState('');
    const [showUserDropdown, setShowUserDropdown] = useState(false);
    const [showCancelledValidations, setShowCancelledValidations] = useState(false);
    const [formData, setFormData] = useState({
        model_name: '',
        description: '',
        development_type: 'In-House',
        owner_id: 0,
        developer_id: null as number | null,
        vendor_id: null as number | null,
        risk_tier_id: null as number | null,
        validation_type_id: null as number | null,
        model_type_id: null as number | null,
        wholly_owned_region_id: null as number | null,
        status: 'In Development',
        user_ids: [] as number[],
        regulatory_category_ids: [] as number[]
    });

    useEffect(() => {
        fetchData();
    }, [id]);

    const fetchData = async () => {
        try {
            // Fetch critical model data first - these are required
            const [modelRes, usersRes, vendorsRes, regionsRes, taxonomiesRes] = await Promise.all([
                api.get(`/models/${id}`),
                api.get('/auth/users'),
                api.get('/vendors/'),
                api.get('/regions/'),
                api.get('/taxonomies/')
            ]);
            const modelData = modelRes.data;
            setModel(modelData);
            setUsers(usersRes.data);
            setVendors(vendorsRes.data);
            setRegions(regionsRes.data);

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
                model_type_id: modelData.model_type_id,
                wholly_owned_region_id: modelData.wholly_owned_region_id,
                status: modelData.status,
                user_ids: modelData.users.map((u: User) => u.user_id),
                regulatory_category_ids: modelData.regulatory_categories.map((c: TaxonomyValue) => c.value_id)
            });

            // Fetch validations separately - this is optional and shouldn't break the page
            try {
                const [validationsRes, validationRequestsRes] = await Promise.all([
                    api.get(`/validations/?model_id=${id}`),
                    api.get(`/validation-workflow/requests/?model_id=${id}`)
                ]);
                setValidations(validationsRes.data);
                setValidationRequests(validationRequestsRes.data);
            } catch (validationError) {
                console.error('Failed to fetch validations:', validationError);
                // Keep validations as empty array - don't break the page
                setValidations([]);
                setValidationRequests([]);
            }
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
                model_type_id: formData.model_type_id || null,
                wholly_owned_region_id: formData.wholly_owned_region_id || null,
                user_ids: formData.user_ids.length > 0 ? formData.user_ids : [],
                regulatory_category_ids: formData.regulatory_category_ids.length > 0 ? formData.regulatory_category_ids : []
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
    const getModelTypeTaxonomy = () => taxonomies.find(t => t.name === 'Model Type');
    const getRegulatoryCategoryTaxonomy = () => taxonomies.find(t => t.name === 'Regulatory Category');

    const toggleRegulatoryCategory = (valueId: number) => {
        setFormData(prev => {
            const ids = prev.regulatory_category_ids;
            if (ids.includes(valueId)) {
                return { ...prev, regulatory_category_ids: ids.filter(id => id !== valueId) };
            } else {
                return { ...prev, regulatory_category_ids: [...ids, valueId] };
            }
        });
    };

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
                    <div className="flex items-center gap-3">
                        <h2 className="text-2xl font-bold">{model.model_name}</h2>
                        {model.wholly_owned_region && (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800 border border-indigo-300">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                                </svg>
                                {model.wholly_owned_region.code}-Owned
                            </span>
                        )}
                    </div>
                </div>
                <div className="flex gap-2">
                    {!editing && (
                        <>
                            <button onClick={() => setShowSubmitChangeModal(true)} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                                Submit Change
                            </button>
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

            {/* Tabs */}
            {!editing && (
                <div className="border-b border-gray-200 mb-6">
                    <nav className="-mb-px flex space-x-8">
                        <button
                            onClick={() => setActiveTab('details')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'details'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            Model Details
                        </button>
                        <button
                            onClick={() => setActiveTab('versions')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'versions'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            Versions
                        </button>
                        <button
                            onClick={() => setActiveTab('delegates')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'delegates'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            Delegates
                        </button>
                        <button
                            onClick={() => setActiveTab('validations')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'validations'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            Validation History ({validationRequests.filter(req => req.current_status !== 'Approved' && req.current_status !== 'Cancelled').length} active, {validationRequests.filter(req => req.current_status === 'Approved').length + validations.length} historical)
                        </button>
                    </nav>
                </div>
            )}

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

                            {getModelTypeTaxonomy() && (
                                <div className="mb-4">
                                    <label htmlFor="model_type_id" className="block text-sm font-medium mb-2">
                                        Model Type
                                    </label>
                                    <select
                                        id="model_type_id"
                                        className="input-field"
                                        value={formData.model_type_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            model_type_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">Select Model Type</option>
                                        {getModelTypeTaxonomy()?.values
                                            .filter(v => v.is_active)
                                            .sort((a, b) => a.sort_order - b.sort_order)
                                            .map(v => (
                                                <option key={v.value_id} value={v.value_id}>{v.label}</option>
                                            ))}
                                    </select>
                                </div>
                            )}

                            <div className="mb-4">
                                <label htmlFor="wholly_owned_region_id" className="block text-sm font-medium mb-2">
                                    Wholly-Owned By Region
                                </label>
                                <select
                                    id="wholly_owned_region_id"
                                    className="input-field"
                                    value={formData.wholly_owned_region_id || ''}
                                    onChange={(e) => setFormData({
                                        ...formData,
                                        wholly_owned_region_id: e.target.value ? parseInt(e.target.value) : null
                                    })}
                                >
                                    <option value="">None (Global)</option>
                                    {regions.map(r => (
                                        <option key={r.region_id} value={r.region_id}>{r.name} ({r.code})</option>
                                    ))}
                                </select>
                                <p className="text-xs text-gray-500 mt-1">
                                    Select a region if this model is wholly-owned by that region's governance structure
                                </p>
                            </div>
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

                        {getRegulatoryCategoryTaxonomy() && (
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Regulatory Categories ({formData.regulatory_category_ids.length} selected)
                                </label>
                                <div className="border rounded bg-gray-50 p-3 max-h-48 overflow-y-auto">
                                    <div className="space-y-1">
                                        {getRegulatoryCategoryTaxonomy()?.values
                                            .filter(v => v.is_active)
                                            .sort((a, b) => a.sort_order - b.sort_order)
                                            .map(v => (
                                                <label key={v.value_id} className="flex items-start gap-2 cursor-pointer hover:bg-white p-1 rounded">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.regulatory_category_ids.includes(v.value_id)}
                                                        onChange={() => toggleRegulatoryCategory(v.value_id)}
                                                        className="mt-1"
                                                    />
                                                    <span className="text-sm">{v.label}</span>
                                                </label>
                                            ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">Save Changes</button>
                            <button type="button" onClick={() => setEditing(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            ) : activeTab === 'details' ? (
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
                            {model.vendor ? (
                                <Link
                                    to={`/vendors/${model.vendor.vendor_id}`}
                                    className="text-lg text-blue-600 hover:text-blue-800 hover:underline"
                                >
                                    {model.vendor.name}
                                </Link>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
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
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Model Type</h4>
                            {model.model_type ? (
                                <span className="px-2 py-1 text-sm rounded bg-teal-100 text-teal-800">
                                    {model.model_type.label}
                                </span>
                            ) : (
                                <p className="text-lg">-</p>
                            )}
                        </div>
                        <div>
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Wholly-Owned By Region</h4>
                            {model.wholly_owned_region ? (
                                <span className="inline-flex items-center gap-1.5 px-2 py-1 text-sm rounded bg-indigo-100 text-indigo-800 border border-indigo-300 font-medium">
                                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                                    </svg>
                                    {model.wholly_owned_region.name} ({model.wholly_owned_region.code})
                                </span>
                            ) : (
                                <p className="text-lg">Global</p>
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
                        <div className="col-span-2">
                            <h4 className="text-sm font-medium text-gray-500 mb-1">Regulatory Categories</h4>
                            {model.regulatory_categories.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {model.regulatory_categories.map(c => (
                                        <span key={c.value_id} className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded text-sm">
                                            {c.label}
                                        </span>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-gray-500">No regulatory categories assigned</p>
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

                    {/* Model-Region Management Section */}
                    <div className="mt-6">
                        <ModelRegionsSection
                            modelId={model.model_id}
                            whollyOwnedRegionId={model.wholly_owned_region_id}
                            whollyOwnedRegion={model.wholly_owned_region}
                        />
                    </div>
                </div>
            ) : activeTab === 'versions' ? (
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h3 className="text-lg font-semibold mb-4">Model Versions</h3>
                    <VersionsList
                        modelId={model.model_id}
                        refreshTrigger={versionsRefreshTrigger}
                        onVersionClick={(version) => setSelectedVersion(version)}
                    />
                </div>
            ) : activeTab === 'delegates' ? (
                <DelegatesSection
                    modelId={model.model_id}
                    modelOwnerId={model.owner_id}
                    currentUserId={user?.user_id || 0}
                />
            ) : (
                <div className="space-y-6">
                    {/* Active Validation Projects */}
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-blue-50 flex justify-between items-center">
                            <div>
                                <h3 className="text-lg font-bold">Active Validation Projects</h3>
                                <p className="text-sm text-gray-600">Workflow-based validation requests in progress</p>
                            </div>
                            <Link
                                to={`/validation-workflow/new?model_id=${model.model_id}`}
                                className="btn-primary text-sm"
                            >
                                + New Validation Request
                            </Link>
                        </div>
                        {validationRequests.filter(req =>
                            req.current_status !== 'Approved' &&
                            req.current_status !== 'Cancelled'
                        ).length === 0 ? (
                            <div className="p-6 text-center text-gray-500">
                                No active validation projects for this model.
                            </div>
                        ) : (
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Request ID
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Request Date
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Requestor
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Type
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Priority
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Status
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Primary Validator
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Target Date
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {validationRequests.filter(req =>
                                        req.current_status !== 'Approved' &&
                                        req.current_status !== 'Cancelled'
                                    ).map((request) => (
                                        <tr key={request.request_id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                                #{request.request_id}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                {request.request_date}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                {request.requestor_name}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                    {request.validation_type}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs rounded ${
                                                    request.priority === 'Critical' ? 'bg-red-100 text-red-800' :
                                                    request.priority === 'High' ? 'bg-orange-100 text-orange-800' :
                                                    request.priority === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                                                    'bg-green-100 text-green-800'
                                                }`}>
                                                    {request.priority}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`px-2 py-1 text-xs rounded ${
                                                    request.current_status === 'Intake' ? 'bg-gray-100 text-gray-800' :
                                                    request.current_status === 'Planning' ? 'bg-blue-100 text-blue-800' :
                                                    request.current_status === 'In Progress' ? 'bg-yellow-100 text-yellow-800' :
                                                    request.current_status === 'Review' ? 'bg-purple-100 text-purple-800' :
                                                    request.current_status === 'Pending Approval' ? 'bg-orange-100 text-orange-800' :
                                                    request.current_status === 'Approved' ? 'bg-green-100 text-green-800' :
                                                    'bg-red-100 text-red-800'
                                                }`}>
                                                    {request.current_status}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                {request.primary_validator || (
                                                    <span className="text-orange-600">Unassigned</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                {request.target_completion_date}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/validation-workflow/${request.request_id}`}
                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                >
                                                    View Details
                                                </Link>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* Historical Validations */}
                    <div className="bg-white rounded-lg shadow-md overflow-hidden">
                        <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
                            <div>
                                <h3 className="text-lg font-bold">Historical Validations</h3>
                                <p className="text-sm text-gray-600">Completed validation records (Approved {showCancelledValidations ? '& Cancelled' : ''})</p>
                            </div>
                            <label className="flex items-center gap-2 text-sm cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={showCancelledValidations}
                                    onChange={(e) => setShowCancelledValidations(e.target.checked)}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-gray-700">Show Cancelled</span>
                            </label>
                        </div>
                        {(() => {
                            const historicalRequests = validationRequests.filter(req =>
                                req.current_status === 'Approved' ||
                                (showCancelledValidations && req.current_status === 'Cancelled')
                            );
                            const totalHistorical = validations.length + historicalRequests.length;

                            return totalHistorical === 0 ? (
                                <div className="p-6 text-center text-gray-500">
                                    No historical validation records found for this model.
                                </div>
                            ) : (
                                <div>
                                    {/* Workflow-based Validations */}
                                    {historicalRequests.length > 0 && (
                                        <div className="border-b">
                                            <div className="px-4 py-2 bg-blue-50">
                                                <h4 className="text-sm font-semibold text-gray-700">Workflow-based Validations</h4>
                                            </div>
                                            <table className="min-w-full divide-y divide-gray-200">
                                                <thead className="bg-gray-50">
                                                    <tr>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Request ID
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Request Date
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Requestor
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Type
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Status
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Primary Validator
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Actions
                                                        </th>
                                                    </tr>
                                                </thead>
                                                <tbody className="bg-white divide-y divide-gray-200">
                                                    {historicalRequests.map((request) => (
                                                        <tr key={request.request_id} className="hover:bg-gray-50">
                                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                                                #{request.request_id}
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                                {request.request_date}
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                                {request.requestor_name}
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap">
                                                                <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                                    {request.validation_type}
                                                                </span>
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap">
                                                                <span className={`px-2 py-1 text-xs rounded ${
                                                                    request.current_status === 'Approved' ? 'bg-green-100 text-green-800' : 'bg-gray-400 text-white'
                                                                }`}>
                                                                    {request.current_status}
                                                                </span>
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                                {request.primary_validator || '-'}
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap">
                                                                <Link
                                                                    to={`/validation-workflow/${request.request_id}`}
                                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                                >
                                                                    View Details
                                                                </Link>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}

                                    {/* Legacy Validations */}
                                    {validations.length > 0 && (
                                        <div>
                                            <div className="px-4 py-2 bg-gray-50">
                                                <h4 className="text-sm font-semibold text-gray-700">Legacy Validation Records</h4>
                                            </div>
                                            <table className="min-w-full divide-y divide-gray-200">
                                                <thead className="bg-gray-50">
                                                    <tr>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Date
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Validator
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Type
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Outcome
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Scope
                                                        </th>
                                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                            Actions
                                                        </th>
                                                    </tr>
                                                </thead>
                                                <tbody className="bg-white divide-y divide-gray-200">
                                                    {validations.map((validation) => (
                                                        <tr key={validation.validation_id} className="hover:bg-gray-50">
                                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                                                {validation.validation_date}
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                                {validation.validator_name}
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap">
                                                                <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                                    {validation.validation_type}
                                                                </span>
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap">
                                                                <span className={`px-2 py-1 text-xs rounded ${
                                                                    validation.outcome === 'Pass'
                                                                        ? 'bg-green-100 text-green-800'
                                                                        : validation.outcome === 'Pass with Findings'
                                                                            ? 'bg-orange-100 text-orange-800'
                                                                            : 'bg-red-100 text-red-800'
                                                                }`}>
                                                                    {validation.outcome}
                                                                </span>
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap">
                                                                <span className="px-2 py-1 text-xs rounded bg-purple-100 text-purple-800">
                                                                    {validation.scope}
                                                                </span>
                                                            </td>
                                                            <td className="px-6 py-4 whitespace-nowrap">
                                                                <Link
                                                                    to={`/validations/${validation.validation_id}`}
                                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                                >
                                                                    View Details
                                                                </Link>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            );
                        })()}
                    </div>
                </div>
            )}

            {/* Submit Change Modal */}
            {showSubmitChangeModal && model && (
                <SubmitChangeModal
                    modelId={model.model_id}
                    onClose={() => setShowSubmitChangeModal(false)}
                    onSuccess={() => {
                        setVersionsRefreshTrigger(prev => prev + 1);
                        setActiveTab('versions');
                    }}
                />
            )}

            {selectedVersion && (
                <VersionDetailModal
                    version={selectedVersion}
                    onClose={() => setSelectedVersion(null)}
                    onSuccess={() => {
                        setVersionsRefreshTrigger(prev => prev + 1);
                        setSelectedVersion(null);
                    }}
                />
            )}
        </Layout>
    );
}

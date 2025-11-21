import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';
import { useTableSort } from '../hooks/useTableSort';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import { regionsApi, Region } from '../api/regions';

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

interface WhollyOwnedRegion {
    region_id: number;
    code: string;
    name: string;
}

interface Model {
    model_id: number;
    model_name: string;
    description: string;
    development_type: string;
    owner_id: number;
    developer_id: number | null;
    vendor_id: number | null;
    wholly_owned_region_id: number | null;
    wholly_owned_region: WhollyOwnedRegion | null;
    status: string;
    created_at: string;
    updated_at: string;
    owner: User;
    developer: User | null;
    vendor: Vendor | null;
    users: User[];
    regions: Region[];
}

export default function ModelsPage() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [models, setModels] = useState<Model[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({
        model_name: '',
        description: '',
        development_type: 'In-House',
        owner_id: 0,
        developer_id: null as number | null,
        vendor_id: null as number | null,
        wholly_owned_region_id: null as number | null,
        status: 'In Development',
        user_ids: [] as number[],
        region_ids: [] as number[],
        initial_version_number: '' as string,
        initial_implementation_date: '' as string,
        auto_create_validation: false,
        validation_request_type_id: 0,
        validation_request_priority_id: 0,
        validation_request_target_date: '' as string,
        validation_request_trigger_reason: '' as string
    });
    const [userSearchTerm, setUserSearchTerm] = useState('');
    const [validationTypes, setValidationTypes] = useState<any[]>([]);
    const [validationPriorities, setValidationPriorities] = useState<any[]>([]);

    // Filters
    const [filters, setFilters] = useState({
        search: '',
        development_types: [] as string[],
        statuses: [] as string[],
        owner_ids: [] as number[],
        vendor_ids: [] as number[],
        region_ids: [] as number[]
    });

    // Apply filters first, then sort
    const filteredModels = models.filter(model => {
        // Search filter (model name or description)
        if (filters.search && !model.model_name.toLowerCase().includes(filters.search.toLowerCase()) &&
            !model.description?.toLowerCase().includes(filters.search.toLowerCase())) {
            return false;
        }

        // Development type filter (multi-select)
        if (filters.development_types.length > 0 && !filters.development_types.includes(model.development_type)) {
            return false;
        }

        // Status filter (multi-select)
        if (filters.statuses.length > 0 && !filters.statuses.includes(model.status)) {
            return false;
        }

        // Owner filter (multi-select)
        if (filters.owner_ids.length > 0 && !filters.owner_ids.includes(model.owner_id)) {
            return false;
        }

        // Vendor filter (multi-select)
        if (filters.vendor_ids.length > 0) {
            // For third-party models, check if vendor is in the selected list
            // For in-house models (vendor_id is null), exclude them
            if (model.vendor_id === null || !filters.vendor_ids.includes(model.vendor_id)) {
                return false;
            }
        }

        // Region filter (multi-select)
        if (filters.region_ids.length > 0) {
            // Check if model has any of the selected regions
            // If model has no regions (global), exclude it
            if (!model.regions || model.regions.length === 0) {
                return false;
            }
            const modelRegionIds = model.regions.map(r => r.region_id);
            const hasMatchingRegion = filters.region_ids.some(rid => modelRegionIds.includes(rid));
            if (!hasMatchingRegion) {
                return false;
            }
        }

        return true;
    });

    // Table sorting (applied to filtered data)
    const { sortedData, requestSort, getSortIcon } = useTableSort<Model>(filteredModels, 'model_name');

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [modelsRes, usersRes, vendorsRes, regionsRes, taxonomiesRes] = await Promise.all([
                api.get('/models/'),
                api.get('/auth/users'),
                api.get('/vendors/'),
                api.get('/regions/'),
                api.get('/taxonomies/')
            ]);
            setModels(modelsRes.data);
            setUsers(usersRes.data);
            setVendors(vendorsRes.data);
            setRegions(regionsRes.data);

            // Fetch taxonomy values for validation types and priorities
            const taxonomyList = taxonomiesRes.data;
            const taxDetails = await Promise.all(
                taxonomyList.map((t: any) => api.get(`/taxonomies/${t.taxonomy_id}`))
            );
            const taxonomies = taxDetails.map((r: any) => r.data);

            const valType = taxonomies.find((t: any) => t.name === 'Validation Type');
            const valPriority = taxonomies.find((t: any) => t.name === 'Validation Priority');

            if (valType) {
                setValidationTypes(valType.values || []);
            }
            if (valPriority) {
                setValidationPriorities(valPriority.values || []);
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate auto-create validation fields if checkbox is checked
        if (formData.auto_create_validation) {
            if (!formData.validation_request_type_id || formData.validation_request_type_id === 0) {
                alert('Please select a Validation Type when auto-creating a validation project.');
                return;
            }
            if (!formData.validation_request_priority_id || formData.validation_request_priority_id === 0) {
                alert('Please select a Priority when auto-creating a validation project.');
                return;
            }
        }

        try {
            const payload = {
                ...formData,
                developer_id: formData.developer_id || null,
                vendor_id: formData.vendor_id || null,
                wholly_owned_region_id: formData.wholly_owned_region_id || null,
                user_ids: formData.user_ids.length > 0 ? formData.user_ids : null,
                region_ids: formData.region_ids.length > 0 ? formData.region_ids : null,
                initial_version_number: formData.initial_version_number || null,
                initial_implementation_date: formData.initial_implementation_date || null,
                validation_request_type_id: formData.validation_request_type_id || null,
                validation_request_priority_id: formData.validation_request_priority_id || null,
                validation_request_target_date: formData.validation_request_target_date || null,
                validation_request_trigger_reason: formData.validation_request_trigger_reason || null
            };
            const response = await api.post('/models/', payload);

            // Check for warnings in the response
            if (response.data.warnings && response.data.warnings.length > 0) {
                const warningMessages = response.data.warnings.map((w: any) => w.message).join('\n\n');
                const viewModel = confirm(`Model created successfully, but with warnings:\n\n${warningMessages}\n\nWould you like to view the model details?`);

                if (viewModel && response.data.model_id) {
                    // Navigate to model details page
                    navigate(`/models/${response.data.model_id}`);
                    return;
                }
            }

            setShowForm(false);
            setFormData({
                model_name: '',
                description: '',
                development_type: 'In-House',
                owner_id: 0,
                developer_id: null,
                vendor_id: null,
                wholly_owned_region_id: null,
                status: 'In Development',
                user_ids: [],
                region_ids: [],
                initial_version_number: '',
                initial_implementation_date: '',
                auto_create_validation: false,
                validation_request_type_id: 0,
                validation_request_priority_id: 0,
                validation_request_target_date: '',
                validation_request_trigger_reason: ''
            });
            fetchData();
        } catch (error: any) {
            console.error('Failed to create model:', error);
            alert(`Failed to create model: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
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
                                    value={formData.owner_id || ''}
                                    onChange={(e) => setFormData({ ...formData, owner_id: e.target.value ? parseInt(e.target.value) : 0 })}
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

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Deployment Regions (Optional)
                                </label>
                                <MultiSelectDropdown
                                    label=""
                                    placeholder="Select Regions"
                                    options={regions.map(r => ({
                                        value: r.region_id,
                                        label: `${r.name} (${r.code})`
                                    }))}
                                    selectedValues={formData.region_ids}
                                    onChange={(values) => setFormData({
                                        ...formData,
                                        region_ids: values as number[]
                                    })}
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Select regions where this model will be deployed. The wholly-owned region (if selected) will be automatically included.
                                </p>
                            </div>

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

                            <div className="mb-4">
                                <label htmlFor="initial_version_number" className="block text-sm font-medium mb-2">
                                    Initial Version Number (Optional)
                                </label>
                                <input
                                    id="initial_version_number"
                                    type="text"
                                    className="input-field"
                                    placeholder="1.0"
                                    value={formData.initial_version_number}
                                    onChange={(e) => setFormData({ ...formData, initial_version_number: e.target.value })}
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Starting version number for this model (defaults to 1.0 if not specified)
                                </p>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="initial_implementation_date" className="block text-sm font-medium mb-2">
                                    Implementation Date (Optional)
                                </label>
                                <input
                                    id="initial_implementation_date"
                                    type="date"
                                    className="input-field"
                                    value={formData.initial_implementation_date}
                                    onChange={(e) => setFormData({ ...formData, initial_implementation_date: e.target.value })}
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Date when this model was (or will be) implemented in production
                                </p>
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

                        {/* Auto-create Validation Project Section */}
                        <div className="mb-4 border-t pt-4">
                            <div className="mb-4">
                                <label className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        checked={formData.auto_create_validation}
                                        onChange={(e) => {
                                            const isChecked = e.target.checked;
                                            // Find "Initial" validation type and set as default
                                            const initialValidationType = validationTypes.find(vt =>
                                                vt.code === 'INITIAL' || vt.label.toLowerCase().includes('initial')
                                            );
                                            setFormData({
                                                ...formData,
                                                auto_create_validation: isChecked,
                                                validation_request_type_id: isChecked && initialValidationType ? initialValidationType.value_id : 0
                                            });
                                        }}
                                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                    />
                                    <span className="text-sm font-medium">Auto-create validation project upon model creation</span>
                                </label>
                                <p className="text-xs text-gray-500 mt-1 ml-6">
                                    Automatically create a validation project for this model when it is created
                                </p>
                            </div>

                            {formData.auto_create_validation && (
                                <div className="ml-6 space-y-4 p-4 bg-gray-50 rounded">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label htmlFor="validation_request_type_id" className="block text-sm font-medium mb-2">
                                                Validation Type <span className="text-red-500">*</span>
                                            </label>
                                            <select
                                                id="validation_request_type_id"
                                                className="input-field"
                                                value={formData.validation_request_type_id || ''}
                                                onChange={(e) => setFormData({ ...formData, validation_request_type_id: e.target.value ? parseInt(e.target.value) : 0 })}
                                                required={formData.auto_create_validation}
                                            >
                                                <option value="">-- Select Validation Type --</option>
                                                {validationTypes.map(vt => (
                                                    <option key={vt.value_id} value={vt.value_id}>
                                                        {vt.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>

                                        <div>
                                            <label htmlFor="validation_request_priority_id" className="block text-sm font-medium mb-2">
                                                Priority <span className="text-red-500">*</span>
                                            </label>
                                            <select
                                                id="validation_request_priority_id"
                                                className="input-field"
                                                value={formData.validation_request_priority_id || ''}
                                                onChange={(e) => setFormData({ ...formData, validation_request_priority_id: e.target.value ? parseInt(e.target.value) : 0 })}
                                                required={formData.auto_create_validation}
                                            >
                                                <option value="">-- Select Priority --</option>
                                                {validationPriorities.map(vp => (
                                                    <option key={vp.value_id} value={vp.value_id}>
                                                        {vp.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>

                                    <div>
                                        <label htmlFor="validation_request_target_date" className="block text-sm font-medium mb-2">
                                            Target Completion Date (Optional)
                                        </label>
                                        <input
                                            id="validation_request_target_date"
                                            type="date"
                                            className="input-field"
                                            value={formData.validation_request_target_date}
                                            onChange={(e) => setFormData({ ...formData, validation_request_target_date: e.target.value })}
                                        />
                                    </div>

                                    <div>
                                        <label htmlFor="validation_request_trigger_reason" className="block text-sm font-medium mb-2">
                                            Trigger Reason (Optional)
                                        </label>
                                        <textarea
                                            id="validation_request_trigger_reason"
                                            className="input-field"
                                            rows={2}
                                            placeholder="Reason for validation project..."
                                            value={formData.validation_request_trigger_reason}
                                            onChange={(e) => setFormData({ ...formData, validation_request_trigger_reason: e.target.value })}
                                        />
                                    </div>
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

            {/* Filters */}
            <div className="bg-white p-4 rounded-lg shadow-md mb-6">
                <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
                    {/* Search */}
                    <div>
                        <label htmlFor="filter-search" className="block text-xs font-medium text-gray-700 mb-1">
                            Search
                        </label>
                        <input
                            id="filter-search"
                            type="text"
                            className="input-field text-sm"
                            placeholder="Model name or description..."
                            value={filters.search}
                            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                        />
                    </div>

                    {/* Development Type */}
                    <MultiSelectDropdown
                        label="Development Type"
                        placeholder="All Types"
                        options={[
                            { value: 'In-House', label: 'In-House' },
                            { value: 'Third-Party', label: 'Third-Party' }
                        ]}
                        selectedValues={filters.development_types}
                        onChange={(values) => setFilters({ ...filters, development_types: values as string[] })}
                    />

                    {/* Status */}
                    <MultiSelectDropdown
                        label="Status"
                        placeholder="All Statuses"
                        options={[
                            { value: 'In Development', label: 'In Development' },
                            { value: 'Active', label: 'Active' },
                            { value: 'Retired', label: 'Retired' }
                        ]}
                        selectedValues={filters.statuses}
                        onChange={(values) => setFilters({ ...filters, statuses: values as string[] })}
                    />

                    {/* Owner */}
                    <MultiSelectDropdown
                        label="Owner"
                        placeholder="All Owners"
                        options={users.map(u => ({ value: u.user_id, label: u.full_name }))}
                        selectedValues={filters.owner_ids}
                        onChange={(values) => setFilters({ ...filters, owner_ids: values as number[] })}
                    />

                    {/* Vendor */}
                    <MultiSelectDropdown
                        label="Vendor"
                        placeholder="All Vendors"
                        options={vendors.map(v => ({ value: v.vendor_id, label: v.name }))}
                        selectedValues={filters.vendor_ids}
                        onChange={(values) => setFilters({ ...filters, vendor_ids: values as number[] })}
                    />

                    {/* Region */}
                    <MultiSelectDropdown
                        label="Region"
                        placeholder="All Regions"
                        options={regions.map(r => ({ value: r.region_id, label: `${r.name} (${r.code})` }))}
                        selectedValues={filters.region_ids}
                        onChange={(values) => setFilters({ ...filters, region_ids: values as number[] })}
                    />
                </div>

                {/* Clear Filters and Results Count */}
                <div className="flex items-center justify-between mt-3 pt-3 border-t">
                    <div className="text-sm text-gray-600">
                        Showing <span className="font-semibold">{sortedData.length}</span> of{' '}
                        <span className="font-semibold">{models.length}</span> models
                    </div>
                    <button
                        onClick={() => setFilters({
                            search: '',
                            development_types: [],
                            statuses: [],
                            owner_ids: [],
                            vendor_ids: [],
                            region_ids: []
                        })}
                        className="text-sm text-blue-600 hover:text-blue-800"
                    >
                        Clear Filters
                    </button>
                </div>
            </div>

            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('model_name')}
                            >
                                <div className="flex items-center gap-2">
                                    Name
                                    {getSortIcon('model_name')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('development_type')}
                            >
                                <div className="flex items-center gap-2">
                                    Type
                                    {getSortIcon('development_type')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('owner.full_name')}
                            >
                                <div className="flex items-center gap-2">
                                    Owner
                                    {getSortIcon('owner.full_name')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('developer.full_name')}
                            >
                                <div className="flex items-center gap-2">
                                    Developer
                                    {getSortIcon('developer.full_name')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('vendor.name')}
                            >
                                <div className="flex items-center gap-2">
                                    Vendor
                                    {getSortIcon('vendor.name')}
                                </div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Regions</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Users</th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('status')}
                            >
                                <div className="flex items-center gap-2">
                                    Status
                                    {getSortIcon('status')}
                                </div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedData.length === 0 ? (
                            <tr>
                                <td colSpan={9} className="px-6 py-4 text-center text-gray-500">
                                    No models yet. Click "Add Model" to create one.
                                </td>
                            </tr>
                        ) : (
                            sortedData.map((model) => (
                                <tr key={model.model_id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => navigate(`/models/${model.model_id}`)}
                                                className="font-medium text-blue-600 hover:text-blue-800 text-left"
                                            >
                                                {model.model_name}
                                            </button>
                                            {model.wholly_owned_region && (
                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 border border-indigo-300 whitespace-nowrap">
                                                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                                        <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                                                    </svg>
                                                    {model.wholly_owned_region.code}
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-sm text-gray-500">{model.description || '-'}</div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs rounded ${model.development_type === 'In-House'
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
                                    <td className="px-6 py-4 text-sm">
                                        {model.regions && model.regions.length > 0 ? (
                                            <div className="flex flex-wrap gap-1">
                                                {model.regions.map(r => (
                                                    <span key={r.region_id} className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs font-semibold">
                                                        {r.region_code}
                                                    </span>
                                                ))}
                                            </div>
                                        ) : (
                                            <span className="text-gray-400">Global</span>
                                        )}
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

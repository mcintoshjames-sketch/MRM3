import { useState, useEffect } from 'react';
import api from '../api/client';
import Layout from '../components/Layout';

// ============================================================================
// TYPES - General Taxonomy
// ============================================================================

interface TaxonomyValue {
    value_id: number;
    taxonomy_id: number;
    code: string;
    label: string;
    description: string | null;
    sort_order: number;
    is_active: boolean;
    created_at: string;
}

interface Taxonomy {
    taxonomy_id: number;
    name: string;
    description: string | null;
    is_system: boolean;
    created_at: string;
    values: TaxonomyValue[];
}

// ============================================================================
// TYPES - Change Type Taxonomy
// ============================================================================

interface ModelChangeType {
    change_type_id: number;
    category_id: number;
    code: number;
    name: string;
    description: string | null;
    mv_activity: string | null;
    requires_mv_approval: boolean;
    sort_order: number;
    is_active: boolean;
}

interface ModelChangeCategory {
    category_id: number;
    code: string;
    name: string;
    sort_order: number;
    change_types: ModelChangeType[];
}

export default function TaxonomyPage() {
    // Tab management
    const [activeTab, setActiveTab] = useState<'general' | 'change-type'>('general');

    // General taxonomy state
    const [taxonomies, setTaxonomies] = useState<Taxonomy[]>([]);
    const [selectedTaxonomy, setSelectedTaxonomy] = useState<Taxonomy | null>(null);
    const [showTaxonomyForm, setShowTaxonomyForm] = useState(false);
    const [showValueForm, setShowValueForm] = useState(false);
    const [editingValue, setEditingValue] = useState<TaxonomyValue | null>(null);
    const [taxonomyFormData, setTaxonomyFormData] = useState({
        name: '',
        description: ''
    });
    const [valueFormData, setValueFormData] = useState({
        code: '',
        label: '',
        description: '',
        sort_order: 0,
        is_active: true
    });

    // Change type taxonomy state
    const [categories, setCategories] = useState<ModelChangeCategory[]>([]);
    const [selectedCategory, setSelectedCategory] = useState<ModelChangeCategory | null>(null);
    const [showCategoryForm, setShowCategoryForm] = useState(false);
    const [showChangeTypeForm, setShowChangeTypeForm] = useState(false);
    const [editingChangeType, setEditingChangeType] = useState<ModelChangeType | null>(null);
    const [categoryFormData, setCategoryFormData] = useState({
        code: '',
        name: '',
        sort_order: 0
    });
    const [changeTypeFormData, setChangeTypeFormData] = useState({
        code: 0,
        name: '',
        description: '',
        mv_activity: '',
        requires_mv_approval: false,
        sort_order: 0,
        is_active: true
    });

    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (activeTab === 'general') {
            fetchTaxonomies();
        } else {
            fetchChangeCategories();
        }
    }, [activeTab]);

    // ============================================================================
    // GENERAL TAXONOMY FUNCTIONS
    // ============================================================================

    const fetchTaxonomies = async () => {
        try {
            const response = await api.get('/taxonomies/');
            setTaxonomies(response.data);
            if (response.data.length > 0 && !selectedTaxonomy) {
                const detailRes = await api.get(`/taxonomies/${response.data[0].taxonomy_id}`);
                setSelectedTaxonomy(detailRes.data);
            }
        } catch (error) {
            console.error('Failed to fetch taxonomies:', error);
        } finally {
            setLoading(false);
        }
    };

    const selectTaxonomy = async (taxonomyId: number) => {
        try {
            const response = await api.get(`/taxonomies/${taxonomyId}`);
            setSelectedTaxonomy(response.data);
        } catch (error) {
            console.error('Failed to fetch taxonomy:', error);
        }
    };

    const resetTaxonomyForm = () => {
        setTaxonomyFormData({ name: '', description: '' });
        setShowTaxonomyForm(false);
    };

    const resetValueForm = () => {
        setValueFormData({
            code: '',
            label: '',
            description: '',
            sort_order: 0,
            is_active: true
        });
        setEditingValue(null);
        setShowValueForm(false);
    };

    const handleTaxonomySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/taxonomies/', taxonomyFormData);
            resetTaxonomyForm();
            fetchTaxonomies();
        } catch (error) {
            console.error('Failed to create taxonomy:', error);
        }
    };

    const handleValueSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedTaxonomy) return;

        try {
            if (editingValue) {
                await api.patch(`/taxonomies/values/${editingValue.value_id}`, valueFormData);
            } else {
                await api.post(`/taxonomies/${selectedTaxonomy.taxonomy_id}/values`, valueFormData);
            }
            resetValueForm();
            selectTaxonomy(selectedTaxonomy.taxonomy_id);
        } catch (error) {
            console.error('Failed to save value:', error);
        }
    };

    const handleEditValue = (value: TaxonomyValue) => {
        setEditingValue(value);
        setValueFormData({
            code: value.code,
            label: value.label,
            description: value.description || '',
            sort_order: value.sort_order,
            is_active: value.is_active
        });
        setShowValueForm(true);
    };

    const handleDeleteValue = async (valueId: number) => {
        if (!confirm('Are you sure you want to delete this value?')) return;
        if (!selectedTaxonomy) return;

        try {
            await api.delete(`/taxonomies/values/${valueId}`);
            selectTaxonomy(selectedTaxonomy.taxonomy_id);
        } catch (error) {
            console.error('Failed to delete value:', error);
        }
    };

    const isSystemProtectedValue = (value: TaxonomyValue): boolean => {
        return selectedTaxonomy?.name === 'Validation Type' && value.code === 'TARGETED';
    };

    const handleDeleteTaxonomy = async (taxonomyId: number) => {
        if (!confirm('Are you sure you want to delete this taxonomy and all its values?')) return;

        try {
            await api.delete(`/taxonomies/${taxonomyId}`);
            setSelectedTaxonomy(null);
            fetchTaxonomies();
        } catch (error) {
            console.error('Failed to delete taxonomy:', error);
        }
    };

    // ============================================================================
    // CHANGE TYPE TAXONOMY FUNCTIONS
    // ============================================================================

    const fetchChangeCategories = async () => {
        try {
            // Admin UI needs to see all types (active and inactive)
            const response = await api.get('/change-taxonomy/categories?active_only=false');
            setCategories(response.data);
            if (response.data.length > 0 && !selectedCategory) {
                setSelectedCategory(response.data[0]);
            }
        } catch (error) {
            console.error('Failed to fetch change categories:', error);
        } finally {
            setLoading(false);
        }
    };

    const selectCategory = (category: ModelChangeCategory) => {
        setSelectedCategory(category);
    };

    const resetCategoryForm = () => {
        setCategoryFormData({ code: '', name: '', sort_order: 0 });
        setShowCategoryForm(false);
    };

    const resetChangeTypeForm = () => {
        setChangeTypeFormData({
            code: 0,
            name: '',
            description: '',
            mv_activity: '',
            requires_mv_approval: false,
            sort_order: 0,
            is_active: true
        });
        setEditingChangeType(null);
        setShowChangeTypeForm(false);
    };

    const handleCategorySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/change-taxonomy/categories', categoryFormData);
            resetCategoryForm();
            fetchChangeCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to create category');
            console.error('Failed to create category:', error);
        }
    };

    const handleChangeTypeSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedCategory) return;

        try {
            if (editingChangeType) {
                await api.patch(`/change-taxonomy/types/${editingChangeType.change_type_id}`, changeTypeFormData);
            } else {
                await api.post('/change-taxonomy/types', {
                    ...changeTypeFormData,
                    category_id: selectedCategory.category_id
                });
            }
            resetChangeTypeForm();
            fetchChangeCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to save change type');
            console.error('Failed to save change type:', error);
        }
    };

    const handleEditChangeType = (type: ModelChangeType) => {
        setEditingChangeType(type);
        setChangeTypeFormData({
            code: type.code,
            name: type.name,
            description: type.description || '',
            mv_activity: type.mv_activity || '',
            requires_mv_approval: type.requires_mv_approval,
            sort_order: type.sort_order,
            is_active: type.is_active
        });
        setShowChangeTypeForm(true);
    };

    const handleDeleteChangeType = async (changeTypeId: number) => {
        if (!confirm('Are you sure you want to delete this change type?')) return;

        try {
            await api.delete(`/change-taxonomy/types/${changeTypeId}`);
            fetchChangeCategories();
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || 'Failed to delete change type';

            // Check if it's a referential integrity error
            if (error.response?.status === 409) {
                const deactivate = confirm(
                    `${errorMessage}\n\n` +
                    `Would you like to deactivate this change type instead? ` +
                    `This will hide it from the dropdown while preserving historical data.`
                );

                if (deactivate) {
                    try {
                        await api.patch(`/change-taxonomy/types/${changeTypeId}`, {
                            is_active: false
                        });
                        fetchChangeCategories();
                        alert('Change type has been deactivated successfully.');
                    } catch (deactivateError: any) {
                        alert(deactivateError.response?.data?.detail || 'Failed to deactivate change type');
                    }
                }
            } else {
                alert(errorMessage);
            }
            console.error('Failed to delete change type:', error);
        }
    };

    const handleDeleteCategory = async (categoryId: number) => {
        if (!confirm('Are you sure you want to delete this category and all its change types?')) return;

        try {
            await api.delete(`/change-taxonomy/categories/${categoryId}`);
            setSelectedCategory(null);
            fetchChangeCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to delete category');
            console.error('Failed to delete category:', error);
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
                <h2 className="text-2xl font-bold">Taxonomy Management</h2>
            </div>

            {/* Tab Toggle */}
            <div className="mb-6">
                <div className="border-b border-gray-200">
                    <nav className="-mb-px flex space-x-8">
                        <button
                            onClick={() => setActiveTab('general')}
                            className={`${
                                activeTab === 'general'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                        >
                            General Taxonomies
                        </button>
                        <button
                            onClick={() => setActiveTab('change-type')}
                            className={`${
                                activeTab === 'change-type'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                        >
                            Change Type Taxonomy
                        </button>
                    </nav>
                </div>
            </div>

            {/* GENERAL TAXONOMIES TAB */}
            {activeTab === 'general' && (
                <>
                    <div className="mb-6 flex justify-end">
                        <button onClick={() => setShowTaxonomyForm(true)} className="btn-primary">
                            + New Taxonomy
                        </button>
                    </div>

                    {showTaxonomyForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h3 className="text-lg font-bold mb-4">Create New Taxonomy</h3>
                            <form onSubmit={handleTaxonomySubmit}>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="mb-4">
                                        <label htmlFor="tax_name" className="block text-sm font-medium mb-2">
                                            Name
                                        </label>
                                        <input
                                            id="tax_name"
                                            type="text"
                                            className="input-field"
                                            value={taxonomyFormData.name}
                                            onChange={(e) => setTaxonomyFormData({ ...taxonomyFormData, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="tax_desc" className="block text-sm font-medium mb-2">
                                            Description
                                        </label>
                                        <input
                                            id="tax_desc"
                                            type="text"
                                            className="input-field"
                                            value={taxonomyFormData.description}
                                            onChange={(e) => setTaxonomyFormData({ ...taxonomyFormData, description: e.target.value })}
                                        />
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">Create</button>
                                    <button type="button" onClick={resetTaxonomyForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="grid grid-cols-4 gap-6">
                        {/* Taxonomy list */}
                        <div className="col-span-1">
                            <div className="bg-white rounded-lg shadow-md p-4">
                                <h3 className="font-bold mb-3">Taxonomies</h3>
                                <div className="space-y-2">
                                    {taxonomies.length === 0 ? (
                                        <p className="text-sm text-gray-500">No taxonomies yet.</p>
                                    ) : (
                                        taxonomies.map((tax) => (
                                            <button
                                                key={tax.taxonomy_id}
                                                onClick={() => selectTaxonomy(tax.taxonomy_id)}
                                                className={`w-full text-left px-3 py-2 rounded text-sm ${selectedTaxonomy?.taxonomy_id === tax.taxonomy_id
                                                    ? 'bg-blue-100 text-blue-800 font-medium'
                                                    : 'hover:bg-gray-100'
                                                    }`}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span>{tax.name}</span>
                                                    {tax.is_system && (
                                                        <span className="text-xs bg-gray-200 px-1 rounded">System</span>
                                                    )}
                                                </div>
                                            </button>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Selected taxonomy details and values */}
                        <div className="col-span-3">
                            {selectedTaxonomy ? (
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <h3 className="text-xl font-bold">{selectedTaxonomy.name}</h3>
                                            {selectedTaxonomy.description && (
                                                <p className="text-gray-600 mt-1">{selectedTaxonomy.description}</p>
                                            )}
                                            <div className="flex gap-2 mt-2">
                                                {selectedTaxonomy.is_system && (
                                                    <span className="text-xs bg-gray-200 px-2 py-1 rounded">
                                                        System Taxonomy
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setShowValueForm(true)}
                                                className="btn-primary text-sm"
                                            >
                                                + Add Value
                                            </button>
                                            {!selectedTaxonomy.is_system && (
                                                <button
                                                    onClick={() => handleDeleteTaxonomy(selectedTaxonomy.taxonomy_id)}
                                                    className="btn-secondary text-red-600 text-sm"
                                                >
                                                    Delete Taxonomy
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    {showValueForm && (
                                        <div className="bg-gray-50 p-4 rounded mb-4">
                                            <h4 className="font-medium mb-3">
                                                {editingValue ? 'Edit Value' : 'Add New Value'}
                                            </h4>
                                            <form onSubmit={handleValueSubmit}>
                                                <div className="grid grid-cols-3 gap-4">
                                                    <div className="mb-3">
                                                        <label htmlFor="val_code" className="block text-sm font-medium mb-1">
                                                            Code {editingValue && <span className="text-xs text-gray-500">(immutable)</span>}
                                                        </label>
                                                        <input
                                                            id="val_code"
                                                            type="text"
                                                            className={`input-field ${editingValue ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                                                            value={valueFormData.code}
                                                            onChange={(e) => setValueFormData({ ...valueFormData, code: e.target.value })}
                                                            disabled={!!editingValue}
                                                            readOnly={!!editingValue}
                                                            required
                                                            title={editingValue ? "Code cannot be changed after creation to maintain data integrity" : ""}
                                                        />
                                                    </div>
                                                    <div className="mb-3">
                                                        <label htmlFor="val_label" className="block text-sm font-medium mb-1">
                                                            Label
                                                        </label>
                                                        <input
                                                            id="val_label"
                                                            type="text"
                                                            className="input-field"
                                                            value={valueFormData.label}
                                                            onChange={(e) => setValueFormData({ ...valueFormData, label: e.target.value })}
                                                            required
                                                        />
                                                    </div>
                                                    <div className="mb-3">
                                                        <label htmlFor="val_order" className="block text-sm font-medium mb-1">
                                                            Sort Order
                                                        </label>
                                                        <input
                                                            id="val_order"
                                                            type="number"
                                                            className="input-field"
                                                            value={valueFormData.sort_order}
                                                            onChange={(e) => setValueFormData({ ...valueFormData, sort_order: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                </div>
                                                <div className="mb-3">
                                                    <label htmlFor="val_desc" className="block text-sm font-medium mb-1">
                                                        Description
                                                    </label>
                                                    <textarea
                                                        id="val_desc"
                                                        className="input-field"
                                                        rows={2}
                                                        value={valueFormData.description}
                                                        onChange={(e) => setValueFormData({ ...valueFormData, description: e.target.value })}
                                                    />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="flex items-center gap-2">
                                                        <input
                                                            type="checkbox"
                                                            checked={valueFormData.is_active}
                                                            onChange={(e) => setValueFormData({ ...valueFormData, is_active: e.target.checked })}
                                                        />
                                                        <span className="text-sm font-medium">Active</span>
                                                    </label>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button type="submit" className="btn-primary text-sm">
                                                        {editingValue ? 'Update' : 'Add'}
                                                    </button>
                                                    <button type="button" onClick={resetValueForm} className="btn-secondary text-sm">
                                                        Cancel
                                                    </button>
                                                </div>
                                            </form>
                                        </div>
                                    )}

                                    <div className="mt-4">
                                        <h4 className="font-medium mb-3">
                                            Values ({selectedTaxonomy.values.length})
                                        </h4>
                                        {selectedTaxonomy.values.length === 0 ? (
                                            <p className="text-gray-500 text-sm">No values yet. Add values to this taxonomy.</p>
                                        ) : (
                                            <div className="border rounded overflow-x-auto">
                                                <table className="min-w-full divide-y divide-gray-200">
                                                    <thead className="bg-gray-50">
                                                        <tr>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-16">
                                                                Order
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-32">
                                                                Code
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                Label
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                Description
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-48">
                                                                Actions
                                                            </th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="bg-white divide-y divide-gray-200">
                                                        {selectedTaxonomy.values
                                                            .sort((a, b) => a.sort_order - b.sort_order)
                                                            .map((value) => (
                                                                <tr key={value.value_id} className={`hover:bg-gray-50 ${!value.is_active ? 'opacity-60' : ''}`}>
                                                                    <td className="px-4 py-3 text-sm text-center">{value.sort_order}</td>
                                                                    <td className="px-4 py-3 text-sm font-mono break-words">{value.code}</td>
                                                                    <td className="px-4 py-3 text-sm font-medium">
                                                                        <div className="flex items-center gap-2">
                                                                            {value.label}
                                                                            {!value.is_active && (
                                                                                <span className="px-1.5 py-0.5 text-xs rounded bg-gray-200 text-gray-600">
                                                                                    Inactive
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-gray-600">
                                                                        {value.description || '-'}
                                                                    </td>
                                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                                        <div className="flex items-center gap-2">
                                                                            <button
                                                                                onClick={() => handleEditValue(value)}
                                                                                className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 hover:bg-blue-200 rounded text-sm font-medium transition-colors"
                                                                                title="Edit this value"
                                                                            >
                                                                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                                                </svg>
                                                                                Edit
                                                                            </button>
                                                                            {isSystemProtectedValue(value) ? (
                                                                                <button
                                                                                    disabled
                                                                                    className="inline-flex items-center px-3 py-1 bg-gray-100 text-gray-400 rounded text-sm font-medium cursor-not-allowed"
                                                                                    title="This value is used by the system for auto-generated validation projects and cannot be deleted"
                                                                                >
                                                                                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                                    </svg>
                                                                                    Delete
                                                                                </button>
                                                                            ) : (
                                                                                <button
                                                                                    onClick={() => handleDeleteValue(value.value_id)}
                                                                                    className="inline-flex items-center px-3 py-1 bg-red-100 text-red-700 hover:bg-red-200 rounded text-sm font-medium transition-colors"
                                                                                    title="Delete this value"
                                                                                >
                                                                                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                                    </svg>
                                                                                    Delete
                                                                                </button>
                                                                            )}
                                                                        </div>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-white rounded-lg shadow-md p-6 text-center text-gray-500">
                                    Select a taxonomy to view and manage its values.
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}

            {/* CHANGE TYPE TAXONOMY TAB */}
            {activeTab === 'change-type' && (
                <>
                    <div className="mb-6 flex justify-end">
                        <button onClick={() => setShowCategoryForm(true)} className="btn-primary">
                            + New Category
                        </button>
                    </div>

                    {showCategoryForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h3 className="text-lg font-bold mb-4">Create New Change Category</h3>
                            <form onSubmit={handleCategorySubmit}>
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="mb-4">
                                        <label htmlFor="cat_code" className="block text-sm font-medium mb-2">
                                            Code
                                        </label>
                                        <input
                                            id="cat_code"
                                            type="text"
                                            className="input-field"
                                            value={categoryFormData.code}
                                            onChange={(e) => setCategoryFormData({ ...categoryFormData, code: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="cat_name" className="block text-sm font-medium mb-2">
                                            Name
                                        </label>
                                        <input
                                            id="cat_name"
                                            type="text"
                                            className="input-field"
                                            value={categoryFormData.name}
                                            onChange={(e) => setCategoryFormData({ ...categoryFormData, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="cat_sort" className="block text-sm font-medium mb-2">
                                            Sort Order
                                        </label>
                                        <input
                                            id="cat_sort"
                                            type="number"
                                            className="input-field"
                                            value={categoryFormData.sort_order}
                                            onChange={(e) => setCategoryFormData({ ...categoryFormData, sort_order: parseInt(e.target.value) })}
                                            required
                                        />
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">Create</button>
                                    <button type="button" onClick={resetCategoryForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="grid grid-cols-4 gap-6">
                        {/* Category list */}
                        <div className="col-span-1">
                            <div className="bg-white rounded-lg shadow-md p-4">
                                <h3 className="font-bold mb-3">Categories</h3>
                                <div className="space-y-2">
                                    {categories.length === 0 ? (
                                        <p className="text-sm text-gray-500">No categories yet.</p>
                                    ) : (
                                        categories.map((cat) => (
                                            <button
                                                key={cat.category_id}
                                                onClick={() => selectCategory(cat)}
                                                className={`w-full text-left px-3 py-2 rounded text-sm ${selectedCategory?.category_id === cat.category_id
                                                    ? 'bg-blue-100 text-blue-800 font-medium'
                                                    : 'hover:bg-gray-100'
                                                    }`}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span>{cat.code}. {cat.name}</span>
                                                    <span className="text-xs bg-gray-200 px-1 rounded">{cat.change_types.length}</span>
                                                </div>
                                            </button>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Selected category change types */}
                        <div className="col-span-3">
                            {selectedCategory ? (
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <h3 className="text-xl font-bold">{selectedCategory.code}. {selectedCategory.name}</h3>
                                            <p className="text-sm text-gray-600 mt-1">
                                                Category for model change classification
                                            </p>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setShowChangeTypeForm(true)}
                                                className="btn-primary text-sm"
                                            >
                                                + Add Change Type
                                            </button>
                                            <button
                                                onClick={() => handleDeleteCategory(selectedCategory.category_id)}
                                                className="btn-secondary text-red-600 text-sm"
                                            >
                                                Delete Category
                                            </button>
                                        </div>
                                    </div>

                                    {showChangeTypeForm && (
                                        <div className="bg-gray-50 p-4 rounded mb-4">
                                            <h4 className="font-medium mb-3">
                                                {editingChangeType ? 'Edit Change Type' : 'Add New Change Type'}
                                            </h4>
                                            <form onSubmit={handleChangeTypeSubmit}>
                                                <div className="grid grid-cols-3 gap-4">
                                                    <div className="mb-3">
                                                        <label htmlFor="type_code" className="block text-sm font-medium mb-1">
                                                            Code
                                                        </label>
                                                        <input
                                                            id="type_code"
                                                            type="number"
                                                            className="input-field"
                                                            value={changeTypeFormData.code}
                                                            onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, code: parseInt(e.target.value) })}
                                                            required
                                                        />
                                                    </div>
                                                    <div className="mb-3 col-span-2">
                                                        <label htmlFor="type_name" className="block text-sm font-medium mb-1">
                                                            Name
                                                        </label>
                                                        <input
                                                            id="type_name"
                                                            type="text"
                                                            className="input-field"
                                                            value={changeTypeFormData.name}
                                                            onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, name: e.target.value })}
                                                            required
                                                        />
                                                    </div>
                                                </div>
                                                <div className="mb-3">
                                                    <label htmlFor="type_desc" className="block text-sm font-medium mb-1">
                                                        Description
                                                    </label>
                                                    <textarea
                                                        id="type_desc"
                                                        className="input-field"
                                                        rows={2}
                                                        value={changeTypeFormData.description}
                                                        onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, description: e.target.value })}
                                                    />
                                                </div>
                                                <div className="grid grid-cols-3 gap-4">
                                                    <div className="mb-3">
                                                        <label htmlFor="type_mv" className="block text-sm font-medium mb-1">
                                                            MV Activity
                                                        </label>
                                                        <select
                                                            id="type_mv"
                                                            className="input-field"
                                                            value={changeTypeFormData.mv_activity}
                                                            onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, mv_activity: e.target.value })}
                                                        >
                                                            <option value="">Not specified</option>
                                                            <option value="Approval">Approval</option>
                                                            <option value="Inform">Inform</option>
                                                            <option value="Not in scope to MV">Not in scope to MV</option>
                                                        </select>
                                                    </div>
                                                    <div className="mb-3">
                                                        <label htmlFor="type_sort" className="block text-sm font-medium mb-1">
                                                            Sort Order
                                                        </label>
                                                        <input
                                                            id="type_sort"
                                                            type="number"
                                                            className="input-field"
                                                            value={changeTypeFormData.sort_order}
                                                            onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, sort_order: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                    <div className="mb-3 flex items-center gap-4 mt-6">
                                                        <label className="flex items-center gap-2">
                                                            <input
                                                                type="checkbox"
                                                                checked={changeTypeFormData.requires_mv_approval}
                                                                onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, requires_mv_approval: e.target.checked })}
                                                            />
                                                            <span className="text-sm font-medium">Requires MV Approval</span>
                                                        </label>
                                                        <label className="flex items-center gap-2">
                                                            <input
                                                                type="checkbox"
                                                                checked={changeTypeFormData.is_active}
                                                                onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, is_active: e.target.checked })}
                                                            />
                                                            <span className="text-sm font-medium">Active</span>
                                                        </label>
                                                    </div>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button type="submit" className="btn-primary text-sm">
                                                        {editingChangeType ? 'Update' : 'Add'}
                                                    </button>
                                                    <button type="button" onClick={resetChangeTypeForm} className="btn-secondary text-sm">
                                                        Cancel
                                                    </button>
                                                </div>
                                            </form>
                                        </div>
                                    )}

                                    <div className="mt-4">
                                        <h4 className="font-medium mb-3">
                                            Change Types ({selectedCategory.change_types.length})
                                        </h4>
                                        {selectedCategory.change_types.length === 0 ? (
                                            <p className="text-gray-500 text-sm">No change types yet. Add change types to this category.</p>
                                        ) : (
                                            <div className="border rounded overflow-x-auto">
                                                <table className="min-w-full divide-y divide-gray-200">
                                                    <thead className="bg-gray-50">
                                                        <tr>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-16">
                                                                Code
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                Name
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-32">
                                                                MV Activity
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-32">
                                                                MV Approval
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-24">
                                                                Status
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-48">
                                                                Actions
                                                            </th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="bg-white divide-y divide-gray-200">
                                                        {selectedCategory.change_types
                                                            .sort((a, b) => a.sort_order - b.sort_order)
                                                            .map((type) => (
                                                                <tr key={type.change_type_id} className={`hover:bg-gray-50 ${!type.is_active ? 'opacity-60' : ''}`}>
                                                                    <td className="px-4 py-3 text-sm text-center font-mono">{type.code}</td>
                                                                    <td className="px-4 py-3 text-sm">
                                                                        <div>
                                                                            <div className="font-medium">{type.name}</div>
                                                                            {type.description && (
                                                                                <div className="text-xs text-gray-500 mt-0.5">{type.description}</div>
                                                                            )}
                                                                        </div>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-gray-600">
                                                                        {type.mv_activity || '-'}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm">
                                                                        {type.requires_mv_approval ? (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-orange-100 text-orange-800">
                                                                                Required
                                                                            </span>
                                                                        ) : (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                                                                                Not Required
                                                                            </span>
                                                                        )}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm">
                                                                        {type.is_active ? (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                                                                                Active
                                                                            </span>
                                                                        ) : (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-600">
                                                                                Inactive
                                                                            </span>
                                                                        )}
                                                                    </td>
                                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                                        <div className="flex items-center gap-2">
                                                                            <button
                                                                                onClick={() => handleEditChangeType(type)}
                                                                                className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 hover:bg-blue-200 rounded text-sm font-medium transition-colors"
                                                                            >
                                                                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                                                </svg>
                                                                                Edit
                                                                            </button>
                                                                            <button
                                                                                onClick={() => handleDeleteChangeType(type.change_type_id)}
                                                                                className="inline-flex items-center px-3 py-1 bg-red-100 text-red-700 hover:bg-red-200 rounded text-sm font-medium transition-colors"
                                                                            >
                                                                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                                </svg>
                                                                                Delete
                                                                            </button>
                                                                        </div>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-white rounded-lg shadow-md p-6 text-center text-gray-500">
                                    Select a category to view and manage its change types.
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </Layout>
    );
}

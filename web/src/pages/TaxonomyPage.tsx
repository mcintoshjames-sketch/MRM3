import { useState, useEffect } from 'react';
import api from '../api/client';
import Layout from '../components/Layout';

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

export default function TaxonomyPage() {
    const [taxonomies, setTaxonomies] = useState<Taxonomy[]>([]);
    const [loading, setLoading] = useState(true);
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

    useEffect(() => {
        fetchTaxonomies();
    }, []);

    const fetchTaxonomies = async () => {
        try {
            const response = await api.get('/taxonomies/');
            setTaxonomies(response.data);
            if (response.data.length > 0 && !selectedTaxonomy) {
                // Load the first taxonomy's details
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
                                        className={`w-full text-left px-3 py-2 rounded text-sm ${
                                            selectedTaxonomy?.taxonomy_id === tax.taxonomy_id
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
                                                    Code
                                                </label>
                                                <input
                                                    id="val_code"
                                                    type="text"
                                                    className="input-field"
                                                    value={valueFormData.code}
                                                    onChange={(e) => setValueFormData({ ...valueFormData, code: e.target.value })}
                                                    required
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
                                    <div className="border rounded overflow-hidden">
                                        <table className="min-w-full divide-y divide-gray-200 table-fixed">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-16">
                                                        Order
                                                    </th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-28">
                                                        Code
                                                    </th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                        Label
                                                    </th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                        Description
                                                    </th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-20">
                                                        Status
                                                    </th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-28">
                                                        Actions
                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white divide-y divide-gray-200">
                                                {selectedTaxonomy.values
                                                    .sort((a, b) => a.sort_order - b.sort_order)
                                                    .map((value) => (
                                                        <tr key={value.value_id}>
                                                            <td className="px-4 py-2 text-sm w-16">{value.sort_order}</td>
                                                            <td className="px-4 py-2 text-sm font-mono w-28">{value.code}</td>
                                                            <td className="px-4 py-2 text-sm font-medium">{value.label}</td>
                                                            <td className="px-4 py-2 text-sm text-gray-600 truncate">
                                                                {value.description || '-'}
                                                            </td>
                                                            <td className="px-4 py-2">
                                                                <span className={`px-2 py-1 text-xs rounded ${
                                                                    value.is_active
                                                                        ? 'bg-green-100 text-green-800'
                                                                        : 'bg-gray-100 text-gray-800'
                                                                }`}>
                                                                    {value.is_active ? 'Active' : 'Inactive'}
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-2">
                                                                <button
                                                                    onClick={() => handleEditValue(value)}
                                                                    className="text-blue-600 hover:text-blue-800 text-sm mr-2"
                                                                >
                                                                    Edit
                                                                </button>
                                                                <button
                                                                    onClick={() => handleDeleteValue(value.value_id)}
                                                                    className="text-red-600 hover:text-red-800 text-sm"
                                                                >
                                                                    Delete
                                                                </button>
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
        </Layout>
    );
}

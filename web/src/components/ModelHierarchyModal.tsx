import { useState, useEffect } from 'react';
import api from '../api/client';

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
}

interface Model {
    model_id: number;
    model_name: string;
}

interface HierarchyRelation {
    id: number;
    parent_model_id?: number;
    child_model_id?: number;
    relation_type_id: number;
    effective_date: string | null;
    end_date: string | null;
    notes: string | null;
}

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
    currentModelId: number;
    currentModelName: string;
    relationshipType: 'parent' | 'child';
    editData?: HierarchyRelation;
}

export default function ModelHierarchyModal({
    isOpen,
    onClose,
    onSuccess,
    currentModelId,
    currentModelName,
    relationshipType,
    editData
}: Props) {
    const [models, setModels] = useState<Model[]>([]);
    const [relationTypes, setRelationTypes] = useState<TaxonomyValue[]>([]);
    const [selectedModelId, setSelectedModelId] = useState<number | ''>('');
    const [relationTypeId, setRelationTypeId] = useState<number | ''>('');
    const [effectiveDate, setEffectiveDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [notes, setNotes] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        if (isOpen) {
            fetchData();
            if (editData) {
                setRelationTypeId(editData.relation_type_id);
                setEffectiveDate(editData.effective_date || '');
                setEndDate(editData.end_date || '');
                setNotes(editData.notes || '');
                // For edit mode, we don't change the model selection
                if (relationshipType === 'parent') {
                    setSelectedModelId(editData.parent_model_id || '');
                } else {
                    setSelectedModelId(editData.child_model_id || '');
                }
            } else {
                resetForm();
            }
        }
    }, [isOpen, editData]);

    const fetchData = async () => {
        try {
            const [modelsRes, taxonomiesRes] = await Promise.all([
                api.get('/models'),
                api.get('/taxonomies')
            ]);

            // Filter out current model from selection
            const availableModels = modelsRes.data.filter(
                (m: Model) => m.model_id !== currentModelId
            );
            setModels(availableModels);

            // Find Model Hierarchy Type taxonomy
            const hierarchyTypeTaxonomy = taxonomiesRes.data.find(
                (t: any) => t.name === 'Model Hierarchy Type'
            );
            if (hierarchyTypeTaxonomy) {
                const valuesRes = await api.get(`/taxonomies/${hierarchyTypeTaxonomy.taxonomy_id}/values`);
                setRelationTypes(valuesRes.data);
                // Auto-select SUB_MODEL if available and not editing
                if (!editData && valuesRes.data.length > 0) {
                    const subModelType = valuesRes.data.find((v: TaxonomyValue) => v.code === 'SUB_MODEL');
                    if (subModelType) {
                        setRelationTypeId(subModelType.value_id);
                    }
                }
            }
        } catch (error) {
            console.error('Error fetching data:', error);
            setError('Failed to load form data');
        }
    };

    const resetForm = () => {
        setSelectedModelId('');
        setRelationTypeId('');
        setEffectiveDate('');
        setEndDate('');
        setNotes('');
        setError('');
        setSearchTerm('');
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // Validate model selection for new relationships
        if (!editData && !selectedModelId) {
            setError(`Please select a ${relationshipType === 'parent' ? 'parent model' : 'sub-model'}`);
            return;
        }

        // Validate relationship type
        if (!relationTypeId) {
            setError('Please select a relationship type');
            return;
        }

        setLoading(true);

        try {
            if (editData) {
                // Update existing relationship
                await api.patch(`/hierarchy/${editData.id}`, {
                    relation_type_id: relationTypeId || undefined,
                    effective_date: effectiveDate || null,
                    end_date: endDate || null,
                    notes: notes || null
                });
            } else {
                // Create new relationship
                const payload: any = {
                    relation_type_id: relationTypeId,
                    effective_date: effectiveDate || null,
                    end_date: endDate || null,
                    notes: notes || null
                };

                if (relationshipType === 'parent') {
                    // Current model is child, selected is parent
                    payload.child_model_id = currentModelId;
                    await api.post(`/models/${selectedModelId}/hierarchy`, payload);
                } else {
                    // Current model is parent, selected is child
                    payload.child_model_id = selectedModelId;
                    await api.post(`/models/${currentModelId}/hierarchy`, payload);
                }
            }

            onSuccess();
            onClose();
            resetForm();
        } catch (error: any) {
            console.error('Error saving hierarchy:', error);
            setError(error.response?.data?.detail || 'Failed to save hierarchy relationship');
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        if (!loading) {
            resetForm();
            onClose();
        }
    };

    if (!isOpen) return null;

    const filteredModels = models.filter(m =>
        m.model_name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-medium text-gray-900">
                        {editData ? 'Edit' : 'Add'} {relationshipType === 'parent' ? 'Parent' : 'Sub-Model'} Relationship
                    </h3>
                    <button
                        onClick={handleClose}
                        disabled={loading}
                        className="text-gray-400 hover:text-gray-500"
                    >
                        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {error && (
                    <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Current Model
                        </label>
                        <input
                            type="text"
                            value={currentModelName}
                            disabled
                            className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                        />
                    </div>

                    {!editData && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Select {relationshipType === 'parent' ? 'Parent' : 'Sub-Model'} *
                            </label>
                            <input
                                type="text"
                                placeholder="Type to search models..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                            <div className="border border-gray-300 rounded-md max-h-64 overflow-y-auto">
                                {filteredModels.length === 0 ? (
                                    <div className="px-3 py-2 text-gray-500 text-sm">
                                        {searchTerm ? 'No models found matching your search' : 'Start typing to search...'}
                                    </div>
                                ) : (
                                    filteredModels.map((model) => (
                                        <div
                                            key={model.model_id}
                                            onClick={() => setSelectedModelId(model.model_id)}
                                            className={`px-3 py-2 cursor-pointer hover:bg-blue-50 ${selectedModelId === model.model_id ? 'bg-blue-100 font-medium' : ''
                                                }`}
                                        >
                                            {model.model_name}
                                        </div>
                                    ))
                                )}
                            </div>
                            {selectedModelId && (
                                <div className="mt-2 text-sm text-gray-600">
                                    Selected: <span className="font-medium">{models.find(m => m.model_id === selectedModelId)?.model_name}</span>
                                </div>
                            )}
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Relationship Type *
                        </label>
                        <select
                            value={relationTypeId}
                            onChange={(e) => setRelationTypeId(Number(e.target.value))}
                            required
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="">-- Select type --</option>
                            {relationTypes.map((type) => (
                                <option key={type.value_id} value={type.value_id}>
                                    {type.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Effective Date
                            </label>
                            <input
                                type="date"
                                value={effectiveDate}
                                onChange={(e) => setEffectiveDate(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                End Date
                            </label>
                            <input
                                type="date"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                min={effectiveDate || undefined}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Notes
                        </label>
                        <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            rows={3}
                            maxLength={500}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            placeholder="Optional notes about this relationship"
                        />
                        <p className="mt-1 text-sm text-gray-500">{notes.length}/500 characters</p>
                    </div>

                    <div className="flex justify-end space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={handleClose}
                            disabled={loading}
                            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                        >
                            {loading ? 'Saving...' : editData ? 'Update' : 'Create'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

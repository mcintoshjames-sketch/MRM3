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

interface DependencyRelation {
    id: number;
    feeder_model_id?: number;
    consumer_model_id?: number;
    dependency_type_id: number;
    description: string | null;
    effective_date: string | null;
    end_date: string | null;
    is_active: boolean;
}

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
    currentModelId: number;
    currentModelName: string;
    dependencyDirection: 'inbound' | 'outbound';
    editData?: DependencyRelation;
}

export default function ModelDependencyModal({
    isOpen,
    onClose,
    onSuccess,
    currentModelId,
    currentModelName,
    dependencyDirection,
    editData
}: Props) {
    const [models, setModels] = useState<Model[]>([]);
    const [dependencyTypes, setDependencyTypes] = useState<TaxonomyValue[]>([]);
    const [selectedModelId, setSelectedModelId] = useState<number | ''>('');
    const [dependencyTypeId, setDependencyTypeId] = useState<number | ''>('');
    const [description, setDescription] = useState('');
    const [effectiveDate, setEffectiveDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [isActive, setIsActive] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        if (isOpen) {
            setError(''); // Clear any previous errors
            fetchData();
            if (editData) {
                setDependencyTypeId(editData.dependency_type_id);
                setDescription(editData.description || '');
                setEffectiveDate(editData.effective_date || '');
                setEndDate(editData.end_date || '');
                setIsActive(editData.is_active);
                // For edit mode, we don't change the model selection
                if (dependencyDirection === 'inbound') {
                    setSelectedModelId(editData.feeder_model_id || '');
                } else {
                    setSelectedModelId(editData.consumer_model_id || '');
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

            // Find Model Dependency Type taxonomy
            const dependencyTypeTaxonomy = taxonomiesRes.data.find(
                (t: any) => t.name === 'Model Dependency Type'
            );
            if (dependencyTypeTaxonomy) {
                const valuesRes = await api.get(`/taxonomies/${dependencyTypeTaxonomy.taxonomy_id}/values`);
                setDependencyTypes(valuesRes.data);
            }
        } catch (error) {
            console.error('Error fetching data:', error);
            // Only show error if we're in create mode and can't load models
            if (!editData) {
                setError('Failed to load form data. Please try again.');
            }
        }
    };

    const resetForm = () => {
        setSelectedModelId('');
        setDependencyTypeId('');
        setDescription('');
        setEffectiveDate('');
        setEndDate('');
        setIsActive(true);
        setError('');
        setSearchTerm('');
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // Validate model selection for new dependencies
        if (!editData && !selectedModelId) {
            setError(`Please select a ${dependencyDirection === 'inbound' ? 'feeder model' : 'consumer model'}`);
            return;
        }

        // Validate dependency type
        if (!dependencyTypeId) {
            setError('Please select a dependency type');
            return;
        }

        setLoading(true);

        try {
            if (editData) {
                // Update existing dependency
                await api.patch(`/dependencies/${editData.id}`, {
                    dependency_type_id: dependencyTypeId || undefined,
                    description: description || null,
                    effective_date: effectiveDate || null,
                    end_date: endDate || null,
                    is_active: isActive
                });
            } else {
                // Create new dependency
                const payload: any = {
                    dependency_type_id: dependencyTypeId,
                    description: description || null,
                    effective_date: effectiveDate || null,
                    end_date: endDate || null,
                    is_active: isActive
                };

                if (dependencyDirection === 'inbound') {
                    // Current model is consumer, selected is feeder
                    payload.consumer_model_id = currentModelId;
                    await api.post(`/models/${selectedModelId}/dependencies`, payload);
                } else {
                    // Current model is feeder, selected is consumer
                    payload.consumer_model_id = selectedModelId;
                    await api.post(`/models/${currentModelId}/dependencies`, payload);
                }
            }

            onSuccess();
            onClose();
            resetForm();
        } catch (error: any) {
            console.error('Error saving dependency:', error);
            // Check for cycle detection error
            if (error.response?.status === 400 && error.response?.data?.detail?.includes('cycle')) {
                setError('Cannot create dependency: ' + error.response.data.detail);
            } else {
                setError(error.response?.data?.detail || 'Failed to save dependency relationship');
            }
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
                        {editData ? 'Edit' : 'Add'} {dependencyDirection === 'inbound' ? 'Inbound' : 'Outbound'} Dependency
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
                    <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
                        <div className="flex">
                            <svg className="h-5 w-5 text-red-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                            <span className="text-sm">{error}</span>
                        </div>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Current Model ({dependencyDirection === 'inbound' ? 'Consumer' : 'Feeder'})
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
                                Select {dependencyDirection === 'inbound' ? 'Feeder Model' : 'Consumer Model'} *
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
                            Dependency Type *
                        </label>
                        <select
                            value={dependencyTypeId}
                            onChange={(e) => setDependencyTypeId(Number(e.target.value))}
                            required
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="">-- Select type --</option>
                            {dependencyTypes.map((type) => (
                                <option key={type.value_id} value={type.value_id}>
                                    {type.label}
                                </option>
                            ))}
                        </select>
                        <p className="mt-1 text-xs text-gray-500">
                            INPUT_DATA: Raw data feed • SCORE: Model output • PARAMETER: Configuration • GOVERNANCE_SIGNAL: Oversight signal
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3}
                            maxLength={500}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            placeholder="Brief description of this dependency (e.g., 'Provides daily market rates for pricing calculations')"
                        />
                        <p className="mt-1 text-sm text-gray-500">{description.length}/500 characters</p>
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

                    <div className="flex items-center">
                        <input
                            type="checkbox"
                            id="isActive"
                            checked={isActive}
                            onChange={(e) => setIsActive(e.target.checked)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <label htmlFor="isActive" className="ml-2 block text-sm text-gray-900">
                            Active dependency
                        </label>
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

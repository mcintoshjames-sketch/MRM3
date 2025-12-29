import React, { useEffect, useMemo, useState } from 'react';
import api from '../api/client';
import VersionSelector, { ModelVersion } from './VersionSelector';
import {
    validationWorkflowApi,
    ModelVersionEntry,
    ValidationRequestModelUpdateResponse,
    ValidationWarning
} from '../api/validationWorkflow';

interface ModelSummary {
    model_id: number;
    model_name: string;
    status: string;
}

interface ValidationTypeSummary {
    code: string;
    label: string;
}

interface ValidationRequestSummary {
    request_id: number;
    models: ModelSummary[];
    validation_type: ValidationTypeSummary;
}

interface ManageModelsModalProps {
    request: ValidationRequestSummary;
    isOpen: boolean;
    onClose: () => void;
    onSave: (response: ValidationRequestModelUpdateResponse) => void;
}

interface AddEntry {
    model_id: number;
    version_id?: number | null;
    version_number?: string | null;
}

interface ModelListItem {
    model_id: number;
    model_name: string;
    status: string;
}

const getPrimaryModelId = (models: ModelSummary[]): number | null => {
    if (!models.length) return null;
    return models.reduce((min, model) => (model.model_id < min ? model.model_id : min), models[0].model_id);
};

const ManageModelsModal: React.FC<ManageModelsModalProps> = ({ request, isOpen, onClose, onSave }) => {
    const [modelsToRemove, setModelsToRemove] = useState<number[]>([]);
    const [modelsToAdd, setModelsToAdd] = useState<AddEntry[]>([]);
    const [modelSearchQuery, setModelSearchQuery] = useState('');
    const [showModelDropdown, setShowModelDropdown] = useState(false);
    const [availableModels, setAvailableModels] = useState<ModelListItem[]>([]);
    const [selectedModelForVersion, setSelectedModelForVersion] = useState<ModelListItem | null>(null);
    const [allowUnassignConflicts, setAllowUnassignConflicts] = useState(false);
    const [loadingModels, setLoadingModels] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [warningDetails, setWarningDetails] = useState<string[]>([]);
    const [conflictValidators, setConflictValidators] = useState<string[]>([]);

    const isChangeType = request.validation_type?.code === 'CHANGE';
    const primaryModelId = getPrimaryModelId(request.models);
    const hasChanges = modelsToAdd.length > 0 || modelsToRemove.length > 0;

    useEffect(() => {
        if (!isOpen) return;
        setModelsToRemove([]);
        setModelsToAdd([]);
        setModelSearchQuery('');
        setShowModelDropdown(false);
        setSelectedModelForVersion(null);
        setAllowUnassignConflicts(false);
        setError(null);
        setWarningDetails([]);
        setConflictValidators([]);

        const fetchModels = async () => {
            setLoadingModels(true);
            try {
                const response = await api.get('/models/?limit=500');
                setAvailableModels(response.data || []);
            } catch (err) {
                console.error('Failed to load models:', err);
                setError('Failed to load models');
            } finally {
                setLoadingModels(false);
            }
        };

        fetchModels();
    }, [isOpen]);

    const excludedIds = useMemo(() => {
        const ids = new Set<number>([
            ...request.models.map((model) => model.model_id),
            ...modelsToAdd.map((entry) => entry.model_id)
        ]);
        if (selectedModelForVersion) {
            ids.add(selectedModelForVersion.model_id);
        }
        return ids;
    }, [request.models, modelsToAdd, selectedModelForVersion]);

    const modelLookup = useMemo(() => {
        const combined = [...availableModels, ...request.models];
        return new Map(combined.map((model) => [model.model_id, model]));
    }, [availableModels, request.models]);

    const filteredModels = useMemo(() => {
        if (!modelSearchQuery.trim()) return [];
        const normalizedSearch = modelSearchQuery.toLowerCase();
        return availableModels.filter((model) => {
            if (excludedIds.has(model.model_id)) return false;
            return (
                model.model_name.toLowerCase().includes(normalizedSearch) ||
                String(model.model_id).includes(normalizedSearch)
            );
        }).slice(0, 50);
    }, [availableModels, excludedIds, modelSearchQuery]);

    if (!isOpen) return null;

    const toggleRemove = (modelId: number) => {
        setModelsToRemove((prev) => (
            prev.includes(modelId) ? prev.filter((id) => id !== modelId) : [...prev, modelId]
        ));
    };

    const handleSelectModel = (model: ModelListItem) => {
        if (isChangeType) {
            setSelectedModelForVersion(model);
            setModelSearchQuery(model.model_name);
            setShowModelDropdown(false);
            return;
        }

        setModelsToAdd((prev) => [...prev, { model_id: model.model_id }]);
        setModelSearchQuery('');
        setShowModelDropdown(false);
    };

    const handleVersionSelect = (version: ModelVersion) => {
        if (!selectedModelForVersion) return;
        setModelsToAdd((prev) => [
            ...prev,
            {
                model_id: selectedModelForVersion.model_id,
                version_id: version.version_id,
                version_number: version.version_number
            }
        ]);
        setSelectedModelForVersion(null);
        setModelSearchQuery('');
    };

    const removeFromAdd = (modelId: number) => {
        setModelsToAdd((prev) => prev.filter((entry) => entry.model_id !== modelId));
    };

    const submitUpdate = async (forceUnassign: boolean = false) => {
        setError(null);
        setWarningDetails([]);
        setConflictValidators([]);

        if (!hasChanges) {
            setError('Select at least one model to add or remove.');
            return;
        }

        if (selectedModelForVersion) {
            setError(`Select a version for ${selectedModelForVersion.model_name}.`);
            return;
        }

        if (isChangeType && modelsToAdd.some((entry) => !entry.version_id)) {
            setError('CHANGE validations require selecting a version for each added model.');
            return;
        }

        setSaving(true);
        try {
            const payload: ModelVersionEntry[] = modelsToAdd.map((entry) => ({
                model_id: entry.model_id,
                version_id: entry.version_id ?? undefined
            }));
            const response = await validationWorkflowApi.updateRequestModels(
                request.request_id,
                {
                    add_models: payload.length ? payload : undefined,
                    remove_model_ids: modelsToRemove.length ? modelsToRemove : undefined,
                    allow_unassign_conflicts: forceUnassign || allowUnassignConflicts
                }
            );
            onSave(response);
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            if (err.response?.status === 409 && detail?.conflicting_validators) {
                setError(detail.message || 'Validator independence violation');
                setConflictValidators(detail.conflicting_validators || []);
                return;
            }

            if (typeof detail === 'string') {
                setError(detail);
            } else if (detail?.message) {
                setError(detail.message);
                if (detail.warnings) {
                    const warningMessages = (detail.warnings as ValidationWarning[]).map(
                        (warning) => warning.message
                    );
                    setWarningDetails(warningMessages);
                }
            } else {
                setError('Failed to update models');
            }
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">Manage Models</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 text-2xl"
                        aria-label="Close"
                    >
                        &times;
                    </button>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded">
                        {error}
                    </div>
                )}

                {warningDetails.length > 0 && (
                    <div className="mb-4 p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded text-sm">
                        <div className="font-medium mb-1">Warnings</div>
                        <ul className="list-disc ml-5 space-y-1">
                            {warningDetails.map((warning, index) => (
                                <li key={`${warning}-${index}`}>{warning}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {conflictValidators.length > 0 && (
                    <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded">
                        <div className="text-sm text-amber-800 font-medium mb-2">
                            Validator independence conflict
                        </div>
                        <p className="text-sm text-amber-700">
                            Conflicting validators: {conflictValidators.join(', ')}
                        </p>
                        <button
                            onClick={() => {
                                setAllowUnassignConflicts(true);
                                submitUpdate(true);
                            }}
                            className="mt-3 bg-amber-600 text-white px-3 py-1 rounded hover:bg-amber-700 text-sm"
                            disabled={saving}
                        >
                            Unassign and Continue
                        </button>
                    </div>
                )}

                <div className="space-y-5">
                    <div>
                        <h3 className="text-sm font-semibold text-gray-700 mb-2">Current Models</h3>
                        <div className="space-y-2">
                            {request.models.map((model) => {
                                const remainingAfterRemove = request.models.length - (modelsToRemove.length + 1) + modelsToAdd.length;
                                const disableRemove = remainingAfterRemove < 1 && !modelsToRemove.includes(model.model_id);
                                return (
                                    <label key={model.model_id} className="flex items-center gap-2 text-sm">
                                        <input
                                            type="checkbox"
                                            checked={modelsToRemove.includes(model.model_id)}
                                            onChange={() => toggleRemove(model.model_id)}
                                            disabled={disableRemove}
                                        />
                                        <span className="font-medium text-gray-700">{model.model_name}</span>
                                        <span className="text-xs text-gray-500">({model.status})</span>
                                        {model.model_id === primaryModelId && (
                                            <span className="text-xs text-gray-500">(Primary)</span>
                                        )}
                                    </label>
                                );
                            })}
                        </div>
                    </div>

                    <div>
                        <h3 className="text-sm font-semibold text-gray-700 mb-2">Add Models</h3>
                        <div className="relative">
                            <input
                                type="text"
                                placeholder="Type to search by name or ID..."
                                value={modelSearchQuery}
                                onChange={(e) => {
                                    setModelSearchQuery(e.target.value);
                                    setShowModelDropdown(true);
                                }}
                                onFocus={() => setShowModelDropdown(true)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                            {showModelDropdown && modelSearchQuery.trim().length > 0 && (
                                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                    {loadingModels && (
                                        <div className="px-4 py-2 text-sm text-gray-500">Loading models...</div>
                                    )}
                                    {!loadingModels && filteredModels.length > 0 && filteredModels.map((model) => (
                                        <div
                                            key={model.model_id}
                                            className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                            onClick={() => handleSelectModel(model)}
                                        >
                                            <div className="font-medium text-gray-800">{model.model_name}</div>
                                            <div className="text-xs text-gray-500">ID: {model.model_id}</div>
                                        </div>
                                    ))}
                                    {!loadingModels && filteredModels.length === 0 && (
                                        <div className="px-4 py-2 text-sm text-gray-500">No models found</div>
                                    )}
                                </div>
                            )}
                        </div>

                        {selectedModelForVersion && (
                            <div className="mt-3">
                                <div className="flex items-center justify-between text-sm text-gray-700">
                                    <span>Select a DRAFT version for {selectedModelForVersion.model_name}</span>
                                    <button
                                        type="button"
                                        onClick={() => setSelectedModelForVersion(null)}
                                        className="text-xs text-blue-600 hover:text-blue-800"
                                    >
                                        Choose different model
                                    </button>
                                </div>
                                <VersionSelector
                                    modelId={selectedModelForVersion.model_id}
                                    filterStatus="DRAFT"
                                    onSelect={handleVersionSelect}
                                />
                            </div>
                        )}

                        {modelsToAdd.length > 0 && (
                            <div className="mt-3 space-y-2">
                                {modelsToAdd.map((entry) => {
                                    const model = modelLookup.get(entry.model_id);
                                    return (
                                        <div key={entry.model_id} className="flex items-center justify-between text-sm bg-gray-50 border border-gray-200 rounded p-2">
                                            <div>
                                                <span className="font-medium text-gray-800">
                                                    {model?.model_name || `Model ${entry.model_id}`}
                                                </span>
                                                {entry.version_number && (
                                                    <span className="ml-2 text-xs text-gray-500">
                                                        Version {entry.version_number}
                                                    </span>
                                                )}
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => removeFromAdd(entry.model_id)}
                                                className="text-gray-400 hover:text-gray-700"
                                            >
                                                ×
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {hasChanges && (
                        <div className="bg-yellow-50 border border-yellow-200 p-3 rounded text-sm text-yellow-900">
                            <div className="font-medium mb-1">This change may affect:</div>
                            <ul className="list-disc ml-5 space-y-1">
                                <li>Lead time calculation</li>
                                <li>Approval requirements (regional)</li>
                                <li>Validation plan expectations</li>
                                <li>Validator assignments (independence check)</li>
                            </ul>
                        </div>
                    )}

                    <label className="text-sm flex items-center gap-2">
                        <input
                            type="checkbox"
                            checked={allowUnassignConflicts}
                            onChange={(e) => setAllowUnassignConflicts(e.target.checked)}
                        />
                        Allow unassigning conflicting validators if needed
                    </label>
                </div>

                <div className="mt-6 flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                        disabled={saving}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => submitUpdate(false)}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                        disabled={saving || !hasChanges}
                    >
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ManageModelsModal;

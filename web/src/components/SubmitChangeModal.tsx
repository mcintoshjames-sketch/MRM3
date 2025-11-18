import React, { useState, useEffect } from 'react';
import { versionsApi, ChangeType } from '../api/versions';
import { changeTaxonomyApi, ModelChangeCategory, ModelChangeType } from '../api/changeTaxonomy';

interface SubmitChangeModalProps {
    modelId: number;
    onClose: () => void;
    onSuccess: () => void;
}

const SubmitChangeModal: React.FC<SubmitChangeModalProps> = ({ modelId, onClose, onSuccess }) => {
    const [versioningMode, setVersioningMode] = useState<'auto' | 'manual'>('auto');
    const [formData, setFormData] = useState({
        version_number: '',
        change_type: 'MINOR' as ChangeType,
        change_type_id: null as number | null,
        change_description: '',
        production_date: '',
    });
    const [categories, setCategories] = useState<ModelChangeCategory[]>([]);
    const [selectedChangeType, setSelectedChangeType] = useState<ModelChangeType | null>(null);
    const [nextVersionPreview, setNextVersionPreview] = useState<string>('');
    const [overrideVersion, setOverrideVersion] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [validationAcknowledgment, setValidationAcknowledgment] = useState<{
        created: boolean;
        type: string;
        warning?: string;
        request_id?: number;
    } | null>(null);

    // Fetch taxonomy data on mount
    useEffect(() => {
        const fetchTaxonomy = async () => {
            try {
                const data = await changeTaxonomyApi.getCategories();
                setCategories(data);
            } catch (err) {
                console.error('Failed to fetch change taxonomy:', err);
            }
        };
        fetchTaxonomy();
    }, []);

    // Fetch preview when change type changes in auto mode
    useEffect(() => {
        if (versioningMode === 'auto') {
            fetchNextVersion();
        }
    }, [formData.change_type, versioningMode]);

    const fetchNextVersion = async () => {
        try {
            const preview = await versionsApi.getNextVersionPreview(modelId, formData.change_type);
            setNextVersionPreview(preview.next_version);
        } catch (err) {
            console.error('Failed to fetch version preview:', err);
            setNextVersionPreview('1.0');
        }
    };

    const handleChangeTypeSelect = (changeTypeId: string) => {
        if (!changeTypeId) {
            setSelectedChangeType(null);
            setFormData({
                ...formData,
                change_type_id: null,
                change_type: 'MINOR',
            });
            return;
        }

        const typeId = parseInt(changeTypeId);

        // Find the selected change type
        let selectedType: ModelChangeType | null = null;
        for (const category of categories) {
            const found = category.change_types.find(t => t.change_type_id === typeId);
            if (found) {
                selectedType = found;
                break;
            }
        }

        if (selectedType) {
            setSelectedChangeType(selectedType);
            // Map to MINOR/MAJOR based on requires_mv_approval
            const changeType: ChangeType = selectedType.requires_mv_approval ? 'MAJOR' : 'MINOR';
            setFormData({
                ...formData,
                change_type_id: typeId,
                change_type: changeType,
            });
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setValidationAcknowledgment(null);
        setLoading(true);

        try {
            let versionNumber: string | null = null;

            if (versioningMode === 'manual') {
                versionNumber = formData.version_number;
            } else {
                // Auto mode - use override if provided, otherwise null (backend will generate)
                versionNumber = overrideVersion || null;
            }

            const response = await versionsApi.createVersion(modelId, {
                version_number: versionNumber,
                change_type: formData.change_type,
                change_type_id: formData.change_type_id,
                change_description: formData.change_description,
                production_date: formData.production_date || null,
            });

            // Check if validation request was created
            if (response.validation_request_created) {
                setValidationAcknowledgment({
                    created: true,
                    type: response.validation_type || 'TARGETED',
                    warning: response.validation_warning || undefined,
                    request_id: response.validation_request_id || undefined
                });
            } else {
                // No validation required, close immediately
                onSuccess();
                onClose();
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit change');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold">Submit Model Change</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 text-2xl"
                    >
                        ✕
                    </button>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                        {error}
                    </div>
                )}

                {validationAcknowledgment && (
                    <div className="mb-4 p-4 bg-blue-100 border border-blue-400 text-blue-900 rounded">
                        <h3 className="font-bold text-lg mb-2">✓ Model Change Submitted Successfully</h3>
                        <p className="mb-3">
                            Your model change has been submitted to Model Validation for review and approval.
                        </p>
                        <div className="bg-white p-3 rounded border border-blue-200 mb-3">
                            <div className="grid grid-cols-2 gap-2 text-sm">
                                <div>
                                    <span className="font-medium">Validation Type:</span> {validationAcknowledgment.type === 'INTERIM' ? 'Interim Model Change Review' : 'Targeted Review'}
                                </div>
                                {validationAcknowledgment.request_id && (
                                    <div>
                                        <span className="font-medium">Request ID:</span> #{validationAcknowledgment.request_id}
                                    </div>
                                )}
                            </div>
                        </div>
                        {validationAcknowledgment.warning && (
                            <div className="p-3 bg-yellow-50 border border-yellow-300 rounded text-yellow-900 text-sm mb-3">
                                <strong>⚠ Warning:</strong> {validationAcknowledgment.warning}
                            </div>
                        )}
                        <p className="text-sm mb-3">
                            The validation request is now pending assignment to a validator. You will be notified when the validation is complete.
                        </p>
                        <button
                            onClick={() => {
                                onSuccess();
                                onClose();
                            }}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 w-full"
                        >
                            Close
                        </button>
                    </div>
                )}

                <form onSubmit={handleSubmit} style={{ display: validationAcknowledgment ? 'none' : 'block' }}>
                    {/* Version Numbering Mode */}
                    <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <label className="block text-sm font-medium text-gray-700 mb-3">
                            Version Numbering
                        </label>
                        <div className="space-y-2">
                            <label className="flex items-center cursor-pointer">
                                <input
                                    type="radio"
                                    name="versioningMode"
                                    value="auto"
                                    checked={versioningMode === 'auto'}
                                    onChange={(e) => setVersioningMode(e.target.value as 'auto' | 'manual')}
                                    className="mr-2"
                                />
                                <span className="text-sm">Auto-generate version number</span>
                            </label>
                            <label className="flex items-center cursor-pointer">
                                <input
                                    type="radio"
                                    name="versioningMode"
                                    value="manual"
                                    checked={versioningMode === 'manual'}
                                    onChange={(e) => setVersioningMode(e.target.value as 'auto' | 'manual')}
                                    className="mr-2"
                                />
                                <span className="text-sm">Specify version number manually</span>
                            </label>
                        </div>
                    </div>

                    {/* Change Type - Hierarchical Taxonomy */}
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Change Type *
                        </label>
                        <select
                            value={formData.change_type_id || ''}
                            onChange={(e) => handleChangeTypeSelect(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            required
                        >
                            <option value="">Select a change type...</option>
                            {categories.map(category => {
                                // Filter out "New Model Development" (code 1) - only for initial model creation
                                const filteredTypes = category.change_types.filter(type => type.code !== 1);

                                // Only show category if it has types after filtering
                                if (filteredTypes.length === 0) return null;

                                return (
                                    <optgroup key={category.category_id} label={`${category.code}. ${category.name}`}>
                                        {filteredTypes.map(type => (
                                            <option key={type.change_type_id} value={type.change_type_id}>
                                                {type.code}. {type.name} {type.requires_mv_approval ? '(MV Approval Required)' : ''}
                                            </option>
                                        ))}
                                    </optgroup>
                                );
                            })}
                        </select>
                        {selectedChangeType && (
                            <div className="mt-2 space-y-1">
                                {/* Description */}
                                {selectedChangeType.description && (
                                    <p className="text-sm text-gray-700 bg-gray-50 p-2 rounded border border-gray-200">
                                        {selectedChangeType.description}
                                    </p>
                                )}
                                {/* MV Activity and Approval Requirements */}
                                <div className="flex items-center gap-3">
                                    {selectedChangeType.mv_activity && (
                                        <span className="text-xs text-gray-600">
                                            <strong>MV Activity:</strong> {selectedChangeType.mv_activity}
                                        </span>
                                    )}
                                    {formData.change_type === 'MAJOR' ? (
                                        <span className="text-xs text-orange-600 font-medium">⚠ Requires validation approval before activation</span>
                                    ) : (
                                        <span className="text-xs text-green-600">✓ No validation required</span>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Version Number Fields */}
                    {versioningMode === 'auto' ? (
                        <>
                            <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium text-gray-700">Next Version:</span>
                                    <span className="text-lg font-bold text-blue-600">{nextVersionPreview}</span>
                                </div>
                                <p className="text-xs text-gray-600">
                                    Based on {formData.change_type} change type
                                </p>
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Override Version Number (Optional)
                                </label>
                                <input
                                    type="text"
                                    value={overrideVersion}
                                    onChange={(e) => setOverrideVersion(e.target.value)}
                                    placeholder={`Leave empty to use ${nextVersionPreview}`}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    maxLength={50}
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Only provide if you want to override the auto-generated version
                                </p>
                            </div>
                        </>
                    ) : (
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Version Number *
                            </label>
                            <input
                                type="text"
                                value={formData.version_number}
                                onChange={(e) => setFormData({ ...formData, version_number: e.target.value })}
                                placeholder="e.g., 1.1, v2.0, 2024.Q1"
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                required
                                maxLength={50}
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Free text - you can use any versioning scheme
                            </p>
                        </div>
                    )}

                    {/* Change Description */}
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Change Description *
                        </label>
                        <textarea
                            value={formData.change_description}
                            onChange={(e) => setFormData({ ...formData, change_description: e.target.value })}
                            placeholder="Describe the changes in this version..."
                            rows={4}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            required
                        />
                    </div>

                    {/* Production Date */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Production Date (Optional)
                        </label>
                        <input
                            type="date"
                            value={formData.production_date}
                            onChange={(e) => setFormData({ ...formData, production_date: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            When this version was/will be deployed to production
                        </p>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                            disabled={loading}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                            disabled={loading}
                        >
                            {loading ? 'Submitting...' : 'Submit Change'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default SubmitChangeModal;

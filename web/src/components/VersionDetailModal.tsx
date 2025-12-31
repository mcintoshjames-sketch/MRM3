import React, { useState, useEffect } from 'react';
import { versionsApi, ModelVersion, ChangeType } from '../api/versions';
import { changeTaxonomyApi, ModelChangeCategory } from '../api/changeTaxonomy';
import { useAuth } from '../contexts/AuthContext';
import { isAdminOrValidator } from '../utils/roleUtils';

interface VersionDetailModalProps {
    version: ModelVersion;
    onClose: () => void;
    onSuccess: () => void;
}

const VersionDetailModal: React.FC<VersionDetailModalProps> = ({ version, onClose, onSuccess }) => {
    const { user } = useAuth();
    const [editMode, setEditMode] = useState(false);
    const [categories, setCategories] = useState<ModelChangeCategory[]>([]);
    const [formData, setFormData] = useState({
        version_number: version.version_number,
        change_type: version.change_type,
        change_type_id: version.change_type_id,
        change_description: version.change_description,
        production_date: version.production_date || '',
    });
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    // Determine if user can edit
    const canEdit = () => {
        // Only DRAFT versions can be edited
        if (version.status !== 'DRAFT') return false;

        // If validation has begun, only validators/admins can edit
        if (version.validation_request_id) {
            return isAdminOrValidator(user);
        }

        // Otherwise, assume owner/developer/delegates can edit (backend will verify)
        return true;
    };

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

    const handleSave = async () => {
        setError(null);
        setLoading(true);

        try {
            await versionsApi.updateVersion(version.version_id, {
                version_number: formData.version_number,
                change_type: formData.change_type,
                change_type_id: formData.change_type_id,
                change_description: formData.change_description,
                production_date: formData.production_date || null,
            });
            onSuccess();
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update version');
        } finally {
            setLoading(false);
        }
    };

    const getStatusBadge = (status: string) => {
        const colors = {
            DRAFT: 'bg-gray-200 text-gray-800',
            IN_VALIDATION: 'bg-blue-200 text-blue-800',
            APPROVED: 'bg-green-200 text-green-800',
            ACTIVE: 'bg-green-600 text-white',
            SUPERSEDED: 'bg-gray-400 text-gray-700',
        };
        return (
            <span className={`px-3 py-1 rounded text-sm font-semibold ${colors[status as keyof typeof colors]}`}>
                {status}
            </span>
        );
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold">Version Details</h2>
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

                <div className="space-y-4">
                    {/* Version Number */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Version Number
                        </label>
                        {editMode ? (
                            <input
                                type="text"
                                value={formData.version_number}
                                onChange={(e) => setFormData({ ...formData, version_number: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                maxLength={50}
                            />
                        ) : (
                            <p className="text-lg font-semibold">{version.version_number}</p>
                        )}
                    </div>

                    {/* Status */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Status
                        </label>
                        {getStatusBadge(version.status)}
                    </div>

                    {/* Change Type */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Change Type
                        </label>
                        {editMode ? (
                            <select
                                value={formData.change_type_id || ''}
                                onChange={(e) => {
                                    const typeId = parseInt(e.target.value);
                                    let changeType: ChangeType = 'MINOR';

                                    // Find change type to determine MINOR/MAJOR
                                    for (const category of categories) {
                                        const found = category.change_types.find(t => t.change_type_id === typeId);
                                        if (found) {
                                            changeType = found.requires_mv_approval ? 'MAJOR' : 'MINOR';
                                            break;
                                        }
                                    }

                                    setFormData({
                                        ...formData,
                                        change_type_id: typeId,
                                        change_type: changeType,
                                    });
                                }}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="">Select a change type...</option>
                                {categories.map(category => {
                                    const filteredTypes = category.change_types.filter(type => type.code !== 1);
                                    if (filteredTypes.length === 0) return null;

                                    return (
                                        <optgroup key={category.category_id} label={`${category.code}. ${category.name}`}>
                                            {filteredTypes.map(type => (
                                                <option key={type.change_type_id} value={type.change_type_id}>
                                                    {type.code}. {type.name}
                                                </option>
                                            ))}
                                        </optgroup>
                                    );
                                })}
                            </select>
                        ) : (
                            <div>
                                <p className="font-medium">{version.change_type_name || version.change_type}</p>
                                {version.change_category_name && (
                                    <p className="text-sm text-gray-500">{version.change_category_name}</p>
                                )}
                                <span className={`inline-block mt-1 px-2 py-1 rounded text-xs font-semibold ${version.change_type === 'MAJOR' ? 'bg-orange-200 text-orange-800' : 'bg-blue-200 text-blue-800'}`}>
                                    {version.change_type}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Change Description */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Change Description
                        </label>
                        {editMode ? (
                            <textarea
                                value={formData.change_description}
                                onChange={(e) => setFormData({ ...formData, change_description: e.target.value })}
                                rows={4}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        ) : (
                            <p className="text-gray-700">{version.change_description}</p>
                        )}
                    </div>

                    {/* Implementation Date */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Implementation Date
                        </label>
                        {editMode ? (
                            <input
                                type="date"
                                value={formData.production_date}
                                onChange={(e) => setFormData({ ...formData, production_date: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        ) : (
                            <p className="text-gray-700">
                                {version.production_date ? version.production_date.split('T')[0] : 'Not set'}
                            </p>
                        )}
                    </div>

                    {/* Created By */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Created By
                        </label>
                        <p className="text-gray-700">{version.created_by_name || 'Unknown'}</p>
                        <p className="text-sm text-gray-500">{new Date(version.created_at).toLocaleString()}</p>
                    </div>

                    {/* Validation Project */}
                    {version.validation_request_id && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Validation Project
                            </label>
                            <p className="text-gray-700">
                                Validation Project #{version.validation_request_id}
                                {version.validation_request_id && (
                                    <span className="ml-2 text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                                        Validation in progress
                                    </span>
                                )}
                            </p>
                        </div>
                    )}
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end gap-3 mt-6">
                    {editMode ? (
                        <>
                            <button
                                type="button"
                                onClick={() => {
                                    setEditMode(false);
                                    setFormData({
                                        version_number: version.version_number,
                                        change_type: version.change_type,
                                        change_type_id: version.change_type_id,
                                        change_description: version.change_description,
                                        production_date: version.production_date || '',
                                    });
                                    setError(null);
                                }}
                                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                                disabled={loading}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={handleSave}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                                disabled={loading}
                            >
                                {loading ? 'Saving...' : 'Save Changes'}
                            </button>
                        </>
                    ) : (
                        <>
                            {canEdit() && (
                                <button
                                    type="button"
                                    onClick={() => setEditMode(true)}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                                >
                                    Edit
                                </button>
                            )}
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                            >
                                Close
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default VersionDetailModal;

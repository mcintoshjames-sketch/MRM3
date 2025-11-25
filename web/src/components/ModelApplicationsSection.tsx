import { useState, useEffect } from 'react';
import api from '../api/client';

interface MapApplication {
    application_id: number;
    application_code: string;
    application_name: string;
    owner_name: string | null;
    department: string | null;
    criticality_tier: string | null;
    status: string;
}

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
}

interface User {
    user_id: number;
    full_name: string;
}

interface ModelApplication {
    model_id: number;
    application_id: number;
    application: MapApplication;
    relationship_type: TaxonomyValue;
    description: string | null;
    effective_date: string | null;
    end_date: string | null;
    created_at: string;
    created_by_user: User | null;
}

interface Props {
    modelId: number;
    canEdit: boolean;
}

export default function ModelApplicationsSection({ modelId, canEdit }: Props) {
    const [applications, setApplications] = useState<ModelApplication[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [includeInactive, setIncludeInactive] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Add modal state
    const [searchTerm, setSearchTerm] = useState('');
    const [searchResults, setSearchResults] = useState<MapApplication[]>([]);
    const [searching, setSearching] = useState(false);
    const [selectedApp, setSelectedApp] = useState<MapApplication | null>(null);
    const [relationshipTypes, setRelationshipTypes] = useState<TaxonomyValue[]>([]);
    const [formData, setFormData] = useState({
        relationship_type_id: 0,
        description: '',
        effective_date: new Date().toISOString().split('T')[0]
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchApplications();
        fetchRelationshipTypes();
    }, [modelId, includeInactive]);

    const fetchApplications = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get(`/models/${modelId}/applications`, {
                params: { include_inactive: includeInactive }
            });
            setApplications(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load applications');
        } finally {
            setLoading(false);
        }
    };

    const fetchRelationshipTypes = async () => {
        try {
            const response = await api.get('/taxonomies/');
            const appRelTaxonomy = response.data.find((t: any) => t.name === 'Application Relationship Type');
            if (appRelTaxonomy) {
                const detailResponse = await api.get(`/taxonomies/${appRelTaxonomy.taxonomy_id}`);
                setRelationshipTypes(detailResponse.data.values.filter((v: TaxonomyValue) => v.code !== 'OTHER' || true));
            }
        } catch (err) {
            console.error('Failed to load relationship types:', err);
        }
    };

    const searchApplications = async () => {
        if (!searchTerm.trim()) return;
        setSearching(true);
        try {
            const response = await api.get('/map/applications', {
                params: { search: searchTerm, status: 'Active', limit: 20 }
            });
            setSearchResults(response.data);
        } catch (err) {
            console.error('Failed to search applications:', err);
        } finally {
            setSearching(false);
        }
    };

    const handleAddApplication = async () => {
        if (!selectedApp || !formData.relationship_type_id) return;
        setSubmitting(true);
        setError(null);
        try {
            await api.post(`/models/${modelId}/applications`, {
                application_id: selectedApp.application_id,
                relationship_type_id: formData.relationship_type_id,
                description: formData.description || null,
                effective_date: formData.effective_date || null
            });
            setShowAddModal(false);
            resetAddForm();
            fetchApplications();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to add application');
        } finally {
            setSubmitting(false);
        }
    };

    const handleRemoveApplication = async (applicationId: number) => {
        if (!confirm('Are you sure you want to remove this application link?')) return;
        try {
            await api.delete(`/models/${modelId}/applications/${applicationId}`);
            fetchApplications();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to remove application');
        }
    };

    const resetAddForm = () => {
        setSearchTerm('');
        setSearchResults([]);
        setSelectedApp(null);
        setFormData({
            relationship_type_id: 0,
            description: '',
            effective_date: new Date().toISOString().split('T')[0]
        });
    };

    const getCriticalityColor = (tier: string | null) => {
        switch (tier) {
            case 'Critical': return 'bg-red-100 text-red-800';
            case 'High': return 'bg-orange-100 text-orange-800';
            case 'Medium': return 'bg-yellow-100 text-yellow-800';
            case 'Low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    if (loading) {
        return (
            <div className="bg-white p-6 rounded-lg shadow-md">
                <div className="animate-pulse">
                    <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
                    <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
                    <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white p-6 rounded-lg shadow-md">
            {/* Header */}
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Supporting Applications</h3>
                <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 text-sm text-gray-600">
                        <input
                            type="checkbox"
                            checked={includeInactive}
                            onChange={(e) => setIncludeInactive(e.target.checked)}
                            className="h-4 w-4 text-blue-600 rounded"
                        />
                        Include Inactive
                    </label>
                    {canEdit && (
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="btn-primary text-sm"
                        >
                            + Add Application
                        </button>
                    )}
                </div>
            </div>

            {error && (
                <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded">
                    {error}
                </div>
            )}

            {/* Applications Table */}
            {applications.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                    <p>No applications linked to this model.</p>
                    {canEdit && (
                        <p className="text-sm mt-2">
                            Click "Add Application" to link supporting applications from MAP.
                        </p>
                    )}
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Application</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Relationship</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Department</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Criticality</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Effective</th>
                                {canEdit && (
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                )}
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {applications.map((rel) => (
                                <tr key={`${rel.model_id}-${rel.application_id}`} className={rel.end_date ? 'bg-gray-50 opacity-60' : ''}>
                                    <td className="px-4 py-3">
                                        <div>
                                            <div className="font-medium text-gray-900">
                                                {rel.application.application_name}
                                            </div>
                                            <div className="text-xs text-gray-500">
                                                {rel.application.application_code}
                                            </div>
                                            {rel.description && (
                                                <div className="text-xs text-gray-600 mt-1 italic">
                                                    {rel.description}
                                                </div>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                            {rel.relationship_type.label}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-600">
                                        {rel.application.department || '-'}
                                    </td>
                                    <td className="px-4 py-3">
                                        {rel.application.criticality_tier && (
                                            <span className={`px-2 py-1 text-xs rounded ${getCriticalityColor(rel.application.criticality_tier)}`}>
                                                {rel.application.criticality_tier}
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-600">
                                        {rel.effective_date?.split('T')[0] || '-'}
                                        {rel.end_date && (
                                            <div className="text-xs text-red-600">
                                                Ended: {rel.end_date.split('T')[0]}
                                            </div>
                                        )}
                                    </td>
                                    {canEdit && (
                                        <td className="px-4 py-3">
                                            {!rel.end_date && (
                                                <button
                                                    onClick={() => handleRemoveApplication(rel.application_id)}
                                                    className="text-red-600 hover:text-red-800 text-sm"
                                                >
                                                    Remove
                                                </button>
                                            )}
                                        </td>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Add Application Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                        <div className="p-6">
                            <h3 className="text-lg font-semibold mb-4">Add Supporting Application</h3>

                            {/* Search MAP */}
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Search MAP Inventory</label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        className="input-field flex-1"
                                        placeholder="Search by name, code, or description..."
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && searchApplications()}
                                    />
                                    <button
                                        onClick={searchApplications}
                                        disabled={searching}
                                        className="btn-secondary"
                                    >
                                        {searching ? 'Searching...' : 'Search'}
                                    </button>
                                </div>
                            </div>

                            {/* Search Results */}
                            {searchResults.length > 0 && !selectedApp && (
                                <div className="mb-4 max-h-48 overflow-y-auto border rounded">
                                    {searchResults.map((app) => (
                                        <div
                                            key={app.application_id}
                                            className="p-3 border-b last:border-b-0 hover:bg-gray-50 cursor-pointer"
                                            onClick={() => setSelectedApp(app)}
                                        >
                                            <div className="font-medium">{app.application_name}</div>
                                            <div className="text-xs text-gray-500 flex gap-4">
                                                <span>{app.application_code}</span>
                                                <span>{app.department}</span>
                                                {app.criticality_tier && (
                                                    <span className={`px-1 rounded ${getCriticalityColor(app.criticality_tier)}`}>
                                                        {app.criticality_tier}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Selected Application */}
                            {selectedApp && (
                                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <div className="font-medium">{selectedApp.application_name}</div>
                                            <div className="text-xs text-gray-600">
                                                {selectedApp.application_code} | {selectedApp.department}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => setSelectedApp(null)}
                                            className="text-gray-400 hover:text-gray-600"
                                        >
                                            ×
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* Relationship Details */}
                            {selectedApp && (
                                <>
                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-1">Relationship Type *</label>
                                        <select
                                            className="input-field"
                                            value={formData.relationship_type_id}
                                            onChange={(e) => setFormData({ ...formData, relationship_type_id: parseInt(e.target.value) })}
                                        >
                                            <option value={0}>Select relationship type...</option>
                                            {relationshipTypes.map((rt) => (
                                                <option key={rt.value_id} value={rt.value_id}>
                                                    {rt.label}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-1">Description</label>
                                        <textarea
                                            className="input-field"
                                            rows={2}
                                            placeholder="Notes about this relationship..."
                                            value={formData.description}
                                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                        />
                                    </div>

                                    <div className="mb-4">
                                        <label className="block text-sm font-medium mb-1">Effective Date</label>
                                        <input
                                            type="date"
                                            className="input-field"
                                            value={formData.effective_date}
                                            onChange={(e) => setFormData({ ...formData, effective_date: e.target.value })}
                                        />
                                    </div>
                                </>
                            )}

                            {/* Actions */}
                            <div className="flex justify-end gap-2 mt-6">
                                <button
                                    onClick={() => { setShowAddModal(false); resetAddForm(); }}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleAddApplication}
                                    disabled={!selectedApp || !formData.relationship_type_id || submitting}
                                    className="btn-primary disabled:opacity-50"
                                >
                                    {submitting ? 'Adding...' : 'Add Application'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

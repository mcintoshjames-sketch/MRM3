import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
    listModelLimitations,
    getLimitation,
    createLimitation,
    updateLimitation,
    retireLimitation,
    LimitationListItem,
    LimitationDetail,
    LimitationCreate,
    LimitationUpdate,
} from '../api/limitations';
import { recommendationsApi, RecommendationListItem, RecommendationCreate } from '../api/recommendations';
import api from '../api/client';
import { isAdminOrValidator } from '../utils/roleUtils';

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
    description?: string;
}

interface User {
    user_id: number;
    full_name: string;
    email: string;
}

interface ModelLimitationsTabProps {
    modelId: number;
}

const ModelLimitationsTab: React.FC<ModelLimitationsTabProps> = ({ modelId }) => {
    const { user } = useAuth();
    const [limitations, setLimitations] = useState<LimitationListItem[]>([]);
    const [categories, setCategories] = useState<TaxonomyValue[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showRetired, setShowRetired] = useState(false);
    const [filterSignificance, setFilterSignificance] = useState<string>('');

    // Modal state
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showRetireModal, setShowRetireModal] = useState(false);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [selectedLimitation, setSelectedLimitation] = useState<LimitationDetail | null>(null);

    const canEdit = isAdminOrValidator(user);

    const fetchLimitations = async () => {
        try {
            setLoading(true);
            setError(null);
            const params: { include_retired?: boolean; significance?: 'Critical' | 'Non-Critical' } = {};
            if (showRetired) params.include_retired = true;
            if (filterSignificance) params.significance = filterSignificance as 'Critical' | 'Non-Critical';
            const data = await listModelLimitations(modelId, params);
            setLimitations(data);
        } catch (err) {
            console.error('Failed to fetch limitations:', err);
            setError('Failed to load limitations');
        } finally {
            setLoading(false);
        }
    };

    const fetchCategories = async () => {
        try {
            // First find the Limitation Category taxonomy ID
            const listResponse = await api.get('/taxonomies/');
            const taxonomies = listResponse.data;
            const limitationCategory = taxonomies.find((t: { name: string }) => t.name === 'Limitation Category');

            if (limitationCategory) {
                // Fetch the taxonomy with its values
                const detailResponse = await api.get(`/taxonomies/${limitationCategory.taxonomy_id}`);
                const taxonomyWithValues = detailResponse.data;
                if (taxonomyWithValues.values) {
                    setCategories(taxonomyWithValues.values.filter((v: { is_active: boolean }) => v.is_active));
                }
            }
        } catch (err) {
            console.error('Failed to fetch categories:', err);
        }
    };

    useEffect(() => {
        fetchLimitations();
        fetchCategories();
    }, [modelId, showRetired, filterSignificance]);

    const handleViewDetail = async (limitationId: number) => {
        try {
            const detail = await getLimitation(limitationId);
            setSelectedLimitation(detail);
            setShowDetailModal(true);
        } catch (err) {
            console.error('Failed to fetch limitation details:', err);
            setError('Failed to load limitation details');
        }
    };

    const handleEditClick = async (limitationId: number) => {
        try {
            const detail = await getLimitation(limitationId);
            setSelectedLimitation(detail);
            setShowEditModal(true);
        } catch (err) {
            console.error('Failed to fetch limitation details:', err);
            setError('Failed to load limitation details');
        }
    };

    const handleRetireClick = async (limitationId: number) => {
        try {
            const detail = await getLimitation(limitationId);
            setSelectedLimitation(detail);
            setShowRetireModal(true);
        } catch (err) {
            console.error('Failed to fetch limitation details:', err);
            setError('Failed to load limitation details');
        }
    };

    const getSignificanceBadge = (significance: string) => {
        if (significance === 'Critical') {
            return <span className="px-2 py-1 text-xs font-medium rounded bg-red-100 text-red-800">Critical</span>;
        }
        return <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-800">Non-Critical</span>;
    };

    const getConclusionBadge = (conclusion: string) => {
        if (conclusion === 'Mitigate') {
            return <span className="px-2 py-1 text-xs font-medium rounded bg-yellow-100 text-yellow-800">Mitigate</span>;
        }
        return <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">Accept</span>;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">Loading limitations...</span>
            </div>
        );
    }

    const criticalCount = limitations.filter(l => l.significance === 'Critical' && !l.is_retired).length;
    const nonCriticalCount = limitations.filter(l => l.significance === 'Non-Critical' && !l.is_retired).length;

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h3 className="text-xl font-bold">Limitations</h3>
                    <p className="text-sm text-gray-500 mt-1">
                        {criticalCount > 0 && (
                            <span className="text-red-600 font-medium">{criticalCount} Critical</span>
                        )}
                        {criticalCount > 0 && nonCriticalCount > 0 && ' · '}
                        {nonCriticalCount > 0 && (
                            <span>{nonCriticalCount} Non-Critical</span>
                        )}
                        {criticalCount === 0 && nonCriticalCount === 0 && 'No active limitations'}
                    </p>
                </div>
                {canEdit && (
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
                    >
                        + Add Limitation
                    </button>
                )}
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4 mb-4">
                <label className="flex items-center gap-2 text-sm text-gray-600">
                    <input
                        type="checkbox"
                        checked={showRetired}
                        onChange={(e) => setShowRetired(e.target.checked)}
                        className="rounded border-gray-300"
                    />
                    Show retired
                </label>
                <select
                    value={filterSignificance}
                    onChange={(e) => setFilterSignificance(e.target.value)}
                    className="text-sm border border-gray-300 rounded px-2 py-1"
                >
                    <option value="">All Significance</option>
                    <option value="Critical">Critical</option>
                    <option value="Non-Critical">Non-Critical</option>
                </select>
            </div>

            {error && (
                <div className="mb-4 p-3 bg-red-100 text-red-800 rounded">
                    {error}
                </div>
            )}

            {limitations.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="mt-4 text-lg">No limitations recorded</p>
                    <p className="mt-2 text-sm">
                        {canEdit
                            ? 'Click "Add Limitation" to document model constraints and weaknesses.'
                            : 'Limitations will appear here when documented by validators.'}
                    </p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Significance</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Conclusion</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {limitations.map((lim) => (
                                <tr key={lim.limitation_id} className={lim.is_retired ? 'bg-gray-50 opacity-60' : ''}>
                                    <td className="px-4 py-4 whitespace-nowrap">
                                        {getSignificanceBadge(lim.significance)}
                                    </td>
                                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {lim.category?.label || categories.find(c => c.value_id === lim.category_id)?.label || 'Unknown'}
                                    </td>
                                    <td className="px-4 py-4 text-sm text-gray-900 max-w-md">
                                        <div className="truncate" title={lim.description}>
                                            {lim.description.length > 100 ? `${lim.description.slice(0, 100)}...` : lim.description}
                                        </div>
                                    </td>
                                    <td className="px-4 py-4 whitespace-nowrap">
                                        {getConclusionBadge(lim.conclusion)}
                                    </td>
                                    <td className="px-4 py-4 whitespace-nowrap text-sm">
                                        {lim.is_retired ? (
                                            <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-600">Retired</span>
                                        ) : (
                                            <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800">Active</span>
                                        )}
                                    </td>
                                    <td className="px-4 py-4 whitespace-nowrap text-sm">
                                        <button
                                            onClick={() => handleViewDetail(lim.limitation_id)}
                                            className="text-blue-600 hover:text-blue-800 mr-3"
                                        >
                                            View
                                        </button>
                                        {canEdit && !lim.is_retired && (
                                            <>
                                                <button
                                                    onClick={() => handleEditClick(lim.limitation_id)}
                                                    className="text-blue-600 hover:text-blue-800 mr-3"
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => handleRetireClick(lim.limitation_id)}
                                                    className="text-red-600 hover:text-red-800"
                                                >
                                                    Retire
                                                </button>
                                            </>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Create Modal */}
            {showCreateModal && (
                <LimitationModal
                    mode="create"
                    modelId={modelId}
                    categories={categories}
                    onClose={() => setShowCreateModal(false)}
                    onSuccess={() => {
                        setShowCreateModal(false);
                        fetchLimitations();
                    }}
                />
            )}

            {/* Edit Modal */}
            {showEditModal && selectedLimitation && (
                <LimitationModal
                    mode="edit"
                    modelId={modelId}
                    categories={categories}
                    limitation={selectedLimitation}
                    onClose={() => {
                        setShowEditModal(false);
                        setSelectedLimitation(null);
                    }}
                    onSuccess={() => {
                        setShowEditModal(false);
                        setSelectedLimitation(null);
                        fetchLimitations();
                    }}
                />
            )}

            {/* Retire Modal */}
            {showRetireModal && selectedLimitation && (
                <RetireLimitationModal
                    limitation={selectedLimitation}
                    onClose={() => {
                        setShowRetireModal(false);
                        setSelectedLimitation(null);
                    }}
                    onSuccess={() => {
                        setShowRetireModal(false);
                        setSelectedLimitation(null);
                        fetchLimitations();
                    }}
                />
            )}

            {/* Detail Modal */}
            {showDetailModal && selectedLimitation && (
                <LimitationDetailModal
                    limitation={selectedLimitation}
                    categories={categories}
                    onClose={() => {
                        setShowDetailModal(false);
                        setSelectedLimitation(null);
                    }}
                />
            )}
        </div>
    );
};

// Limitation Create/Edit Modal Component
interface LimitationModalProps {
    mode: 'create' | 'edit';
    modelId: number;
    categories: TaxonomyValue[];
    limitation?: LimitationDetail;
    onClose: () => void;
    onSuccess: () => void;
}

const LimitationModal: React.FC<LimitationModalProps> = ({
    mode,
    modelId,
    categories,
    limitation,
    onClose,
    onSuccess,
}) => {
    const [formData, setFormData] = useState<{
        significance: 'Critical' | 'Non-Critical';
        category_id: number;
        description: string;
        impact_assessment: string;
        conclusion: 'Mitigate' | 'Accept';
        conclusion_rationale: string;
        user_awareness_description: string;
        recommendation_id: number | null;
    }>({
        significance: limitation?.significance || 'Non-Critical',
        category_id: limitation?.category_id || (categories[0]?.value_id || 0),
        description: limitation?.description || '',
        impact_assessment: limitation?.impact_assessment || '',
        conclusion: limitation?.conclusion || 'Accept',
        conclusion_rationale: limitation?.conclusion_rationale || '',
        user_awareness_description: limitation?.user_awareness_description || '',
        recommendation_id: limitation?.recommendation_id || null,
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Recommendation linking state
    const [recommendations, setRecommendations] = useState<RecommendationListItem[]>([]);
    const [loadingRecommendations, setLoadingRecommendations] = useState(false);
    const [recommendationMode, setRecommendationMode] = useState<'none' | 'existing' | 'new'>('none');
    const [newRecForm, setNewRecForm] = useState({
        title: '',
        description: '',
        target_date: '',
        priority_id: 0,
        assigned_to_id: 0,
    });
    const [priorities, setPriorities] = useState<TaxonomyValue[]>([]);
    const [availableUsers, setAvailableUsers] = useState<User[]>([]);
    const [userSearchQuery, setUserSearchQuery] = useState('');
    const [showUserDropdown, setShowUserDropdown] = useState(false);

    // Filter users based on search query
    const filteredUsers = availableUsers.filter(u =>
        u.full_name.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
        u.email.toLowerCase().includes(userSearchQuery.toLowerCase())
    );

    // Get selected user name for display
    const selectedUser = availableUsers.find(u => u.user_id === newRecForm.assigned_to_id);

    // Fetch recommendations for this model when conclusion is Mitigate
    useEffect(() => {
        if (formData.conclusion === 'Mitigate') {
            fetchRecommendations();
            fetchPriorities();
            fetchUsers();
        }
    }, [formData.conclusion, modelId]);

    const fetchRecommendations = async () => {
        try {
            setLoadingRecommendations(true);
            const data = await recommendationsApi.list({ model_id: modelId });
            // Filter to show only open recommendations (not closed)
            const openRecs = data.filter(r => r.current_status?.code !== 'CLOSED');
            setRecommendations(openRecs);
        } catch (err) {
            console.error('Failed to fetch recommendations:', err);
        } finally {
            setLoadingRecommendations(false);
        }
    };

    const fetchPriorities = async () => {
        try {
            // Fetch recommendation priority taxonomy
            const taxResponse = await api.get('/taxonomies/');
            const priorityTax = taxResponse.data.find((t: { name: string }) => t.name === 'Recommendation Priority');
            if (priorityTax) {
                const priorityDetail = await api.get(`/taxonomies/${priorityTax.taxonomy_id}`);
                setPriorities(priorityDetail.data.values?.filter((v: { is_active: boolean }) => v.is_active) || []);
            }
        } catch (err) {
            console.error('Failed to fetch priorities:', err);
        }
    };

    const fetchUsers = async () => {
        try {
            const response = await api.get('/auth/users');
            setAvailableUsers(response.data || []);
        } catch (err) {
            console.error('Failed to fetch users:', err);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validation
        if (!formData.category_id) {
            setError('Please select a category');
            return;
        }
        if (!formData.description.trim()) {
            setError('Description is required');
            return;
        }
        if (!formData.impact_assessment.trim()) {
            setError('Impact assessment is required');
            return;
        }
        if (!formData.conclusion_rationale.trim()) {
            setError('Conclusion rationale is required');
            return;
        }
        if (formData.significance === 'Critical' && !formData.user_awareness_description.trim()) {
            setError('User awareness description is required for Critical limitations');
            return;
        }

        // Validate new recommendation form if creating new
        if (formData.conclusion === 'Mitigate' && recommendationMode === 'new') {
            if (!newRecForm.title.trim()) {
                setError('Recommendation title is required');
                return;
            }
            if (!newRecForm.description.trim()) {
                setError('Recommendation description is required');
                return;
            }
            if (!newRecForm.target_date) {
                setError('Recommendation target date is required');
                return;
            }
            if (!newRecForm.priority_id) {
                setError('Recommendation priority is required');
                return;
            }
            if (!newRecForm.assigned_to_id) {
                setError('Recommendation assignee is required');
                return;
            }
        }

        try {
            setSaving(true);
            let recommendationId = formData.recommendation_id;

            // Create new recommendation if selected
            if (formData.conclusion === 'Mitigate' && recommendationMode === 'new') {
                const recPayload: RecommendationCreate = {
                    model_id: modelId,
                    title: newRecForm.title,
                    description: newRecForm.description,
                    priority_id: newRecForm.priority_id,
                    assigned_to_id: newRecForm.assigned_to_id,
                    original_target_date: newRecForm.target_date,
                };
                const newRec = await recommendationsApi.create(recPayload);
                recommendationId = newRec.recommendation_id;
            }

            if (mode === 'create') {
                const payload: LimitationCreate = {
                    significance: formData.significance,
                    category_id: formData.category_id,
                    description: formData.description,
                    impact_assessment: formData.impact_assessment,
                    conclusion: formData.conclusion,
                    conclusion_rationale: formData.conclusion_rationale,
                    recommendation_id: formData.conclusion === 'Mitigate' && recommendationMode !== 'none' && recommendationId ? recommendationId : undefined,
                    user_awareness_description: formData.significance === 'Critical' ? formData.user_awareness_description : undefined,
                };
                await createLimitation(modelId, payload);
            } else if (limitation) {
                const payload: LimitationUpdate = {
                    significance: formData.significance,
                    category_id: formData.category_id,
                    description: formData.description,
                    impact_assessment: formData.impact_assessment,
                    conclusion: formData.conclusion,
                    conclusion_rationale: formData.conclusion_rationale,
                    recommendation_id: formData.conclusion === 'Mitigate' && recommendationMode !== 'none' && recommendationId ? recommendationId : null,
                    user_awareness_description: formData.significance === 'Critical' ? formData.user_awareness_description : null,
                };
                await updateLimitation(limitation.limitation_id, payload);
            }
            onSuccess();
        } catch (err: unknown) {
            console.error('Failed to save limitation:', err);
            const errorDetail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(errorDetail || 'Failed to save limitation');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="p-6 border-b">
                    <h2 className="text-xl font-bold">
                        {mode === 'create' ? 'Add Limitation' : 'Edit Limitation'}
                    </h2>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {error && (
                        <div className="p-3 bg-red-100 text-red-800 rounded text-sm">
                            {error}
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Significance *
                            </label>
                            <select
                                value={formData.significance}
                                onChange={(e) => setFormData({ ...formData, significance: e.target.value as 'Critical' | 'Non-Critical' })}
                                className="w-full border border-gray-300 rounded px-3 py-2"
                                required
                            >
                                <option value="Non-Critical">Non-Critical</option>
                                <option value="Critical">Critical</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Category *
                            </label>
                            <select
                                value={formData.category_id}
                                onChange={(e) => setFormData({ ...formData, category_id: parseInt(e.target.value) })}
                                className="w-full border border-gray-300 rounded px-3 py-2"
                                required
                            >
                                <option value="">Select category...</option>
                                {categories.map((cat) => (
                                    <option key={cat.value_id} value={cat.value_id}>
                                        {cat.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description *
                        </label>
                        <textarea
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className="w-full border border-gray-300 rounded px-3 py-2"
                            rows={3}
                            placeholder="Describe the nature of this limitation..."
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Impact Assessment *
                        </label>
                        <textarea
                            value={formData.impact_assessment}
                            onChange={(e) => setFormData({ ...formData, impact_assessment: e.target.value })}
                            className="w-full border border-gray-300 rounded px-3 py-2"
                            rows={3}
                            placeholder="Assess the impact of this limitation on model outputs and decisions..."
                            required
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Conclusion *
                            </label>
                            <select
                                value={formData.conclusion}
                                onChange={(e) => {
                                    const newConclusion = e.target.value as 'Mitigate' | 'Accept';
                                    setFormData({ ...formData, conclusion: newConclusion, recommendation_id: null });
                                    if (newConclusion === 'Accept') {
                                        setRecommendationMode('none');
                                    }
                                }}
                                className="w-full border border-gray-300 rounded px-3 py-2"
                                required
                            >
                                <option value="Accept">Accept</option>
                                <option value="Mitigate">Mitigate</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Conclusion Rationale *
                        </label>
                        <textarea
                            value={formData.conclusion_rationale}
                            onChange={(e) => setFormData({ ...formData, conclusion_rationale: e.target.value })}
                            className="w-full border border-gray-300 rounded px-3 py-2"
                            rows={2}
                            placeholder="Explain the rationale for this conclusion..."
                            required
                        />
                    </div>

                    {/* Recommendation Linking Section - Only shown when Mitigate is selected */}
                    {formData.conclusion === 'Mitigate' && (
                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 space-y-3">
                            <div className="flex items-center gap-2">
                                <svg className="w-5 h-5 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <span className="text-sm font-medium text-yellow-800">Link to Recommendation (Optional)</span>
                            </div>
                            <p className="text-xs text-yellow-700">
                                When a limitation requires mitigation, you can link it to an existing recommendation or create a new one to track the remediation work.
                            </p>

                            {/* Recommendation Mode Selection */}
                            <div className="flex gap-4">
                                <label className="flex items-center gap-2">
                                    <input
                                        type="radio"
                                        name="recMode"
                                        checked={recommendationMode === 'none'}
                                        onChange={() => {
                                            setRecommendationMode('none');
                                            setFormData({ ...formData, recommendation_id: null });
                                        }}
                                        className="text-yellow-600"
                                    />
                                    <span className="text-sm text-gray-700">No recommendation</span>
                                </label>
                                <label className="flex items-center gap-2">
                                    <input
                                        type="radio"
                                        name="recMode"
                                        checked={recommendationMode === 'existing'}
                                        onChange={() => setRecommendationMode('existing')}
                                        className="text-yellow-600"
                                    />
                                    <span className="text-sm text-gray-700">Link existing</span>
                                </label>
                                <label className="flex items-center gap-2">
                                    <input
                                        type="radio"
                                        name="recMode"
                                        checked={recommendationMode === 'new'}
                                        onChange={() => setRecommendationMode('new')}
                                        className="text-yellow-600"
                                    />
                                    <span className="text-sm text-gray-700">Create new</span>
                                </label>
                            </div>

                            {/* Existing Recommendation Dropdown */}
                            {recommendationMode === 'existing' && (
                                <div>
                                    {loadingRecommendations ? (
                                        <p className="text-sm text-gray-500">Loading recommendations...</p>
                                    ) : recommendations.length === 0 ? (
                                        <p className="text-sm text-gray-500">No open recommendations found for this model.</p>
                                    ) : (
                                        <select
                                            value={formData.recommendation_id || ''}
                                            onChange={(e) => setFormData({ ...formData, recommendation_id: e.target.value ? parseInt(e.target.value) : null })}
                                            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                        >
                                            <option value="">Select a recommendation...</option>
                                            {recommendations.map((rec) => (
                                                <option key={rec.recommendation_id} value={rec.recommendation_id}>
                                                    {rec.recommendation_code} - {rec.title} ({rec.current_status?.label || 'Unknown'})
                                                </option>
                                            ))}
                                        </select>
                                    )}
                                </div>
                            )}

                            {/* New Recommendation Form */}
                            {recommendationMode === 'new' && (
                                <div className="space-y-3 pt-2 border-t border-yellow-200">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Recommendation Title *
                                        </label>
                                        <input
                                            type="text"
                                            value={newRecForm.title}
                                            onChange={(e) => setNewRecForm({ ...newRecForm, title: e.target.value })}
                                            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                            placeholder="e.g., Address data quality limitation"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Description *
                                        </label>
                                        <textarea
                                            value={newRecForm.description}
                                            onChange={(e) => setNewRecForm({ ...newRecForm, description: e.target.value })}
                                            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                            rows={2}
                                            placeholder="Describe the recommended actions to mitigate this limitation..."
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Priority *
                                            </label>
                                            <select
                                                value={newRecForm.priority_id}
                                                onChange={(e) => setNewRecForm({ ...newRecForm, priority_id: parseInt(e.target.value) || 0 })}
                                                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                            >
                                                <option value={0}>Select priority...</option>
                                                {priorities.map((p) => (
                                                    <option key={p.value_id} value={p.value_id}>
                                                        {p.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Target Date *
                                            </label>
                                            <input
                                                type="date"
                                                value={newRecForm.target_date}
                                                onChange={(e) => setNewRecForm({ ...newRecForm, target_date: e.target.value })}
                                                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                            />
                                        </div>
                                    </div>
                                    <div className="relative">
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Assign To *
                                        </label>
                                        <div className="relative">
                                            <input
                                                type="text"
                                                value={selectedUser ? selectedUser.full_name : userSearchQuery}
                                                onChange={(e) => {
                                                    setUserSearchQuery(e.target.value);
                                                    setNewRecForm({ ...newRecForm, assigned_to_id: 0 });
                                                    setShowUserDropdown(true);
                                                }}
                                                onFocus={() => setShowUserDropdown(true)}
                                                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                                placeholder="Search by name or email..."
                                            />
                                            {selectedUser && (
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        setNewRecForm({ ...newRecForm, assigned_to_id: 0 });
                                                        setUserSearchQuery('');
                                                    }}
                                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                                >
                                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                    </svg>
                                                </button>
                                            )}
                                        </div>
                                        {showUserDropdown && !selectedUser && (
                                            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded shadow-lg max-h-48 overflow-y-auto">
                                                {filteredUsers.length === 0 ? (
                                                    <div className="px-3 py-2 text-sm text-gray-500">
                                                        {userSearchQuery ? 'No users found' : 'Type to search users...'}
                                                    </div>
                                                ) : (
                                                    filteredUsers.slice(0, 10).map((u) => (
                                                        <button
                                                            key={u.user_id}
                                                            type="button"
                                                            onClick={() => {
                                                                setNewRecForm({ ...newRecForm, assigned_to_id: u.user_id });
                                                                setUserSearchQuery('');
                                                                setShowUserDropdown(false);
                                                            }}
                                                            className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 border-b border-gray-100 last:border-b-0"
                                                        >
                                                            <div className="font-medium">{u.full_name}</div>
                                                            <div className="text-gray-500 text-xs">{u.email}</div>
                                                        </button>
                                                    ))
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {formData.significance === 'Critical' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                User Awareness Description *
                                <span className="text-red-500 text-xs ml-1">(Required for Critical)</span>
                            </label>
                            <textarea
                                value={formData.user_awareness_description}
                                onChange={(e) => setFormData({ ...formData, user_awareness_description: e.target.value })}
                                className="w-full border border-gray-300 rounded px-3 py-2"
                                rows={2}
                                placeholder="Describe how users are made aware of this limitation..."
                                required
                            />
                        </div>
                    )}

                    <div className="flex justify-end gap-3 pt-4 border-t">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
                            disabled={saving}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                            disabled={saving}
                        >
                            {saving ? 'Saving...' : mode === 'create' ? 'Create' : 'Save Changes'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// Retire Limitation Modal
interface RetireLimitationModalProps {
    limitation: LimitationDetail;
    onClose: () => void;
    onSuccess: () => void;
}

const RetireLimitationModal: React.FC<RetireLimitationModalProps> = ({
    limitation,
    onClose,
    onSuccess,
}) => {
    const [retirementReason, setRetirementReason] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!retirementReason.trim()) {
            setError('Retirement reason is required');
            return;
        }

        try {
            setSaving(true);
            await retireLimitation(limitation.limitation_id, {
                retirement_reason: retirementReason,
            });
            onSuccess();
        } catch (err: unknown) {
            console.error('Failed to retire limitation:', err);
            const errorDetail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(errorDetail || 'Failed to retire limitation');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg w-full max-w-lg">
                <div className="p-6 border-b">
                    <h2 className="text-xl font-bold text-red-600">Retire Limitation</h2>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {error && (
                        <div className="p-3 bg-red-100 text-red-800 rounded text-sm">
                            {error}
                        </div>
                    )}

                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
                        <p className="font-medium text-yellow-800">Are you sure you want to retire this limitation?</p>
                        <p className="mt-1 text-yellow-700">
                            Retired limitations are hidden by default but can still be viewed in the history.
                        </p>
                    </div>

                    <div className="bg-gray-50 p-3 rounded">
                        <p className="text-sm text-gray-600">
                            <span className="font-medium">Description:</span> {limitation.description.slice(0, 100)}
                            {limitation.description.length > 100 && '...'}
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Retirement Reason *
                        </label>
                        <textarea
                            value={retirementReason}
                            onChange={(e) => setRetirementReason(e.target.value)}
                            className="w-full border border-gray-300 rounded px-3 py-2"
                            rows={3}
                            placeholder="Explain why this limitation is being retired..."
                            required
                        />
                    </div>

                    <div className="flex justify-end gap-3 pt-4 border-t">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
                            disabled={saving}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                            disabled={saving}
                        >
                            {saving ? 'Retiring...' : 'Retire Limitation'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// Limitation Detail Modal
interface LimitationDetailModalProps {
    limitation: LimitationDetail;
    categories: TaxonomyValue[];
    onClose: () => void;
}

const LimitationDetailModal: React.FC<LimitationDetailModalProps> = ({
    limitation,
    categories,
    onClose,
}) => {
    const categoryLabel = limitation.category?.label || categories.find(c => c.value_id === limitation.category_id)?.label || 'Unknown';

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="p-6 border-b flex justify-between items-center">
                    <h2 className="text-xl font-bold">Limitation Details</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    {/* Status badges */}
                    <div className="flex items-center gap-3">
                        {limitation.significance === 'Critical' ? (
                            <span className="px-3 py-1 text-sm font-medium rounded bg-red-100 text-red-800">Critical</span>
                        ) : (
                            <span className="px-3 py-1 text-sm font-medium rounded bg-gray-100 text-gray-800">Non-Critical</span>
                        )}
                        {limitation.conclusion === 'Mitigate' ? (
                            <span className="px-3 py-1 text-sm font-medium rounded bg-yellow-100 text-yellow-800">Mitigate</span>
                        ) : (
                            <span className="px-3 py-1 text-sm font-medium rounded bg-green-100 text-green-800">Accept</span>
                        )}
                        {limitation.is_retired && (
                            <span className="px-3 py-1 text-sm font-medium rounded bg-gray-100 text-gray-600">Retired</span>
                        )}
                    </div>

                    {/* Category */}
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">Category</h4>
                        <p className="text-gray-900">{categoryLabel}</p>
                    </div>

                    {/* Description */}
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">Description</h4>
                        <p className="text-gray-900 whitespace-pre-wrap">{limitation.description}</p>
                    </div>

                    {/* Impact Assessment */}
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">Impact Assessment</h4>
                        <p className="text-gray-900 whitespace-pre-wrap">{limitation.impact_assessment}</p>
                    </div>

                    {/* Conclusion Rationale */}
                    <div>
                        <h4 className="text-sm font-medium text-gray-500 mb-1">Conclusion Rationale</h4>
                        <p className="text-gray-900 whitespace-pre-wrap">{limitation.conclusion_rationale}</p>
                    </div>

                    {/* User Awareness (for Critical) */}
                    {limitation.significance === 'Critical' && limitation.user_awareness_description && (
                        <div className="bg-red-50 p-4 rounded border border-red-200">
                            <h4 className="text-sm font-medium text-red-800 mb-1">User Awareness</h4>
                            <p className="text-red-900 whitespace-pre-wrap">{limitation.user_awareness_description}</p>
                        </div>
                    )}

                    {/* Traceability */}
                    {(limitation.validation_request_id || limitation.model_version_id || limitation.recommendation_id) && (
                        <div className="border-t pt-4">
                            <h4 className="text-sm font-medium text-gray-500 mb-2">Traceability</h4>
                            <div className="grid grid-cols-3 gap-4 text-sm">
                                {limitation.validation_request_id && (
                                    <div>
                                        <span className="text-gray-500">Validation Request:</span>{' '}
                                        <span className="text-gray-900">#{limitation.validation_request_id}</span>
                                    </div>
                                )}
                                {limitation.model_version && (
                                    <div>
                                        <span className="text-gray-500">Model Version:</span>{' '}
                                        <span className="text-gray-900">{limitation.model_version.version_name}</span>
                                    </div>
                                )}
                                {limitation.recommendation && (
                                    <div className="col-span-3">
                                        <span className="text-gray-500">Linked Recommendation:</span>{' '}
                                        <Link
                                            to={`/recommendations/${limitation.recommendation.recommendation_id}`}
                                            className="text-blue-600 hover:text-blue-800 hover:underline"
                                        >
                                            {limitation.recommendation.title}
                                        </Link>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Retirement info */}
                    {limitation.is_retired && (
                        <div className="bg-gray-50 p-4 rounded border border-gray-200">
                            <h4 className="text-sm font-medium text-gray-700 mb-2">Retirement Details</h4>
                            <div className="text-sm space-y-1">
                                <p><span className="text-gray-500">Retired on:</span> {limitation.retirement_date?.split('T')[0]}</p>
                                <p><span className="text-gray-500">Retired by:</span> {limitation.retired_by?.full_name}</p>
                                <p><span className="text-gray-500">Reason:</span> {limitation.retirement_reason}</p>
                            </div>
                        </div>
                    )}

                    {/* Metadata */}
                    <div className="border-t pt-4 text-sm text-gray-500">
                        <p>Created by {limitation.created_by?.full_name} on {limitation.created_at.split('T')[0]}</p>
                        <p>Last updated: {limitation.updated_at.split('T')[0]}</p>
                    </div>
                </div>

                <div className="p-6 border-t">
                    <button
                        onClick={onClose}
                        className="w-full px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ModelLimitationsTab;

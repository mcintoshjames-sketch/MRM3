import { useState, useEffect } from 'react';
import { Recommendation, TaxonomyValue, RecommendationUpdate, recommendationsApi } from '../api/recommendations';
import api from '../api/client';

interface User {
    user_id: number;
    email: string;
    full_name: string;
}

interface RecommendationEditModalProps {
    recommendation: Recommendation;
    isOpen: boolean;
    onClose: () => void;
    onSave: () => void;
}

// Statuses that allow full editing
const FULL_EDIT_STATUSES = ['REC_DRAFT', 'REC_PENDING_RESPONSE', 'REC_PENDING_VALIDATOR_REVIEW'];

// Statuses that allow limited editing
const LIMITED_EDIT_STATUSES = ['REC_PENDING_ACKNOWLEDGEMENT', 'REC_OPEN', 'REC_REWORK_REQUIRED'];

export default function RecommendationEditModal({
    recommendation,
    isOpen,
    onClose,
    onSave
}: RecommendationEditModalProps) {
    const [formData, setFormData] = useState<RecommendationUpdate>({});
    const [priorities, setPriorities] = useState<TaxonomyValue[]>([]);
    const [categories, setCategories] = useState<TaxonomyValue[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const currentStatusCode = recommendation.current_status?.code || '';
    const isFullEdit = FULL_EDIT_STATUSES.includes(currentStatusCode);
    const isLimitedEdit = LIMITED_EDIT_STATUSES.includes(currentStatusCode);

    useEffect(() => {
        if (isOpen) {
            // Initialize form with current values
            // Extract IDs from nested objects since API returns expanded relationships
            setFormData({
                title: recommendation.title,
                description: recommendation.description,
                root_cause_analysis: recommendation.root_cause_analysis || '',
                priority_id: recommendation.priority?.value_id || recommendation.priority_id,
                category_id: recommendation.category?.value_id || recommendation.category_id || null,
                assigned_to_id: recommendation.assigned_to?.user_id || recommendation.assigned_to_id,
                current_target_date: recommendation.current_target_date,
            });
            setError(null);
            fetchTaxonomies();
            fetchUsers();
        }
    }, [isOpen, recommendation]);

    const fetchTaxonomies = async () => {
        try {
            const response = await api.get('/taxonomies/');
            const taxonomies = response.data;

            // Find priority taxonomy
            const priorityTax = taxonomies.find((t: any) => t.name === 'Recommendation Priority');
            if (priorityTax) {
                const detailRes = await api.get(`/taxonomies/${priorityTax.taxonomy_id}`);
                setPriorities(detailRes.data.values?.filter((v: TaxonomyValue) => v.is_active) || []);
            }

            // Find category taxonomy
            const categoryTax = taxonomies.find((t: any) => t.name === 'Recommendation Category');
            if (categoryTax) {
                const detailRes = await api.get(`/taxonomies/${categoryTax.taxonomy_id}`);
                setCategories(detailRes.data.values?.filter((v: TaxonomyValue) => v.is_active) || []);
            }
        } catch (err) {
            console.error('Failed to fetch taxonomies:', err);
        }
    };

    const fetchUsers = async () => {
        try {
            const response = await api.get('/auth/users');
            setUsers(response.data);
        } catch (err) {
            console.error('Failed to fetch users:', err);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setError(null);

        try {
            // Build update payload - only include changed fields
            const updatePayload: RecommendationUpdate = {};

            // Extract original IDs from nested objects
            const originalPriorityId = recommendation.priority?.value_id || recommendation.priority_id;
            const originalCategoryId = recommendation.category?.value_id || recommendation.category_id || null;
            const originalAssignedToId = recommendation.assigned_to?.user_id || recommendation.assigned_to_id;

            if (isFullEdit) {
                if (formData.title !== recommendation.title) {
                    updatePayload.title = formData.title;
                }
                if (formData.description !== recommendation.description) {
                    updatePayload.description = formData.description;
                }
                if (formData.root_cause_analysis !== (recommendation.root_cause_analysis || '')) {
                    updatePayload.root_cause_analysis = formData.root_cause_analysis;
                }
                if (formData.priority_id !== originalPriorityId) {
                    updatePayload.priority_id = formData.priority_id;
                }
                if (formData.category_id !== originalCategoryId) {
                    updatePayload.category_id = formData.category_id;
                }
            }

            // These fields are allowed in both full and limited edit modes
            if (formData.assigned_to_id !== originalAssignedToId) {
                updatePayload.assigned_to_id = formData.assigned_to_id;
            }
            if (formData.current_target_date !== recommendation.current_target_date) {
                updatePayload.current_target_date = formData.current_target_date;
            }

            // Only submit if there are changes
            if (Object.keys(updatePayload).length === 0) {
                onClose();
                return;
            }

            await recommendationsApi.update(recommendation.recommendation_id, updatePayload);
            onSave();
            onClose();
        } catch (err: any) {
            console.error('Failed to update recommendation:', err);
            setError(err.response?.data?.detail || 'Failed to update recommendation');
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div className="px-6 py-4 border-b border-gray-200">
                    <div className="flex justify-between items-center">
                        <h2 className="text-lg font-medium text-gray-900">
                            Edit Recommendation
                        </h2>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-500"
                        >
                            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                    {isLimitedEdit && (
                        <p className="mt-2 text-sm text-amber-600 bg-amber-50 px-3 py-2 rounded">
                            In {recommendation.current_status?.label} status, only Assigned To and Target Date can be modified.
                        </p>
                    )}
                </div>

                <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                            {error}
                        </div>
                    )}

                    {/* Title - Full edit only */}
                    {isFullEdit && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700">
                                Title <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                value={formData.title || ''}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                required
                            />
                        </div>
                    )}

                    {/* Description - Full edit only */}
                    {isFullEdit && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700">
                                Description <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                value={formData.description || ''}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                rows={4}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                required
                            />
                        </div>
                    )}

                    {/* Root Cause Analysis - Full edit only */}
                    {isFullEdit && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700">
                                Root Cause Analysis
                            </label>
                            <textarea
                                value={formData.root_cause_analysis || ''}
                                onChange={(e) => setFormData({ ...formData, root_cause_analysis: e.target.value })}
                                rows={3}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                            />
                        </div>
                    )}

                    {/* Priority - Full edit only */}
                    {isFullEdit && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700">
                                Priority <span className="text-red-500">*</span>
                            </label>
                            <select
                                value={formData.priority_id || ''}
                                onChange={(e) => setFormData({ ...formData, priority_id: parseInt(e.target.value) })}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                required
                            >
                                <option value="">Select priority...</option>
                                {priorities.map((p) => (
                                    <option key={p.value_id} value={p.value_id}>
                                        {p.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Category - Full edit only */}
                    {isFullEdit && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700">
                                Category
                            </label>
                            <select
                                value={formData.category_id || ''}
                                onChange={(e) => setFormData({ ...formData, category_id: e.target.value ? parseInt(e.target.value) : null })}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                            >
                                <option value="">Select category...</option>
                                {categories.map((c) => (
                                    <option key={c.value_id} value={c.value_id}>
                                        {c.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Assigned To - Always editable */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Assigned To <span className="text-red-500">*</span>
                        </label>
                        <select
                            value={formData.assigned_to_id || ''}
                            onChange={(e) => setFormData({ ...formData, assigned_to_id: parseInt(e.target.value) })}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                            required
                        >
                            <option value="">Select user...</option>
                            {users.map((u) => (
                                <option key={u.user_id} value={u.user_id}>
                                    {u.full_name} ({u.email})
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Current Target Date - Always editable */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Current Target Date <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="date"
                            value={formData.current_target_date || ''}
                            onChange={(e) => setFormData({ ...formData, current_target_date: e.target.value })}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                            required
                        />
                        {formData.current_target_date !== recommendation.original_target_date && (
                            <p className="mt-1 text-xs text-gray-500">
                                Original target: {recommendation.original_target_date}
                            </p>
                        )}
                    </div>

                    {/* Form Actions */}
                    <div className="flex justify-end space-x-3 pt-4 border-t">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            className={`px-4 py-2 text-sm font-medium text-white rounded-md ${
                                saving
                                    ? 'bg-blue-400 cursor-not-allowed'
                                    : 'bg-blue-600 hover:bg-blue-700'
                            }`}
                        >
                            {saving ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

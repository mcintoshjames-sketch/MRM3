import { useState, useEffect } from 'react';
import api from '../api/client';
import { bulkUpdateFields, BulkUpdateFieldsRequest, BulkUpdateFieldsResponse } from '../api/modelBulk';

interface User {
    user_id: number;
    email: string;
    full_name: string;
}

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
    is_active: boolean;
}

interface Taxonomy {
    taxonomy_id: number;
    name: string;
    values: TaxonomyValue[];
}

interface Props {
    isOpen: boolean;
    selectedModelIds: number[];
    onClose: () => void;
    onSuccess: (message: string) => void;
}

// Available fields for bulk update
const BULK_UPDATE_FIELDS = [
    { key: 'owner_id', label: 'Owner', type: 'user_picker', group: 'People' },
    { key: 'developer_id', label: 'Developer', type: 'user_picker', group: 'People' },
    { key: 'shared_owner_id', label: 'Shared Owner', type: 'user_picker', group: 'People' },
    { key: 'shared_developer_id', label: 'Shared Developer', type: 'user_picker', group: 'People' },
    { key: 'monitoring_manager_id', label: 'Monitoring Manager', type: 'user_picker', group: 'People' },
    { key: 'products_covered', label: 'Products Covered', type: 'textarea', group: 'Text' },
    { key: 'user_ids', label: 'Model Users', type: 'multi_user_picker', group: 'Collections' },
    { key: 'regulatory_category_ids', label: 'Regulatory Categories', type: 'checkbox_list', group: 'Collections' },
] as const;

type FieldKey = typeof BULK_UPDATE_FIELDS[number]['key'];

export default function BulkUpdateFieldsModal({ isOpen, selectedModelIds, onClose, onSuccess }: Props) {
    // Step state
    const [step, setStep] = useState<1 | 2>(1);

    // Data loading
    const [users, setUsers] = useState<User[]>([]);
    const [taxonomies, setTaxonomies] = useState<Taxonomy[]>([]);
    const [loading, setLoading] = useState(false);

    // Field selection (Step 1)
    const [selectedFields, setSelectedFields] = useState<Set<FieldKey>>(new Set());

    // Field values (Step 2)
    const [fieldValues, setFieldValues] = useState<Record<string, any>>({});
    const [multiSelectModes, setMultiSelectModes] = useState<Record<string, 'add' | 'replace'>>({
        user_ids: 'add',
        regulatory_category_ids: 'add',
    });

    // User search state for each picker
    const [userSearchTerms, setUserSearchTerms] = useState<Record<string, string>>({});
    const [showUserDropdowns, setShowUserDropdowns] = useState<Record<string, boolean>>({});

    // Submission state
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [results, setResults] = useState<BulkUpdateFieldsResponse | null>(null);

    // Load data on open
    useEffect(() => {
        if (isOpen) {
            loadData();
            // Reset state
            setStep(1);
            setSelectedFields(new Set());
            setFieldValues({});
            setMultiSelectModes({ user_ids: 'add', regulatory_category_ids: 'add' });
            setUserSearchTerms({});
            setShowUserDropdowns({});
            setError(null);
            setResults(null);
        }
    }, [isOpen]);

    const loadData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [usersRes, taxonomiesRes] = await Promise.all([
                api.get('/auth/users'),
                api.get('/taxonomies/')
            ]);
            setUsers(usersRes.data);
            setTaxonomies(taxonomiesRes.data);
        } catch (err) {
            setError('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    const getRegulatoryCategories = (): TaxonomyValue[] => {
        const taxonomy = taxonomies.find(t => t.name === 'Regulatory Category');
        return taxonomy?.values.filter(v => v.is_active) || [];
    };

    const toggleField = (key: FieldKey) => {
        setSelectedFields(prev => {
            const next = new Set(prev);
            if (next.has(key)) {
                next.delete(key);
                // Clear value when deselecting
                setFieldValues(prev => {
                    const { [key]: _, ...rest } = prev;
                    return rest;
                });
            } else {
                next.add(key);
            }
            return next;
        });
    };

    const handleUserSelect = (fieldKey: string, user: User | null) => {
        setFieldValues(prev => ({
            ...prev,
            [fieldKey]: user?.user_id ?? null
        }));
        setUserSearchTerms(prev => ({
            ...prev,
            [fieldKey]: user?.full_name ?? ''
        }));
        setShowUserDropdowns(prev => ({
            ...prev,
            [fieldKey]: false
        }));
    };

    const handleMultiUserToggle = (userId: number) => {
        setFieldValues(prev => {
            const current: number[] = prev.user_ids || [];
            if (current.includes(userId)) {
                return { ...prev, user_ids: current.filter(id => id !== userId) };
            }
            return { ...prev, user_ids: [...current, userId] };
        });
    };

    const handleCategoryToggle = (valueId: number) => {
        setFieldValues(prev => {
            const current: number[] = prev.regulatory_category_ids || [];
            if (current.includes(valueId)) {
                return { ...prev, regulatory_category_ids: current.filter(id => id !== valueId) };
            }
            return { ...prev, regulatory_category_ids: [...current, valueId] };
        });
    };

    const handleSubmit = async () => {
        setSubmitting(true);
        setError(null);
        setResults(null);

        try {
            // Build request with only selected fields
            const request: BulkUpdateFieldsRequest = {
                model_ids: selectedModelIds,
            };

            for (const field of selectedFields) {
                const value = fieldValues[field];

                if (field === 'user_ids') {
                    request.user_ids = value || [];
                    request.user_ids_mode = multiSelectModes.user_ids;
                } else if (field === 'regulatory_category_ids') {
                    request.regulatory_category_ids = value || [];
                    request.regulatory_category_ids_mode = multiSelectModes.regulatory_category_ids;
                } else if (field === 'products_covered') {
                    request.products_covered = value ?? null;
                } else {
                    // People pickers
                    (request as any)[field] = value ?? null;
                }
            }

            const response = await bulkUpdateFields(request);
            setResults(response);

            // Build success message
            let message = `Updated ${response.total_modified} model${response.total_modified !== 1 ? 's' : ''} successfully`;
            if (response.total_failed > 0) {
                message += `. ${response.total_failed} failed.`;
            }

            onSuccess(message);

            // Only close if all succeeded
            if (response.total_failed === 0) {
                handleClose();
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update models');
        } finally {
            setSubmitting(false);
        }
    };

    const handleClose = () => {
        setStep(1);
        setSelectedFields(new Set());
        setFieldValues({});
        setError(null);
        setResults(null);
        onClose();
    };

    const filteredUsers = (searchTerm: string) => {
        if (!searchTerm) return users.slice(0, 20);
        const term = searchTerm.toLowerCase();
        return users
            .filter(u => u.full_name.toLowerCase().includes(term) || u.email.toLowerCase().includes(term))
            .slice(0, 20);
    };

    const renderUserPicker = (fieldKey: string, label: string) => {
        const searchTerm = userSearchTerms[fieldKey] || '';
        const showDropdown = showUserDropdowns[fieldKey] || false;
        const selectedUserId = fieldValues[fieldKey];
        const selectedUser = selectedUserId ? users.find(u => u.user_id === selectedUserId) : null;

        return (
            <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <div className="relative">
                    <input
                        type="text"
                        placeholder="Search users..."
                        value={searchTerm}
                        onChange={(e) => {
                            setUserSearchTerms(prev => ({ ...prev, [fieldKey]: e.target.value }));
                            setShowUserDropdowns(prev => ({ ...prev, [fieldKey]: true }));
                        }}
                        onFocus={() => setShowUserDropdowns(prev => ({ ...prev, [fieldKey]: true }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    />
                    {showDropdown && (
                        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto">
                            <div
                                className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm text-gray-500 italic border-b"
                                onClick={() => handleUserSelect(fieldKey, null)}
                            >
                                Clear selection
                            </div>
                            {filteredUsers(searchTerm).map(user => (
                                <div
                                    key={user.user_id}
                                    className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                    onClick={() => handleUserSelect(fieldKey, user)}
                                >
                                    {user.full_name} ({user.email})
                                </div>
                            ))}
                            {filteredUsers(searchTerm).length === 0 && (
                                <div className="px-4 py-2 text-sm text-gray-500">No users found</div>
                            )}
                        </div>
                    )}
                </div>
                {selectedUser && (
                    <p className="mt-1 text-sm text-green-600">Selected: {selectedUser.full_name}</p>
                )}
            </div>
        );
    };

    const renderMultiUserPicker = () => {
        const selectedUserIds: number[] = fieldValues.user_ids || [];
        const searchTerm = userSearchTerms.user_ids || '';

        return (
            <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">Model Users</label>
                    <div className="flex items-center gap-2 text-sm">
                        <label className="flex items-center gap-1">
                            <input
                                type="radio"
                                name="user_ids_mode"
                                checked={multiSelectModes.user_ids === 'add'}
                                onChange={() => setMultiSelectModes(prev => ({ ...prev, user_ids: 'add' }))}
                            />
                            Add to existing
                        </label>
                        <label className="flex items-center gap-1">
                            <input
                                type="radio"
                                name="user_ids_mode"
                                checked={multiSelectModes.user_ids === 'replace'}
                                onChange={() => setMultiSelectModes(prev => ({ ...prev, user_ids: 'replace' }))}
                            />
                            Replace all
                        </label>
                    </div>
                </div>
                <input
                    type="text"
                    placeholder="Search users to add..."
                    value={searchTerm}
                    onChange={(e) => setUserSearchTerms(prev => ({ ...prev, user_ids: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 mb-2"
                />
                <div className="border border-gray-200 rounded-md max-h-48 overflow-y-auto">
                    {filteredUsers(searchTerm).map(user => (
                        <label
                            key={user.user_id}
                            className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer"
                        >
                            <input
                                type="checkbox"
                                checked={selectedUserIds.includes(user.user_id)}
                                onChange={() => handleMultiUserToggle(user.user_id)}
                            />
                            <span className="text-sm">{user.full_name} ({user.email})</span>
                        </label>
                    ))}
                </div>
                {selectedUserIds.length > 0 && (
                    <p className="mt-1 text-sm text-green-600">{selectedUserIds.length} user(s) selected</p>
                )}
            </div>
        );
    };

    const renderCategoryPicker = () => {
        const selectedCategoryIds: number[] = fieldValues.regulatory_category_ids || [];
        const categories = getRegulatoryCategories();

        return (
            <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">Regulatory Categories</label>
                    <div className="flex items-center gap-2 text-sm">
                        <label className="flex items-center gap-1">
                            <input
                                type="radio"
                                name="category_mode"
                                checked={multiSelectModes.regulatory_category_ids === 'add'}
                                onChange={() => setMultiSelectModes(prev => ({ ...prev, regulatory_category_ids: 'add' }))}
                            />
                            Add to existing
                        </label>
                        <label className="flex items-center gap-1">
                            <input
                                type="radio"
                                name="category_mode"
                                checked={multiSelectModes.regulatory_category_ids === 'replace'}
                                onChange={() => setMultiSelectModes(prev => ({ ...prev, regulatory_category_ids: 'replace' }))}
                            />
                            Replace all
                        </label>
                    </div>
                </div>
                <div className="border border-gray-200 rounded-md max-h-48 overflow-y-auto">
                    {categories.map(cat => (
                        <label
                            key={cat.value_id}
                            className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer"
                        >
                            <input
                                type="checkbox"
                                checked={selectedCategoryIds.includes(cat.value_id)}
                                onChange={() => handleCategoryToggle(cat.value_id)}
                            />
                            <span className="text-sm">{cat.label}</span>
                        </label>
                    ))}
                    {categories.length === 0 && (
                        <div className="px-3 py-2 text-sm text-gray-500">No regulatory categories available</div>
                    )}
                </div>
                {selectedCategoryIds.length > 0 && (
                    <p className="mt-1 text-sm text-green-600">{selectedCategoryIds.length} category(ies) selected</p>
                )}
            </div>
        );
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
                    <h3 className="text-lg font-bold">
                        {step === 1 ? 'Select Fields to Update' : 'Update Field Values'}
                    </h3>
                    <button
                        onClick={handleClose}
                        className="text-gray-400 hover:text-gray-600"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-6">
                    {/* Model count */}
                    <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                        <span className="text-sm text-blue-800">
                            {selectedModelIds.length} model{selectedModelIds.length !== 1 ? 's' : ''} selected
                        </span>
                    </div>

                    {loading ? (
                        <div className="text-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                            <p className="mt-2 text-gray-500">Loading...</p>
                        </div>
                    ) : (
                        <>
                            {error && (
                                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                                    {error}
                                </div>
                            )}

                            {/* Results display */}
                            {results && results.total_failed > 0 && (
                                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
                                    <p className="font-medium text-yellow-800 mb-2">
                                        {results.total_modified} succeeded, {results.total_failed} failed
                                    </p>
                                    <div className="max-h-32 overflow-y-auto">
                                        {results.results.filter(r => !r.success).map(r => (
                                            <p key={r.model_id} className="text-yellow-700 text-xs">
                                                {r.model_name || `Model ${r.model_id}`}: {r.error}
                                            </p>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Step 1: Field Selection */}
                            {step === 1 && (
                                <>
                                    <p className="text-sm text-gray-600 mb-4">
                                        Select the fields you want to update on the selected models:
                                    </p>

                                    {/* Group fields */}
                                    {['People', 'Text', 'Collections'].map(group => {
                                        const groupFields = BULK_UPDATE_FIELDS.filter(f => f.group === group);
                                        return (
                                            <div key={group} className="mb-4">
                                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                                                    {group}
                                                    {group === 'Collections' && (
                                                        <span className="font-normal normal-case ml-1">(can add or replace)</span>
                                                    )}
                                                </h4>
                                                <div className="border border-gray-200 rounded-md divide-y">
                                                    {groupFields.map(field => (
                                                        <label
                                                            key={field.key}
                                                            className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer"
                                                        >
                                                            <input
                                                                type="checkbox"
                                                                checked={selectedFields.has(field.key)}
                                                                onChange={() => toggleField(field.key)}
                                                            />
                                                            <span className="text-sm">{field.label}</span>
                                                        </label>
                                                    ))}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </>
                            )}

                            {/* Step 2: Field Values */}
                            {step === 2 && (
                                <>
                                    <p className="text-sm text-gray-600 mb-4">
                                        Provide values for the selected fields:
                                    </p>

                                    {Array.from(selectedFields).map(fieldKey => {
                                        const field = BULK_UPDATE_FIELDS.find(f => f.key === fieldKey);
                                        if (!field) return null;

                                        if (field.type === 'user_picker') {
                                            return (
                                                <div key={fieldKey}>
                                                    {renderUserPicker(fieldKey, field.label)}
                                                </div>
                                            );
                                        }

                                        if (field.type === 'multi_user_picker') {
                                            return (
                                                <div key={fieldKey}>
                                                    {renderMultiUserPicker()}
                                                </div>
                                            );
                                        }

                                        if (field.type === 'checkbox_list') {
                                            return (
                                                <div key={fieldKey}>
                                                    {renderCategoryPicker()}
                                                </div>
                                            );
                                        }

                                        if (field.type === 'textarea') {
                                            return (
                                                <div key={fieldKey} className="mb-4">
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        {field.label}
                                                    </label>
                                                    <textarea
                                                        value={fieldValues[fieldKey] || ''}
                                                        onChange={(e) => setFieldValues(prev => ({
                                                            ...prev,
                                                            [fieldKey]: e.target.value || null
                                                        }))}
                                                        placeholder="Enter value (leave empty to clear)"
                                                        rows={3}
                                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                                    />
                                                    <p className="mt-1 text-xs text-gray-500">
                                                        Leave empty to clear this field on all selected models.
                                                    </p>
                                                </div>
                                            );
                                        }

                                        return null;
                                    })}
                                </>
                            )}

                            {/* Actions */}
                            <div className="flex justify-between gap-3 mt-6 pt-4 border-t">
                                {step === 2 && (
                                    <button
                                        type="button"
                                        onClick={() => setStep(1)}
                                        className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
                                        disabled={submitting}
                                    >
                                        Back
                                    </button>
                                )}
                                <div className="flex gap-3 ml-auto">
                                    <button
                                        type="button"
                                        onClick={handleClose}
                                        className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
                                        disabled={submitting}
                                    >
                                        Cancel
                                    </button>
                                    {step === 1 ? (
                                        <button
                                            type="button"
                                            onClick={() => setStep(2)}
                                            disabled={selectedFields.size === 0}
                                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            Next
                                        </button>
                                    ) : (
                                        <button
                                            type="button"
                                            onClick={handleSubmit}
                                            disabled={submitting}
                                            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {submitting ? (
                                                <span className="flex items-center gap-2">
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                                    Updating...
                                                </span>
                                            ) : (
                                                `Update ${selectedModelIds.length} Model${selectedModelIds.length !== 1 ? 's' : ''}`
                                            )}
                                        </button>
                                    )}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

import { useState, useEffect } from 'react';
import { listCategories, listTags, bulkAssignTag, bulkRemoveTag, TagCategory, TagWithCategory, BulkTagResponse } from '../api/tags';
import TagBadge from './TagBadge';

interface Props {
    isOpen: boolean;
    mode: 'assign' | 'remove';
    selectedModelIds: number[];
    onClose: () => void;
    onSuccess: (message: string) => void;
}

export default function BulkTagModal({ isOpen, mode, selectedModelIds, onClose, onSuccess }: Props) {
    const [categories, setCategories] = useState<TagCategory[]>([]);
    const [tags, setTags] = useState<TagWithCategory[]>([]);
    const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
    const [selectedTagId, setSelectedTagId] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Load categories and tags on open
    useEffect(() => {
        if (isOpen) {
            loadData();
        }
    }, [isOpen]);

    const loadData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [categoriesData, tagsData] = await Promise.all([
                listCategories(),
                listTags({ is_active: true })
            ]);
            setCategories(categoriesData);
            setTags(tagsData);
        } catch (err) {
            setError('Failed to load tags');
        } finally {
            setLoading(false);
        }
    };

    // Filter tags by selected category
    const filteredTags = selectedCategoryId
        ? tags.filter(t => t.category_id === selectedCategoryId)
        : tags;

    // Get selected tag details
    const selectedTag = selectedTagId ? tags.find(t => t.tag_id === selectedTagId) : null;

    const handleSubmit = async () => {
        if (!selectedTagId) return;

        setSubmitting(true);
        setError(null);

        try {
            let result: BulkTagResponse;
            let message: string;

            if (mode === 'assign') {
                result = await bulkAssignTag(selectedTagId, selectedModelIds);
                const tagName = selectedTag?.name || 'tag';

                if (result.already_had_tag && result.already_had_tag > 0) {
                    message = `Tagged ${result.total_modified} model${result.total_modified !== 1 ? 's' : ''} with '${tagName}', ${result.already_had_tag} already had this tag`;
                } else {
                    message = `Tagged ${result.total_modified} model${result.total_modified !== 1 ? 's' : ''} with '${tagName}' successfully`;
                }
            } else {
                result = await bulkRemoveTag(selectedTagId, selectedModelIds);
                const tagName = selectedTag?.name || 'tag';

                if (result.did_not_have_tag && result.did_not_have_tag > 0) {
                    message = `Removed '${tagName}' tag from ${result.total_modified} model${result.total_modified !== 1 ? 's' : ''}, ${result.did_not_have_tag} did not have this tag`;
                } else {
                    message = `Removed '${tagName}' tag from ${result.total_modified} model${result.total_modified !== 1 ? 's' : ''} successfully`;
                }
            }

            onSuccess(message);
            handleClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || `Failed to ${mode} tag`);
        } finally {
            setSubmitting(false);
        }
    };

    const handleClose = () => {
        setSelectedCategoryId(null);
        setSelectedTagId(null);
        setError(null);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
                <h3 className="text-lg font-bold mb-4">
                    {mode === 'assign' ? 'Assign Tag to Models' : 'Remove Tag from Models'}
                </h3>

                <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                    <span className="text-sm text-blue-800">
                        {selectedModelIds.length} model{selectedModelIds.length !== 1 ? 's' : ''} selected
                    </span>
                </div>

                {loading ? (
                    <div className="text-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                        <p className="mt-2 text-gray-500">Loading tags...</p>
                    </div>
                ) : (
                    <>
                        {error && (
                            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                                {error}
                            </div>
                        )}

                        {/* Category Filter */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Category (optional filter)
                            </label>
                            <select
                                className="input-field"
                                value={selectedCategoryId || ''}
                                onChange={(e) => {
                                    const val = e.target.value ? parseInt(e.target.value) : null;
                                    setSelectedCategoryId(val);
                                    setSelectedTagId(null);
                                }}
                            >
                                <option value="">All Categories</option>
                                {categories.map(cat => (
                                    <option key={cat.category_id} value={cat.category_id}>
                                        {cat.name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Tag Selection */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Select Tag
                            </label>
                            <select
                                className="input-field"
                                value={selectedTagId || ''}
                                onChange={(e) => setSelectedTagId(e.target.value ? parseInt(e.target.value) : null)}
                            >
                                <option value="">-- Select a tag --</option>
                                {filteredTags.map(tag => (
                                    <option key={tag.tag_id} value={tag.tag_id}>
                                        {tag.category.name}: {tag.name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Tag Preview */}
                        {selectedTag && (
                            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm text-gray-600 mr-2">Preview:</span>
                                <TagBadge
                                    name={selectedTag.name}
                                    color={selectedTag.effective_color}
                                />
                                <span className="ml-2 text-xs text-gray-500">
                                    ({selectedTag.category.name})
                                </span>
                            </div>
                        )}

                        {/* Actions */}
                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                type="button"
                                onClick={handleClose}
                                className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
                                disabled={submitting}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={handleSubmit}
                                disabled={!selectedTagId || submitting}
                                className={`px-4 py-2 rounded text-white ${
                                    mode === 'assign'
                                        ? 'bg-blue-600 hover:bg-blue-700'
                                        : 'bg-red-600 hover:bg-red-700'
                                } disabled:opacity-50 disabled:cursor-not-allowed`}
                            >
                                {submitting ? (
                                    <span className="flex items-center gap-2">
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                        {mode === 'assign' ? 'Assigning...' : 'Removing...'}
                                    </span>
                                ) : (
                                    mode === 'assign' ? 'Assign Tag' : 'Remove Tag'
                                )}
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

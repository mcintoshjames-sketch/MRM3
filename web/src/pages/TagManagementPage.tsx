import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import TagBadge from '../components/TagBadge';
import {
  TagCategory,
  Tag,
  TagCategoryWithTags,
  listCategories,
  getCategory,
  createCategory,
  updateCategory,
  deleteCategory,
  createTag,
  updateTag,
  deleteTag,
  getTagUsageStatistics,
  TagUsageStatistics,
} from '../api/tags';
import { isValidHexColor, DEFAULT_TAG_COLOR } from '../utils/getContrastTextColor';

const TagManagementPage: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.capabilities?.is_admin;

  // State
  const [categories, setCategories] = useState<TagCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<TagCategoryWithTags | null>(null);
  const [statistics, setStatistics] = useState<TagUsageStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Modal state
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [showTagModal, setShowTagModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<TagCategory | null>(null);
  const [editingTag, setEditingTag] = useState<Tag | null>(null);

  // Form state for category
  const [categoryForm, setCategoryForm] = useState({
    name: '',
    description: '',
    color: DEFAULT_TAG_COLOR,
    sort_order: 0,
  });

  // Form state for tag
  const [tagForm, setTagForm] = useState({
    name: '',
    description: '',
    color: '',
    sort_order: 0,
    is_active: true,
  });

  // Fetch data
  const fetchCategories = useCallback(async () => {
    try {
      const data = await listCategories();
      setCategories(data);
      // Auto-select first category if none selected
      if (!selectedCategory && data.length > 0) {
        const categoryDetails = await getCategory(data[0].category_id);
        setSelectedCategory(categoryDetails);
      }
    } catch (err) {
      setError('Failed to load categories');
      console.error(err);
    }
  }, [selectedCategory]);

  const fetchStatistics = useCallback(async () => {
    try {
      const data = await getTagUsageStatistics();
      setStatistics(data);
    } catch (err) {
      console.error('Failed to load statistics:', err);
    }
  }, []);

  const loadCategoryDetails = useCallback(async (categoryId: number) => {
    try {
      const data = await getCategory(categoryId);
      setSelectedCategory(data);
    } catch (err) {
      setError('Failed to load category details');
      console.error(err);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchCategories(), fetchStatistics()]);
      setLoading(false);
    };
    init();
  }, [fetchCategories, fetchStatistics]);

  // Clear messages after 3 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  // Category handlers
  const handleOpenCategoryModal = (category?: TagCategory) => {
    if (category) {
      setEditingCategory(category);
      setCategoryForm({
        name: category.name,
        description: category.description || '',
        color: category.color,
        sort_order: category.sort_order,
      });
    } else {
      setEditingCategory(null);
      setCategoryForm({
        name: '',
        description: '',
        color: DEFAULT_TAG_COLOR,
        sort_order: categories.length + 1,
      });
    }
    setShowCategoryModal(true);
  };

  const handleSaveCategory = async () => {
    if (!categoryForm.name.trim()) {
      setError('Category name is required');
      return;
    }
    if (!isValidHexColor(categoryForm.color)) {
      setError('Invalid color format. Use #RRGGBB (e.g., #DC2626)');
      return;
    }

    try {
      if (editingCategory) {
        await updateCategory(editingCategory.category_id, categoryForm);
        setSuccessMessage('Category updated successfully');
      } else {
        await createCategory(categoryForm);
        setSuccessMessage('Category created successfully');
      }
      setShowCategoryModal(false);
      await fetchCategories();
      await fetchStatistics();
      if (selectedCategory) {
        await loadCategoryDetails(selectedCategory.category_id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save category');
    }
  };

  const handleDeleteCategory = async (category: TagCategory) => {
    if (category.is_system) {
      setError('Cannot delete system category');
      return;
    }
    if (!confirm(`Delete category "${category.name}"? This will also delete all tags in this category.`)) {
      return;
    }

    try {
      await deleteCategory(category.category_id);
      setSuccessMessage('Category deleted successfully');
      if (selectedCategory?.category_id === category.category_id) {
        setSelectedCategory(null);
      }
      await fetchCategories();
      await fetchStatistics();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete category');
    }
  };

  // Tag handlers
  const handleOpenTagModal = (tag?: Tag) => {
    if (tag) {
      setEditingTag(tag);
      setTagForm({
        name: tag.name,
        description: tag.description || '',
        color: tag.color || '',
        sort_order: tag.sort_order,
        is_active: tag.is_active,
      });
    } else {
      setEditingTag(null);
      setTagForm({
        name: '',
        description: '',
        color: '',
        sort_order: (selectedCategory?.tags.length || 0) + 1,
        is_active: true,
      });
    }
    setShowTagModal(true);
  };

  const handleSaveTag = async () => {
    if (!selectedCategory) {
      setError('No category selected');
      return;
    }
    if (!tagForm.name.trim()) {
      setError('Tag name is required');
      return;
    }
    if (tagForm.color && !isValidHexColor(tagForm.color)) {
      setError('Invalid color format. Use #RRGGBB (e.g., #DC2626) or leave empty for category color');
      return;
    }

    try {
      const data = {
        ...tagForm,
        color: tagForm.color || undefined,
        category_id: selectedCategory.category_id,
      };

      if (editingTag) {
        await updateTag(editingTag.tag_id, data);
        setSuccessMessage('Tag updated successfully');
      } else {
        await createTag(data as Parameters<typeof createTag>[0]);
        setSuccessMessage('Tag created successfully');
      }
      setShowTagModal(false);
      await loadCategoryDetails(selectedCategory.category_id);
      await fetchStatistics();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save tag');
    }
  };

  const handleDeleteTag = async (tag: Tag) => {
    if (!confirm(`Delete tag "${tag.name}"?`)) {
      return;
    }

    try {
      await deleteTag(tag.tag_id);
      setSuccessMessage('Tag deleted successfully');
      if (selectedCategory) {
        await loadCategoryDetails(selectedCategory.category_id);
      }
      await fetchStatistics();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete tag');
    }
  };

  if (!isAdmin) {
    return (
      <Layout>
        <div className="p-6">
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
            <p className="text-yellow-800">You do not have permission to manage tags. Contact an administrator.</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Tag Management</h1>
          <p className="mt-1 text-sm text-gray-500">
            Create and manage tag categories and tags for model categorization.
          </p>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
            {error}
          </div>
        )}
        {successMessage && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-md text-sm">
            {successMessage}
          </div>
        )}

        {/* Statistics */}
        {statistics && (
          <div className="mb-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="text-2xl font-bold text-gray-900">{statistics.total_categories}</div>
              <div className="text-sm text-gray-500">Categories</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="text-2xl font-bold text-gray-900">{statistics.total_tags}</div>
              <div className="text-sm text-gray-500">Total Tags</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="text-2xl font-bold text-gray-900">{statistics.total_active_tags}</div>
              <div className="text-sm text-gray-500">Active Tags</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="text-2xl font-bold text-gray-900">{statistics.total_model_associations}</div>
              <div className="text-sm text-gray-500">Model Tags</div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading...</div>
        ) : (
          <div className="flex gap-6">
            {/* Categories sidebar */}
            <div className="w-64 flex-shrink-0">
              <div className="bg-white rounded-lg border border-gray-200">
                <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                  <h2 className="font-semibold text-gray-900">Categories</h2>
                  <button
                    onClick={() => handleOpenCategoryModal()}
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    + Add
                  </button>
                </div>
                <div className="divide-y divide-gray-100">
                  {categories.map((category) => (
                    <button
                      key={category.category_id}
                      onClick={() => loadCategoryDetails(category.category_id)}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center justify-between group ${
                        selectedCategory?.category_id === category.category_id ? 'bg-blue-50' : ''
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        <span
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: category.color }}
                        />
                        <span className="text-sm font-medium text-gray-900">{category.name}</span>
                        <span className="text-xs text-gray-400">({category.tag_count})</span>
                      </span>
                      {!category.is_system && (
                        <span className="opacity-0 group-hover:opacity-100 flex gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenCategoryModal(category);
                            }}
                            className="text-gray-400 hover:text-blue-600 p-1"
                            title="Edit"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                            </svg>
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteCategory(category);
                            }}
                            className="text-gray-400 hover:text-red-600 p-1"
                            title="Delete"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </span>
                      )}
                    </button>
                  ))}
                  {categories.length === 0 && (
                    <div className="px-4 py-6 text-center text-gray-500 text-sm">
                      No categories yet. Click "+ Add" to create one.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Tags content */}
            <div className="flex-1">
              {selectedCategory ? (
                <div className="bg-white rounded-lg border border-gray-200">
                  <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                    <div>
                      <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                        <span
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: selectedCategory.color }}
                        />
                        {selectedCategory.name}
                      </h2>
                      {selectedCategory.description && (
                        <p className="text-sm text-gray-500 mt-0.5">{selectedCategory.description}</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleOpenTagModal()}
                      className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
                    >
                      + Add Tag
                    </button>
                  </div>

                  {/* Tags table */}
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tag</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Models</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {selectedCategory.tags.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="px-4 py-8 text-center text-gray-500 text-sm">
                              No tags in this category. Click "+ Add Tag" to create one.
                            </td>
                          </tr>
                        ) : (
                          selectedCategory.tags.map((tag) => (
                            <tr key={tag.tag_id} className="hover:bg-gray-50">
                              <td className="px-4 py-3">
                                <TagBadge
                                  name={tag.name}
                                  color={tag.effective_color}
                                  size="md"
                                />
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                                {tag.description || '-'}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-900">
                                {tag.model_count}
                              </td>
                              <td className="px-4 py-3">
                                <span
                                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                    tag.is_active
                                      ? 'bg-green-100 text-green-800'
                                      : 'bg-gray-100 text-gray-800'
                                  }`}
                                >
                                  {tag.is_active ? 'Active' : 'Inactive'}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-right">
                                <div className="flex justify-end gap-2">
                                  <button
                                    onClick={() => handleOpenTagModal(tag)}
                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                  >
                                    Edit
                                  </button>
                                  <button
                                    onClick={() => handleDeleteTag(tag)}
                                    className="text-red-600 hover:text-red-800 text-sm"
                                    disabled={tag.model_count > 0}
                                    title={tag.model_count > 0 ? 'Cannot delete tag that is in use' : 'Delete tag'}
                                  >
                                    Delete
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="bg-gray-50 rounded-lg border border-gray-200 p-12 text-center text-gray-500">
                  Select a category from the sidebar to view and manage its tags.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Category Modal */}
        {showCategoryModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">
                  {editingCategory ? 'Edit Category' : 'New Category'}
                </h3>
              </div>
              <div className="px-6 py-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                  <input
                    type="text"
                    value={categoryForm.name}
                    onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., Regulatory"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={categoryForm.description}
                    onChange={(e) => setCategoryForm({ ...categoryForm, description: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    rows={2}
                    placeholder="Optional description"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Color *</label>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={categoryForm.color}
                      onChange={(e) => setCategoryForm({ ...categoryForm, color: e.target.value.toUpperCase() })}
                      className="w-12 h-10 border border-gray-300 rounded cursor-pointer"
                    />
                    <input
                      type="text"
                      value={categoryForm.color}
                      onChange={(e) => setCategoryForm({ ...categoryForm, color: e.target.value.toUpperCase() })}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono"
                      placeholder="#DC2626"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Sort Order</label>
                  <input
                    type="number"
                    value={categoryForm.sort_order}
                    onChange={(e) => setCategoryForm({ ...categoryForm, sort_order: parseInt(e.target.value) || 0 })}
                    className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
              <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  onClick={() => setShowCategoryModal(false)}
                  className="px-4 py-2 text-gray-700 hover:text-gray-900"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveCategory}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  {editingCategory ? 'Save Changes' : 'Create Category'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tag Modal */}
        {showTagModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">
                  {editingTag ? 'Edit Tag' : 'New Tag'}
                </h3>
              </div>
              <div className="px-6 py-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                  <input
                    type="text"
                    value={tagForm.name}
                    onChange={(e) => setTagForm({ ...tagForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., CCAR 2025"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={tagForm.description}
                    onChange={(e) => setTagForm({ ...tagForm, description: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    rows={2}
                    placeholder="Optional description"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Color Override
                    <span className="font-normal text-gray-400 ml-1">(leave empty to use category color)</span>
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={tagForm.color || selectedCategory?.color || DEFAULT_TAG_COLOR}
                      onChange={(e) => setTagForm({ ...tagForm, color: e.target.value.toUpperCase() })}
                      className="w-12 h-10 border border-gray-300 rounded cursor-pointer"
                    />
                    <input
                      type="text"
                      value={tagForm.color}
                      onChange={(e) => setTagForm({ ...tagForm, color: e.target.value.toUpperCase() })}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono"
                      placeholder="Leave empty for category color"
                    />
                    {tagForm.color && (
                      <button
                        type="button"
                        onClick={() => setTagForm({ ...tagForm, color: '' })}
                        className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Sort Order</label>
                    <input
                      type="number"
                      value={tagForm.sort_order}
                      onChange={(e) => setTagForm({ ...tagForm, sort_order: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                    <select
                      value={tagForm.is_active ? 'active' : 'inactive'}
                      onChange={(e) => setTagForm({ ...tagForm, is_active: e.target.value === 'active' })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                    </select>
                  </div>
                </div>
                {/* Preview */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Preview</label>
                  <TagBadge
                    name={tagForm.name || 'Tag Name'}
                    color={tagForm.color || selectedCategory?.color || DEFAULT_TAG_COLOR}
                    size="md"
                  />
                </div>
              </div>
              <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  onClick={() => setShowTagModal(false)}
                  className="px-4 py-2 text-gray-700 hover:text-gray-900"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveTag}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  {editingTag ? 'Save Changes' : 'Create Tag'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default TagManagementPage;

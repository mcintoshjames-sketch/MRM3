import React, { useState, useEffect, useRef, useMemo } from 'react';
import { TagWithCategory, TagCategory, listTags, listCategories } from '../api/tags';
import TagBadge from './TagBadge';

export interface TagSelectorProps {
  /** Currently selected tag IDs */
  selectedTagIds: number[];
  /** Callback when selection changes */
  onChange: (tagIds: number[]) => void;
  /** Whether multi-select is enabled */
  multiple?: boolean;
  /** Placeholder text */
  placeholder?: string;
  /** Disable the selector */
  disabled?: boolean;
  /** Optional label */
  label?: string;
  /** Contact info for requesting new tags */
  adminContactInfo?: string;
}

interface GroupedTags {
  category: TagCategory;
  tags: TagWithCategory[];
}

/**
 * A searchable, multi-select tag dropdown grouped by category.
 *
 * Features:
 * - Type-ahead search filtering
 * - Tags grouped by category with collapsible sections
 * - "Don't see your tag?" footer with admin contact
 * - Selected tags shown as badges above the input
 */
const TagSelector: React.FC<TagSelectorProps> = ({
  selectedTagIds,
  onChange,
  multiple = true,
  placeholder = 'Search tags...',
  disabled = false,
  label,
  adminContactInfo = 'Contact your MRM Admin to request a new tag.',
}) => {
  const [tags, setTags] = useState<TagWithCategory[]>([]);
  const [_categories, setCategories] = useState<TagCategory[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState<Set<number>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch tags and categories on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [tagsData, categoriesData] = await Promise.all([
          listTags({ is_active: true }),
          listCategories(),
        ]);
        setTags(tagsData);
        setCategories(categoriesData);
        // Expand all categories by default
        setExpandedCategories(new Set(categoriesData.map((c) => c.category_id)));
      } catch (error) {
        console.error('Failed to fetch tags:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter tags based on search query
  const filteredTags = useMemo(() => {
    if (!searchQuery.trim()) return tags;
    const query = searchQuery.toLowerCase();
    return tags.filter(
      (tag) =>
        tag.name.toLowerCase().includes(query) ||
        tag.category.name.toLowerCase().includes(query)
    );
  }, [tags, searchQuery]);

  // Group filtered tags by category
  const groupedTags = useMemo((): GroupedTags[] => {
    const groups = new Map<number, GroupedTags>();

    filteredTags.forEach((tag) => {
      const categoryId = tag.category_id;
      if (!groups.has(categoryId)) {
        groups.set(categoryId, {
          category: tag.category,
          tags: [],
        });
      }
      groups.get(categoryId)!.tags.push(tag);
    });

    // Sort by category sort_order
    return Array.from(groups.values()).sort(
      (a, b) => a.category.sort_order - b.category.sort_order
    );
  }, [filteredTags]);

  // Get selected tags for display
  const selectedTags = useMemo(() => {
    return tags.filter((tag) => selectedTagIds.includes(tag.tag_id));
  }, [tags, selectedTagIds]);

  const handleTagSelect = (tagId: number) => {
    if (multiple) {
      if (selectedTagIds.includes(tagId)) {
        onChange(selectedTagIds.filter((id) => id !== tagId));
      } else {
        onChange([...selectedTagIds, tagId]);
      }
    } else {
      onChange([tagId]);
      setIsOpen(false);
    }
    setSearchQuery('');
  };

  const handleRemoveTag = (tagId: number) => {
    onChange(selectedTagIds.filter((id) => id !== tagId));
  };

  const toggleCategory = (categoryId: number) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  return (
    <div ref={containerRef} className="relative">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      )}

      {/* Selected tags display */}
      {selectedTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {selectedTags.map((tag) => (
            <TagBadge
              key={tag.tag_id}
              name={tag.name}
              color={tag.effective_color}
              onRemove={disabled ? undefined : () => handleRemoveTag(tag.tag_id)}
              size="sm"
            />
          ))}
        </div>
      )}

      {/* Search input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          placeholder={placeholder}
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          disabled={disabled}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          disabled={disabled}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          <svg
            className={`w-5 h-5 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Dropdown */}
      {isOpen && !disabled && (
        <div className="absolute z-20 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-80 overflow-y-auto">
          {loading ? (
            <div className="px-4 py-3 text-sm text-gray-500">Loading tags...</div>
          ) : groupedTags.length === 0 ? (
            <div className="px-4 py-3 text-sm text-gray-500">
              {searchQuery ? 'No tags match your search.' : 'No tags available.'}
            </div>
          ) : (
            <>
              {groupedTags.map(({ category, tags: categoryTags }) => (
                <div key={category.category_id} className="border-b border-gray-100 last:border-b-0">
                  {/* Category header */}
                  <button
                    type="button"
                    onClick={() => toggleCategory(category.category_id)}
                    className="w-full px-3 py-2 flex items-center justify-between text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    <span className="flex items-center gap-2">
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: category.color }}
                      />
                      {category.name}
                      <span className="text-xs text-gray-400">({categoryTags.length})</span>
                    </span>
                    <svg
                      className={`w-4 h-4 transition-transform ${
                        expandedCategories.has(category.category_id) ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {/* Tags in category */}
                  {expandedCategories.has(category.category_id) && (
                    <div className="pb-1">
                      {categoryTags.map((tag) => {
                        const isSelected = selectedTagIds.includes(tag.tag_id);
                        return (
                          <button
                            key={tag.tag_id}
                            type="button"
                            onClick={() => handleTagSelect(tag.tag_id)}
                            className={`w-full px-4 py-1.5 text-left text-sm flex items-center gap-2 hover:bg-gray-50 ${
                              isSelected ? 'bg-blue-50' : ''
                            }`}
                          >
                            {multiple && (
                              <span
                                className={`w-4 h-4 rounded border flex items-center justify-center ${
                                  isSelected
                                    ? 'bg-blue-600 border-blue-600 text-white'
                                    : 'border-gray-300'
                                }`}
                              >
                                {isSelected && (
                                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path
                                      fillRule="evenodd"
                                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                      clipRule="evenodd"
                                    />
                                  </svg>
                                )}
                              </span>
                            )}
                            <TagBadge name={tag.name} color={tag.effective_color} size="sm" />
                            {tag.model_count > 0 && (
                              <span className="text-xs text-gray-400 ml-auto">
                                {tag.model_count} models
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}

          {/* Footer with admin contact */}
          <div className="px-3 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
            Don't see the tag you need? {adminContactInfo}
          </div>
        </div>
      )}
    </div>
  );
};

export default TagSelector;

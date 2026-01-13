import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import TagBadge from '../components/TagBadge';
import client from '../api/client';
import {
    TagUsageStatistics,
    TagWithCategory,
    TagListItem,
    listTags,
    listCategories,
    getTagUsageStatistics,
    TagCategory,
} from '../api/tags';
import { useTableSort } from '../hooks/useTableSort';

interface ModelWithTags {
    model_id: number;
    model_name: string;
    description: string | null;
    development_type: string;
    status: string;
    owner: {
        user_id: number;
        full_name: string;
    };
    risk_tier: {
        label: string;
    } | null;
    tags: TagListItem[];
}

const ModelTagsReportPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [statistics, setStatistics] = useState<TagUsageStatistics | null>(null);
    const [models, setModels] = useState<ModelWithTags[]>([]);
    const [tags, setTags] = useState<TagWithCategory[]>([]);
    const [categories, setCategories] = useState<TagCategory[]>([]);

    // Filters
    const [categoryFilter, setCategoryFilter] = useState<string>('');
    const [tagFilter, setTagFilter] = useState<string>('');
    const [showUntaggedOnly, setShowUntaggedOnly] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [statsRes, modelsRes, tagsRes, categoriesRes] = await Promise.all([
                getTagUsageStatistics(),
                client.get('/models/'),
                listTags({ is_active: true }),
                listCategories(),
            ]);
            setStatistics(statsRes);
            setModels(modelsRes.data);
            setTags(tagsRes);
            setCategories(categoriesRes);
        } catch (error) {
            console.error('Failed to fetch report data:', error);
        } finally {
            setLoading(false);
        }
    };

    // Filter models based on selected criteria
    const filteredModels = useMemo(() => {
        return models.filter((model) => {
            // Show only untagged models
            if (showUntaggedOnly) {
                return !model.tags || model.tags.length === 0;
            }

            // Filter by category
            if (categoryFilter) {
                const categoryId = parseInt(categoryFilter, 10);
                const hasTagInCategory = model.tags?.some(
                    (t) => t.category_id === categoryId
                );
                if (!hasTagInCategory) return false;
            }

            // Filter by specific tag
            if (tagFilter) {
                const tagId = parseInt(tagFilter, 10);
                const hasTag = model.tags?.some((t) => t.tag_id === tagId);
                if (!hasTag) return false;
            }

            return true;
        });
    }, [models, categoryFilter, tagFilter, showUntaggedOnly]);

    // Table sorting
    const { sortedData, requestSort, getSortIcon } = useTableSort<ModelWithTags>(
        filteredModels,
        'model_name'
    );

    // Get available tags for selected category
    const filteredTagOptions = useMemo(() => {
        if (!categoryFilter) return tags;
        const categoryId = parseInt(categoryFilter, 10);
        return tags.filter((t) => t.category_id === categoryId);
    }, [tags, categoryFilter]);

    const exportToCsv = () => {
        if (sortedData.length === 0) return;

        const headers = [
            'Model ID',
            'Model Name',
            'Development Type',
            'Status',
            'Owner',
            'Risk Tier',
            'Tags',
            'Tag Categories',
        ];

        const rows = sortedData.map((model) => {
            const tagNames = model.tags?.map((t) => t.name).join('; ') || '';
            const tagCategories = [
                ...new Set(model.tags?.map((t) => t.category_name) || []),
            ].join('; ');

            return [
                model.model_id,
                `"${model.model_name.replace(/"/g, '""')}"`,
                model.development_type,
                model.status,
                `"${model.owner?.full_name || ''}"`,
                model.risk_tier?.label || '',
                `"${tagNames}"`,
                `"${tagCategories}"`,
            ].join(',');
        });

        const csvContent = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        const today = new Date().toISOString().split('T')[0];
        link.download = `model_tags_report_${today}.csv`;
        link.click();
    };

    // Calculate summary stats
    const summaryStats = useMemo(() => {
        const totalModels = models.length;
        const modelsWithTags = models.filter(
            (m) => m.tags && m.tags.length > 0
        ).length;
        const modelsWithoutTags = totalModels - modelsWithTags;
        const tagCoverage =
            totalModels > 0 ? ((modelsWithTags / totalModels) * 100).toFixed(1) : '0';

        return {
            totalModels,
            modelsWithTags,
            modelsWithoutTags,
            tagCoverage,
        };
    }, [models]);

    if (loading) {
        return (
            <Layout>
                <div className="p-6">
                    <div className="animate-pulse">
                        <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
                        <div className="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
                        <div className="grid grid-cols-4 gap-4 mb-6">
                            {[1, 2, 3, 4].map((i) => (
                                <div key={i} className="h-24 bg-gray-200 rounded"></div>
                            ))}
                        </div>
                        <div className="h-64 bg-gray-200 rounded"></div>
                    </div>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="p-6">
                {/* Header */}
                <div className="mb-6">
                    <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
                        <Link to="/reports" className="hover:text-blue-600">
                            Reports
                        </Link>
                        <span>/</span>
                        <span>Model Tags Report</span>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900">Model Tags Report</h2>
                    <p className="mt-2 text-sm text-gray-600">
                        Overview of model tagging across the inventory. Track tag usage,
                        identify untagged models, and export data for analysis.
                    </p>
                </div>

                {/* Summary Statistics */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    <div className="bg-white p-4 rounded-lg shadow border border-gray-200">
                        <div className="text-sm font-medium text-gray-500">Total Models</div>
                        <div className="text-2xl font-bold text-gray-900">
                            {summaryStats.totalModels}
                        </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow border border-gray-200">
                        <div className="text-sm font-medium text-gray-500">
                            Models with Tags
                        </div>
                        <div className="text-2xl font-bold text-green-600">
                            {summaryStats.modelsWithTags}
                        </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow border border-gray-200">
                        <div className="text-sm font-medium text-gray-500">
                            Models without Tags
                        </div>
                        <div className="text-2xl font-bold text-amber-600">
                            {summaryStats.modelsWithoutTags}
                        </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow border border-gray-200">
                        <div className="text-sm font-medium text-gray-500">Tag Coverage</div>
                        <div className="text-2xl font-bold text-blue-600">
                            {summaryStats.tagCoverage}%
                        </div>
                    </div>
                </div>

                {/* Tag Statistics by Category */}
                {statistics && statistics.tags_by_category.length > 0 && (
                    <div className="bg-white p-4 rounded-lg shadow border border-gray-200 mb-6">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">
                            Tag Usage by Category
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            {statistics.tags_by_category.map((cat) => (
                                <div
                                    key={cat.category_id}
                                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                                >
                                    <div
                                        className="w-4 h-4 rounded-full flex-shrink-0"
                                        style={{ backgroundColor: cat.category_color }}
                                    />
                                    <div className="flex-1 min-w-0">
                                        <div className="font-medium text-gray-900 truncate">
                                            {cat.category_name}
                                        </div>
                                        <div className="text-sm text-gray-500">
                                            {cat.tag_count} tags, {cat.model_associations} uses
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Filters */}
                <div className="bg-white p-4 rounded-lg shadow border border-gray-200 mb-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Category
                            </label>
                            <select
                                value={categoryFilter}
                                onChange={(e) => {
                                    setCategoryFilter(e.target.value);
                                    setTagFilter(''); // Reset tag filter when category changes
                                }}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
                            >
                                <option value="">All Categories</option>
                                {categories.map((cat) => (
                                    <option key={cat.category_id} value={cat.category_id}>
                                        {cat.name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Tag
                            </label>
                            <select
                                value={tagFilter}
                                onChange={(e) => setTagFilter(e.target.value)}
                                disabled={showUntaggedOnly}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm disabled:bg-gray-100"
                            >
                                <option value="">All Tags</option>
                                {filteredTagOptions.map((tag) => (
                                    <option key={tag.tag_id} value={tag.tag_id}>
                                        {categoryFilter ? tag.name : `${tag.category.name}: ${tag.name}`}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-transparent mb-1">
                                Option
                            </label>
                            <div className="flex items-center h-[38px]">
                                <input
                                    type="checkbox"
                                    id="show-untagged"
                                    checked={showUntaggedOnly}
                                    onChange={(e) => {
                                        setShowUntaggedOnly(e.target.checked);
                                        if (e.target.checked) {
                                            setCategoryFilter('');
                                            setTagFilter('');
                                        }
                                    }}
                                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                />
                                <label
                                    htmlFor="show-untagged"
                                    className="ml-2 text-sm font-medium text-gray-700"
                                >
                                    Show only untagged models
                                </label>
                            </div>
                        </div>

                        <div className="flex items-end gap-2">
                            <button
                                onClick={fetchData}
                                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm"
                            >
                                Refresh
                            </button>
                            <button
                                onClick={exportToCsv}
                                disabled={sortedData.length === 0}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm disabled:bg-gray-300 disabled:cursor-not-allowed"
                            >
                                Export CSV
                            </button>
                        </div>
                    </div>
                </div>

                {/* Results Summary */}
                <div className="flex justify-between items-center mb-4">
                    <div className="text-sm text-gray-600">
                        Showing <span className="font-semibold">{sortedData.length}</span> of{' '}
                        <span className="font-semibold">{models.length}</span> models
                    </div>
                    {(categoryFilter || tagFilter || showUntaggedOnly) && (
                        <button
                            onClick={() => {
                                setCategoryFilter('');
                                setTagFilter('');
                                setShowUntaggedOnly(false);
                            }}
                            className="text-sm text-blue-600 hover:text-blue-800"
                        >
                            Clear Filters
                        </button>
                    )}
                </div>

                {/* Models Table */}
                <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('model_name')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Model Name
                                            {getSortIcon('model_name')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('development_type')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Type
                                            {getSortIcon('development_type')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('status')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Status
                                            {getSortIcon('status')}
                                        </div>
                                    </th>
                                    <th
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                        onClick={() => requestSort('owner.full_name')}
                                    >
                                        <div className="flex items-center gap-2">
                                            Owner
                                            {getSortIcon('owner.full_name')}
                                        </div>
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Tags
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {sortedData.length === 0 ? (
                                    <tr>
                                        <td
                                            colSpan={6}
                                            className="px-6 py-8 text-center text-gray-500"
                                        >
                                            No models found matching the selected filters.
                                        </td>
                                    </tr>
                                ) : (
                                    sortedData.map((model) => (
                                        <tr key={model.model_id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4">
                                                <Link
                                                    to={`/models/${model.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                                >
                                                    {model.model_name}
                                                </Link>
                                                {model.description && (
                                                    <p className="text-xs text-gray-500 truncate max-w-xs mt-1">
                                                        {model.description}
                                                    </p>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-900">
                                                {model.development_type}
                                            </td>
                                            <td className="px-6 py-4">
                                                <span
                                                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                                        model.status === 'Active'
                                                            ? 'bg-green-100 text-green-800'
                                                            : model.status === 'Retired'
                                                            ? 'bg-gray-100 text-gray-800'
                                                            : 'bg-yellow-100 text-yellow-800'
                                                    }`}
                                                >
                                                    {model.status}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-900">
                                                {model.owner?.full_name || '-'}
                                            </td>
                                            <td className="px-6 py-4">
                                                {model.tags && model.tags.length > 0 ? (
                                                    <div className="flex flex-wrap gap-1">
                                                        {model.tags.map((tag) => (
                                                            <TagBadge
                                                                key={tag.tag_id}
                                                                name={tag.name}
                                                                color={tag.effective_color}
                                                                size="sm"
                                                            />
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <span className="text-gray-400 text-sm italic">
                                                        No tags
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4">
                                                <Link
                                                    to={`/models/${model.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                                >
                                                    View
                                                </Link>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Footer Info */}
                <div className="mt-6 text-sm text-gray-500">
                    Report generated at {new Date().toLocaleString()}
                </div>
            </div>
        </Layout>
    );
};

export default ModelTagsReportPage;

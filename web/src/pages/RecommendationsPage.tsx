import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { recommendationsApi, RecommendationListItem, TaxonomyValue } from '../api/recommendations';
import Layout from '../components/Layout';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import RecommendationCreateModal from '../components/RecommendationCreateModal';
import { useTableSort } from '../hooks/useTableSort';
import { useColumnPreferences, ColumnDefinition } from '../hooks/useColumnPreferences';
import { ColumnPickerModal, SaveViewModal } from '../components/ColumnPickerModal';
import { useAuth } from '../contexts/AuthContext';

interface Model {
    model_id: number;
    model_name: string;
}

interface User {
    user_id: number;
    email: string;
    full_name: string;
}

export default function RecommendationsPage() {
    const { user } = useAuth();
    const [searchParams] = useSearchParams();
    const [recommendations, setRecommendations] = useState<RecommendationListItem[]>([]);
    const [models, setModels] = useState<Model[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [priorities, setPriorities] = useState<TaxonomyValue[]>([]);
    const [statuses, setStatuses] = useState<TaxonomyValue[]>([]);
    const [categories, setCategories] = useState<TaxonomyValue[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showCreateModal, setShowCreateModal] = useState(false);

    // Read URL params for pre-filtering
    const urlModelId = searchParams.get('model_id');
    const urlValidationRequestId = searchParams.get('validation_request_id');

    // Filters
    const [filters, setFilters] = useState({
        search: '',
        status_filter: [] as string[],
        priority_filter: [] as string[],
        category_filter: [] as string[],
        model_id: urlModelId ? parseInt(urlModelId) : null as number | null,
        validation_request_id: urlValidationRequestId ? parseInt(urlValidationRequestId) : null as number | null,
        assigned_to_id: null as number | null,
        overdue_only: false
    });

    // Terminal statuses
    const terminalStatusCodes = ['REC_DROPPED', 'REC_CLOSED'];

    // Column customization configuration
    const availableColumns: ColumnDefinition[] = [
        { key: 'recommendation_code', label: 'Code', default: true },
        { key: 'title', label: 'Title', default: true },
        { key: 'model', label: 'Model', default: true },
        { key: 'priority', label: 'Priority', default: true },
        { key: 'current_status', label: 'Status', default: true },
        { key: 'category', label: 'Category', default: true },
        { key: 'assigned_to', label: 'Assigned To', default: true },
        { key: 'current_target_date', label: 'Target Date', default: true },
        { key: 'updated_at', label: 'Updated', default: true },
        { key: 'created_at', label: 'Created', default: false },
        { key: 'validation_request_id', label: 'Validation ID', default: false },
        { key: 'monitoring_cycle_id', label: 'Monitoring Cycle', default: false },
    ];

    const defaultViews = {
        'default': {
            id: 'default',
            name: 'Default View',
            columns: availableColumns.filter(col => col.default).map(col => col.key),
            isDefault: true
        },
        'compact': {
            id: 'compact',
            name: 'Compact View',
            columns: ['recommendation_code', 'title', 'current_status', 'priority', 'current_target_date'],
            isDefault: true
        },
        'full': {
            id: 'full',
            name: 'All Columns',
            columns: availableColumns.map(col => col.key),
            isDefault: true
        }
    };

    const columnPrefs = useColumnPreferences({
        entityType: 'recommendations',
        availableColumns,
        defaultViews,
    });

    // Apply filters
    const filteredRecommendations = recommendations.filter(rec => {
        // Search filter (code or title)
        if (filters.search) {
            const searchLower = filters.search.toLowerCase();
            const matchesCode = rec.recommendation_code.toLowerCase().includes(searchLower);
            const matchesTitle = rec.title.toLowerCase().includes(searchLower);
            const matchesModel = rec.model?.model_name?.toLowerCase().includes(searchLower);
            if (!matchesCode && !matchesTitle && !matchesModel) {
                return false;
            }
        }

        // Status filter
        if (filters.status_filter.length > 0) {
            const statusCode = rec.current_status?.code || '';
            if (!filters.status_filter.includes(statusCode)) {
                return false;
            }
        }

        // Priority filter
        if (filters.priority_filter.length > 0) {
            const priorityCode = rec.priority?.code || '';
            if (!filters.priority_filter.includes(priorityCode)) {
                return false;
            }
        }

        // Category filter
        if (filters.category_filter.length > 0) {
            const categoryCode = rec.category?.code || '';
            if (!filters.category_filter.includes(categoryCode)) {
                return false;
            }
        }

        // Model filter
        if (filters.model_id) {
            if (rec.model_id !== filters.model_id) {
                return false;
            }
        }

        // Validation request filter
        if (filters.validation_request_id) {
            if (rec.validation_request_id !== filters.validation_request_id) {
                return false;
            }
        }

        // Assigned to filter
        if (filters.assigned_to_id) {
            if (rec.assigned_to_id !== filters.assigned_to_id) {
                return false;
            }
        }

        // Overdue filter
        if (filters.overdue_only) {
            // Exclude terminal statuses
            if (terminalStatusCodes.includes(rec.current_status?.code || '')) {
                return false;
            }
            const targetDate = new Date(rec.current_target_date);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            if (targetDate >= today) {
                return false;
            }
        }

        return true;
    });

    // Table sorting
    const { sortedData, requestSort, getSortIcon } = useTableSort<RecommendationListItem>(
        filteredRecommendations,
        'updated_at',
        'desc'
    );

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch recommendations
            const recs = await recommendationsApi.list();
            setRecommendations(recs);

            // Fetch models for filter
            const modelsRes = await api.get('/models/');
            setModels(modelsRes.data);

            // Fetch users for filter
            const usersRes = await api.get('/auth/users');
            setUsers(usersRes.data);

            // Fetch taxonomies
            const taxonomiesRes = await api.get('/taxonomies/');
            const taxonomyList = taxonomiesRes.data;

            const taxDetails = await Promise.all(
                taxonomyList.map((t: any) => api.get(`/taxonomies/${t.taxonomy_id}`))
            );
            const taxonomies = taxDetails.map((r: any) => r.data);

            const priorityTax = taxonomies.find((t: any) => t.name === 'Recommendation Priority');
            const statusTax = taxonomies.find((t: any) => t.name === 'Recommendation Status');
            const categoryTax = taxonomies.find((t: any) => t.name === 'Recommendation Category');

            if (priorityTax) setPriorities(priorityTax.values || []);
            if (statusTax) setStatuses(statusTax.values || []);
            if (categoryTax) setCategories(categoryTax.values || []);
        } catch (err: any) {
            console.error('Failed to fetch data:', err);
            setError(err.response?.data?.detail || 'Failed to load recommendations');
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (code: string) => {
        switch (code) {
            case 'REC_DRAFT': return 'bg-gray-100 text-gray-800';
            case 'REC_PENDING_RESPONSE': return 'bg-blue-100 text-blue-800';
            case 'REC_PENDING_ACKNOWLEDGEMENT': return 'bg-indigo-100 text-indigo-800';
            case 'REC_IN_REBUTTAL': return 'bg-purple-100 text-purple-800';
            case 'REC_PENDING_ACTION_PLAN': return 'bg-yellow-100 text-yellow-800';
            case 'REC_PENDING_VALIDATOR_REVIEW': return 'bg-orange-100 text-orange-800';
            case 'REC_OPEN': return 'bg-green-100 text-green-800';
            case 'REC_REWORK_REQUIRED': return 'bg-red-100 text-red-800';
            case 'REC_PENDING_CLOSURE_REVIEW': return 'bg-cyan-100 text-cyan-800';
            case 'REC_PENDING_APPROVAL': return 'bg-amber-100 text-amber-800';
            case 'REC_CLOSED': return 'bg-emerald-100 text-emerald-800';
            case 'REC_DROPPED': return 'bg-gray-400 text-white';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getPriorityColor = (code: string) => {
        switch (code) {
            case 'HIGH': return 'bg-red-100 text-red-800';
            case 'MEDIUM': return 'bg-yellow-100 text-yellow-800';
            case 'LOW': return 'bg-green-100 text-green-800';
            case 'CONSIDERATION': return 'bg-blue-100 text-blue-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const isOverdue = (rec: RecommendationListItem) => {
        if (terminalStatusCodes.includes(rec.current_status?.code || '')) return false;
        const targetDate = new Date(rec.current_target_date);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return targetDate < today;
    };

    const getDaysOverdue = (rec: RecommendationListItem) => {
        const targetDate = new Date(rec.current_target_date);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const diffTime = today.getTime() - targetDate.getTime();
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    };

    // Column renderers for dynamic table
    const columnRenderers: Record<string, {
        header: string;
        sortKey?: string;
        cell: (rec: RecommendationListItem) => React.ReactNode;
        csvValue: (rec: RecommendationListItem) => string;
    }> = {
        recommendation_code: {
            header: 'Code',
            sortKey: 'recommendation_code',
            cell: (rec) => (
                <div className="flex items-center gap-1.5">
                    <Link
                        to={`/recommendations/${rec.recommendation_id}`}
                        className="font-mono text-blue-600 hover:text-blue-800 hover:underline"
                    >
                        {rec.recommendation_code}
                    </Link>
                    {rec.validation_request_id && (
                        <span
                            title="From Validation"
                            className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-600"
                        >
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </span>
                    )}
                    {rec.monitoring_cycle_id && (
                        <span
                            title="From Monitoring"
                            className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-purple-100 text-purple-600"
                        >
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                        </span>
                    )}
                </div>
            ),
            csvValue: (rec) => rec.recommendation_code
        },
        title: {
            header: 'Title',
            sortKey: 'title',
            cell: (rec) => (
                <div className="max-w-xs truncate" title={rec.title}>
                    {rec.title}
                </div>
            ),
            csvValue: (rec) => rec.title.replace(/"/g, '""')
        },
        model: {
            header: 'Model',
            sortKey: 'model.model_name',
            cell: (rec) => rec.model ? (
                <Link
                    to={`/models/${rec.model.model_id}`}
                    className="text-blue-600 hover:text-blue-800 hover:underline"
                >
                    {rec.model.model_name}
                </Link>
            ) : (
                <span className="text-gray-400">-</span>
            ),
            csvValue: (rec) => rec.model?.model_name || ''
        },
        priority: {
            header: 'Priority',
            sortKey: 'priority.label',
            cell: (rec) => (
                <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(rec.priority?.code || '')}`}>
                    {rec.priority?.label}
                </span>
            ),
            csvValue: (rec) => rec.priority?.label || ''
        },
        current_status: {
            header: 'Status',
            sortKey: 'current_status.label',
            cell: (rec) => (
                <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs rounded ${getStatusColor(rec.current_status?.code || '')}`}>
                        {rec.current_status?.label}
                    </span>
                    {isOverdue(rec) && (
                        <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-red-600 text-white" title={`${getDaysOverdue(rec)} days overdue`}>
                            OVERDUE
                        </span>
                    )}
                </div>
            ),
            csvValue: (rec) => isOverdue(rec) ? `${rec.current_status?.label || ''} (OVERDUE)` : (rec.current_status?.label || '')
        },
        category: {
            header: 'Category',
            cell: (rec) => rec.category?.label || <span className="text-gray-400">-</span>,
            csvValue: (rec) => rec.category?.label || ''
        },
        assigned_to: {
            header: 'Assigned To',
            sortKey: 'assigned_to.full_name',
            cell: (rec) => rec.assigned_to?.full_name || <span className="text-gray-400">Unassigned</span>,
            csvValue: (rec) => rec.assigned_to?.full_name || ''
        },
        current_target_date: {
            header: 'Target Date',
            sortKey: 'current_target_date',
            cell: (rec) => (
                <span className={isOverdue(rec) ? 'text-red-600 font-semibold' : ''}>
                    {rec.current_target_date}
                </span>
            ),
            csvValue: (rec) => rec.current_target_date
        },
        updated_at: {
            header: 'Updated',
            sortKey: 'updated_at',
            cell: (rec) => rec.updated_at.split('T')[0],
            csvValue: (rec) => rec.updated_at.split('T')[0]
        },
        created_at: {
            header: 'Created',
            sortKey: 'created_at',
            cell: (rec) => rec.created_at.split('T')[0],
            csvValue: (rec) => rec.created_at.split('T')[0]
        },
        validation_request_id: {
            header: 'Validation ID',
            sortKey: 'validation_request_id',
            cell: (rec) => rec.validation_request_id ? (
                <Link
                    to={`/validation-workflow/${rec.validation_request_id}`}
                    className="text-blue-600 hover:text-blue-800 hover:underline"
                >
                    #{rec.validation_request_id}
                </Link>
            ) : (
                <span className="text-gray-400">-</span>
            ),
            csvValue: (rec) => rec.validation_request_id ? `#${rec.validation_request_id}` : ''
        },
        monitoring_cycle_id: {
            header: 'Monitoring Cycle',
            sortKey: 'monitoring_cycle_id',
            cell: (rec) => rec.monitoring_cycle_id || <span className="text-gray-400">-</span>,
            csvValue: (rec) => rec.monitoring_cycle_id?.toString() || ''
        }
    };

    // CSV Export (uses selected columns)
    const exportToCSV = () => {
        if (columnPrefs.selectedColumns.length === 0) {
            alert('Please select at least one column to export.');
            return;
        }

        const headers = columnPrefs.selectedColumns
            .filter(colKey => columnRenderers[colKey])
            .map(colKey => columnRenderers[colKey].header);

        const rows = sortedData.map(rec => {
            const row: string[] = [];
            columnPrefs.selectedColumns.forEach(colKey => {
                const renderer = columnRenderers[colKey];
                let value = renderer ? renderer.csvValue(rec) : '';
                value = value.replace(/"/g, '""');
                if (value.includes(',') || value.includes('"') || value.includes('\n')) {
                    value = `"${value}"`;
                }
                row.push(value);
            });
            return row.join(',');
        });

        const csvContent = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `recommendations_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
    };

    const canCreate = user?.role === 'Admin' || user?.role === 'Validator';

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold">Recommendations</h2>
                    <p className="text-sm text-gray-600 mt-1">
                        Track and manage validation findings and remediation actions
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => columnPrefs.setShowColumnsModal(true)}
                        className="btn-secondary"
                    >
                        Columns ({columnPrefs.selectedColumns.length})
                    </button>
                    <button onClick={exportToCSV} className="btn-secondary">
                        Export CSV
                    </button>
                    {canCreate && (
                        <button onClick={() => setShowCreateModal(true)} className="btn-primary">
                            + New Recommendation
                        </button>
                    )}
                </div>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            {/* Filters */}
            <div className="bg-white p-4 rounded-lg shadow-md mb-6">
                <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
                    {/* Search */}
                    <div>
                        <label htmlFor="filter-search" className="block text-xs font-medium text-gray-700 mb-1">
                            Search
                        </label>
                        <input
                            id="filter-search"
                            type="text"
                            className="input-field text-sm"
                            placeholder="Code, title, model..."
                            value={filters.search}
                            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                        />
                    </div>

                    {/* Status */}
                    <MultiSelectDropdown
                        label="Status"
                        placeholder="All Statuses"
                        options={statuses.map(s => ({ value: s.code, label: s.label }))}
                        selectedValues={filters.status_filter}
                        onChange={(values) => setFilters({ ...filters, status_filter: values as string[] })}
                    />

                    {/* Priority */}
                    <MultiSelectDropdown
                        label="Priority"
                        placeholder="All Priorities"
                        options={priorities.map(p => ({ value: p.code, label: p.label }))}
                        selectedValues={filters.priority_filter}
                        onChange={(values) => setFilters({ ...filters, priority_filter: values as string[] })}
                    />

                    {/* Category */}
                    <MultiSelectDropdown
                        label="Category"
                        placeholder="All Categories"
                        options={categories.map(c => ({ value: c.code, label: c.label }))}
                        selectedValues={filters.category_filter}
                        onChange={(values) => setFilters({ ...filters, category_filter: values as string[] })}
                    />

                    {/* Model */}
                    <div>
                        <label htmlFor="filter-model" className="block text-xs font-medium text-gray-700 mb-1">
                            Model
                        </label>
                        <select
                            id="filter-model"
                            className="input-field text-sm"
                            value={filters.model_id || ''}
                            onChange={(e) => setFilters({ ...filters, model_id: e.target.value ? parseInt(e.target.value) : null })}
                        >
                            <option value="">All Models</option>
                            {models.map(m => (
                                <option key={m.model_id} value={m.model_id}>{m.model_name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Assigned To */}
                    <div>
                        <label htmlFor="filter-assigned" className="block text-xs font-medium text-gray-700 mb-1">
                            Assigned To
                        </label>
                        <select
                            id="filter-assigned"
                            className="input-field text-sm"
                            value={filters.assigned_to_id || ''}
                            onChange={(e) => setFilters({ ...filters, assigned_to_id: e.target.value ? parseInt(e.target.value) : null })}
                        >
                            <option value="">All Users</option>
                            {users.map(u => (
                                <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Overdue Filter */}
                <div className="mt-3 flex items-center">
                    <label className="flex items-center cursor-pointer">
                        <input
                            type="checkbox"
                            className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                            checked={filters.overdue_only}
                            onChange={(e) => setFilters({ ...filters, overdue_only: e.target.checked })}
                        />
                        <span className="ml-2 text-sm font-medium text-gray-700">
                            Show overdue only
                        </span>
                        {filters.overdue_only && (
                            <span className="ml-2 px-1.5 py-0.5 text-xs font-medium rounded bg-red-600 text-white">
                                OVERDUE
                            </span>
                        )}
                    </label>
                </div>

                {/* Clear Filters and Results Count */}
                <div className="flex items-center justify-between mt-3 pt-3 border-t">
                    <div className="text-sm text-gray-600">
                        Showing <span className="font-semibold">{filteredRecommendations.length}</span> of{' '}
                        <span className="font-semibold">{recommendations.length}</span> recommendations
                    </div>
                    <button
                        onClick={() => setFilters({
                            search: '',
                            status_filter: [],
                            priority_filter: [],
                            category_filter: [],
                            model_id: null,
                            validation_request_id: null,
                            assigned_to_id: null,
                            overdue_only: false
                        })}
                        className="text-sm text-blue-600 hover:text-blue-800"
                    >
                        Clear Filters
                    </button>
                </div>
            </div>

            {/* Dynamic Table */}
            <div className="bg-white rounded-lg shadow-md overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            {columnPrefs.selectedColumns.map(colKey => {
                                const renderer = columnRenderers[colKey];
                                if (!renderer) return null;
                                return (
                                    <th
                                        key={colKey}
                                        className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase ${renderer.sortKey ? 'cursor-pointer hover:bg-gray-100' : ''}`}
                                        onClick={() => renderer.sortKey && requestSort(renderer.sortKey)}
                                    >
                                        <div className="flex items-center gap-2">
                                            {renderer.header}
                                            {renderer.sortKey && getSortIcon(renderer.sortKey)}
                                        </div>
                                    </th>
                                );
                            })}
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedData.length === 0 ? (
                            <tr>
                                <td colSpan={columnPrefs.selectedColumns.length} className="px-6 py-4 text-center text-gray-500">
                                    No recommendations found.
                                    {canCreate && ' Click "New Recommendation" to create one.'}
                                </td>
                            </tr>
                        ) : (
                            sortedData.map((rec) => (
                                <tr key={rec.recommendation_id} className="hover:bg-gray-50">
                                    {columnPrefs.selectedColumns.map(colKey => {
                                        const renderer = columnRenderers[colKey];
                                        if (!renderer) return null;
                                        return (
                                            <td key={colKey} className="px-6 py-4 whitespace-nowrap text-sm">
                                                {renderer.cell(rec)}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Create Modal */}
            {showCreateModal && (
                <RecommendationCreateModal
                    onClose={() => setShowCreateModal(false)}
                    onCreated={() => {
                        setShowCreateModal(false);
                        fetchData();
                    }}
                    models={models}
                    users={users}
                    priorities={priorities}
                    categories={categories}
                    preselectedModelId={filters.model_id || undefined}
                    preselectedValidationRequestId={filters.validation_request_id || undefined}
                />
            )}

            {/* Column Picker Modal */}
            <ColumnPickerModal
                isOpen={columnPrefs.showColumnsModal}
                onClose={() => columnPrefs.setShowColumnsModal(false)}
                availableColumns={availableColumns}
                selectedColumns={columnPrefs.selectedColumns}
                toggleColumn={columnPrefs.toggleColumn}
                selectAllColumns={columnPrefs.selectAllColumns}
                deselectAllColumns={columnPrefs.deselectAllColumns}
                currentViewId={columnPrefs.currentViewId}
                allViews={columnPrefs.allViews}
                loadView={columnPrefs.loadView}
                onSaveAsNew={() => {
                    columnPrefs.setEditingViewId(null);
                    columnPrefs.setNewViewName('');
                    columnPrefs.setNewViewDescription('');
                    columnPrefs.setNewViewIsPublic(false);
                    columnPrefs.setShowSaveViewModal(true);
                }}
            />

            {/* Save View Modal */}
            <SaveViewModal
                isOpen={columnPrefs.showSaveViewModal}
                onClose={() => columnPrefs.setShowSaveViewModal(false)}
                onSave={columnPrefs.saveView}
                viewName={columnPrefs.newViewName}
                setViewName={columnPrefs.setNewViewName}
                viewDescription={columnPrefs.newViewDescription}
                setViewDescription={columnPrefs.setNewViewDescription}
                isPublic={columnPrefs.newViewIsPublic}
                setIsPublic={columnPrefs.setNewViewIsPublic}
                isEditing={columnPrefs.editingViewId !== null}
            />
        </Layout>
    );
}

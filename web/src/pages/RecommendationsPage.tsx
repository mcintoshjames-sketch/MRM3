import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { recommendationsApi, RecommendationListItem, TaxonomyValue } from '../api/recommendations';
import Layout from '../components/Layout';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import RecommendationCreateModal from '../components/RecommendationCreateModal';
import { useTableSort } from '../hooks/useTableSort';
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

    // CSV Export
    const exportToCSV = () => {
        const headers = [
            'Code',
            'Title',
            'Model',
            'Priority',
            'Status',
            'Category',
            'Assigned To',
            'Target Date',
            'Created At',
            'Updated At'
        ];

        const rows = sortedData.map(rec => [
            rec.recommendation_code,
            `"${rec.title.replace(/"/g, '""')}"`,
            rec.model?.model_name || '',
            rec.priority?.label || '',
            rec.current_status?.label || '',
            rec.category?.label || '',
            rec.assigned_to?.full_name || '',
            rec.current_target_date,
            rec.created_at.split('T')[0],
            rec.updated_at.split('T')[0]
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `recommendations_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
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

            {/* Table */}
            <div className="bg-white rounded-lg shadow-md overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('recommendation_code')}
                            >
                                <div className="flex items-center gap-2">
                                    Code
                                    {getSortIcon('recommendation_code')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('title')}
                            >
                                <div className="flex items-center gap-2">
                                    Title
                                    {getSortIcon('title')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('model.model_name')}
                            >
                                <div className="flex items-center gap-2">
                                    Model
                                    {getSortIcon('model.model_name')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('priority.label')}
                            >
                                <div className="flex items-center gap-2">
                                    Priority
                                    {getSortIcon('priority.label')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('current_status.label')}
                            >
                                <div className="flex items-center gap-2">
                                    Status
                                    {getSortIcon('current_status.label')}
                                </div>
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Category
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('assigned_to.full_name')}
                            >
                                <div className="flex items-center gap-2">
                                    Assigned To
                                    {getSortIcon('assigned_to.full_name')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('current_target_date')}
                            >
                                <div className="flex items-center gap-2">
                                    Target Date
                                    {getSortIcon('current_target_date')}
                                </div>
                            </th>
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                onClick={() => requestSort('updated_at')}
                            >
                                <div className="flex items-center gap-2">
                                    Updated
                                    {getSortIcon('updated_at')}
                                </div>
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedData.length === 0 ? (
                            <tr>
                                <td colSpan={9} className="px-6 py-4 text-center text-gray-500">
                                    No recommendations found.
                                    {canCreate && ' Click "New Recommendation" to create one.'}
                                </td>
                            </tr>
                        ) : (
                            sortedData.map((rec) => (
                                <tr key={rec.recommendation_id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
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
                                    </td>
                                    <td className="px-6 py-4 text-sm">
                                        <div className="max-w-xs truncate" title={rec.title}>
                                            {rec.title}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        <Link
                                            to={`/models/${rec.model_id}`}
                                            className="text-blue-600 hover:text-blue-800 hover:underline"
                                        >
                                            {rec.model?.model_name}
                                        </Link>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(rec.priority?.code || '')}`}>
                                            {rec.priority?.label}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
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
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                        {rec.category?.label || '-'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {rec.assigned_to?.full_name || <span className="text-gray-400">Unassigned</span>}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        <span className={isOverdue(rec) ? 'text-red-600 font-semibold' : ''}>
                                            {rec.current_target_date}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                        {rec.updated_at.split('T')[0]}
                                    </td>
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
        </Layout>
    );
}

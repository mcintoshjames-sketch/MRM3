import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import {
    exceptionsApi,
    ModelExceptionListItem,
    ModelExceptionDetail,
    TaxonomyValueBrief,
    ExceptionSummary,
    EXCEPTION_TYPE_LABELS,
    EXCEPTION_STATUS_CONFIG,
    CreateExceptionRequest,
} from '../api/exceptions';
import api from '../api/client';

const ExceptionsReportPage: React.FC = () => {
    const { user } = useAuth();
    const isAdmin = user?.role === 'Admin';

    // State
    const [loading, setLoading] = useState(true);
    const [exceptions, setExceptions] = useState<ModelExceptionListItem[]>([]);
    const [summary, setSummary] = useState<ExceptionSummary | null>(null);
    const [total, setTotal] = useState(0);

    // Filters
    const [statusFilter, setStatusFilter] = useState<string>('');
    const [typeFilter, setTypeFilter] = useState<string>('');
    const [regionFilter, setRegionFilter] = useState<number | null>(null);

    // Regions for filter
    const [regions, setRegions] = useState<{ region_id: number; code: string; name: string }[]>([]);

    // Pagination
    const [skip, setSkip] = useState(0);
    const limit = 50;

    // Detail modal state
    const [selectedExceptionId, setSelectedExceptionId] = useState<number | null>(null);
    const [exceptionDetail, setExceptionDetail] = useState<ModelExceptionDetail | null>(null);
    const [detailLoading, setDetailLoading] = useState(false);

    // Acknowledge modal state
    const [showAcknowledgeModal, setShowAcknowledgeModal] = useState(false);
    const [acknowledgeNotes, setAcknowledgeNotes] = useState('');
    const [acknowledgeLoading, setAcknowledgeLoading] = useState(false);

    // Close modal state
    const [showCloseModal, setShowCloseModal] = useState(false);
    const [closureNarrative, setClosureNarrative] = useState('');
    const [closureReasonId, setClosureReasonId] = useState<number | null>(null);
    const [closureReasons, setClosureReasons] = useState<TaxonomyValueBrief[]>([]);
    const [closeLoading, setCloseLoading] = useState(false);

    // Detect all modal state
    const [showDetectModal, setShowDetectModal] = useState(false);
    const [detectLoading, setDetectLoading] = useState(false);
    const [detectResult, setDetectResult] = useState<{ type1_count: number; type2_count: number; type3_count: number; total_created: number } | null>(null);

    // Create exception modal state
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [createLoading, setCreateLoading] = useState(false);
    const [createModelId, setCreateModelId] = useState<number | null>(null);
    const [createExceptionType, setCreateExceptionType] = useState<string>('');
    const [createDescription, setCreateDescription] = useState('');
    const [createInitialStatus, setCreateInitialStatus] = useState<'OPEN' | 'ACKNOWLEDGED'>('OPEN');
    const [createAcknowledgmentNotes, setCreateAcknowledgmentNotes] = useState('');
    const [createError, setCreateError] = useState<string | null>(null);

    // Model search for create modal
    const [models, setModels] = useState<{ model_id: number; model_name: string; model_code: string | null }[]>([]);
    const [modelSearchQuery, setModelSearchQuery] = useState('');
    const [showModelDropdown, setShowModelDropdown] = useState(false);

    // Fetch exceptions
    const fetchExceptions = useCallback(async () => {
        try {
            setLoading(true);
            const response = await exceptionsApi.list({
                status: statusFilter || undefined,
                exception_type: typeFilter || undefined,
                region_id: regionFilter || undefined,
                skip,
                limit,
            });
            setExceptions(response.items);
            setTotal(response.total);
        } catch (error) {
            console.error('Failed to fetch exceptions:', error);
        } finally {
            setLoading(false);
        }
    }, [statusFilter, typeFilter, regionFilter, skip, limit]);

    // Fetch regions for filter
    const fetchRegions = useCallback(async () => {
        try {
            const response = await api.get('/regions/');
            setRegions(response.data);
        } catch (error) {
            console.error('Failed to fetch regions:', error);
        }
    }, []);

    // Fetch summary
    const fetchSummary = useCallback(async () => {
        try {
            const summaryData = await exceptionsApi.getSummary();
            setSummary(summaryData);
        } catch (error) {
            console.error('Failed to fetch summary:', error);
        }
    }, []);

    // Fetch closure reasons
    const fetchClosureReasons = useCallback(async () => {
        try {
            const reasons = await exceptionsApi.getClosureReasons();
            setClosureReasons(reasons);
        } catch (error) {
            console.error('Failed to fetch closure reasons:', error);
        }
    }, []);

    // Fetch models for create modal
    const fetchModels = useCallback(async () => {
        try {
            const response = await api.get('/models/', { params: { limit: 1000, exclude_sub_models: true } });
            setModels(response.data.items || []);
        } catch (error) {
            console.error('Failed to fetch models:', error);
        }
    }, []);

    useEffect(() => {
        fetchExceptions();
        fetchSummary();
        fetchClosureReasons();
        fetchRegions();
    }, [fetchExceptions, fetchSummary, fetchClosureReasons, fetchRegions]);

    // Fetch models when create modal opens
    useEffect(() => {
        if (showCreateModal && models.length === 0) {
            fetchModels();
        }
    }, [showCreateModal, models.length, fetchModels]);

    // Fetch exception detail
    const fetchExceptionDetail = async (id: number) => {
        try {
            setDetailLoading(true);
            const detail = await exceptionsApi.get(id);
            setExceptionDetail(detail);
        } catch (error) {
            console.error('Failed to fetch exception detail:', error);
        } finally {
            setDetailLoading(false);
        }
    };

    // Handle opening detail modal
    const handleOpenDetail = (id: number) => {
        setSelectedExceptionId(id);
        fetchExceptionDetail(id);
    };

    // Handle closing detail modal
    const handleCloseDetail = () => {
        setSelectedExceptionId(null);
        setExceptionDetail(null);
    };

    // Handle acknowledge
    const handleAcknowledge = async () => {
        if (!exceptionDetail) return;
        try {
            setAcknowledgeLoading(true);
            await exceptionsApi.acknowledge(exceptionDetail.exception_id, {
                notes: acknowledgeNotes || undefined,
            });
            setShowAcknowledgeModal(false);
            setAcknowledgeNotes('');
            fetchExceptions();
            fetchSummary();
            fetchExceptionDetail(exceptionDetail.exception_id);
        } catch (error) {
            console.error('Failed to acknowledge exception:', error);
        } finally {
            setAcknowledgeLoading(false);
        }
    };

    // Handle close
    const handleClose = async () => {
        if (!exceptionDetail || !closureReasonId) return;
        try {
            setCloseLoading(true);
            await exceptionsApi.close(exceptionDetail.exception_id, {
                closure_narrative: closureNarrative,
                closure_reason_id: closureReasonId,
            });
            setShowCloseModal(false);
            setClosureNarrative('');
            setClosureReasonId(null);
            fetchExceptions();
            fetchSummary();
            fetchExceptionDetail(exceptionDetail.exception_id);
        } catch (error) {
            console.error('Failed to close exception:', error);
        } finally {
            setCloseLoading(false);
        }
    };

    // Handle detect all
    const handleDetectAll = async () => {
        try {
            setDetectLoading(true);
            const result = await exceptionsApi.detectAll();
            setDetectResult(result);
            fetchExceptions();
            fetchSummary();
        } catch (error) {
            console.error('Failed to detect exceptions:', error);
        } finally {
            setDetectLoading(false);
        }
    };

    // Handle create exception
    const handleCreateException = async () => {
        if (!createModelId || !createExceptionType || createDescription.length < 10) {
            setCreateError('Please fill in all required fields');
            return;
        }

        try {
            setCreateLoading(true);
            setCreateError(null);

            const request: CreateExceptionRequest = {
                model_id: createModelId,
                exception_type: createExceptionType,
                description: createDescription,
                initial_status: createInitialStatus,
            };

            if (createInitialStatus === 'ACKNOWLEDGED' && createAcknowledgmentNotes) {
                request.acknowledgment_notes = createAcknowledgmentNotes;
            }

            await exceptionsApi.create(request);

            // Reset form and close modal
            setShowCreateModal(false);
            resetCreateForm();

            // Refresh data
            fetchExceptions();
            fetchSummary();
        } catch (error: unknown) {
            console.error('Failed to create exception:', error);
            const errMsg = error instanceof Error ? error.message : 'Failed to create exception';
            setCreateError(errMsg);
        } finally {
            setCreateLoading(false);
        }
    };

    // Reset create form
    const resetCreateForm = () => {
        setCreateModelId(null);
        setCreateExceptionType('');
        setCreateDescription('');
        setCreateInitialStatus('OPEN');
        setCreateAcknowledgmentNotes('');
        setCreateError(null);
        setModelSearchQuery('');
        setShowModelDropdown(false);
    };

    // Filter models for searchable dropdown
    const filteredModels = models.filter((model) =>
        model.model_name.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
        (model.model_code && model.model_code.toLowerCase().includes(modelSearchQuery.toLowerCase()))
    ).slice(0, 50);

    // Get selected model name for display
    const selectedModelName = createModelId
        ? models.find((m) => m.model_id === createModelId)?.model_name || ''
        : '';

    // CSV export
    const exportToCsv = () => {
        if (exceptions.length === 0) return;

        const headers = [
            'Exception Code',
            'Model ID',
            'Model Name',
            'Exception Type',
            'Status',
            'Description',
            'Detected At',
            'Acknowledged At',
            'Closed At',
            'Auto-Closed',
        ];

        const rows = exceptions.map((exc) => [
            exc.exception_code,
            exc.model_id,
            exc.model.model_name,
            EXCEPTION_TYPE_LABELS[exc.exception_type] || exc.exception_type,
            exc.status,
            exc.description,
            exc.detected_at?.split('T')[0] || '',
            exc.acknowledged_at?.split('T')[0] || '',
            exc.closed_at?.split('T')[0] || '',
            exc.auto_closed ? 'Yes' : 'No',
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `exceptions_report_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // Status badge
    const getStatusBadge = (status: string) => {
        const config = EXCEPTION_STATUS_CONFIG[status] || {
            label: status,
            color: 'text-gray-800',
            bgColor: 'bg-gray-100',
        };
        return (
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.color}`}>
                {config.label}
            </span>
        );
    };

    // Pagination
    const handlePrevPage = () => {
        if (skip > 0) setSkip(Math.max(0, skip - limit));
    };

    const handleNextPage = () => {
        if (skip + limit < total) setSkip(skip + limit);
    };

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex justify-between items-start">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">Model Exceptions Report</h2>
                        <p className="text-sm text-gray-600 mt-1">
                            Track and manage model exceptions including unmitigated performance issues, out-of-scope usage, and pre-validation deployments.
                        </p>
                    </div>
                    <div className="flex gap-2">
                        {isAdmin && (
                            <button
                                onClick={() => {
                                    setDetectResult(null);
                                    setShowDetectModal(true);
                                }}
                                className="btn-secondary"
                            >
                                Detect All Exceptions
                            </button>
                        )}
                        {isAdmin && (
                            <button
                                onClick={() => {
                                    resetCreateForm();
                                    setShowCreateModal(true);
                                }}
                                className="btn-primary"
                            >
                                + Create Exception
                            </button>
                        )}
                        <button
                            onClick={exportToCsv}
                            className="btn-secondary"
                            disabled={exceptions.length === 0}
                        >
                            Export CSV
                        </button>
                        <button
                            onClick={() => {
                                fetchExceptions();
                                fetchSummary();
                            }}
                            className="btn-primary"
                        >
                            Refresh Report
                        </button>
                    </div>
                </div>

                {/* Summary Cards */}
                {summary && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="bg-white p-4 rounded-lg shadow-md border-l-4 border-red-500">
                            <p className="text-sm text-gray-600">Open Exceptions</p>
                            <p className="text-2xl font-bold text-red-600">{summary.total_open}</p>
                        </div>
                        <div className="bg-white p-4 rounded-lg shadow-md border-l-4 border-yellow-500">
                            <p className="text-sm text-gray-600">Acknowledged</p>
                            <p className="text-2xl font-bold text-yellow-600">{summary.total_acknowledged}</p>
                        </div>
                        <div className="bg-white p-4 rounded-lg shadow-md border-l-4 border-green-500">
                            <p className="text-sm text-gray-600">Closed</p>
                            <p className="text-2xl font-bold text-green-600">{summary.total_closed}</p>
                        </div>
                        <div className="bg-white p-4 rounded-lg shadow-md border-l-4 border-blue-500">
                            <p className="text-sm text-gray-600">Total Exceptions</p>
                            <p className="text-2xl font-bold text-blue-600">
                                {summary.total_open + summary.total_acknowledged + summary.total_closed}
                            </p>
                        </div>
                    </div>
                )}

                {/* By Type Summary */}
                {summary && Object.keys(summary.by_type).length > 0 && (
                    <div className="bg-white p-4 rounded-lg shadow-md">
                        <h3 className="text-sm font-medium text-gray-700 mb-3">Exceptions by Type</h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {Object.entries(summary.by_type).map(([type, count]) => (
                                <div key={type} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                                    <span className="text-sm text-gray-700">
                                        {EXCEPTION_TYPE_LABELS[type] || type}
                                    </span>
                                    <span className="text-sm font-semibold text-gray-900">{count}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Filters */}
                <div className="bg-white p-4 rounded-lg shadow-md">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Filter by Status
                            </label>
                            <select
                                value={statusFilter}
                                onChange={(e) => {
                                    setStatusFilter(e.target.value);
                                    setSkip(0);
                                }}
                                className="input-field"
                            >
                                <option value="">All Statuses</option>
                                <option value="OPEN">Open</option>
                                <option value="ACKNOWLEDGED">Acknowledged</option>
                                <option value="CLOSED">Closed</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Filter by Type
                            </label>
                            <select
                                value={typeFilter}
                                onChange={(e) => {
                                    setTypeFilter(e.target.value);
                                    setSkip(0);
                                }}
                                className="input-field"
                            >
                                <option value="">All Types</option>
                                <option value="UNMITIGATED_PERFORMANCE">Unmitigated Performance Problem</option>
                                <option value="OUTSIDE_INTENDED_PURPOSE">Model Used Outside Intended Purpose</option>
                                <option value="USE_PRIOR_TO_VALIDATION">Model In Use Prior to Full Validation</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Filter by Region
                            </label>
                            <select
                                value={regionFilter || ''}
                                onChange={(e) => {
                                    setRegionFilter(e.target.value ? Number(e.target.value) : null);
                                    setSkip(0);
                                }}
                                className="input-field"
                            >
                                <option value="">All Regions</option>
                                {regions.map((region) => (
                                    <option key={region.region_id} value={region.region_id}>
                                        {region.name} ({region.code})
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="flex items-end">
                            <p className="text-sm text-gray-500">
                                Showing {exceptions.length} of {total} exceptions
                            </p>
                        </div>
                    </div>
                </div>

                {/* Exceptions Table */}
                <div className="bg-white rounded-lg shadow-md overflow-hidden">
                    {loading ? (
                        <div className="p-8 text-center text-gray-500">Loading exceptions...</div>
                    ) : (
                        <>
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Exception Code
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Model
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Type
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Status
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Detected
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Actions
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {exceptions.length === 0 ? (
                                            <tr>
                                                <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                                                    No exceptions found.
                                                </td>
                                            </tr>
                                        ) : (
                                            exceptions.map((exc) => (
                                                <tr key={exc.exception_id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <button
                                                            onClick={() => handleOpenDetail(exc.exception_id)}
                                                            className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline"
                                                        >
                                                            {exc.exception_code}
                                                        </button>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <Link
                                                            to={`/models/${exc.model_id}`}
                                                            className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                                                        >
                                                            {exc.model.model_name}
                                                        </Link>
                                                        {exc.model.model_code && (
                                                            <span className="text-xs text-gray-500 ml-2">
                                                                ({exc.model.model_code})
                                                            </span>
                                                        )}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <span className="text-sm text-gray-900">
                                                            {EXCEPTION_TYPE_LABELS[exc.exception_type] || exc.exception_type}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        {getStatusBadge(exc.status)}
                                                        {exc.auto_closed && (
                                                            <span className="ml-2 text-xs text-gray-500" title="Auto-closed by system">
                                                                (auto)
                                                            </span>
                                                        )}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {exc.detected_at?.split('T')[0] || '-'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <button
                                                            onClick={() => handleOpenDetail(exc.exception_id)}
                                                            className="text-blue-600 hover:text-blue-800 text-sm"
                                                        >
                                                            View Details
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>

                            {/* Pagination */}
                            {total > limit && (
                                <div className="px-6 py-4 flex items-center justify-between border-t border-gray-200">
                                    <div className="text-sm text-gray-500">
                                        Page {Math.floor(skip / limit) + 1} of {Math.ceil(total / limit)}
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={handlePrevPage}
                                            disabled={skip === 0}
                                            className="btn-secondary text-sm disabled:opacity-50"
                                        >
                                            Previous
                                        </button>
                                        <button
                                            onClick={handleNextPage}
                                            disabled={skip + limit >= total}
                                            className="btn-secondary text-sm disabled:opacity-50"
                                        >
                                            Next
                                        </button>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Detail Modal */}
                {selectedExceptionId && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex justify-between items-start mb-4">
                                    <h3 className="text-lg font-semibold text-gray-900">
                                        Exception Details
                                    </h3>
                                    <button
                                        onClick={handleCloseDetail}
                                        className="text-gray-400 hover:text-gray-600"
                                    >
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>

                                {detailLoading ? (
                                    <div className="p-8 text-center text-gray-500">Loading...</div>
                                ) : exceptionDetail ? (
                                    <div className="space-y-4">
                                        {/* Basic Info */}
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <p className="text-sm font-medium text-gray-500">Exception Code</p>
                                                <p className="text-sm text-gray-900">{exceptionDetail.exception_code}</p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-500">Status</p>
                                                <p className="text-sm">{getStatusBadge(exceptionDetail.status)}</p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-500">Model</p>
                                                <Link
                                                    to={`/models/${exceptionDetail.model_id}`}
                                                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                                                >
                                                    {exceptionDetail.model.model_name}
                                                </Link>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-500">Type</p>
                                                <p className="text-sm text-gray-900">
                                                    {EXCEPTION_TYPE_LABELS[exceptionDetail.exception_type] || exceptionDetail.exception_type}
                                                </p>
                                            </div>
                                        </div>

                                        {/* Description */}
                                        <div>
                                            <p className="text-sm font-medium text-gray-500">Description</p>
                                            <p className="text-sm text-gray-900 mt-1">{exceptionDetail.description}</p>
                                        </div>

                                        {/* Dates */}
                                        <div className="grid grid-cols-3 gap-4">
                                            <div>
                                                <p className="text-sm font-medium text-gray-500">Detected</p>
                                                <p className="text-sm text-gray-900">
                                                    {exceptionDetail.detected_at?.split('T')[0] || '-'}
                                                </p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-500">Acknowledged</p>
                                                <p className="text-sm text-gray-900">
                                                    {exceptionDetail.acknowledged_at?.split('T')[0] || '-'}
                                                </p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-500">Closed</p>
                                                <p className="text-sm text-gray-900">
                                                    {exceptionDetail.closed_at?.split('T')[0] || '-'}
                                                </p>
                                            </div>
                                        </div>

                                        {/* Acknowledgment Info */}
                                        {exceptionDetail.acknowledged_by && (
                                            <div className="bg-yellow-50 p-3 rounded">
                                                <p className="text-sm font-medium text-yellow-800">Acknowledgment</p>
                                                <p className="text-sm text-yellow-700 mt-1">
                                                    Acknowledged by {exceptionDetail.acknowledged_by.full_name || exceptionDetail.acknowledged_by.email}
                                                </p>
                                                {exceptionDetail.acknowledgment_notes && (
                                                    <p className="text-sm text-yellow-700 mt-1">
                                                        Notes: {exceptionDetail.acknowledgment_notes}
                                                    </p>
                                                )}
                                            </div>
                                        )}

                                        {/* Closure Info */}
                                        {exceptionDetail.closed_at && (
                                            <div className="bg-green-50 p-3 rounded">
                                                <p className="text-sm font-medium text-green-800">
                                                    Closure {exceptionDetail.auto_closed && '(Auto-closed)'}
                                                </p>
                                                {exceptionDetail.closed_by && (
                                                    <p className="text-sm text-green-700 mt-1">
                                                        Closed by {exceptionDetail.closed_by.full_name || exceptionDetail.closed_by.email}
                                                    </p>
                                                )}
                                                {exceptionDetail.closure_reason && (
                                                    <p className="text-sm text-green-700 mt-1">
                                                        Reason: {exceptionDetail.closure_reason.label}
                                                    </p>
                                                )}
                                                {exceptionDetail.closure_narrative && (
                                                    <p className="text-sm text-green-700 mt-1">
                                                        Narrative: {exceptionDetail.closure_narrative}
                                                    </p>
                                                )}
                                            </div>
                                        )}

                                        {/* Status History */}
                                        {exceptionDetail.status_history && exceptionDetail.status_history.length > 0 && (
                                            <div>
                                                <p className="text-sm font-medium text-gray-500 mb-2">Status History</p>
                                                <div className="space-y-2">
                                                    {exceptionDetail.status_history.map((history) => (
                                                        <div
                                                            key={history.history_id}
                                                            className="text-sm bg-gray-50 p-2 rounded"
                                                        >
                                                            <span className="text-gray-500">
                                                                {history.changed_at?.split('T')[0]}
                                                            </span>
                                                            <span className="mx-2">→</span>
                                                            <span className="font-medium">{history.new_status}</span>
                                                            {history.changed_by && (
                                                                <span className="text-gray-500">
                                                                    {' '}by {history.changed_by.full_name || history.changed_by.email}
                                                                </span>
                                                            )}
                                                            {history.notes && (
                                                                <p className="text-gray-600 mt-1">{history.notes}</p>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Actions */}
                                        {isAdmin && exceptionDetail.status !== 'CLOSED' && (
                                            <div className="flex gap-2 pt-4 border-t">
                                                {exceptionDetail.status === 'OPEN' && (
                                                    <button
                                                        onClick={() => setShowAcknowledgeModal(true)}
                                                        className="btn-secondary"
                                                    >
                                                        Acknowledge
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => setShowCloseModal(true)}
                                                    className="btn-primary"
                                                >
                                                    Close Exception
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="p-8 text-center text-gray-500">Failed to load details</div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Acknowledge Modal */}
                {showAcknowledgeModal && exceptionDetail && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                            <div className="p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                                    Acknowledge Exception
                                </h3>
                                <p className="text-sm text-gray-600 mb-4">
                                    Acknowledging this exception indicates that you are aware of the issue and will take action to resolve it.
                                </p>
                                <div className="mb-4">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Notes (optional)
                                    </label>
                                    <textarea
                                        value={acknowledgeNotes}
                                        onChange={(e) => setAcknowledgeNotes(e.target.value)}
                                        rows={3}
                                        className="input-field"
                                        placeholder="Add any notes about this acknowledgment..."
                                    />
                                </div>
                                <div className="flex justify-end gap-2">
                                    <button
                                        onClick={() => {
                                            setShowAcknowledgeModal(false);
                                            setAcknowledgeNotes('');
                                        }}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleAcknowledge}
                                        disabled={acknowledgeLoading}
                                        className="btn-primary"
                                    >
                                        {acknowledgeLoading ? 'Saving...' : 'Acknowledge'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Close Modal */}
                {showCloseModal && exceptionDetail && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                            <div className="p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                                    Close Exception
                                </h3>
                                <div className="mb-4">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Closure Reason <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        value={closureReasonId || ''}
                                        onChange={(e) => setClosureReasonId(Number(e.target.value))}
                                        className="input-field"
                                    >
                                        <option value="">Select a reason...</option>
                                        {closureReasons.map((reason) => (
                                            <option key={reason.value_id} value={reason.value_id}>
                                                {reason.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="mb-4">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Closure Narrative <span className="text-red-500">*</span>
                                    </label>
                                    <textarea
                                        value={closureNarrative}
                                        onChange={(e) => setClosureNarrative(e.target.value)}
                                        rows={4}
                                        className="input-field"
                                        placeholder="Explain why this exception is being closed (min 10 characters)..."
                                    />
                                    {closureNarrative.length > 0 && closureNarrative.length < 10 && (
                                        <p className="text-xs text-red-500 mt-1">
                                            Narrative must be at least 10 characters ({closureNarrative.length}/10)
                                        </p>
                                    )}
                                </div>
                                <div className="flex justify-end gap-2">
                                    <button
                                        onClick={() => {
                                            setShowCloseModal(false);
                                            setClosureNarrative('');
                                            setClosureReasonId(null);
                                        }}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleClose}
                                        disabled={closeLoading || !closureReasonId || closureNarrative.length < 10}
                                        className="btn-primary disabled:opacity-50"
                                    >
                                        {closeLoading ? 'Closing...' : 'Close Exception'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Detect All Modal */}
                {showDetectModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                            <div className="p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                                    Detect All Exceptions
                                </h3>
                                {!detectResult ? (
                                    <>
                                        <p className="text-sm text-gray-600 mb-4">
                                            This will scan all models for exception conditions and create new exceptions where applicable.
                                        </p>
                                        <ul className="text-sm text-gray-600 mb-4 list-disc list-inside space-y-1">
                                            <li>Type 1: Unmitigated performance problems (RED monitoring without recommendations)</li>
                                            <li>Type 2: Models used outside intended purpose (attestation violations)</li>
                                            <li>Type 3: Models in use prior to full validation (early deployments)</li>
                                        </ul>
                                        <div className="flex justify-end gap-2">
                                            <button
                                                onClick={() => setShowDetectModal(false)}
                                                className="btn-secondary"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={handleDetectAll}
                                                disabled={detectLoading}
                                                className="btn-primary"
                                            >
                                                {detectLoading ? 'Detecting...' : 'Run Detection'}
                                            </button>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <div className="mb-4">
                                            <p className="text-sm font-medium text-green-600 mb-2">
                                                Detection Complete
                                            </p>
                                            <div className="bg-gray-50 p-3 rounded space-y-2">
                                                <p className="text-sm text-gray-700">
                                                    Type 1 (Unmitigated Performance): {detectResult.type1_count} new
                                                </p>
                                                <p className="text-sm text-gray-700">
                                                    Type 2 (Outside Intended Purpose): {detectResult.type2_count} new
                                                </p>
                                                <p className="text-sm text-gray-700">
                                                    Type 3 (Use Prior to Validation): {detectResult.type3_count} new
                                                </p>
                                                <p className="text-sm font-semibold text-gray-900 pt-2 border-t">
                                                    Total Created: {detectResult.total_created}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex justify-end">
                                            <button
                                                onClick={() => setShowDetectModal(false)}
                                                className="btn-primary"
                                            >
                                                Close
                                            </button>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Create Exception Modal */}
                {showCreateModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex justify-between items-start mb-4">
                                    <h3 className="text-lg font-semibold text-gray-900">
                                        Create Exception
                                    </h3>
                                    <button
                                        onClick={() => {
                                            setShowCreateModal(false);
                                            resetCreateForm();
                                        }}
                                        className="text-gray-400 hover:text-gray-600"
                                    >
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>

                                {createError && (
                                    <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
                                        {createError}
                                    </div>
                                )}

                                <div className="space-y-4">
                                    {/* Model Selection (Searchable) */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Model <span className="text-red-500">*</span>
                                        </label>
                                        <div className="relative">
                                            <input
                                                type="text"
                                                placeholder="Type to search for a model..."
                                                value={modelSearchQuery}
                                                onChange={(e) => {
                                                    setModelSearchQuery(e.target.value);
                                                    setShowModelDropdown(true);
                                                }}
                                                onFocus={() => setShowModelDropdown(true)}
                                                className="input-field"
                                            />
                                            {showModelDropdown && modelSearchQuery.length > 0 && (
                                                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                                    {filteredModels.length > 0 ? (
                                                        filteredModels.map((model) => (
                                                            <div
                                                                key={model.model_id}
                                                                className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                                                onClick={() => {
                                                                    setCreateModelId(model.model_id);
                                                                    setModelSearchQuery(model.model_name);
                                                                    setShowModelDropdown(false);
                                                                }}
                                                            >
                                                                {model.model_name}
                                                                {model.model_code && (
                                                                    <span className="text-gray-500 ml-2">({model.model_code})</span>
                                                                )}
                                                            </div>
                                                        ))
                                                    ) : (
                                                        <div className="px-4 py-2 text-sm text-gray-500">No models found</div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                        {createModelId && (
                                            <p className="mt-1 text-sm text-green-600">✓ Selected: {selectedModelName}</p>
                                        )}
                                    </div>

                                    {/* Exception Type */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Exception Type <span className="text-red-500">*</span>
                                        </label>
                                        <select
                                            value={createExceptionType}
                                            onChange={(e) => setCreateExceptionType(e.target.value)}
                                            className="input-field"
                                        >
                                            <option value="">Select exception type...</option>
                                            <option value="UNMITIGATED_PERFORMANCE">Unmitigated Performance Problem</option>
                                            <option value="OUTSIDE_INTENDED_PURPOSE">Model Used Outside Intended Purpose</option>
                                            <option value="USE_PRIOR_TO_VALIDATION">Model In Use Prior to Full Validation</option>
                                        </select>
                                    </div>

                                    {/* Description */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Description <span className="text-red-500">*</span>
                                        </label>
                                        <textarea
                                            value={createDescription}
                                            onChange={(e) => setCreateDescription(e.target.value)}
                                            rows={4}
                                            className="input-field"
                                            placeholder="Describe the exception (min 10 characters)..."
                                        />
                                        {createDescription.length > 0 && createDescription.length < 10 && (
                                            <p className="text-xs text-red-500 mt-1">
                                                Description must be at least 10 characters ({createDescription.length}/10)
                                            </p>
                                        )}
                                    </div>

                                    {/* Initial Status */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Initial Status
                                        </label>
                                        <select
                                            value={createInitialStatus}
                                            onChange={(e) => setCreateInitialStatus(e.target.value as 'OPEN' | 'ACKNOWLEDGED')}
                                            className="input-field"
                                        >
                                            <option value="OPEN">Open</option>
                                            <option value="ACKNOWLEDGED">Acknowledged</option>
                                        </select>
                                        <p className="text-xs text-gray-500 mt-1">
                                            {createInitialStatus === 'ACKNOWLEDGED'
                                                ? 'Exception will be created as already acknowledged'
                                                : 'Exception will need to be acknowledged after creation'}
                                        </p>
                                    </div>

                                    {/* Acknowledgment Notes (shown only if ACKNOWLEDGED) */}
                                    {createInitialStatus === 'ACKNOWLEDGED' && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Acknowledgment Notes
                                            </label>
                                            <textarea
                                                value={createAcknowledgmentNotes}
                                                onChange={(e) => setCreateAcknowledgmentNotes(e.target.value)}
                                                rows={2}
                                                className="input-field"
                                                placeholder="Optional notes for the acknowledgment..."
                                            />
                                        </div>
                                    )}
                                </div>

                                <div className="flex justify-end gap-2 mt-6 pt-4 border-t">
                                    <button
                                        onClick={() => {
                                            setShowCreateModal(false);
                                            resetCreateForm();
                                        }}
                                        className="btn-secondary"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleCreateException}
                                        disabled={createLoading || !createModelId || !createExceptionType || createDescription.length < 10}
                                        className="btn-primary disabled:opacity-50"
                                    >
                                        {createLoading ? 'Creating...' : 'Create Exception'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default ExceptionsReportPage;

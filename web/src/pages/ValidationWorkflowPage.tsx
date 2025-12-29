import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useLocation } from 'react-router-dom';
import api from '../api/client';
import { regionsApi, Region } from '../api/regions';
import Layout from '../components/Layout';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import ValidationWarningModal from '../components/ValidationWarningModal';
import VersionBlockerModal, { VersionBlocker } from '../components/VersionBlockerModal';
import { useTableSort } from '../hooks/useTableSort';
import { useColumnPreferences, ColumnDefinition } from '../hooks/useColumnPreferences';
import { ColumnPickerModal, SaveViewModal } from '../components/ColumnPickerModal';

interface ValidationRequest {
    request_id: number;
    model_ids: number[];  // Support multiple models
    model_names: string[];  // Support multiple model names
    request_date: string;
    requestor_name: string;
    validation_type: string;
    priority: string;
    target_completion_date: string;
    current_status: string;
    days_in_status: number;
    primary_validator: string | null;
    regions?: Region[];  // Support multiple regions
    created_at: string;
    updated_at: string;
}

interface Model {
    model_id: number;
    model_name: string;
}

interface ModelVersion {
    version_id: number;
    version_number: string;
    production_date: string | null;
    status: string;
}

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
    is_active?: boolean;
}

interface ValidationWarning {
    warning_type: string;
    severity: string;
    model_id: number;
    model_name: string;
    version_number?: string;
    message: string;
    details?: Record<string, any>;
}

interface ValidationWarningsResponse {
    has_warnings: boolean;
    can_proceed: boolean;
    warnings: ValidationWarning[];
}

export default function ValidationWorkflowPage() {
    const [searchParams] = useSearchParams();
    const location = useLocation();
    const [requests, setRequests] = useState<ValidationRequest[]>([]);
    const [models, setModels] = useState<Model[]>([]);
    const [validationTypes, setValidationTypes] = useState<TaxonomyValue[]>([]);
    const [priorities, setPriorities] = useState<TaxonomyValue[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [suggestedModels, setSuggestedModels] = useState<Model[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);
    const [suggestedRegions, setSuggestedRegions] = useState<Region[]>([]);
    const [loadingRegionSuggestions, setLoadingRegionSuggestions] = useState(false);
    const [showRegionWarning, setShowRegionWarning] = useState(false);
    const [missingRegions, setMissingRegions] = useState<Region[]>([]);
    const [modelVersions, setModelVersions] = useState<{ [modelId: number]: ModelVersion[] }>({});
    const [selectedVersions, setSelectedVersions] = useState<{ [modelId: number]: number | null }>({});
    const [loadingVersions, setLoadingVersions] = useState(false);
    const [showValidationWarnings, setShowValidationWarnings] = useState(false);
    const [validationWarnings, setValidationWarnings] = useState<ValidationWarning[]>([]);
    const [canProceedWithWarnings, setCanProceedWithWarnings] = useState(false);
    const [versionBlockers, setVersionBlockers] = useState<VersionBlocker[]>([]);

    const [formData, setFormData] = useState({
        model_ids: [] as number[],  // Support multiple models
        validation_type_id: 0,
        priority_id: 0,
        target_completion_date: '',
        trigger_reason: '',
        region_ids: [] as number[]  // Support multiple regions
    });

    // Detect if CHANGE validation type is selected (requires version linking)
    const isChangeType = validationTypes.find(t => t.value_id === formData.validation_type_id)?.code === 'CHANGE';

    // Filters
    const [filters, setFilters] = useState({
        search: '',
        status_filter: [] as string[],
        priority_filter: [] as string[],
        validation_type_filter: [] as string[],
        region_ids: [] as number[],
        overdue_only: false,
        unassigned_only: false,
        show_cancelled: false  // Hide cancelled items by default
    });

    // Column customization configuration
    const availableColumns: ColumnDefinition[] = [
        { key: 'request_id', label: 'ID', default: true },
        { key: 'model_names', label: 'Model', default: true },
        { key: 'validation_type', label: 'Type', default: true },
        { key: 'regions', label: 'Region', default: true },
        { key: 'priority', label: 'Priority', default: true },
        { key: 'current_status', label: 'Status', default: true },
        { key: 'days_in_status', label: 'Days in Status', default: true },
        { key: 'target_completion_date', label: 'Target Date', default: true },
        { key: 'updated_at', label: 'Last Modified', default: true },
        { key: 'primary_validator', label: 'Validator', default: true },
        { key: 'requestor_name', label: 'Requestor', default: false },
        { key: 'request_date', label: 'Request Date', default: false },
        { key: 'created_at', label: 'Created Date', default: false },
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
            columns: ['request_id', 'model_names', 'current_status', 'priority', 'target_completion_date'],
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
        entityType: 'validation_requests',
        availableColumns,
        defaultViews,
    });

    // Apply filters
    const filteredRequests = requests.filter(req => {
        // Hide cancelled items by default (unless show_cancelled is true or user explicitly filtered for Cancelled)
        if (!filters.show_cancelled && req.current_status === 'Cancelled' && !filters.status_filter.includes('Cancelled')) {
            return false;
        }

        // Search filter (model name) - search across all model names
        if (filters.search) {
            const searchLower = filters.search.toLowerCase();
            const hasMatchingModel = req.model_names.some(name =>
                name.toLowerCase().includes(searchLower)
            );
            if (!hasMatchingModel) {
                return false;
            }
        }

        // Status filter
        if (filters.status_filter.length > 0 && !filters.status_filter.includes(req.current_status)) {
            return false;
        }

        // Priority filter
        if (filters.priority_filter.length > 0 && !filters.priority_filter.includes(req.priority)) {
            return false;
        }

        // Validation type filter
        if (filters.validation_type_filter.length > 0 && !filters.validation_type_filter.includes(req.validation_type)) {
            return false;
        }

        // Region filter (multi-select)
        if (filters.region_ids.length > 0) {
            // Check if request has any matching region
            // If request has no regions (global), exclude it
            if (!req.regions || req.regions.length === 0) {
                return false;
            }
            // Check if any of the request's regions match the filter
            const hasMatchingRegion = req.regions.some(region =>
                filters.region_ids.includes(region.region_id)
            );
            if (!hasMatchingRegion) {
                return false;
            }
        }

        // Overdue filter
        if (filters.overdue_only) {
            const terminalStatuses = ['Approved', 'Cancelled'];
            if (terminalStatuses.includes(req.current_status)) return false;

            const targetDate = new Date(req.target_completion_date);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            if (targetDate >= today) return false;
        }

        // Unassigned filter (pending assignment)
        if (filters.unassigned_only && req.primary_validator) {
            return false;
        }

        return true;
    });

    // Add table sorting (default to updated_at descending to show most recently modified first)
    const { sortedData, requestSort, getSortIcon } = useTableSort<ValidationRequest>(
        filteredRequests,
        'updated_at',
        'desc'
    );

    // Auto-open form and pre-populate model_ids from query params
    useEffect(() => {
        if (location.pathname === '/validation-workflow/new') {
            setShowForm(true);
            const modelIdParam = searchParams.get('model_id');
            if (modelIdParam) {
                setFormData(prev => ({
                    ...prev,
                    model_ids: [parseInt(modelIdParam)]  // Add as first model in the list
                }));
            }
        }
    }, [location.pathname, searchParams]);

    // Initialize filters from URL parameters
    useEffect(() => {
        const statusParam = searchParams.get('status');
        const pendingAssignmentParam = searchParams.get('pending_assignment') === 'true';
        if (statusParam || pendingAssignmentParam) {
            setFilters(prev => ({
                ...prev,
                status_filter: statusParam ? [statusParam] : pendingAssignmentParam ? ['Intake'] : prev.status_filter,
                unassigned_only: pendingAssignmentParam ? true : prev.unassigned_only,
            }));
        }
    }, [searchParams]);

    // Auto-select "Initial" validation type if all selected models have no prior validations
    useEffect(() => {
        const checkAndSetInitialValidationType = async () => {
            if (formData.model_ids.length > 0 && validationTypes.length > 0) {
                try {
                    // Check if any of the selected models have validation projects
                    const modelValidationsRes = await api.get('/validation-workflow/requests/');
                    const allValidations = modelValidationsRes.data;

                    // Check if any selected model appears in any validation project
                    const hasAnyPriorValidations = formData.model_ids.some(modelId =>
                        allValidations.some((req: ValidationRequest) =>
                            req.model_ids.includes(modelId)
                        )
                    );

                    // If none of the models have prior validations, default to "Initial" validation type
                    if (!hasAnyPriorValidations) {
                        const initialType = validationTypes.find(
                            (type: TaxonomyValue) => type.code === 'INITIAL' || type.label.toLowerCase().includes('initial')
                        );
                        if (initialType && formData.validation_type_id === 0) {
                            setFormData(prev => ({
                                ...prev,
                                validation_type_id: initialType.value_id
                            }));
                        }
                    }
                } catch (err) {
                    console.error('Failed to check model validations:', err);
                }
            }
        };

        checkAndSetInitialValidationType();
    }, [formData.model_ids, validationTypes]);

    // Fetch grouping suggestions when exactly one model is selected
    useEffect(() => {
        const fetchSuggestions = async () => {
            if (formData.model_ids.length === 1) {
                try {
                    setLoadingSuggestions(true);
                    const response = await api.get(`/models/${formData.model_ids[0]}/validation-suggestions`);
                    setSuggestedModels(response.data.suggested_models || []);
                } catch (err) {
                    console.error('Failed to fetch grouping suggestions:', err);
                    setSuggestedModels([]);
                } finally {
                    setLoadingSuggestions(false);
                }
            } else {
                setSuggestedModels([]);
            }
        };

        fetchSuggestions();
    }, [formData.model_ids]);

    // Fetch suggested regions when models are selected (Phase 4)
    useEffect(() => {
        const fetchRegionSuggestions = async () => {
            if (formData.model_ids.length > 0) {
                try {
                    setLoadingRegionSuggestions(true);
                    const modelIdsStr = formData.model_ids.join(',');
                    const response = await api.get(`/validation-workflow/requests/preview-regions?model_ids=${modelIdsStr}`);
                    setSuggestedRegions(response.data.suggested_regions || []);
                } catch (err) {
                    console.error('Failed to fetch region suggestions:', err);
                    setSuggestedRegions([]);
                } finally {
                    setLoadingRegionSuggestions(false);
                }
            } else {
                setSuggestedRegions([]);
            }
        };

        fetchRegionSuggestions();
    }, [formData.model_ids]);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch validation projects
            const requestsRes = await api.get('/validation-workflow/requests/');
            setRequests(requestsRes.data);

            // Fetch models for form
            const modelsRes = await api.get('/models/');
            setModels(modelsRes.data);

            // Fetch taxonomies for form
            const taxonomiesRes = await api.get('/taxonomies/');
            const taxonomyList = taxonomiesRes.data;

            // Fetch taxonomy values
            const taxDetails = await Promise.all(
                taxonomyList.map((t: any) => api.get(`/taxonomies/${t.taxonomy_id}`))
            );
            const taxonomies = taxDetails.map((r: any) => r.data);

            const valType = taxonomies.find((t: any) => t.name === 'Validation Type');
            const priority = taxonomies.find((t: any) => t.name === 'Validation Priority');

            if (valType) {
                setValidationTypes((valType.values || []).filter((v: TaxonomyValue) => v.is_active !== false));
            }
            if (priority) {
                setPriorities((priority.values || []).filter((v: TaxonomyValue) => v.is_active !== false));
            }

            // Fetch regions
            const regionsData = await regionsApi.getRegions();
            setRegions(regionsData);
        } catch (err: any) {
            console.error('Failed to fetch data:', err);
            setError(err.response?.data?.detail || 'Failed to load validation projects');
        } finally {
            setLoading(false);
        }
    };

    // Fetch versions for selected models
    useEffect(() => {
        const fetchVersions = async () => {
            if (formData.model_ids.length === 0) {
                setModelVersions({});
                setSelectedVersions({});
                return;
            }

            setLoadingVersions(true);
            try {
                const versionsPromises = formData.model_ids.map(modelId =>
                    api.get(`/models/${modelId}/versions/`)
                );
                const versionsResponses = await Promise.all(versionsPromises);

                const newModelVersions: { [modelId: number]: ModelVersion[] } = {};
                const newSelectedVersions: { [modelId: number]: number | null } = {};

                formData.model_ids.forEach((modelId, index) => {
                    const versions = versionsResponses[index].data;
                    newModelVersions[modelId] = versions;

                    // Auto-select the latest DRAFT version if available, otherwise null
                    // DRAFT versions need validation; ACTIVE versions are already validated and in production
                    const draftVersions = versions.filter((v: ModelVersion) => v.status === 'DRAFT');
                    if (draftVersions.length > 0) {
                        // Sort by version_id descending to get latest
                        draftVersions.sort((a: ModelVersion, b: ModelVersion) => b.version_id - a.version_id);
                        newSelectedVersions[modelId] = draftVersions[0].version_id;
                    } else {
                        newSelectedVersions[modelId] = null;
                    }
                });

                setModelVersions(newModelVersions);
                setSelectedVersions(newSelectedVersions);
            } catch (err) {
                console.error('Failed to fetch model versions:', err);
            } finally {
                setLoadingVersions(false);
            }
        };

        fetchVersions();
    }, [formData.model_ids]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (formData.model_ids.length === 0 || !formData.validation_type_id || !formData.priority_id) {
            setError('Please fill in all required fields (at least one model must be selected)');
            return;
        }

        // For CHANGE validation type, require version selection for all models
        if (isChangeType) {
            const modelsWithoutVersions = formData.model_ids.filter(
                modelId => !selectedVersions[modelId]
            );
            if (modelsWithoutVersions.length > 0) {
                const modelNames = modelsWithoutVersions.map(id =>
                    models.find(m => m.model_id === id)?.model_name || `Model ${id}`
                ).join(', ');
                setError(`CHANGE validations require version selection. Missing versions for: ${modelNames}`);
                return;
            }
        }

        // Check for target completion date warnings
        if (formData.target_completion_date) {
            try {
                const payload = {
                    ...formData,
                    model_versions: selectedVersions,
                    check_warnings: true  // Flag to check without creating
                };
                const response = await api.post('/validation-workflow/requests/', payload);
                const warningsData: ValidationWarningsResponse = response.data;

                if (warningsData.has_warnings) {
                    // Show warning modal
                    setValidationWarnings(warningsData.warnings);
                    setCanProceedWithWarnings(warningsData.can_proceed);
                    setShowValidationWarnings(true);
                    return;
                }
            } catch (err: any) {
                console.error('Failed to check warnings:', err);
                setError(err.response?.data?.detail || 'Failed to validate request');
                return;
            }
        }

        // Check if models have regional scope that isn't covered
        if (suggestedRegions.length > 0) {
            const missing = suggestedRegions.filter(
                region => !formData.region_ids.includes(region.region_id)
            );

            if (missing.length > 0) {
                // Show warning modal
                setMissingRegions(missing);
                setShowRegionWarning(true);
                return;
            }
        }

        // Proceed with submission
        await submitValidationRequest();
    };

    const submitValidationRequest = async () => {
        try {
            const payload = {
                ...formData,
                model_versions: selectedVersions  // Add version tracking
            };
            await api.post('/validation-workflow/requests/', payload);
            setShowForm(false);
            setShowRegionWarning(false);
            setMissingRegions([]);
            setFormData({
                model_ids: [],
                validation_type_id: 0,
                priority_id: 0,
                target_completion_date: '',
                trigger_reason: '',
                region_ids: []
            });
            setSelectedVersions({});
            setModelVersions({});
            fetchData();
        } catch (err: any) {
            console.error('Failed to create request:', err);
            // Check if error contains version blockers for CHANGE validation type
            if (err.response?.status === 400 && err.response?.data?.detail?.blockers) {
                setVersionBlockers(err.response.data.detail.blockers);
            } else {
                setError(typeof err.response?.data?.detail === 'string'
                    ? err.response.data.detail
                    : 'Failed to create validation project');
            }
            setShowRegionWarning(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Intake': return 'bg-gray-100 text-gray-800';
            case 'Planning': return 'bg-blue-100 text-blue-800';
            case 'In Progress': return 'bg-yellow-100 text-yellow-800';
            case 'Review': return 'bg-purple-100 text-purple-800';
            case 'Pending Approval': return 'bg-orange-100 text-orange-800';
            case 'Revision': return 'bg-amber-100 text-amber-800';  // Sent back for revisions
            case 'Approved': return 'bg-green-100 text-green-800';
            case 'On Hold': return 'bg-red-100 text-red-800';
            case 'Cancelled': return 'bg-gray-400 text-white';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'Critical': return 'bg-red-100 text-red-800';
            case 'High': return 'bg-orange-100 text-orange-800';
            case 'Medium': return 'bg-yellow-100 text-yellow-800';
            case 'Low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    // Check if a validation request is overdue (target date passed and not in terminal state)
    const isOverdue = (req: ValidationRequest) => {
        const terminalStatuses = ['Approved', 'Cancelled'];
        if (terminalStatuses.includes(req.current_status)) return false;

        const targetDate = new Date(req.target_completion_date);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return targetDate < today;
    };

    // Column renderers for dynamic table
    const columnRenderers: Record<string, {
        header: string;
        sortKey?: string;
        cell: (req: ValidationRequest) => React.ReactNode;
        csvValue: (req: ValidationRequest) => string;
    }> = {
        request_id: {
            header: 'ID',
            sortKey: 'request_id',
            cell: (req) => (
                <Link
                    to={`/validation-workflow/${req.request_id}`}
                    className="font-mono text-blue-600 hover:text-blue-800 hover:underline"
                >
                    #{req.request_id}
                </Link>
            ),
            csvValue: (req) => req.request_id.toString()
        },
        model_names: {
            header: 'Model',
            cell: (req) => (
                <div className="flex flex-wrap gap-1">
                    {req.model_names.map((name, idx) => (
                        <span key={req.model_ids[idx]} className="text-sm text-gray-900">
                            {name}{idx < req.model_names.length - 1 ? ',' : ''}
                        </span>
                    ))}
                </div>
            ),
            csvValue: (req) => req.model_names.join('; ')
        },
        validation_type: {
            header: 'Type',
            sortKey: 'validation_type',
            cell: (req) => req.validation_type,
            csvValue: (req) => req.validation_type
        },
        regions: {
            header: 'Region',
            cell: (req) => req.regions && req.regions.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                    {req.regions.map(region => (
                        <span key={region.region_id} className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                            {region.code}
                        </span>
                    ))}
                </div>
            ) : (
                <span className="text-gray-400 text-xs">Global</span>
            ),
            csvValue: (req) => req.regions?.map(r => r.code).join('; ') || 'Global'
        },
        priority: {
            header: 'Priority',
            sortKey: 'priority',
            cell: (req) => (
                <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(req.priority)}`}>
                    {req.priority}
                </span>
            ),
            csvValue: (req) => req.priority
        },
        current_status: {
            header: 'Status',
            sortKey: 'current_status',
            cell: (req) => (
                <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs rounded ${getStatusColor(req.current_status)}`}>
                        {req.current_status}
                    </span>
                    {isOverdue(req) && (
                        <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-red-600 text-white" title="Target completion date has passed">
                            OVERDUE
                        </span>
                    )}
                </div>
            ),
            csvValue: (req) => isOverdue(req) ? `${req.current_status} (OVERDUE)` : req.current_status
        },
        days_in_status: {
            header: 'Days in Status',
            sortKey: 'days_in_status',
            cell: (req) => (
                <span className={req.days_in_status > 14 ? 'text-red-600 font-semibold' : ''}>
                    {req.days_in_status} days
                </span>
            ),
            csvValue: (req) => req.days_in_status.toString()
        },
        target_completion_date: {
            header: 'Target Date',
            sortKey: 'target_completion_date',
            cell: (req) => req.target_completion_date,
            csvValue: (req) => req.target_completion_date
        },
        updated_at: {
            header: 'Last Modified',
            sortKey: 'updated_at',
            cell: (req) => req.updated_at ? req.updated_at.split('T')[0] : 'N/A',
            csvValue: (req) => req.updated_at ? req.updated_at.split('T')[0] : ''
        },
        primary_validator: {
            header: 'Validator',
            sortKey: 'primary_validator',
            cell: (req) => req.primary_validator || <span className="text-gray-400">Unassigned</span>,
            csvValue: (req) => req.primary_validator || ''
        },
        requestor_name: {
            header: 'Requestor',
            sortKey: 'requestor_name',
            cell: (req) => req.requestor_name,
            csvValue: (req) => req.requestor_name
        },
        request_date: {
            header: 'Request Date',
            sortKey: 'request_date',
            cell: (req) => req.request_date ? req.request_date.split('T')[0] : 'N/A',
            csvValue: (req) => req.request_date ? req.request_date.split('T')[0] : ''
        },
        created_at: {
            header: 'Created Date',
            sortKey: 'created_at',
            cell: (req) => req.created_at ? req.created_at.split('T')[0] : 'N/A',
            csvValue: (req) => req.created_at ? req.created_at.split('T')[0] : ''
        }
    };

    // CSV Export handler
    const handleExportCSV = () => {
        if (columnPrefs.selectedColumns.length === 0) {
            alert('Please select at least one column to export.');
            return;
        }

        const headers = columnPrefs.selectedColumns
            .filter(colKey => columnRenderers[colKey])
            .map(colKey => columnRenderers[colKey].header);

        const rows = sortedData.map(req => {
            const row: string[] = [];
            columnPrefs.selectedColumns.forEach(colKey => {
                const renderer = columnRenderers[colKey];
                let value = renderer ? renderer.csvValue(req) : '';
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
        link.download = `validation_requests_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
    };

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
                    <h2 className="text-2xl font-bold">Validation Workflow</h2>
                    <p className="text-sm text-gray-600 mt-1">
                        Manage validation projects through their complete lifecycle
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => columnPrefs.setShowColumnsModal(true)}
                        className="btn-secondary"
                    >
                        Columns ({columnPrefs.selectedColumns.length})
                    </button>
                    <button onClick={handleExportCSV} className="btn-secondary">
                        Export CSV
                    </button>
                    <button onClick={() => setShowForm(true)} className="btn-primary">
                        + New Validation Project
                    </button>
                </div>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            {showForm && (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">Create New Validation Project</h3>
                    <p className="text-sm text-gray-600 mb-4">
                        Submit a validation project. The outcome will be determined after the validation work is complete.
                    </p>
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Models (Required - Select one or more)
                                </label>
                                <MultiSelectDropdown
                                    label=""
                                    placeholder="Select Models"
                                    options={models.map(m => ({
                                        value: m.model_id,
                                        label: m.model_name,
                                        searchText: `${m.model_name} ${m.model_id}`,
                                        secondaryLabel: `ID: ${m.model_id}`
                                    }))}
                                    selectedValues={formData.model_ids}
                                    onChange={(values) => setFormData({ ...formData, model_ids: values as number[] })}
                                />

                                {/* Grouping Suggestions */}
                                {formData.model_ids.length === 1 && (
                                    <div className="mt-3">
                                        {loadingSuggestions ? (
                                            <div className="text-sm text-gray-500 italic">
                                                Loading suggestions...
                                            </div>
                                        ) : suggestedModels.length > 0 ? (
                                            <div className="bg-blue-50 border border-blue-200 rounded p-3">
                                                <div className="flex items-start justify-between mb-2">
                                                    <div>
                                                        <p className="text-sm font-medium text-blue-900">
                                                            Suggested Models
                                                        </p>
                                                        <p className="text-xs text-blue-700 mt-1">
                                                            These models were previously validated together with your selection
                                                        </p>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        onClick={() => {
                                                            const suggestedIds = suggestedModels.map(m => m.model_id);
                                                            const allIds = [...new Set([...formData.model_ids, ...suggestedIds])];
                                                            setFormData({ ...formData, model_ids: allIds });
                                                        }}
                                                        className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
                                                    >
                                                        Add All
                                                    </button>
                                                </div>
                                                <ul className="text-sm text-blue-800 space-y-1">
                                                    {suggestedModels.map(model => (
                                                        <li key={model.model_id} className="flex items-center justify-between">
                                                            <span>{model.model_name}</span>
                                                            <button
                                                                type="button"
                                                                onClick={() => {
                                                                    if (!formData.model_ids.includes(model.model_id)) {
                                                                        setFormData({
                                                                            ...formData,
                                                                            model_ids: [...formData.model_ids, model.model_id]
                                                                        });
                                                                    }
                                                                }}
                                                                className="text-xs text-blue-600 hover:text-blue-800 underline"
                                                                disabled={formData.model_ids.includes(model.model_id)}
                                                            >
                                                                {formData.model_ids.includes(model.model_id) ? 'Added' : 'Add'}
                                                            </button>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        ) : (
                                            <div className="text-xs text-gray-500 italic">
                                                No previous grouping suggestions available for this model
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Model Version Selection */}
                                {formData.model_ids.length > 0 && (
                                    <div className="mt-4">
                                        <label className="block text-sm font-medium mb-2">
                                            Model Versions {isChangeType ? <span className="text-red-600">(Required for Change Validations)</span> : '(Optional)'}
                                        </label>
                                        <p className="text-xs text-gray-600 mb-3">
                                            {isChangeType
                                                ? 'CHANGE validations require linking each model to a specific version. Select the version containing the changes to be validated.'
                                                : 'Select the specific version being validated for each model. If no version is selected, the validation will apply to the model generally.'
                                            }
                                        </p>
                                        {loadingVersions ? (
                                            <div className="text-sm text-gray-500 italic">Loading versions...</div>
                                        ) : (
                                            <div className="space-y-2">
                                                {formData.model_ids.map(modelId => {
                                                    const model = models.find(m => m.model_id === modelId);
                                                    const versions = modelVersions[modelId] || [];
                                                    return (
                                                        <div key={modelId} className="bg-gray-50 p-3 rounded border border-gray-200">
                                                            <div className="flex items-start gap-3">
                                                                <div className="flex-1">
                                                                    <label className="block text-xs font-medium text-gray-700 mb-1">
                                                                        {model?.model_name}
                                                                    </label>
                                                                    <select
                                                                        className={`input-field text-sm ${isChangeType && !selectedVersions[modelId] ? 'border-red-300' : ''}`}
                                                                        value={selectedVersions[modelId] || ''}
                                                                        onChange={(e) => setSelectedVersions({
                                                                            ...selectedVersions,
                                                                            [modelId]: e.target.value ? parseInt(e.target.value) : null
                                                                        })}
                                                                    >
                                                                        {!isChangeType && <option value="">No specific version (general validation)</option>}
                                                                        {isChangeType && <option value="">-- Select a version (required) --</option>}
                                                                        {versions.map((v: ModelVersion) => (
                                                                            <option key={v.version_id} value={v.version_id}>
                                                                                {v.version_number} - {v.status}
                                                                                {v.production_date ? ` (Implemented: ${v.production_date.split('T')[0]})` : ''}
                                                                            </option>
                                                                        ))}
                                                                    </select>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            <div className="mb-4">
                                <label htmlFor="validation_type_id" className="block text-sm font-medium mb-2">
                                    Validation Type (Required)
                                </label>
                                <select
                                    id="validation_type_id"
                                    className="input-field"
                                    value={formData.validation_type_id || ''}
                                    onChange={(e) => setFormData({ ...formData, validation_type_id: parseInt(e.target.value) || 0 })}
                                    required
                                >
                                    <option value="">Select Type</option>
                                    {validationTypes.map(t => (
                                        <option key={t.value_id} value={t.value_id}>{t.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="priority_id" className="block text-sm font-medium mb-2">
                                    Priority (Required)
                                </label>
                                <select
                                    id="priority_id"
                                    className="input-field"
                                    value={formData.priority_id || ''}
                                    onChange={(e) => setFormData({ ...formData, priority_id: parseInt(e.target.value) || 0 })}
                                    required
                                >
                                    <option value="">Select Priority</option>
                                    {priorities.map(p => (
                                        <option key={p.value_id} value={p.value_id}>{p.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="target_completion_date" className="block text-sm font-medium mb-2">
                                    Target Completion Date (Required)
                                </label>
                                <input
                                    id="target_completion_date"
                                    type="date"
                                    className="input-field"
                                    value={formData.target_completion_date}
                                    onChange={(e) => setFormData({ ...formData, target_completion_date: e.target.value })}
                                    required
                                />
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Specific Region Scope (Optional)
                                    <span className="text-xs text-gray-500 ml-2">Leave empty if the validation is global (not specific to a region)</span>
                                </label>
                                <MultiSelectDropdown
                                    label=""
                                    placeholder="Select Regions (or leave empty for global)"
                                    options={regions.map(r => ({ value: r.region_id, label: `${r.name} (${r.code})` }))}
                                    selectedValues={formData.region_ids}
                                    onChange={(values) => setFormData({ ...formData, region_ids: values as number[] })}
                                />

                                {/* Regional Scope Intelligence (Phase 4) */}
                                {formData.model_ids.length > 0 && (
                                    <div className="mt-3">
                                        {loadingRegionSuggestions ? (
                                            <div className="text-sm text-gray-500 italic">
                                                Loading region suggestions...
                                            </div>
                                        ) : suggestedRegions.length > 0 ? (
                                            <div className="bg-purple-50 border border-purple-200 rounded p-3">
                                                <p className="text-sm font-medium text-purple-900 mb-2 flex items-center gap-2">
                                                    Suggested Regions
                                                    <span className="text-xs font-normal text-gray-600 cursor-help" title="Automatically suggested based on the geographic scope of your selected models">
                                                        ⓘ
                                                    </span>
                                                </p>
                                                <p className="text-xs text-purple-700 mb-3">
                                                    Based on the selected models, you may add one or more region scopes if the validation applies only to them:
                                                </p>
                                                <ul className="space-y-2">
                                                    {suggestedRegions.map(region => (
                                                        <li key={region.region_id} className="flex items-start justify-between text-sm">
                                                            <div className="flex items-center gap-2">
                                                                <span className="font-medium text-purple-900">
                                                                    {region.name} ({region.code})
                                                                </span>
                                                                {region.requires_regional_approval && (
                                                                    <span className="px-2 py-0.5 bg-orange-100 text-orange-800 text-xs rounded">
                                                                        Approval Required
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <button
                                                                type="button"
                                                                onClick={() => {
                                                                    if (!formData.region_ids.includes(region.region_id)) {
                                                                        setFormData({
                                                                            ...formData,
                                                                            region_ids: [...formData.region_ids, region.region_id]
                                                                        });
                                                                    }
                                                                }}
                                                                className="text-xs text-purple-600 hover:text-purple-800 underline"
                                                                disabled={formData.region_ids.includes(region.region_id)}
                                                            >
                                                                {formData.region_ids.includes(region.region_id) ? 'Added' : 'Add'}
                                                            </button>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        ) : (
                                            <div className="text-xs text-gray-500 italic">
                                                No regional scope detected for selected models
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="mb-4">
                            <label htmlFor="trigger_reason" className="block text-sm font-medium mb-2">
                                Trigger Reason (Optional)
                            </label>
                            <input
                                id="trigger_reason"
                                type="text"
                                className="input-field"
                                value={formData.trigger_reason}
                                onChange={(e) => setFormData({ ...formData, trigger_reason: e.target.value })}
                                placeholder="What triggered this validation project?"
                            />
                        </div>

                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">Submit Project</button>
                            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Region Warning Modal */}
            {showRegionWarning && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6">
                        <h3 className="text-xl font-bold text-orange-900 mb-4 flex items-center gap-2">
                            <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            Regional Scope Warning
                        </h3>
                        <div className="mb-4">
                            <p className="text-gray-700 mb-3">
                                The selected models are deployed in the following region(s) that you have <strong>not selected</strong> for this validation:
                            </p>
                            <ul className="bg-orange-50 border border-orange-200 rounded p-3 space-y-2">
                                {missingRegions.map(region => (
                                    <li key={region.region_id} className="flex items-center gap-2 text-sm">
                                        <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                                        <span className="font-medium text-orange-900">{region.name} ({region.code})</span>
                                        {region.requires_regional_approval && (
                                            <span className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded">
                                                Requires Approval
                                            </span>
                                        )}
                                    </li>
                                ))}
                            </ul>
                            <p className="text-gray-600 mt-3 text-sm">
                                If you proceed without selecting these regions, the validation may not cover the full scope of the model deployments.
                            </p>
                        </div>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => {
                                    setShowRegionWarning(false);
                                    setMissingRegions([]);
                                }}
                                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                            >
                                Go Back and Add Regions
                            </button>
                            <button
                                onClick={submitValidationRequest}
                                className="px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
                            >
                                Proceed Anyway
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Target Completion Date Warnings Modal */}
            {showValidationWarnings && (
                <ValidationWarningModal
                    warnings={validationWarnings}
                    canProceed={canProceedWithWarnings}
                    onClose={() => {
                        setShowValidationWarnings(false);
                        setValidationWarnings([]);
                    }}
                    onProceed={async () => {
                        setShowValidationWarnings(false);
                        setValidationWarnings([]);
                        await submitValidationRequest();
                    }}
                    onAmend={() => {
                        setShowValidationWarnings(false);
                        setValidationWarnings([]);
                        // User can now edit the target_completion_date field in the form
                    }}
                />
            )}

            {/* Version Blockers Modal (for CHANGE validation type) */}
            {versionBlockers.length > 0 && (
                <VersionBlockerModal
                    blockers={versionBlockers}
                    onClose={() => setVersionBlockers([])}
                    onSelectVersion={(modelId, versionId) => {
                        setSelectedVersions(prev => ({ ...prev, [modelId]: versionId }));
                        setVersionBlockers(prev => prev.filter(b => b.model_id !== modelId));
                    }}
                />
            )}

            {/* Filters */}
            <div className="bg-white p-4 rounded-lg shadow-md mb-6">
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                    {/* Search */}
                    <div>
                        <label htmlFor="filter-search" className="block text-xs font-medium text-gray-700 mb-1">
                            Search Model
                        </label>
                        <input
                            id="filter-search"
                            type="text"
                            className="input-field text-sm"
                            placeholder="Model name..."
                            value={filters.search}
                            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                        />
                    </div>

                    {/* Status */}
                    <MultiSelectDropdown
                        label="Status"
                        placeholder="All Statuses"
                        options={[
                            { value: 'Intake', label: 'Intake' },
                            { value: 'Planning', label: 'Planning' },
                            { value: 'In Progress', label: 'In Progress' },
                            { value: 'Review', label: 'Review' },
                            { value: 'Pending Approval', label: 'Pending Approval' },
                            { value: 'Revision', label: 'Revision' },
                            { value: 'Approved', label: 'Approved' },
                            { value: 'On Hold', label: 'On Hold' },
                            { value: 'Cancelled', label: 'Cancelled' }
                        ]}
                        selectedValues={filters.status_filter}
                        onChange={(values) => setFilters({ ...filters, status_filter: values as string[] })}
                    />

                    {/* Priority */}
                    <MultiSelectDropdown
                        label="Priority"
                        placeholder="All Priorities"
                        options={priorities.map(p => ({ value: p.label, label: p.label }))}
                        selectedValues={filters.priority_filter}
                        onChange={(values) => setFilters({ ...filters, priority_filter: values as string[] })}
                    />

                    {/* Validation Type */}
                    <MultiSelectDropdown
                        label="Validation Type"
                        placeholder="All Types"
                        options={validationTypes.map(t => ({ value: t.label, label: t.label }))}
                        selectedValues={filters.validation_type_filter}
                        onChange={(values) => setFilters({ ...filters, validation_type_filter: values as string[] })}
                    />

                    {/* Region */}
                    <MultiSelectDropdown
                        label="Region"
                        placeholder="All Regions"
                        options={regions.map(r => ({ value: r.region_id, label: `${r.name} (${r.code})` }))}
                        selectedValues={filters.region_ids}
                        onChange={(values) => setFilters({ ...filters, region_ids: values as number[] })}
                    />
                </div>

                {/* Toggle Filters */}
                <div className="mt-3 flex items-center gap-6">
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

                    <label className="flex items-center cursor-pointer">
                        <input
                            type="checkbox"
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            checked={filters.unassigned_only}
                            onChange={(e) => setFilters({ ...filters, unassigned_only: e.target.checked })}
                        />
                        <span className="ml-2 text-sm font-medium text-gray-700">
                            Awaiting validator assignment
                        </span>
                        {filters.unassigned_only && (
                            <span className="ml-2 px-1.5 py-0.5 text-xs font-medium rounded bg-blue-600 text-white">
                                UNASSIGNED
                            </span>
                        )}
                    </label>

                    <label className="flex items-center cursor-pointer">
                        <input
                            type="checkbox"
                            className="h-4 w-4 text-gray-600 focus:ring-gray-500 border-gray-300 rounded"
                            checked={filters.show_cancelled}
                            onChange={(e) => setFilters({ ...filters, show_cancelled: e.target.checked })}
                        />
                        <span className="ml-2 text-sm font-medium text-gray-700">
                            Show cancelled
                        </span>
                    </label>
                </div>

                {/* Clear Filters and Results Count */}
                <div className="flex items-center justify-between mt-3 pt-3 border-t">
                    <div className="text-sm text-gray-600">
                        Showing <span className="font-semibold">{filteredRequests.length}</span> of{' '}
                        <span className="font-semibold">{requests.length}</span> projects
                    </div>
                    <button
                        onClick={() => setFilters({
                            search: '',
                            status_filter: [],
                            priority_filter: [],
                            validation_type_filter: [],
                            region_ids: [],
                            overdue_only: false,
                            unassigned_only: false,
                            show_cancelled: false
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
                                    No validation projects found. Click "New Validation Project" to create one.
                                </td>
                            </tr>
                        ) : (
                            sortedData.map((req) => (
                                <tr key={req.request_id} className="hover:bg-gray-50">
                                    {columnPrefs.selectedColumns.map(colKey => {
                                        const renderer = columnRenderers[colKey];
                                        if (!renderer) return null;
                                        return (
                                            <td key={colKey} className="px-6 py-4 whitespace-nowrap text-sm">
                                                {renderer.cell(req)}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

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

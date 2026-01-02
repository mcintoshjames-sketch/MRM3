import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { canManageModels } from '../utils/roleUtils';
import Layout from '../components/Layout';
import { useTableSort } from '../hooks/useTableSort';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import MRSAReviewStatusBadge, { MRSAReviewStatusCode } from '../components/MRSAReviewStatusBadge';
import { Region } from '../api/regions';
import { exportViewsApi, ExportView } from '../api/exportViews';
import { linkChangeToAttestationIfPresent } from '../api/attestation';

interface User {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
}

interface Vendor {
    vendor_id: number;
    name: string;
    contact_info: string;
}

interface WhollyOwnedRegion {
    region_id: number;
    code: string;
    name: string;
}

// Region as returned in model list (different from Region API)
interface ModelRegionItem {
    region_id: number;
    region_code: string;
    region_name: string;
}

interface ModelType {
    type_id: number;
    category_id: number;
    name: string;
    description: string | null;
    sort_order: number;
    is_active: boolean;
}

interface ModelTypeCategory {
    category_id: number;
    name: string;
    description: string | null;
    sort_order: number;
    model_types: ModelType[];
}

interface TaxonomyValue {
    value_id: number;
    label: string;
    code?: string;
    requires_irp?: boolean;  // For MRSA Risk Level taxonomy
}

interface IRPContactUser {
    user_id: number;
    email: string;
    full_name: string;
}

interface IRPItem {
    irp_id: number;
    process_name: string;
    description?: string;
    is_active: boolean;
    contact_user_id: number;
    contact_user?: IRPContactUser;
}

interface MRSAReviewStatus {
    mrsa_id: number;
    mrsa_name: string;
    risk_level: string | null;
    last_review_date: string | null;
    next_due_date: string | null;
    status: MRSAReviewStatusCode;
    days_until_due: number | null;
    owner: IRPContactUser | null;
    has_exception: boolean;
    exception_due_date: string | null;
}

interface Methodology {
    methodology_id: number;
    name: string;
    category?: {
        name: string;
    };
}

interface UserWithLOB extends User {
    lob?: {
        lob_id: number;
        name: string;
    };
}

interface Model {
    model_id: number;
    model_name: string;
    description: string;
    products_covered: string | null;
    development_type: string;
    owner_id: number;
    developer_id: number | null;
    vendor_id: number | null;
    wholly_owned_region_id: number | null;
    wholly_owned_region: WhollyOwnedRegion | null;
    status: string;
    model_type_id: number | null;
    model_type: ModelType | null;
    created_at: string;
    updated_at: string;
    row_approval_status: string | null;
    submitted_at: string | null;
    is_model: boolean;
    is_aiml: boolean | null;
    // MRSA fields
    is_mrsa: boolean;
    mrsa_risk_level_id: number | null;
    mrsa_risk_level: TaxonomyValue | null;
    mrsa_risk_rationale: string | null;
    mrsa_review_status?: MRSAReviewStatusCode | null;
    mrsa_last_review_date?: string | null;
    mrsa_next_due_date?: string | null;
    mrsa_days_until_due?: number | null;
    mrsa_has_exception?: boolean;
    mrsa_exception_due_date?: string | null;
    // Usage frequency taxonomy
    usage_frequency_id: number | null;
    usage_frequency: TaxonomyValue | null;
    owner: UserWithLOB;
    developer: UserWithLOB | null;
    vendor: Vendor | null;
    users: User[];
    regions: ModelRegionItem[];
    // Additional fields from API
    shared_owner: UserWithLOB | null;
    shared_developer: UserWithLOB | null;
    monitoring_manager: UserWithLOB | null;
    business_line_name: string | null;
    risk_tier: TaxonomyValue | null;
    methodology: Methodology | null;
    ownership_type: TaxonomyValue | null;
    regulatory_categories: TaxonomyValue[];
    // IRPs covering this MRSA
    irps: IRPItem[];
    // Computed validation fields
    scorecard_outcome: string | null;
    residual_risk: string | null;
    // Computed approval status fields
    approval_status: string | null;
    approval_status_label: string | null;
    // Computed from model version history
    model_last_updated: string | null;
    // Computed revalidation fields
    validation_status: 'current' | 'due_soon' | 'overdue' | null;
    next_validation_due_date: string | null;
    days_until_validation_due: number | null;
    last_validation_date: string | null;
    days_overdue: number | null;
    penalty_notches: number | null;
    adjusted_scorecard_outcome: string | null;
}

export default function ModelsPage() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const { user } = useAuth();
    const canManageModelsFlag = canManageModels(user);
    const [models, setModels] = useState<Model[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [modelTypes, setModelTypes] = useState<ModelTypeCategory[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);

    // KPI drill-down filter state
    const [kpiDrillDownIds, setKpiDrillDownIds] = useState<number[] | null>(null);
    const [kpiDrillDownActive, setKpiDrillDownActive] = useState(false);

    // Handle ?create=true query param to auto-open create form
    // Handle ?ids=1,2,3 query param for KPI drill-down
    useEffect(() => {
        if (searchParams.get('create') === 'true') {
            setShowForm(true);
            // Clear the query param so it doesn't persist on refresh
            setSearchParams({}, { replace: true });
        }

        // Handle KPI drill-down IDs parameter
        const idsParam = searchParams.get('ids');
        if (idsParam) {
            const modelIds = idsParam.split(',')
                .map(id => parseInt(id.trim(), 10))
                .filter(id => !isNaN(id));
            if (modelIds.length > 0) {
                setKpiDrillDownIds(modelIds);
                setKpiDrillDownActive(true);
            }
        } else {
            setKpiDrillDownIds(null);
            setKpiDrillDownActive(false);
        }
    }, [searchParams, setSearchParams]);
    const [formData, setFormData] = useState({
        model_name: '',
        description: '',
        products_covered: '',
        development_type: 'In-House',
        owner_id: 0,
        developer_id: null as number | null,
        vendor_id: null as number | null,
        wholly_owned_region_id: null as number | null,
        model_type_id: null as number | null,
        usage_frequency_id: 0,
        status: 'In Development',
        user_ids: [] as number[],
        region_ids: [] as number[],
        initial_version_number: '' as string,
        initial_implementation_date: '' as string,
        is_model: true,
        // MRSA fields (only applicable when is_model=false)
        is_mrsa: false,
        mrsa_risk_level_id: null as number | null,
        mrsa_risk_rationale: '' as string,
        auto_create_validation: false,
        validation_request_type_id: 0,
        validation_request_priority_id: 0,
        validation_request_target_date: '' as string,
        validation_request_trigger_reason: '' as string
    });
    const [includeNonModels, setIncludeNonModels] = useState(false);
    const [mrsaRiskLevels, setMrsaRiskLevels] = useState<TaxonomyValue[]>([]);
    // View mode: 'models' = Models only, 'mrsas' = MRSAs only, 'all' = All entities
    const [viewMode, setViewMode] = useState<'models' | 'mrsas' | 'all'>('models');
    const [userSearchTerm, setUserSearchTerm] = useState('');
    const [validationTypes, setValidationTypes] = useState<any[]>([]);
    const [validationPriorities, setValidationPriorities] = useState<any[]>([]);
    const [usageFrequencies, setUsageFrequencies] = useState<any[]>([]);

    // Check if form has unsaved changes
    const formIsDirty = showForm && (
        formData.model_name !== '' ||
        formData.description !== '' ||
        formData.products_covered !== '' ||
        formData.owner_id !== 0 ||
        formData.developer_id !== null ||
        formData.vendor_id !== null ||
        formData.wholly_owned_region_id !== null ||
        formData.model_type_id !== null ||
        formData.usage_frequency_id !== 0 ||
        formData.user_ids.length > 0 ||
        formData.region_ids.length > 0 ||
        formData.initial_version_number !== '' ||
        formData.initial_implementation_date !== '' ||
        formData.auto_create_validation ||
        formData.validation_request_trigger_reason !== ''
    );

    // Warn on browser refresh/close
    useEffect(() => {
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            if (formIsDirty) {
                e.preventDefault();
                e.returnValue = '';
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    }, [formIsDirty]);

    const handleCancelForm = () => {
        if (formIsDirty) {
            if (!confirm('You have unsaved changes. Are you sure you want to close this form? Your changes will be lost.')) {
                return;
            }
        }
        setShowForm(false);
        setFormData({
            model_name: '',
            description: '',
            products_covered: '',
            development_type: 'In-House',
            owner_id: 0,
            developer_id: null,
            vendor_id: null,
            wholly_owned_region_id: null,
            model_type_id: null,
            usage_frequency_id: 0,
            status: 'In Development',
            user_ids: [],
            region_ids: [],
            initial_version_number: '',
            initial_implementation_date: '',
            is_model: true,
            is_mrsa: false,
            mrsa_risk_level_id: null,
            mrsa_risk_rationale: '',
            auto_create_validation: false,
            validation_request_type_id: 0,
            validation_request_priority_id: 0,
            validation_request_target_date: '',
            validation_request_trigger_reason: ''
        });
    };
    const [showExportModal, setShowExportModal] = useState(false);
    const [showColumnsModal, setShowColumnsModal] = useState(false);
    const [showSaveViewModal, setShowSaveViewModal] = useState(false);
    const [newViewName, setNewViewName] = useState('');
    const [newViewDescription, setNewViewDescription] = useState('');
    const [newViewIsPublic, setNewViewIsPublic] = useState(false);
    const [editingViewId, setEditingViewId] = useState<number | null>(null);
    const [dbViews, setDbViews] = useState<ExportView[]>([]);

    // Define available columns for table and export
    // 'default' determines which columns are shown initially in the table
    const availableColumns = [
        { key: 'model_id', label: 'Model ID', default: false },
        { key: 'model_name', label: 'Model Name', default: true },
        { key: 'is_aiml', label: 'AI/ML', default: true },
        { key: 'is_mrsa', label: 'MRSA', default: false },
        { key: 'mrsa_risk_level', label: 'MRSA Risk Level', default: false },
        { key: 'mrsa_risk_rationale', label: 'MRSA Risk Rationale', default: false },
        { key: 'mrsa_review_status', label: 'MRSA Review Status', default: false },
        { key: 'mrsa_last_review_date', label: 'MRSA Last Review', default: false },
        { key: 'mrsa_next_due_date', label: 'MRSA Next Due', default: false },
        { key: 'irp_coverage', label: 'IRP (MRSA Only)', default: false },
        { key: 'irp_contact', label: 'IRP Contact (MRSA Only)', default: false },
        { key: 'owner', label: 'Owner', default: true },
        { key: 'owner_lob', label: 'Owner LOB', default: false },
        { key: 'developer', label: 'Developer', default: true },
        { key: 'shared_owner', label: 'Shared Owner', default: false },
        { key: 'shared_owner_lob', label: 'Shared Owner LOB', default: false },
        { key: 'shared_developer', label: 'Shared Developer', default: false },
        { key: 'monitoring_manager', label: 'Monitoring Manager', default: false },
        { key: 'business_line_name', label: 'Business Line', default: false },
        { key: 'vendor', label: 'Vendor', default: true },
        { key: 'regions', label: 'Regions', default: true },
        { key: 'users', label: 'Users', default: true },
        { key: 'status', label: 'Status', default: true },
        { key: 'risk_tier', label: 'Risk Tier', default: false },
        { key: 'usage_frequency', label: 'Usage Frequency', default: false },
        { key: 'methodology', label: 'Methodology', default: false },
        { key: 'ownership_type', label: 'Ownership Type', default: false },
        { key: 'model_type', label: 'Model Type', default: false },
        { key: 'regulatory_categories', label: 'Regulatory Categories', default: false },
        { key: 'scorecard_outcome', label: 'Scorecard Outcome', default: false },
        { key: 'residual_risk', label: 'Residual Risk', default: false },
        { key: 'approval_status', label: 'Approval Status', default: false },
        { key: 'description', label: 'Description', default: false },
        { key: 'products_covered', label: 'Products Covered', default: false },
        { key: 'development_type', label: 'Development Type', default: false },
        { key: 'wholly_owned_region', label: 'Wholly Owned Region', default: false },
        { key: 'row_approval_status', label: 'Inventory Acceptance', default: false },
        { key: 'created_at', label: 'Created Date', default: false },
        { key: 'updated_at', label: 'Modified On', default: false },
        { key: 'model_last_updated', label: 'Model Last Updated', default: true },
        // Revalidation computed fields
        { key: 'validation_status', label: 'Validation Status', default: false },
        { key: 'next_validation_due_date', label: 'Next Validation Due', default: false },
        { key: 'days_until_validation_due', label: 'Days Until Due', default: false },
        { key: 'last_validation_date', label: 'Last Validation', default: false },
        { key: 'days_overdue', label: 'Days Overdue', default: false },
        { key: 'penalty_notches', label: 'Penalty Notches', default: false },
        { key: 'adjusted_scorecard_outcome', label: 'Adjusted Outcome', default: false }
    ];

    const mrsaReviewStatusOptions = [
        { value: 'OVERDUE', label: 'Overdue' },
        { value: 'NEVER_REVIEWED', label: 'Never Reviewed' },
        { value: 'NO_IRP', label: 'No IRP' },
        { value: 'UPCOMING', label: 'Upcoming' },
        { value: 'CURRENT', label: 'Current' },
        { value: 'NO_REQUIREMENT', label: 'No Requirement' }
    ];

    // Define default preset views
    const defaultViews = {
        'default': {
            id: 'default',
            name: 'Default View',
            columns: availableColumns.filter(col => col.default).map(col => col.key),
            isDefault: true
        },
        'basic': {
            id: 'basic',
            name: 'Basic Info',
            columns: ['model_id', 'model_name', 'status'],
            isDefault: true
        },
        'full': {
            id: 'full',
            name: 'Full Details',
            columns: availableColumns.map(col => col.key),
            isDefault: true
        },
        'ownership': {
            id: 'ownership',
            name: 'Ownership Report',
            columns: ['model_name', 'development_type', 'owner', 'developer', 'vendor', 'status'],
            isDefault: true
        }
    };

    // Combined views: default views + database views
    const allViews: Record<string, any> = React.useMemo(() => {
        const combined: Record<string, any> = { ...defaultViews };
        // Add database views
        dbViews.forEach(view => {
            combined[`db_${view.view_id}`] = {
                id: `db_${view.view_id}`,
                name: view.view_name,
                columns: view.columns,
                isDefault: false,
                isPublic: view.is_public,
                dbView: view
            };
        });
        return combined;
    }, [dbViews]);

    const [currentViewId, setCurrentViewId] = useState<string>('default');
    const [selectedColumns, setSelectedColumns] = useState<string[]>(
        availableColumns.filter(col => col.default).map(col => col.key)
    );

    useEffect(() => {
        if (viewMode !== 'mrsas') return;
        const mrsaColumns = ['mrsa_review_status', 'mrsa_last_review_date', 'mrsa_next_due_date'];
        setSelectedColumns((prev) => {
            const next = new Set(prev);
            mrsaColumns.forEach((column) => next.add(column));
            return Array.from(next);
        });
    }, [viewMode]);

    // Filters
    const [filters, setFilters] = useState({
        search: '',
        development_types: [] as string[],
        statuses: [] as string[],
        owner_ids: [] as number[],
        vendor_ids: [] as number[],
        region_ids: [] as number[],
        mrsa_review_statuses: [] as MRSAReviewStatusCode[],
        include_sub_models: false,
        is_aiml: '' as '' | 'true' | 'false' | 'null'  // '', 'true', 'false', 'null' (undefined)
    });
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(50);

    // Apply filters first, then sort
    const filteredModels = models.filter(model => {
        // Search filter (model name or description)
        if (filters.search && !model.model_name.toLowerCase().includes(filters.search.toLowerCase()) &&
            !model.description?.toLowerCase().includes(filters.search.toLowerCase())) {
            return false;
        }

        // Development type filter (multi-select)
        if (filters.development_types.length > 0 && !filters.development_types.includes(model.development_type)) {
            return false;
        }

        // Status filter (multi-select)
        if (filters.statuses.length > 0 && !filters.statuses.includes(model.status)) {
            return false;
        }

        // Owner filter (multi-select)
        if (filters.owner_ids.length > 0 && !filters.owner_ids.includes(model.owner_id)) {
            return false;
        }

        // Vendor filter (multi-select)
        if (filters.vendor_ids.length > 0) {
            // For third-party models, check if vendor is in the selected list
            // For in-house models (vendor_id is null), exclude them
            if (model.vendor_id === null || !filters.vendor_ids.includes(model.vendor_id)) {
                return false;
            }
        }

        // Region filter (multi-select)
        if (filters.region_ids.length > 0) {
            // Check if model has any of the selected regions
            // If model has no regions (global), exclude it
            if (!model.regions || model.regions.length === 0) {
                return false;
            }
            const modelRegionIds = model.regions.map(r => r.region_id);
            const hasMatchingRegion = filters.region_ids.some(rid => modelRegionIds.includes(rid));
            if (!hasMatchingRegion) {
                return false;
            }
        }

        // View mode filter: 'models' = only is_model=true, 'mrsas' = only is_mrsa=true, 'all' = all
        if (viewMode === 'models') {
            // In 'models' view, show only is_model=true (exclude non-models unless checkbox is checked)
            if (!model.is_model && !includeNonModels) {
                return false;
            }
        } else if (viewMode === 'mrsas') {
            // In 'mrsas' view, show only is_mrsa=true
            if (!model.is_mrsa) {
                return false;
            }
        }
        // 'all' view shows everything (no filter)

        // AI/ML classification filter
        if (filters.is_aiml !== '') {
            if (filters.is_aiml === 'true' && model.is_aiml !== true) {
                return false;
            }
            if (filters.is_aiml === 'false' && model.is_aiml !== false) {
                return false;
            }
            if (filters.is_aiml === 'null' && model.is_aiml !== null) {
                return false;
            }
        }

        // MRSA review status filter (only applies to MRSAs)
        if (filters.mrsa_review_statuses.length > 0) {
            if (!model.is_mrsa) {
                return false;
            }
            if (!model.mrsa_review_status || !filters.mrsa_review_statuses.includes(model.mrsa_review_status)) {
                return false;
            }
        }

        return true;
    });

    // Table sorting (applied to filtered data)
    const { sortedData, requestSort, getSortIcon, sortConfig } = useTableSort<Model>(filteredModels, 'model_name');
    const totalPages = Math.max(1, Math.ceil(sortedData.length / pageSize));
    const paginatedModels = useMemo(() => {
        const startIndex = (currentPage - 1) * pageSize;
        return sortedData.slice(startIndex, startIndex + pageSize);
    }, [sortedData, currentPage, pageSize]);
    useEffect(() => {
        setCurrentPage(1);
    }, [filters, viewMode, includeNonModels, sortConfig.key, sortConfig.direction]);
    useEffect(() => {
        if (currentPage > totalPages) {
            setCurrentPage(totalPages);
        }
    }, [currentPage, totalPages]);

    useEffect(() => {
        // On initial mount, check URL directly to avoid race condition with URL parsing effect
        // On subsequent renders, use the kpiDrillDownIds state
        let modelIdsToFetch = kpiDrillDownIds;

        // If kpiDrillDownIds is null but URL has ids param, parse it directly
        // This handles the initial mount before URL parsing effect runs
        if (!modelIdsToFetch) {
            const idsParam = searchParams.get('ids');
            if (idsParam) {
                modelIdsToFetch = idsParam.split(',')
                    .map(id => parseInt(id.trim(), 10))
                    .filter(id => !isNaN(id));
                if (modelIdsToFetch.length === 0) {
                    modelIdsToFetch = null;
                }
            }
        }

        fetchData(modelIdsToFetch);
        loadExportViews();
    }, [kpiDrillDownIds, searchParams]);

    // Refetch models when include_sub_models filter changes
    useEffect(() => {
        if (!loading) { // Only refetch if initial load is complete
            // Get model IDs from URL or state
            let modelIdsToFetch = kpiDrillDownIds;
            if (!modelIdsToFetch) {
                const idsParam = searchParams.get('ids');
                if (idsParam) {
                    modelIdsToFetch = idsParam.split(',')
                        .map(id => parseInt(id.trim(), 10))
                        .filter(id => !isNaN(id));
                    if (modelIdsToFetch.length === 0) {
                        modelIdsToFetch = null;
                    }
                }
            }
            fetchData(modelIdsToFetch);
        }
    }, [filters.include_sub_models, kpiDrillDownIds, searchParams]);

    // Clear KPI drill-down filter
    const clearKpiDrillDown = () => {
        setSearchParams({}, { replace: true });
        setKpiDrillDownIds(null);
        setKpiDrillDownActive(false);
    };

    const loadExportViews = async () => {
        try {
            const views = await exportViewsApi.list('models');
            setDbViews(views);
        } catch (error) {
            console.error('Failed to load export views:', error);
        }
    };

    const fetchData = async (modelIds?: number[] | null) => {
        try {
            const params = new URLSearchParams();
            if (!filters.include_sub_models) {
                params.append('exclude_sub_models', 'true');
            }
            // Include computed fields (scorecard_outcome, residual_risk, approval_status)
            params.append('include_computed_fields', 'true');

            // Add model IDs filter for KPI drill-down
            if (modelIds && modelIds.length > 0) {
                params.append('model_ids', modelIds.join(','));
            }

            // Build taxonomy query string (axios serializes arrays as names[] but FastAPI expects names=v1&names=v2)
            const taxonomyNames = ['Validation Type', 'Validation Priority', 'Model Usage Frequency', 'MRSA Risk Level'];
            const taxonomyQueryString = taxonomyNames.map(n => `names=${encodeURIComponent(n)}`).join('&');

            const [
                modelsRes,
                usersRes,
                vendorsRes,
                regionsRes,
                taxonomiesRes,
                modelTypesRes,
                mrsaReviewRes
            ] = await Promise.all([
                api.get(`/models/?${params.toString()}`),
                api.get('/auth/users'),
                api.get('/vendors/'),
                api.get('/regions/'),
                api.get(`/taxonomies/by-names/?${taxonomyQueryString}`),
                api.get('/model-types/categories'),
                api.get('/irps/mrsa-review-status').catch(() => ({ data: [] }))
            ]);
            const mrsaReviewMap = new Map<number, MRSAReviewStatus>(
                (mrsaReviewRes.data as MRSAReviewStatus[]).map((item) => [item.mrsa_id, item])
            );
            const enrichedModels = modelsRes.data.map((model: Model) => {
                if (!model.is_mrsa) {
                    return {
                        ...model,
                        mrsa_review_status: null,
                        mrsa_last_review_date: null,
                        mrsa_next_due_date: null,
                        mrsa_days_until_due: null,
                        mrsa_has_exception: false,
                        mrsa_exception_due_date: null
                    };
                }

                const reviewStatus = mrsaReviewMap.get(model.model_id);
                return {
                    ...model,
                    mrsa_review_status: reviewStatus?.status ?? null,
                    mrsa_last_review_date: reviewStatus?.last_review_date ?? null,
                    mrsa_next_due_date: reviewStatus?.next_due_date ?? null,
                    mrsa_days_until_due: reviewStatus?.days_until_due ?? null,
                    mrsa_has_exception: reviewStatus?.has_exception ?? false,
                    mrsa_exception_due_date: reviewStatus?.exception_due_date ?? null
                };
            });
            setModels(enrichedModels);
            setUsers(usersRes.data);
            setVendors(vendorsRes.data);
            setRegions(regionsRes.data);
            setModelTypes(modelTypesRes.data);

            // Extract taxonomy values from batch response
            const taxonomies = taxonomiesRes.data;
            const valType = taxonomies.find((t: any) => t.name === 'Validation Type');
            const valPriority = taxonomies.find((t: any) => t.name === 'Validation Priority');
            const usageFreq = taxonomies.find((t: any) => t.name === 'Model Usage Frequency');
            const mrsaRiskLevel = taxonomies.find((t: any) => t.name === 'MRSA Risk Level');

            if (valType) {
                setValidationTypes(valType.values || []);
            }
            if (valPriority) {
                setValidationPriorities(valPriority.values || []);
            }
            if (usageFreq) {
                setUsageFrequencies(usageFreq.values || []);
            }
            if (mrsaRiskLevel) {
                setMrsaRiskLevels(mrsaRiskLevel.values || []);
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate required fields
        if (!formData.usage_frequency_id || formData.usage_frequency_id === 0) {
            alert('Please select a Usage Frequency.');
            return;
        }

        // Validate MRSA fields if is_mrsa is checked
        if (formData.is_mrsa) {
            if (!formData.mrsa_risk_level_id) {
                alert('Please select an MRSA Risk Level.');
                return;
            }
            if (!formData.mrsa_risk_rationale || formData.mrsa_risk_rationale.trim() === '') {
                alert('Please provide an MRSA Risk Rationale.');
                return;
            }
        }

        // Validate auto-create validation fields if checkbox is checked
        if (formData.auto_create_validation) {
            if (!formData.validation_request_type_id || formData.validation_request_type_id === 0) {
                alert('Please select a Validation Type when auto-creating a validation project.');
                return;
            }
            if (!formData.validation_request_priority_id || formData.validation_request_priority_id === 0) {
                alert('Please select a Priority when auto-creating a validation project.');
                return;
            }
        }

        try {
            const payload = {
                ...formData,
                developer_id: formData.developer_id || null,
                vendor_id: formData.vendor_id || null,
                wholly_owned_region_id: formData.wholly_owned_region_id || null,
                model_type_id: formData.model_type_id || null,
                usage_frequency_id: formData.usage_frequency_id,
                user_ids: formData.user_ids.length > 0 ? formData.user_ids : null,
                region_ids: formData.region_ids.length > 0 ? formData.region_ids : null,
                initial_version_number: formData.initial_version_number || null,
                initial_implementation_date: formData.initial_implementation_date || null,
                validation_request_type_id: formData.validation_request_type_id || null,
                validation_request_priority_id: formData.validation_request_priority_id || null,
                validation_request_target_date: formData.validation_request_target_date || null,
                validation_request_trigger_reason: formData.validation_request_trigger_reason || null,
                // MRSA fields - only include if is_mrsa is true
                is_mrsa: formData.is_mrsa,
                mrsa_risk_level_id: formData.is_mrsa ? formData.mrsa_risk_level_id : null,
                mrsa_risk_rationale: formData.is_mrsa ? (formData.mrsa_risk_rationale || null) : null
            };
            console.log('DEBUG: Creating model with payload:', JSON.stringify(payload, null, 2));
            console.log('DEBUG: usage_frequency_id value:', formData.usage_frequency_id, 'type:', typeof formData.usage_frequency_id);
            const response = await api.post('/models/', payload);

            // Link to attestation if navigated from attestation page
            if (response.data.model_id) {
                await linkChangeToAttestationIfPresent('NEW_MODEL', {
                    model_id: response.data.model_id,
                });
            }

            // Check for warnings in the response
            if (response.data.warnings && response.data.warnings.length > 0) {
                const warningMessages = response.data.warnings.map((w: any) => w.message).join('\n\n');
                const viewModel = confirm(`Model created successfully, but with warnings:\n\n${warningMessages}\n\nWould you like to view the model details?`);

                if (viewModel && response.data.model_id) {
                    // Navigate to model details page
                    navigate(`/models/${response.data.model_id}`);
                    return;
                }
            }

            setShowForm(false);
            setFormData({
                model_name: '',
                description: '',
                products_covered: '',
                development_type: 'In-House',
                owner_id: 0,
                developer_id: null,
                vendor_id: null,
                wholly_owned_region_id: null,
                model_type_id: null,
                usage_frequency_id: 0,
                status: 'In Development',
                user_ids: [],
                region_ids: [],
                initial_version_number: '',
                initial_implementation_date: '',
                is_model: true,
                is_mrsa: false,
                mrsa_risk_level_id: null,
                mrsa_risk_rationale: '',
                auto_create_validation: false,
                validation_request_type_id: 0,
                validation_request_priority_id: 0,
                validation_request_target_date: '',
                validation_request_trigger_reason: ''
            });
            fetchData();
        } catch (error: any) {
            console.error('Failed to create model:', error);
            alert(`Failed to create model: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
        }
    };

    const handleDelete = async (modelId: number) => {
        if (!confirm('Are you sure you want to delete this model?')) return;

        try {
            await api.delete(`/models/${modelId}`);
            fetchData();
        } catch (error) {
            console.error('Failed to delete model:', error);
        }
    };

    const addUserToModel = (userId: number) => {
        if (!formData.user_ids.includes(userId)) {
            setFormData(prev => ({
                ...prev,
                user_ids: [...prev.user_ids, userId]
            }));
        }
        setUserSearchTerm('');
    };

    const removeUserFromModel = (userId: number) => {
        setFormData(prev => ({
            ...prev,
            user_ids: prev.user_ids.filter(id => id !== userId)
        }));
    };

    const getFilteredUsers = () => {
        if (!userSearchTerm) return [];
        return users.filter(u =>
            !formData.user_ids.includes(u.user_id) &&
            (u.full_name.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
                u.email.toLowerCase().includes(userSearchTerm.toLowerCase()))
        );
    };

    const toggleColumn = (columnKey: string) => {
        setSelectedColumns(prev => {
            if (prev.includes(columnKey)) {
                return prev.filter(k => k !== columnKey);
            } else {
                return [...prev, columnKey];
            }
        });
    };

    const selectAllColumns = () => {
        setSelectedColumns(availableColumns.map(col => col.key));
    };

    const deselectAllColumns = () => {
        setSelectedColumns([]);
    };

    const loadView = (viewId: string) => {
        const view = allViews[viewId];
        if (view) {
            setSelectedColumns(view.columns);
            setCurrentViewId(viewId);
        }
    };

    const formatDate = (value: string | null | undefined) => {
        if (!value) return '-';
        return value.split('T')[0];
    };

    // Column renderers: define how each column renders in table and CSV
    const columnRenderers: Record<string, {
        header: string;
        sortKey?: string;
        cell: (model: Model) => React.ReactNode;
        csvValue: (model: Model) => string;
    }> = {
        model_id: {
            header: 'Model ID',
            sortKey: 'model_id',
            cell: (model) => model.model_id,
            csvValue: (model) => model.model_id.toString()
        },
        model_name: {
            header: 'Name',
            sortKey: 'model_name',
            cell: (model) => (
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => navigate(`/models/${model.model_id}`)}
                        className="font-medium text-blue-600 hover:text-blue-800 text-left"
                    >
                        {model.model_name}
                    </button>
                    {!model.is_model && (
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-700">
                            Non-Model
                        </span>
                    )}
                    {model.row_approval_status && (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${model.row_approval_status === 'Draft'
                            ? 'bg-blue-100 text-blue-800'
                            : model.row_approval_status === 'needs_revision'
                                ? 'bg-orange-100 text-orange-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                            {model.row_approval_status === 'Draft' ? 'Draft' :
                                model.row_approval_status === 'needs_revision' ? 'Needs Revision' :
                                    model.row_approval_status}
                        </span>
                    )}
                    {model.wholly_owned_region && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 border border-indigo-300 whitespace-nowrap">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                            </svg>
                            {model.wholly_owned_region.code}
                        </span>
                    )}
                </div>
            ),
            csvValue: (model) => model.model_name
        },
        is_aiml: {
            header: 'AI/ML',
            sortKey: 'is_aiml',
            cell: (model) => model.is_aiml === true ? (
                <span className="px-2 py-1 text-xs rounded bg-purple-100 text-purple-800 font-medium">AI/ML</span>
            ) : model.is_aiml === false ? (
                <span className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">Non-AI/ML</span>
            ) : (
                <span className="text-sm text-gray-400 italic">Undefined</span>
            ),
            csvValue: (model) => model.is_aiml === true ? 'AI/ML' : model.is_aiml === false ? 'Non-AI/ML' : 'Undefined'
        },
        is_mrsa: {
            header: 'MRSA',
            sortKey: 'is_mrsa',
            cell: (model) => model.is_mrsa ? (
                <span className="px-2 py-1 text-xs rounded bg-amber-100 text-amber-800 font-medium">MRSA</span>
            ) : (
                <span className="text-sm text-gray-400">-</span>
            ),
            csvValue: (model) => model.is_mrsa ? 'Yes' : 'No'
        },
        mrsa_risk_level: {
            header: 'MRSA Risk Level',
            sortKey: 'mrsa_risk_level.label',
            cell: (model) => model.mrsa_risk_level ? (
                <span className={`px-2 py-1 text-xs rounded font-medium ${
                    model.mrsa_risk_level.code === 'HIGH_RISK' ? 'bg-red-100 text-red-800' :
                    model.mrsa_risk_level.code === 'LOW_RISK' ? 'bg-green-100 text-green-800' :
                    'bg-gray-100 text-gray-700'
                }`}>
                    {model.mrsa_risk_level.label}
                </span>
            ) : (
                <span className="text-sm text-gray-400">-</span>
            ),
            csvValue: (model) => model.mrsa_risk_level?.label || ''
        },
        mrsa_risk_rationale: {
            header: 'MRSA Risk Rationale',
            cell: (model) => model.is_mrsa && model.mrsa_risk_rationale ? (
                <span className="truncate max-w-xs block" title={model.mrsa_risk_rationale}>
                    {model.mrsa_risk_rationale.length > 50
                        ? model.mrsa_risk_rationale.slice(0, 50) + '...'
                        : model.mrsa_risk_rationale}
                </span>
            ) : (
                <span className="text-sm text-gray-400">-</span>
            ),
            csvValue: (model) => model.is_mrsa ? (model.mrsa_risk_rationale || '') : ''
        },
        mrsa_review_status: {
            header: 'MRSA Review Status',
            sortKey: 'mrsa_review_status',
            cell: (model) => {
                if (!model.is_mrsa || !model.mrsa_review_status) {
                    return <span className="text-sm text-gray-400">-</span>;
                }
                return <MRSAReviewStatusBadge status={model.mrsa_review_status} />;
            },
            csvValue: (model) => model.is_mrsa && model.mrsa_review_status ? model.mrsa_review_status : ''
        },
        mrsa_last_review_date: {
            header: 'MRSA Last Review',
            sortKey: 'mrsa_last_review_date',
            cell: (model) => {
                if (!model.is_mrsa) return <span className="text-sm text-gray-400">-</span>;
                return <span>{formatDate(model.mrsa_last_review_date)}</span>;
            },
            csvValue: (model) =>
                model.is_mrsa && model.mrsa_last_review_date ? formatDate(model.mrsa_last_review_date) : ''
        },
        mrsa_next_due_date: {
            header: 'MRSA Next Due',
            sortKey: 'mrsa_next_due_date',
            cell: (model) => {
                if (!model.is_mrsa) return <span className="text-sm text-gray-400">-</span>;
                return (
                    <div>
                        <div>{formatDate(model.mrsa_next_due_date)}</div>
                        {model.mrsa_has_exception && model.mrsa_exception_due_date && (
                            <div className="text-xs text-purple-600 mt-0.5">
                                Exception: {formatDate(model.mrsa_exception_due_date)}
                            </div>
                        )}
                    </div>
                );
            },
            csvValue: (model) =>
                model.is_mrsa && model.mrsa_next_due_date ? formatDate(model.mrsa_next_due_date) : ''
        },
        irp_coverage: {
            header: 'IRP (MRSA Only)',
            cell: (model) => {
                if (!model.is_mrsa) return <span className="text-gray-400">-</span>;
                if (!model.irps || model.irps.length === 0) {
                    return <span className="text-red-500 font-medium">No IRP</span>;
                }
                return (
                    <div className="flex flex-wrap gap-1">
                        {model.irps.map(irp => (
                            <span
                                key={irp.irp_id}
                                className="px-2 py-0.5 bg-green-100 text-green-800 rounded text-xs font-medium"
                                title={irp.description || irp.process_name}
                            >
                                {irp.process_name}
                            </span>
                        ))}
                    </div>
                );
            },
            csvValue: (model) => {
                if (!model.is_mrsa) return '';
                if (!model.irps || model.irps.length === 0) return 'No IRP';
                return model.irps.map(irp => irp.process_name).join('; ');
            }
        },
        irp_contact: {
            header: 'IRP Contact (MRSA Only)',
            cell: (model) => {
                if (!model.is_mrsa) return <span className="text-gray-400">-</span>;
                if (!model.irps || model.irps.length === 0) {
                    return <span className="text-gray-400">-</span>;
                }
                // Get unique contacts across all IRPs
                const contacts = model.irps
                    .filter(irp => irp.contact_user)
                    .map(irp => irp.contact_user!.full_name);
                const uniqueContacts = [...new Set(contacts)];
                if (uniqueContacts.length === 0) {
                    return <span className="text-gray-400">-</span>;
                }
                return uniqueContacts.join(', ');
            },
            csvValue: (model) => {
                if (!model.is_mrsa) return '';
                if (!model.irps || model.irps.length === 0) return '';
                const contacts = model.irps
                    .filter(irp => irp.contact_user)
                    .map(irp => irp.contact_user!.full_name);
                const uniqueContacts = [...new Set(contacts)];
                return uniqueContacts.join('; ');
            }
        },
        owner: {
            header: 'Owner',
            sortKey: 'owner.full_name',
            cell: (model) => model.owner?.full_name || '-',
            csvValue: (model) => model.owner?.full_name || ''
        },
        owner_lob: {
            header: 'Owner LOB',
            cell: (model) => model.owner?.lob?.name || '-',
            csvValue: (model) => model.owner?.lob?.name || ''
        },
        developer: {
            header: 'Developer',
            sortKey: 'developer.full_name',
            cell: (model) => model.developer?.full_name || '-',
            csvValue: (model) => model.developer?.full_name || ''
        },
        shared_owner: {
            header: 'Shared Owner',
            sortKey: 'shared_owner.full_name',
            cell: (model) => model.shared_owner?.full_name || '-',
            csvValue: (model) => model.shared_owner?.full_name || ''
        },
        shared_owner_lob: {
            header: 'Shared Owner LOB',
            cell: (model) => model.shared_owner?.lob?.name || '-',
            csvValue: (model) => model.shared_owner?.lob?.name || ''
        },
        shared_developer: {
            header: 'Shared Developer',
            sortKey: 'shared_developer.full_name',
            cell: (model) => model.shared_developer?.full_name || '-',
            csvValue: (model) => model.shared_developer?.full_name || ''
        },
        monitoring_manager: {
            header: 'Monitoring Manager',
            sortKey: 'monitoring_manager.full_name',
            cell: (model) => model.monitoring_manager?.full_name || '-',
            csvValue: (model) => model.monitoring_manager?.full_name || ''
        },
        business_line_name: {
            header: 'Business Line',
            sortKey: 'business_line_name',
            cell: (model) => model.business_line_name || '-',
            csvValue: (model) => model.business_line_name || ''
        },
        vendor: {
            header: 'Vendor',
            sortKey: 'vendor.name',
            cell: (model) => model.vendor?.name || '-',
            csvValue: (model) => model.vendor?.name || ''
        },
        regions: {
            header: 'Regions',
            cell: (model) => model.regions && model.regions.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                    {model.regions.map(r => (
                        <span key={r.region_id} className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs font-semibold">
                            {r.region_code}
                        </span>
                    ))}
                </div>
            ) : (
                <span className="text-gray-400">Global</span>
            ),
            csvValue: (model) => model.regions?.map(r => r.region_code).join('; ') || ''
        },
        users: {
            header: 'Users',
            cell: (model) => model.users?.length > 0 ? model.users.map(u => u.full_name).join(', ') : '-',
            csvValue: (model) => model.users?.map(u => u.full_name).join('; ') || ''
        },
        status: {
            header: 'Status',
            sortKey: 'status',
            cell: (model) => (
                <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                    {model.status}
                </span>
            ),
            csvValue: (model) => model.status
        },
        risk_tier: {
            header: 'Risk Tier',
            sortKey: 'risk_tier.label',
            cell: (model) => {
                if (!model.risk_tier) return <span className="text-gray-400">-</span>;
                const code = model.risk_tier.code;
                const label = model.risk_tier.label;
                let shortLabel = label;
                let colorClass = 'bg-gray-100 text-gray-700';

                if (code === 'TIER_1' || label.toLowerCase().includes('high')) {
                    shortLabel = 'High';
                    colorClass = 'bg-red-100 text-red-800';
                } else if (code === 'TIER_2' || label.toLowerCase().includes('medium')) {
                    shortLabel = 'Medium';
                    colorClass = 'bg-yellow-100 text-yellow-800';
                } else if (code === 'TIER_3' || (label.toLowerCase().includes('low') && !label.toLowerCase().includes('very'))) {
                    shortLabel = 'Low';
                    colorClass = 'bg-green-100 text-green-800';
                } else if (code === 'TIER_4' || label.toLowerCase().includes('very low') || label.toLowerCase().includes('minimal')) {
                    shortLabel = 'Very Low';
                    colorClass = 'bg-blue-100 text-blue-800';
                }

                return (
                    <span className={`px-2 py-1 text-xs rounded font-medium ${colorClass}`}>
                        {shortLabel}
                    </span>
                );
            },
            csvValue: (model) => model.risk_tier?.label || ''
        },
        usage_frequency: {
            header: 'Usage Frequency',
            sortKey: 'usage_frequency.label',
            cell: (model) => model.usage_frequency?.label || '-',
            csvValue: (model) => model.usage_frequency?.label || ''
        },
        methodology: {
            header: 'Methodology',
            sortKey: 'methodology.name',
            cell: (model) => model.methodology?.name || '-',
            csvValue: (model) => model.methodology?.name || ''
        },
        ownership_type: {
            header: 'Ownership Type',
            sortKey: 'ownership_type.label',
            cell: (model) => model.ownership_type?.label || '-',
            csvValue: (model) => model.ownership_type?.label || ''
        },
        model_type: {
            header: 'Model Type',
            sortKey: 'model_type.name',
            cell: (model) => model.model_type?.name || '-',
            csvValue: (model) => model.model_type?.name || ''
        },
        regulatory_categories: {
            header: 'Regulatory Categories',
            cell: (model) => model.regulatory_categories?.length > 0
                ? model.regulatory_categories.map(rc => rc.label).join(', ')
                : '-',
            csvValue: (model) => model.regulatory_categories?.map(rc => rc.label).join('; ') || ''
        },
        scorecard_outcome: {
            header: 'Scorecard Outcome',
            sortKey: 'scorecard_outcome',
            cell: (model) => model.scorecard_outcome ? (
                <span className={`px-2 py-1 text-xs rounded font-medium ${
                    model.scorecard_outcome === 'Green' ? 'bg-green-100 text-green-800' :
                    model.scorecard_outcome === 'Green-' ? 'bg-green-100 text-green-700' :
                    model.scorecard_outcome === 'Yellow+' ? 'bg-yellow-100 text-yellow-800' :
                    model.scorecard_outcome === 'Yellow' ? 'bg-yellow-100 text-yellow-700' :
                    model.scorecard_outcome === 'Yellow-' ? 'bg-orange-100 text-orange-800' :
                    model.scorecard_outcome === 'Red' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-700'
                }`}>
                    {model.scorecard_outcome}
                </span>
            ) : (
                <span className="text-gray-400">-</span>
            ),
            csvValue: (model) => model.scorecard_outcome || ''
        },
        residual_risk: {
            header: 'Residual Risk',
            sortKey: 'residual_risk',
            cell: (model) => model.residual_risk ? (
                <span className={`px-2 py-1 text-xs rounded font-medium ${
                    model.residual_risk === 'High' ? 'bg-red-100 text-red-800' :
                    model.residual_risk === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                    model.residual_risk === 'Low' ? 'bg-green-100 text-green-800' :
                    'bg-gray-100 text-gray-700'
                }`}>
                    {model.residual_risk}
                </span>
            ) : (
                <span className="text-gray-400">-</span>
            ),
            csvValue: (model) => model.residual_risk || ''
        },
        approval_status: {
            header: 'Approval Status',
            sortKey: 'approval_status',
            cell: (model) => {
                if (!model.approval_status) {
                    return <span className="text-gray-400">-</span>;
                }
                // Badge colors based on status
                const badgeClasses = {
                    'NEVER_VALIDATED': 'bg-gray-100 text-gray-800',
                    'APPROVED': 'bg-green-100 text-green-800',
                    'INTERIM_APPROVED': 'bg-yellow-100 text-yellow-800',
                    'VALIDATION_IN_PROGRESS': 'bg-blue-100 text-blue-800',
                    'EXPIRED': 'bg-red-100 text-red-800'
                };
                const className = badgeClasses[model.approval_status as keyof typeof badgeClasses] || 'bg-gray-100 text-gray-700';
                return (
                    <span className={`px-2 py-1 text-xs rounded font-medium ${className}`}>
                        {model.approval_status_label || model.approval_status}
                    </span>
                );
            },
            csvValue: (model) => model.approval_status_label || model.approval_status || ''
        },
        description: {
            header: 'Description',
            cell: (model) => model.description ? (
                <span className="truncate max-w-xs block" title={model.description}>
                    {model.description.length > 50 ? model.description.slice(0, 50) + '...' : model.description}
                </span>
            ) : '-',
            csvValue: (model) => model.description || ''
        },
        products_covered: {
            header: 'Products Covered',
            cell: (model) => model.products_covered ? (
                <span className="truncate max-w-xs block" title={model.products_covered}>
                    {model.products_covered.length > 50 ? model.products_covered.slice(0, 50) + '...' : model.products_covered}
                </span>
            ) : '-',
            csvValue: (model) => model.products_covered || ''
        },
        development_type: {
            header: 'Development Type',
            sortKey: 'development_type',
            cell: (model) => model.development_type,
            csvValue: (model) => model.development_type
        },
        wholly_owned_region: {
            header: 'Wholly Owned Region',
            sortKey: 'wholly_owned_region.name',
            cell: (model) => model.wholly_owned_region
                ? `${model.wholly_owned_region.name} (${model.wholly_owned_region.code})`
                : '-',
            csvValue: (model) => model.wholly_owned_region
                ? `${model.wholly_owned_region.name} (${model.wholly_owned_region.code})`
                : ''
        },
        row_approval_status: {
            header: 'Inventory Acceptance',
            sortKey: 'row_approval_status',
            cell: (model) => {
                const status = model.row_approval_status;
                if (!status) return 'Accepted';
                if (status === 'Draft') return 'Draft';
                if (status === 'needs_revision') return 'Needs Revision';
                if (status === 'rejected') return 'Rejected';
                return status;
            },
            csvValue: (model) => {
                const status = model.row_approval_status;
                if (!status) return 'Accepted';
                if (status === 'Draft') return 'Draft';
                if (status === 'needs_revision') return 'Needs Revision';
                if (status === 'rejected') return 'Rejected';
                return status;
            }
        },
        created_at: {
            header: 'Created Date',
            sortKey: 'created_at',
            cell: (model) => model.created_at?.split('T')[0] || '-',
            csvValue: (model) => model.created_at?.split('T')[0] || ''
        },
        updated_at: {
            header: 'Modified On',
            sortKey: 'updated_at',
            cell: (model) => model.updated_at?.split('T')[0] || '-',
            csvValue: (model) => model.updated_at?.split('T')[0] || ''
        },
        model_last_updated: {
            header: 'Model Last Updated',
            sortKey: 'model_last_updated',
            cell: (model) => model.model_last_updated ? model.model_last_updated.split('T')[0] : '',
            csvValue: (model) => model.model_last_updated ? model.model_last_updated.split('T')[0] : ''
        },
        // Revalidation computed fields
        validation_status: {
            header: 'Validation Status',
            sortKey: 'validation_status',
            cell: (model) => {
                if (!model.validation_status) return <span className="text-gray-400">-</span>;
                const colors: Record<string, string> = {
                    current: 'bg-green-100 text-green-800',
                    due_soon: 'bg-yellow-100 text-yellow-800',
                    overdue: 'bg-red-100 text-red-800'
                };
                return (
                    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[model.validation_status] || ''}`}>
                        {model.validation_status.replace('_', ' ')}
                    </span>
                );
            },
            csvValue: (model) => model.validation_status || ''
        },
        next_validation_due_date: {
            header: 'Next Validation Due',
            sortKey: 'next_validation_due_date',
            cell: (model) => model.next_validation_due_date || <span className="text-gray-400">-</span>,
            csvValue: (model) => model.next_validation_due_date || ''
        },
        days_until_validation_due: {
            header: 'Days Until Due',
            sortKey: 'days_until_validation_due',
            cell: (model) => model.days_until_validation_due !== null
                ? model.days_until_validation_due.toString()
                : <span className="text-gray-400">-</span>,
            csvValue: (model) => model.days_until_validation_due?.toString() || ''
        },
        last_validation_date: {
            header: 'Last Validation',
            sortKey: 'last_validation_date',
            cell: (model) => model.last_validation_date || <span className="text-gray-400">-</span>,
            csvValue: (model) => model.last_validation_date || ''
        },
        days_overdue: {
            header: 'Days Overdue',
            sortKey: 'days_overdue',
            cell: (model) => {
                if (!model.days_overdue || model.days_overdue === 0) return <span className="text-gray-400">-</span>;
                return (
                    <span className="text-red-600 font-medium">{model.days_overdue}</span>
                );
            },
            csvValue: (model) => model.days_overdue?.toString() || '0'
        },
        penalty_notches: {
            header: 'Penalty Notches',
            sortKey: 'penalty_notches',
            cell: (model) => {
                if (!model.penalty_notches || model.penalty_notches === 0) return <span className="text-gray-400">-</span>;
                return (
                    <span className="text-orange-600 font-medium">+{model.penalty_notches}</span>
                );
            },
            csvValue: (model) => model.penalty_notches?.toString() || '0'
        },
        adjusted_scorecard_outcome: {
            header: 'Adjusted Outcome',
            sortKey: 'adjusted_scorecard_outcome',
            cell: (model) => {
                if (!model.adjusted_scorecard_outcome) return <span className="text-gray-400">-</span>;
                const colors: Record<string, string> = {
                    'Green': 'bg-green-100 text-green-800',
                    'Green-': 'bg-green-100 text-green-700',
                    'Yellow+': 'bg-yellow-100 text-yellow-800',
                    'Yellow': 'bg-yellow-100 text-yellow-700',
                    'Yellow-': 'bg-orange-100 text-orange-800',
                    'Red': 'bg-red-100 text-red-800'
                };
                return (
                    <span className={`px-2 py-1 text-xs rounded font-medium ${colors[model.adjusted_scorecard_outcome] || 'bg-gray-100 text-gray-700'}`}>
                        {model.adjusted_scorecard_outcome}
                    </span>
                );
            },
            csvValue: (model) => model.adjusted_scorecard_outcome || ''
        }
    };

    const saveCurrentView = async () => {
        if (!newViewName.trim()) {
            alert('Please enter a name for this view.');
            return;
        }

        try {
            if (editingViewId) {
                // Update existing view
                await exportViewsApi.update(editingViewId, {
                    view_name: newViewName,
                    columns: selectedColumns,
                    is_public: newViewIsPublic,
                    description: newViewDescription || undefined
                });
            } else {
                // Create new view
                const newView = await exportViewsApi.create({
                    entity_type: 'models',
                    view_name: newViewName,
                    columns: selectedColumns,
                    is_public: newViewIsPublic,
                    description: newViewDescription || undefined
                });
                setCurrentViewId(`db_${newView.view_id}`);
            }

            // Reload views from API
            await loadExportViews();

            // Reset form
            setNewViewName('');
            setNewViewDescription('');
            setNewViewIsPublic(false);
            setShowSaveViewModal(false);
            setEditingViewId(null);
        } catch (error: any) {
            console.error('Failed to save view:', error);
            alert(`Failed to save view: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
        }
    };

    const deleteView = async (viewId: string) => {
        const view = allViews[viewId];
        if (view.isDefault) {
            alert('Cannot delete default views.');
            return;
        }

        if (!confirm(`Delete view "${view.name}"?`)) {
            return;
        }

        try {
            // Extract numeric ID from db_X format
            const numericId = parseInt(viewId.replace('db_', ''));
            await exportViewsApi.delete(numericId);

            // Reload views
            await loadExportViews();

            // If deleted view was current, switch to default
            if (currentViewId === viewId) {
                setCurrentViewId('default');
                loadView('default');
            }
        } catch (error: any) {
            console.error('Failed to delete view:', error);
            alert(`Failed to delete view: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
        }
    };

    const startEditView = (viewId: string) => {
        const view = allViews[viewId];
        if (view.isDefault) {
            alert('Cannot edit default views. You can save a copy with a new name.');
            return;
        }
        // Extract numeric ID from db_X format
        const numericId = parseInt(viewId.replace('db_', ''));
        setEditingViewId(numericId);
        setNewViewName(view.name);
        if (view.dbView) {
            setNewViewDescription(view.dbView.description || '');
            setNewViewIsPublic(view.dbView.is_public);
        }
        setShowSaveViewModal(true);
    };

    const handleExportCSV = () => {
        if (selectedColumns.length === 0) {
            alert('Please select at least one column to export.');
            return;
        }

        try {
            // Generate CSV headers using column renderers
            const headers = selectedColumns
                .filter(colKey => columnRenderers[colKey])
                .map(colKey => columnRenderers[colKey].header);

            // Generate CSV rows using column renderers
            const rows = sortedData.map(model => {
                const row: string[] = [];
                selectedColumns.forEach(colKey => {
                    const renderer = columnRenderers[colKey];
                    let value = renderer ? renderer.csvValue(model) : '';
                    // Escape quotes and commas for CSV
                    value = value.replace(/"/g, '""');
                    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
                        value = `"${value}"`;
                    }
                    row.push(value);
                });
                return row.join(',');
            });

            // Combine headers and rows
            const csv = [headers.join(','), ...rows].join('\n');

            // Create blob and download
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;

            // Generate filename with current date
            const date = new Date().toISOString().split('T')[0];
            link.setAttribute('download', `models_${date}.csv`);

            // Trigger download
            document.body.appendChild(link);
            link.click();

            // Cleanup
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);

            // Close modal
            setShowExportModal(false);
        } catch (error) {
            console.error('Failed to export CSV:', error);
            alert('Failed to export CSV. Please try again.');
        }
    };
    const totalRows = sortedData.length;
    const startItem = totalRows === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const endItem = Math.min(currentPage * pageSize, totalRows);

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div data-testid="models-page">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold">Models</h2>
                    <div className="flex gap-2">
                        <button onClick={() => setShowColumnsModal(true)} className="btn-secondary">
                            Columns ({selectedColumns.length})
                        </button>
                        <button onClick={() => setShowExportModal(true)} className="btn-secondary">
                            Export CSV
                        </button>
                        <button onClick={() => setShowForm(true)} className="btn-primary">
                            + Add Model
                        </button>
                    </div>
                </div>

                {/* KPI Drill-Down Banner */}
                {kpiDrillDownActive && kpiDrillDownIds && (
                    <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div>
                                <span className="font-medium text-blue-800">KPI Drill-Down View</span>
                                <span className="text-blue-600 ml-2">
                                    Showing {kpiDrillDownIds.length} model{kpiDrillDownIds.length !== 1 ? 's' : ''} from KPI report
                                </span>
                            </div>
                        </div>
                        <button
                            onClick={clearKpiDrillDown}
                            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                        >
                            Clear Filter
                        </button>
                    </div>
                )}

                {showForm && (
                    <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                        <h3 className="text-lg font-bold mb-4">Create New Model</h3>
                        <form onSubmit={handleSubmit}>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="mb-4">
                                    <label htmlFor="model_name" className="block text-sm font-medium mb-2">Model Name</label>
                                    <input
                                        id="model_name"
                                        type="text"
                                        className="input-field"
                                        value={formData.model_name}
                                        onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                                        required
                                    />
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="development_type" className="block text-sm font-medium mb-2">Development Type</label>
                                    <select
                                        id="development_type"
                                        className="input-field"
                                        value={formData.development_type}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            development_type: e.target.value,
                                            vendor_id: e.target.value === 'In-House' ? null : formData.vendor_id
                                        })}
                                    >
                                        <option value="In-House">In-House</option>
                                        <option value="Third-Party">Third-Party</option>
                                    </select>
                                </div>

                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">Classification</label>
                                    <div className="flex items-center gap-4">
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="radio"
                                                name="is_model"
                                                checked={formData.is_model === true}
                                                onChange={() => setFormData({ ...formData, is_model: true })}
                                                className="w-4 h-4 text-blue-600"
                                            />
                                            <span className="text-sm">Model</span>
                                        </label>
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="radio"
                                                name="is_model"
                                                checked={formData.is_model === false}
                                                onChange={() => setFormData({ ...formData, is_model: false })}
                                                className="w-4 h-4 text-blue-600"
                                            />
                                            <span className="text-sm">Non-Model</span>
                                        </label>
                                    </div>
                                    <p className="text-xs text-gray-500 mt-1">Non-models are tools/applications that use quantitative methods but don't meet the regulatory definition of a model</p>
                                </div>

                                {/* MRSA Classification - only shown when is_model=false */}
                                {formData.is_model === false && (
                                    <div className="mb-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                                        <h4 className="text-sm font-medium text-purple-800 mb-3">MRSA Classification</h4>

                                        <div className="mb-3">
                                            <label className="flex items-center gap-2 cursor-pointer">
                                                <input
                                                    type="checkbox"
                                                    checked={formData.is_mrsa}
                                                    onChange={(e) => setFormData({
                                                        ...formData,
                                                        is_mrsa: e.target.checked,
                                                        // Clear MRSA fields when unchecked
                                                        mrsa_risk_level_id: e.target.checked ? formData.mrsa_risk_level_id : null,
                                                        mrsa_risk_rationale: e.target.checked ? formData.mrsa_risk_rationale : ''
                                                    })}
                                                    className="w-4 h-4 text-purple-600 rounded"
                                                />
                                                <span className="text-sm font-medium">Mark as MRSA (Model Risk-Sensitive Application)</span>
                                            </label>
                                            <p className="text-xs text-gray-500 mt-1 ml-6">
                                                MRSAs are non-model applications that exhibit model-like risk characteristics and require governance oversight
                                            </p>
                                        </div>

                                        {formData.is_mrsa && (
                                            <>
                                                <div className="mb-3">
                                                    <label htmlFor="mrsa_risk_level_id" className="block text-sm font-medium mb-1">
                                                        MRSA Risk Level <span className="text-red-500">*</span>
                                                    </label>
                                                    <select
                                                        id="mrsa_risk_level_id"
                                                        className="input-field"
                                                        value={formData.mrsa_risk_level_id || ''}
                                                        onChange={(e) => setFormData({
                                                            ...formData,
                                                            mrsa_risk_level_id: e.target.value ? parseInt(e.target.value) : null
                                                        })}
                                                        required
                                                    >
                                                        <option value="">Select Risk Level</option>
                                                        {mrsaRiskLevels.map(level => (
                                                            <option key={level.value_id} value={level.value_id}>
                                                                {level.label}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>

                                                {/* IRP Warning for High-Risk MRSAs */}
                                                {formData.mrsa_risk_level_id && mrsaRiskLevels.find(
                                                    l => l.value_id === formData.mrsa_risk_level_id && l.requires_irp
                                                ) && (
                                                    <div className="mb-3 p-2 bg-amber-50 border border-amber-200 rounded flex items-start gap-2">
                                                        <span className="text-amber-600">⚠️</span>
                                                        <p className="text-xs text-amber-800">
                                                            High-Risk MRSAs require Independent Review Process (IRP) coverage.
                                                            After creation, assign this MRSA to an IRP via the IRPs management page.
                                                        </p>
                                                    </div>
                                                )}

                                                <div className="mb-3">
                                                    <label htmlFor="mrsa_risk_rationale" className="block text-sm font-medium mb-1">
                                                        Risk Rationale <span className="text-red-500">*</span>
                                                    </label>
                                                    <textarea
                                                        id="mrsa_risk_rationale"
                                                        className="input-field"
                                                        rows={3}
                                                        value={formData.mrsa_risk_rationale}
                                                        onChange={(e) => setFormData({
                                                            ...formData,
                                                            mrsa_risk_rationale: e.target.value
                                                        })}
                                                        placeholder="Provide justification for the MRSA risk classification..."
                                                        required
                                                    />
                                                    <p className="text-xs text-gray-500 mt-1">
                                                        Explain why this application is classified at this risk level
                                                    </p>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                )}

                                <div className="mb-4">
                                    <label htmlFor="owner_id" className="block text-sm font-medium mb-2">Owner (Required)</label>
                                    <select
                                        id="owner_id"
                                        className="input-field"
                                        value={formData.owner_id || ''}
                                        onChange={(e) => setFormData({ ...formData, owner_id: e.target.value ? parseInt(e.target.value) : 0 })}
                                        required
                                    >
                                        <option value="">Select Owner</option>
                                        {users.map(u => (
                                            <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="developer_id" className="block text-sm font-medium mb-2">Developer (Optional)</label>
                                    <select
                                        id="developer_id"
                                        className="input-field"
                                        value={formData.developer_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            developer_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">None</option>
                                        {users.map(u => (
                                            <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
                                        ))}
                                    </select>
                                </div>

                                {formData.development_type === 'Third-Party' && (
                                    <div className="mb-4">
                                        <label htmlFor="vendor_id" className="block text-sm font-medium mb-2">Vendor (Required for Third-Party)</label>
                                        <select
                                            id="vendor_id"
                                            className="input-field"
                                            value={formData.vendor_id || ''}
                                            onChange={(e) => setFormData({
                                                ...formData,
                                                vendor_id: e.target.value ? parseInt(e.target.value) : null
                                            })}
                                            required
                                        >
                                            <option value="">Select Vendor</option>
                                            {vendors.map(v => (
                                                <option key={v.vendor_id} value={v.vendor_id}>{v.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                <div className="mb-4">
                                    <label htmlFor="model_type_id" className="block text-sm font-medium mb-2">
                                        Model Type
                                    </label>
                                    <select
                                        id="model_type_id"
                                        className="input-field"
                                        value={formData.model_type_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            model_type_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">Select Model Type</option>
                                        {modelTypes.map(category => (
                                            <optgroup key={category.category_id} label={category.name}>
                                                {category.model_types.map(type => (
                                                    <option key={type.type_id} value={type.type_id}>
                                                        {type.name}
                                                    </option>
                                                ))}
                                            </optgroup>
                                        ))}
                                    </select>
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="wholly_owned_region_id" className="block text-sm font-medium mb-2">
                                        Wholly-Owned By Region
                                    </label>
                                    <select
                                        id="wholly_owned_region_id"
                                        className="input-field"
                                        value={formData.wholly_owned_region_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            wholly_owned_region_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">None (Global)</option>
                                        {regions.map(r => (
                                            <option key={r.region_id} value={r.region_id}>{r.name} ({r.code})</option>
                                        ))}
                                    </select>
                                    <p className="text-xs text-gray-500 mt-1">
                                        Select a region if this model is wholly-owned by that region's governance structure
                                    </p>
                                </div>

                                <div className="mb-4">
                                    <label className="block text-sm font-medium mb-2">
                                        Deployment Regions (Optional)
                                    </label>
                                    <MultiSelectDropdown
                                        label=""
                                        placeholder="Select Regions"
                                        options={regions.map(r => ({
                                            value: r.region_id,
                                            label: `${r.name} (${r.code})`
                                        }))}
                                        selectedValues={formData.region_ids}
                                        onChange={(values) => setFormData({
                                            ...formData,
                                            region_ids: values as number[]
                                        })}
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        Select regions where this model will be deployed. The wholly-owned region (if selected) will be automatically included.
                                    </p>
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="usage_frequency_id" className="block text-sm font-medium mb-2">
                                        Typical Usage Frequency <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        id="usage_frequency_id"
                                        className="input-field"
                                        value={formData.usage_frequency_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            usage_frequency_id: e.target.value ? parseInt(e.target.value) : 0
                                        })}
                                        required
                                    >
                                        <option value="">Select Usage Frequency</option>
                                        {usageFrequencies
                                            .filter(v => v.is_active)
                                            .sort((a: any, b: any) => a.sort_order - b.sort_order)
                                            .map((v: any) => (
                                                <option key={v.value_id} value={v.value_id}>{v.label}</option>
                                            ))}
                                    </select>
                                    <p className="text-xs text-gray-500 mt-1">
                                        How often is this model typically used in production?
                                    </p>
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="status" className="block text-sm font-medium mb-2">Status</label>
                                    <select
                                        id="status"
                                        className="input-field"
                                        value={formData.status}
                                        onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                                    >
                                        <option value="In Development">In Development</option>
                                        <option value="Active">Active</option>
                                        <option value="Retired">Retired</option>
                                    </select>
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="initial_version_number" className="block text-sm font-medium mb-2">
                                        Initial Version Number (Optional)
                                    </label>
                                    <input
                                        id="initial_version_number"
                                        type="text"
                                        className="input-field"
                                        placeholder="1.0"
                                        value={formData.initial_version_number}
                                        onChange={(e) => setFormData({ ...formData, initial_version_number: e.target.value })}
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        Starting version number for this model (defaults to 1.0 if not specified)
                                    </p>
                                </div>

                                <div className="mb-4">
                                    <label htmlFor="initial_implementation_date" className="block text-sm font-medium mb-2">
                                        Implementation Date (Optional)
                                    </label>
                                    <input
                                        id="initial_implementation_date"
                                        type="date"
                                        className="input-field"
                                        value={formData.initial_implementation_date}
                                        onChange={(e) => setFormData({ ...formData, initial_implementation_date: e.target.value })}
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        Date when this model was (or will be) implemented in production
                                    </p>
                                </div>
                            </div>

                        <div className="mb-4">
                            <label htmlFor="description" className="block text-sm font-medium mb-2">Description and Purpose</label>
                            <textarea
                                id="description"
                                className="input-field"
                                rows={3}
                                placeholder="Describe what this model does and its business purpose..."
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            />
                        </div>
                        <div className="mb-4">
                            <label htmlFor="products_covered" className="block text-sm font-medium mb-2">Products Covered</label>
                            <textarea
                                id="products_covered"
                                className="input-field"
                                rows={2}
                                placeholder="List products, portfolios, or lines of business covered by this model..."
                                value={formData.products_covered}
                                onChange={(e) => setFormData({ ...formData, products_covered: e.target.value })}
                            />
                        </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-2">
                                    Model Users ({formData.user_ids.length} selected)
                                </label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        className="input-field"
                                        placeholder="Search users by name or email..."
                                        value={userSearchTerm}
                                        onChange={(e) => setUserSearchTerm(e.target.value)}
                                    />
                                    {userSearchTerm && getFilteredUsers().length > 0 && (
                                        <div className="absolute z-10 w-full bg-white border rounded shadow-lg max-h-40 overflow-y-auto">
                                            {getFilteredUsers().map(u => (
                                                <button
                                                    key={u.user_id}
                                                    type="button"
                                                    className="w-full text-left px-3 py-2 hover:bg-gray-100"
                                                    onClick={() => addUserToModel(u.user_id)}
                                                >
                                                    {u.full_name} ({u.email})
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                {formData.user_ids.length > 0 && (
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {formData.user_ids.map(uid => {
                                            const selectedUser = users.find(u => u.user_id === uid);
                                            return selectedUser ? (
                                                <div key={uid} className="bg-blue-100 text-blue-800 px-2 py-1 rounded flex items-center gap-1">
                                                    <span className="text-sm">{selectedUser.full_name}</span>
                                                    <button
                                                        type="button"
                                                        onClick={() => removeUserFromModel(uid)}
                                                        className="text-blue-600 hover:text-blue-800 font-bold"
                                                    >
                                                        ×
                                                    </button>
                                                </div>
                                            ) : null;
                                        })}
                                    </div>
                                )}
                            </div>

                            {/* Auto-create Validation Project Section */}
                            <div className="mb-4 border-t pt-4">
                                <div className="mb-4">
                                    <label className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            checked={formData.auto_create_validation}
                                            onChange={(e) => {
                                                const isChecked = e.target.checked;
                                                // Find "Initial" validation type and set as default
                                                const initialValidationType = validationTypes.find(vt =>
                                                    vt.code === 'INITIAL' || vt.label.toLowerCase().includes('initial')
                                                );
                                                setFormData({
                                                    ...formData,
                                                    auto_create_validation: isChecked,
                                                    validation_request_type_id: isChecked && initialValidationType ? initialValidationType.value_id : 0
                                                });
                                            }}
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                        />
                                        <span className="text-sm font-medium">Auto-create validation project upon model creation</span>
                                    </label>
                                    <p className="text-xs text-gray-500 mt-1 ml-6">
                                        Automatically create a validation project for this model when it is created
                                    </p>
                                </div>

                                {formData.auto_create_validation && (
                                    <div className="ml-6 space-y-4 p-4 bg-gray-50 rounded">
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <label htmlFor="validation_request_type_id" className="block text-sm font-medium mb-2">
                                                    Validation Type <span className="text-red-500">*</span>
                                                </label>
                                                <select
                                                    id="validation_request_type_id"
                                                    className="input-field"
                                                    value={formData.validation_request_type_id || ''}
                                                    onChange={(e) => setFormData({ ...formData, validation_request_type_id: e.target.value ? parseInt(e.target.value) : 0 })}
                                                    required={formData.auto_create_validation}
                                                >
                                                    <option value="">-- Select Validation Type --</option>
                                                    {validationTypes.map(vt => (
                                                        <option key={vt.value_id} value={vt.value_id}>
                                                            {vt.label}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>

                                            <div>
                                                <label htmlFor="validation_request_priority_id" className="block text-sm font-medium mb-2">
                                                    Priority <span className="text-red-500">*</span>
                                                </label>
                                                <select
                                                    id="validation_request_priority_id"
                                                    className="input-field"
                                                    value={formData.validation_request_priority_id || ''}
                                                    onChange={(e) => setFormData({ ...formData, validation_request_priority_id: e.target.value ? parseInt(e.target.value) : 0 })}
                                                    required={formData.auto_create_validation}
                                                >
                                                    <option value="">-- Select Priority --</option>
                                                    {validationPriorities.map(vp => (
                                                        <option key={vp.value_id} value={vp.value_id}>
                                                            {vp.label}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>
                                        </div>

                                        <div>
                                            <label htmlFor="validation_request_target_date" className="block text-sm font-medium mb-2">
                                                Target Completion Date (Optional)
                                            </label>
                                            <input
                                                id="validation_request_target_date"
                                                type="date"
                                                className="input-field"
                                                value={formData.validation_request_target_date}
                                                onChange={(e) => setFormData({ ...formData, validation_request_target_date: e.target.value })}
                                            />
                                        </div>

                                        <div>
                                            <label htmlFor="validation_request_trigger_reason" className="block text-sm font-medium mb-2">
                                                Trigger Reason (Optional)
                                            </label>
                                            <textarea
                                                id="validation_request_trigger_reason"
                                                className="input-field"
                                                rows={2}
                                                placeholder="Reason for validation project..."
                                                value={formData.validation_request_trigger_reason}
                                                onChange={(e) => setFormData({ ...formData, validation_request_trigger_reason: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-2">
                                <button type="submit" className="btn-primary">Create</button>
                                <button type="button" onClick={handleCancelForm} className="btn-secondary">
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                )}

                {/* Export Column Selection Modal */}
                {showExportModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
                            <div className="p-6 border-b border-gray-200">
                                <h3 className="text-xl font-bold">Select Columns to Export</h3>
                                <p className="text-sm text-gray-600 mt-1">
                                    Choose which columns to include in the CSV export. Your selection will be saved for future exports.
                                </p>
                            </div>

                            <div className="flex-1 overflow-y-auto p-6">
                                {/* View Selector */}
                                <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                                    <label className="block text-sm font-medium mb-2">Saved Views</label>
                                    <div className="flex gap-2">
                                        <select
                                            value={currentViewId}
                                            onChange={(e) => loadView(e.target.value)}
                                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                            <optgroup label="Default Views">
                                                {Object.values(allViews)
                                                    .filter((v: any) => v.isDefault)
                                                    .map((view: any) => (
                                                        <option key={view.id} value={view.id}>
                                                            {view.name} ({view.columns.length} columns)
                                                        </option>
                                                    ))}
                                            </optgroup>
                                            {Object.values(allViews).some((v: any) => !v.isDefault) && (
                                                <optgroup label="My Views">
                                                    {Object.values(allViews)
                                                        .filter((v: any) => !v.isDefault && !v.isPublic)
                                                        .map((view: any) => (
                                                            <option key={view.id} value={view.id}>
                                                                {view.name} ({view.columns.length} columns)
                                                            </option>
                                                        ))}
                                                </optgroup>
                                            )}
                                            {Object.values(allViews).some((v: any) => v.isPublic) && (
                                                <optgroup label="Public Views">
                                                    {Object.values(allViews)
                                                        .filter((v: any) => !v.isDefault && v.isPublic)
                                                        .map((view: any) => (
                                                            <option key={view.id} value={view.id}>
                                                                {view.name} ({view.columns.length} columns) 🌐
                                                            </option>
                                                        ))}
                                                </optgroup>
                                            )}
                                        </select>
                                        <button
                                            onClick={() => {
                                                setNewViewName('');
                                                setNewViewDescription('');
                                                setNewViewIsPublic(false);
                                                setEditingViewId(null);
                                                setShowSaveViewModal(true);
                                            }}
                                            className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm whitespace-nowrap"
                                        >
                                            💾 Save as New
                                        </button>
                                        {!allViews[currentViewId]?.isDefault && (
                                            <>
                                                <button
                                                    onClick={() => startEditView(currentViewId)}
                                                    className="px-3 py-2 border border-gray-300 rounded-md hover:bg-gray-50 text-sm"
                                                    title="Rename view"
                                                >
                                                    ✏️
                                                </button>
                                                <button
                                                    onClick={() => deleteView(currentViewId)}
                                                    className="px-3 py-2 border border-red-300 text-red-600 rounded-md hover:bg-red-50 text-sm"
                                                    title="Delete view"
                                                >
                                                    🗑️
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>

                                <div className="flex gap-2 mb-4">
                                    <button
                                        onClick={selectAllColumns}
                                        className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50"
                                    >
                                        Select All
                                    </button>
                                    <button
                                        onClick={deselectAllColumns}
                                        className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50"
                                    >
                                        Deselect All
                                    </button>
                                    <div className="ml-auto text-sm text-gray-600">
                                        {selectedColumns.length} of {availableColumns.length} columns selected
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    {availableColumns.map(col => (
                                        <label
                                            key={col.key}
                                            className="flex items-center gap-2 p-3 border border-gray-200 rounded hover:bg-gray-50 cursor-pointer"
                                        >
                                            <input
                                                type="checkbox"
                                                checked={selectedColumns.includes(col.key)}
                                                onChange={() => toggleColumn(col.key)}
                                                className="w-4 h-4 text-blue-600 rounded"
                                            />
                                            <span className="text-sm">{col.label}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="p-6 border-t border-gray-200 flex justify-end gap-2">
                                <button
                                    onClick={() => setShowExportModal(false)}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleExportCSV}
                                    className="btn-primary"
                                    disabled={selectedColumns.length === 0}
                                >
                                    Export {selectedColumns.length > 0 ? `(${selectedColumns.length} columns)` : ''}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Save View Modal */}
                {showSaveViewModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                            <div className="p-6 border-b border-gray-200">
                                <h3 className="text-xl font-bold">
                                    {editingViewId ? 'Rename View' : 'Save Column Selection as View'}
                                </h3>
                                <p className="text-sm text-gray-600 mt-1">
                                    {editingViewId
                                        ? 'Enter a new name for this view.'
                                        : 'Give your current column selection a name so you can quickly load it later.'}
                                </p>
                            </div>

                            <div className="p-6 space-y-4">
                                <div>
                                    <label className="block text-sm font-medium mb-2">View Name *</label>
                                    <input
                                        type="text"
                                        value={newViewName}
                                        onChange={(e) => setNewViewName(e.target.value)}
                                        placeholder="e.g., Compliance Report"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        autoFocus
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium mb-2">Description (optional)</label>
                                    <textarea
                                        value={newViewDescription}
                                        onChange={(e) => setNewViewDescription(e.target.value)}
                                        placeholder="What is this view for?"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        rows={2}
                                    />
                                </div>

                                <div>
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={newViewIsPublic}
                                            onChange={(e) => setNewViewIsPublic(e.target.checked)}
                                            className="w-4 h-4 text-blue-600 rounded"
                                        />
                                        <span className="text-sm font-medium">
                                            Make this view public 🌐
                                        </span>
                                    </label>
                                    <p className="text-xs text-gray-500 mt-1 ml-6">
                                        Public views can be seen and used by all users, but only you can edit or delete them.
                                    </p>
                                </div>

                                {!editingViewId && (
                                    <p className="text-xs text-gray-500 bg-blue-50 p-2 rounded">
                                        Currently selected: {selectedColumns.length} column{selectedColumns.length !== 1 ? 's' : ''}
                                    </p>
                                )}
                            </div>

                            <div className="p-6 border-t border-gray-200 flex justify-end gap-2">
                                <button
                                    onClick={() => {
                                        setShowSaveViewModal(false);
                                        setNewViewName('');
                                        setNewViewDescription('');
                                        setNewViewIsPublic(false);
                                        setEditingViewId(null);
                                    }}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={saveCurrentView}
                                    className="btn-primary"
                                >
                                    {editingViewId ? 'Rename' : 'Save View'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Column Picker Modal */}
                {showColumnsModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
                            <div className="p-6 border-b border-gray-200">
                                <h3 className="text-xl font-bold">Customize Table Columns</h3>
                                <p className="text-sm text-gray-600 mt-1">
                                    Select which columns to display in the table. This also affects CSV exports.
                                </p>
                            </div>

                            <div className="flex-1 overflow-y-auto p-6">
                                {/* View Selector */}
                                <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                                    <label className="block text-sm font-medium mb-2">Saved Views</label>
                                    <div className="flex gap-2">
                                        <select
                                            value={currentViewId}
                                            onChange={(e) => loadView(e.target.value)}
                                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                            <optgroup label="Default Views">
                                                {Object.values(allViews)
                                                    .filter((v: any) => v.isDefault)
                                                    .map((view: any) => (
                                                        <option key={view.id} value={view.id}>
                                                            {view.name} ({view.columns.length} columns)
                                                        </option>
                                                    ))}
                                            </optgroup>
                                            {Object.values(allViews).some((v: any) => !v.isDefault && !v.isPublic) && (
                                                <optgroup label="My Views">
                                                    {Object.values(allViews)
                                                        .filter((v: any) => !v.isDefault && !v.isPublic)
                                                        .map((view: any) => (
                                                            <option key={view.id} value={view.id}>
                                                                {view.name} ({view.columns.length} columns)
                                                            </option>
                                                        ))}
                                                </optgroup>
                                            )}
                                            {Object.values(allViews).some((v: any) => v.isPublic) && (
                                                <optgroup label="Public Views">
                                                    {Object.values(allViews)
                                                        .filter((v: any) => !v.isDefault && v.isPublic)
                                                        .map((view: any) => (
                                                            <option key={view.id} value={view.id}>
                                                                {view.name} ({view.columns.length} columns) 🌐
                                                            </option>
                                                        ))}
                                                </optgroup>
                                            )}
                                        </select>
                                        <button
                                            onClick={() => {
                                                setNewViewName('');
                                                setNewViewDescription('');
                                                setNewViewIsPublic(false);
                                                setEditingViewId(null);
                                                setShowSaveViewModal(true);
                                            }}
                                            className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm whitespace-nowrap"
                                        >
                                            Save as New
                                        </button>
                                    </div>
                                </div>

                                <div className="flex gap-2 mb-4">
                                    <button
                                        onClick={selectAllColumns}
                                        className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50"
                                    >
                                        Select All
                                    </button>
                                    <button
                                        onClick={deselectAllColumns}
                                        className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50"
                                    >
                                        Deselect All
                                    </button>
                                    <button
                                        onClick={() => loadView('default')}
                                        className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-50"
                                    >
                                        Reset to Default
                                    </button>
                                    <div className="ml-auto text-sm text-gray-600">
                                        {selectedColumns.length} of {availableColumns.length} columns selected
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    {availableColumns.map(col => (
                                        <label
                                            key={col.key}
                                            className="flex items-center gap-2 p-3 border border-gray-200 rounded hover:bg-gray-50 cursor-pointer"
                                        >
                                            <input
                                                type="checkbox"
                                                checked={selectedColumns.includes(col.key)}
                                                onChange={() => toggleColumn(col.key)}
                                                className="w-4 h-4 text-blue-600 rounded"
                                            />
                                            <span className="text-sm">{col.label}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="p-6 border-t border-gray-200 flex justify-end gap-2">
                                <button
                                    onClick={() => setShowColumnsModal(false)}
                                    className="btn-primary"
                                >
                                    Done
                                </button>
                            </div>
                        </div>
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
                                placeholder="Model name or description..."
                                value={filters.search}
                                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                            />
                        </div>

                        {/* Development Type */}
                        <MultiSelectDropdown
                            label="Development Type"
                            placeholder="All Types"
                            options={[
                                { value: 'In-House', label: 'In-House' },
                                { value: 'Third-Party', label: 'Third-Party' }
                            ]}
                            selectedValues={filters.development_types}
                            onChange={(values) => setFilters({ ...filters, development_types: values as string[] })}
                        />

                        {/* Status */}
                        <MultiSelectDropdown
                            label="Status"
                            placeholder="All Statuses"
                            options={[
                                { value: 'In Development', label: 'In Development' },
                                { value: 'Active', label: 'Active' },
                                { value: 'Retired', label: 'Retired' }
                            ]}
                            selectedValues={filters.statuses}
                            onChange={(values) => setFilters({ ...filters, statuses: values as string[] })}
                        />

                        {/* Owner */}
                        <MultiSelectDropdown
                            label="Owner"
                            placeholder="All Owners"
                            options={users.map(u => ({ value: u.user_id, label: u.full_name }))}
                            selectedValues={filters.owner_ids}
                            onChange={(values) => setFilters({ ...filters, owner_ids: values as number[] })}
                        />

                        {/* Vendor */}
                        <MultiSelectDropdown
                            label="Vendor"
                            placeholder="All Vendors"
                            options={vendors.map(v => ({ value: v.vendor_id, label: v.name }))}
                            selectedValues={filters.vendor_ids}
                            onChange={(values) => setFilters({ ...filters, vendor_ids: values as number[] })}
                        />

                        {/* Region */}
                        <MultiSelectDropdown
                            label="Region"
                            placeholder="All Regions"
                            options={regions.map(r => ({ value: r.region_id, label: `${r.name} (${r.code})` }))}
                            selectedValues={filters.region_ids}
                            onChange={(values) => setFilters({ ...filters, region_ids: values as number[] })}
                        />

                        {/* AI/ML Classification */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">AI/ML Classification</label>
                            <select
                                value={filters.is_aiml}
                                onChange={(e) => setFilters({ ...filters, is_aiml: e.target.value as '' | 'true' | 'false' | 'null' })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
                            >
                                <option value="">All Models</option>
                                <option value="true">AI/ML Models</option>
                                <option value="false">Non-AI/ML Models</option>
                                <option value="null">Undefined (No Methodology)</option>
                            </select>
                        </div>

                        {(viewMode === 'mrsas' || viewMode === 'all') && (
                            <MultiSelectDropdown
                                label="MRSA Review Status"
                                placeholder="All Statuses"
                                options={mrsaReviewStatusOptions}
                                selectedValues={filters.mrsa_review_statuses}
                                onChange={(values) => setFilters({ ...filters, mrsa_review_statuses: values as MRSAReviewStatusCode[] })}
                            />
                        )}

                        {/* View Mode Toggle */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">View Mode</label>
                            <div className="flex rounded-md shadow-sm">
                                <button
                                    type="button"
                                    onClick={() => setViewMode('models')}
                                    className={`px-3 py-2 text-xs font-medium rounded-l-md border ${
                                        viewMode === 'models'
                                            ? 'bg-blue-600 text-white border-blue-600'
                                            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                                    }`}
                                >
                                    Models
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setViewMode('mrsas')}
                                    className={`px-3 py-2 text-xs font-medium border-t border-b ${
                                        viewMode === 'mrsas'
                                            ? 'bg-amber-600 text-white border-amber-600'
                                            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                                    }`}
                                >
                                    MRSAs
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setViewMode('all')}
                                    className={`px-3 py-2 text-xs font-medium rounded-r-md border ${
                                        viewMode === 'all'
                                            ? 'bg-gray-600 text-white border-gray-600'
                                            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                                    }`}
                                >
                                    All
                                </button>
                            </div>
                        </div>

                        {/* Include Non-Models Toggle - only show in 'models' view */}
                        {viewMode === 'models' && (
                            <div className="flex items-center space-x-2 pt-5">
                                <input
                                    type="checkbox"
                                    id="include-non-models"
                                    checked={includeNonModels}
                                    onChange={(e) => setIncludeNonModels(e.target.checked)}
                                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                />
                                <label htmlFor="include-non-models" className="text-sm font-medium text-gray-700 whitespace-nowrap">
                                    Include Non-Models
                                </label>
                            </div>
                        )}

                        {/* Include Sub-Models Toggle */}
                        <div className="flex items-center space-x-2 pt-5">
                            <input
                                type="checkbox"
                                id="include-sub-models"
                                checked={filters.include_sub_models}
                                onChange={(e) => setFilters({ ...filters, include_sub_models: e.target.checked })}
                                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                            <label htmlFor="include-sub-models" className="text-sm font-medium text-gray-700 whitespace-nowrap">
                                Include Sub-Models
                            </label>
                        </div>
                    </div>

                    {/* Clear Filters and Results Count */}
                    <div className="flex items-center justify-between mt-3 pt-3 border-t">
                        <div className="text-sm text-gray-600">
                            Showing <span className="font-semibold">{sortedData.length}</span> of{' '}
                            <span className="font-semibold">{models.length}</span>{' '}
                            {viewMode === 'mrsas' ? 'MRSAs' : viewMode === 'all' ? 'entities' : 'models'}
                        </div>
                        <button
                            onClick={() => {
                                setFilters({
                                    search: '',
                                    development_types: [],
                                    statuses: [],
                                    owner_ids: [],
                                    vendor_ids: [],
                                    region_ids: [],
                                    mrsa_review_statuses: [],
                                    include_sub_models: false,
                                    is_aiml: ''
                                });
                                setIncludeNonModels(false);
                                setViewMode('models');
                            }}
                            className="text-sm text-blue-600 hover:text-blue-800"
                        >
                            Clear Filters
                        </button>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-md">
                    <div className="max-h-[60vh] overflow-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50 sticky top-0 z-10">
                                <tr>
                                    {selectedColumns.filter(colKey => columnRenderers[colKey]).map(colKey => {
                                        const renderer = columnRenderers[colKey];
                                        const isSortable = !!renderer.sortKey;
                                        return (
                                            <th
                                                key={colKey}
                                                className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase ${isSortable ? 'cursor-pointer hover:bg-gray-100' : ''}`}
                                                onClick={isSortable ? () => requestSort(renderer.sortKey!) : undefined}
                                            >
                                                <div className="flex items-center gap-2">
                                                    {renderer.header}
                                                    {isSortable && getSortIcon(renderer.sortKey!)}
                                                </div>
                                            </th>
                                        );
                                    })}
                                    {canManageModelsFlag && (
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                    )}
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {sortedData.length === 0 ? (
                                    <tr>
                                        <td colSpan={selectedColumns.length + (canManageModelsFlag ? 1 : 0)} className="px-6 py-4 text-center text-gray-500">
                                            No models yet. Click "Add Model" to create one.
                                        </td>
                                    </tr>
                                ) : (
                                    paginatedModels.map((model) => (
                                        <tr key={model.model_id} className="hover:bg-gray-50">
                                            {selectedColumns.filter(colKey => columnRenderers[colKey]).map(colKey => (
                                                <td key={colKey} className="px-6 py-4 whitespace-nowrap text-sm">
                                                    {columnRenderers[colKey].cell(model)}
                                                </td>
                                            ))}
                                            {canManageModelsFlag && (
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <button
                                                        onClick={() => handleDelete(model.model_id)}
                                                        className="text-red-600 hover:text-red-800 text-sm"
                                                    >
                                                        Delete
                                                    </button>
                                                </td>
                                            )}
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                    <div className="px-4 py-3 border-t flex flex-wrap items-center justify-between gap-3">
                        <div className="text-sm text-gray-600">
                            Showing {startItem}-{endItem} of {totalRows}
                        </div>
                        <div className="flex flex-wrap items-center gap-3">
                            <label className="text-sm text-gray-600">
                                Rows per page
                                <select
                                    className="ml-2 input-field text-sm"
                                    value={pageSize}
                                    onChange={(e) => {
                                        setPageSize(parseInt(e.target.value, 10));
                                        setCurrentPage(1);
                                    }}
                                >
                                    {[25, 50, 100, 200].map((size) => (
                                        <option key={size} value={size}>{size}</option>
                                    ))}
                                </select>
                            </label>
                            <div className="flex items-center gap-2 text-sm">
                                <button
                                    type="button"
                                    onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                                    disabled={currentPage === 1}
                                    className="px-3 py-1 border rounded disabled:opacity-50"
                                >
                                    Prev
                                </button>
                                <span className="text-gray-600">
                                    Page {currentPage} of {totalPages}
                                </span>
                                <button
                                    type="button"
                                    onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                                    disabled={currentPage >= totalPages}
                                    className="px-3 py-1 border rounded disabled:opacity-50"
                                >
                                    Next
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
}

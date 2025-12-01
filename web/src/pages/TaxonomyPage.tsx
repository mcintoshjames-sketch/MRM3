import React, { useState, useEffect } from 'react';
import api from '../api/client';
import Layout from '../components/Layout';

// ============================================================================
// TYPES - General Taxonomy
// ============================================================================

interface TaxonomyValue {
    value_id: number;
    taxonomy_id: number;
    code: string;
    label: string;
    description: string | null;
    sort_order: number;
    is_active: boolean;
    created_at: string;
}

interface Taxonomy {
    taxonomy_id: number;
    name: string;
    description: string | null;
    is_system: boolean;
    created_at: string;
    values: TaxonomyValue[];
}

// ============================================================================
// TYPES - Change Type Taxonomy
// ============================================================================

interface ModelChangeType {
    change_type_id: number;
    category_id: number;
    code: number;
    name: string;
    description: string | null;
    mv_activity: string | null;
    requires_mv_approval: boolean;
    sort_order: number;
    is_active: boolean;
}

interface ModelChangeCategory {
    category_id: number;
    code: string;
    name: string;
    sort_order: number;
    change_types: ModelChangeType[];
}

// ============================================================================
// TYPES - Model Type Taxonomy
// ============================================================================

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

// ============================================================================
// TYPES - KPM (Key Performance Metrics) Taxonomy
// ============================================================================

interface Kpm {
    kpm_id: number;
    category_id: number;
    name: string;
    description: string | null;
    calculation: string | null;
    interpretation: string | null;
    sort_order: number;
    is_active: boolean;
    evaluation_type: 'Quantitative' | 'Qualitative' | 'Outcome Only';
}

interface KpmCategory {
    category_id: number;
    code: string;
    name: string;
    description: string | null;
    sort_order: number;
    category_type: 'Quantitative' | 'Qualitative';
    kpms: Kpm[];
}

// ============================================================================
// TYPES - FRY 14 Reporting Configuration
// ============================================================================

interface FryLineItem {
    line_item_id: number;
    line_item_text: string;
    sort_order: number;
}

interface FryMetricGroup {
    metric_group_id: number;
    metric_group_name: string;
    model_driven: boolean;
    is_active: boolean;
    rationale?: string;
    line_items?: FryLineItem[];
}

interface FrySchedule {
    schedule_id: number;
    schedule_code: string;
    is_active: boolean;
    description?: string;
    metric_groups?: FryMetricGroup[];
}

interface FryReport {
    report_id: number;
    report_code: string;
    description?: string;
    is_active: boolean;
    schedules?: FrySchedule[];
}

// ============================================================================
// TYPES - Recommendation Priority Configuration
// ============================================================================

interface RecommendationPriorityConfig {
    config_id: number;
    priority: {
        value_id: number;
        code: string;
        label: string;
    };
    requires_final_approval: boolean;
    requires_action_plan: boolean;
    enforce_timeframes: boolean;
    description: string | null;
    created_at: string;
    updated_at: string;
}

interface RegionalOverride {
    override_id: number;
    priority: {
        value_id: number;
        code: string;
        label: string;
    };
    region: {
        region_id: number;
        code: string;
        name: string;
    };
    requires_action_plan: boolean | null;
    requires_final_approval: boolean | null;
    enforce_timeframes: boolean | null;
    description: string | null;
    created_at: string;
    updated_at: string;
}

interface Region {
    region_id: number;
    code: string;
    name: string;
}

export default function TaxonomyPage() {
    // Tab management
    const [activeTab, setActiveTab] = useState<'general' | 'change-type' | 'model-type' | 'kpm' | 'fry' | 'recommendation-priority'>('general');

    // Recommendation Priority Config state
    const [priorityConfigs, setPriorityConfigs] = useState<RecommendationPriorityConfig[]>([]);
    const [priorityConfigLoading, setPriorityConfigLoading] = useState(false);
    const [priorityConfigError, setPriorityConfigError] = useState<string | null>(null);
    const [editingPriorityConfig, setEditingPriorityConfig] = useState<RecommendationPriorityConfig | null>(null);

    // Timeframe Config state
    const [timeframeConfigs, setTimeframeConfigs] = useState<any[]>([]);
    const [timeframeConfigsLoading, setTimeframeConfigsLoading] = useState(false);
    const [showTimeframeSection, setShowTimeframeSection] = useState(false);
    const [editingTimeframeConfig, setEditingTimeframeConfig] = useState<any | null>(null);

    // Regional Override state
    const [regionalOverrides, setRegionalOverrides] = useState<Record<number, RegionalOverride[]>>({});
    const [regions, setRegions] = useState<Region[]>([]);
    const [expandedPriorityIds, setExpandedPriorityIds] = useState<Set<number>>(new Set());
    const [editingRegionalOverride, setEditingRegionalOverride] = useState<{
        isNew: boolean;
        priorityId: number;
        override: Partial<RegionalOverride>;
    } | null>(null);

    // General taxonomy state
    const [taxonomies, setTaxonomies] = useState<Taxonomy[]>([]);
    const [selectedTaxonomy, setSelectedTaxonomy] = useState<Taxonomy | null>(null);
    const [showTaxonomyForm, setShowTaxonomyForm] = useState(false);
    const [showValueForm, setShowValueForm] = useState(false);
    const [editingValue, setEditingValue] = useState<TaxonomyValue | null>(null);
    const [taxonomyFormData, setTaxonomyFormData] = useState({
        name: '',
        description: ''
    });
    const [valueFormData, setValueFormData] = useState({
        code: '',
        label: '',
        description: '',
        sort_order: 0,
        is_active: true
    });

    // Change type taxonomy state
    const [categories, setCategories] = useState<ModelChangeCategory[]>([]);
    const [selectedCategory, setSelectedCategory] = useState<ModelChangeCategory | null>(null);
    const [showCategoryForm, setShowCategoryForm] = useState(false);
    const [showChangeTypeForm, setShowChangeTypeForm] = useState(false);
    const [editingChangeType, setEditingChangeType] = useState<ModelChangeType | null>(null);
    const [categoryFormData, setCategoryFormData] = useState({
        code: '',
        name: '',
        sort_order: 0
    });
    const [changeTypeFormData, setChangeTypeFormData] = useState({
        code: 0,
        name: '',
        description: '',
        mv_activity: '',
        requires_mv_approval: false,
        sort_order: 0,
        is_active: true
    });

    // Model type taxonomy state
    const [modelCategories, setModelCategories] = useState<ModelTypeCategory[]>([]);
    const [selectedModelCategory, setSelectedModelCategory] = useState<ModelTypeCategory | null>(null);
    const [showModelCategoryForm, setShowModelCategoryForm] = useState(false);
    const [showModelTypeForm, setShowModelTypeForm] = useState(false);
    const [editingModelType, setEditingModelType] = useState<ModelType | null>(null);
    const [modelCategoryFormData, setModelCategoryFormData] = useState({
        name: '',
        description: '',
        sort_order: 0
    });
    const [modelTypeFormData, setModelTypeFormData] = useState({
        name: '',
        description: '',
        sort_order: 0,
        is_active: true
    });

    // KPM taxonomy state
    const [kpmCategories, setKpmCategories] = useState<KpmCategory[]>([]);
    const [selectedKpmCategory, setSelectedKpmCategory] = useState<KpmCategory | null>(null);
    const [showKpmCategoryForm, setShowKpmCategoryForm] = useState(false);
    const [showKpmForm, setShowKpmForm] = useState(false);
    const [editingKpm, setEditingKpm] = useState<Kpm | null>(null);
    const [kpmCategoryFormData, setKpmCategoryFormData] = useState({
        code: '',
        name: '',
        description: '',
        category_type: 'Quantitative' as 'Quantitative' | 'Qualitative',
        sort_order: 0
    });
    const [kpmFormData, setKpmFormData] = useState({
        name: '',
        description: '',
        calculation: '',
        interpretation: '',
        sort_order: 0,
        is_active: true
    });

    // FRY 14 state
    const [fryReports, setFryReports] = useState<FryReport[]>([]);
    const [selectedFryReport, setSelectedFryReport] = useState<FryReport | null>(null);
    const [expandedReports, setExpandedReports] = useState<Set<number>>(new Set());
    const [expandedSchedules, setExpandedSchedules] = useState<Set<number>>(new Set());
    const [expandedMetricGroups, setExpandedMetricGroups] = useState<Set<number>>(new Set());
    const [editingFryItem, setEditingFryItem] = useState<FryMetricGroup | null>(null);

    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (activeTab === 'general') {
            fetchTaxonomies();
        } else if (activeTab === 'change-type') {
            fetchChangeCategories();
        } else if (activeTab === 'model-type') {
            fetchModelCategories();
        } else if (activeTab === 'kpm') {
            fetchKpmCategories();
        } else if (activeTab === 'fry') {
            fetchFryReports();
        } else if (activeTab === 'recommendation-priority') {
            fetchPriorityConfigs();
        }
    }, [activeTab]);

    // ============================================================================
    // GENERAL TAXONOMY FUNCTIONS
    // ============================================================================

    const fetchTaxonomies = async () => {
        try {
            const response = await api.get('/taxonomies/');
            setTaxonomies(response.data);
            if (response.data.length > 0 && !selectedTaxonomy) {
                const detailRes = await api.get(`/taxonomies/${response.data[0].taxonomy_id}`);
                setSelectedTaxonomy(detailRes.data);
            }
        } catch (error) {
            console.error('Failed to fetch taxonomies:', error);
        } finally {
            setLoading(false);
        }
    };

    const selectTaxonomy = async (taxonomyId: number) => {
        try {
            const response = await api.get(`/taxonomies/${taxonomyId}`);
            setSelectedTaxonomy(response.data);
        } catch (error) {
            console.error('Failed to fetch taxonomy:', error);
        }
    };

    const resetTaxonomyForm = () => {
        setTaxonomyFormData({ name: '', description: '' });
        setShowTaxonomyForm(false);
    };

    const resetValueForm = () => {
        setValueFormData({
            code: '',
            label: '',
            description: '',
            sort_order: 0,
            is_active: true
        });
        setEditingValue(null);
        setShowValueForm(false);
    };

    const handleTaxonomySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/taxonomies/', taxonomyFormData);
            resetTaxonomyForm();
            fetchTaxonomies();
        } catch (error) {
            console.error('Failed to create taxonomy:', error);
        }
    };

    const handleValueSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedTaxonomy) return;

        try {
            if (editingValue) {
                await api.patch(`/taxonomies/values/${editingValue.value_id}`, valueFormData);
            } else {
                await api.post(`/taxonomies/${selectedTaxonomy.taxonomy_id}/values`, valueFormData);
            }
            resetValueForm();
            selectTaxonomy(selectedTaxonomy.taxonomy_id);
        } catch (error) {
            console.error('Failed to save value:', error);
        }
    };

    const handleEditValue = (value: TaxonomyValue) => {
        setEditingValue(value);
        setValueFormData({
            code: value.code,
            label: value.label,
            description: value.description || '',
            sort_order: value.sort_order,
            is_active: value.is_active
        });
        setShowValueForm(true);
    };

    const handleDeleteValue = async (valueId: number) => {
        if (!confirm('Are you sure you want to delete this value?')) return;
        if (!selectedTaxonomy) return;

        try {
            await api.delete(`/taxonomies/values/${valueId}`);
            selectTaxonomy(selectedTaxonomy.taxonomy_id);
        } catch (error) {
            console.error('Failed to delete value:', error);
        }
    };

    const isSystemProtectedValue = (value: TaxonomyValue): boolean => {
        return selectedTaxonomy?.name === 'Validation Type' && value.code === 'TARGETED';
    };

    const handleDeleteTaxonomy = async (taxonomyId: number) => {
        if (!confirm('Are you sure you want to delete this taxonomy and all its values?')) return;

        try {
            await api.delete(`/taxonomies/${taxonomyId}`);
            setSelectedTaxonomy(null);
            fetchTaxonomies();
        } catch (error) {
            console.error('Failed to delete taxonomy:', error);
        }
    };

    // ============================================================================
    // CHANGE TYPE TAXONOMY FUNCTIONS
    // ============================================================================

    const fetchChangeCategories = async () => {
        try {
            // Admin UI needs to see all types (active and inactive)
            const response = await api.get('/change-taxonomy/categories?active_only=false');
            setCategories(response.data);
            if (response.data.length > 0 && !selectedCategory) {
                setSelectedCategory(response.data[0]);
            }
        } catch (error) {
            console.error('Failed to fetch change categories:', error);
        } finally {
            setLoading(false);
        }
    };

    const selectCategory = (category: ModelChangeCategory) => {
        setSelectedCategory(category);
    };

    const resetCategoryForm = () => {
        setCategoryFormData({ code: '', name: '', sort_order: 0 });
        setShowCategoryForm(false);
    };

    const resetChangeTypeForm = () => {
        setChangeTypeFormData({
            code: 0,
            name: '',
            description: '',
            mv_activity: '',
            requires_mv_approval: false,
            sort_order: 0,
            is_active: true
        });
        setEditingChangeType(null);
        setShowChangeTypeForm(false);
    };

    const handleCategorySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/change-taxonomy/categories', categoryFormData);
            resetCategoryForm();
            fetchChangeCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to create category');
            console.error('Failed to create category:', error);
        }
    };

    const handleChangeTypeSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedCategory) return;

        try {
            if (editingChangeType) {
                await api.patch(`/change-taxonomy/types/${editingChangeType.change_type_id}`, changeTypeFormData);
            } else {
                await api.post('/change-taxonomy/types', {
                    ...changeTypeFormData,
                    category_id: selectedCategory.category_id
                });
            }
            resetChangeTypeForm();
            fetchChangeCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to save change type');
            console.error('Failed to save change type:', error);
        }
    };

    const handleEditChangeType = (type: ModelChangeType) => {
        setEditingChangeType(type);
        setChangeTypeFormData({
            code: type.code,
            name: type.name,
            description: type.description || '',
            mv_activity: type.mv_activity || '',
            requires_mv_approval: type.requires_mv_approval,
            sort_order: type.sort_order,
            is_active: type.is_active
        });
        setShowChangeTypeForm(true);
    };

    const handleDeleteChangeType = async (changeTypeId: number) => {
        if (!confirm('Are you sure you want to delete this change type?')) return;

        try {
            await api.delete(`/change-taxonomy/types/${changeTypeId}`);
            fetchChangeCategories();
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || 'Failed to delete change type';

            // Check if it's a referential integrity error
            if (error.response?.status === 409) {
                const deactivate = confirm(
                    `${errorMessage}\n\n` +
                    `Would you like to deactivate this change type instead? ` +
                    `This will hide it from the dropdown while preserving historical data.`
                );

                if (deactivate) {
                    try {
                        await api.patch(`/change-taxonomy/types/${changeTypeId}`, {
                            is_active: false
                        });
                        fetchChangeCategories();
                        alert('Change type has been deactivated successfully.');
                    } catch (deactivateError: any) {
                        alert(deactivateError.response?.data?.detail || 'Failed to deactivate change type');
                    }
                }
            } else {
                alert(errorMessage);
            }
            console.error('Failed to delete change type:', error);
        }
    };

    const handleDeleteCategory = async (categoryId: number) => {
        if (!confirm('Are you sure you want to delete this category and all its change types?')) return;

        try {
            await api.delete(`/change-taxonomy/categories/${categoryId}`);
            setSelectedCategory(null);
            fetchChangeCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to delete category');
            console.error('Failed to delete category:', error);
        }
    };

    // ============================================================================
    // MODEL TYPE TAXONOMY FUNCTIONS
    // ============================================================================

    const fetchModelCategories = async () => {
        try {
            const response = await api.get('/model-types/categories');
            setModelCategories(response.data);
            if (response.data.length > 0 && !selectedModelCategory) {
                setSelectedModelCategory(response.data[0]);
            }
        } catch (error) {
            console.error('Failed to fetch model categories:', error);
        } finally {
            setLoading(false);
        }
    };

    const selectModelCategory = (category: ModelTypeCategory) => {
        setSelectedModelCategory(category);
    };

    const resetModelCategoryForm = () => {
        setModelCategoryFormData({ name: '', description: '', sort_order: 0 });
        setShowModelCategoryForm(false);
    };

    const resetModelTypeForm = () => {
        setModelTypeFormData({
            name: '',
            description: '',
            sort_order: 0,
            is_active: true
        });
        setEditingModelType(null);
        setShowModelTypeForm(false);
    };

    const handleModelCategorySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/model-types/categories', modelCategoryFormData);
            resetModelCategoryForm();
            fetchModelCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to create category');
            console.error('Failed to create category:', error);
        }
    };

    const handleModelTypeSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedModelCategory) return;

        try {
            if (editingModelType) {
                await api.patch(`/model-types/types/${editingModelType.type_id}`, modelTypeFormData);
            } else {
                await api.post('/model-types/types', {
                    ...modelTypeFormData,
                    category_id: selectedModelCategory.category_id
                });
            }
            resetModelTypeForm();
            fetchModelCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to save model type');
            console.error('Failed to save model type:', error);
        }
    };

    const handleEditModelType = (type: ModelType) => {
        setEditingModelType(type);
        setModelTypeFormData({
            name: type.name,
            description: type.description || '',
            sort_order: type.sort_order,
            is_active: type.is_active
        });
        setShowModelTypeForm(true);
    };

    const handleDeleteModelType = async (typeId: number) => {
        if (!confirm('Are you sure you want to delete this model type?')) return;

        try {
            await api.delete(`/model-types/types/${typeId}`);
            fetchModelCategories();
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || 'Failed to delete model type';

            // Check if it's a referential integrity error
            if (error.response?.status === 409) {
                const deactivate = confirm(
                    `${errorMessage}\n\n` +
                    `Would you like to deactivate this model type instead? ` +
                    `This will hide it from the dropdown while preserving historical data.`
                );

                if (deactivate) {
                    try {
                        await api.patch(`/model-types/types/${typeId}`, {
                            is_active: false
                        });
                        fetchModelCategories();
                        alert('Model type has been deactivated successfully.');
                    } catch (deactivateError: any) {
                        alert(deactivateError.response?.data?.detail || 'Failed to deactivate model type');
                    }
                }
            } else {
                alert(errorMessage);
            }
            console.error('Failed to delete model type:', error);
        }
    };

    const handleDeleteModelCategory = async (categoryId: number) => {
        if (!confirm('Are you sure you want to delete this category and all its model types?')) return;

        try {
            await api.delete(`/model-types/categories/${categoryId}`);
            setSelectedModelCategory(null);
            fetchModelCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to delete category');
            console.error('Failed to delete category:', error);
        }
    };

    // ============================================================================
    // KPM TAXONOMY FUNCTIONS
    // ============================================================================

    const fetchKpmCategories = async () => {
        try {
            const response = await api.get('/kpm/categories?active_only=false');
            setKpmCategories(response.data);
            // Update selectedKpmCategory with fresh data, or select first category
            if (response.data.length > 0) {
                if (selectedKpmCategory) {
                    // Find the updated version of the currently selected category
                    const updatedCategory = response.data.find(
                        (cat: KpmCategory) => cat.category_id === selectedKpmCategory.category_id
                    );
                    setSelectedKpmCategory(updatedCategory || response.data[0]);
                } else {
                    setSelectedKpmCategory(response.data[0]);
                }
            }
        } catch (error) {
            console.error('Failed to fetch KPM categories:', error);
        } finally {
            setLoading(false);
        }
    };

    const selectKpmCategory = (category: KpmCategory) => {
        setSelectedKpmCategory(category);
    };

    const resetKpmCategoryForm = () => {
        setKpmCategoryFormData({ code: '', name: '', description: '', category_type: 'Quantitative', sort_order: 0 });
        setShowKpmCategoryForm(false);
    };

    const resetKpmForm = () => {
        setKpmFormData({
            name: '',
            description: '',
            calculation: '',
            interpretation: '',
            sort_order: 0,
            is_active: true
        });
        setEditingKpm(null);
        setShowKpmForm(false);
    };

    const handleKpmCategorySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/kpm/categories', kpmCategoryFormData);
            resetKpmCategoryForm();
            fetchKpmCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to create category');
            console.error('Failed to create category:', error);
        }
    };

    const handleKpmSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedKpmCategory) return;

        try {
            if (editingKpm) {
                await api.patch(`/kpm/kpms/${editingKpm.kpm_id}`, kpmFormData);
            } else {
                await api.post('/kpm/kpms', {
                    ...kpmFormData,
                    category_id: selectedKpmCategory.category_id
                });
            }
            resetKpmForm();
            fetchKpmCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to save KPM');
            console.error('Failed to save KPM:', error);
        }
    };

    const handleEditKpm = (kpm: Kpm) => {
        setEditingKpm(kpm);
        setKpmFormData({
            name: kpm.name,
            description: kpm.description || '',
            calculation: kpm.calculation || '',
            interpretation: kpm.interpretation || '',
            sort_order: kpm.sort_order,
            is_active: kpm.is_active
        });
        setShowKpmForm(true);
    };

    const handleDeleteKpm = async (kpmId: number) => {
        if (!confirm('Are you sure you want to delete this KPM?')) return;

        try {
            await api.delete(`/kpm/kpms/${kpmId}`);
            fetchKpmCategories();
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || 'Failed to delete KPM';

            if (error.response?.status === 409) {
                const deactivate = confirm(
                    `${errorMessage}\n\n` +
                    `Would you like to deactivate this KPM instead? ` +
                    `This will hide it from the list while preserving historical data.`
                );

                if (deactivate) {
                    try {
                        await api.patch(`/kpm/kpms/${kpmId}`, { is_active: false });
                        fetchKpmCategories();
                        alert('KPM has been deactivated successfully.');
                    } catch (deactivateError: any) {
                        alert(deactivateError.response?.data?.detail || 'Failed to deactivate KPM');
                    }
                }
            } else {
                alert(errorMessage);
            }
            console.error('Failed to delete KPM:', error);
        }
    };

    const handleDeleteKpmCategory = async (categoryId: number) => {
        if (!confirm('Are you sure you want to delete this category and all its KPMs?')) return;

        try {
            await api.delete(`/kpm/categories/${categoryId}`);
            setSelectedKpmCategory(null);
            fetchKpmCategories();
        } catch (error: any) {
            alert(error.response?.data?.detail || 'Failed to delete category');
            console.error('Failed to delete category:', error);
        }
    };

    // ============================================================================
    // FRY 14 REPORTING FUNCTIONS
    // ============================================================================

    const fetchFryReports = async () => {
        try {
            const response = await api.get('/fry/reports');
            setFryReports(response.data);
        } catch (error) {
            console.error('Error fetching FRY reports:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchFryReportDetails = async (reportId: number) => {
        try {
            const response = await api.get(`/fry/reports/${reportId}`);
            setSelectedFryReport(response.data);
            setExpandedReports(new Set([...expandedReports, reportId]));
        } catch (error) {
            console.error('Error fetching report details:', error);
        }
    };

    const toggleFryReport = async (reportId: number) => {
        if (expandedReports.has(reportId)) {
            const newExpanded = new Set(expandedReports);
            newExpanded.delete(reportId);
            setExpandedReports(newExpanded);
        } else {
            await fetchFryReportDetails(reportId);
        }
    };

    const toggleFrySchedule = (scheduleId: number) => {
        const newExpanded = new Set(expandedSchedules);
        if (newExpanded.has(scheduleId)) {
            newExpanded.delete(scheduleId);
        } else {
            newExpanded.add(scheduleId);
        }
        setExpandedSchedules(newExpanded);
    };

    const toggleFryMetricGroup = (metricGroupId: number) => {
        const newExpanded = new Set(expandedMetricGroups);
        if (newExpanded.has(metricGroupId)) {
            newExpanded.delete(metricGroupId);
        } else {
            newExpanded.add(metricGroupId);
        }
        setExpandedMetricGroups(newExpanded);
    };

    const handleEditFryMetricGroup = (metricGroup: FryMetricGroup) => {
        setEditingFryItem({ ...metricGroup });
    };

    const handleSaveFryMetricGroup = async () => {
        if (!editingFryItem) return;

        try {
            await api.patch(`/fry/metric-groups/${editingFryItem.metric_group_id}`, {
                metric_group_name: editingFryItem.metric_group_name,
                model_driven: editingFryItem.model_driven,
                rationale: editingFryItem.rationale,
                is_active: editingFryItem.is_active
            });

            // Refresh report details
            if (selectedFryReport) {
                await fetchFryReportDetails(selectedFryReport.report_id);
            }

            setEditingFryItem(null);
        } catch (error) {
            console.error('Error saving metric group:', error);
            alert('Failed to save metric group');
        }
    };

    const handleCancelFryEdit = () => {
        setEditingFryItem(null);
    };

    // ============================================================================
    // RECOMMENDATION PRIORITY CONFIG FUNCTIONS
    // ============================================================================

    const fetchPriorityConfigs = async () => {
        try {
            setPriorityConfigLoading(true);
            setPriorityConfigError(null);
            const response = await api.get('/recommendations/priority-config/');
            setPriorityConfigs(response.data);
        } catch (error) {
            console.error('Error fetching priority configs:', error);
            setPriorityConfigError('Failed to load priority configurations');
        } finally {
            setPriorityConfigLoading(false);
            setLoading(false);
        }
    };

    const handleSavePriorityConfig = async (config: RecommendationPriorityConfig) => {
        try {
            await api.patch(`/recommendations/priority-config/${config.priority.value_id}`, {
                requires_final_approval: config.requires_final_approval,
                requires_action_plan: config.requires_action_plan,
                enforce_timeframes: config.enforce_timeframes,
                description: config.description
            });
            await fetchPriorityConfigs();
            setEditingPriorityConfig(null);
        } catch (error) {
            console.error('Error updating priority config:', error);
            alert('Failed to update priority configuration');
        }
    };

    // ============================================================================
    // TIMEFRAME CONFIG FUNCTIONS
    // ============================================================================

    const fetchTimeframeConfigs = async () => {
        try {
            setTimeframeConfigsLoading(true);
            const response = await api.get('/recommendations/timeframe-config/');
            setTimeframeConfigs(response.data);
        } catch (error) {
            console.error('Error fetching timeframe configs:', error);
        } finally {
            setTimeframeConfigsLoading(false);
        }
    };

    const handleSaveTimeframeConfig = async () => {
        if (!editingTimeframeConfig) return;

        try {
            await api.patch(`/recommendations/timeframe-config/${editingTimeframeConfig.config_id}`, {
                max_days: editingTimeframeConfig.max_days,
                description: editingTimeframeConfig.description
            });
            await fetchTimeframeConfigs();
            setEditingTimeframeConfig(null);
        } catch (error) {
            console.error('Error updating timeframe config:', error);
            alert('Failed to update timeframe configuration');
        }
    };

    const toggleTimeframeSection = async () => {
        if (!showTimeframeSection) {
            await fetchTimeframeConfigs();
        }
        setShowTimeframeSection(!showTimeframeSection);
    };

    // ============================================================================
    // REGIONAL OVERRIDE FUNCTIONS
    // ============================================================================

    const fetchRegions = async () => {
        try {
            const response = await api.get('/regions/');
            setRegions(response.data);
        } catch (error) {
            console.error('Error fetching regions:', error);
        }
    };

    const fetchRegionalOverrides = async (priorityId: number) => {
        try {
            const response = await api.get(`/recommendations/priority-config/${priorityId}/regional-overrides/`);
            setRegionalOverrides(prev => ({
                ...prev,
                [priorityId]: response.data
            }));
        } catch (error) {
            console.error('Error fetching regional overrides:', error);
        }
    };

    const togglePriorityExpanded = async (priorityId: number) => {
        const newExpanded = new Set(expandedPriorityIds);
        if (newExpanded.has(priorityId)) {
            newExpanded.delete(priorityId);
        } else {
            newExpanded.add(priorityId);
            // Fetch regions and overrides when expanding
            if (regions.length === 0) {
                await fetchRegions();
            }
            await fetchRegionalOverrides(priorityId);
        }
        setExpandedPriorityIds(newExpanded);
    };

    const handleSaveRegionalOverride = async () => {
        if (!editingRegionalOverride) return;

        try {
            const { isNew, priorityId, override } = editingRegionalOverride;

            if (isNew) {
                await api.post('/recommendations/priority-config/regional-overrides/', {
                    priority_id: priorityId,
                    region_id: override.region?.region_id,
                    requires_action_plan: override.requires_action_plan,
                    requires_final_approval: override.requires_final_approval,
                    enforce_timeframes: override.enforce_timeframes,
                    description: override.description
                });
            } else {
                await api.patch(`/recommendations/priority-config/regional-overrides/${override.override_id}`, {
                    requires_action_plan: override.requires_action_plan,
                    requires_final_approval: override.requires_final_approval,
                    enforce_timeframes: override.enforce_timeframes,
                    description: override.description
                });
            }

            await fetchRegionalOverrides(priorityId);
            setEditingRegionalOverride(null);
        } catch (error) {
            console.error('Error saving regional override:', error);
            alert('Failed to save regional override');
        }
    };

    const handleDeleteRegionalOverride = async (overrideId: number, priorityId: number) => {
        if (!confirm('Are you sure you want to delete this regional override?')) return;

        try {
            await api.delete(`/recommendations/priority-config/regional-overrides/${overrideId}`);
            await fetchRegionalOverrides(priorityId);
        } catch (error) {
            console.error('Error deleting regional override:', error);
            alert('Failed to delete regional override');
        }
    };

    const getAvailableRegionsForOverride = (priorityId: number): Region[] => {
        const existingRegionIds = new Set(
            (regionalOverrides[priorityId] || []).map(o => o.region.region_id)
        );
        return regions.filter(r => !existingRegionIds.has(r.region_id));
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
                <h2 className="text-2xl font-bold">Taxonomy Management</h2>
            </div>

            {/* Tab Toggle */}
            <div className="mb-6">
                <div className="border-b border-gray-200">
                    <nav className="-mb-px flex space-x-8">
                        <button
                            onClick={() => setActiveTab('general')}
                            className={`${activeTab === 'general'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                        >
                            General Taxonomies
                        </button>
                        <button
                            onClick={() => setActiveTab('change-type')}
                            className={`${activeTab === 'change-type'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                        >
                            Change Type Taxonomy
                        </button>
                        <button
                            onClick={() => setActiveTab('model-type')}
                            className={`${activeTab === 'model-type'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                        >
                            Model Type Taxonomy
                        </button>
                        <button
                            onClick={() => setActiveTab('kpm')}
                            className={`${activeTab === 'kpm'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                        >
                            KPM Library
                        </button>
                        <button
                            onClick={() => setActiveTab('fry')}
                            className={`${activeTab === 'fry'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                        >
                            FRY 14 Config
                        </button>
                        <button
                            onClick={() => setActiveTab('recommendation-priority')}
                            className={`${activeTab === 'recommendation-priority'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                        >
                            Recommendation Priority
                        </button>
                    </nav>
                </div>
            </div>

            {/* GENERAL TAXONOMIES TAB */}
            {activeTab === 'general' && (
                <>
                    <div className="mb-6 flex justify-end">
                        <button onClick={() => setShowTaxonomyForm(true)} className="btn-primary">
                            + New Taxonomy
                        </button>
                    </div>

                    {showTaxonomyForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h3 className="text-lg font-bold mb-4">Create New Taxonomy</h3>
                            <form onSubmit={handleTaxonomySubmit}>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="mb-4">
                                        <label htmlFor="tax_name" className="block text-sm font-medium mb-2">
                                            Name
                                        </label>
                                        <input
                                            id="tax_name"
                                            type="text"
                                            className="input-field"
                                            value={taxonomyFormData.name}
                                            onChange={(e) => setTaxonomyFormData({ ...taxonomyFormData, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="tax_desc" className="block text-sm font-medium mb-2">
                                            Description
                                        </label>
                                        <input
                                            id="tax_desc"
                                            type="text"
                                            className="input-field"
                                            value={taxonomyFormData.description}
                                            onChange={(e) => setTaxonomyFormData({ ...taxonomyFormData, description: e.target.value })}
                                        />
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">Create</button>
                                    <button type="button" onClick={resetTaxonomyForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="grid grid-cols-4 gap-6">
                        {/* Taxonomy list */}
                        <div className="col-span-1">
                            <div className="bg-white rounded-lg shadow-md p-4">
                                <h3 className="font-bold mb-3">Taxonomies</h3>
                                <div className="space-y-2">
                                    {taxonomies.length === 0 ? (
                                        <p className="text-sm text-gray-500">No taxonomies yet.</p>
                                    ) : (
                                        taxonomies.map((tax) => (
                                            <button
                                                key={tax.taxonomy_id}
                                                onClick={() => selectTaxonomy(tax.taxonomy_id)}
                                                className={`w-full text-left px-3 py-2 rounded text-sm ${selectedTaxonomy?.taxonomy_id === tax.taxonomy_id
                                                    ? 'bg-blue-100 text-blue-800 font-medium'
                                                    : 'hover:bg-gray-100'
                                                    }`}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span>{tax.name}</span>
                                                    {tax.is_system && (
                                                        <span className="text-xs bg-gray-200 px-1 rounded">System</span>
                                                    )}
                                                </div>
                                            </button>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Selected taxonomy details and values */}
                        <div className="col-span-3">
                            {selectedTaxonomy ? (
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <h3 className="text-xl font-bold">{selectedTaxonomy.name}</h3>
                                            {selectedTaxonomy.description && (
                                                <p className="text-gray-600 mt-1">{selectedTaxonomy.description}</p>
                                            )}
                                            <div className="flex gap-2 mt-2">
                                                {selectedTaxonomy.is_system && (
                                                    <span className="text-xs bg-gray-200 px-2 py-1 rounded">
                                                        System Taxonomy
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setShowValueForm(true)}
                                                className="btn-primary text-sm"
                                            >
                                                + Add Value
                                            </button>
                                            {!selectedTaxonomy.is_system && (
                                                <button
                                                    onClick={() => handleDeleteTaxonomy(selectedTaxonomy.taxonomy_id)}
                                                    className="btn-secondary text-red-600 text-sm"
                                                >
                                                    Delete Taxonomy
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    {showValueForm && (
                                        <div className="bg-gray-50 p-4 rounded mb-4">
                                            <h4 className="font-medium mb-3">
                                                {editingValue ? 'Edit Value' : 'Add New Value'}
                                            </h4>
                                            <form onSubmit={handleValueSubmit}>
                                                <div className="grid grid-cols-3 gap-4">
                                                    <div className="mb-3">
                                                        <label htmlFor="val_code" className="block text-sm font-medium mb-1">
                                                            Code {editingValue && <span className="text-xs text-gray-500">(immutable)</span>}
                                                        </label>
                                                        <input
                                                            id="val_code"
                                                            type="text"
                                                            className={`input-field ${editingValue ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                                                            value={valueFormData.code}
                                                            onChange={(e) => setValueFormData({ ...valueFormData, code: e.target.value })}
                                                            disabled={!!editingValue}
                                                            readOnly={!!editingValue}
                                                            required
                                                            title={editingValue ? "Code cannot be changed after creation to maintain data integrity" : ""}
                                                        />
                                                    </div>
                                                    <div className="mb-3">
                                                        <label htmlFor="val_label" className="block text-sm font-medium mb-1">
                                                            Label
                                                        </label>
                                                        <input
                                                            id="val_label"
                                                            type="text"
                                                            className="input-field"
                                                            value={valueFormData.label}
                                                            onChange={(e) => setValueFormData({ ...valueFormData, label: e.target.value })}
                                                            required
                                                        />
                                                    </div>
                                                    <div className="mb-3">
                                                        <label htmlFor="val_order" className="block text-sm font-medium mb-1">
                                                            Sort Order
                                                        </label>
                                                        <input
                                                            id="val_order"
                                                            type="number"
                                                            className="input-field"
                                                            value={valueFormData.sort_order}
                                                            onChange={(e) => setValueFormData({ ...valueFormData, sort_order: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                </div>
                                                <div className="mb-3">
                                                    <label htmlFor="val_desc" className="block text-sm font-medium mb-1">
                                                        Description
                                                    </label>
                                                    <textarea
                                                        id="val_desc"
                                                        className="input-field"
                                                        rows={2}
                                                        value={valueFormData.description}
                                                        onChange={(e) => setValueFormData({ ...valueFormData, description: e.target.value })}
                                                    />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="flex items-center gap-2">
                                                        <input
                                                            type="checkbox"
                                                            checked={valueFormData.is_active}
                                                            onChange={(e) => setValueFormData({ ...valueFormData, is_active: e.target.checked })}
                                                        />
                                                        <span className="text-sm font-medium">Active</span>
                                                    </label>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button type="submit" className="btn-primary text-sm">
                                                        {editingValue ? 'Update' : 'Add'}
                                                    </button>
                                                    <button type="button" onClick={resetValueForm} className="btn-secondary text-sm">
                                                        Cancel
                                                    </button>
                                                </div>
                                            </form>
                                        </div>
                                    )}

                                    <div className="mt-4">
                                        <h4 className="font-medium mb-3">
                                            Values ({selectedTaxonomy.values.length})
                                        </h4>
                                        {selectedTaxonomy.values.length === 0 ? (
                                            <p className="text-gray-500 text-sm">No values yet. Add values to this taxonomy.</p>
                                        ) : (
                                            <div className="border rounded overflow-x-auto">
                                                <table className="min-w-full divide-y divide-gray-200">
                                                    <thead className="bg-gray-50">
                                                        <tr>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-16">
                                                                Order
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-32">
                                                                Code
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                Label
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                Description
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-48">
                                                                Actions
                                                            </th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="bg-white divide-y divide-gray-200">
                                                        {selectedTaxonomy.values
                                                            .sort((a, b) => a.sort_order - b.sort_order)
                                                            .map((value) => (
                                                                <tr key={value.value_id} className={`hover:bg-gray-50 ${!value.is_active ? 'opacity-60' : ''}`}>
                                                                    <td className="px-4 py-3 text-sm text-center">{value.sort_order}</td>
                                                                    <td className="px-4 py-3 text-sm font-mono break-words">{value.code}</td>
                                                                    <td className="px-4 py-3 text-sm font-medium">
                                                                        <div className="flex items-center gap-2">
                                                                            {value.label}
                                                                            {!value.is_active && (
                                                                                <span className="px-1.5 py-0.5 text-xs rounded bg-gray-200 text-gray-600">
                                                                                    Inactive
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-gray-600">
                                                                        {value.description || '-'}
                                                                    </td>
                                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                                        <div className="flex items-center gap-2">
                                                                            <button
                                                                                onClick={() => handleEditValue(value)}
                                                                                className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 hover:bg-blue-200 rounded text-sm font-medium transition-colors"
                                                                                title="Edit this value"
                                                                            >
                                                                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                                                </svg>
                                                                                Edit
                                                                            </button>
                                                                            {isSystemProtectedValue(value) ? (
                                                                                <button
                                                                                    disabled
                                                                                    className="inline-flex items-center px-3 py-1 bg-gray-100 text-gray-400 rounded text-sm font-medium cursor-not-allowed"
                                                                                    title="This value is used by the system for auto-generated validation projects and cannot be deleted"
                                                                                >
                                                                                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                                    </svg>
                                                                                    Delete
                                                                                </button>
                                                                            ) : (
                                                                                <button
                                                                                    onClick={() => handleDeleteValue(value.value_id)}
                                                                                    className="inline-flex items-center px-3 py-1 bg-red-100 text-red-700 hover:bg-red-200 rounded text-sm font-medium transition-colors"
                                                                                    title="Delete this value"
                                                                                >
                                                                                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                                    </svg>
                                                                                    Delete
                                                                                </button>
                                                                            )}
                                                                        </div>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-white rounded-lg shadow-md p-6 text-center text-gray-500">
                                    Select a taxonomy to view and manage its values.
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}

            {/* CHANGE TYPE TAXONOMY TAB */}
            {activeTab === 'change-type' && (
                <>
                    <div className="mb-6 flex justify-end">
                        <button onClick={() => setShowCategoryForm(true)} className="btn-primary">
                            + New Category
                        </button>
                    </div>

                    {showCategoryForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h3 className="text-lg font-bold mb-4">Create New Change Category</h3>
                            <form onSubmit={handleCategorySubmit}>
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="mb-4">
                                        <label htmlFor="cat_code" className="block text-sm font-medium mb-2">
                                            Code
                                        </label>
                                        <input
                                            id="cat_code"
                                            type="text"
                                            className="input-field"
                                            value={categoryFormData.code}
                                            onChange={(e) => setCategoryFormData({ ...categoryFormData, code: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="cat_name" className="block text-sm font-medium mb-2">
                                            Name
                                        </label>
                                        <input
                                            id="cat_name"
                                            type="text"
                                            className="input-field"
                                            value={categoryFormData.name}
                                            onChange={(e) => setCategoryFormData({ ...categoryFormData, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="cat_sort" className="block text-sm font-medium mb-2">
                                            Sort Order
                                        </label>
                                        <input
                                            id="cat_sort"
                                            type="number"
                                            className="input-field"
                                            value={categoryFormData.sort_order}
                                            onChange={(e) => setCategoryFormData({ ...categoryFormData, sort_order: parseInt(e.target.value) })}
                                            required
                                        />
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">Create</button>
                                    <button type="button" onClick={resetCategoryForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="grid grid-cols-4 gap-6">
                        {/* Category list */}
                        <div className="col-span-1">
                            <div className="bg-white rounded-lg shadow-md p-4">
                                <h3 className="font-bold mb-3">Categories</h3>
                                <div className="space-y-2">
                                    {categories.length === 0 ? (
                                        <p className="text-sm text-gray-500">No categories yet.</p>
                                    ) : (
                                        categories.map((cat) => (
                                            <button
                                                key={cat.category_id}
                                                onClick={() => selectCategory(cat)}
                                                className={`w-full text-left px-3 py-2 rounded text-sm ${selectedCategory?.category_id === cat.category_id
                                                    ? 'bg-blue-100 text-blue-800 font-medium'
                                                    : 'hover:bg-gray-100'
                                                    }`}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span>{cat.code}. {cat.name}</span>
                                                    <span className="text-xs bg-gray-200 px-1 rounded">{cat.change_types.length}</span>
                                                </div>
                                            </button>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Selected category change types */}
                        <div className="col-span-3">
                            {selectedCategory ? (
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <h3 className="text-xl font-bold">{selectedCategory.code}. {selectedCategory.name}</h3>
                                            <p className="text-sm text-gray-600 mt-1">
                                                Category for model change classification
                                            </p>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setShowChangeTypeForm(true)}
                                                className="btn-primary text-sm"
                                            >
                                                + Add Change Type
                                            </button>
                                            <button
                                                onClick={() => handleDeleteCategory(selectedCategory.category_id)}
                                                className="btn-secondary text-red-600 text-sm"
                                            >
                                                Delete Category
                                            </button>
                                        </div>
                                    </div>

                                    {showChangeTypeForm && (
                                        <div className="bg-gray-50 p-4 rounded mb-4">
                                            <h4 className="font-medium mb-3">
                                                {editingChangeType ? 'Edit Change Type' : 'Add New Change Type'}
                                            </h4>
                                            <form onSubmit={handleChangeTypeSubmit}>
                                                <div className="grid grid-cols-3 gap-4">
                                                    <div className="mb-3">
                                                        <label htmlFor="type_code" className="block text-sm font-medium mb-1">
                                                            Code
                                                        </label>
                                                        <input
                                                            id="type_code"
                                                            type="number"
                                                            className="input-field"
                                                            value={changeTypeFormData.code}
                                                            onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, code: parseInt(e.target.value) })}
                                                            required
                                                        />
                                                    </div>
                                                    <div className="mb-3 col-span-2">
                                                        <label htmlFor="type_name" className="block text-sm font-medium mb-1">
                                                            Name
                                                        </label>
                                                        <input
                                                            id="type_name"
                                                            type="text"
                                                            className="input-field"
                                                            value={changeTypeFormData.name}
                                                            onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, name: e.target.value })}
                                                            required
                                                        />
                                                    </div>
                                                </div>
                                                <div className="mb-3">
                                                    <label htmlFor="type_desc" className="block text-sm font-medium mb-1">
                                                        Description
                                                    </label>
                                                    <textarea
                                                        id="type_desc"
                                                        className="input-field"
                                                        rows={2}
                                                        value={changeTypeFormData.description}
                                                        onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, description: e.target.value })}
                                                    />
                                                </div>
                                                <div className="grid grid-cols-3 gap-4">
                                                    <div className="mb-3">
                                                        <label htmlFor="type_mv" className="block text-sm font-medium mb-1">
                                                            MV Activity
                                                        </label>
                                                        <select
                                                            id="type_mv"
                                                            className="input-field"
                                                            value={changeTypeFormData.mv_activity}
                                                            onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, mv_activity: e.target.value })}
                                                        >
                                                            <option value="">Not specified</option>
                                                            <option value="Approval">Approval</option>
                                                            <option value="Inform">Inform</option>
                                                            <option value="Not in scope to MV">Not in scope to MV</option>
                                                        </select>
                                                    </div>
                                                    <div className="mb-3">
                                                        <label htmlFor="type_sort" className="block text-sm font-medium mb-1">
                                                            Sort Order
                                                        </label>
                                                        <input
                                                            id="type_sort"
                                                            type="number"
                                                            className="input-field"
                                                            value={changeTypeFormData.sort_order}
                                                            onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, sort_order: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                    <div className="mb-3 flex items-center gap-4 mt-6">
                                                        <label className="flex items-center gap-2">
                                                            <input
                                                                type="checkbox"
                                                                checked={changeTypeFormData.requires_mv_approval}
                                                                onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, requires_mv_approval: e.target.checked })}
                                                            />
                                                            <span className="text-sm font-medium">Requires MV Approval</span>
                                                        </label>
                                                        <label className="flex items-center gap-2">
                                                            <input
                                                                type="checkbox"
                                                                checked={changeTypeFormData.is_active}
                                                                onChange={(e) => setChangeTypeFormData({ ...changeTypeFormData, is_active: e.target.checked })}
                                                            />
                                                            <span className="text-sm font-medium">Active</span>
                                                        </label>
                                                    </div>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button type="submit" className="btn-primary text-sm">
                                                        {editingChangeType ? 'Update' : 'Add'}
                                                    </button>
                                                    <button type="button" onClick={resetChangeTypeForm} className="btn-secondary text-sm">
                                                        Cancel
                                                    </button>
                                                </div>
                                            </form>
                                        </div>
                                    )}

                                    <div className="mt-4">
                                        <h4 className="font-medium mb-3">
                                            Change Types ({selectedCategory.change_types.length})
                                        </h4>
                                        {selectedCategory.change_types.length === 0 ? (
                                            <p className="text-gray-500 text-sm">No change types yet. Add change types to this category.</p>
                                        ) : (
                                            <div className="border rounded overflow-x-auto">
                                                <table className="min-w-full divide-y divide-gray-200">
                                                    <thead className="bg-gray-50">
                                                        <tr>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-16">
                                                                Code
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                Name
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-32">
                                                                MV Activity
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-32">
                                                                MV Approval
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-24">
                                                                Status
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-48">
                                                                Actions
                                                            </th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="bg-white divide-y divide-gray-200">
                                                        {selectedCategory.change_types
                                                            .sort((a, b) => a.sort_order - b.sort_order)
                                                            .map((type) => (
                                                                <tr key={type.change_type_id} className={`hover:bg-gray-50 ${!type.is_active ? 'opacity-60' : ''}`}>
                                                                    <td className="px-4 py-3 text-sm text-center font-mono">{type.code}</td>
                                                                    <td className="px-4 py-3 text-sm">
                                                                        <div>
                                                                            <div className="font-medium">{type.name}</div>
                                                                            {type.description && (
                                                                                <div className="text-xs text-gray-500 mt-0.5">{type.description}</div>
                                                                            )}
                                                                        </div>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm text-gray-600">
                                                                        {type.mv_activity || '-'}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm">
                                                                        {type.requires_mv_approval ? (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-orange-100 text-orange-800">
                                                                                Required
                                                                            </span>
                                                                        ) : (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                                                                                Not Required
                                                                            </span>
                                                                        )}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm">
                                                                        {type.is_active ? (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                                                                                Active
                                                                            </span>
                                                                        ) : (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-600">
                                                                                Inactive
                                                                            </span>
                                                                        )}
                                                                    </td>
                                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                                        <div className="flex items-center gap-2">
                                                                            <button
                                                                                onClick={() => handleEditChangeType(type)}
                                                                                className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 hover:bg-blue-200 rounded text-sm font-medium transition-colors"
                                                                            >
                                                                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                                                </svg>
                                                                                Edit
                                                                            </button>
                                                                            <button
                                                                                onClick={() => handleDeleteChangeType(type.change_type_id)}
                                                                                className="inline-flex items-center px-3 py-1 bg-red-100 text-red-700 hover:bg-red-200 rounded text-sm font-medium transition-colors"
                                                                            >
                                                                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                                </svg>
                                                                                Delete
                                                                            </button>
                                                                        </div>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-white rounded-lg shadow-md p-6 text-center text-gray-500">
                                    Select a category to view and manage its change types.
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}

            {/* MODEL TYPE TAXONOMY TAB */}
            {activeTab === 'model-type' && (
                <>
                    <div className="mb-6 flex justify-end">
                        <button onClick={() => setShowModelCategoryForm(true)} className="btn-primary">
                            + New Category
                        </button>
                    </div>

                    {showModelCategoryForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h3 className="text-lg font-bold mb-4">Create New Model Category</h3>
                            <form onSubmit={handleModelCategorySubmit}>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="mb-4">
                                        <label htmlFor="mcat_name" className="block text-sm font-medium mb-2">
                                            Name
                                        </label>
                                        <input
                                            id="mcat_name"
                                            type="text"
                                            className="input-field"
                                            value={modelCategoryFormData.name}
                                            onChange={(e) => setModelCategoryFormData({ ...modelCategoryFormData, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="mcat_sort" className="block text-sm font-medium mb-2">
                                            Sort Order
                                        </label>
                                        <input
                                            id="mcat_sort"
                                            type="number"
                                            className="input-field"
                                            value={modelCategoryFormData.sort_order}
                                            onChange={(e) => setModelCategoryFormData({ ...modelCategoryFormData, sort_order: parseInt(e.target.value) })}
                                            required
                                        />
                                    </div>
                                </div>
                                <div className="mb-4">
                                    <label htmlFor="mcat_desc" className="block text-sm font-medium mb-2">
                                        Description
                                    </label>
                                    <textarea
                                        id="mcat_desc"
                                        className="input-field"
                                        rows={2}
                                        value={modelCategoryFormData.description}
                                        onChange={(e) => setModelCategoryFormData({ ...modelCategoryFormData, description: e.target.value })}
                                    />
                                </div>
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">Create</button>
                                    <button type="button" onClick={resetModelCategoryForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="grid grid-cols-4 gap-6">
                        {/* Category list */}
                        <div className="col-span-1">
                            <div className="bg-white rounded-lg shadow-md p-4">
                                <h3 className="font-bold mb-3">Categories</h3>
                                <div className="space-y-2">
                                    {modelCategories.length === 0 ? (
                                        <p className="text-sm text-gray-500">No categories yet.</p>
                                    ) : (
                                        modelCategories.map((cat) => (
                                            <button
                                                key={cat.category_id}
                                                onClick={() => selectModelCategory(cat)}
                                                className={`w-full text-left px-3 py-2 rounded text-sm ${selectedModelCategory?.category_id === cat.category_id
                                                    ? 'bg-blue-100 text-blue-800 font-medium'
                                                    : 'hover:bg-gray-100'
                                                    }`}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span>{cat.name}</span>
                                                    <span className="text-xs bg-gray-200 px-1 rounded">{cat.model_types.length}</span>
                                                </div>
                                            </button>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Selected category model types */}
                        <div className="col-span-3">
                            {selectedModelCategory ? (
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="flex justify-between items-center mb-4">
                                        <h3 className="text-xl font-bold">{selectedModelCategory.name}</h3>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setShowModelTypeForm(true)}
                                                className="btn-primary text-sm"
                                            >
                                                + Add Model Type
                                            </button>
                                            <button
                                                onClick={() => handleDeleteModelCategory(selectedModelCategory.category_id)}
                                                className="btn-secondary text-red-600 text-sm"
                                            >
                                                Delete Category
                                            </button>
                                        </div>
                                    </div>
                                    {selectedModelCategory.description && (
                                        <p className="text-sm text-gray-600 mb-4">
                                            {selectedModelCategory.description}
                                        </p>
                                    )}

                                    {showModelTypeForm && (
                                        <div className="bg-gray-50 p-4 rounded mb-4">
                                            <h4 className="font-medium mb-3">
                                                {editingModelType ? 'Edit Model Type' : 'Add New Model Type'}
                                            </h4>
                                            <form onSubmit={handleModelTypeSubmit}>
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="mb-3">
                                                        <label htmlFor="mtype_name" className="block text-sm font-medium mb-1">
                                                            Name
                                                        </label>
                                                        <input
                                                            id="mtype_name"
                                                            type="text"
                                                            className="input-field"
                                                            value={modelTypeFormData.name}
                                                            onChange={(e) => setModelTypeFormData({ ...modelTypeFormData, name: e.target.value })}
                                                            required
                                                        />
                                                    </div>
                                                    <div className="mb-3">
                                                        <label htmlFor="mtype_sort" className="block text-sm font-medium mb-1">
                                                            Sort Order
                                                        </label>
                                                        <input
                                                            id="mtype_sort"
                                                            type="number"
                                                            className="input-field"
                                                            value={modelTypeFormData.sort_order}
                                                            onChange={(e) => setModelTypeFormData({ ...modelTypeFormData, sort_order: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                </div>
                                                <div className="mb-3">
                                                    <label htmlFor="mtype_desc" className="block text-sm font-medium mb-1">
                                                        Description
                                                    </label>
                                                    <textarea
                                                        id="mtype_desc"
                                                        className="input-field"
                                                        rows={2}
                                                        value={modelTypeFormData.description}
                                                        onChange={(e) => setModelTypeFormData({ ...modelTypeFormData, description: e.target.value })}
                                                    />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="flex items-center gap-2">
                                                        <input
                                                            type="checkbox"
                                                            checked={modelTypeFormData.is_active}
                                                            onChange={(e) => setModelTypeFormData({ ...modelTypeFormData, is_active: e.target.checked })}
                                                        />
                                                        <span className="text-sm font-medium">Active</span>
                                                    </label>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button type="submit" className="btn-primary text-sm">
                                                        {editingModelType ? 'Update' : 'Add'}
                                                    </button>
                                                    <button type="button" onClick={resetModelTypeForm} className="btn-secondary text-sm">
                                                        Cancel
                                                    </button>
                                                </div>
                                            </form>
                                        </div>
                                    )}

                                    <div className="mt-4">
                                        <h4 className="font-medium mb-3">
                                            Model Types ({selectedModelCategory.model_types.length})
                                        </h4>
                                        {selectedModelCategory.model_types.length === 0 ? (
                                            <p className="text-gray-500 text-sm">No model types yet. Add model types to this category.</p>
                                        ) : (
                                            <div className="border rounded overflow-x-auto">
                                                <table className="min-w-full divide-y divide-gray-200">
                                                    <thead className="bg-gray-50">
                                                        <tr>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-16">
                                                                Order
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                Name
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                Description
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-24">
                                                                Status
                                                            </th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-48">
                                                                Actions
                                                            </th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="bg-white divide-y divide-gray-200">
                                                        {selectedModelCategory.model_types
                                                            .sort((a, b) => a.sort_order - b.sort_order)
                                                            .map((type) => (
                                                                <tr key={type.type_id} className={`hover:bg-gray-50 ${!type.is_active ? 'opacity-60' : ''}`}>
                                                                    <td className="px-4 py-3 text-sm text-center">{type.sort_order}</td>
                                                                    <td className="px-4 py-3 text-sm font-medium">{type.name}</td>
                                                                    <td className="px-4 py-3 text-sm text-gray-600">
                                                                        {type.description || '-'}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-sm">
                                                                        {type.is_active ? (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                                                                                Active
                                                                            </span>
                                                                        ) : (
                                                                            <span className="px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-600">
                                                                                Inactive
                                                                            </span>
                                                                        )}
                                                                    </td>
                                                                    <td className="px-4 py-3 whitespace-nowrap">
                                                                        <div className="flex items-center gap-2">
                                                                            <button
                                                                                onClick={() => handleEditModelType(type)}
                                                                                className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 hover:bg-blue-200 rounded text-sm font-medium transition-colors"
                                                                            >
                                                                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                                                </svg>
                                                                                Edit
                                                                            </button>
                                                                            <button
                                                                                onClick={() => handleDeleteModelType(type.type_id)}
                                                                                className="inline-flex items-center px-3 py-1 bg-red-100 text-red-700 hover:bg-red-200 rounded text-sm font-medium transition-colors"
                                                                            >
                                                                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                                </svg>
                                                                                Delete
                                                                            </button>
                                                                        </div>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-white rounded-lg shadow-md p-6 text-center text-gray-500">
                                    Select a category to view and manage its model types.
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}

            {/* KPM LIBRARY TAB */}
            {activeTab === 'kpm' && (
                <>
                    <div className="mb-6 flex justify-end">
                        <button onClick={() => setShowKpmCategoryForm(true)} className="btn-primary">
                            + New Category
                        </button>
                    </div>

                    {showKpmCategoryForm && (
                        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                            <h3 className="text-lg font-bold mb-4">Create New KPM Category</h3>
                            <form onSubmit={handleKpmCategorySubmit}>
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="mb-4">
                                        <label htmlFor="kpm_cat_code" className="block text-sm font-medium mb-2">
                                            Code
                                        </label>
                                        <input
                                            id="kpm_cat_code"
                                            type="text"
                                            className="input-field"
                                            value={kpmCategoryFormData.code}
                                            onChange={(e) => setKpmCategoryFormData({ ...kpmCategoryFormData, code: e.target.value })}
                                            required
                                            placeholder="e.g., model_calibration"
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="kpm_cat_name" className="block text-sm font-medium mb-2">
                                            Name
                                        </label>
                                        <input
                                            id="kpm_cat_name"
                                            type="text"
                                            className="input-field"
                                            value={kpmCategoryFormData.name}
                                            onChange={(e) => setKpmCategoryFormData({ ...kpmCategoryFormData, name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="mb-4">
                                        <label htmlFor="kpm_cat_sort" className="block text-sm font-medium mb-2">
                                            Sort Order
                                        </label>
                                        <input
                                            id="kpm_cat_sort"
                                            type="number"
                                            className="input-field"
                                            value={kpmCategoryFormData.sort_order}
                                            onChange={(e) => setKpmCategoryFormData({ ...kpmCategoryFormData, sort_order: parseInt(e.target.value) })}
                                            required
                                        />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <label htmlFor="kpm_cat_type" className="block text-sm font-medium mb-2">
                                            Category Type
                                        </label>
                                        <select
                                            id="kpm_cat_type"
                                            className="input-field"
                                            value={kpmCategoryFormData.category_type}
                                            onChange={(e) => setKpmCategoryFormData({ ...kpmCategoryFormData, category_type: e.target.value as 'Quantitative' | 'Qualitative' })}
                                            required
                                        >
                                            <option value="Quantitative">Quantitative</option>
                                            <option value="Qualitative">Qualitative</option>
                                        </select>
                                        <p className="text-xs text-gray-500 mt-1">
                                            Quantitative: Metrics with numerical thresholds. Qualitative: Judgment-based assessments.
                                        </p>
                                    </div>
                                    <div>
                                        <label htmlFor="kpm_cat_desc" className="block text-sm font-medium mb-2">
                                            Description
                                        </label>
                                        <textarea
                                            id="kpm_cat_desc"
                                            className="input-field"
                                            rows={2}
                                            value={kpmCategoryFormData.description}
                                            onChange={(e) => setKpmCategoryFormData({ ...kpmCategoryFormData, description: e.target.value })}
                                        />
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button type="submit" className="btn-primary">Create</button>
                                    <button type="button" onClick={resetKpmCategoryForm} className="btn-secondary">
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="grid grid-cols-4 gap-6">
                        {/* Category list - grouped by type */}
                        <div className="col-span-1">
                            <div className="bg-white rounded-lg shadow-md p-4">
                                <h3 className="font-bold mb-3">Categories</h3>
                                {kpmCategories.length === 0 ? (
                                    <p className="text-sm text-gray-500">No categories yet.</p>
                                ) : (
                                    <>
                                        {/* Group categories by their explicit category_type */}
                                        {(() => {
                                            const quantitativeCategories = kpmCategories.filter(cat =>
                                                cat.category_type === 'Quantitative'
                                            );
                                            const qualitativeCategories = kpmCategories.filter(cat =>
                                                cat.category_type === 'Qualitative'
                                            );

                                            return (
                                                <>
                                                    {/* Quantitative Section */}
                                                    {quantitativeCategories.length > 0 && (
                                                        <div className="mb-4">
                                                            <div className="flex items-center gap-2 mb-2 pb-1 border-b border-blue-200">
                                                                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                                                                <span className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
                                                                    Quantitative
                                                                </span>
                                                                <span className="text-xs text-gray-400">({quantitativeCategories.length})</span>
                                                            </div>
                                                            <div className="space-y-1">
                                                                {quantitativeCategories.map((cat) => (
                                                                    <button
                                                                        key={cat.category_id}
                                                                        onClick={() => selectKpmCategory(cat)}
                                                                        className={`w-full text-left px-3 py-2 rounded text-sm ${selectedKpmCategory?.category_id === cat.category_id
                                                                            ? 'bg-blue-100 text-blue-800 font-medium'
                                                                            : 'hover:bg-gray-100'
                                                                            }`}
                                                                    >
                                                                        <div className="flex items-center justify-between">
                                                                            <span className="truncate">{cat.name}</span>
                                                                            <span className="text-xs bg-blue-100 text-blue-700 px-1.5 rounded ml-1">{cat.kpms.length}</span>
                                                                        </div>
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* Qualitative Section */}
                                                    {qualitativeCategories.length > 0 && (
                                                        <div>
                                                            <div className="flex items-center gap-2 mb-2 pb-1 border-b border-purple-200">
                                                                <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                                                                <span className="text-xs font-semibold text-purple-700 uppercase tracking-wide">
                                                                    Qualitative
                                                                </span>
                                                                <span className="text-xs text-gray-400">({qualitativeCategories.length})</span>
                                                            </div>
                                                            <div className="space-y-1">
                                                                {qualitativeCategories.map((cat) => (
                                                                    <button
                                                                        key={cat.category_id}
                                                                        onClick={() => selectKpmCategory(cat)}
                                                                        className={`w-full text-left px-3 py-2 rounded text-sm ${selectedKpmCategory?.category_id === cat.category_id
                                                                            ? 'bg-purple-100 text-purple-800 font-medium'
                                                                            : 'hover:bg-gray-100'
                                                                            }`}
                                                                    >
                                                                        <div className="flex items-center justify-between">
                                                                            <span className="truncate">{cat.name}</span>
                                                                            <span className="text-xs bg-purple-100 text-purple-700 px-1.5 rounded ml-1">{cat.kpms.length}</span>
                                                                        </div>
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                </>
                                            );
                                        })()}
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Selected category KPMs */}
                        <div className="col-span-3">
                            {selectedKpmCategory ? (
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="flex justify-between items-center mb-4">
                                        <div>
                                            <h3 className="text-xl font-bold">{selectedKpmCategory.name}</h3>
                                            <p className="text-xs text-gray-500 font-mono">{selectedKpmCategory.code}</p>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setShowKpmForm(true)}
                                                className="btn-primary text-sm"
                                            >
                                                + Add KPM
                                            </button>
                                            <button
                                                onClick={() => handleDeleteKpmCategory(selectedKpmCategory.category_id)}
                                                className="btn-secondary text-red-600 text-sm"
                                            >
                                                Delete Category
                                            </button>
                                        </div>
                                    </div>
                                    {selectedKpmCategory.description && (
                                        <p className="text-sm text-gray-600 mb-4">
                                            {selectedKpmCategory.description}
                                        </p>
                                    )}

                                    {showKpmForm && (
                                        <div className="bg-gray-50 p-4 rounded mb-4">
                                            <h4 className="font-medium mb-3">
                                                {editingKpm ? 'Edit KPM' : 'Add New KPM'}
                                            </h4>
                                            <form onSubmit={handleKpmSubmit}>
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="mb-3">
                                                        <label htmlFor="kpm_name" className="block text-sm font-medium mb-1">
                                                            Name
                                                        </label>
                                                        <input
                                                            id="kpm_name"
                                                            type="text"
                                                            className="input-field"
                                                            value={kpmFormData.name}
                                                            onChange={(e) => setKpmFormData({ ...kpmFormData, name: e.target.value })}
                                                            required
                                                        />
                                                    </div>
                                                    <div className="mb-3">
                                                        <label htmlFor="kpm_sort" className="block text-sm font-medium mb-1">
                                                            Sort Order
                                                        </label>
                                                        <input
                                                            id="kpm_sort"
                                                            type="number"
                                                            className="input-field"
                                                            value={kpmFormData.sort_order}
                                                            onChange={(e) => setKpmFormData({ ...kpmFormData, sort_order: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                </div>
                                                <div className="mb-3">
                                                    <label htmlFor="kpm_desc" className="block text-sm font-medium mb-1">
                                                        Description
                                                    </label>
                                                    <textarea
                                                        id="kpm_desc"
                                                        className="input-field"
                                                        rows={2}
                                                        value={kpmFormData.description}
                                                        onChange={(e) => setKpmFormData({ ...kpmFormData, description: e.target.value })}
                                                    />
                                                </div>
                                                <div className="mb-3">
                                                    <label htmlFor="kpm_calc" className="block text-sm font-medium mb-1">
                                                        Calculation
                                                    </label>
                                                    <textarea
                                                        id="kpm_calc"
                                                        className="input-field"
                                                        rows={2}
                                                        value={kpmFormData.calculation}
                                                        onChange={(e) => setKpmFormData({ ...kpmFormData, calculation: e.target.value })}
                                                        placeholder="How is this KPM calculated?"
                                                    />
                                                </div>
                                                <div className="mb-3">
                                                    <label htmlFor="kpm_interp" className="block text-sm font-medium mb-1">
                                                        Interpretation
                                                    </label>
                                                    <textarea
                                                        id="kpm_interp"
                                                        className="input-field"
                                                        rows={2}
                                                        value={kpmFormData.interpretation}
                                                        onChange={(e) => setKpmFormData({ ...kpmFormData, interpretation: e.target.value })}
                                                        placeholder="How should this KPM be interpreted?"
                                                    />
                                                </div>
                                                <div className="mb-3">
                                                    <label className="flex items-center gap-2">
                                                        <input
                                                            type="checkbox"
                                                            checked={kpmFormData.is_active}
                                                            onChange={(e) => setKpmFormData({ ...kpmFormData, is_active: e.target.checked })}
                                                        />
                                                        <span className="text-sm font-medium">Active</span>
                                                    </label>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button type="submit" className="btn-primary text-sm">
                                                        {editingKpm ? 'Update' : 'Add'}
                                                    </button>
                                                    <button type="button" onClick={resetKpmForm} className="btn-secondary text-sm">
                                                        Cancel
                                                    </button>
                                                </div>
                                            </form>
                                        </div>
                                    )}

                                    <div className="mt-4">
                                        <h4 className="font-medium mb-3">
                                            KPMs ({selectedKpmCategory.kpms.length})
                                        </h4>
                                        {selectedKpmCategory.kpms.length === 0 ? (
                                            <p className="text-gray-500 text-sm">No KPMs yet. Add KPMs to this category.</p>
                                        ) : (
                                            <div className="space-y-4">
                                                {selectedKpmCategory.kpms
                                                    .sort((a, b) => a.sort_order - b.sort_order)
                                                    .map((kpm) => (
                                                        <div key={kpm.kpm_id} className={`border rounded p-4 ${!kpm.is_active ? 'opacity-60 bg-gray-50' : 'bg-white'}`}>
                                                            <div className="flex justify-between items-start mb-2">
                                                                <div>
                                                                    <h5 className="font-semibold text-lg">{kpm.name}</h5>
                                                                    {!kpm.is_active && (
                                                                        <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-200 text-gray-600">
                                                                            Inactive
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                <div className="flex items-center gap-2">
                                                                    <button
                                                                        onClick={() => handleEditKpm(kpm)}
                                                                        className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 hover:bg-blue-200 rounded text-sm font-medium transition-colors"
                                                                    >
                                                                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                                        </svg>
                                                                        Edit
                                                                    </button>
                                                                    <button
                                                                        onClick={() => handleDeleteKpm(kpm.kpm_id)}
                                                                        className="inline-flex items-center px-3 py-1 bg-red-100 text-red-700 hover:bg-red-200 rounded text-sm font-medium transition-colors"
                                                                    >
                                                                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                        </svg>
                                                                        Delete
                                                                    </button>
                                                                </div>
                                                            </div>
                                                            {kpm.description && (
                                                                <p className="text-sm text-gray-700 mb-2">{kpm.description}</p>
                                                            )}
                                                            {kpm.calculation && (
                                                                <div className="mt-2">
                                                                    <span className="text-xs font-semibold text-gray-500 uppercase">Calculation:</span>
                                                                    <p className="text-sm text-gray-600 mt-1">{kpm.calculation}</p>
                                                                </div>
                                                            )}
                                                            {kpm.interpretation && (
                                                                <div className="mt-2">
                                                                    <span className="text-xs font-semibold text-gray-500 uppercase">Interpretation:</span>
                                                                    <p className="text-sm text-gray-600 mt-1">{kpm.interpretation}</p>
                                                                </div>
                                                            )}
                                                        </div>
                                                    ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-white rounded-lg shadow-md p-6 text-center text-gray-500">
                                    Select a category to view and manage its KPMs.
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}

            {/* FRY 14 CONFIGURATION TAB */}
            {activeTab === 'fry' && (
                <>
                    <div className="mb-4">
                        <p className="text-sm text-gray-700">
                            Manage the Federal Reserve Board FR Y-14 reporting structure including schedules, metric groups, and line items.
                        </p>
                    </div>

                    {fryReports.length === 0 ? (
                        <div className="text-center py-12 bg-white shadow rounded-lg">
                            <p className="text-gray-500">No FRY reports configured.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {fryReports.map((report) => (
                                <div key={report.report_id} className="bg-white shadow rounded-lg overflow-hidden">
                                    {/* Report Header */}
                                    <div
                                        className="px-6 py-4 border-b border-gray-200 cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                                        onClick={() => toggleFryReport(report.report_id)}
                                    >
                                        <div className="flex items-center">
                                            <svg
                                                className={`h-5 w-5 text-gray-400 transition-transform ${expandedReports.has(report.report_id) ? 'transform rotate-90' : ''
                                                    }`}
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                            </svg>
                                            <div className="ml-3">
                                                <h3 className="text-lg font-medium text-gray-900">{report.report_code}</h3>
                                                <p className="text-sm text-gray-500">{report.description}</p>
                                            </div>
                                        </div>
                                        <span
                                            className={`px-2 py-1 text-xs font-medium rounded-full ${report.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                                }`}
                                        >
                                            {report.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </div>

                                    {/* Schedules (expanded view) */}
                                    {expandedReports.has(report.report_id) && selectedFryReport?.report_id === report.report_id && (
                                        <div className="px-6 py-4 bg-gray-50">
                                            {selectedFryReport.schedules && selectedFryReport.schedules.length > 0 ? (
                                                <div className="space-y-3">
                                                    {selectedFryReport.schedules.map((schedule) => (
                                                        <div key={schedule.schedule_id} className="bg-white rounded-md shadow-sm overflow-hidden">
                                                            {/* Schedule Header */}
                                                            <div
                                                                className="px-4 py-3 border-b border-gray-200 cursor-pointer hover:bg-gray-50 flex items-center"
                                                                onClick={() => toggleFrySchedule(schedule.schedule_id)}
                                                            >
                                                                <svg
                                                                    className={`h-4 w-4 text-gray-400 transition-transform ${expandedSchedules.has(schedule.schedule_id) ? 'transform rotate-90' : ''
                                                                        }`}
                                                                    fill="none"
                                                                    viewBox="0 0 24 24"
                                                                    stroke="currentColor"
                                                                >
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                                                </svg>
                                                                <div className="ml-2">
                                                                    <h4 className="text-sm font-medium text-gray-900">{schedule.schedule_code}</h4>
                                                                    {schedule.description && (
                                                                        <p className="text-xs text-gray-500">{schedule.description}</p>
                                                                    )}
                                                                </div>
                                                            </div>

                                                            {/* Metric Groups */}
                                                            {expandedSchedules.has(schedule.schedule_id) && schedule.metric_groups && (
                                                                <div className="px-4 py-3 bg-gray-50">
                                                                    {schedule.metric_groups.map((metricGroup) => (
                                                                        <div key={metricGroup.metric_group_id} className="mb-3 last:mb-0">
                                                                            {/* Metric Group Header */}
                                                                            <div className="bg-white rounded-md p-3 shadow-sm">
                                                                                <div className="flex items-start justify-between">
                                                                                    <div
                                                                                        className="flex-1 cursor-pointer"
                                                                                        onClick={() => toggleFryMetricGroup(metricGroup.metric_group_id)}
                                                                                    >
                                                                                        <div className="flex items-center">
                                                                                            <svg
                                                                                                className={`h-4 w-4 text-gray-400 transition-transform ${expandedMetricGroups.has(metricGroup.metric_group_id)
                                                                                                    ? 'transform rotate-90'
                                                                                                    : ''
                                                                                                    }`}
                                                                                                fill="none"
                                                                                                viewBox="0 0 24 24"
                                                                                                stroke="currentColor"
                                                                                            >
                                                                                                <path
                                                                                                    strokeLinecap="round"
                                                                                                    strokeLinejoin="round"
                                                                                                    strokeWidth={2}
                                                                                                    d="M9 5l7 7-7 7"
                                                                                                />
                                                                                            </svg>
                                                                                            <h5 className="ml-2 text-sm font-medium text-gray-900">
                                                                                                {metricGroup.metric_group_name}
                                                                                            </h5>
                                                                                            <span
                                                                                                className={`ml-2 px-2 py-0.5 text-xs font-medium rounded-full ${metricGroup.model_driven
                                                                                                    ? 'bg-blue-100 text-blue-800'
                                                                                                    : 'bg-gray-100 text-gray-600'
                                                                                                    }`}
                                                                                            >
                                                                                                {metricGroup.model_driven ? 'Model-Driven' : 'Non-Model'}
                                                                                            </span>
                                                                                        </div>
                                                                                    </div>
                                                                                    <button
                                                                                        onClick={() => handleEditFryMetricGroup(metricGroup)}
                                                                                        className="ml-2 text-blue-600 hover:text-blue-800 text-sm"
                                                                                    >
                                                                                        Edit
                                                                                    </button>
                                                                                </div>

                                                                                {metricGroup.rationale && (
                                                                                    <p className="mt-2 text-xs text-gray-600 ml-6">{metricGroup.rationale}</p>
                                                                                )}

                                                                                {/* Line Items */}
                                                                                {expandedMetricGroups.has(metricGroup.metric_group_id) &&
                                                                                    metricGroup.line_items &&
                                                                                    metricGroup.line_items.length > 0 && (
                                                                                        <div className="mt-3 ml-6 pl-3 border-l-2 border-gray-200">
                                                                                            <h6 className="text-xs font-medium text-gray-700 mb-2">Line Items:</h6>
                                                                                            <ul className="space-y-1">
                                                                                                {metricGroup.line_items.map((lineItem, idx) => (
                                                                                                    <li key={lineItem.line_item_id} className="text-xs text-gray-600">
                                                                                                        {idx + 1}. {lineItem.line_item_text}
                                                                                                    </li>
                                                                                                ))}
                                                                                            </ul>
                                                                                        </div>
                                                                                    )}
                                                                            </div>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <p className="text-sm text-gray-500">No schedules available for this report.</p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Edit Metric Group Modal */}
                    {editingFryItem && (
                        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
                            <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                                <h3 className="text-lg font-medium text-gray-900 mb-4">Edit Metric Group</h3>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Metric Group Name</label>
                                        <input
                                            type="text"
                                            value={editingFryItem.metric_group_name}
                                            onChange={(e) => setEditingFryItem({ ...editingFryItem, metric_group_name: e.target.value })}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                        />
                                    </div>

                                    <div>
                                        <label className="flex items-center">
                                            <input
                                                type="checkbox"
                                                checked={editingFryItem.model_driven}
                                                onChange={(e) => setEditingFryItem({ ...editingFryItem, model_driven: e.target.checked })}
                                                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            />
                                            <span className="ml-2 text-sm text-gray-700">Model-Driven</span>
                                        </label>
                                    </div>

                                    <div>
                                        <label className="flex items-center">
                                            <input
                                                type="checkbox"
                                                checked={editingFryItem.is_active}
                                                onChange={(e) => setEditingFryItem({ ...editingFryItem, is_active: e.target.checked })}
                                                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            />
                                            <span className="ml-2 text-sm text-gray-700">Active</span>
                                        </label>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Rationale</label>
                                        <textarea
                                            value={editingFryItem.rationale || ''}
                                            onChange={(e) => setEditingFryItem({ ...editingFryItem, rationale: e.target.value })}
                                            rows={4}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                        />
                                    </div>
                                </div>

                                <div className="mt-6 flex justify-end space-x-3">
                                    <button
                                        onClick={handleCancelFryEdit}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleSaveFryMetricGroup}
                                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                                    >
                                        Save Changes
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* RECOMMENDATION PRIORITY CONFIGURATION TAB */}
            {activeTab === 'recommendation-priority' && (
                <>
                    <div className="mb-4">
                        <p className="text-sm text-gray-700">
                            Configure how each recommendation priority level affects the workflow. Settings determine whether action plans and final approvals are required.
                        </p>
                    </div>

                    {priorityConfigLoading ? (
                        <div className="text-center py-12 bg-white shadow rounded-lg">
                            <p className="text-gray-500">Loading priority configurations...</p>
                        </div>
                    ) : priorityConfigError ? (
                        <div className="text-center py-12 bg-white shadow rounded-lg">
                            <p className="text-red-500">{priorityConfigError}</p>
                            <button
                                onClick={fetchPriorityConfigs}
                                className="mt-4 px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-800"
                            >
                                Retry
                            </button>
                        </div>
                    ) : priorityConfigs.length === 0 ? (
                        <div className="text-center py-12 bg-white shadow rounded-lg">
                            <p className="text-gray-500">No priority configurations found.</p>
                        </div>
                    ) : (
                        <div className="bg-white shadow rounded-lg overflow-hidden">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-10">
                                            {/* Expand */}
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Priority
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Requires Action Plan
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Requires Final Approval
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Enforce Timeframes
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Description
                                        </th>
                                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {priorityConfigs.map((config) => (
                                        <React.Fragment key={config.config_id}>
                                            <tr className="hover:bg-gray-50">
                                                <td className="px-2 py-4">
                                                    <button
                                                        onClick={() => togglePriorityExpanded(config.priority.value_id)}
                                                        className="text-gray-500 hover:text-gray-700"
                                                        title={expandedPriorityIds.has(config.priority.value_id) ? 'Collapse regional overrides' : 'Expand regional overrides'}
                                                    >
                                                        <svg
                                                            className={`h-5 w-5 transform transition-transform ${
                                                                expandedPriorityIds.has(config.priority.value_id) ? 'rotate-90' : ''
                                                            }`}
                                                            fill="none"
                                                            viewBox="0 0 24 24"
                                                            stroke="currentColor"
                                                        >
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                                        </svg>
                                                    </button>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="flex items-center">
                                                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                                            config.priority.code === 'HIGH' ? 'bg-red-100 text-red-800' :
                                                            config.priority.code === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                                                            config.priority.code === 'LOW' ? 'bg-blue-100 text-blue-800' :
                                                            config.priority.code === 'CONSIDERATION' ? 'bg-gray-100 text-gray-600' :
                                                            'bg-gray-100 text-gray-800'
                                                        }`}>
                                                            {config.priority.label}
                                                        </span>
                                                        <span className="ml-2 text-xs text-gray-500">({config.priority.code})</span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                        config.requires_action_plan ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                                                    }`}>
                                                        {config.requires_action_plan ? 'Yes' : 'No'}
                                                    </span>
                                                    <span className="ml-1 text-xs text-gray-400">(default)</span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                        config.requires_final_approval ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                                                    }`}>
                                                        {config.requires_final_approval ? 'Yes' : 'No'}
                                                    </span>
                                                    <span className="ml-1 text-xs text-gray-400">(default)</span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                        config.enforce_timeframes ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                                                    }`}>
                                                        {config.enforce_timeframes ? 'Yes' : 'No'}
                                                    </span>
                                                    <span className="ml-1 text-xs text-gray-400">(default)</span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <p className="text-sm text-gray-600 max-w-xs truncate" title={config.description || ''}>
                                                        {config.description || '—'}
                                                    </p>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <button
                                                        onClick={() => setEditingPriorityConfig(config)}
                                                        className="text-blue-600 hover:text-blue-800"
                                                    >
                                                        Edit
                                                    </button>
                                                </td>
                                            </tr>

                                            {/* Expanded Regional Overrides Section */}
                                            {expandedPriorityIds.has(config.priority.value_id) && (
                                                <tr>
                                                    <td colSpan={7} className="bg-gray-50 px-6 py-4">
                                                        <div className="ml-8">
                                                            <div className="flex justify-between items-center mb-3">
                                                                <h4 className="text-sm font-medium text-gray-700">
                                                                    Regional Overrides for {config.priority.label} Priority
                                                                </h4>
                                                                <button
                                                                    onClick={() => {
                                                                        const availableRegions = getAvailableRegionsForOverride(config.priority.value_id);
                                                                        if (availableRegions.length === 0) {
                                                                            alert('All regions already have overrides for this priority.');
                                                                            return;
                                                                        }
                                                                        setEditingRegionalOverride({
                                                                            isNew: true,
                                                                            priorityId: config.priority.value_id,
                                                                            override: {
                                                                                requires_action_plan: null,
                                                                                requires_final_approval: null,
                                                                                enforce_timeframes: null,
                                                                                description: ''
                                                                            }
                                                                        });
                                                                    }}
                                                                    className="text-sm text-blue-600 hover:text-blue-800"
                                                                >
                                                                    + Add Regional Override
                                                                </button>
                                                            </div>

                                                            {(regionalOverrides[config.priority.value_id] || []).length === 0 ? (
                                                                <p className="text-sm text-gray-500 italic">
                                                                    No regional overrides configured. Default settings apply to all regions.
                                                                </p>
                                                            ) : (
                                                                <table className="min-w-full border border-gray-200 rounded">
                                                                    <thead className="bg-gray-100">
                                                                        <tr>
                                                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                                                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Requires Action Plan</th>
                                                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Requires Final Approval</th>
                                                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Enforce Timeframes</th>
                                                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                                                                            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                                                                        </tr>
                                                                    </thead>
                                                                    <tbody className="divide-y divide-gray-200">
                                                                        {(regionalOverrides[config.priority.value_id] || []).map((override) => (
                                                                            <tr key={override.override_id} className="bg-white">
                                                                                <td className="px-4 py-2">
                                                                                    <span className="text-sm font-medium text-gray-900">
                                                                                        {override.region.name}
                                                                                    </span>
                                                                                    <span className="ml-1 text-xs text-gray-500">({override.region.code})</span>
                                                                                </td>
                                                                                <td className="px-4 py-2">
                                                                                    {override.requires_action_plan === null ? (
                                                                                        <span className="text-xs text-gray-400 italic">Inherit default</span>
                                                                                    ) : (
                                                                                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                                                            override.requires_action_plan ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                                                                                        }`}>
                                                                                            {override.requires_action_plan ? 'Yes' : 'No'}
                                                                                        </span>
                                                                                    )}
                                                                                </td>
                                                                                <td className="px-4 py-2">
                                                                                    {override.requires_final_approval === null ? (
                                                                                        <span className="text-xs text-gray-400 italic">Inherit default</span>
                                                                                    ) : (
                                                                                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                                                            override.requires_final_approval ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                                                                                        }`}>
                                                                                            {override.requires_final_approval ? 'Yes' : 'No'}
                                                                                        </span>
                                                                                    )}
                                                                                </td>
                                                                                <td className="px-4 py-2">
                                                                                    {override.enforce_timeframes === null ? (
                                                                                        <span className="text-xs text-gray-400 italic">Inherit default</span>
                                                                                    ) : (
                                                                                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                                                            override.enforce_timeframes ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                                                                                        }`}>
                                                                                            {override.enforce_timeframes ? 'Yes' : 'No'}
                                                                                        </span>
                                                                                    )}
                                                                                </td>
                                                                                <td className="px-4 py-2">
                                                                                    <span className="text-xs text-gray-600">
                                                                                        {override.description || '—'}
                                                                                    </span>
                                                                                </td>
                                                                                <td className="px-4 py-2 text-right">
                                                                                    <button
                                                                                        onClick={() => setEditingRegionalOverride({
                                                                                            isNew: false,
                                                                                            priorityId: config.priority.value_id,
                                                                                            override: { ...override }
                                                                                        })}
                                                                                        className="text-blue-600 hover:text-blue-800 text-xs mr-3"
                                                                                    >
                                                                                        Edit
                                                                                    </button>
                                                                                    <button
                                                                                        onClick={() => handleDeleteRegionalOverride(override.override_id, config.priority.value_id)}
                                                                                        className="text-red-600 hover:text-red-800 text-xs"
                                                                                    >
                                                                                        Delete
                                                                                    </button>
                                                                                </td>
                                                                            </tr>
                                                                        ))}
                                                                    </tbody>
                                                                </table>
                                                            )}

                                                            <p className="mt-2 text-xs text-gray-500">
                                                                Regional overrides apply when a model is deployed in the specified region.
                                                                If multiple regions apply, the most restrictive setting wins.
                                                            </p>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </React.Fragment>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Edit Priority Config Modal */}
                    {editingPriorityConfig && (
                        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
                            <div className="bg-white rounded-lg p-6 max-w-lg w-full">
                                <h3 className="text-lg font-medium text-gray-900 mb-4">
                                    Edit Priority Configuration: {editingPriorityConfig.priority.label}
                                </h3>

                                <div className="space-y-4">
                                    <div>
                                        <label className="flex items-center">
                                            <input
                                                type="checkbox"
                                                checked={editingPriorityConfig.requires_action_plan}
                                                onChange={(e) => setEditingPriorityConfig({
                                                    ...editingPriorityConfig,
                                                    requires_action_plan: e.target.checked
                                                })}
                                                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            />
                                            <span className="ml-2 text-sm text-gray-700">Requires Action Plan</span>
                                        </label>
                                        <p className="mt-1 text-xs text-gray-500 ml-6">
                                            If unchecked, developers can skip action plan submission and proceed directly to validator review.
                                        </p>
                                    </div>

                                    <div>
                                        <label className="flex items-center">
                                            <input
                                                type="checkbox"
                                                checked={editingPriorityConfig.requires_final_approval}
                                                onChange={(e) => setEditingPriorityConfig({
                                                    ...editingPriorityConfig,
                                                    requires_final_approval: e.target.checked
                                                })}
                                                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            />
                                            <span className="ml-2 text-sm text-gray-700">Requires Final Approval</span>
                                        </label>
                                        <p className="mt-1 text-xs text-gray-500 ml-6">
                                            If checked, closure requires approval from designated approvers before the recommendation can be closed.
                                        </p>
                                    </div>

                                    <div>
                                        <label className="flex items-center">
                                            <input
                                                type="checkbox"
                                                checked={editingPriorityConfig.enforce_timeframes}
                                                onChange={(e) => setEditingPriorityConfig({
                                                    ...editingPriorityConfig,
                                                    enforce_timeframes: e.target.checked
                                                })}
                                                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            />
                                            <span className="ml-2 text-sm text-gray-700">Enforce Timeframes</span>
                                        </label>
                                        <p className="mt-1 text-xs text-gray-500 ml-6">
                                            If checked, target dates must be within the maximum allowed timeframe. If unchecked, timeframe limits are advisory only.
                                        </p>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Description</label>
                                        <textarea
                                            value={editingPriorityConfig.description || ''}
                                            onChange={(e) => setEditingPriorityConfig({
                                                ...editingPriorityConfig,
                                                description: e.target.value
                                            })}
                                            rows={3}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                            placeholder="Optional description of this priority level's workflow..."
                                        />
                                    </div>
                                </div>

                                <div className="mt-6 flex justify-end space-x-3">
                                    <button
                                        onClick={() => setEditingPriorityConfig(null)}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={() => handleSavePriorityConfig(editingPriorityConfig)}
                                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                                    >
                                        Save Changes
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Regional Override Modal */}
                    {editingRegionalOverride && (
                        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
                            <div className="bg-white rounded-lg p-6 max-w-lg w-full">
                                <h3 className="text-lg font-medium text-gray-900 mb-4">
                                    {editingRegionalOverride.isNew ? 'Add Regional Override' : 'Edit Regional Override'}
                                </h3>

                                <div className="space-y-4">
                                    {/* Region selector (only for new overrides) */}
                                    {editingRegionalOverride.isNew && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700">Region</label>
                                            <select
                                                value={editingRegionalOverride.override.region?.region_id || ''}
                                                onChange={(e) => {
                                                    const regionId = parseInt(e.target.value);
                                                    const selectedRegion = regions.find(r => r.region_id === regionId);
                                                    setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: {
                                                            ...editingRegionalOverride.override,
                                                            region: selectedRegion ? {
                                                                region_id: selectedRegion.region_id,
                                                                code: selectedRegion.code,
                                                                name: selectedRegion.name
                                                            } : undefined
                                                        }
                                                    });
                                                }}
                                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                            >
                                                <option value="">Select a region...</option>
                                                {getAvailableRegionsForOverride(editingRegionalOverride.priorityId).map(region => (
                                                    <option key={region.region_id} value={region.region_id}>
                                                        {region.name} ({region.code})
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    )}

                                    {/* Display region for existing overrides */}
                                    {!editingRegionalOverride.isNew && editingRegionalOverride.override.region && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700">Region</label>
                                            <p className="mt-1 text-sm text-gray-900">
                                                {editingRegionalOverride.override.region.name} ({editingRegionalOverride.override.region.code})
                                            </p>
                                        </div>
                                    )}

                                    {/* Requires Action Plan */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">Requires Action Plan</label>
                                        <div className="flex space-x-4">
                                            <label className="flex items-center">
                                                <input
                                                    type="radio"
                                                    name="requires_action_plan"
                                                    checked={editingRegionalOverride.override.requires_action_plan === null}
                                                    onChange={() => setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: { ...editingRegionalOverride.override, requires_action_plan: null }
                                                    })}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm text-gray-700">Inherit default</span>
                                            </label>
                                            <label className="flex items-center">
                                                <input
                                                    type="radio"
                                                    name="requires_action_plan"
                                                    checked={editingRegionalOverride.override.requires_action_plan === true}
                                                    onChange={() => setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: { ...editingRegionalOverride.override, requires_action_plan: true }
                                                    })}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm text-gray-700">Yes</span>
                                            </label>
                                            <label className="flex items-center">
                                                <input
                                                    type="radio"
                                                    name="requires_action_plan"
                                                    checked={editingRegionalOverride.override.requires_action_plan === false}
                                                    onChange={() => setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: { ...editingRegionalOverride.override, requires_action_plan: false }
                                                    })}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm text-gray-700">No</span>
                                            </label>
                                        </div>
                                        <p className="mt-1 text-xs text-gray-500">
                                            Override the default action plan requirement for models deployed in this region.
                                        </p>
                                    </div>

                                    {/* Requires Final Approval */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">Requires Final Approval</label>
                                        <div className="flex space-x-4">
                                            <label className="flex items-center">
                                                <input
                                                    type="radio"
                                                    name="requires_final_approval"
                                                    checked={editingRegionalOverride.override.requires_final_approval === null}
                                                    onChange={() => setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: { ...editingRegionalOverride.override, requires_final_approval: null }
                                                    })}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm text-gray-700">Inherit default</span>
                                            </label>
                                            <label className="flex items-center">
                                                <input
                                                    type="radio"
                                                    name="requires_final_approval"
                                                    checked={editingRegionalOverride.override.requires_final_approval === true}
                                                    onChange={() => setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: { ...editingRegionalOverride.override, requires_final_approval: true }
                                                    })}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm text-gray-700">Yes</span>
                                            </label>
                                            <label className="flex items-center">
                                                <input
                                                    type="radio"
                                                    name="requires_final_approval"
                                                    checked={editingRegionalOverride.override.requires_final_approval === false}
                                                    onChange={() => setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: { ...editingRegionalOverride.override, requires_final_approval: false }
                                                    })}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm text-gray-700">No</span>
                                            </label>
                                        </div>
                                        <p className="mt-1 text-xs text-gray-500">
                                            Override the default final approval requirement for models deployed in this region.
                                        </p>
                                    </div>

                                    {/* Enforce Timeframes */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">Enforce Timeframes</label>
                                        <div className="flex space-x-4">
                                            <label className="flex items-center">
                                                <input
                                                    type="radio"
                                                    name="enforce_timeframes"
                                                    checked={editingRegionalOverride.override.enforce_timeframes === null}
                                                    onChange={() => setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: { ...editingRegionalOverride.override, enforce_timeframes: null }
                                                    })}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm text-gray-700">Inherit default</span>
                                            </label>
                                            <label className="flex items-center">
                                                <input
                                                    type="radio"
                                                    name="enforce_timeframes"
                                                    checked={editingRegionalOverride.override.enforce_timeframes === true}
                                                    onChange={() => setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: { ...editingRegionalOverride.override, enforce_timeframes: true }
                                                    })}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm text-gray-700">Yes</span>
                                            </label>
                                            <label className="flex items-center">
                                                <input
                                                    type="radio"
                                                    name="enforce_timeframes"
                                                    checked={editingRegionalOverride.override.enforce_timeframes === false}
                                                    onChange={() => setEditingRegionalOverride({
                                                        ...editingRegionalOverride,
                                                        override: { ...editingRegionalOverride.override, enforce_timeframes: false }
                                                    })}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm text-gray-700">No</span>
                                            </label>
                                        </div>
                                        <p className="mt-1 text-xs text-gray-500">
                                            Override the default timeframe enforcement for models deployed in this region.
                                        </p>
                                    </div>

                                    {/* Description */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Description</label>
                                        <textarea
                                            value={editingRegionalOverride.override.description || ''}
                                            onChange={(e) => setEditingRegionalOverride({
                                                ...editingRegionalOverride,
                                                override: { ...editingRegionalOverride.override, description: e.target.value }
                                            })}
                                            rows={2}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                            placeholder="Optional description of this regional override..."
                                        />
                                    </div>
                                </div>

                                <div className="mt-6 flex justify-end space-x-3">
                                    <button
                                        onClick={() => setEditingRegionalOverride(null)}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleSaveRegionalOverride}
                                        disabled={editingRegionalOverride.isNew && !editingRegionalOverride.override.region}
                                        className={`px-4 py-2 text-sm font-medium text-white border border-transparent rounded-md ${
                                            editingRegionalOverride.isNew && !editingRegionalOverride.override.region
                                                ? 'bg-blue-400 cursor-not-allowed'
                                                : 'bg-blue-600 hover:bg-blue-700'
                                        }`}
                                    >
                                        {editingRegionalOverride.isNew ? 'Create Override' : 'Save Changes'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Timeframe Configuration Section */}
                    <div className="mt-8 border-t pt-6">
                        <button
                            onClick={toggleTimeframeSection}
                            className="flex items-center justify-between w-full text-left"
                        >
                            <div>
                                <h3 className="text-lg font-medium text-gray-900">Timeframe Configurations</h3>
                                <p className="text-sm text-gray-500">
                                    Configure maximum remediation days by priority, risk tier, and usage frequency
                                </p>
                            </div>
                            <svg
                                className={`h-5 w-5 text-gray-500 transform transition-transform ${showTimeframeSection ? 'rotate-180' : ''}`}
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </button>

                        {showTimeframeSection && (
                            <div className="mt-4">
                                {timeframeConfigsLoading ? (
                                    <div className="text-center py-8">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                                        <p className="mt-2 text-sm text-gray-500">Loading timeframe configurations...</p>
                                    </div>
                                ) : (
                                    <>
                                        {/* Color Legend */}
                                        <div className="mb-4 flex flex-wrap gap-4 text-xs">
                                            <span className="flex items-center gap-1">
                                                <span className="inline-block w-4 h-4 rounded bg-red-100 border border-red-200"></span>
                                                <span className="text-gray-600">Immediate (0 days)</span>
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <span className="inline-block w-4 h-4 rounded bg-orange-100 border border-orange-200"></span>
                                                <span className="text-gray-600">1-90 days</span>
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <span className="inline-block w-4 h-4 rounded bg-yellow-100 border border-yellow-200"></span>
                                                <span className="text-gray-600">91-180 days</span>
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <span className="inline-block w-4 h-4 rounded bg-blue-100 border border-blue-200"></span>
                                                <span className="text-gray-600">181-365 days</span>
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <span className="inline-block w-4 h-4 rounded bg-green-100 border border-green-200"></span>
                                                <span className="text-gray-600">&gt;365 days</span>
                                            </span>
                                        </div>

                                        {/* 2D Matrix Grid by Priority */}
                                        {['HIGH', 'MEDIUM', 'LOW'].map((priority) => {
                                            const priorityConfigs = timeframeConfigs.filter(c => c.priority?.code === priority);
                                            if (priorityConfigs.length === 0) return null;

                                            const riskTiers = ['TIER_1', 'TIER_2', 'TIER_3', 'TIER_4'];
                                            const usageFrequencies = ['DAILY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY'];

                                            const riskTierLabels: Record<string, string> = {
                                                'TIER_1': 'Tier 1 (High)',
                                                'TIER_2': 'Tier 2 (Medium)',
                                                'TIER_3': 'Tier 3 (Low)',
                                                'TIER_4': 'Tier 4 (Very Low)'
                                            };

                                            const frequencyLabels: Record<string, string> = {
                                                'DAILY': 'Daily',
                                                'MONTHLY': 'Monthly',
                                                'QUARTERLY': 'Quarterly',
                                                'ANNUALLY': 'Annually'
                                            };

                                            // Helper to find config for a specific tier/frequency combination
                                            const findConfig = (tierCode: string, freqCode: string) => {
                                                return priorityConfigs.find(
                                                    c => c.risk_tier?.code === tierCode && c.usage_frequency?.code === freqCode
                                                );
                                            };

                                            // Get background color class for cell (without text color)
                                            const getCellBgColor = (maxDays: number): string => {
                                                if (maxDays === 0) return 'bg-red-100 hover:bg-red-200';
                                                if (maxDays <= 90) return 'bg-orange-100 hover:bg-orange-200';
                                                if (maxDays <= 180) return 'bg-yellow-100 hover:bg-yellow-200';
                                                if (maxDays <= 365) return 'bg-blue-100 hover:bg-blue-200';
                                                return 'bg-green-100 hover:bg-green-200';
                                            };

                                            return (
                                                <div key={priority} className="mb-8">
                                                    <h4 className={`text-sm font-semibold mb-3 ${
                                                        priority === 'HIGH' ? 'text-red-700' :
                                                        priority === 'MEDIUM' ? 'text-amber-700' :
                                                        'text-green-700'
                                                    }`}>
                                                        {priority} Priority
                                                    </h4>
                                                    <div className="overflow-x-auto">
                                                        <table className="border-collapse border border-gray-300 rounded-lg">
                                                            <thead>
                                                                <tr>
                                                                    <th className="border border-gray-300 bg-gray-100 px-4 py-2 text-xs font-medium text-gray-600 uppercase w-32">
                                                                        Risk Tier
                                                                    </th>
                                                                    {usageFrequencies.map(freq => (
                                                                        <th key={freq} className="border border-gray-300 bg-gray-100 px-4 py-2 text-xs font-medium text-gray-600 uppercase text-center min-w-[100px]">
                                                                            {frequencyLabels[freq]}
                                                                        </th>
                                                                    ))}
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {riskTiers.map(tier => (
                                                                    <tr key={tier}>
                                                                        <td className="border border-gray-300 bg-gray-50 px-4 py-2 text-sm font-medium text-gray-700">
                                                                            {riskTierLabels[tier]}
                                                                        </td>
                                                                        {usageFrequencies.map(freq => {
                                                                            const config = findConfig(tier, freq);
                                                                            return (
                                                                                <td
                                                                                    key={`${tier}-${freq}`}
                                                                                    className={`border border-gray-300 px-4 py-3 text-center cursor-pointer transition-colors ${
                                                                                        config ? getCellBgColor(config.max_days) : 'bg-gray-50 hover:bg-gray-100'
                                                                                    }`}
                                                                                    onClick={() => config && setEditingTimeframeConfig({...config})}
                                                                                    title={config ? `Click to edit: ${config.max_days} days` : 'No configuration'}
                                                                                >
                                                                                    {config ? (
                                                                                        <span className="text-sm font-semibold text-gray-800">
                                                                                            {config.max_days === 0 ? 'Immediate' : `${config.max_days}d`}
                                                                                        </span>
                                                                                    ) : (
                                                                                        <span className="text-gray-400">-</span>
                                                                                    )}
                                                                                </td>
                                                                            );
                                                                        })}
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                    <p className="mt-2 text-xs text-gray-500">
                                                        Click any cell to edit the maximum remediation days
                                                    </p>
                                                </div>
                                            );
                                        })}

                                        {timeframeConfigs.length === 0 && (
                                            <p className="text-sm text-gray-500 text-center py-4">
                                                No timeframe configurations found. Run database seed to create default configurations.
                                            </p>
                                        )}
                                    </>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Timeframe Config Edit Modal */}
                    {editingTimeframeConfig && (
                        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
                            <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
                                <div className="px-6 py-4 border-b border-gray-200">
                                    <h3 className="text-lg font-medium text-gray-900">
                                        Edit Timeframe Configuration
                                    </h3>
                                </div>
                                <div className="px-6 py-4 space-y-4">
                                    {/* Read-only fields */}
                                    <div className="grid grid-cols-3 gap-4">
                                        <div>
                                            <label className="block text-xs font-medium text-gray-500">Priority</label>
                                            <p className="mt-1 text-sm font-medium text-gray-900">{editingTimeframeConfig.priority?.label || editingTimeframeConfig.priority?.code}</p>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-gray-500">Risk Tier</label>
                                            <p className="mt-1 text-sm font-medium text-gray-900">{editingTimeframeConfig.risk_tier?.label || editingTimeframeConfig.risk_tier?.code?.replace('_', ' ')}</p>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-gray-500">Frequency</label>
                                            <p className="mt-1 text-sm font-medium text-gray-900">{editingTimeframeConfig.usage_frequency?.label || editingTimeframeConfig.usage_frequency?.code}</p>
                                        </div>
                                    </div>

                                    {/* Editable fields */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">
                                            Maximum Days <span className="text-red-500">*</span>
                                        </label>
                                        <input
                                            type="number"
                                            min="0"
                                            value={editingTimeframeConfig.max_days}
                                            onChange={(e) => setEditingTimeframeConfig({
                                                ...editingTimeframeConfig,
                                                max_days: parseInt(e.target.value) || 0
                                            })}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                        />
                                        <p className="mt-1 text-xs text-gray-500">
                                            Use 0 for immediate remediation requirement
                                        </p>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700">Description</label>
                                        <textarea
                                            value={editingTimeframeConfig.description || ''}
                                            onChange={(e) => setEditingTimeframeConfig({
                                                ...editingTimeframeConfig,
                                                description: e.target.value
                                            })}
                                            rows={2}
                                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 input-field"
                                            placeholder="Optional description..."
                                        />
                                    </div>
                                </div>

                                <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
                                    <button
                                        onClick={() => setEditingTimeframeConfig(null)}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleSaveTimeframeConfig}
                                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                                    >
                                        Save Changes
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </Layout>
    );
}
